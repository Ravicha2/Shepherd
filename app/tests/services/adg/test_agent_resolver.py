"""Tests for agent_resolver: OpenAI SDK tool-calling loop that resolves
SymbolicConstraints to ConstraintEdges by traversing the ADG.

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
    SymbolicConstraint,
)
from services.adg.adg_tools import dive, list_modules
from services.adg.agent_resolver import resolve_agent_constraints, _extract_json, TOOL_CALL_CAP


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture
def sample_adg() -> ADG:
    """ADG with auth/api modules for resolution tests."""
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=1000),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware"), kind=FQNKind.MODULE, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=1200),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.UserView", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.middleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware", target="app.auth.middleware.AuthMiddleware", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.auth.middleware", kind="IMPORTS"),
    ]
    return ADG(nodes=nodes, edges=edges)


@pytest.fixture
def auth_constraint() -> SymbolicConstraint:
    return SymbolicConstraint(
        subject="the users API module",
        object="auth middleware module",
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        justification="ADR 001: API modules must not depend on auth middleware",
        adr_id="ADR-001",
        adr_path="docs/adr/001.md",
    )


# -- Helpers for mocking OpenAI SDK responses --------------------------------

def _tool_call(call_id: str, name: str, arguments: dict) -> dict:
    """Build a mock tool_call dict matching OpenAI SDK structure."""
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _assistant_msg(tool_calls: list[dict]) -> dict:
    """Assistant message with tool calls."""
    return {"role": "assistant", "content": None, "tool_calls": tool_calls}


def _tool_result_msg(tool_call_id: str, content: str) -> dict:
    """Tool result message."""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def _final_answer(subject: str, object: str, predicate: str, justification: str, adr_id: str, adr_path: str) -> dict:
    """Final assistant message with resolved constraint as JSON."""
    return {
        "role": "assistant",
        "content": json.dumps({
            "subject": subject,
            "object": object,
            "predicate": predicate,
            "justification": justification,
            "adr_id": adr_id,
            "adr_path": adr_path,
        }),
    }


# -- Test: basic resolution --------------------------------------------------

class TestBasicResolution:
    """Verify resolve_agent_constraints produces ConstraintEdges from
    SymbolicConstraints via an LLM tool-calling loop."""

    def test_single_constraint_produces_edge(
        self, sample_adg: ADG, auth_constraint: SymbolicConstraint
    ) -> None:
        # LLM calls list_modules → gets modules, then dive on auth →
        # resolves to exact FQNs, returns final answer
        modules_result = json.dumps(list_modules(sample_adg))
        dive_auth_result = json.dumps(dive("app.auth", sample_adg, depth=2))
        dive_api_result = json.dumps(dive("app.api", sample_adg, depth=2))

        responses = [
            # Round 1: LLM asks for modules
            _make_mock_response(
                tool_calls=[_tool_call("tc1", "list_modules", {})],
            ),
            # Round 2: LLM sees modules, dives into auth
            _make_mock_response(
                tool_calls=[_tool_call("tc2", "dive", {"fqn": "app.auth", "depth": 2})],
            ),
            # Round 3: LLM dives into api too
            _make_mock_response(
                tool_calls=[_tool_call("tc3", "dive", {"fqn": "app.api", "depth": 2})],
            ),
            # Round 4: LLM returns resolved constraint
            _make_mock_response(
                content=json.dumps({
                    "subject": "app.api.users.*",
                    "object": "app.auth.middleware.*",
                    "predicate": "prohibits_dependency",
                    "justification": "ADR 001: API modules must not depend on auth middleware",
                    "adr_id": "ADR-001",
                    "adr_path": "docs/adr/001.md",
                }),
            ),
        ]

        edges = _run_resolver(auth_constraint, sample_adg, responses)

        assert len(edges) == 1
        edge = edges[0]
        assert edge.subject == "app.api.users.*"
        assert edge.object == "app.auth.middleware.*"
        assert edge.predicate == PredicateType.PROHIBITS_DEPENDENCY
        assert edge.adr_id == "ADR-001"

    def test_no_tool_calls_direct_answer(
        self, sample_adg: ADG, auth_constraint: SymbolicConstraint
    ) -> None:
        """LLM answers immediately without tool calls."""
        responses = [
            _make_mock_response(
                content=json.dumps({
                    "subject": "app.api.*",
                    "object": "app.auth.*",
                    "predicate": "prohibits_dependency",
                    "justification": auth_constraint.justification,
                    "adr_id": auth_constraint.adr_id,
                    "adr_path": auth_constraint.adr_path,
                }),
            ),
        ]

        edges = _run_resolver(auth_constraint, sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].subject == "app.api.*"


# -- Test: tool call cap -----------------------------------------------------

class TestToolCallCap:
    """Verify that exceeding the tool call cap sends a best-effort request."""

    def test_cap_sends_best_effort_request(
        self, sample_adg: ADG, auth_constraint: SymbolicConstraint
    ) -> None:
        """When LLM exceeds tool call cap, a final best-effort request is sent."""
        # Provide exactly TOOL_CALL_CAP tool-call responses (each with 1 tool call),
        # then one best-effort response
        many_responses = []
        for i in range(TOOL_CALL_CAP):
            many_responses.append(
                _make_mock_response(
                    tool_calls=[_tool_call(f"tc{i}", "dive", {"fqn": "app.auth", "depth": 2})],
                )
            )
        # After cap, one more call for the best-effort request
        many_responses.append(
            _make_mock_response(
                content=json.dumps({
                    "subject": "app.api.users.*",
                    "object": "app.auth.middleware.*",
                    "predicate": "prohibits_dependency",
                    "justification": auth_constraint.justification,
                    "adr_id": auth_constraint.adr_id,
                    "adr_path": auth_constraint.adr_path,
                }),
            )
        )

        edges = _run_resolver(auth_constraint, sample_adg, many_responses)
        # The best-effort fallback produces a result from the final LLM call
        assert len(edges) == 1
        assert edges[0].subject == "app.api.users.*"

    def test_cap_best_effort_returns_empty_on_failure(
        self, sample_adg: ADG, auth_constraint: SymbolicConstraint
    ) -> None:
        """If best-effort request returns unparseable content, return empty."""
        from unittest.mock import MagicMock
        many_responses = []
        for i in range(TOOL_CALL_CAP):
            many_responses.append(
                _make_mock_response(
                    tool_calls=[_tool_call(f"tc{i}", "dive", {"fqn": "app.auth", "depth": 2})],
                )
            )
        # Best-effort response is empty/garbage
        many_responses.append(_make_mock_response(content="I cannot resolve this."))

        edges = _run_resolver(auth_constraint, sample_adg, many_responses)
        assert edges == []


# -- Test: best-effort wildcard fallback -------------------------------------

class TestWildcardFallback:
    """Verify that when exact match fails, ancestor + .* wildcard is used."""

    def test_wildcard_fallback_on_partial_match(
        self, sample_adg: ADG
    ) -> None:
        """LLM resolves to a module FQN, which gets .* wildcard appended."""
        constraint = SymbolicConstraint(
            subject="the API module",
            object="auth middleware",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="ADR 002",
            adr_id="ADR-002",
            adr_path="docs/adr/002.md",
        )
        # LLM resolves to module-level FQNs, which should get .* wildcards
        responses = [
            _make_mock_response(
                content=json.dumps({
                    "subject": "app.api",
                    "object": "app.auth.middleware",
                    "predicate": "prohibits_dependency",
                    "justification": "ADR 002",
                    "adr_id": "ADR-002",
                    "adr_path": "docs/adr/002.md",
                }),
            ),
        ]

        edges = _run_resolver(constraint, sample_adg, responses)
        assert len(edges) == 1
        # Module FQNs should have .* appended automatically
        assert edges[0].subject == "app.api.*"
        assert edges[0].object == "app.auth.middleware.*"


# -- Test: external dependency handling --------------------------------------

class TestExternalDependency:
    """Verify external dependencies use EXTERNAL node logic."""

    def test_external_object_creates_external_node(
        self, sample_adg: ADG
    ) -> None:
        """When LLM resolves object to an external package, it should
        produce a ConstraintEdge with the external FQN."""
        constraint = SymbolicConstraint(
            subject="the users API module",
            object="requests library",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            justification="ADR 003: API module requires requests",
            adr_id="ADR-003",
            adr_path="docs/adr/003.md",
        )
        # LLM resolves object to external "requests" package
        responses = [
            _make_mock_response(
                content=json.dumps({
                    "subject": "app.api.users.*",
                    "object": "requests",
                    "predicate": "requires_dependency",
                    "justification": "ADR 003: API module requires requests",
                    "adr_id": "ADR-003",
                    "adr_path": "docs/adr/003.md",
                }),
            ),
        ]

        edges = _run_resolver(constraint, sample_adg, responses)
        assert len(edges) == 1
        assert edges[0].object == "requests"


# -- Test: one session per constraint ----------------------------------------

class TestSessionIsolation:
    """Verify each constraint gets its own LLM session."""

    def test_two_constraints_two_sessions(
        self, sample_adg: ADG
    ) -> None:
        """Two constraints should result in two separate LLM conversations."""
        constraints = [
            SymbolicConstraint(
                subject="API module",
                object="auth module",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                justification="ADR 001",
                adr_id="ADR-001",
                adr_path="docs/adr/001.md",
            ),
            SymbolicConstraint(
                subject="core module",
                object="database module",
                predicate=PredicateType.REQUIRES_DEPENDENCY,
                justification="ADR 002",
                adr_id="ADR-002",
                adr_path="docs/adr/002.md",
            ),
        ]
        # Each constraint gets its own final answer
        responses_per_call = [
            # First constraint session
            [_make_mock_response(content=json.dumps({
                "subject": "app.api.*",
                "object": "app.auth.*",
                "predicate": "prohibits_dependency",
                "justification": "ADR 001",
                "adr_id": "ADR-001",
                "adr_path": "docs/adr/001.md",
            }))],
            # Second constraint session
            [_make_mock_response(content=json.dumps({
                "subject": "app.core.*",
                "object": "app.db.*",
                "predicate": "requires_dependency",
                "justification": "ADR 002",
                "adr_id": "ADR-002",
                "adr_path": "docs/adr/002.md",
            }))],
        ]

        mock_client = MagicMock()
        call_count = 0
        def side_effect(**kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1
            return responses_per_call[idx][0]
        mock_client.chat.completions.create.side_effect = side_effect

        with patch("services.adg.agent_resolver.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
            config = _make_config()
            edges = resolve_agent_constraints(constraints, sample_adg, config)

        assert len(edges) == 2
        assert mock_client.chat.completions.create.call_count == 2


# -- Helpers -----------------------------------------------------------------

def _make_mock_response(content: str | None = None, tool_calls: list[dict] | None = None):
    """Create a mock OpenAI ChatCompletion response."""
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


def _make_config():
    """Create a minimal config for testing."""
    from services.extract.config import LangExtractConfig
    return LangExtractConfig(
        model_id="test-model",
        model_url="https://test.example.com/v1",
        api_key_env="TEST_API_KEY",
        provider="openai",
    )


def _run_resolver(
    constraint: SymbolicConstraint,
    adg: ADG,
    responses: list,
) -> list[ConstraintEdge]:
    """Run resolve_agent_constraints with a mocked OpenAI client."""
    mock_client = MagicMock()
    responses_iter = iter(responses)
    mock_client.chat.completions.create.side_effect = lambda **kwargs: next(responses_iter)

    with patch("services.adg.agent_resolver.OpenAI", return_value=mock_client), \
         patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
        config = _make_config()
        return resolve_agent_constraints([constraint], adg, config)


# -- Test: JSON extraction from LLM responses ------------------------------

class TestExtractJson:
    """Verify _extract_json strips markdown fences and surrounding text."""

    def test_plain_json(self) -> None:
        raw = '{"subject": "app.api.*", "object": "app.db.*"}'
        assert _extract_json(raw) == raw

    def test_markdown_json_fence(self) -> None:
        raw = '```json\n{"subject": "app.api.*", "object": "app.db.*"}\n```'
        assert '"subject"' in _extract_json(raw)
        assert _extract_json(raw) == '{"subject": "app.api.*", "object": "app.db.*"}'

    def test_markdown_plain_fence(self) -> None:
        raw = '```\n{"subject": "app.api.*", "object": "app.db.*"}\n```'
        assert '"subject"' in _extract_json(raw)

    def test_json_with_surrounding_text(self) -> None:
        raw = 'Here is the result:\n{"subject": "app.api.*", "object": "app.db.*"}\nDone.'
        assert '"subject"' in _extract_json(raw)

    def test_fence_with_explanation(self) -> None:
        raw = 'Based on my analysis:\n```json\n{"subject": "app.api.*", "object": "app.db.*"}\n```\nThat resolves it.'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["subject"] == "app.api.*"