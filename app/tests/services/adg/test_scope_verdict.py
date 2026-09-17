"""Per-edge scope verdict pins (issue #157; ADR 019).

The resolver emits a `scope` verdict as one more key in the per-edge JSON it
already produces (ADR 019 decision 1): `runtime` | `tooling` | `none`.
`_parse_edges` is the parse seam:

- `runtime` / `tooling` materialize on `ConstraintEdge.scope`;
- `none` emits no edge at all, but is retained as trace residue so a wrong
  `none` (the worst failure: a silently deleted real constraint) stays
  auditable by #158's confusion matrix;
- a missing or invalid `scope` key defaults to `runtime` — loud, never
  silently sheltered in the tooling exclusion (ADR 019 decision 3).

Zero LLM: recorded/constructed response payloads replayed through the parse
path only.
"""
from __future__ import annotations

import json

from services.adg.unified_resolver import _parse_edges
from services.models import ConstraintScope, PredicateType


def _payload(*scopes: object, subject: str = "app.api.*", object_: str = "app.db.*") -> str:
    """One edge per scope value; a sentinel `...` omits the scope key."""
    items = []
    for scope in scopes:
        item = {
            "subject": subject,
            "object": object_,
            "predicate": "prohibits_dependency",
            "justification": "pin fixture",
            "adr_id": "ADR-001",
            "adr_path": "docs/adr/001.md",
        }
        if scope is not ...:
            item["scope"] = scope
        items.append(item)
    return json.dumps(items)


# -- All three verdicts --------------------------------------------------------


def test_runtime_scope_materializes() -> None:
    edges = _parse_edges(_payload("runtime"), "ADR-001", "docs/adr/001.md")
    assert len(edges) == 1
    assert edges[0].scope is ConstraintScope.RUNTIME


def test_tooling_scope_materializes() -> None:
    edges = _parse_edges(_payload("tooling"), "ADR-001", "docs/adr/001.md")
    assert len(edges) == 1
    assert edges[0].scope is ConstraintScope.TOOLING


def test_none_scope_drops_and_records_residue() -> None:
    residue: list[dict] = []
    edges = _parse_edges(_payload("none"), "ADR-001", "docs/adr/001.md", none_verdict_edges=residue)
    assert edges == []
    assert len(residue) == 1
    assert residue[0]["subject"] == "app.api.*"
    assert residue[0]["object"] == "app.db.*"
    assert residue[0]["predicate"] == "prohibits_dependency"
    assert residue[0]["scope"] == "none"


def test_none_dropped_without_collector() -> None:
    """The collector is optional: the edge still drops, no crash."""
    assert _parse_edges(_payload("none"), "ADR-001", "docs/adr/001.md") == []


# -- Missing / invalid key defaults loud to runtime ----------------------------


def test_missing_scope_defaults_to_runtime() -> None:
    edges = _parse_edges(_payload(...), "ADR-001", "docs/adr/001.md")
    assert len(edges) == 1
    assert edges[0].scope is ConstraintScope.RUNTIME


def test_invalid_scope_defaults_to_runtime() -> None:
    edges = _parse_edges(_payload("banana"), "ADR-001", "docs/adr/001.md")
    assert len(edges) == 1
    assert edges[0].scope is ConstraintScope.RUNTIME


# -- Mixed answer: per-edge, not per-ADR ---------------------------------------


def test_mixed_scopes_triage_per_edge() -> None:
    """One session, one ADR: runtime, tooling, and none coexist (the mixed-ADR
    case a whole-ADR verdict cannot represent)."""
    residue: list[dict] = []
    edges = _parse_edges(
        _payload("runtime", "tooling", "none"), "ADR-001", "docs/adr/001.md",
        none_verdict_edges=residue,
    )
    assert [e.scope for e in edges] == [ConstraintScope.RUNTIME, ConstraintScope.TOOLING]
    assert len(residue) == 1


def test_predicate_still_parsed_alongside_scope() -> None:
    edges = _parse_edges(_payload("tooling"), "ADR-001", "docs/adr/001.md")
    assert edges[0].predicate is PredicateType.PROHIBITS_DEPENDENCY


# -- Session seam: scope flows edge -> trace, none leaves residue --------------
#
# Reuses the mocked-OpenAI harness from test_unified_resolver: the LLM is a
# recorded payload, so the session plumbing (scope key -> ConstraintEdge.scope
# -> trace record) is pinned zero-LLM.

from unittest.mock import MagicMock, patch  # noqa: E402

from tests.services.adg.test_unified_resolver import (  # noqa: E402
    ADR_PROHIBIT_DEP,
    _make_config,
    _make_mock_response,
    _stub_backend,
    sample_adg,  # noqa: F401 — re-exported so pytest resolves the fixture here
)


def _run_session(content: str, tmp_path, adg, adr_text: str = ADR_PROHIBIT_DEP):
    from services.adg.unified_resolver import resolve_adr_constraints

    mock_client = MagicMock()
    responses_iter = iter([_make_mock_response(content=content)])
    mock_client.chat.completions.create.side_effect = lambda **kwargs: next(responses_iter)
    with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
         patch.dict("os.environ", {"TEST_API_KEY": "test-key", "RESOLVER_TRACE_DIR": str(tmp_path)}):
        edges = resolve_adr_constraints(
            adr_text, "ADR-001", "docs/adr/001.md", adg, _make_config(), _stub_backend,
        )
    record = json.loads((tmp_path / "resolver_traces.jsonl").read_text().splitlines()[-1])
    return edges, record


def test_session_scope_flows_to_edge_and_trace(tmp_path, sample_adg) -> None:
    edges, record = _run_session(_payload("tooling"), tmp_path, sample_adg)
    assert [e.scope for e in edges] == [ConstraintScope.TOOLING]
    assert record["edges"][0]["scope"] == "tooling"


def test_session_none_verdict_absent_but_trace_residue(tmp_path, sample_adg) -> None:
    residue_edges, record = _run_session(_payload("none"), tmp_path, sample_adg)
    assert residue_edges == []
    assert record["num_edges"] == 0
    assert record["none_verdict_edges"] == [{
        "subject": "app.api.*",
        "object": "app.db.*",
        "predicate": "prohibits_dependency",
        "scope": "none",
    }]


def test_session_trace_carries_empty_none_residue_when_absent(tmp_path, sample_adg) -> None:
    _, record = _run_session(_payload("runtime", "tooling"), tmp_path, sample_adg)
    assert record["none_verdict_edges"] == []


def test_session_per_edge_overrides_whole_adr_tooling_prose(tmp_path, sample_adg) -> None:
    """The mixed-ADR case ADR 019 exists for: ADR prose full of tooling role
    words, but the edge carries `runtime` — the per-edge verdict wins because
    the whole-ADR `classify_adr_scope` regex is gone."""
    tooling_prose = (
        "# ADR: Frontend stack\n\n## Decision\n\n"
        "Keep using Jest for the frontend testing frameworks; run linting and "
        "formatting via the CI pipeline. The UI layer must not depend on graphene.\n"
    )
    edges, record = _run_session(_payload("runtime"), tmp_path, sample_adg, adr_text=tooling_prose)
    assert [e.scope for e in edges] == [ConstraintScope.RUNTIME]
    assert record["edges"][0]["scope"] == "runtime"


def test_session_mixed_verdicts_per_edge(tmp_path, sample_adg) -> None:
    edges, record = _run_session(_payload("runtime", "tooling", "none"), tmp_path, sample_adg)
    assert [e.scope for e in edges] == [ConstraintScope.RUNTIME, ConstraintScope.TOOLING]
    assert [e["scope"] for e in record["edges"]] == ["runtime", "tooling"]
    assert len(record["none_verdict_edges"]) == 1


# -- Prompt surface (ADR 019 decision 5) ---------------------------------------
#
# Role nouns only, no tool names, no copyable FQN literals (the #146 Rule 3
# lesson). The `## Scope verdict` section lands after `## Mandate, not mention`
# and the output-format block names the key.

from services.adg.unified_resolver import _SYSTEM_PROMPT_TEMPLATE  # noqa: E402


def test_prompt_carries_scope_verdict_section() -> None:
    assert "## Scope verdict" in _SYSTEM_PROMPT_TEMPLATE


def test_scope_section_follows_mandate_section() -> None:
    assert _SYSTEM_PROMPT_TEMPLATE.index("## Mandate, not mention") < _SYSTEM_PROMPT_TEMPLATE.index("## Scope verdict")


def _scope_section() -> str:
    section = _SYSTEM_PROMPT_TEMPLATE.split("## Scope verdict", 1)[1].split("## ", 1)[0]
    return " ".join(section.split())


def test_scope_section_names_role_nouns_not_tools() -> None:
    section = _scope_section()
    for role_noun in ("linters", "formatters", "type checkers", "test frameworks", "package managers"):
        assert role_noun in section, role_noun
    # no tool-name literals (would be copyable / vocabulary-overfit bait)
    for tool in ("ruff", "pytest", "pipenv", "black", "jest"):
        assert tool.lower() not in section.lower(), tool


def test_scope_section_states_language_version_is_tooling() -> None:
    assert "language-version" in _scope_section()


def test_scope_section_judges_each_edge_independently() -> None:
    assert "each edge independently" in _scope_section()


def test_output_format_block_names_scope_key_and_default() -> None:
    output_block = _SYSTEM_PROMPT_TEMPLATE.split("## Output format", 1)[1].split("## ", 1)[0]
    assert "scope" in output_block
    assert "runtime" in output_block and "tooling" in output_block and "none" in output_block
