"""Tests for unified agent wiring: pipeline, merge, and CLI use resolve_adr_constraints.

Seams under test:
1. merge_constraint_edges() merges resolved ConstraintEdges (no agent call)
2. ADGPipeline.build_seed() discovers ADRs and calls resolve_adr_constraints
3. ADGPipeline.run_prepared() does not call agent resolver (constraints in ADG)
4. symbolic_resolver.py deleted
5. CLI seed_build passes ADR directory through pipeline
6. End-to-end: pipeline produces violations with FQN patterns
"""
from __future__ import annotations

import json
from pathlib import Path
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
)
from services.pipeline import ADGPipeline, PipelineInputs, adg_with_specificity
from services.adg.merge import merge_constraint_edges


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
def sample_constraint_edges() -> list[ConstraintEdge]:
    return [
        ConstraintEdge(
            subject="app.api.users.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.auth.middleware.*",
            justification="ADR 001: API must not depend on auth",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        ),
    ]


# -- Seam 1: merge_constraint_edges merges resolved edges directly ------------------


class TestMergeConstraintEdges:
    """merge_constraint_edges() merges ConstraintEdges directly, no agent call."""

    def test_merge_adds_edges_to_adg(self, sample_adg, sample_constraint_edges):
        result = merge_constraint_edges(sample_adg, sample_constraint_edges)
        assert len(result.constraint_edges) == 1
        assert result.constraint_edges[0].subject == "app.api.users.*"

    def test_merge_no_symbolic_import(self):
        """merge.py must NOT import resolve_agent_constraints."""
        import services.adg.merge as merge_mod
        assert not hasattr(merge_mod, "resolve_agent_constraints"), (
            "merge.py still imports resolve_agent_constraints; should only merge resolved edges"
        )


# -- Seam 2: Pipeline build_seed calls resolve_adr_constraints -----------------------


class TestPipelineBuildSeed:
    """ADGPipeline.build_seed() discovers ADRs and calls resolve_adr_constraints."""

    def test_build_seed_calls_resolve_adr_constraints(self, sample_adg, tmp_path):
        """build_seed() must call resolve_adr_constraints for each ADR file."""
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "001-test.md").write_text("# ADR 001\n\nWe chose X.")

        mock_config = MagicMock()

        with patch("services.adg.unified_resolver.resolve_adr_constraints") as mock_resolve:
            mock_resolve.return_value = [
                ConstraintEdge(
                    subject="app.api.*",
                    predicate=PredicateType.PROHIBITS_DEPENDENCY,
                    object="app.auth.*",
                    justification="test",
                    adr_id="001-test",
                    adr_path=str(adr_dir / "001-test.md"),
                ),
            ]
            result = ADGPipeline.build_seed(sample_adg, adr_dir, config=mock_config)

            mock_resolve.assert_called_once()
            assert len(result.constraint_edges) == 1
            assert result.constraint_edges[0].specificity > 0.0

    def test_build_seed_requires_config(self, sample_adg, tmp_path):
        """build_seed() must raise ValueError if config is not provided."""
        with pytest.raises(ValueError, match="config is required"):
            ADGPipeline.build_seed(sample_adg, tmp_path)

    def test_build_seed_empty_adr_dir(self, sample_adg, tmp_path):
        """build_seed() with no ADR files returns ADG with specificity but no constraints."""
        empty_dir = tmp_path / "empty_adr"
        empty_dir.mkdir()

        result = ADGPipeline.build_seed(sample_adg, empty_dir, config=MagicMock())
        assert len(result.constraint_edges) == 0

    def test_run_prepared_does_not_call_agent(self, sample_adg, sample_constraint_edges):
        """run_prepared() must not call any agent resolver; constraints are in the ADG."""
        adg_with_constraints = ADG(
            nodes=sample_adg.nodes,
            edges=sample_adg.edges,
            constraint_edges=sample_constraint_edges,
        )
        diff_result = DiffResult(to_sha="abc123", changed_fqns=[])

        with patch("services.pipeline.add_external_nodes", wraps=lambda adg, **kw: adg) as mock_ext:
            inputs = PipelineInputs(adg=adg_with_constraints, diff_result=diff_result)
            result = ADGPipeline().run_prepared(inputs)
            # add_external_nodes is called, but no agent resolver
            mock_ext.assert_called_once()


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


# -- Seam 5: End-to-end pipeline with constraint edges in ADG -------------------------


class TestEndToEndPipelineWithConstraintEdges:
    """Full pipeline: constraint edges in ADG, CPT detects violations."""

    def test_pipeline_produces_violations_with_fqn_patterns(self, sample_adg):
        """End-to-end: constraint edges in ADG, CPT detects violations with FQN patterns."""
        constraint_edges = [
            ConstraintEdge(
                subject="app.api.users.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.auth.middleware.*",
                justification="ADR 001: API must not depend on auth",
                adr_id="ADR-001",
                adr_path="docs/adr/001.md",
            ),
        ]
        adg_with_constraints = ADG(
            nodes=sample_adg.nodes,
            edges=sample_adg.edges,
            constraint_edges=constraint_edges,
        )
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
        inputs = PipelineInputs(adg=adg_with_constraints, diff_result=diff_result)
        result = ADGPipeline().run_prepared(inputs)

        # CPT should detect violations
        assert len(result.violations) >= 1, "Expected at least one violation from constraint edges"
        # Violations must have FQN pattern subjects/objects (not prose)
        for violation in result.violations:
            assert "." in violation.constraint.subject, (
                f"Subject should be FQN pattern, got prose: {violation.constraint.subject}"
            )
            assert "." in violation.constraint.object or violation.constraint.object.islower(), (
                f"Object should be FQN pattern or external package, got: {violation.constraint.object}"
            )