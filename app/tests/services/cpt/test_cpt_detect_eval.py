"""CPT detect eval: score detection against gold constraints + mock diffs.

Retrieval group of the eval suite. Constraints come from the ingestion ground
truth (tests/ground_truth/<repo>_ground_truth.json) - no LLM, no Neo4j. Cases
(diff + expected violations) live in tests/ground_truth/cpt_detect_ground_truth.json.

CLI (from app/): uv run --extra dev python -m tests.services.cpt.test_cpt_detect_eval
  prints actual violations per case as a curation skeleton for expected_violations.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.adg.treesitter import parse_repo
from services.cpt.diff_processor import process_diff
from services.cpt.engine import detect
from services.models import ConstraintEdge, Diff, FileChange, FQNKind, PredicateType
from services.pipeline import adg_with_specificity, augment_immutable
from tests.services.adg.test_unified_resolver_eval import _score_fqn

REPO_ROOT = Path(__file__).resolve().parents[4]
REPOS_YAML_PATH = REPO_ROOT / "repos" / "repos.yaml"
GROUND_TRUTH_DIR = REPO_ROOT / "tests" / "ground_truth"
CPT_GROUND_TRUTH_PATH = GROUND_TRUTH_DIR / "cpt_detect_ground_truth.json"

pytestmark = [pytest.mark.cpt_eval]

_SCORE_RANK = {"exact_match": 2, "partial_match": 1, "miss": 0}


def _repo_root(repo_id: str) -> Path:
    with open(REPOS_YAML_PATH) as f:
        repos = yaml.safe_load(f)
    repo = next(r for r in repos["repos"] if r["id"] == repo_id)
    repo_path = Path(repo["url"])
    if not repo_path.is_absolute():
        repo_path = REPO_ROOT / "repos" / repo_path
    return repo_path


def _gold_constraints(repo_id: str) -> list[ConstraintEdge]:
    path = GROUND_TRUTH_DIR / f"{repo_id.replace('-', '_')}_ground_truth.json"
    with open(path) as f:
        gt = json.load(f)
    edges: list[ConstraintEdge] = []
    for entry in gt:
        for constraint in entry.get("constraints", []):
            edges.append(ConstraintEdge(
                subject=constraint["subject"],
                predicate=PredicateType(constraint["predicate"]),
                object=constraint["object"],
                justification=constraint["justification"],
                adr_id=entry["adr_id"],
                adr_path=entry["adr_path"],
            ))
    return edges


def _load_cases() -> dict[str, dict]:
    with open(CPT_GROUND_TRUTH_PATH) as f:
        return json.load(f)


def _build_diff(repo_root: Path, case: dict) -> Diff:
    changed_files: list[FileChange] = []
    file_contents: dict[str, bytes] = {}
    from_contents: dict[str, bytes] = {}
    for spec in case["diff"]:
        old = (repo_root / spec["path"]).read_bytes()
        changed_files.append(FileChange(path=spec["path"], status="modified"))
        file_contents[spec["path"]] = old + spec["append"].encode()
        from_contents[spec["path"]] = old
    return Diff(
        to_sha="deadbeef",
        from_sha="cafebabe",
        changed_files=changed_files,
        file_contents=file_contents,
        from_contents=from_contents,
    )


def run_case(repo_id: str, case: dict):
    """Full retrieval pipeline on gold constraints: merge -> specificity -> augment -> detect."""
    repo_root = _repo_root(repo_id)
    adg = parse_repo(repo_root)
    merged = add_external_nodes(adg, project_root=repo_root)
    merged = merge_constraint_edges(merged, _gold_constraints(repo_id), project_root=repo_root)
    merged = adg_with_specificity(merged)
    diff = _build_diff(repo_root, case)
    merged = augment_immutable(merged, diff)
    diff_result = process_diff(diff)
    return detect(diff_result, merged)


def _violation_summary(violation) -> dict:
    constraint = violation.constraint
    return {
        "adr_id": constraint.adr_id,
        "predicate": constraint.predicate.value,
        "subject": constraint.subject,
        "object": constraint.object,
        "matched_fqn": str(violation.matched_fqn),
        "changed_fqn": str(violation.changed_fqn),
        "evidence": violation.evidence,
    }


def score_case(case: dict, violations) -> dict:
    """Score actual violations against the case's expected_violations.

    An expected violation matches an actual one when adr_id, predicate, subject
    and object are equal; matched_fqn is scored exact/partial (ancestor-descendant
    tolerance, same as the ingestion eval) because module-level dedup can shift
    which level of a namespace the violation is reported at.
    """
    expected = case.get("expected_violations", [])
    matched_actual: set[int] = set()
    results: list[dict] = []

    for exp in expected:
        best = "miss"
        best_index: int | None = None
        for index, violation in enumerate(violations):
            if index in matched_actual:
                continue
            constraint = violation.constraint
            if (
                constraint.adr_id == exp["adr_id"]
                and constraint.predicate == PredicateType(exp["predicate"])
                and constraint.subject == exp["subject"]
                and constraint.object == exp["object"]
            ):
                fqn_score = _score_fqn(str(violation.matched_fqn), exp["matched_fqn"])
                if _SCORE_RANK[fqn_score] > _SCORE_RANK[best]:
                    best = fqn_score
                    best_index = index
        if best_index is not None:
            matched_actual.add(best_index)
        results.append({
            "expected": exp,
            "score": best,
            "justification": exp.get("justification", ""),
        })

    unexpected = [
        _violation_summary(violation)
        for index, violation in enumerate(violations)
        if index not in matched_actual
    ]
    return {
        "case_id": case["case_id"],
        "exact": sum(1 for r in results if r["score"] == "exact_match"),
        "partial": sum(1 for r in results if r["score"] == "partial_match"),
        "miss": sum(1 for r in results if r["score"] == "miss"),
        "total": len(results),
        "false_positives": len(unexpected),
        "unexpected": unexpected,
        "per_constraint": results,
    }


def _merged_node_counts(repo_id: str) -> dict:
    """Node counts after the merge path, to track wildcard-EXTERNAL pollution (issue #114)."""
    repo_root = _repo_root(repo_id)
    adg = parse_repo(repo_root)
    merged = add_external_nodes(adg, project_root=repo_root)
    merged = merge_constraint_edges(merged, _gold_constraints(repo_id), project_root=repo_root)
    external = sum(1 for n in merged.nodes if n.kind == FQNKind.EXTERNAL)
    return {"adg_nodes": len(merged.nodes), "external_nodes": external}


def run_repo_eval(repo_id: str) -> dict:
    cases = _load_cases()[repo_id]["cases"]
    case_results = []
    for case in cases:
        result = run_case(repo_id, case)
        case_results.append(score_case(case, result.violations))
    report = {
        "repo_id": repo_id,
        "cases": case_results,
        "exact": sum(c["exact"] for c in case_results),
        "partial": sum(c["partial"] for c in case_results),
        "miss": sum(c["miss"] for c in case_results),
        "false_positives": sum(c["false_positives"] for c in case_results),
        "total": sum(c["total"] for c in case_results),
        "node_counts": _merged_node_counts(repo_id),
    }
    report["accuracy"] = round(
        (report["exact"] + 0.5 * report["partial"]) / report["total"], 4
    ) if report["total"] else 0.0
    return report


def _all_repos() -> list[str]:
    return list(_load_cases().keys())


@pytest.fixture(scope="module", params=_all_repos(), ids=lambda r: r)
def repo_id(request) -> str:
    return request.param


@pytest.fixture(scope="module")
def repo_report(repo_id) -> dict:
    return run_repo_eval(repo_id)


def test_cpt_detect_eval(repo_id, repo_report) -> None:
    """Report-only: tallies must be internally consistent, accuracy is printed not gated."""
    print(f"\n[cpt_eval:{repo_id}] exact={repo_report['exact']} partial={repo_report['partial']} "
          f"miss={repo_report['miss']} total={repo_report['total']} "
          f"false_positives={repo_report['false_positives']} accuracy={repo_report['accuracy']:.3f} "
          f"adg_nodes={repo_report['node_counts']['adg_nodes']} external_nodes={repo_report['node_counts']['external_nodes']}")
    for case_result in repo_report["cases"]:
        print(f"  {case_result['case_id']}: exact={case_result['exact']} partial={case_result['partial']} "
              f"miss={case_result['miss']} unexpected={case_result['false_positives']}")
        for unexpected in case_result["unexpected"]:
            print(f"    unexpected: [{unexpected['adr_id']}] {unexpected['predicate']} "
                  f"{unexpected['subject']} -> {unexpected['object']} at {unexpected['matched_fqn']}")
    assert repo_report["total"] >= 0
    assert repo_report["exact"] + repo_report["partial"] + repo_report["miss"] == repo_report["total"]


def test_cpt_eval_report_write() -> None:
    """Write the aggregated report JSON next to the other eval reports."""
    reports = {repo_id: run_repo_eval(repo_id) for repo_id in _all_repos()}
    (GROUND_TRUTH_DIR / "cpt_detect_eval_report.json").write_text(json.dumps(reports, indent=2))


if __name__ == "__main__":
    for rid in _all_repos():
        for case in _load_cases()[rid]["cases"]:
            result = run_case(rid, case)
            print(f"\n=== {rid}:{case['case_id']} ({case['description']}) ===")
            print(json.dumps([_violation_summary(v) for v in result.violations], indent=2))