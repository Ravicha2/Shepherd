#!/usr/bin/env python3
"""#158 triage-accuracy scorer: the resolver's per-edge scope verdicts vs the
human-labeled corpus (benchmark/scope_labels.json).

Axis 2 of #158. Reads the resolver traces of a benchmark-arms batch (one
resolver_traces.jsonl per cell, #140 convention) and scores every emitted edge
and every `none`-dropped edge against the ADR's labeled expected_scope, because
scope is a per-edge verdict (ADR 019 decision 1) while the label is per ADR.

Reported:
- confusion matrix over runtime/tooling/none, ADR-label x resolver-verdict
- `none`-precision: a wrong `none` silently deletes a real constraint
- `tooling`-recall: which tooling mis-tags remain
- recall-safety: has-gold ADRs whose runtime edge was dropped or tagged `none`,
  enumerated per repo (a hard failure, never averaged away)
- the experimenter ADR-0008 passing-mention trap, reported explicitly

Usage (from repo root):
  python3 benchmark/score_scope_triage.py <trace_dir_or_batch_dir> [--labels PATH]
  python3 benchmark/score_scope_triage.py --self-check
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = REPO_ROOT / "benchmark" / "scope_labels.json"
GOLD_DIR = REPO_ROOT / "benchmark" / "gold"
TRAP = ("experimenter", "ADR-0008")
SCOPES = ("runtime", "tooling", "none")


# -- Pure scoring (pinned by app/tests/services/adg/test_scope_triage_score.py) --


def load_labels(path: Path) -> dict[tuple[str, str], dict]:
    data = json.loads(Path(path).read_text())
    return {(r["repo_id"], r["adr_id"]): r for r in data["adrs"]}


def has_gold(repo_id: str) -> set[str]:
    """ADR ids whose benchmark gold carries at least one constraint."""
    stem = repo_id.replace("-", "_")
    rows = json.loads((GOLD_DIR / f"{stem}_gold.json").read_text())
    return {r["adr_id"] for r in rows if r["constraints"]}


def parse_trace_dir(trace_dir: Path, only_run: str | None = None) -> dict[tuple[str, str], dict]:
    """One record per ADR session, keyed (repo_id, adr_id).

    The cell's repo id comes from the trace dir name
    (<repo>_node_on_run<k>), the #149 naming convention; a trace dir of loose
    jsonl files is also accepted (repo read from the file name). `only_run`
    keeps one k (the ADR 018 k>=2 discipline needs the runs separable).
    """
    out: dict[tuple[str, str], dict] = {}
    files = sorted(Path(trace_dir).glob("**/resolver_traces.jsonl"))
    if not files:
        files = sorted(Path(trace_dir).glob("**/*.jsonl"))
    for path in files:
        repo_id = path.parent.name.split("_node_on_run")[0] if path.parent != Path(trace_dir) else path.stem
        run = path.parent.name.rsplit("run", 1)[-1] if "_node_on_run" in path.parent.name else ""
        if only_run is not None and run != only_run:
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            key = (repo_id, rec["adr_id"])
            slot = out.setdefault(key, {"verdicts": [], "dropped": [], "runs": set()})
            slot["verdicts"].extend(e.get("scope", "runtime") for e in rec.get("edges", []))
            slot["dropped"].extend(rec.get("none_verdict_edges", []))
            slot["runs"].add(run)
    return out


def score(labels: dict[tuple[str, str], dict],
          verdicts: dict[tuple[str, str], dict]) -> dict:
    gold_by_repo = defaultdict(set)
    for repo_id, adr_id in labels:
        gold_by_repo[repo_id].update(has_gold(repo_id) & {adr_id})

    confusion: Counter = Counter()
    per_repo: dict[str, Counter] = defaultdict(Counter)
    recall_failures: list[dict] = []
    mis_tags: list[dict] = []

    for key, label in sorted(labels.items()):
        expected = label["expected_scope"]
        observed = verdicts.get(key, {"verdicts": [], "dropped": [], "runs": set()})
        emitted = Counter(observed["verdicts"])
        dropped = len(observed["dropped"])

        for verdict in observed["verdicts"]:
            confusion[(expected, verdict)] += 1
            per_repo[key[0]][(expected, verdict)] += 1
        if dropped:
            confusion[(expected, "none")] += dropped
            per_repo[key[0]][(expected, "none")] += dropped

        # recall-safety: has-gold ADRs, enumerated, never averaged
        if key[1] in gold_by_repo[key[0]]:
            required = (label.get("recall_safety") or {}).get("required", expected)
            failure = None
            if dropped:
                failure = f"{dropped} edge(s) dropped with a `none` verdict"
            elif not emitted:
                failure = "no edge emitted at all"
            elif required not in emitted:
                # Scope-blind matching keeps a demoted edge scored as gold (ADR 019),
                # so a tooling tag is a mis-tag, not a lost edge. Reported only when
                # EVERY edge of the ADR is demoted: a has-gold ADR may legitimately
                # carry a tooling aside (experimenter ADR-0010's typescript) next to
                # its runtime gold rows, which is per-edge triage working, not a miss.
                other = {s: c for s, c in emitted.items() if s != required}
                if other:
                    mis_tags.append({
                        "repo_id": key[0], "adr_id": key[1], "required": required,
                        "other_verdicts": other,
                        "why": (label.get("recall_safety") or {}).get("why", ""),
                    })
            if failure:
                recall_failures.append({
                    "repo_id": key[0], "adr_id": key[1], "required": required,
                    "failure": failure,
                    "why": (label.get("recall_safety") or {}).get("why", ""),
                })

    none_pred = sum(c for (e, v), c in confusion.items() if v == "none")
    none_tp = confusion.get(("none", "none"), 0)
    tooling_denom = sum(c for (e, v), c in confusion.items() if e == "tooling")
    tooling_tp = confusion.get(("tooling", "tooling"), 0)

    return {
        "confusion": {f"{e}->{v}": c for (e, v), c in sorted(confusion.items())},
        "per_repo_confusion": {repo: {f"{e}->{v}": c for (e, v), c in sorted(counts.items())}
                               for repo, counts in sorted(per_repo.items())},
        "totals": {
            "edges_scored": sum(confusion.values()),
            "expected_scope_mix": dict(Counter(l["expected_scope"] for l in labels.values())),
            "none_precision": (none_tp / none_pred) if none_pred else None,
            "none_predicted": none_pred, "none_true_positive": none_tp,
            "tooling_recall": (tooling_tp / tooling_denom) if tooling_denom else None,
            "tooling_expected_edges": tooling_denom, "tooling_tagged": tooling_tp,
        },
        "recall_safety_failures": recall_failures,
        "mis_tags": mis_tags,
        "trap_adr_0008": {
            "verdicts": verdicts.get(TRAP, {}).get("verdicts", []),
            "dropped": len(verdicts.get(TRAP, {}).get("dropped", [])),
            "passed": "runtime" in verdicts.get(TRAP, {}).get("verdicts", []),
        },
    }


def render_markdown(result: dict) -> str:
    t = result["totals"]
    lines = ["# #158 triage accuracy (per-edge verdicts vs the human labels)", ""]
    lines += ["## Confusion matrix (rows = ADR label, columns = resolver verdict)", "",
              "| expected \\ observed | runtime | tooling | none |", "|---|---|---|---|"]
    for expected in SCOPES:
        row = [str(result["confusion"].get(f"{expected}->{v}", 0)) for v in SCOPES]
        lines.append(f"| {expected} | " + " | ".join(row) + " |")
    lines += ["", f"Edges scored: {t['edges_scored']}  "
                  f"(label mix {t['expected_scope_mix']})", ""]
    np_ = t["none_precision"]
    tr_ = t["tooling_recall"]
    lines += [
        "## The two named metrics", "",
        f"- `none`-precision: {t['none_true_positive']}/{t['none_predicted']} = "
        f"{'n/a' if np_ is None else format(np_, '.3f')}",
        f"- `tooling`-recall: {t['tooling_tagged']}/{t['tooling_expected_edges']} = "
        f"{'n/a' if tr_ is None else format(tr_, '.3f')}", "",
    ]
    fails = result["recall_safety_failures"]
    lines += ["## Recall-safety (has-gold runtime edges, enumerated per repo)", "",
              "A `none`-drop or a tooling demotion is scope-induced and final. A zero-emitted ADR",
              "is only a candidate: the scorer does not read the prior baseline, so an extraction",
              "miss that already existed there is reported here too. Diff against the baseline dir",
              "before calling it a loss.", ""]
    lines += [f"- **FAILURE** {f['repo_id']} {f['adr_id']}: {f['failure']}" for f in fails] or \
             ["- no has-gold edge lost on any repo"]
    lines += [""]
    if result["mis_tags"]:
        lines += ["Mis-tags on has-gold ADRs (gold still matches scope-blind, but the tag is wrong):", ""]
        lines += [f"- {m['repo_id']} {m['adr_id']}: required {m['required']}, got {m['other_verdicts']}"
                  for m in result["mis_tags"]]
        lines += [""]
    trap = result["trap_adr_0008"]
    lines += ["## experimenter ADR-0008 passing-mention trap", "",
              f"- verdicts: {trap['verdicts']}, dropped: {trap['dropped']}, "
              f"runtime edge survived: **{trap['passed']}**", ""]
    lines += ["## Per-repo confusion", ""]
    for repo, counts in result["per_repo_confusion"].items():
        lines.append(f"- {repo}: {counts}")
    return "\n".join(lines) + "\n"


# -- CLI -----------------------------------------------------------------------


def _self_check() -> None:
    labels = {
        ("r", "A"): {"repo_id": "r", "adr_id": "A", "expected_scope": "runtime",
                     "recall_safety": {"required": "runtime"}},
        ("r", "B"): {"repo_id": "r", "adr_id": "B", "expected_scope": "tooling"},
        ("r", "C"): {"repo_id": "r", "adr_id": "C", "expected_scope": "none"},
    }
    verdicts = {
        ("r", "A"): {"verdicts": ["runtime"], "dropped": []},
        ("r", "B"): {"verdicts": ["runtime"], "dropped": []},
        ("r", "C"): {"verdicts": [], "dropped": [{"subject": "x"}]},
    }
    real = has_gold
    try:
        globals()["has_gold"] = lambda repo: {"A"}  # the has-gold set in the fixture
        out = score(labels, verdicts)
    finally:
        globals()["has_gold"] = real
    assert out["confusion"] == {"none->none": 1, "runtime->runtime": 1, "tooling->runtime": 1}, out["confusion"]
    assert out["totals"]["none_precision"] == 1.0
    assert out["totals"]["tooling_recall"] == 0.0
    assert out["recall_safety_failures"] == [], out["recall_safety_failures"]
    # a dropped edge on a has-gold ADR is a hard failure
    verdicts[("r", "A")] = {"verdicts": [], "dropped": [{"subject": "x"}]}
    globals()["has_gold"] = lambda repo: {"A"}
    try:
        out = score(labels, verdicts)
    finally:
        globals()["has_gold"] = real
    assert out["recall_safety_failures"] and "dropped" in out["recall_safety_failures"][0]["failure"]
    print("self-check ok")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--self-check" in sys.argv:
        _self_check()
        raise SystemExit(0)
    trace_dir = Path(args[0])
    labels_path = Path(sys.argv[sys.argv.index("--labels") + 1]) if "--labels" in sys.argv else DEFAULT_LABELS
    only_run = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else None
    suffix = f"_run{only_run}" if only_run else ""
    result = score(load_labels(labels_path), parse_trace_dir(trace_dir, only_run))
    (Path(trace_dir) / f"_triage{suffix}.json").write_text(json.dumps(result, indent=2) + "\n")
    md = render_markdown(result)
    (Path(trace_dir) / f"_triage{suffix}.md").write_text(md)
    print(md)
