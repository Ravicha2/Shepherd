"""Eval gate: frozen-baseline ratchet (ADR 018, issue #119).

Asserts the committed baseline reports still satisfy the frozen ratchet
constants. Never executes an eval harness: under the eval freeze (gold set
evolved 3x; further iteration on the same set risks overfitting) the floor
moves only by deliberate re-baseline, re-committing reports and constants
together and recording the row in eval.md.

Denominators: real repos only (openlobby, python-tuf, tamr-client).
flask/django are synthetic smoke fixtures, excluded from every gate tally.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
GROUND_TRUTH_DIR = REPO_ROOT / "tests" / "ground_truth"

REAL_CPT_REPOS = ("openlobby", "python-tuf", "tamr-client")
REAL_INGESTION_REPOS = ("openlobby", "python_tuf", "tamr_client")

# Frozen ratchet constants, read off the committed 2026-09-08T13-06-27
# baseline run (git 8f27035). Move only together with a re-committed report,
# per ADR 018's re-baseline protocol.
RETRIEVAL_MIN_MATCHED_SCORE = 12.0  # exact + 0.5*partial, of 14 expected
RETRIEVAL_MAX_FP = 1
INGESTION_MIN_BLENDED = 17 / 30  # (5 + 0.5*7)/15, kept symbolic so the baseline always passes exactly
INGESTION_MAX_FP = 15

pytestmark = [pytest.mark.cpt_eval]


def _load_json(path: Path) -> dict:
    assert path.exists(), f"committed baseline missing: {path}"
    return json.loads(path.read_text())


def _real_repos(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k in REAL_CPT_REPOS}


def test_retrieval_gate() -> None:
    report = _load_json(GROUND_TRUTH_DIR / "cpt_detect_eval_report.json")
    repos = _real_repos(report)
    assert set(repos) == set(REAL_CPT_REPOS), "real-repo baseline incomplete"

    matched_score = sum(r["exact"] + 0.5 * r["partial"] for r in repos.values())
    total_fp = sum(r["false_positives"] for r in repos.values())
    total_expected = sum(r["total"] for r in repos.values())

    assert total_expected == 14, (
        f"retrieval denominator drifted: expected 14 violations, report holds {total_expected}"
    )
    assert matched_score >= RETRIEVAL_MIN_MATCHED_SCORE, (
        f"retrieval ratchet tripped: matched score {matched_score} < {RETRIEVAL_MIN_MATCHED_SCORE} "
        f"(exact={sum(r['exact'] for r in repos.values())}, "
        f"partial={sum(r['partial'] for r in repos.values())}, fp={total_fp}); "
        "if intentional, re-baseline per ADR 018 and re-commit reports+constants together"
    )
    assert total_fp <= RETRIEVAL_MAX_FP, (
        f"retrieval FP ratchet tripped: {total_fp} > {RETRIEVAL_MAX_FP}; "
        "if intentional, re-baseline per ADR 018"
    )


def test_ingestion_gate() -> None:
    repos = {}
    for repo in REAL_INGESTION_REPOS:
        path = GROUND_TRUTH_DIR / f"{repo}_eval_report.json"
        assert path.exists(), f"committed baseline missing: {path}"
        repos[repo] = json.loads(path.read_text())

    exact = sum(r["exact"] for r in repos.values())
    partial = sum(r["partial"] for r in repos.values())
    total = sum(r["total"] for r in repos.values())
    total_fp = sum(r["false_positives"] for r in repos.values())

    assert total == 15, (
        f"ingestion denominator drifted: expected 15 constraints, reports hold {total}"
    )
    blended = (exact + 0.5 * partial) / total
    assert blended >= INGESTION_MIN_BLENDED, (
        f"ingestion ratchet tripped: blended {blended:.4f} < {INGESTION_MIN_BLENDED} "
        f"(exact={exact}, partial={partial}, miss={sum(r['miss'] for r in repos.values())}, "
        f"fp={total_fp}); if intentional, re-baseline per ADR 018 and re-commit "
        "reports+constants together"
    )
    assert total_fp <= INGESTION_MAX_FP, (
        f"ingestion FP ratchet tripped: {total_fp} > {INGESTION_MAX_FP}; "
        "if intentional, re-baseline per ADR 018"
    )