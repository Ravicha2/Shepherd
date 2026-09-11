"""#142 spike runner: ONE real-LLM ADR-0007 session with the node_search stub
reachable through the dispatch seam. Bolt-on only (no production change):
_TOOLS + _TOOL_FUNCTIONS are extended at runtime, exactly as the spike tests do.

Usage (from app/):
  uv run --extra dev python -m tests.services.adg.run_node_search_spike_142

Writes:
  - resolved edges (stdout)
  - tool_calls trace with result_fqns -> RESOLVER_TRACE_DIR
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import services.adg.unified_resolver as ur
from services.adg.treesitter import parse_repo
from services.adg.unified_resolver import resolve_adr_constraints
from services.extract.config import LangExtractConfig
from services.models import ADG

from tests.services.adg.test_node_search_spike_142 import (
    ADR_0007_PATH,
    ADR_0007_TEXT,
    node_search_stub,
)

REPO_ROOT = Path(__file__).resolve().parents[3]  # Shepherd/app
SHEPHERD_ROOT = REPO_ROOT.parent  # Shepherd/ (holds .env)
OPENLOBBY_ROOT = Path("/Users/ravichasuksawasdinaayuthaya/UNSW/research/dataset-Shepherd/small/openlobby-server")
if not OPENLOBBY_ROOT.exists():  # portable fallback via repos.yaml resolution
    OPENLOBBY_ROOT = (SHEPHERD_ROOT / "dataset-Shepherd" / "small" / "openlobby-server").resolve()


def build_node_search_surface(adg: ADG):
    tool = {
        "type": "function",
        "function": {
            "name": "node_search",
            "description": (
                "Name/prefix existence check over the codebase graph. Returns "
                "{fqn, kind} entries: kind-labeled ADG nodes (module/class/"
                "function/method) PLUS external import targets (kind "
                "external_import) with no code behind them. Tiers: exact > "
                "prefix > substring, case-insensitive. Capped at 20 with "
                "per-tier counts and a 'narrow' hint on overflow."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Name or dotted prefix, e.g. 'relay', 'graphene', 'openlobby.core.api'"},
                },
                "required": ["query"],
            },
        },
    }
    handler = {
        "node_search": lambda args, adg, backend: json.dumps(node_search_stub(args["query"], adg)),
    }
    return tool, handler


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(SHEPHERD_ROOT / ".env")

    adg = parse_repo(OPENLOBBY_ROOT)
    tool, handler = build_node_search_surface(adg)

    trace_dir = os.environ.get("RESOLVER_TRACE_DIR", str(REPO_ROOT / "logs" / "issue-142" / "spike-run1"))
    print(f"trace dir: {trace_dir}", file=sys.stderr)

    with patch.object(ur, "_TOOLS", list(ur._TOOLS) + [tool]), \
         patch.object(ur, "_TOOL_FUNCTIONS", {**ur._TOOL_FUNCTIONS, **handler}):
        config = LangExtractConfig()
        edges = resolve_adr_constraints(
            adr_text=ADR_0007_TEXT,
            adr_id="ADR-0007",
            adr_path=ADR_0007_PATH,
            adg=adg,
            config=config,
            search_backend=__import__("services.adg.search", fromlist=["build_search_backend"]).build_search_backend(OPENLOBBY_ROOT, adg),
        )

    print("\n=== resolved edges (real session, node_search stub reachable) ===")
    for e in edges:
        print(f"  {e.subject}  {e.predicate.value}  {e.object}")
    if not edges:
        print("  (none)")

    # summarize the trace
    trace_path = Path(trace_dir) / "resolver_traces.jsonl"
    if trace_path.exists():
        last = [json.loads(line) for line in trace_path.read_text().strip().splitlines()][-1]
        print("\n=== tool calls ===")
        for tc in last.get("tool_calls", []):
            print(f"  {tc['name']}({tc['arguments']})")
            for f in tc.get("result_fqns", [])[:12]:
                print(f"     -> {f}")
        print(f"hit_cap={last.get('hit_cap')} parse_failed={last.get('parse_failed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())