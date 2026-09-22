"""#163: `--changed-scopes` supplies a historical case's changed set to detect.

The benchmark's historical cases carry no commit diff. Their changed set is the
set of nodes under the case's expected probe scopes, which is what the harness
convention measures (`test_benchmark_arms_eval._module_scopes_changed`). This is
the CLI-side twin, so the two-arm run's CPT arm fires on the changed set the
harness measured rather than on whatever the historical commit happened to
touch.
"""
from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import cli.main as main
from cli.config import RepoConfig
from cli.main import app, scoped_changes
from services.fqn import FQN
from services.models import ADG, DiffResult, FQNKind, FQNNode

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
runner = CliRunner()


def plain(output: str) -> str:
    return ANSI_ESCAPE.sub("", output)


def _node(dotted: str) -> FQNNode:
    return FQNNode(
        fqn=FQN.from_dotted_safe(dotted),
        kind=FQNKind.FUNCTION,
        file_path=f"{dotted.replace('.', '/')}.py",
        line_start=1,
        line_end=9,
    )


def _adg(*dotted_names: str) -> ADG:
    return ADG(nodes=[_node(name) for name in dotted_names], edges=[], constraint_edges=[])


def _stub_repo(tmp_path, adg: ADG):
    """A repo whose graph is `adg` and whose git side is never used."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir(exist_ok=True)
    store = MagicMock()
    store.load_adg.return_value = adg
    store.load_dismissals.return_value = []
    return RepoConfig(id="test-repo", url=str(repo_path), adr_dir="docs/adr"), store


class TestScopedChanges:
    """The pure changed-set builder."""

    def test_takes_every_node_under_each_prefix(self) -> None:
        adg = _adg(
            "experimenter.jetstream.client.load_data_from_gcs",
            "experimenter.jetstream.client.other",
            "experimenter.nimbus_ui.views.home",
        )

        result = scoped_changes(adg, ["experimenter.jetstream.client"])

        assert {str(f.fqn) for f in result.changed_fqns} == {
            "experimenter.jetstream.client.load_data_from_gcs",
            "experimenter.jetstream.client.other",
        }
        assert all(f.change_type == "modified" for f in result.changed_fqns)

    def test_the_prefix_itself_counts(self) -> None:
        result = scoped_changes(_adg("experimenter.jetstream.client"), ["experimenter.jetstream.client"])

        assert [str(f.fqn) for f in result.changed_fqns] == ["experimenter.jetstream.client"]

    def test_a_prefix_does_not_match_a_sibling_that_merely_starts_with_it(self) -> None:
        # "app.service" must not swallow "app.services", a different module.
        result = scoped_changes(_adg("app.service.UserService", "app.services.Registry"), ["app.service"])

        assert [str(f.fqn) for f in result.changed_fqns] == ["app.service.UserService"]

    def test_several_scopes_union(self) -> None:
        adg = _adg("app.service.UserService", "app.repo.UserRepo", "app.other.Thing")

        result = scoped_changes(adg, ["app.service", "app.repo"])

        assert {str(f.fqn) for f in result.changed_fqns} == {
            "app.service.UserService",
            "app.repo.UserRepo",
        }

    def test_no_matching_node_yields_an_empty_set(self) -> None:
        assert scoped_changes(_adg("app.other.Thing"), ["app.gone"]).changed_fqns == []

    def test_one_empty_prefix_is_how_the_empty_set_is_spelled(self) -> None:
        """A compliant historical case expects nothing: the set is empty, not absent.

        `--changed-scopes ''` is the spelling. It has to match no node even when the
        graph is full, so the structural pass alone decides the case.
        """
        result = scoped_changes(_adg("app.service.UserService", "app.repo.UserRepo"), [""])

        assert result.changed_fqns == []
        assert not any(str(f.fqn) for f in scoped_changes(_adg("a.b"), [""]).changed_fqns)

    def test_the_file_path_comes_from_the_node(self) -> None:
        result = scoped_changes(_adg("app.service.UserService"), ["app.service"])

        assert result.changed_fqns[0].file_path == "app/service/UserService.py"

    def test_scoped_changes_returns_a_diff_result(self) -> None:
        assert isinstance(scoped_changes(_adg("app.service.UserService"), ["app.service"]), DiffResult)


class TestChangedScopesOnTheCli:
    """The flag reaches detection and the git diff is skipped entirely."""

    @patch("cli.main.GraphStore")
    @patch.object(main, "GitAdapter")
    @patch.object(main, "_get_repo")
    def test_detect_reports_the_synthetic_set_and_reads_no_diff(
        self, mock_get_repo, mock_adapter, mock_store_cls, tmp_path
    ) -> None:
        repo_cfg, store = _stub_repo(tmp_path, _adg("app.service.UserService", "app.repo.UserRepo"))
        mock_get_repo.return_value = repo_cfg
        mock_store_cls.return_value = store

        result = runner.invoke(
            app, ["detect", "--repo", "test-repo", "--changed-scopes", "app.service", "--json"]
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output[result.output.find("{") : result.output.rfind("}") + 1])
        assert [f["fqn"] for f in payload["changed_fqns"]] == ["app.service.UserService"]
        assert payload["changed_files"] == []
        assert not mock_adapter.return_value.get_diff.called

    @patch("cli.main.GraphStore")
    @patch.object(main, "GitAdapter")
    @patch.object(main, "_get_repo")
    def test_violation_list_accepts_the_flag(
        self, mock_get_repo, mock_adapter, mock_store_cls, tmp_path
    ) -> None:
        """`violation list` is the command the two-arm harness calls."""
        repo_cfg, store = _stub_repo(tmp_path, _adg("app.service.UserService"))
        mock_get_repo.return_value = repo_cfg
        mock_store_cls.return_value = store

        result = runner.invoke(
            app, ["violation", "list", "--repo", "test-repo", "--changed-scopes", "app.service"]
        )

        assert result.exit_code == 0, result.output
        assert not mock_adapter.return_value.get_diff.called

    @patch("cli.main.GraphStore")
    @patch.object(main, "GitAdapter")
    @patch.object(main, "_get_repo")
    def test_an_empty_prefix_is_still_a_changed_set_decision(
        self, mock_get_repo, mock_adapter, mock_store_cls, tmp_path
    ) -> None:
        """`--changed-scopes ''` is the argv the driver sends for a 0-unit case.

        The empty set must suppress the git diff: without the flag a 0-unit
        historical case would be detected against whatever that commit touched.
        """
        repo_cfg, store = _stub_repo(tmp_path, _adg("app.service.UserService"))
        mock_get_repo.return_value = repo_cfg
        mock_store_cls.return_value = store

        result = runner.invoke(
            app, ["violation", "list", "--repo", "test-repo", "--changed-scopes", ""]
        )

        assert result.exit_code == 0, result.output
        assert not mock_adapter.return_value.get_diff.called

    @patch("cli.main.GraphStore")
    @patch.object(main, "_get_repo")
    def test_without_the_flag_the_diff_path_still_runs(self, mock_get_repo, mock_store_cls, tmp_path) -> None:
        """The flag is opt-in: a plain run still asks git for the commit's diff."""
        repo_cfg, store = _stub_repo(tmp_path, _adg("app.service.UserService"))
        mock_get_repo.return_value = repo_cfg
        mock_store_cls.return_value = store

        with patch.object(main.GitAdapter, "get_diff", side_effect=ValueError("no such sha")) as get_diff:
            result = runner.invoke(app, ["detect", "--repo", "test-repo", "--commit", "deadbeef"])

        assert result.exit_code == 1
        assert get_diff.called
        assert "Git error" in plain(result.output)
