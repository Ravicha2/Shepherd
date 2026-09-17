"""#165 record: where HA's post-fix detect() time goes, and how hard the
reverse filter bites. Same seed build as time_ha_detect.py, with the engine's
two structural stages timed separately.

  PYTHONHASHSEED=0 uv run --extra dev python ../benchmark/profile_ha_detect.py
"""
from __future__ import annotations

import time
from pathlib import Path

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.adg.treesitter import parse_repo
from services.models import DiffResult
from services.pipeline import adg_with_specificity

from time_ha_detect import gold_constraints

from services.cpt import engine

HA_ROOT = Path(__file__).resolve().parents[2] / "dataset-Shepherd" / "large" / "home-assistant"


def main() -> None:
    root = HA_ROOT.resolve()
    edges = gold_constraints()
    adg = parse_repo(root)
    seed = adg_with_specificity(
        merge_constraint_edges(add_external_nodes(adg, project_root=root), edges, project_root=root)
    )

    t = time.perf_counter()
    matched = engine.match_constraints(seed)
    print(f"match_constraints_seconds: {time.perf_counter() - t:.2f}", flush=True)

    # filter bite: candidates vs subject matches, per constraint
    adjacency = engine._build_adjacency(seed.edges)
    universe = {str(n.fqn) for n in seed.nodes}
    for mc in matched.values():
        kinds = {"CONTAINS", "IMPORTS", "CALLS", "INHERITS"}
        objects = {str(fqn) for fqn, _ in mc.object_matches}
        t = time.perf_counter()
        candidates = engine._reverse_candidates(adjacency, kinds, objects)
        reverse_seconds = time.perf_counter() - t
        print(
            f"{mc.constraint.adr_id} {mc.constraint.object}: "
            f"subject_matches={len(mc.subject_matches)} candidates={len(candidates)} "
            f"universe={len(universe)} skipped={len(mc.subject_matches) - len(candidates)} "
            f"reverse_seconds={reverse_seconds:.2f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
