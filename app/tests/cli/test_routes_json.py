"""`cpt routes` emits the ADR 021 inventory as deterministic JSON."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, source in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")


def test_routes_emits_records_and_no_guards(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, {
        "app/__init__.py": "",
        "app/views.py": (
            "from fastapi import APIRouter\n"
            "\n"
            "router = APIRouter()\n"
            "\n"
            "@router.get('/users/{user_id}')\n"
            "def get_user(user_id: int):\n"
            "    return {}\n"
        ),
    }, "route")

    result = runner.invoke(app, ["routes", "--path", str(repo)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["gaps"] == []
    assert payload["routes"][0]["handler_fqn"] == "app.views.get_user"
    assert payload["routes"][0]["canonical_path"] == "/users/{}"
    assert "guards" not in payload["routes"][0]


def test_routes_rerun_is_byte_identical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, {
        "app/__init__.py": "",
        "app/views.py": (
            "from flask import Blueprint\n"
            "\n"
            "bp = Blueprint('views', __name__)\n"
            "\n"
            "@bp.route('/items/<int:item_id>', methods=['GET', 'POST'])\n"
            "def item(item_id):\n"
            "    return ''\n"
        ),
    }, "route")

    first = runner.invoke(app, ["routes", "--path", str(repo)])
    second = runner.invoke(app, ["routes", "--path", str(repo)])

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout


def test_routes_reads_a_pinned_sha_without_checkout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    old_sha = _commit(repo, {
        "app/__init__.py": "",
        "app/views.py": (
            "from fastapi import APIRouter\n"
            "\n"
            "router = APIRouter()\n"
            "\n"
            "@router.get('/old')\n"
            "def old():\n"
            "    return {}\n"
        ),
    }, "old")
    _commit(repo, {
        "app/views.py": (
            "from fastapi import APIRouter\n"
            "\n"
            "router = APIRouter()\n"
            "\n"
            "@router.get('/new')\n"
            "def new():\n"
            "    return {}\n"
        ),
    }, "new")

    result = runner.invoke(app, ["routes", "--path", str(repo), "--sha", old_sha])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert [route["raw_path"] for route in payload["routes"]] == ["/old"]
    assert payload["routes"][0]["handler_fqn"] == "app.views.old"


def test_routes_sha_rerun_is_byte_identical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sha = _commit(repo, {
        "app/__init__.py": "",
        "app/views.py": (
            "from flask import Blueprint\n"
            "\n"
            "bp = Blueprint('views', __name__)\n"
            "\n"
            "@bp.route('/items/<int:item_id>')\n"
            "def item(item_id):\n"
            "    return ''\n"
        ),
    }, "route")

    first = runner.invoke(app, ["routes", "--path", str(repo), "--sha", sha])
    second = runner.invoke(app, ["routes", "--path", str(repo), "--sha", sha])

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout


def test_routes_rejects_an_unknown_sha(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit(repo, {"app/__init__.py": ""}, "empty")

    result = runner.invoke(app, ["routes", "--path", str(repo), "--sha", "does-not-exist"])

    assert result.exit_code == 1
    assert "git" in result.output.lower() or "sha" in result.output.lower()
