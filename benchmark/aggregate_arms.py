#!/usr/bin/env python3
"""Aggregate #149 benchmark-arms cell reports into the pre-registered reading.

Reads every <repo>_<arm>_run<k>.json in a report dir and applies the rules
registered on #149 (issuecomment 5679974749):
- per repo, per arm, per run table (never one system-wide number)
- noise floor: max run-to-run |delta| within node_on's k runs, per repo per metric
- effect rule: |delta of arm means| > floor AND direction in >= 2 of 3 paired
  run comparisons (node_on run i vs node_off run i)
- decision routing: KEEP if node_on carries gold-matching load beyond floor;
  CUT candidate only if node_on <= node_off everywhere beyond floor AND adds
  FP mass beyond floor; else no-movement -> prompt/validation work (#146)

Usage: python3 benchmark/aggregate_arms.py <report_dir>   (from repo root)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python"]


def _metrics(report: dict) -> dict[str, float]:
    ing, det = report["ingestion"], report["detection"]
    flat = {
        "ing_exact": ing["exact"], "ing_partial": ing["partial"], "ing_miss": ing["miss"],
        "ing_fp": ing["false_positives"],
        "cls_A_matched": ing["class_split"].get("A", {}).get("matched", 0),
        "cls_A_fp": ing["class_split"].get("A", {}).get("false_positive_edges", 0),
        "cls_BC_matched": ing["class_split"].get("B/C", {}).get("matched", 0),
        "cls_BC_fp": ing["class_split"].get("B/C", {}).get("false_positive_edges", 0),
        "det_exact": det["exact"], "det_partial": det["partial"], "det_miss": det["miss"],
        "fires_structural": det["structural"], "fires_merge_mech": det["merge_mechanism"],
        "fires_arm_candidates": det["arm_candidates"],
    }
    return flat


def load_cells(report_dir: Path) -> dict:
    cells: dict[str, dict[int, dict[str, dict[str, float]]]] = defaultdict(dict)
    for path in sorted(report_dir.glob("*_run*.json")):
        report = json.loads(path.read_text())
        cells[report["repo_id"]].setdefault(report["arm"], {})[report["run_index"]] = _metrics(report)
    return cells


def aggregate(report_dir: Path) -> None:
    cells = load_cells(report_dir)
    print(f"# {report_dir}\n")
    for repo in REPOS:
        if repo not in cells:
            continue
        arms = cells[repo]
        print(f"## {repo}")
        header = None
        for arm in ("node_on", "node_off"):
            for run_index in sorted(arms.get(arm, {})):
                row = arms[arm][run_index]
                if header is None:
                    header = list(row)
                    print("| arm run | " + " | ".join(header) + " |")
                    print("|---" * (len(header) + 1) + "|")
                print(f"| {arm} {run_index} | " + " | ".join(str(row[m]) for m in header) + " |")

        on_runs = arms.get("node_on", {})
        off_runs = arms.get("node_off", {})
        if not on_runs:
            print("(no node_on runs)\n")
            continue
        metrics = list(next(iter(on_runs.values())))
        # Noise floor: max pairwise |delta| within node_on's runs.
        floor = {}
        for m in metrics:
            values = [run[m] for run in on_runs.values()]
            floor[m] = max(abs(a - b) for a in values for b in values) if len(values) > 1 else 0

        paired = sorted(set(on_runs) & set(off_runs))
        print(f"\nnoise floor (node_on run-to-run, {len(on_runs)} runs) and arm delta:")
        print("| metric | floor | mean_on | mean_off | delta | paired signs | effect |")
        print("|---|---|---|---|---|---|---|")
        effects = {}
        for m in metrics:
            mean_on = sum(run[m] for run in on_runs.values()) / len(on_runs)
            mean_off = sum(run[m] for run in off_runs.values()) / len(off_runs) if off_runs else float("nan")
            delta = mean_on - mean_off
            signs = []
            for i in paired:
                diff = on_runs[i][m] - off_runs[i][m]
                signs.append(1 if diff > 0 else -1 if diff < 0 else 0)
            consistent = (sum(1 for s in signs if s == (1 if delta > 0 else -1)) if signs and delta else 0)
            effect = bool(off_runs) and abs(delta) > floor[m] and consistent >= 2
            effects[m] = (effect, delta)
            sign_str = "/".join(f"{i:+d}" for i in signs) or "-"
            print(f"| {m} | {floor[m]} | {mean_on:.2f} | {mean_off:.2f} | {delta:+.2f} | {sign_str} | {'EFFECT' if effect else ''} |")

        # Registered decision routing, direction-aware: node_on helping = load
        # metrics up or miss metrics down beyond floor; node_on only hurting
        # (FP or miss up beyond floor, no helping anywhere) = cut candidate.
        helps = any(e and ((m in ("ing_miss", "det_miss")) != (d > 0))
                    for m, (e, d) in effects.items())
        hurts = [m for m, (e, d) in effects.items() if e and d > 0
                 and m not in ("ing_exact", "ing_partial", "cls_A_matched", "cls_BC_matched",
                               "det_exact", "det_partial", "fires_structural")]
        if helps:
            routing = "KEEP (gold-matching load moved beyond floor)"
        elif hurts:
            routing = f"CUT CANDIDATE (only hurts: {', '.join(hurts)}; routes to its own issue + re-baseline)"
        else:
            routing = "NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration"
        print(f"\ndecision: {routing}\n")


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("benchmark/reports")
    aggregate(directory)
