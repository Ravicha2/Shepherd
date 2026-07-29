"""Tests for unified_resolver: one LLM session per ADR producing ConstraintEdges.

Tests mock the LLM API to verify resolution orchestration, not instruction-following.
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    Edge,
    FQNKind,
    FQNNode,
    PredicateType,
)
from services.adg.adg_tools import dive, list_modules
from services.adg.unified_resolver import (
    _add_wildcard_for_modules,
    _external_packages,
    _extract_json,
    _is_internal,
    _parse_edges,
    _root_segments,
    _validate_edge,
    resolve_adr_constraints,
    ResolutionTrace,
    TOOL_CALL_CAP,
)
from services.extract.config import LangExtractConfig


# -- Fixtures ---------------------------------------------------------------

ADR_PROHIBIT_DEP = """\
# ADR 001: Prohibit direct database access from API layer

## Status
Accepted

## Context
The API layer should not directly import database modules. All database
access must go through the repository layer.

## Decision
We prohibit any import of app.db modules from app.api modules. The API
layer must use app.repository for all data access.

## Consequences
- API modules cannot import database modules directly
- All data access goes through the repository abstraction
"""

ADR_PRESCRIBE_IMPL = """\
# ADR 002: Use RepositoryBase for all repository implementations

## Status
Accepted

## Context
We need a consistent interface for all repository classes. Currently
repositories implement their own interfaces inconsistently.

## Decision Outcome
We chose option 3: build a minimal RepositoryBase abstraction. All repository
implementations must inherit from RepositoryBase.

## Consequences
- RepositoryBase is the required base class for all repositories
- New repositories must implement the RepositoryBase interface
"""

ADR_NO_CONSTRAINTS = """\
# ADR 003: Use Python 3.12

## Status
Accepted

## Context
We need to decide on a Python version for the project.

## Decision
We will use Python 3.12 for the project.

## Consequences
- All code must be compatible with Python 3.12
"""


@pytest.fixture
def sample_adg() -> ADG:
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=1000),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.db"), kind=FQNKind.MODULE, file_path="app/db/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.db.queries"), kind=FQNKind.MODULE, file_path="app/db/queries.py", line_start=0, line_end=30, start_byte=0, end_byte=500),
        FQNNode(fqn=FQN.from_dotted("app.repository"), kind=FQNKind.MODULE, file_path="app/repository/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.repository.RepositoryBase"), kind=FQNKind.CLASS, file_path="app/repository/base.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware"), kind=FQNKind.MODULE, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=1200),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.UserView", kind="CONTAINS"),
        Edge(source="app", target="app.db", kind="CONTAINS"),
        Edge(source="app.db", target="app.db.queries", kind="CONTAINS"),
        Edge(source="app", target="app.repository", kind="CONTAINS"),
        Edge(source="app.repository", target="app.repository.RepositoryBase", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.middleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware", target="app.auth.middleware.AuthMiddleware", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.auth.middleware", kind="IMPORTS"),
    ]
    return ADG(nodes=nodes, edges=edges)


# -- Helpers -----------------------------------------------------------------

def _make_config() -> LangExtractConfig:
    return LangExtractConfig(
        model_id="test-model",
        model_url="https://test.example.com/v1",
        api_key_env="TEST_API_KEY",
        provider="openai",
    )


def _make_mock_response(content: str | None = None, tool_calls: list[dict] | None = None):
    msg = MagicMock()
    msg.content = content
    if tool_calls:
        tc_objs = []
        for tc in tool_calls:
            tc_obj = MagicMock()
            tc_obj.id = tc["id"]
            tc_obj.type = "function"
            tc_obj.function.name = tc["function"]["name"]
            tc_obj.function.arguments = tc["function"]["arguments"]
            tc_objs.append(tc_obj)
        msg.tool_calls = tc_objs
    else:
        msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


def _tool_call(call_id: str, name: str, arguments: dict) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _run_unified(
    adr_text: str,
    adr_id: str,
    adr_path: str,
    adg: ADG,
    responses: list,
) -> list[ConstraintEdge]:
    mock_client = MagicMock()
    responses_iter = iter(responses)
    mock_client.chat.completions.create.side_effect = lambda **kwargs: next(responses_iter)

    with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
         patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
        config = _make_config()
        return resolve_adr_constraints(adr_text, adr_id, adr_path, adg, config)


# -- Test: basic resolution --------------------------------------------------

class TestBasicResolution:
    def test_single_prohibition_constraint(self, sample_adg: ADG) -> None:
        """Prohibition ADR produces prohibits_dependency edge."""
        responses = [
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.api.*",
                    "object": "app.db.*",
                    "predicate": "prohibits_dependency",
                    "justification": "API must not import DB modules directly",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"
        assert edges[0].object == "app.db.*"
        assert edges[0].predicate == PredicateType.PROHIBITS_DEPENDENCY

    def test_prescriptive_constraint(self, sample_adg: ADG) -> None:
        """Prescriptive ADR produces requires_implementation, not prohibition."""
        responses = [
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.repository.*",
                    "object": "app.repository.RepositoryBase",
                    "predicate": "requires_implementation",
                    "justification": "All repositories must inherit RepositoryBase",
                    "adr_id": "ADR-002",
                    "adr_path": "docs/adr/002.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PRESCRIBE_IMPL, "ADR-002", "docs/adr/002.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].predicate == PredicateType.REQUIRES_IMPLEMENTATION

    def test_no_constraints_returns_empty(self, sample_adg: ADG) -> None:
        """ADR with no architectural constraints returns empty list."""
        responses = [
            _make_mock_response(content="[]"),
        ]
        edges = _run_unified(ADR_NO_CONSTRAINTS, "ADR-003", "docs/adr/003.md", sample_adg, responses)
        assert edges == []

    def test_multiple_constraints_from_one_adr(self, sample_adg: ADG) -> None:
        """Single ADR session produces multiple ConstraintEdges."""
        responses = [
            _make_mock_response(
                content=json.dumps([
                    {
                        "subject": "app.api.*",
                        "object": "app.db.*",
                        "predicate": "prohibits_dependency",
                        "justification": "API must not import DB",
                        "adr_id": "ADR-001",
                        "adr_path": "docs/adr/001.md",
                    },
                    {
                        "subject": "app.api.*",
                        "object": "app.repository.*",
                        "predicate": "requires_dependency",
                        "justification": "API must use repository for data access",
                        "adr_id": "ADR-001",
                        "adr_path": "docs/adr/001.md",
                    },
                ]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 2


# -- Test: tool-calling resolution ------------------------------------------

class TestToolCalling:
    def test_uses_tools_then_resolves(self, sample_adg: ADG) -> None:
        """Agent calls list_modules, dive, then produces constraints."""
        modules_result = json.dumps(list_modules(sample_adg))
        dive_result = json.dumps(dive("app.api", sample_adg, depth=2))

        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "list_modules", {})]),
            _make_mock_response(tool_calls=[_tool_call("tc2", "dive", {"fqn": "app.api", "depth": 2})]),
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.api.*",
                    "object": "app.db.*",
                    "predicate": "prohibits_dependency",
                    "justification": "API must not import DB",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"


# -- Test: wildcard fallback ------------------------------------------------

class TestWildcardFallback:
    def test_module_fqn_gets_wildcard(self, sample_adg: ADG) -> None:
        """Module-level FQNs automatically get .* wildcard appended."""
        responses = [
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.api",
                    "object": "app.db",
                    "predicate": "prohibits_dependency",
                    "justification": "test",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"
        assert edges[0].object == "app.db.*"

    def test_class_fqn_no_wildcard(self, sample_adg: ADG) -> None:
        """Class-level FQNs keep their exact FQN (no wildcard)."""
        responses = [
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.repository.*",
                    "object": "app.repository.RepositoryBase",
                    "predicate": "requires_implementation",
                    "justification": "test",
                    "adr_id": "ADR-002",
                    "adr_path": "docs/adr/002.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PRESCRIBE_IMPL, "ADR-002", "docs/adr/002.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].object == "app.repository.RepositoryBase"


# -- Test: tool call cap -----------------------------------------------------

class TestToolCallCap:
    def test_cap_sends_best_effort(self, sample_adg: ADG) -> None:
        """After hitting tool call cap, a best-effort request is sent."""
        many_responses = []
        for i in range(TOOL_CALL_CAP):
            many_responses.append(
                _make_mock_response(tool_calls=[_tool_call(f"tc{i}", "dive", {"fqn": "app.api", "depth": 2})])
            )
        # Best-effort response after cap
        many_responses.append(
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.api.*",
                    "object": "app.db.*",
                    "predicate": "prohibits_dependency",
                    "justification": "best-effort after cap",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }]),
            )
        )
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, many_responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"

    def test_cap_best_effort_failure_returns_empty(self, sample_adg: ADG) -> None:
        """If best-effort response is unparseable, return empty."""
        many_responses = []
        for i in range(TOOL_CALL_CAP):
            many_responses.append(
                _make_mock_response(tool_calls=[_tool_call(f"tc{i}", "dive", {"fqn": "app.api", "depth": 2})])
            )
        many_responses.append(_make_mock_response(content="Cannot resolve."))
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, many_responses)
        assert edges == []


# -- Test: _extract_json ----------------------------------------------------

class TestExtractJson:
    def test_plain_json_array(self) -> None:
        raw = '[{"subject": "app.api.*"}]'
        assert _extract_json(raw) == raw

    def test_markdown_fence(self) -> None:
        raw = '```json\n[{"subject": "app.api.*"}]\n```'
        result = _extract_json(raw)
        assert '"subject"' in result

    def test_json_with_surrounding_text(self) -> None:
        raw = 'Here is the result:\n[{"subject": "app.api.*"}]\nDone.'
        assert '"subject"' in _extract_json(raw)

    def test_single_object_fallback(self) -> None:
        raw = 'Some text {"subject": "app.api.*", "object": "app.db.*"} more'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["subject"] == "app.api.*"


# -- Test: _parse_edges -----------------------------------------------------

class TestParseEdges:
    def test_valid_array(self) -> None:
        data = json.dumps([{
            "subject": "app.api.*",
            "object": "app.db.*",
            "predicate": "prohibits_dependency",
            "justification": "test",
            "adr_id": "ADR-001",
            "adr_path": "docs/adr/001.md",
        }])
        edges = _parse_edges(data, "ADR-001", "docs/adr/001.md")
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"

    def test_single_dict_wrapped(self) -> None:
        data = json.dumps({
            "subject": "app.api.*",
            "object": "app.db.*",
            "predicate": "prohibits_dependency",
            "justification": "test",
            "adr_id": "ADR-001",
            "adr_path": "docs/adr/001.md",
        })
        edges = _parse_edges(data, "ADR-001", "docs/adr/001.md")
        assert len(edges) == 1

    def test_empty_array(self) -> None:
        assert _parse_edges("[]", "ADR-001", "docs/adr/001.md") == []

    def test_invalid_predicate_skipped(self) -> None:
        data = json.dumps([{
            "subject": "app.api.*",
            "object": "app.db.*",
            "predicate": "unknown_predicate",
            "justification": "test",
            "adr_id": "ADR-001",
            "adr_path": "docs/adr/001.md",
        }])
        edges = _parse_edges(data, "ADR-001", "docs/adr/001.md")
        assert len(edges) == 0

    def test_empty_subject_skipped(self) -> None:
        data = json.dumps([{
            "subject": "",
            "object": "app.db.*",
            "predicate": "prohibits_dependency",
            "justification": "test",
            "adr_id": "ADR-001",
            "adr_path": "docs/adr/001.md",
        }])
        edges = _parse_edges(data, "ADR-001", "docs/adr/001.md")
        assert len(edges) == 0

    def test_default_adr_id_and_path(self) -> None:
        data = json.dumps([{
            "subject": "app.api.*",
            "object": "app.db.*",
            "predicate": "prohibits_dependency",
            "justification": "test",
        }])
        edges = _parse_edges(data, "ADR-001", "docs/adr/001.md")
        assert edges[0].adr_id == "ADR-001"
        assert edges[0].adr_path == "docs/adr/001.md"


# -- Test: JSONL trace logging -------------------------------------------------

class TestLogTrace:
    def test_writes_jsonl_on_success(self, sample_adg: ADG, tmp_path) -> None:
        from services.adg.unified_resolver import _log_trace
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.db.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        trace = ResolutionTrace(tool_calls=[{"name": "list_modules", "arguments": {}}], hit_cap=False, parse_failed=False)
        with patch.dict("os.environ", {"RESOLVER_TRACE_DIR": str(tmp_path)}):
            _log_trace("ADR-001", "docs/adr/001.md", [edge], trace)
        trace_file = tmp_path / "resolver_traces.jsonl"
        assert trace_file.exists()
        record = json.loads(trace_file.read_text().strip())
        assert record["resolver"] == "unified"
        assert record["adr_id"] == "ADR-001"
        assert record["num_edges"] == 1
        assert record["edges"][0]["predicate"] == "prohibits_dependency"

    def test_writes_jsonl_on_miss(self, sample_adg: ADG, tmp_path) -> None:
        from services.adg.unified_resolver import _log_trace
        trace = ResolutionTrace(tool_calls=[], hit_cap=True, parse_failed=False)
        with patch.dict("os.environ", {"RESOLVER_TRACE_DIR": str(tmp_path)}):
            _log_trace("ADR-001", "docs/adr/001.md", [], trace)
        record = json.loads((tmp_path / "resolver_traces.jsonl").read_text().strip())
        assert record["num_edges"] == 0
        assert record["hit_cap"] is True


# -- Test: _add_wildcard_for_modules -----------------------------------------

class TestAddWildcardForModules:
    def test_module_gets_wildcard(self, sample_adg: ADG) -> None:
        assert _add_wildcard_for_modules("app.api", sample_adg) == "app.api.*"

    def test_already_has_wildcard(self, sample_adg: ADG) -> None:
        assert _add_wildcard_for_modules("app.api.*", sample_adg) == "app.api.*"

    def test_class_no_wildcard(self, sample_adg: ADG) -> None:
        assert _add_wildcard_for_modules("app.auth.middleware.AuthMiddleware", sample_adg) == "app.auth.middleware.AuthMiddleware"

    def test_unknown_fqn_unchanged(self, sample_adg: ADG) -> None:
        assert _add_wildcard_for_modules("unknown.module", sample_adg) == "unknown.module"


# -- Test: _validate_edge ----------------------------------------------------

class TestRootSegments:
    def test_returns_top_level_modules(self, sample_adg: ADG) -> None:
        # ponytail: top-level modules = MODULE nodes with no CONTAINS parent
        assert _root_segments(sample_adg) == {"app"}

    def test_empty_adg_returns_empty_set(self) -> None:
        empty_adg = ADG(nodes=[], edges=[])
        assert _root_segments(empty_adg) == set()


# -- Test: _external_packages -------------------------------------------------

class TestExternalPackages:
    def test_no_imports_returns_empty_set(self, sample_adg: ADG) -> None:
        # sample_adg has one internal IMPORTS edge (app.api.users -> app.auth.middleware)
        assert _external_packages(sample_adg) == set()

    def test_external_imports_returned(self) -> None:
        adg = ADG(
            nodes=[FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0)],
            edges=[Edge(source="app", target="elasticsearch", kind="IMPORTS")],
        )
        assert _external_packages(adg) == {"elasticsearch"}

    def test_submodule_import_returns_root(self) -> None:
        adg = ADG(
            nodes=[FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0)],
            edges=[Edge(source="app", target="graphene.relay.Node", kind="IMPORTS")],
        )
        assert _external_packages(adg) == {"graphene"}


# -- Test: _validate_edge ----------------------------------------------------

class TestValidateEdge:
    def test_valid_module_patterns_pass(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.db.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is True

    def test_valid_class_patterns_pass(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="app.repository.*",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            object="app.repository.RepositoryBase",
            justification="test",
            adr_id="ADR-002",
            adr_path="docs/adr/002.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is True

    def test_hallucinated_subject_fails(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="app.nonexistent.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.db.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is False

    def test_hallucinated_object_fails(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.hallucinated.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is False

    def test_both_hallucinated_fails(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="app.api_layer.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.database_layer.*",
            justification="test",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is False

    def test_requires_external_object_in_list_passes(self, sample_adg: ADG) -> None:
        # ponytail: requires_* external object must be in external_packages list
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            object="elasticsearch",
            justification="ADR requires Elasticsearch for fulltext search",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, {"elasticsearch"}) is True

    def test_requires_external_object_not_in_list_fails(self, sample_adg: ADG) -> None:
        # ponytail: hallucinated external package for requires_* is dropped
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            object="halluc_pkg",
            justification="not actually imported",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is False

    def test_prohibits_external_object_not_in_list_passes(self, sample_adg: ADG) -> None:
        # ponytail: prohibits_* external object may be absent (linter checks absence)
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="rest_framework",
            justification="ADR prohibits REST framework; not imported in codebase",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is True

    def test_external_package_subject_passes(self, sample_adg: ADG) -> None:
        edge = ConstraintEdge(
            subject="django",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            object="app.repository.RepositoryBase",
            justification="external subject, internal object",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is True

    def test_hallucinated_internal_object_with_external_subject_fails(self, sample_adg: ADG) -> None:
        # External subject passes, but hallucinated internal object must still drop.
        edge = ConstraintEdge(
            subject="django",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            object="app.hallucinated.*",
            justification="bad internal object",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        assert _validate_edge(edge, sample_adg, set()) is False


# -- Test: _is_internal -------------------------------------------------------

class TestIsInternal:
    def test_internal_module_is_internal(self, sample_adg: ADG) -> None:
        assert _is_internal("app.api.*", sample_adg) is True

    def test_internal_class_is_internal(self, sample_adg: ADG) -> None:
        assert _is_internal("app.repository.RepositoryBase", sample_adg) is True

    def test_external_package_is_not_internal(self, sample_adg: ADG) -> None:
        assert _is_internal("elasticsearch", sample_adg) is False

    def test_external_package_with_wildcard_is_not_internal(self, sample_adg: ADG) -> None:
        assert _is_internal("django.*", sample_adg) is False

    def test_hallucinated_internal_prefix_is_not_internal(self, sample_adg: ADG) -> None:
        # First segment IS a root, but no ADG node matches -> not internal (hallucination).
        assert _is_internal("app.hallucinated.*", sample_adg) is False


# -- Test: loop detection ------------------------------------------------------

class TestLoopDetection:
    def test_repeated_tool_call_injects_nudge(self, sample_adg: ADG) -> None:
        """If LLM repeats the same dive call, a nudge message is injected."""
        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "dive", {"fqn": "app.api", "depth": 2})]),
            _make_mock_response(tool_calls=[_tool_call("tc2", "dive", {"fqn": "app.api", "depth": 2})]),
            _make_mock_response(
                content=json.dumps([{
                    "subject": "app.api.*",
                    "object": "app.db.*",
                    "predicate": "prohibits_dependency",
                    "justification": "after nudge",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"


# -- Test: end-to-end hallucination filtering ---------------------------------

class TestHallucinationFiltering:
    def test_hallucinated_fqns_filtered_out(self, sample_adg: ADG) -> None:
        """Edges with nonexistent FQNs are dropped, valid ones are kept."""
        responses = [
            _make_mock_response(
                content=json.dumps([
                    {
                        "subject": "app.api.*",
                        "object": "app.db.*",
                        "predicate": "prohibits_dependency",
                        "justification": "valid edge",
                        "adr_id": "ADR-001",
                        "adr_path": "docs/adr/001.md",
                    },
                    {
                        "subject": "app.hallucinated.*",
                        "object": "app.db.*",
                        "predicate": "prohibits_dependency",
                        "justification": "bad subject",
                        "adr_id": "ADR-001",
                        "adr_path": "docs/adr/001.md",
                    },
                    {
                        "subject": "app.api.*",
                        "object": "app.also_fake.*",
                        "predicate": "prohibits_dependency",
                        "justification": "bad object",
                        "adr_id": "ADR-001",
                        "adr_path": "docs/adr/001.md",
                    },
                ]),
            ),
        ]
        edges = _run_unified(ADR_PROHIBIT_DEP, "ADR-001", "docs/adr/001.md", sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"
        assert edges[0].object == "app.db.*"