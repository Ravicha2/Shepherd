"""#245: `seed build` persists handler object parameters via the back-fill pass.

Neo4j is stubbed; what is under test is the wiring: parse -> inventory ->
back-fill -> store_adg, so the persisted ADG carries the facts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import cli.main as main
from cli.config import GlobalConfig, RepoConfig
from cli.main import app
from services.models import ADG

runner = CliRunner()


def test_seed_build_persists_object_parameters(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    (repo_path / "app").mkdir(parents=True)
    (repo_path / "app" / "__init__.py").write_text("")
    (repo_path / "app" / "views.py").write_text(
        "from fastapi import APIRouter\n"
        "\n"
        "router = APIRouter()\n"
        "\n"
        "@router.get('/users/{user_id}')\n"
        "def get_user(user_id: int):\n"
        "    return {}\n"
    )
    constraints = tmp_path / "constraints.json"
    constraints.write_text("[]")

    config = GlobalConfig(repos=[RepoConfig(id="fixture", url=str(repo_path))])
    store = MagicMock()
    store.load_adg.return_value = ADG()

    with patch.object(main, "load_config", return_value=config), \
         patch.object(main, "GraphStore", return_value=store):
        result = runner.invoke(
            app, ["seed", "build", "--repo", "fixture", "--constraints", str(constraints)]
        )

    assert result.exit_code == 0, result.output
    stored = store.store_adg.call_args.args[0]
    assert stored.node_of["app.views.get_user"].object_parameters == ("user_id",)
