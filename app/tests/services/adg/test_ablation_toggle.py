"""Ablation toggle + tool-surface pins (no LLM, no API key).

Two concerns:
- #133 regression pin: list_dependents was cut everywhere (0 usage in 33 traced
  baseline sessions, presence degraded openlobby grounding — see #131). The
  name must stay absent from every surface the LLM session sees and from the
  adg_tools library.
- The surviving #131 search_off arm: the backend branch selects the stub only
  when its flag is set.
"""
from __future__ import annotations

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
