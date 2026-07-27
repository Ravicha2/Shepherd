"""Tests for agent resolver wiring: pipeline, merge, and CLI call agent resolver
instead of symbolic resolver.

Seams under test:
1. merge_constraints() delegates to resolve_agent_constraints() via config
2. ADGPipeline.build_seed() and run_prepared() accept and forward config
3. symbolic_resolver.py deleted
4. CLI seed_build passes config.langextract through pipeline
5. End-to-end: pipeline produces violations with FQN pattern subjects/objects
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from services.fqn import FQN
from services.models import (
    ADG,
    ChangedFQN,
    ConstraintEdge,
    Diff,
    DiffResult,
    Edge,
    FQNKind,
    FQNNode,
    PredicateType,
    SymbolicConstraint,
)
from services.pipeline import ADGPipeline, PipelineInputs, adg_with_specificity
from services.extract.config import LangExtractConfig


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture
def sample_adg() -> ADG:
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware"), kind=FQNKind.MODULE, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.UserView", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.middleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware", target="app.auth.middleware.AuthMiddleware", kind="CONTAINS"),
        Edge(source="app.api.users.UserView", target="app.auth.middleware.AuthMiddleware", kind="IMPORTS"),
    ]
    return ADG(nodes=nodes, edges=edges)


@pytest.fixture
def sample_constraints() -> list[SymbolicConstraint]:
    return [
        SymbolicConstraint(
            subject="the users API module",
            object="auth middleware",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="ADR 001: API must not depend on auth",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        ),
    ]


@pytest.fixture
def agent_config() -> LangExtractConfig:
    return LangExtractConfig(
        model_id="test-model",
        model_url="https://test.example.com/v1",
        api_key_env="TEST_API_KEY",
        provider="openai",
    )


def _mock_llm_response(subject: str, object: str, predicate: str, adr_id: str, adr_path: str, justification: str = "test"):
    """Build a mock OpenAI response that returns a resolved constraint."""
    msg = MagicMock()
    msg.content = json.dumps({
        "subject": subject,
        "object": object,
        "predicate": predicate,
        "justification": justification,
        "adr_id": adr_id,
        "adr_path": adr_path,
    })
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# -- Seam 1: merge_constraints delegates to agent resolver ------------------


class TestMergeConstraintsUsesAgentResolver:
    """merge_constraints() must call resolve_agent_constraints, not the symbolic one."""

    def test_merge_constraints_calls_agent_resolver(self, sample_adg, sample_constraints, agent_config):
        """merge_constraints with config delegates to resolve_agent_constraints."""
        mock_response = _mock_llm_response(
            subject="app.api.users.*",
            object="app.auth.middleware.*",
            predicate="prohibits_dependency",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("services.adg.merge.resolve_agent_constraints") as mock_resolve, \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            mock_resolve.return_value = [
                ConstraintEdge(
                    subject="app.api.users.*",
                    predicate=PredicateType.PROHIBITS_DEPENDENCY,
                    object="app.auth.middleware.*",
                    justification="ADR 001",
                    adr_id="ADR-001",
                    adr_path="docs/adr/001.md",
                ),
            ]
            from services.adg.merge import merge_constraints
            result = merge_constraints(sample_adg, sample_constraints, config=agent_config)

            mock_resolve.assert_called_once_with(sample_constraints, sample_adg, agent_config)

    def test_merge_constraints_no_symbolic_import(self):
        """merge.py must NOT import resolve_symbolic_constraints."""
        import services.adg.merge as merge_mod
        # The module should not have the old symbolic resolver import
        assert not hasattr(merge_mod, "resolve_symbolic_constraints"), (
            "merge.py still imports resolve_symbolic_constraints; should use resolve_agent_constraints"
        )


# -- Seam 2: Pipeline forwards config ---------------------------------------


class TestPipelineForwardsConfig:
    """ADGPipeline.build_seed() and run_prepared() accept and forward config."""

    def test_build_seed_accepts_config(self, sample_adg, sample_constraints, agent_config):
        """build_seed() must accept config and forward it to merge_constraints."""
        with patch("services.adg.merge.resolve_agent_constraints") as mock_resolve, \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            mock_resolve.return_value = [
                ConstraintEdge(
                    subject="app.api.users.*",
                    predicate=PredicateType.PROHIBITS_DEPENDENCY,
                    object="app.auth.middleware.*",
                    justification="test",
                    adr_id="ADR-001",
                    adr_path="docs/adr/001.md",
                ),
            ]
            result = ADGPipeline.build_seed(sample_adg, sample_constraints, config=agent_config)
            mock_resolve.assert_called_once_with(sample_constraints, sample_adg, agent_config)
            assert len(result.constraint_edges) == 1
            assert result.constraint_edges[0].specificity > 0.0

    def test_run_prepared_accepts_config(self, sample_adg, sample_constraints, agent_config):
        """run_prepared() must accept config in PipelineInputs."""
        with patch("services.adg.merge.resolve_agent_constraints") as mock_resolve, \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            mock_resolve.return_value = [
                ConstraintEdge(
                    subject="app.api.users.*",
                    predicate=PredicateType.PROHIBITS_DEPENDENCY,
                    object="app.auth.middleware.*",
                    justification="test",
                    adr_id="ADR-001",
                    adr_path="docs/adr/001.md",
                ),
            ]
            diff_result = DiffResult(
                to_sha="abc123",
                changed_fqns=[
                    ChangedFQN(
                        fqn=FQN.from_dotted("app.api.users"),
                        change_type="modified",
                        file_path="app/api/users.py",
                        enclosing_module=FQN.from_dotted("app.api.users"),
                    ),
                ],
            )
            inputs = PipelineInputs(
                adg=sample_adg,
                constraints=sample_constraints,
                diff_result=diff_result,
                config=agent_config,
            )
            result = ADGPipeline().run_prepared(inputs)
            mock_resolve.assert_called_once_with(sample_constraints, sample_adg, agent_config)


# -- Seam 3: symbolic_resolver.py deleted ------------------------------------


class TestSymbolicResolverDeleted:
    """symbolic_resolver.py must be removed from the codebase."""

    def test_symbolic_resolver_module_not_importable(self):
        """Importing services.adg.symbolic_resolver must fail."""
        with pytest.raises(ImportError):
            import services.adg.symbolic_resolver  # noqa: F401

    def test_symbolic_resolver_not_in_init_exports(self):
        """resolve_symbolic_constraints must not be in adg.__init__ exports."""
        import services.adg as adg_pkg
        assert "resolve_symbolic_constraints" not in adg_pkg.__all__, (
            "resolve_symbolic_constraints still exported from adg.__init__"
        )


# -- Seam 5: End-to-end pipeline with agent resolver -------------------------


class TestEndToEndPipelineWithAgentResolver:
    """Full pipeline: mock LLM resolves constraints, CPT detects violations."""

    def test_pipeline_produces_violations_with_fqn_patterns(self, sample_adg, sample_constraints, agent_config):
        """End-to-end: agent resolves, CPT detects violations with FQN patterns."""
        mock_response = _mock_llm_response(
            subject="app.api.users.*",
            object="app.auth.middleware.*",
            predicate="prohibits_dependency",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
            justification="ADR 001: API must not depend on auth",
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("services.adg.agent_resolver.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            diff_result = DiffResult(
                to_sha="abc123",
                changed_fqns=[
                    ChangedFQN(
                        fqn=FQN.from_dotted("app.api.users.UserView"),
                        change_type="modified",
                        file_path="app/api/users.py",
                        enclosing_module=FQN.from_dotted("app.api.users"),
                    ),
                ],
            )
            inputs = PipelineInputs(
                adg=sample_adg,
                constraints=sample_constraints,
                diff_result=diff_result,
                config=agent_config,
            )
            result = ADGPipeline().run_prepared(inputs)

            # CPT should detect violations
            assert len(result.violations) >= 1, "Expected at least one violation from agent-resolved constraints"
            # Violations must have FQN pattern subjects/objects (not prose)
            for violation in result.violations:
                assert "." in violation.constraint.subject, (
                    f"Subject should be FQN pattern, got prose: {violation.constraint.subject}"
                )
                assert "." in violation.constraint.object or violation.constraint.object.islower(), (
                    f"Object should be FQN pattern or external package, got: {violation.constraint.object}"
                )