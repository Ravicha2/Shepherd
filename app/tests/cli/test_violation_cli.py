"""Tests for violation list and dismiss CLI commands."""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.config import RepoConfig
from cli.main import app, DetectionResult
from services.cpt.dismissal import Dismissal, violation_short_id
from services.cpt.engine import CPTResult
from services.cpt.resolution import Violation
from services.fqn import FQN
from services.models import ConstraintEdge, DiffResult, PredicateType
from services.resolver import MatchStatus

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def plain(output: str) -> str:
    """Strip ANSI styling: Rich 15 segments style spans per word, which breaks
    raw substring asserts (e.g. 'violation(s) dismissed')."""
    return ANSI_ESCAPE.sub("", output)


runner = CliRunner()


def _make_constraint(
    subject: str = "app.service.*",
    predicate: PredicateType = PredicateType.PROHIBITS_DEPENDENCY,
    object: str = "app.repo.*",
    adr_id: str = "ADR-001",
) -> ConstraintEdge:
    return ConstraintEdge(
        subject=subject,
        predicate=predicate,
        object=object,
        justification="test constraint",
        adr_id=adr_id,
        adr_path="docs/adr/001.md",
    )


def _make_violation(
    subject: str = "app.service.*",
    predicate: PredicateType = PredicateType.PROHIBITS_DEPENDENCY,
    object: str = "app.repo.*",
    matched_fqn: str = "app.service.UserService",
    adr_id: str = "ADR-001",
) -> Violation:
    return Violation(
        constraint=_make_constraint(subject, predicate, object, adr_id),
        changed_fqn=FQN.from_dotted_safe("app.service.UserService"),
        matched_fqn=FQN.from_dotted_safe(matched_fqn),
        match_status=MatchStatus.EXACT,
        evidence="test evidence",
        change_type="structural",
    )


def _make_cpt_result(violations: list[Violation] | None = None) -> CPTResult:
    if violations is None:
        violations = [
            _make_violation(adr_id="ADR-001"),
            _make_violation(matched_fqn="app.service.OrderService", adr_id="ADR-002"),
        ]
    return CPTResult(violations=violations, orphans=[], self_loop_constraints=[])


_MOCK_REPO_CFG = RepoConfig(id="test-repo", url="/tmp/test-repo", adr_dir="docs/adr")


def _make_detection_result(violations: list[Violation] | None = None) -> DetectionResult:
    cpt_result = _make_cpt_result(violations)
    mock_diff = MagicMock()
    mock_diff.to_sha = "abc123def456"
    mock_diff.from_sha = "parent123"
    return DetectionResult(
        cpt_result=cpt_result,
        diff=mock_diff,
        diff_result=DiffResult(to_sha="abc123def456", changed_files=[], changed_fqns=[]),
        repo_cfg=_MOCK_REPO_CFG,
        repo_path=Path("/tmp/test-repo"),
    )


class TestViolationList:
    """Test cpt violation list --repo <id>."""

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_list_shows_active_violations_with_short_ids(self, mock_detect, mock_store_cls):
        dr = _make_detection_result()
        mock_detect.return_value = dr

        mock_store = MagicMock()
        mock_store.load_dismissals.return_value = []
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["violation", "list", "--repo", "test-repo"])
        assert result.exit_code == 0
        for v in dr.cpt_result.violations:
            assert violation_short_id(v) in plain(result.output)

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_list_filters_dismissed(self, mock_detect, mock_store_cls):
        v1 = _make_violation(adr_id="ADR-001")
        dr = _make_detection_result(violations=[v1])
        mock_detect.return_value = dr

        dismissal = Dismissal.from_violation(v1)
        mock_store = MagicMock()
        mock_store.load_dismissals.return_value = [dismissal]
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["violation", "list", "--repo", "test-repo"])
        assert result.exit_code == 0
        assert "No active violations" in plain(result.output)

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_list_shows_dismissed_count(self, mock_detect, mock_store_cls):
        v1 = _make_violation(adr_id="ADR-001")
        v2 = _make_violation(matched_fqn="app.service.OrderService", adr_id="ADR-002")
        dr = _make_detection_result(violations=[v1, v2])
        mock_detect.return_value = dr

        dismissal = Dismissal.from_violation(v1)
        mock_store = MagicMock()
        mock_store.load_dismissals.return_value = [dismissal]
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["violation", "list", "--repo", "test-repo"])
        assert "1 violation(s) dismissed" in plain(result.output)

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_list_no_violations(self, mock_detect, mock_store_cls):
        dr = _make_detection_result(violations=[])
        mock_detect.return_value = dr
        mock_store = MagicMock()
        mock_store.load_dismissals.return_value = []
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["violation", "list", "--repo", "test-repo"])
        assert result.exit_code == 0
        assert "No active violations" in plain(result.output)


class TestViolationDismiss:
    """Test cpt violation dismiss <short_id> --repo <id>."""

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_dismiss_by_short_id(self, mock_detect, mock_store_cls):
        v1 = _make_violation(adr_id="ADR-001")
        dr = _make_detection_result(violations=[v1])
        mock_detect.return_value = dr

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        short_id = violation_short_id(v1)
        result = runner.invoke(app, ["violation", "dismiss", short_id, "--repo", "test-repo"])
        assert result.exit_code == 0
        mock_store.connect.assert_called_once()
        mock_store.store_dismissal.assert_called_once()
        assert "Dismissed" in plain(result.output)

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_dismiss_unknown_short_id_fails(self, mock_detect, mock_store_cls):
        dr = _make_detection_result()
        mock_detect.return_value = dr
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["violation", "dismiss", "zzzzz", "--repo", "test-repo"])
        assert result.exit_code == 1
        assert "No violation" in plain(result.output)

    @patch("cli.main.GraphStore")
    @patch("cli.main._run_detection")
    def test_dismiss_stores_correct_fields(self, mock_detect, mock_store_cls):
        v1 = _make_violation(adr_id="ADR-001")
        dr = _make_detection_result(violations=[v1])
        mock_detect.return_value = dr

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        short_id = violation_short_id(v1)
        result = runner.invoke(app, ["violation", "dismiss", short_id, "--repo", "test-repo"])
        assert result.exit_code == 0

        call_args = mock_store.store_dismissal.call_args[0][0]
        assert isinstance(call_args, Dismissal)
        assert call_args.short_id == short_id
        assert call_args.subject == v1.constraint.subject
        assert call_args.predicate == v1.constraint.predicate.value


class TestSeedBuildWipesDismissals:
    """Per ADR 012: seed rebuild wipes all dismissals via clear_all."""

    @patch("cli.main.GraphStore")
    @patch("cli.main.ADGPipeline")
    @patch("cli.main.parse_repo")
    @patch("cli.main._get_repo")
    @patch("cli.main.load_config")
    def test_seed_build_calls_clear_all(
        self, mock_config, mock_get_repo, mock_parse,
        mock_pipeline_cls, mock_store_cls
    ):
        from services.models import ADG as ADGModel

        mock_config.return_value = MagicMock()
        mock_config.return_value.langextract = MagicMock()
        mock_get_repo.return_value = _MOCK_REPO_CFG

        with patch.object(Path, "exists", return_value=True):
            mock_parse.return_value = ADGModel(nodes=[], edges=[], constraint_edges=[])
            mock_pipeline = MagicMock()
            mock_pipeline.build_seed.return_value = ADGModel(nodes=[], edges=[], constraint_edges=[])
            mock_pipeline_cls.return_value = mock_pipeline

            mock_store = MagicMock()
            mock_store_cls.return_value = mock_store

            result = runner.invoke(app, ["seed", "build", "--repo", "test-repo"])
            assert result.exit_code == 0
            mock_store.clear_all.assert_called_once()