"""#142 spike, landed as #143 pins: anchor-bait mechanism tests for node_search.

Original question (issue #142): does a name/prefix existence-check surface over ADG
nodes + IMPORTS targets make the resolver pick the right object FQN on the
anchor-bait class (openlobby ADR-0007: codebase imports `graphene.relay`,
gold expects `graphene.relay`, resolver stably emits `graphql_relay` /
`graphene_django` — the pip-name vs import-path confusion)?

Result: mechanism CONFIRMED (spike runs logs/issue-142/spike-run{1,2,3}; the
import path was emitted only in sessions that called the tool and saw it on
the surface, 5/5 in the MUST-verify arm). #143 landed the production tool, so
these tests now pin the REAL tool (services.adg.adg_tools.node_search) instead
of the throwaway stub:

- The surface itself: exact/prefix/substring tiers, kind labels (external_import
  for IMPORTS targets), cap + refusal shape (TestNodeSearch covers the unit
  shape in test_adg_tools.py; these cover the anchor-bait fixtures).
- The causal link: the emulated resolver's emission is a decision rule applied
  to the REAL tool result; strip IMPORTS targets and the emission falls back to
  the pip-name miss.
- The negative control: search_code's lift returns ADG nodes only, so the
  dotted import path was never on any pre-#143 surface.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.adg.adg_tools import node_search
from services.fqn import FQN
from services.models import ADG, ConstraintEdge, Edge, FQNKind, FQNNode, PredicateType
from services.adg.unified_resolver import (
    _ENTRY_POINT_ROOTS,
    _extract_result_fqns,
    _root_segments,
    resolve_adr_constraints,
)
from services.extract.config import LangExtractConfig


REPO_ROOT = Path(__file__).resolve().parents[4]
OPENLOBBY_ROOT = REPO_ROOT / "repos" / ".." / ".." / "dataset-Shepherd" / "small" / "openlobby-server"

ADR_0007_PATH = "docs/architecture/decisions/0007-adopt-graphql-relay-specification.md"

# The openlobby ADR-0007 text (verbatim from the fixture repo).
ADR_0007_TEXT = """\
# 7. Adopt GraphQL Relay specification

Date: 2017-11-11

## Status

Accepted

## Context

We need to make API friendly for clients and design pagination.

## Decision

We will adopt GraphQL Relay specification. It solves pagination so we don't
have to reinvent a wheel. It has handy Node interface for re-fetching objects.
It has a way to define inputs in mutations.

Graphene lib has good support for creating API following Relay specifications.

## Consequences

* It will be easy to write SPA in JavaScript because it has Relay client lib.
* It may require some extra work to fulfill Relay specification.
"""


# -- The production tool under test ----------------------------------------------


def node_search_stub(query: str, adg: ADG, cap: int = 20) -> dict:
    """Back-compat alias: the spike's stub name now calls the production tool.

    The #142 spike validated the mechanism with a throwaway stub
    (capped at 20); #143 landed it as services.adg.adg_tools.node_search with
    the same tiered shape. The mechanism tests below run against the real
    tool via this alias, so the causal pins keep their names."""
    return node_search(query, adg, cap=cap)


# -- Stub ADG: the anchor-bait microcosm ----------------------------------------

def spike_adg() -> ADG:
    """Minimal ADG carrying the anchor-bait shape: internal openlobby.core.api
    modules, a graphene.relay IMPORTS target (the codebase's real import path),
    a graphql_relay IMPORTS target (the pip-name decoy actually imported in
    mutations.py), and a graphene_django IMPORTS target (the other stable
    baseline emission). Plus a setup root to exercise entry-point filtering."""
    nodes = [
        FQNNode(fqn=FQN.from_dotted("openlobby"), kind=FQNKind.MODULE, file_path="openlobby/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core"), kind=FQNKind.MODULE, file_path="openlobby/core/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api"), kind=FQNKind.MODULE, file_path="openlobby/core/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api.paginator"), kind=FQNKind.MODULE, file_path="openlobby/core/api/paginator.py", line_start=0, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api.types"), kind=FQNKind.MODULE, file_path="openlobby/core/api/types.py", line_start=0, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api.types.Author"), kind=FQNKind.CLASS, file_path="openlobby/core/api/types.py", line_start=5, line_end=35, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api.mutations"), kind=FQNKind.MODULE, file_path="openlobby/core/api/mutations.py", line_start=0, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("openlobby.core.api.mutations.Login"), kind=FQNKind.CLASS, file_path="openlobby/core/api/mutations.py", line_start=5, line_end=35, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("setup"), kind=FQNKind.MODULE, file_path="setup.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="openlobby", target="openlobby.core", kind="CONTAINS"),
        Edge(source="openlobby.core", target="openlobby.core.api", kind="CONTAINS"),
        Edge(source="openlobby.core.api", target="openlobby.core.api.paginator", kind="CONTAINS"),
        Edge(source="openlobby.core.api", target="openlobby.core.api.types", kind="CONTAINS"),
        Edge(source="openlobby.core.api.types", target="openlobby.core.api.types.Author", kind="CONTAINS"),
        Edge(source="openlobby.core.api", target="openlobby.core.api.mutations", kind="CONTAINS"),
        Edge(source="openlobby.core.api.mutations", target="openlobby.core.api.mutations.Login", kind="CONTAINS"),
        # the real import edges from openlobby/core/api/{paginator,types,mutations}.py
        Edge(source="openlobby.core.api.paginator", target="graphene.relay", kind="IMPORTS"),
        Edge(source="openlobby.core.api.types", target="graphene", kind="IMPORTS"),
        Edge(source="openlobby.core.api.types", target="graphene.relay", kind="IMPORTS"),
        Edge(source="openlobby.core.api.mutations", target="graphql_relay", kind="IMPORTS"),
        Edge(source="setup", target="graphene_django", kind="IMPORTS"),
    ]
    return ADG(nodes=nodes, edges=edges)


# -- Mocked session helpers (established pattern) --------------------------------

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


def _run_session(
    adg: ADG,
    responses: list,
    extra_tool_handlers: dict[str, callable] | None = None,
    extra_tools: list[dict] | None = None,
):
    """Mocked session with the stub tool bolted onto the dispatch surface.

    Returns (edges, captured_tool_results): the tool message contents the LLM
    actually saw, so the spike asserts on the real stub payload, not the script.
    """
    import services.adg.unified_resolver as ur

    handlers = dict(ur._TOOL_FUNCTIONS)
    tools = list(ur._TOOLS)
    if extra_tool_handlers:
        handlers.update(extra_tool_handlers)
    if extra_tools:
        tools = tools + extra_tools

    mock_client = MagicMock()
    responses_iter = iter(responses)
    mock_client.chat.completions.create.side_effect = lambda **kwargs: next(responses_iter)

    captured: list = []
    real_create = mock_client.chat.completions.create.side_effect

    def _capture_and_dispatch(**kwargs):
        captured.append([dict(m) for m in kwargs.get("messages", [])])
        return real_create(**kwargs)

    mock_client.chat.completions.create.side_effect = _capture_and_dispatch

    with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
         patch.dict("os.environ", {"TEST_API_KEY": "test-key"}), \
         patch.object(ur, "_TOOLS", tools), \
         patch.object(ur, "_TOOL_FUNCTIONS", handlers):
        config = _make_config()
        edges = resolve_adr_constraints(
            ADR_0007_TEXT, "ADR-0007", ADR_0007_PATH, adg, config,
            search_backend=lambda query, top_k=10: [],
        )
    tool_payloads = [
        m["content"]
        for messages in captured
        for m in messages
        if m.get("role") == "tool"
    ]
    return edges, tool_payloads


def _tool_results_from_messages(captured) -> list[str]:
    return [
        m["content"]
        for messages in captured
        for m in messages
        if m.get("role") == "tool"
    ]


# -- The decision rule: what the stub surface makes the resolver emit -----------

DECISION_RULE_NOTE = (
    "Emulated agent policy (the mechanism under test): pick the object FQN "
    "from the node_search surface. If the surface shows a dotted import-path "
    "hit under a package the ADR's prose names (graphene.relay), emit it; "
    "pip-name decoys (graphql_relay, graphene_django) rank below the "
    "import-path form. This mirrors how the prompt's grounding rule "
    "(FQNs MUST come from tool results) would steer a real agent."
)


def _emit_from_surface(surface_payload: str) -> list[dict]:
    """The emulated resolver's decision rule, applied to the REAL stub result.

    Returns the constraint objects the session emits given what the tool
    actually returned. This is the causal link the spike tests: change the
    surface, and the emission follows.
    """
    payload = json.loads(surface_payload)
    entries = [e["fqn"] for e in payload.get("entries", [])]
    # The ADR names Graphene and the Relay specification. The codebase's
    # import path for Relay is `graphene.relay` (from graphene import relay /
    # from graphene.relay import PageInfo). If the surface exposes that
    # dotted import-path target, the emulated resolver grounds on it.
    if "graphene.relay" in entries:
        object_fqn = "graphene.relay"
    elif "graphene" in entries:
        object_fqn = "graphene"
    elif "graphql_relay" in entries:
        object_fqn = "graphql_relay"  # the anchor-bait miss, reproduced
    else:
        object_fqn = "graphql_relay"  # ungrounded fallback = baseline behavior
    return [{
        "subject": "openlobby.core.api.*",
        "object": object_fqn,
        "predicate": "requires_dependency",
        "justification": "ADR-0007 adopts GraphQL Relay specification via Graphene",
        "adr_id": "ADR-0007",
        "adr_path": ADR_0007_PATH,
    }]


# -- Tests -----------------------------------------------------------------------

class TestNodeSearchStub:
    """Stub exists: nodes + IMPORTS targets, prefix match, kind-labeled, capped."""

    def setup_method(self):
        self.adg = spike_adg()

    def test_exact_match_on_internal_node(self):
        result = node_search_stub("openlobby.core.api.types.Author", self.adg)
        assert result["entries"][0] == {"fqn": "openlobby.core.api.types.Author", "kind": "class"}
        assert result["counts"]["exact"] == 1

    def test_prefix_match_surfaces_descendants(self):
        result = node_search_stub("openlobby.core.api.pag", self.adg)
        fqns = [e["fqn"] for e in result["entries"]]
        assert "openlobby.core.api.paginator" in fqns

    def test_dotted_prefix_tier(self):
        result = node_search_stub("openlobby.core.api", self.adg)
        fqns = [e["fqn"] for e in result["entries"]]
        assert "openlobby.core.api.paginator" in fqns
        assert "openlobby.core.api.types" in fqns
        assert "openlobby.core.api.mutations" in fqns

    def test_imports_targets_included_and_kind_labeled_external(self):
        result = node_search_stub("graphene", self.adg)
        by_fqn = {e["fqn"]: e["kind"] for e in result["entries"]}
        # the dotted import path AND the bare package both surface
        assert by_fqn.get("graphene.relay") == "external_import"
        assert by_fqn.get("graphene") == "external_import"
        # pip-name decoys also surface (labeled, so the agent can tell them apart)
        result2 = node_search_stub("graphql", self.adg)
        by_fqn2 = {e["fqn"]: e["kind"] for e in result2["entries"]}
        assert by_fqn2.get("graphql_relay") == "external_import"
        # setup.py's graphene_django import is an IMPORTS target too
        result3 = node_search_stub("graphene_django", self.adg)
        assert any(e["fqn"] == "graphene_django" for e in result3["entries"])

    def test_substring_tier(self):
        result = node_search_stub("relay", self.adg)
        fqns = [e["fqn"] for e in result["entries"]]
        assert "graphene.relay" in fqns
        assert "graphql_relay" in fqns

    def test_no_match_note(self):
        result = node_search_stub("left_pad", self.adg)
        assert result["entries"] == []
        # the real tool adds the relaxed tier to the counts shape
        assert result["counts"] == {"exact": 0, "prefix": 0, "substring": 0, "relaxed": 0}
        assert result.get("note") == "no match"

    def test_cap_and_overbroad_refusal(self):
        result = node_search_stub("o", self.adg, cap=3)
        # 'o' substring-matches openlobby.* family (8 nodes) > cap 3 with no exact/prefix tier
        assert result["truncated"] is True
        assert len(result["entries"]) <= 3

    def test_entry_point_root_nodes_still_indexed_here(self):
        # The stub indexes ADG nodes verbatim; entry-point filtering is the
        # resolver's search_code lift concern (#135), not node_search's.
        result = node_search_stub("setup", self.adg)
        assert any(e["fqn"] == "setup" for e in result["entries"])


class TestStubReachableInSession:
    """Mocked ADR-0007 session with the stub reachable through _dispatch_tool."""

    def setup_method(self):
        self.adg = spike_adg()
        self.node_search_tool = {
            "type": "function",
            "function": {
                "name": "node_search",
                "description": "Name/prefix existence check over ADG nodes and import targets.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
        self.handler = {
            "node_search": lambda args, adg, backend: json.dumps(node_search_stub(args["query"], adg)),
        }

    def test_stub_result_reaches_llm_as_tool_message(self):
        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "node_search", {"query": "relay"})]),
            _make_mock_response(content="[]"),
        ]
        edges, tool_payloads = _run_session(
            self.adg, responses,
            extra_tool_handlers=self.handler,
            extra_tools=[self.node_search_tool],
        )
        assert edges == []
        assert len(tool_payloads) == 1
        payload = json.loads(tool_payloads[0])
        fqns = [e["fqn"] for e in payload["entries"]]
        # THE SURFACE: both the import path and the pip-name decoy are visible
        assert "graphene.relay" in fqns
        assert "graphql_relay" in fqns
        kinds = {e["fqn"]: e["kind"] for e in payload["entries"]}
        assert kinds["graphene.relay"] == "external_import"
        assert kinds["graphql_relay"] == "external_import"

    def test_result_fqns_extraction_supports_new_payload(self):
        """Provenance integration: _extract_result_fqns must read the stub's
        {entries: [...]} shape so #137 attribution works for node_search."""
        payload = json.dumps(node_search_stub("relay", self.adg))
        fqns = _extract_result_fqns("node_search", payload)
        assert "graphene.relay" in fqns
        assert "graphql_relay" in fqns

    def test_overbroad_query_refusal_reaches_llm(self):
        # handler with a small cap so the prefix tier (8 openlobby.* nodes)
        # exceeds it: the refusal shape, never the repo dump
        capped_handler = {
            "node_search": lambda args, adg, backend: json.dumps(node_search_stub(args["query"], adg, cap=3)),
        }
        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "node_search", {"query": "o"})]),
            _make_mock_response(content="[]"),
        ]
        _, tool_payloads = _run_session(
            self.adg, responses,
            extra_tool_handlers=capped_handler,
            extra_tools=[self.node_search_tool],
        )
        payload = json.loads(tool_payloads[0])
        assert payload["truncated"] is True
        assert "narrow" in payload["note"]


class TestMechanism:
    """The causal check: with the stub present, does the session emit
    graphene.relay (mechanism holds) or still graphql_relay (mechanism fails)?"""

    def setup_method(self):
        self.adg = spike_adg()
        self.node_search_tool = {
            "type": "function",
            "function": {
                "name": "node_search",
                "description": "Name/prefix existence check over ADG nodes and import targets.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
        self.handler = {
            "node_search": lambda args, adg, backend: json.dumps(node_search_stub(args["query"], adg)),
        }

    def _session_with_surface_driven_emission(self):
        """Scripted session whose final emission is COMPUTED from the real stub
        result: turn 1 calls node_search; turn 2 applies the emulated agent's
        decision rule to whatever the stub actually returned."""
        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "node_search", {"query": "relay"})]),
        ]
        # two-step: run turn 1, read the real tool result, script turn 2
        mock_client = MagicMock()
        step1 = iter(responses)
        mock_client.chat.completions.create.side_effect = lambda **kwargs: next(step1)

        import services.adg.unified_resolver as ur
        with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}), \
             patch.object(ur, "_TOOL_FUNCTIONS", {**ur._TOOL_FUNCTIONS, **self.handler}), \
             patch.object(ur, "_TOOLS", list(ur._TOOLS) + [self.node_search_tool]):
            from services.adg.unified_resolver import _dispatch_tool
            surface = _dispatch_tool("node_search", {"query": "relay"}, self.adg, backend=None)

        final_edges = _emit_from_surface(surface)
        responses_final = [_make_mock_response(content=json.dumps(final_edges))]
        step2 = iter(responses_final)
        mock_client.chat.completions.create.side_effect = lambda **kwargs: next(step2)

        with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}), \
             patch.object(ur, "_TOOLS", list(ur._TOOLS) + [self.node_search_tool]), \
             patch.object(ur, "_TOOL_FUNCTIONS", {**ur._TOOL_FUNCTIONS, **self.handler}):
            config = _make_config()
            edges = resolve_adr_constraints(
                ADR_0007_TEXT, "ADR-0007", ADR_0007_PATH, self.adg, config,
                search_backend=lambda query, top_k=10: [],
            )
        return edges, surface

    def test_mechanism_holds_surface_makes_resolver_pick_graphene_relay(self):
        edges, surface = self._session_with_surface_driven_emission()
        payload = json.loads(surface)
        fqns = [e["fqn"] for e in payload["entries"]]
        assert "graphene.relay" in fqns, f"surface must show the import path: {fqns}"
        assert len(edges) == 1
        assert edges[0].object == "graphene.relay", (
            f"mechanism result: emitted object={edges[0].object!r} "
            f"(gold=graphene.relay, baseline miss=graphql_relay)"
        )
        assert edges[0].predicate == PredicateType.REQUIRES_DEPENDENCY
        assert edges[0].subject == "openlobby.core.api.*"

    def test_negative_control_without_surface_reproduces_baseline_miss(self):
        """Without the stub (the #140 negative control: ADR-0007 missed in all
        5 arms), the emulated agent with search-only access sees no
        graphene.relay surface and reproduces the graphql_relay miss."""
        # the search-only backend the 5 arms had: semble over the repo lifts
        # code FQNs, never import-target FQNs — stubbed here as empty to model
        # the strongest form: no tool shows the dotted import path
        responses = [
            _make_mock_response(content=json.dumps([{
                "subject": "openlobby.core.api.*",
                "object": "graphql_relay",
                "predicate": "requires_dependency",
                "justification": "ADR-0007 adopts Relay (pip-name guess, no surface)",
                "adr_id": "ADR-0007",
                "adr_path": ADR_0007_PATH,
            }])),
        ]
        edges, tool_payloads = _run_session(self.adg, responses)
        assert len(edges) == 1
        assert edges[0].object == "graphql_relay"
        assert tool_payloads == []  # no tool was called: the 5-arm signature

    def test_surface_counterfactual_decoy_only_reproduces_miss(self):
        """Counterfactual: a surface WITHOUT external-IMPORTS indexing (today's
        search_code analog, nodes only) hides graphene.relay, and the emulated
        resolver falls back to the pip-name miss. This isolates the indexing
        decision as the load-bearing part of the mechanism."""
        nodes_only_handler = {
            "node_search": lambda args, adg, backend: json.dumps(
                {**node_search_stub(args["query"], adg),
                 # strip import-target hits: the counterfactual surface
                 "entries": [e for e in node_search_stub(args["query"], adg)["entries"] if e["kind"] != "external_import"]}
            ),
        }
        responses = [
            _make_mock_response(tool_calls=[_tool_call("tc1", "node_search", {"query": "relay"})]),
        ]
        mock_client = MagicMock()
        step1 = iter(responses)
        mock_client.chat.completions.create.side_effect = lambda **kwargs: next(step1)

        import services.adg.unified_resolver as ur
        with patch("services.adg.unified_resolver.OpenAI", return_value=mock_client), \
             patch.dict("os.environ", {"TEST_API_KEY": "test-key"}), \
             patch.object(ur, "_TOOL_FUNCTIONS", {**ur._TOOL_FUNCTIONS, **nodes_only_handler}):
            from services.adg.unified_resolver import _dispatch_tool
            surface = _dispatch_tool("node_search", {"query": "relay"}, self.adg, backend=None)

        final_edges = _emit_from_surface(surface)
        assert final_edges[0]["object"] == "graphql_relay", (
            "counterfactual: without IMPORTS targets on the surface the "
            "emulated resolver emits the pip-name miss"
        )


# -- Real-ADG verification (the fixture the 5 #140 arms actually ran on) ---------

def _openlobby_adg() -> ADG:
    from services.adg.treesitter import parse_repo
    repo_root = Path("/Users/ravichasuksawasdinaayuthaya/UNSW/research/dataset-Shepherd/small/openlobby-server")
    if not repo_root.exists():
        pytest.skip("openlobby fixture repo not present")
    return parse_repo(repo_root)


class TestRealOpenlobbyADG:
    """The stub against the ADG the #140 arms actually ran on: the surface
    must expose the gold object (graphene.relay) AND the decoys, and the
    emulated decision rule applied to this real surface emits graphene.relay."""

    def setup_method(self):
        self.adg = _openlobby_adg()

    def test_surface_shows_gold_object_and_decoys_on_relay_query(self):
        result = node_search_stub("relay", self.adg)
        by_fqn = {e["fqn"]: e["kind"] for e in result["entries"]}
        # gold object: the dotted import path the codebase actually imports
        assert by_fqn.get("graphene.relay") == "external_import"
        # the anchor-bait decoy the resolver stably emitted across all 5 arms
        assert by_fqn.get("graphql_relay") == "external_import"

    def test_surface_shows_pip_name_variant_on_substring_query(self):
        # graphene_django (the other stable baseline emission) is an IMPORTS
        # target only via setup.py's views import (graphene_django.views), so
        # its root form surfaces on its own query
        result = node_search_stub("graphene_django", self.adg)
        by_fqn = {e["fqn"]: e["kind"] for e in result["entries"]}
        assert "graphene_django.views" in by_fqn
        assert by_fqn.get("graphene_django.views") == "external_import"

    def test_surface_shows_gold_object_on_graphene_query(self):
        result = node_search_stub("graphene", self.adg)
        by_fqn = {e["fqn"]: e["kind"] for e in result["entries"]}
        assert by_fqn.get("graphene.relay") == "external_import"
        assert by_fqn.get("graphene") == "external_import"

    def test_emulated_rule_on_real_surface_emits_gold_object(self):
        surface = json.dumps(node_search_stub("relay", self.adg))
        emitted = _emit_from_surface(surface)
        assert emitted[0]["object"] == "graphene.relay"

    def test_search_code_surface_cannot_show_the_import_path(self):
        """Negative control, made explicit: the semble search lift only ever
        returns ADG NODES (file-chunk lift), so no search_code result can
        contain graphene.relay — the without-tool behavior across all 5 arms."""
        from services.adg.unified_resolver import _external_packages, _root_segments
        targets = {e.target for e in self.adg.edges if e.kind == "IMPORTS"}
        node_fqns = {str(n.fqn) for n in self.adg.nodes}
        assert "graphene.relay" in targets
        assert "graphene.relay" not in node_fqns
        # and the prompt's External packages list shows only the pip-root form
        assert "graphene" in _external_packages(self.adg)
        assert "graphene.relay" not in _external_packages(self.adg)

    def test_entry_point_roots_excluded_from_stub_candidates(self):
        """Spike stub applied to the real ADG mirrors the #135 narrowing: the
        entry-point roots (manage/setup) are search-lift concerns, but the stub
        indexes ADG nodes verbatim — pinned so the difference stays visible."""
        roots = _root_segments(self.adg) - _ENTRY_POINT_ROOTS
        assert roots == {"openlobby"}