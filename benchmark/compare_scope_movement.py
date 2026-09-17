#!/usr/bin/env python3
"""#158 axis 1: FP/quality movement of the post-#157 resolver vs a baseline batch.

Reads two benchmark-arms report dirs and prints, per repo:
- ingestion FP with the zero-gold / has-gold ADR split (an FP on a gold-bearing
  ADR is a different failure from an FP on a zero-constraint ADR)
- excluded_tooling_edges (the tooling tag's accounting surface, #136 seam)
- #154 violation-level detection columns plus the pattern-equality bridge
- detection fires per ADR, diffed baseline -> new, so a named fire family
  (flowkit ADR-0010 airflow, ADR-0012 Scope) can be read off directly

Usage (repo root):
  python3 benchmark/compare_scope_movement.py <baseline_dir> <new_dir> [--runs 1,2]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = REPO_ROOT / "benchmark" / "gold"
REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python"]


def gold_adrs(repo_id: str) -> set[str]:
    rows = json.loads((GOLD_DIR / f"{repo_id.replace('-', '_')}_gold.json").read_text())
    return {r["adr_id"] for r in rows if r["constraints"]}


def load(report_dir: Path) -> dict[str, dict[int, dict]]:
    cells: dict[str, dict[int, dict]] = defaultdict(dict)
    for path in sorted(Path(report_dir).glob("*_run*.json")):
        if path.name.startswith("_"):  # the dir's own reading artifacts
            continue
        r = json.loads(path.read_text())
        cells[r["repo_id"]][r["run_index"]] = r
    return cells


def fp_split(report: dict, repo_id: str) -> dict[str, int]:
    with_gold = gold_adrs(repo_id)
    split = Counter()
    for fp in report["ingestion"]["false_positive_edges"]:
        split["has_gold" if fp["adr_id"] in with_gold else "zero_gold"] += 1
    return dict(split)


def fires_by_adr(report: dict) -> Counter:
    counts: Counter = Counter()
    for case in report["detection"]["cases"]:
        for kind, fires in case["fires"].items():
            for fire in fires:
                counts[(fire["adr_id"], fire["predicate"], fire["object"])] += 1
    return counts


def _det(report: dict) -> str:
    d = report["detection"]
    return (f"{d['exact']}/{d['partial']}/{d['miss']} "
            f"(pattern {d.get('pattern_exact',0)}/{d.get('pattern_partial',0)}/{d.get('pattern_miss',0)}, "
            f"overlap {d.get('diagnostic_overlap',0)}, stale {d.get('stale_gold_units',0)})")


def main(baseline_dir: Path, new_dir: Path, runs: list[int]) -> None:
    base, new = load(baseline_dir), load(new_dir)
    print(f"# FP / quality movement vs `{baseline_dir.name}`\n")
    print("| repo | run | ing e/p/m | FP | zero-gold FP | has-gold FP | excl. tooling | class A/B-C matched,FP | detection violation e/p/m |")
    print("|---|---|---|---|---|---|---|---|---|")
    for repo in REPOS:
        for run_index in sorted(base.get(repo, {})):
            b = base[repo][run_index]
            s = fp_split(b, repo)
            ing = b["ingestion"]
            print(f"| {repo} | base r{run_index} | {ing['exact']}/{ing['partial']}/{ing['miss']} | "
                  f"{ing['false_positives']} | {s.get('zero_gold',0)} | {s.get('has_gold',0)} | "
                  f"{len(ing.get('excluded_tooling_edges',[]))} | "
                  f"A {ing['class_split'].get('A',{}).get('matched',0)},{ing['class_split'].get('A',{}).get('false_positive_edges',0)} "
                  f"B/C {ing['class_split'].get('B/C',{}).get('matched',0)},{ing['class_split'].get('B/C',{}).get('false_positive_edges',0)} | "
                  f"{_det(b)} |")
        for run_index in sorted(new.get(repo, {})):
            if runs and run_index not in runs:
                continue
            n = new[repo][run_index]
            s = fp_split(n, repo)
            ing = n["ingestion"]
            print(f"| {repo} | **new r{run_index}** | {ing['exact']}/{ing['partial']}/{ing['miss']} | "
                  f"{ing['false_positives']} | {s.get('zero_gold',0)} | {s.get('has_gold',0)} | "
                  f"{len(ing.get('excluded_tooling_edges',[]))} | "
                  f"A {ing['class_split'].get('A',{}).get('matched',0)},{ing['class_split'].get('A',{}).get('false_positive_edges',0)} "
                  f"B/C {ing['class_split'].get('B/C',{}).get('matched',0)},{ing['class_split'].get('B/C',{}).get('false_positive_edges',0)} | "
                  f"{_det(n)} |")

    print("\n## detection fires per (adr, predicate, object), baseline -> new\n")
    for repo in REPOS:
        if repo not in base or repo not in new:
            continue
        b = Counter()
        n = Counter()
        for report in base[repo].values():
            b += fires_by_adr(report)
        for run_index, report in new[repo].items():
            if runs and run_index not in runs:
                continue
            n += fires_by_adr(report)
        keys = {k for k in set(b) | set(n) if b.get(k, 0) != n.get(k, 0)}
        if not keys:
            print(f"- {repo}: no per-ADR fire movement")
            continue
        print(f"\n**{repo}**\n")
        print("| adr | predicate | object | base fires | new fires |")
        print("|---|---|---|---|---|")
        for key in sorted(keys, key=lambda k: -(b.get(k, 0) + n.get(k, 0)))[:40]:
            print(f"| {key[0]} | {key[1]} | {key[2]} | {b.get(key,0)} | {n.get(key,0)} |")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    wanted = []
    if "--runs" in sys.argv:
        wanted = [int(x) for x in sys.argv[sys.argv.index("--runs") + 1].split(",")]
    main(Path(args[0]), Path(args[1]), wanted)
