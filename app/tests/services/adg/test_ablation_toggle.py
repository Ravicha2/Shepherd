"""Ablation toggle + tool-surface pins (no LLM, no API key).

Four concerns:
- #133 regression pin: list_dependents was cut everywhere (0 usage in 33 traced
  baseline sessions, presence degraded openlobby grounding — see #131). The
  name must stay absent from every surface the LLM session sees and from the
  adg_tools library.
- The surviving #131 search_off arm: the backend branch selects the stub only
  when its flag is set.
- #137/#143 neighborhood arms: children_off / node_search_off scrub all five
  surfaces (schema, handler, search description, prompt paragraph, example
  steps), restore after the context exits, and refuse a combined arm. Plus
  the attribution instrument pin: traces carry result_fqns and per-edge
  provenance.
- #143 surface pins: list_dependencies stays absent from every session surface
  (replaced by node_search); node_search present in schema + handler, its
  result_fqns extraction works, and its absence from the prompt's scrub
  targets.
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

import services.adg.adg_tools as adg_tools
import services.adg.unified_resolver as unified_resolver
from tests.services.adg import test_unified_resolver_eval as harness


def test_list_dependents_absent_from_every_surface() -> None:
    names = [tool["function"]["name"] for tool in unified_resolver._TOOLS]
    assert "list_dependents" not in names
    assert all("list_dependents" not in tool["function"]["description"] for tool in unified_resolver._TOOLS)
    assert "list_dependents" not in unified_resolver._TOOL_FUNCTIONS
    assert "list_dependents" not in unified_resolver._SYSTEM_PROMPT_TEMPLATE
    assert not hasattr(adg_tools, "list_dependents")


# -- #143 surface pins ----------------------------------------------------------


def test_list_dependencies_replaced_by_node_search() -> None:
    """#143: list_dependencies is gone from every LLM-visible surface; the
    session surface carries node_search in its place."""
    names = [tool["function"]["name"] for tool in unified_resolver._TOOLS]
    assert "list_dependencies" not in names
    assert "list_dependencies" not in unified_resolver._TOOL_FUNCTIONS
    assert "list_dependencies" not in unified_resolver._SYSTEM_PROMPT_TEMPLATE
    assert "node_search" in names
    assert "node_search" in unified_resolver._TOOL_FUNCTIONS
    assert "node_search" in unified_resolver._SYSTEM_PROMPT_TEMPLATE
    # search_code description steers to node_search
    search_tool = next(t for t in unified_resolver._TOOLS if t["function"]["name"] == "search_code")
    assert "node_search" in search_tool["function"]["description"]
    # no example step or prompt sentence still names the removed tool
    assert "list_dependencies" not in unified_resolver._SYSTEM_PROMPT_TEMPLATE


def test_node_search_schema_declares_imports_target_kinds() -> None:
    """The #142 anchor-bait contract: the schema tells the agent that external
    import targets (kind external_import) are indexed."""
    tool = next(t for t in unified_resolver._TOOLS if t["function"]["name"] == "node_search")
    assert "external_import" in tool["function"]["description"]
    props = tool["function"]["parameters"]["properties"]
    assert "query" in props


def test_prompt_carries_object_side_grounding_rule() -> None:
    """#142 steering condition: the prompt mandates grounding external objects
    on node_search results (pip names are not import paths)."""
    prompt = unified_resolver._SYSTEM_PROMPT_TEMPLATE
    assert "External objects MUST be verified with node_search" in prompt
    assert "pip" in prompt.lower() or "Pip/package" in prompt
    assert "external_import" in prompt


def test_search_backend_branch_selects_the_stub_only_when_flagged(monkeypatch) -> None:
    monkeypatch.setenv("ABLATION_SEARCH_OFF", "1")
    assert harness._select_search_backend("repo_root_unused", "adg_unused") is harness._empty_search_backend

    monkeypatch.delenv("ABLATION_SEARCH_OFF", raising=False)
    sentinel = object()
    monkeypatch.setattr(harness, "build_search_backend", lambda repo_root, adg: sentinel)
    assert harness._select_search_backend("repo_root_unused", "adg_unused") is sentinel


def test_empty_search_backend_matches_the_real_backend_signature() -> None:
    assert harness._empty_search_backend("any query") == []
    assert harness._empty_search_backend("any query", top_k=3) == []


# -- #137 neighborhood arms ----------------------------------------------------


@pytest.mark.parametrize("removed_tool,flag", [
    ("list_children", "ABLATION_CHILDREN_OFF"),
    ("node_search", "ABLATION_NODE_SEARCH_OFF"),
])
def test_scrub_removes_all_five_surfaces(removed_tool, flag, monkeypatch) -> None:
    monkeypatch.setenv(flag, "1")
    tools, handlers, prompt_template = harness._scrubbed_tool_surface(removed_tool)
    assert len(tools) == 2
    assert all(tool["function"]["name"] != removed_tool for tool in tools)
    assert all(removed_tool not in tool["function"]["description"] for tool in tools)
    assert removed_tool not in handlers
    assert removed_tool not in prompt_template
    # the two tools that remain are the untouched ones
    assert {tool["function"]["name"] for tool in tools} == {
        name for name in unified_resolver._TOOL_FUNCTIONS if name != removed_tool
    }


def test_children_scrub_also_deletes_both_example_steps(monkeypatch) -> None:
    monkeypatch.setenv("ABLATION_CHILDREN_OFF", "1")
    _, _, prompt_template = harness._scrubbed_tool_surface("list_children")
    assert 'list_children("app.routes")' not in prompt_template
    assert 'list_children("app.services")' not in prompt_template


def test_node_search_scrub_keeps_example_steps(monkeypatch) -> None:
    """No prompt example names node_search, so the scrub is paragraph-only
    and the children example steps must survive intact."""
    monkeypatch.setenv("ABLATION_NODE_SEARCH_OFF", "1")
    _, _, prompt_template = harness._scrubbed_tool_surface("node_search")
    assert 'list_children("app.routes")' in prompt_template
    assert 'list_children("app.services")' in prompt_template


@pytest.mark.parametrize("removed_tool,flag", [
    ("list_children", "ABLATION_CHILDREN_OFF"),
    ("node_search", "ABLATION_NODE_SEARCH_OFF"),
])
def test_surface_patch_applies_and_restores(removed_tool, flag, monkeypatch) -> None:
    monkeypatch.setenv(flag, "1")
    with harness._neighborhood_tool_surface(removed_tool=removed_tool):
        assert all(tool["function"]["name"] != removed_tool for tool in unified_resolver._TOOLS)
        assert removed_tool not in unified_resolver._TOOL_FUNCTIONS
        assert removed_tool not in unified_resolver._SYSTEM_PROMPT_TEMPLATE
    # patch restores after the context exits
    assert {tool["function"]["name"] for tool in unified_resolver._TOOLS} == {
        "search_code", "list_children", "node_search"
    }
    assert set(unified_resolver._TOOL_FUNCTIONS) == {"search_code", "list_children", "node_search"}
    assert "list_children" in unified_resolver._SYSTEM_PROMPT_TEMPLATE


def test_surface_context_is_noop_without_flags(monkeypatch) -> None:
    monkeypatch.delenv("ABLATION_CHILDREN_OFF", raising=False)
    monkeypatch.delenv("ABLATION_NODE_SEARCH_OFF", raising=False)
    with harness._neighborhood_tool_surface(removed_tool="list_children"):
        assert len(unified_resolver._TOOLS) == 3
        assert "list_children" in unified_resolver._TOOL_FUNCTIONS


def test_combined_arm_refused(monkeypatch) -> None:
    monkeypatch.setenv("ABLATION_CHILDREN_OFF", "1")
    monkeypatch.setenv("ABLATION_NODE_SEARCH_OFF", "1")
    with pytest.raises(RuntimeError, match="one variable per arm"):
        with harness._neighborhood_tool_surface(removed_tool="list_children"):
            pass


def test_ablation_arm_labels_route_flags(monkeypatch) -> None:
    from tests.eval_paths import _ablation_arm

    monkeypatch.delenv("ABLATION_SEARCH_OFF", raising=False)
    monkeypatch.delenv("ABLATION_CHILDREN_OFF", raising=False)
    monkeypatch.delenv("ABLATION_NODE_SEARCH_OFF", raising=False)
    assert _ablation_arm() == "baseline"

    monkeypatch.setenv("ABLATION_CHILDREN_OFF", "1")
    assert _ablation_arm() == "children_off"

    monkeypatch.delenv("ABLATION_CHILDREN_OFF", raising=False)
    monkeypatch.setenv("ABLATION_NODE_SEARCH_OFF", "1")
    assert _ablation_arm() == "node_search_off"


# -- #137 attribution instrument pins ------------------------------------------


def test_extract_result_fqns_shapes() -> None:
    search_payload = json.dumps([{"fqn": "app.api.users", "kind": "module", "file": "f.py", "snippet": "x"}])
    assert unified_resolver._extract_result_fqns("search_code", search_payload) == ["app.api.users"]
    children_payload = json.dumps({"entries": [{"fqn": "app.api.users", "kind": "module"}], "truncated": False})
    assert unified_resolver._extract_result_fqns("list_children", children_payload) == ["app.api.users"]
    node_search_payload = json.dumps({
        "entries": [{"fqn": "graphene.relay", "kind": "external_import"}],
        "truncated": False,
        "counts": {"exact": 0, "prefix": 1, "substring": 0, "relaxed": 0},
    })
    assert unified_resolver._extract_result_fqns("node_search", node_search_payload) == ["graphene.relay"]
    # unknown payloads yield [], never raise
    assert unified_resolver._extract_result_fqns("search_code", json.dumps({"error": "unknown tool: x"})) == []
    assert unified_resolver._extract_result_fqns("search_code", "not json") == []
    # dedup preserves order
    dup_payload = json.dumps([{"fqn": "a.b"}, {"fqn": "a.b"}, {"fqn": "a.c"}])
    assert unified_resolver._extract_result_fqns("search_code", dup_payload) == ["a.b", "a.c"]


def test_covers_prefix_tolerance() -> None:
    assert unified_resolver._covers("app.api.users", "app.api.users.UserView.*") is True
    assert unified_resolver._covers("app.api.users.UserView", "app.api.users") is True
    assert unified_resolver._covers("app", "app.api.*") is True
    assert unified_resolver._covers("app.api", "app.db.*") is False
    assert unified_resolver._covers("app.api", "app.api.*") is True  # X vs X.*
