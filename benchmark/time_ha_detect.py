"""#165 kill criterion: one full-graph detect() on home-assistant after the
reverse-reachability skip-filter. Run from app/:

  PYTHONHASHSEED=0 uv run --extra dev python ../benchmark/time_ha_detect.py

Builds the pin-tree seed from the two HA gold constraints (selenium, gpiozero,
both `homeassistant.components.*` wildcard subjects) and times detect().
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.adg.treesitter import parse_repo
from services.cpt.engine import detect
from services.models import ConstraintEdge, DiffResult, PredicateType
from services.pipeline import adg_with_specificity

REPO_ROOT = Path(__file__).resolve().parents[1]
HA_ROOT = REPO_ROOT.parent / "dataset-Shepherd" / "large" / "home-assistant"
GOLD = REPO_ROOT / "benchmark" / "gold" / "home_assistant_gold.json"


def gold_constraints() -> list[ConstraintEdge]:
    gold = json.loads(GOLD.read_text())
    edges: list[ConstraintEdge] = []
    for adr in gold:
        for c in adr["constraints"]:
            edges.append(ConstraintEdge(
                subject=c["subject"], predicate=PredicateType(c["predicate"]),
                object=c["object"], justification=c["justification"],
                adr_id=adr["adr_id"], adr_path=adr["adr_path"],
            ))
    return edges


def main() -> None:
    root = HA_ROOT.resolve()
    edges = gold_constraints()
    print(f"repo: {root}")
    print(f"constraints: {[(e.subject, e.predicate, e.object) for e in edges]}")

    t = time.perf_counter()
    adg = parse_repo(root)
    print(f"parse_seconds: {time.perf_counter() - t:.1f}  nodes={len(adg.nodes)} edges={len(adg.edges)}", flush=True)

    t = time.perf_counter()
    merged = merge_constraint_edges(add_external_nodes(adg, project_root=root), edges, project_root=root)
    seed = adg_with_specificity(merged)
    print(f"merge_seconds: {time.perf_counter() - t:.1f}  nodes={len(seed.nodes)}", flush=True)

    t = time.perf_counter()
    result = detect(DiffResult(to_sha="baseline"), seed)
    elapsed = time.perf_counter() - t
    print(f"detect_seconds: {elapsed:.1f}  violations={len(result.violations)}", flush=True)
    for v in result.violations:
        print(f"  {v.constraint.adr_id} {v.constraint.predicate} {v.matched_fqn} -> {v.constraint.object}")


if __name__ == "__main__":
    main()
