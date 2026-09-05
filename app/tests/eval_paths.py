"""Versioned eval report locations.

Each eval run writes under tests/ground_truth/reports/<timestamp>/ instead of
overwriting the top-level report, so runs (which involve LLM output and don't
reproduce) stay diffable after the fact. The top-level reports are the frozen
pre-versioning baselines; compare with
  diff tests/ground_truth/<repo>_eval_report.json tests/ground_truth/reports/<ts>/<repo>_eval_report.json
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

GROUND_TRUTH_DIR = Path(__file__).resolve().parents[2] / "tests" / "ground_truth"
RUN_DIR = GROUND_TRUTH_DIR / "reports" / datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def report_path(repo_id: str) -> Path:
    return RUN_DIR / f"{repo_id.replace('-', '_')}_eval_report.json"


def _git_commit() -> str:
    # ponytail: "unknown" on failure rather than failing the eval run
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def write_report(path: Path, payload: dict) -> None:
    """Write one eval report, stamped with _meta (generation time + git commit)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_meta": {"generated_at": RUN_DIR.name, "git_commit": _git_commit()}, **payload}
    path.write_text(json.dumps(payload, indent=2))
