"""#142 spike runner: ONE real-LLM ADR-0007 session with node_search reachable
through the dispatch seam. Since #143 the production tool is on the surface by
default, so this runner no longer bolts anything on — it runs the plain
resolver (kept for reproducing the #142 evidence with the landed tool).

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

from services.adg.treesitter import parse_repo
from services.adg.unified_resolver import resolve_adr_constraints
from services.extract.config import LangExtractConfig

from tests.services.adg.test_node_search_spike_142 import (
    ADR_0007_PATH,
    ADR_0007_TEXT,
)

REPO_ROOT = Path(__file__).resolve().parents[3]  # Shepherd/app
SHEPHERD_ROOT = REPO_ROOT.parent  # Shepherd/ (holds .env)
OPENLOBBY_ROOT = Path("/Users/ravichasuksawasdinaayuthaya/UNSW/research/dataset-Shepherd/small/openlobby-server")
if not OPENLOBBY_ROOT.exists():  # portable fallback via repos.yaml resolution
    OPENLOBBY_ROOT = (SHEPHERD_ROOT / "dataset-Shepherd" / "small" / "openlobby-server").resolve()


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(SHEPHERD_ROOT / ".env")

    adg = parse_repo(OPENLOBBY_ROOT)

    trace_dir = os.environ.get("RESOLVER_TRACE_DIR", str(REPO_ROOT / "logs" / "issue-143" / "run1"))
    print(f"trace dir: {trace_dir}", file=sys.stderr)

    config = LangExtractConfig()
    edges = resolve_adr_constraints(
        adr_text=ADR_0007_TEXT,
        adr_id="ADR-0007",
        adr_path=ADR_0007_PATH,
        adg=adg,
        config=config,
        search_backend=__import__("services.adg.search", fromlist=["build_search_backend"]).build_search_backend(OPENLOBBY_ROOT, adg),
    )

    print("\n=== resolved edges (real session, node_search on the surface) ===")
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