"""Benchmark arms eval (#149): node_on vs node_off measured on benchmark/gold.

Transfers the #140 instrument to the benchmark set per the pre-registration on
#149 (issuecomment 5679974749). One cell = (repo, arm, k): the resolver runs
over every benchmark-gold ADR (arm surface via ABLATION_NODE_SEARCH_OFF as
usual), edges are scored against the benchmark gold constraints (ingestion
side, class-split by edges[].provenance), then that same run's edges feed the
benchmark verification convention on every instance (detection side).

The detection convention mirrors the #138 verification harness exactly
(status-aware diffs incl. deleted files, historical cases on a detached
worktree with expected-module scopes, documented_false_positives folded into
the structural subtraction set) with one arms-run extension the registration
covers: the structural baseline is measured empirically per run (empty-diff
detect on that run's resolved-edge graph), because resolver-invented edges
differ run to run and the gold baseline_firings list cannot know them.

Batch CLI (from app/, one cell per invocation so cells resume independently):
  BENCH_REPO=flowkit BENCH_RUN=1 \\
  BENCH_REPORT_DIR=../benchmark/reports/<batch-ts> \\
  RESOLVER_TRACE_DIR=../logs/benchmark-arms-149/flowkit_node_on_run1 \\
  PYTHONHASHSEED=0 uv run --extra dev python -m tests.services.adg.test_benchmark_arms_eval
Add ABLATION_NODE_SEARCH_OFF=1 for the node_off arm. RESOLVER_TRACE_DIR is
required (the class split is a registered metric; a silent trace miss would
degrade every edge to prompt-only).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.adg.treesitter import parse_repo
from services.models import ConstraintEdge, Diff, DiffResult, FileChange, FQNKind
from services.pipeline import adg_with_specificity, augment_immutable
from services.cpt.diff_processor import process_diff
from services.cpt.engine import detect
from tests.eval_paths import write_report
from tests.services.adg.test_unified_resolver_eval import (
    _flag_on,
    _repo_root,
    _score_fqn,
    run_eval,
)
from tests.services.cpt.test_cpt_detect_eval import _violation_summary

REPO_ROOT = Path(__file__).resolve().parents[4]
BENCHMARK_GOLD_DIR = REPO_ROOT / "benchmark" / "gold"
BENCHMARK_REPORTS_DIR = REPO_ROOT / "benchmark" / "reports"

# #160: home-assistant joins the denominator (gold un-parked 2026-09-15, 14/14
# PASS post-#150) after the measured full-graph cell put its detect cost on the
# record; see the cell report's convention note.
BENCHMARK_REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python",
                   "home-assistant"]

HAS_API_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))

_SCORE_RANK = {"exact_match": 2, "partial_match": 1, "miss": 0}

FireKey = tuple  # (adr_id, predicate, subject, object, matched_fqn)


# -- Pure helpers (pinned below, no LLM) --------------------------------------


def _load_gold(repo_id: str) -> tuple[list[dict], dict]:
    stem = repo_id.replace("-", "_")
    with open(BENCHMARK_GOLD_DIR / f"{stem}_gold.json") as f:
        gold = json.load(f)
    with open(BENCHMARK_GOLD_DIR / f"{stem}_instances.json") as f:
        instances = json.load(f)
    return gold, instances


def _repo_roots(adg) -> set[str]:
    """Top-level packages defined in the repo (first FQN segment, non-external)."""
    return {
        str(node.fqn).split(".")[0]
        for node in adg.nodes
        if node.kind != FQNKind.EXTERNAL and str(node.fqn).split(".")[0]
    }


def _internal_fqns(adg) -> set[str]:
    """The expansion universe (#154): concrete ADG node FQNs at the repo pin,
    external nodes excluded (they have no node to expand against)."""
    return {str(node.fqn) for node in adg.nodes if node.kind != FQNKind.EXTERNAL}


def _expand_pattern(pattern: str, internal_fqns: set[str]) -> set[str]:
    """Expand one constraint pattern into the concrete internal FQNs it covers.

    Namespace-root inclusive: `X.*` covers the X namespace root and everything
    under it. This mirrors the ingestion scorer's object-side convention
    (`tests/services/adg/test_resolver_eval_scorer.py`: `X.*` vs bare `X` is a
    wildcard-granularity partial, not a miss) so the two legs agree on what
    "the X namespace" means. An exact pattern covers only itself."""
    base = pattern[:-2] if pattern.endswith(".*") else pattern
    return {fqn for fqn in internal_fqns if fqn == base or fqn.startswith(base + ".")}


def _is_internal_pattern(pattern: str, roots: set[str]) -> bool:
    return pattern.rstrip(".*").split(".")[0] in roots


def _expand_triples(subject: str, predicate: str, object_: str,
                    roots: set[str], internal_fqns: set[str]) -> set[tuple]:
    """Expand a constraint into concrete (subject, predicate, object) triples
    against the pinned ADG. Internal objects expand; external objects have no
    node, so their side is literal string equality (object grounding is #146's
    scope, not a tolerance the scorer grants)."""
    subjects = _expand_pattern(subject, internal_fqns)
    objects = (_expand_pattern(object_, internal_fqns)
               if _is_internal_pattern(object_, roots) else {object_})
    return {(s, predicate, o) for s in subjects for o in objects}


def _object_matches(expected_object: str, actual_object: str,
                    roots: set[str], internal_fqns: set[str]) -> bool:
    """#154 object convention: external = string equality; internal pattern =
    expansion overlap against the pinned ADG."""
    if _is_internal_pattern(expected_object, roots):
        return bool(_expand_pattern(expected_object, internal_fqns)
                    & _expand_pattern(actual_object, internal_fqns))
    return expected_object == actual_object


def _edge_class(provenance: dict, subject: str, object_: str, roots: set[str]) -> str:
    """Pre-registered class split: B/C if either side is tool-grounded, else
    A when the object is external (prompt-instructed anchor), else other."""
    if provenance.get("subject") or provenance.get("object"):
        return "B/C"
    if object_.rstrip(".*").split(".")[0] not in roots:
        return "A"
    return "other"


def _provenance_by_edge(trace_records: list[dict]) -> dict[tuple, dict]:
    """Join key (adr_id, subject, predicate, object) -> edges[].provenance."""
    out: dict[tuple, dict] = {}
    for record in trace_records:
        for edge in record.get("edges", []):
            out[(record["adr_id"], edge["subject"], edge["predicate"], edge["object"])] = edge["provenance"]
    return out


def _fire_key(fire: dict) -> FireKey:
    return (fire["adr_id"], fire["predicate"], fire["subject"], fire["object"], fire["matched_fqn"])


def _classify_extra_fires(extra_fires: list[dict], structural_keys: set[FireKey]) -> dict:
    """Pre-registered fire classification: fires already matching the structural
    baseline set (gold baseline_firings + documented_false_positives + this
    run's empirical empty-diff fires) are structural; the remainder splits into
    the merge-mechanism family (requires_* with wildcard subject firing where
    the changed scope lacks the object — resolver over-extraction, not arm
    movement) and candidate arm movement (everything else)."""
    classified = {"structural": [], "merge_mechanism": [], "arm_candidates": []}
    for fire in extra_fires:
        if _fire_key(fire) in structural_keys:
            classified["structural"].append(fire)
        elif fire["predicate"].startswith("requires") and fire["subject"].endswith(".*"):
            classified["merge_mechanism"].append(fire)
        else:
            classified["arm_candidates"].append(fire)
    return classified


def _structural_keys(instances: dict, case: dict, empirical_fires: list[dict]) -> set[FireKey]:
    """The subtraction set per case: repo-level gold baseline_firings, the
    case's documented_false_positives, and this run's empirical empty-diff
    fires (same tree as the case — pin seed or historical worktree)."""
    keys = {tuple(row) for row in instances.get("baseline_firings", [])}
    keys |= {tuple(row) for row in case.get("documented_false_positives", [])}
    keys |= {_fire_key(fire) for fire in empirical_fires}
    return keys


def _build_case_diff(repo_root: Path, case: dict) -> Diff:
    """Status-aware diff builder (#138 verification convention): added files
    have no pin bytes, modified append to pin bytes, deleted keep from-side
    only; a spec that says modified but is missing on disk is an add."""
    changed_files: list[FileChange] = []
    file_contents: dict[str, bytes] = {}
    from_contents: dict[str, bytes] = {}
    for spec in case.get("diff", []):
        path, status = spec["path"], spec.get("status", "modified")
        if status == "modified" and not (repo_root / path).exists():
            status = "added"
        old = b"" if status == "added" else (repo_root / path).read_bytes()
        from_contents[path] = old
        if status == "deleted":
            changed_files.append(FileChange(path=path, status="deleted"))
        else:
            changed_files.append(FileChange(path=path, status=status))
            new = spec["append"].encode()
            file_contents[path] = new if status == "added" else old + new
    return Diff(
        to_sha="deadbeef", from_sha="cafebabe",
        changed_files=changed_files, file_contents=file_contents, from_contents=from_contents,
    )


def _module_scopes_changed(adg, module_prefixes: list[str]):
    """All FQNs under the given module prefixes, treated as modified
    (historical-case convention: expected matched_fqns name the probe scopes)."""
    from services.models import ChangedFQN

    return [
        ChangedFQN(fqn=node.fqn, change_type="modified", file_path=node.file_path,
                  enclosing_module=None, enclosing_class=None)
        for node in adg.nodes
        if any(str(node.fqn) == p or str(node.fqn).startswith(p + ".") for p in module_prefixes)
    ]


def _fire_summary(violation) -> dict:
    # #138 verification shape + change_type for fire-family auditing
    return {**_violation_summary(violation), "change_type": violation.change_type}


def _pattern_equality_scores(case: dict, violations) -> list[str]:
    """#154 bridge column: the OLD key, reproduced verbatim so pilot rows stay
    comparable. Match on (adr_id, predicate, subject, object) with strict string
    equality on subject and object, matched_fqn scored exact/partial, one actual
    fire per expected unit in expectation order. Kept purely so the shift is
    attributable to the key alone, never to a run-to-run difference."""
    used: set[int] = set()
    scores: list[str] = []
    for exp in case.get("expected_violations", []):
        best, best_index = "miss", None
        for index, violation in enumerate(violations):
            if index in used:
                continue
            constraint = violation.constraint
            if (constraint.adr_id == exp["adr_id"]
                    and constraint.predicate.value == exp["predicate"]
                    and constraint.subject == exp["subject"]
                    and constraint.object == exp["object"]):
                score = _score_fqn(str(violation.matched_fqn), exp["matched_fqn"])
                if _SCORE_RANK[score] > _SCORE_RANK[best]:
                    best, best_index = score, index
        if best_index is not None:
            used.add(best_index)
        scores.append(best)
    return scores


def _score_case_units(case: dict, violations, roots: set[str],
                      internal_fqns: set[str]) -> tuple[list[dict], set[int]]:
    """#154 violation-level key: match each expected unit to an actual violation
    on (adr_id, predicate, object), then score matched_fqn exact/partial.

    Subject-pattern string equality is DROPPED from the key: `matched_fqn` is the
    materialized subject the engine actually fired on, and the engine forgives
    wildcard granularity at fire time. Scoring `subject == subject` after the fact
    made a violation fired at the right FQN, right adr_id, right predicate score
    MISS because `flowapi.* != flowapi.flowapi.*` as strings (the 13-unit
    subject-anchoring family reading as 0% recall). Over-breadth is still charged:
    an over-broad subject fires on out-of-scope FQNs -> extra fires -> FP.

    Object: external = string equality; internal pattern = expansion overlap
    against the pinned ADG. Each row also carries the old key's score
    (`pattern_score`) so pilot rows stay comparable (kept alongside, per the issue
    body). Returns (per-unit rows, indices of matched actual fires)."""
    pattern_scores = _pattern_equality_scores(case, violations)
    used: set[int] = set()
    rows: list[dict] = []
    for position, exp in enumerate(case.get("expected_violations", [])):
        best, best_index = "miss", None
        for index, violation in enumerate(violations):
            if index in used:
                continue
            constraint = violation.constraint
            if (constraint.adr_id != exp["adr_id"]
                    or constraint.predicate.value != exp["predicate"]
                    or not _object_matches(exp["object"], constraint.object, roots, internal_fqns)):
                continue
            score = _score_fqn(str(violation.matched_fqn), exp["matched_fqn"])
            if _SCORE_RANK[score] > _SCORE_RANK[best]:
                best, best_index = score, index
        if best_index is not None:
            used.add(best_index)
        rows.append({"expected_fqn": exp["matched_fqn"], "score": best,
                     "subject": exp["subject"], "object": exp["object"],
                     "pattern_score": pattern_scores[position]})
    return rows, used


def _constraint_level_score(case: dict, violations, roots: set[str],
                            internal_fqns: set[str]) -> dict:
    """#154 diagnostic columns: constraint-level expansion, set overlap per repo.

    The one place that can see "right violation, wrong-scoped constraint" (a
    violation fired at the right FQN from a scope that only coincidentally covers
    it), which the violation-level key is blind to by construction. Universe =
    ADG node set at the repo pin; internal objects expand, external objects stay
    literal. A gold pattern matching zero graph nodes is a stale-gold signal,
    reported (never silently dropped): zero-relevant per rag-eval."""
    expected_triples: set[tuple] = set()
    stale = 0
    for exp in case.get("expected_violations", []):
        triples = _expand_triples(exp["subject"], exp["predicate"], exp["object"],
                                  roots, internal_fqns)
        if not triples:
            stale += 1
        expected_triples |= triples
    actual_triples: set[tuple] = set()
    for violation in violations:
        constraint = violation.constraint
        actual_triples |= _expand_triples(constraint.subject, constraint.predicate.value,
                                          constraint.object, roots, internal_fqns)
    overlap = expected_triples & actual_triples
    return {
        "expected_triples": len(expected_triples),
        "actual_triples": len(actual_triples),
        "overlap": len(overlap),
        "stale_gold_units": stale,
    }


def _prepared_seed(repo_root: Path, constraint_edges: list[ConstraintEdge]):
    adg = parse_repo(repo_root)
    merged = add_external_nodes(adg, project_root=repo_root)
    merged = merge_constraint_edges(merged, constraint_edges, project_root=repo_root)
    return adg_with_specificity(merged)


def _empty_diff_result() -> DiffResult:
    return DiffResult(to_sha="baseline")


def _cost_block(
    trace_records: list[dict],
    parse_seconds: float,
    resolve_seconds: float,
    detect_seconds: float,
    case_reports: list[dict],
) -> dict:
    """#153 cost block: stage wall times + resolver token totals read back from
    this cell's trace records (sessions = ADR sessions = trace records)."""
    return {
        "parse_seconds": round(parse_seconds, 3),
        "resolve_seconds": round(resolve_seconds, 3),
        "detect_seconds": round(detect_seconds, 3),
        "per_case_detect_seconds": [round(case["detect_seconds"], 3) for case in case_reports],
        "prompt_tokens": sum(r.get("usage", {}).get("prompt_tokens", 0) for r in trace_records),
        "completion_tokens": sum(r.get("usage", {}).get("completion_tokens", 0) for r in trace_records),
        "sessions": len(trace_records),
    }


# -- Cell runner (LLM; CLI-driven, one cell per invocation) --------------------


def _run_detection(instances: dict, repo_root: Path, all_edges: list,
                   roots: set[str]) -> list[dict]:
    """Every instance case through the verification convention on this run's
    resolved edges: pin-tree diff cases share one seed; historical cases get a
    detached worktree seed with expected-module probe scopes."""
    case_reports: list[dict] = []
    seed = None  # pin-tree seed, built lazily (diff cases only)
    pin_baseline: list[dict] | None = None
    pin_internal: set[str] = set()
    for case in instances["cases"]:
        case_start = time.perf_counter()  # #153: wall time attributable to this case
        if case.get("type") == "historical" and "diff" not in case:
            with tempfile.TemporaryDirectory() as tmp:
                worktree = Path(tmp) / "wt"
                subprocess.run(
                    ["git", "worktree", "add", "--detach", str(worktree), case["commit"]],
                    cwd=repo_root, check=True, capture_output=True,
                )
                try:
                    hist_seed = _prepared_seed(worktree, all_edges)
                    empirical = [_fire_summary(v) for v in detect(_empty_diff_result(), hist_seed).violations]
                    modules = sorted({exp["matched_fqn"] for exp in case.get("expected_violations", [])})
                    diff_result = DiffResult(to_sha="historical", changed_fqns=_module_scopes_changed(hist_seed, modules))
                    violations = detect(diff_result, hist_seed).violations
                    case_internal = _internal_fqns(hist_seed)
                finally:
                    subprocess.run(
                        ["git", "worktree", "remove", "--force", str(worktree)],
                        cwd=repo_root, check=True, capture_output=True,
                    )
        else:
            if seed is None:
                seed = _prepared_seed(repo_root, all_edges)
                pin_baseline = [_fire_summary(v) for v in detect(_empty_diff_result(), seed).violations]
                pin_internal = _internal_fqns(seed)
            diff = _build_case_diff(repo_root, case)
            violations = detect(process_diff(diff), augment_immutable(seed, diff)).violations
            empirical = pin_baseline
            case_internal = pin_internal

        rows, used = _score_case_units(case, violations, roots, case_internal)
        diagnostics = _constraint_level_score(case, violations, roots, case_internal)
        extra = [_fire_summary(v) for index, v in enumerate(violations) if index not in used]
        fires = _classify_extra_fires(extra, _structural_keys(instances, case, empirical))
        case_reports.append({
            "case_id": case["case_id"],
            "type": case.get("type", ""),
            "detect_seconds": time.perf_counter() - case_start,
            "per_unit": rows,
            "exact": sum(1 for r in rows if r["score"] == "exact_match"),
            "partial": sum(1 for r in rows if r["score"] == "partial_match"),
            "miss": sum(1 for r in rows if r["score"] == "miss"),
            "pattern_exact": sum(1 for r in rows if r["pattern_score"] == "exact_match"),
            "pattern_partial": sum(1 for r in rows if r["pattern_score"] == "partial_match"),
            "pattern_miss": sum(1 for r in rows if r["pattern_score"] == "miss"),
            "total": len(rows),
            "diagnostics": diagnostics,
            "fires": fires,
        })
    return case_reports


def _class_split_summary(per_constraint: list[dict], fp_edges: list[dict]) -> dict:
    """Matched rows + FP edges per class; miss rows are class-less (no edge)."""
    summary: dict[str, dict[str, int]] = {}

    def _bucket(cls: str) -> dict[str, int]:
        return summary.setdefault(cls or "unattributed", {"matched": 0, "false_positive_edges": 0})

    for row in per_constraint:
        if row["score"] != "miss":
            _bucket(row.get("class"))["matched"] += 1
    for edge in fp_edges:
        _bucket(edge.get("class"))["false_positive_edges"] += 1
    return summary


def run_cell(repo_id: str, arm: str, run_index: int, report_dir: Path) -> dict:
    gold, instances = _load_gold(repo_id)
    repo_root = _repo_root(repo_id)
    parse_start = time.perf_counter()  # #153: stage timing, parse = repo tree-sitter pass
    adg = parse_repo(repo_root)
    parse_seconds = time.perf_counter() - parse_start
    roots = _repo_roots(adg)

    trace_dir_env = os.environ.get("RESOLVER_TRACE_DIR")
    if not trace_dir_env:
        raise RuntimeError("RESOLVER_TRACE_DIR must point at this cell's trace dir (see module docstring)")
    trace_path = Path(trace_dir_env) / "resolver_traces.jsonl"

    # Ingestion side: the #140 instrument loop (arm surface, scoring, FP
    # itemization) with the benchmark gold as ground truth; resolved edges
    # come back on the result for the detection side.
    resolve_start = time.perf_counter()  # #153: resolve = the LLM session loop
    result = run_eval(gold, adg, repo_id)
    resolve_seconds = time.perf_counter() - resolve_start

    # Provenance join + class split (registered metric: fail loud, never silent).
    trace_records = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    if len(trace_records) < len(gold):
        raise RuntimeError(
            f"trace underflow: {len(trace_records)} records for {len(gold)} ADR sessions "
            f"({trace_path}) — the class split would silently degrade to prompt-only"
        )
    provenance = _provenance_by_edge(trace_records)

    def _class_of(adr_id: str, subject: str, predicate: str, object_: str) -> str:
        return _edge_class(
            provenance.get((adr_id, subject, predicate, object_), {}), subject, object_, roots
        )

    for row in result.results:
        if row["score"] != "miss" and row["resolved_subject"]:
            row["class"] = _class_of(row["adr_id"], row["resolved_subject"],
                                     row["expected"]["predicate"], row["resolved_object"])
    for entry in result.false_positive_edges:
        entry["class"] = _class_of(entry["adr_id"], entry["subject"], entry["predicate"], entry["object"])

    all_edges = result.resolved_edges
    detect_start = time.perf_counter()  # #153: detect = seed builds + per-case detection
    case_reports = _run_detection(instances, repo_root, all_edges, roots)
    detect_seconds = time.perf_counter() - detect_start

    report = {
        "repo_id": repo_id,
        "arm": arm,
        "run_index": run_index,
        "pin_commit": instances["pin_commit"],
        "ingestion": {
            **result.to_report(),
            "class_split": _class_split_summary(result.results, result.false_positive_edges),
        },
        "detection": {
            "cases": case_reports,
            "exact": sum(c["exact"] for c in case_reports),
            "partial": sum(c["partial"] for c in case_reports),
            "miss": sum(c["miss"] for c in case_reports),
            "total": sum(c["total"] for c in case_reports),
            "pattern_exact": sum(c["pattern_exact"] for c in case_reports),
            "pattern_partial": sum(c["pattern_partial"] for c in case_reports),
            "pattern_miss": sum(c["pattern_miss"] for c in case_reports),
            "stale_gold_units": sum(c["diagnostics"]["stale_gold_units"] for c in case_reports),
            "diagnostic_overlap": sum(c["diagnostics"]["overlap"] for c in case_reports),
            "structural": sum(len(c["fires"]["structural"]) for c in case_reports),
            "merge_mechanism": sum(len(c["fires"]["merge_mechanism"]) for c in case_reports),
            "arm_candidates": sum(len(c["fires"]["arm_candidates"]) for c in case_reports),
        },
        "cost": _cost_block(trace_records, parse_seconds, resolve_seconds, detect_seconds, case_reports),
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    write_report(report_dir / f"{repo_id.replace('-', '_')}_{arm}_run{run_index}.json", report)
    return report


# -- Pins (pure; no LLM, no repo parse) ----------------------------------------


def test_benchmark_gold_shape() -> None:
    """#160 scope pin: 5 repos, 60 cases, 63 expected units (census 2026-09-15)."""
    cases = units = 0
    for repo_id in BENCHMARK_REPOS:
        _, instances = _load_gold(repo_id)
        ids = [case["case_id"] for case in instances["cases"]]
        assert len(ids) == len(set(ids)), f"{repo_id}: duplicate case_id"
        cases += len(ids)
        units += sum(len(case.get("expected_violations", [])) for case in instances["cases"])
        assert instances["pin_commit"], f"{repo_id}: missing pin_commit"
    assert (len(BENCHMARK_REPOS), cases, units) == (5, 60, 63)


def test_edge_class_split() -> None:
    roots = {"flowclient", "flowmachine"}
    # either side tool-grounded -> B/C
    assert _edge_class({"subject": ["search_code"]}, "flowclient.*", "flowmachine", roots) == "B/C"
    assert _edge_class({"object": ["node_search"]}, "flowclient.*", "goose", roots) == "B/C"
    # prompt-only + external object -> A (the anchor-bait signature)
    assert _edge_class({}, "experimenter.*", "graphene", roots) == "A"
    assert _edge_class({}, "experimenter.*", "graphene.relay", roots) == "A"
    # prompt-only + internal object -> other
    assert _edge_class({}, "flowclient.*", "flowmachine.core", roots) == "other"
    assert _edge_class({"subject": [], "object": []}, "x", "external_pkg", roots) == "A"


def test_classify_extra_fires() -> None:
    fire = {"adr_id": "ADR-0003", "predicate": "prohibits_dependency", "subject": "flowclient.flowclient.*",
            "object": "flowmachine", "matched_fqn": "flowclient.flowclient.aggregates",
            "changed_fqn": "c", "change_type": "modified"}
    structural = {("ADR-0003", "prohibits_dependency", "flowclient.flowclient.*", "flowmachine",
                   "flowclient.flowclient.aggregates")}
    mechanism = {**fire, "adr_id": "ADR-0004", "predicate": "requires_dependency",
                 "subject": "tuf.*", "object": "securesystemslib"}
    movement = {**fire, "adr_id": "ADR-0007", "predicate": "requires_dependency",
                "subject": "tuf.api.metadata", "object": "securesystemslib.gpg"}
    classified = _classify_extra_fires([fire, mechanism, movement], structural)
    assert [classified[k] for k in ("structural", "merge_mechanism", "arm_candidates")] == [
        [fire], [mechanism], [movement],
    ]
    assert _classify_extra_fires([], set()) == {"structural": [], "merge_mechanism": [], "arm_candidates": []}


def test_structural_keys_union() -> None:
    instances = {"baseline_firings": [["ADR-0003", "prohibits_dependency", "s", "o", "m"]]}
    case = {"documented_false_positives": [["ADR-0009", "requires_dependency", "s2", "o2", "m2"]]}
    empirical = [{"adr_id": "ADR-0001", "predicate": "requires_dependency", "subject": "s3",
                  "object": "o3", "matched_fqn": "m3", "changed_fqn": "c", "change_type": "modified"}]
    keys = _structural_keys(instances, case, empirical)
    assert keys == {
        ("ADR-0003", "prohibits_dependency", "s", "o", "m"),
        ("ADR-0009", "requires_dependency", "s2", "o2", "m2"),
        ("ADR-0001", "requires_dependency", "s3", "o3", "m3"),
    }


def test_build_case_diff_statuses(tmp_path) -> None:
    (tmp_path / "existing.py").write_text("old = 1\n")
    (tmp_path / "gone.py").write_text("to be removed\n")
    case = {"diff": [
        {"path": "existing.py", "append": "\nnew = 2\n"},
        {"path": "brand_new.py", "status": "added", "append": "fresh = 1\n"},
        {"path": "gone.py", "status": "deleted", "append": ""},
        {"path": "no_status_new.py", "append": "implicit add\n"},  # missing on disk => added
    ]}
    diff = _build_case_diff(tmp_path, case)
    by_path = {fc.path: fc.status for fc in diff.changed_files}
    assert by_path == {"existing.py": "modified", "brand_new.py": "added",
                       "gone.py": "deleted", "no_status_new.py": "added"}
    assert diff.file_contents["existing.py"] == b"old = 1\n\nnew = 2\n"
    assert diff.file_contents["brand_new.py"] == b"fresh = 1\n"
    assert "gone.py" not in diff.file_contents and diff.from_contents["gone.py"] == b"to be removed\n"
    assert diff.file_contents["no_status_new.py"] == b"implicit add\n"


def test_provenance_by_edge_join() -> None:
    records = [{"adr_id": "ADR-0001", "edges": [
        {"subject": "a", "predicate": "prohibits_dependency", "object": "b",
         "provenance": {"subject": ["search_code"], "object": []}},
    ]}]
    joined = _provenance_by_edge(records)
    assert joined[("ADR-0001", "a", "prohibits_dependency", "b")] == {"subject": ["search_code"], "object": []}
    assert ("ADR-0002", "a", "prohibits_dependency", "b") not in joined


def test_class_split_summary_buckets() -> None:
    per_constraint = [
        {"score": "exact_match", "class": "B/C"},
        {"score": "partial_match", "class": "A"},
        {"score": "miss"},  # class-less
    ]
    fp_edges = [{"class": "A"}, {"class": None}]
    summary = _class_split_summary(per_constraint, fp_edges)
    assert summary == {
        "B/C": {"matched": 1, "false_positive_edges": 0},
        "A": {"matched": 1, "false_positive_edges": 1},
        "unattributed": {"matched": 0, "false_positive_edges": 1},
    }


# -- #154 detection-scorer convention: violation-level key + diagnostics -------


def _violation(adr_id: str, predicate: str, subject: str, object_: str, matched_fqn: str):
    from services.cpt.resolution import Violation
    from services.fqn import FQN
    from services.models import ConstraintEdge, PredicateType
    from services.resolver import MatchStatus

    constraint = ConstraintEdge(
        subject=subject, predicate=PredicateType(predicate), object=object_,
        justification="pin fixture", adr_id=adr_id, adr_path="docs/adr/x.md",
    )
    return Violation(
        constraint=constraint, changed_fqn=FQN.from_dotted(matched_fqn),
        matched_fqn=FQN.from_dotted(matched_fqn), match_status=MatchStatus.WILDCARD,
        evidence="pin fixture", change_type="modified",
    )


def test_violation_level_key_drops_subject_pattern_equality() -> None:
    """#154: the 13-unit subject-anchoring family. A violation fired at the right
    matched_fqn, right adr_id, right predicate, right object must score on
    matched_fqn even when the constraint subject pattern differs in granularity
    (`flowapi.*` vs gold `flowapi.flowapi.*`). The old key demanded string
    equality on subject and scored this MISS."""
    case = {"expected_violations": [{
        "adr_id": "ADR-0004", "predicate": "requires_dependency",
        "subject": "flowapi.flowapi.*", "object": "quart",
        "matched_fqn": "flowapi.flowapi.legacy_backend.run_query_locally",
    }]}
    violations = [_violation("ADR-0004", "requires_dependency", "flowapi.*", "quart",
                             "flowapi.flowapi.legacy_backend.run_query_locally")]
    rows, used = _score_case_units(case, violations, {"flowapi", "flowclient", "flowmachine"},
                                   {"flowapi.flowapi.legacy_backend.run_query_locally"})
    assert rows[0]["score"] == "exact_match"
    assert rows[0]["pattern_score"] == "miss"  # the demoted column still records the old read
    assert used == {0}


def test_violation_level_key_still_scores_matched_fqn_exact_partial() -> None:
    """The key change drops subject pattern equality, NOT the matched_fqn
    exact/partial grading: a fire at an ancestor of the gold FQN is partial."""
    case = {"expected_violations": [{
        "adr_id": "ADR-0003", "predicate": "prohibits_dependency",
        "subject": "flowapi.flowapi.*", "object": "flowmachine",
        "matched_fqn": "flowapi.flowapi.client_proxy",
    }]}
    exact = _violation("ADR-0003", "prohibits_dependency", "flowapi.*", "flowmachine",
                       "flowapi.flowapi.client_proxy")
    ancestor = _violation("ADR-0003", "prohibits_dependency", "flowapi.*", "flowmachine",
                          "flowapi")
    rows, _ = _score_case_units(case, [exact], {"flowapi"}, {"flowapi.flowapi.client_proxy"})
    assert rows[0]["score"] == "exact_match"
    rows, _ = _score_case_units(case, [ancestor], {"flowapi"}, {"flowapi.flowapi.client_proxy"})
    assert rows[0]["score"] == "partial_match"


def test_violation_level_key_rejects_wrong_adr_predicate_or_object() -> None:
    """Over-breadth is still charged: a right-FQN fire under the wrong adr_id,
    wrong predicate, or wrong external object is not credited."""
    case = {"expected_violations": [{
        "adr_id": "ADR-0004", "predicate": "requires_dependency",
        "subject": "flowapi.flowapi.*", "object": "quart",
        "matched_fqn": "flowapi.flowapi.legacy_backend.run_query_locally",
    }]}
    fqn = "flowapi.flowapi.legacy_backend.run_query_locally"
    roots, internal = {"flowapi"}, {fqn}
    wrong_adr = _violation("ADR-0005", "requires_dependency", "flowapi.*", "quart", fqn)
    wrong_pred = _violation("ADR-0004", "requires_dependency", "flowapi.*", "zmq", fqn)
    wrong_obj = _violation("ADR-0004", "requires_dependency", "flowapi.*", "redis", fqn)
    for v in (wrong_adr, wrong_pred, wrong_obj):
        rows, used = _score_case_units(case, [v], roots, internal)
        assert rows[0]["score"] == "miss", v.constraint.object
        assert used == set()


def test_object_match_internal_expansion_external_equality() -> None:
    """#154 object convention: internal objects compare by expansion overlap
    against the pinned ADG; external objects (no node) are literal string
    equality, so wrong external grounding stays a miss (object grounding is
    #146's scope)."""
    internal = {"tuf.repository", "tuf.repository.writer", "tuf.api.metadata"}
    roots = {"tuf"}
    # internal pattern overlaps a concrete internal object (exact vs .* base)
    assert _object_matches("tuf.api.metadata.*", "tuf.api.metadata", roots, internal)
    assert _object_matches("tuf.repository.*", "tuf.repository.writer", roots, internal)
    # external objects are literal
    assert _object_matches("mozilla_nimbus_schemas.*", "mozilla_nimbus_schemas.*", roots - {"tuf"}, internal)
    assert not _object_matches("pydantic", "mozilla_nimbus_schemas.*", {"experimenter"}, internal)
    # no overlap -> no credit
    assert not _object_matches("tuf.api.metadata.*", "tuf.repository", roots, internal)


def test_expand_pattern_includes_namespace_root() -> None:
    """Expansion is namespace-inclusive base-or-under for both forms (mirroring
    the ingestion scorer's ancestor tolerance: `X.*` vs bare `X` is a
    wildcard-granularity partial, and a bare `X` object is satisfied by any
    reachable under X per the engine's requires semantics). A pattern with no
    node at or under it expands to the empty set (the stale-gold signal)."""
    internal = {"a.b", "a.b.c", "a.bc", "z"}
    assert _expand_pattern("a.b.*", internal) == {"a.b", "a.b.c"}
    assert _expand_pattern("a.b", internal) == {"a.b", "a.b.c"}
    assert _expand_pattern("a.bc.*", internal) == {"a.bc"}
    assert _expand_pattern("missing.*", internal) == set()


def test_constraint_level_diagnostic_reports_stale_gold() -> None:
    """#154 diagnostics: constraint-level expansion overlap is reported
    alongside, and a gold pattern matching zero graph nodes is a stale-gold
    signal counted, never silently dropped (zero-relevant N/A per rag-eval)."""
    case = {"expected_violations": [
        {"adr_id": "ADR-0008", "predicate": "prohibits_dependency",
         "subject": "examples.*", "object": "structurizr.api.*",
         "matched_fqn": "examples.direct_api_client"},
        {"adr_id": "ADR-0009", "predicate": "requires_dependency",
         "subject": "gone.*", "object": "also_gone.*",
         "matched_fqn": "gone.thing"},
    ]}
    roots = {"examples", "src", "structurizr"}
    internal = {"examples.direct_api_client", "structurizr.api",
                "src.structurizr.api", "src.structurizr.api.parse"}
    violations = [_violation("ADR-0008", "prohibits_dependency", "examples.*",
                             "structurizr.api.*", "examples.direct_api_client")]
    diag = _constraint_level_score(case, violations, roots, internal)
    assert diag["stale_gold_units"] == 1  # the `gone.*` gold object has no node
    assert diag["overlap"] >= 1



def test_cost_block_sums_usage_across_sessions() -> None:
    """#153 cost block: token totals + session count come from the trace records
    (a pre-instrument trace with no usage key must not crash the report), the
    three stage timings pass through rounded, per-case timings as a list."""
    records = [
        {"adr_id": "ADR-1", "usage": {"prompt_tokens": 100, "completion_tokens": 50, "llm_calls": 3}},
        {"adr_id": "ADR-2", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "llm_calls": 1}},
        {"adr_id": "ADR-3"},  # pre-#153 trace shape
    ]
    cases = [{"case_id": "c1", "detect_seconds": 1.23456}, {"case_id": "c2", "detect_seconds": 0.4}]
    cost = _cost_block(records, 2.0, 100.567, 7.25, cases)
    assert cost == {
        "parse_seconds": 2.0,
        "resolve_seconds": 100.567,
        "detect_seconds": 7.25,
        "per_case_detect_seconds": [1.235, 0.4],
        "prompt_tokens": 110,
        "completion_tokens": 55,
        "sessions": 3,
    }


def test_aggregator_cost_means() -> None:
    """#153 aggregator: cost fields mean over an arm's runs (runs without cost
    data tolerated), per_case_detect_seconds flattens to a per-case mean."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("aggregate_arms", REPO_ROOT / "benchmark" / "aggregate_arms.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    means = module._cost_means({
        1: {"parse_seconds": 2.0, "resolve_seconds": 100.0, "detect_seconds": 8.0,
            "per_case_detect_seconds": [1.0, 3.0], "prompt_tokens": 1000,
            "completion_tokens": 500, "sessions": 9},
        2: {"parse_seconds": 4.0, "resolve_seconds": 200.0, "detect_seconds": 4.0,
            "per_case_detect_seconds": [2.0, 2.0], "prompt_tokens": 2000,
            "completion_tokens": 1500, "sessions": 10},
        3: {},  # pre-#153 report: no cost block
    })
    assert means == {
        "parse_seconds": 3.0, "resolve_seconds": 150.0, "detect_seconds": 6.0,
        "per_case_detect_seconds": 2.0, "prompt_tokens": 1500.0,
        "completion_tokens": 1000.0, "sessions": 9.5,
    }
    empty = module._cost_means({1: {}})
    assert empty["parse_seconds"] != empty["parse_seconds"]  # nan when no run carries the field


# -- CLI -----------------------------------------------------------------------


if __name__ == "__main__":
    repo_id = os.environ.get("BENCH_REPO", BENCHMARK_REPOS[0])
    run_index = int(os.environ.get("BENCH_RUN", "1"))
    report_dir = Path(os.environ.get(
        "BENCH_REPORT_DIR", str(BENCHMARK_REPORTS_DIR / datetime.now().strftime("%Y-%m-%dT%H-%M-%S"))
    ))
    arm = "node_off" if _flag_on("ABLATION_NODE_SEARCH_OFF") else "node_on"
    report = run_cell(repo_id, arm, run_index, report_dir)
    ing, det = report["ingestion"], report["detection"]
    print(f"\n[benchmark_arms:{repo_id} {arm} run{run_index}] "
          f"ingestion e/p/m={ing['exact']}/{ing['partial']}/{ing['miss']} FP={ing['false_positives']} "
          f"class_split={ing['class_split']} | "
          f"detection e/p/m={det['exact']}/{det['partial']}/{det['miss']} "
          f"fires struct/mech/arm={det['structural']}/{det['merge_mechanism']}/{det['arm_candidates']} | "
          f"cost parse/resolve/detect={report['cost']['parse_seconds']}/{report['cost']['resolve_seconds']}/"
          f"{report['cost']['detect_seconds']}s tokens p/c={report['cost']['prompt_tokens']}/"
          f"{report['cost']['completion_tokens']} sessions={report['cost']['sessions']}")
