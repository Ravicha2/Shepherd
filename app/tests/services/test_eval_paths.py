"""Versioned eval report paths: every run gets its own timestamped directory."""
from __future__ import annotations

import re
from pathlib import Path

from tests.eval_paths import GROUND_TRUTH_DIR, RUN_DIR, report_path, write_report


def test_report_path_lands_in_timestamped_run_dir() -> None:
    """Reports live under reports/<timestamp>/, dash-repo ids are underscored."""
    path = report_path("python-tuf")
    assert path.parent.parent == GROUND_TRUTH_DIR / "reports"
    assert path.parent == RUN_DIR
    assert path.name == "python_tuf_eval_report.json"


def test_run_dir_stamp_format() -> None:
    """Run directory name is a sortable filesystem-safe timestamp."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}", RUN_DIR.name)


def test_write_report_stamps_meta(tmp_path: Path) -> None:
    """Written reports carry _meta (generation time + git commit) for triage."""
    target = tmp_path / "nested" / "report.json"
    write_report(target, {"accuracy": 0.5})
    import json
    payload = json.loads(target.read_text())
    assert payload["_meta"]["git_commit"]
    assert payload["accuracy"] == 0.5


def test_write_report_stamps_versions(tmp_path: Path, monkeypatch) -> None:
    """_meta records the resolver stack versions: semble package, semble model,
    LANGEXTRACT model id (#130: LLM runs don't reproduce, versions are the only
    reproducibility left). Env overrides are captured, not the defaults."""
    monkeypatch.setenv("LANGEXTRACT_MODEL_ID", "vendor/model-x")
    monkeypatch.setenv("SEMBLE_MODEL_NAME", "local/potion-y")
    target = tmp_path / "report.json"
    write_report(target, {})
    import json
    meta = json.loads(target.read_text())["_meta"]
    assert meta["semble_version"] == "0.5.6"
    assert meta["semble_model"] == "local/potion-y"
    assert meta["resolver_model"] == "vendor/model-x"
