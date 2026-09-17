"""#157 scope corpus pin: recorded real resolver sessions over the benchmark gold.

Layer 1 of ADR 019's two-layer test strategy. One recorded real session per
benchmark-gold ADR (`benchmark/scope_fixtures/<repo>.json`, captured by
`record_scope_corpus.py`) is replayed zero-LLM through the parse + materialize +
score path. This pins PLUMBING and RECALL-SAFETY, not triage quality:

- the `scope` key on each recorded edge reaches `ConstraintEdge.scope` and the
  trace/accounting seam (issue AC);
- no has-gold ADR loses a runtime edge to a `none` verdict (recall-safety);
- `none` verdicts leave trace residue and materialize no constraint.

Triage QUALITY (is `tooling`/`none` the right verdict?) is reported as committed
data — `TRIAGE_REPORT` — and lives as a gate in #158's k>=2 confusion matrix.
ADR 019: "fixtures carry one run's variance — plumbing pins, not quality claims."
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.adg.treesitter import parse_repo
from services.adg.unified_resolver import _materialize_edges, _parse_edges
from services.cpt.engine import CPTResult, detect
from services.models import ADG, ChangedFQN, ConstraintEdge, ConstraintScope, DiffResult
from tests.services.adg.test_benchmark_arms_eval import _load_gold
from tests.services.adg.test_unified_resolver_eval import _score_constraint, _repo_root

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DIR = REPO_ROOT / "benchmark" / "scope_fixtures"

BENCHMARK_REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python"]

# #157 / #156 recall-safety enumeration: has-gold ADRs whose text brushes tooling
# language. No has-gold runtime edge may be lost; the tuf language-version rows go
# `tooling` AND must still match gold (the accepted, scope-blind divergence).
RECALL_SAFETY_ADRS = {
    "experimenter": ["ADR-0008", "ADR-0010"],
    "python-tuf": ["ADR-0001", "ADR-0010"],
    "structurizr-python": ["ADR-0008"],
    "flowkit": ["ADR-0004"],
}

# #157 named expectations, reported (not gated here — see module docstring).
NAMED_EXPECTATIONS = {
    "flowkit": {"ADR-0001": "tooling", "ADR-0002": "tooling",
                "ADR-0008": "tooling", "ADR-0009": "tooling", "ADR-0010": "tooling",
                "ADR-0011": "none", "ADR-0012": "none"},
    "structurizr-python": {"ADR-0001": "none", "ADR-0002": "none",
                           "ADR-0003": "tooling", "ADR-0004": "tooling",
                           "ADR-0006": "tooling", "ADR-0007": "tooling"},
}


def _fixture(repo_id: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{repo_id.replace('-', '_')}.json").read_text())


def _parse_raw(raw: str, adr_id: str, adr_path: str) -> tuple[list, list[dict]]:
    """Replay a recorded response through the production parse path."""
    residue: list[dict] = []
    edges = _parse_edges(raw, adr_id, adr_path, residue)
    return edges, residue


@pytest.fixture(scope="module")
def adgs() -> dict:
    return {repo: parse_repo(_repo_root(repo)) for repo in BENCHMARK_REPOS}


# -- Corpus shape --------------------------------------------------------------


def test_fixture_covers_every_benchmark_gold_adr() -> None:
    total = 0
    for repo_id in BENCHMARK_REPOS:
        fixture = _fixture(repo_id)
        gold, _ = _load_gold(repo_id)
        assert [e["adr_id"] for e in fixture["adrs"]] == [g["adr_id"] for g in gold], repo_id
        assert all(e["raw_response"] for e in fixture["adrs"]), f"{repo_id}: empty recorded response"
        total += len(fixture["adrs"])
    assert total == 47


# -- Plumbing: scope key -> ConstraintEdge.scope -> trace residue -------------


def test_every_recorded_edge_carries_a_scope_verdict(adgs) -> None:
    """The recorded sessions' edges all materialize with a scope; `none` never
    materializes (it leaves residue instead)."""
    for repo_id in BENCHMARK_REPOS:
        fixture = _fixture(repo_id)
        for entry in fixture["adrs"]:
            edges, residue = _parse_raw(entry["raw_response"], entry["adr_id"], entry["adr_path"])
            for edge in edges:
                assert edge.scope in (ConstraintScope.RUNTIME, ConstraintScope.TOOLING), (
                    repo_id, entry["adr_id"]
                )
            assert all(row["scope"] == "none" for row in residue)


def test_none_verdict_produces_no_constraint(adgs) -> None:
    """AC: a `none` verdict never materializes as a constraint.

    The recorded run emitted no `none` verdicts (policy ADRs correctly returned
    `[]`, which the prompt instructs), so the property is exercised on a
    corpus-derived response with a `none` injected: it must drop and leave
    residue, and never enter the materialized set."""
    fixture = _fixture("flowkit")
    entry = next(e for e in fixture["adrs"] if e["adr_id"] == "ADR-0003")
    items = json.loads(entry["raw_response"][entry["raw_response"].find("["):entry["raw_response"].rfind("]") + 1])
    items[0]["scope"] = "none"
    edges, residue = _parse_raw(json.dumps(items), entry["adr_id"], entry["adr_path"])
    assert len(residue) == 1
    assert residue[0]["scope"] == "none"
    dropped = (residue[0]["subject"], residue[0]["predicate"], residue[0]["object"])
    assert dropped not in {(e.subject, e.predicate.value, e.object) for e in edges}


def test_missing_scope_defaults_runtime_on_replay() -> None:
    """A recorded response replayed with the scope key stripped still yields
    runtime edges (the dataclass default): loud, never sheltered."""
    fixture = _fixture("flowkit")
    entry = next(e for e in fixture["adrs"] if e["adr_id"] == "ADR-0003")
    items = json.loads(entry["raw_response"][entry["raw_response"].find("["):entry["raw_response"].rfind("]") + 1])
    for item in items:
        item.pop("scope", None)
    edges, _ = _parse_raw(json.dumps(items), entry["adr_id"], entry["adr_path"])
    assert edges and all(e.scope is ConstraintScope.RUNTIME for e in edges)


# -- Recall-safety: no has-gold runtime edge lost ------------------------------


def _scope_blind_materialized(entry: dict, adg) -> list:
    """The same recorded edges with every scope key stripped: all materialize as
    runtime (`runtime` is the missing-scope default). This is the pre-#157
    baseline the triage must not fall below."""
    items = json.loads(entry["raw_response"][entry["raw_response"].find("["):entry["raw_response"].rfind("]") + 1])
    for item in items:
        item.pop("scope", None)
    edges, _ = _parse_raw(json.dumps(items), entry["adr_id"], entry["adr_path"])
    return _materialize_edges(edges, adg)


def test_scope_triage_never_lowers_a_gold_score(adgs) -> None:
    """The #156 recall-safety property, isolated from extraction quality: for
    every has-gold ADR brushing tooling language, the scored gold rows under
    per-edge triage are no worse than under scope-blind (all-runtime) replay. A
    `none` verdict that deleted a real constraint would lower a score here."""
    for repo_id, adr_ids in RECALL_SAFETY_ADRS.items():
        fixture = _fixture(repo_id)
        by_id = {e["adr_id"]: e for e in fixture["adrs"]}
        adg = adgs[repo_id]
        gold, _ = _load_gold(repo_id)
        gold_by_id = {g["adr_id"]: g for g in gold}
        for adr_id in adr_ids:
            entry = by_id[adr_id]
            parsed_edges, _ = _parse_raw(entry["raw_response"], adr_id, entry["adr_path"])
            triaged = _materialize_edges(parsed_edges, adg)
            blind = _scope_blind_materialized(entry, adg)
            for expected in gold_by_id[adr_id]["constraints"]:
                triaged_score, _ = _score_constraint(expected, triaged)
                blind_score, _ = _score_constraint(expected, blind)
                assert triaged_score == blind_score, (
                    f"{repo_id} {adr_id}: scope triage changed a gold score "
                    f"({blind_score} -> {triaged_score}): {expected}"
                )


def test_tuf_language_version_gold_matches_despite_tooling_scope(adgs) -> None:
    """The accepted divergence (ADR 019 decision 2): tuf ADR-0001's language-version
    rows are tagged `tooling` and STILL satisfy gold — matching is scope-blind."""
    fixture = _fixture("python-tuf")
    entry = next(e for e in fixture["adrs"] if e["adr_id"] == "ADR-0001")
    edges, _ = _parse_raw(entry["raw_response"], "ADR-0001", entry["adr_path"])
    materialized = _materialize_edges(edges, adgs["python-tuf"])
    gold, _ = _load_gold("python-tuf")
    expected = next(g for g in gold if g["adr_id"] == "ADR-0001")["constraints"]
    assert any(e.scope is ConstraintScope.TOOLING for e in materialized)
    for row in expected:
        score, _ = _score_constraint(row, materialized)
        assert score == "exact_match"


# -- Triage quality: reported as committed data, gated in #158 -----------------


def _triage_rows() -> list[dict]:
    rows: list[dict] = []
    for repo_id in BENCHMARK_REPOS:
        fixture = _fixture(repo_id)
        named = NAMED_EXPECTATIONS.get(repo_id, {})
        for entry in fixture["adrs"]:
            edges, residue = _parse_raw(entry["raw_response"], entry["adr_id"], entry["adr_path"])
            verdicts = sorted({e.scope.value for e in edges} | ({"none"} if residue else set()))
            expected = named.get(entry["adr_id"])
            # An empty answer satisfies a `none` expectation: the prompt instructs
            # "emit nothing", so no edges at all is the none outcome.
            if expected == "none":
                matched = "none" in verdicts or not edges
            elif expected:
                matched = expected in verdicts
            else:
                matched = None
            rows.append({
                "repo_id": repo_id,
                "adr_id": entry["adr_id"],
                "verdicts": verdicts,
                "n_edges": len(edges),
                "n_none": len(residue),
                "named_expected": expected,
                "named_match": matched,
            })
    return rows


TRIAGE_REPORT = _triage_rows()


def test_triage_report_shape() -> None:
    """The reported quality artifact covers all 47 ADRs and is honest about the
    named-expectation gaps; the gate for these lives in #158's k>=2 runs."""
    assert len(TRIAGE_REPORT) == 47
    named = [r for r in TRIAGE_REPORT if r["named_expected"]]
    assert named, "named expectations should be present in the report"
    for row in named:
        assert isinstance(row["named_match"], bool)


def test_recall_safety_adrs_carry_no_none_verdict() -> None:
    """Verdict-level recall-safety: no recorded edge on a recall-safety ADR gets a
    `none` verdict (nothing deleted). Extraction recall (whether an edge was
    produced at all) is #158's quality gate, not this pin."""
    by_key = {(r["repo_id"], r["adr_id"]): r for r in TRIAGE_REPORT}
    for repo_id, adr_ids in RECALL_SAFETY_ADRS.items():
        for adr_id in adr_ids:
            row = by_key[(repo_id, adr_id)]
            assert row["n_none"] == 0, (repo_id, adr_id)
            assert "none" not in row["verdicts"], (repo_id, adr_id)


# -- #159: engine-side skip (TOOLING edges are invisible to detect) ------------


def _retag(constraint: ConstraintEdge, scope: ConstraintScope) -> ConstraintEdge:
    return ConstraintEdge(
        subject=constraint.subject,
        predicate=constraint.predicate,
        object=constraint.object,
        justification=constraint.justification,
        adr_id=constraint.adr_id,
        adr_path=constraint.adr_path,
        specificity=constraint.specificity,
        scope=scope,
    )


def test_tooling_scope_silences_real_corpus_fires(adgs) -> None:
    """#159 at the engine seam, on the real parsed graph rather than a synthetic
    pattern: the committed flowkit fixture replay fires real violations; tagging
    exactly those same edges `tooling` silences every one of them, and detect then
    sees them nowhere at all (no violation, no orphan).

    The runtime run is asserted first because the fixture's OWN tooling verdicts
    (flowkit ADR-0001/0002) happen to be orphans that fire nothing: a bare
    "tooling fires == 0" would pass on an inert edge set and prove nothing."""
    adg = adgs["flowkit"]
    fixture = _fixture("flowkit")
    edges: list[ConstraintEdge] = []
    for entry in fixture["adrs"]:
        parsed, _ = _parse_raw(entry["raw_response"], entry["adr_id"], entry["adr_path"])
        edges.extend(_materialize_edges(parsed, adg))

    diff = DiffResult(
        to_sha="baseline",
        changed_fqns=[
            ChangedFQN(fqn=node.fqn, change_type="modified", file_path=node.file_path,
                       enclosing_module=None, enclosing_class=None)
            for node in adg.nodes
        ],
    )

    def run(constraint_edges: list[ConstraintEdge]) -> CPTResult:
        return detect(diff, ADG(nodes=adg.nodes, edges=adg.edges, constraint_edges=constraint_edges))

    runtime_result = run(edges)
    assert runtime_result.violations, "fixture replay should fire (non-vacuity guard)"
    assert {v.constraint.adr_id for v in runtime_result.violations} >= {"ADR-0003", "ADR-0011"}

    tooling_result = run([_retag(c, ConstraintScope.TOOLING) for c in edges])
    assert tooling_result.violations == []
    assert tooling_result.orphans == []
