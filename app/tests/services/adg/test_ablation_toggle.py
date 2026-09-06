"""Ablation toggle checks for issue #131 (no LLM, no API key).

The ablation arms in test_unified_resolver_eval are env-flag-scoped patches of
the resolver tool surface. These tests pin the toggle mechanism itself: the v2
scrub removes list_dependents from every surface the LLM session sees, the
patch is active only inside the context, and the v1 backend branch selects the
stub only when its flag is set. If the resolver prompt or tool descriptions
change, the scrub asserts here fail loudly instead of silently contaminating
the dependents_off arm.
"""
from __future__ import annotations

import services.adg.unified_resolver as unified_resolver
from tests.services.adg import test_unified_resolver_eval as harness


def test_dependents_off_tools_drop_the_tool_and_every_mention() -> None:
    tools = harness._dependents_off_tools()
    assert len(tools) == 3
    assert all(tool["function"]["name"] != "list_dependents" for tool in tools)
    assert all("list_dependents" not in tool["function"]["description"] for tool in tools)


def test_dependents_off_prompt_template_drops_every_mention() -> None:
    assert "list_dependents" not in harness._dependents_off_prompt_template()


def test_tool_surface_patch_scopes_to_the_context(monkeypatch) -> None:
    monkeypatch.setenv("ABLATION_DEPENDENTS_OFF", "1")
    with harness._ablation_tool_surface():
        assert all(tool["function"]["name"] != "list_dependents" for tool in unified_resolver._TOOLS)
        assert "list_dependents" not in unified_resolver._TOOL_FUNCTIONS
        assert "list_dependents" not in unified_resolver._SYSTEM_PROMPT_TEMPLATE
    assert len(unified_resolver._TOOLS) == 4, "patch did not restore after the context exited"
    assert "list_dependents" in unified_resolver._TOOL_FUNCTIONS
    assert "list_dependents" in unified_resolver._SYSTEM_PROMPT_TEMPLATE


def test_tool_surface_noop_without_the_flag(monkeypatch) -> None:
    monkeypatch.delenv("ABLATION_DEPENDENTS_OFF", raising=False)
    with harness._ablation_tool_surface():
        assert len(unified_resolver._TOOLS) == 4


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
