"""#165 kill criterion: one full-graph detect() on home-assistant after the
reverse-reachability skip-filter. Run from app/:

  PYTHONHASHSEED=0 uv run --extra dev python ../benchmark/time_ha_detect.py

Builds the pin-tree seed from the two HA gold constraints (selenium, gpiozero,
both `homeassistant.components.*` wildcard subjects) and times detect().
"""
from __future__ import annotations

import time
from pathlib import Path

from services.adg.gold import load_gold_edges
from services.adg.treesitter import parse_repo
from services.cpt.engine import detect
from services.models import DiffResult
from services.pipeline import ADGPipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
HA_ROOT = REPO_ROOT.parent / "dataset-Shepherd" / "large" / "home-assistant"
GOLD = REPO_ROOT / "benchmark" / "gold" / "home_assistant_gold.json"


def gold_constraints():
    return load_gold_edges(GOLD)


def main() -> None:
    root = HA_ROOT.resolve()
    edges = gold_constraints()
    print(f"repo: {root}")
    print(f"constraints: {[(e.subject, e.predicate, e.object) for e in edges]}")

    t = time.perf_counter()
    adg = parse_repo(root)
    print(f"parse_seconds: {time.perf_counter() - t:.1f}  nodes={len(adg.nodes)} edges={len(adg.edges)}", flush=True)

    t = time.perf_counter()
    seed = ADGPipeline.build_gold_seed(adg, GOLD, project_root=root)
    print(f"merge_seconds: {time.perf_counter() - t:.1f}  nodes={len(seed.nodes)}", flush=True)

    t = time.perf_counter()
    result = detect(DiffResult(to_sha="baseline"), seed)
    elapsed = time.perf_counter() - t
    print(f"detect_seconds: {elapsed:.1f}  violations={len(result.violations)}", flush=True)
    for v in result.violations:
        print(f"  {v.constraint.adr_id} {v.constraint.predicate} {v.matched_fqn} -> {v.constraint.object}")


if __name__ == "__main__":
    main()
