"""#190: `detect --json` carries the raw pre-dedup list and the governed-module
keys the replay records."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cli.config import RepoConfig
from cli.main import DetectionResult, app
from services.cpt.engine import CPTResult
from services.cpt.resolution import Violation
from services.fqn import FQN
from services.models import ConstraintEdge, DiffResult, PredicateType
from services.resolver import MatchStatus

runner = CliRunner()


def test_detect_json_includes_raw_violations_with_governed_keys() -> None:
    v = Violation(
        constraint=ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.models.*",
            justification="layering",
            adr_id="ADR-003",
            adr_path="docs/adr/003.md",
        ),
        changed_fqn=FQN.from_dotted_safe("app.api.users"),
        matched_fqn=FQN.from_dotted_safe("app.api.users"),
        match_status=MatchStatus.WILDCARD,
        evidence="app.api.users has dependency path to app.models.thing",
        change_type="structural",
        location={"file_path": "app/api/users.py", "line_start": 1, "line_end": 5},
        fan_in=3,
        governed_file_path="app/api/users.py",
    )
    dr = DetectionResult(
        cpt_result=CPTResult(violations=[v], raw_violations=[v], orphans=[], self_loop_constraints=[]),
        diff=MagicMock(to_sha="abc123", from_sha=None),
        diff_result=DiffResult(to_sha="abc123", changed_files=[], changed_fqns=[]),
        repo_cfg=RepoConfig(id="test-repo", url="/tmp/test-repo", adr_dir="docs/adr"),
        repo_path=Path("/tmp/test-repo"),
    )

    with patch("cli.main._run_detection", return_value=dr):
        result = runner.invoke(app, ["detect", "--repo", "test-repo", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert len(payload["raw_violations"]) == 1
    raw = payload["raw_violations"][0]
    assert raw["governed_fqn"] == "app.api.users"
    assert raw["fan_in"] == 3
    assert raw["governed_file_path"] == "app/api/users.py"
    assert payload["violations"][0]["fan_in"] == 3
