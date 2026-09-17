"""#158 pins for the triage-accuracy scorer (benchmark/score_scope_triage.py).

Pure-function pins only: no LLM, no traces on disk. The live numbers come from
the k>=2 benchmark batch, not from here.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

spec = importlib.util.spec_from_file_location(
    "score_scope_triage", REPO_ROOT / "benchmark" / "score_scope_triage.py"
)
score_scope_triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_scope_triage)


def _labels() -> dict:
    return {
        ("r", "A"): {"repo_id": "r", "adr_id": "A", "expected_scope": "runtime",
                     "recall_safety": {"required": "runtime"}},
        ("r", "B"): {"repo_id": "r", "adr_id": "B", "expected_scope": "tooling"},
        ("r", "C"): {"repo_id": "r", "adr_id": "C", "expected_scope": "none"},
    }


def _with_gold(monkeypatch, adrs: set[str]) -> None:
    monkeypatch.setattr(score_scope_triage, "has_gold", lambda repo_id: adrs)


def test_confusion_counts_emitted_and_dropped_edges(monkeypatch) -> None:
    _with_gold(monkeypatch, {"A"})
    verdicts = {
        ("r", "A"): {"verdicts": ["runtime"], "dropped": []},
        ("r", "B"): {"verdicts": ["runtime"], "dropped": []},
        ("r", "C"): {"verdicts": [], "dropped": [{"subject": "x"}]},
    }
    out = score_scope_triage.score(_labels(), verdicts)
    assert out["confusion"] == {"none->none": 1, "runtime->runtime": 1, "tooling->runtime": 1}
    assert out["totals"]["none_precision"] == 1.0
    assert out["totals"]["tooling_recall"] == 0.0
    assert out["recall_safety_failures"] == []


def test_wrong_none_on_a_has_gold_adr_is_a_hard_failure(monkeypatch) -> None:
    """A `none` on a runtime-labeled ADR deletes a real constraint: worst mode."""
    _with_gold(monkeypatch, {"A"})
    verdicts = {("r", "A"): {"verdicts": [], "dropped": [{"subject": "x"}]}}
    out = score_scope_triage.score(_labels(), verdicts)
    assert out["totals"]["none_precision"] == 0.0
    assert [f["adr_id"] for f in out["recall_safety_failures"]] == ["A"]
    assert "dropped" in out["recall_safety_failures"][0]["failure"]


def test_demoted_gold_edge_is_a_mis_tag_not_a_lost_edge(monkeypatch) -> None:
    """Scope-blind matching keeps gold scored under a tooling tag (ADR 019), so
    the edge is not lost; it is enumerated as a mis-tag instead."""
    _with_gold(monkeypatch, {"A"})
    verdicts = {("r", "A"): {"verdicts": ["tooling"], "dropped": []}}
    out = score_scope_triage.score(_labels(), verdicts)
    assert out["recall_safety_failures"] == []
    assert out["mis_tags"] == [{"repo_id": "r", "adr_id": "A", "required": "runtime",
                                "other_verdicts": {"tooling": 1}, "why": ""}]


def test_mixed_adr_with_a_tooling_aside_is_not_a_mis_tag(monkeypatch) -> None:
    """experimenter ADR-0010 shape: runtime gold rows plus a tooling aside
    (typescript) is per-edge triage working, so nothing is reported."""
    _with_gold(monkeypatch, {"A"})
    verdicts = {("r", "A"): {"verdicts": ["runtime", "tooling"], "dropped": []}}
    out = score_scope_triage.score(_labels(), verdicts)
    assert out["recall_safety_failures"] == []
    assert out["mis_tags"] == []


def test_tooling_recall_counts_edges_on_tooling_labeled_adrs(monkeypatch) -> None:
    _with_gold(monkeypatch, set())
    verdicts = {("r", "B"): {"verdicts": ["tooling", "tooling", "runtime"], "dropped": []}}
    out = score_scope_triage.score(_labels(), verdicts)
    assert out["totals"]["tooling_recall"] == 2 / 3


def test_trace_dir_repo_id_comes_from_the_cell_dir_name(tmp_path) -> None:
    cell = tmp_path / "python-tuf_node_on_run2"
    cell.mkdir()
    (cell / "resolver_traces.jsonl").write_text(
        '{"adr_id": "ADR-0001", "edges": [{"scope": "tooling"}], "none_verdict_edges": []}\n'
    )
    parsed = score_scope_triage.parse_trace_dir(tmp_path)
    assert parsed[("python-tuf", "ADR-0001")]["verdicts"] == ["tooling"]
    assert parsed[("python-tuf", "ADR-0001")]["runs"] == {"2"}


def test_trace_dir_repo_id_normalizes_underscores_to_label_hyphens(tmp_path) -> None:
    """#160: the report-file stem form (`home_assistant_node_on_run1`) must key
    back to the labels' hyphenated repo id, or the scorer silently skips the repo."""
    cell = tmp_path / "home_assistant_node_on_run1"
    cell.mkdir()
    (cell / "resolver_traces.jsonl").write_text(
        '{"adr_id": "ADR-0019", "edges": [{"scope": "runtime"}], "none_verdict_edges": []}\n'
    )
    parsed = score_scope_triage.parse_trace_dir(tmp_path)
    assert parsed[("home-assistant", "ADR-0019")]["verdicts"] == ["runtime"]


def test_every_benchmark_gold_adr_is_labeled() -> None:
    """#160 AC: no benchmark ADR is left unlabeled (an unlabeled row is scored
    nowhere, i.e. a silent skip, not a zero)."""
    from tests.services.adg.test_benchmark_arms_eval import BENCHMARK_REPOS, _load_gold

    labels = score_scope_triage.load_labels(score_scope_triage.DEFAULT_LABELS)
    for repo_id in BENCHMARK_REPOS:
        gold, _ = _load_gold(repo_id)
        missing = [g["adr_id"] for g in gold if (repo_id, g["adr_id"]) not in labels]
        assert not missing, f"{repo_id}: unlabeled {missing}"
    ha = [r for r in json.loads(score_scope_triage.DEFAULT_LABELS.read_text())["adrs"]
          if r["repo_id"] == "home-assistant"]
    assert len(ha) == 22 and not any(r["contested"] for r in ha)
