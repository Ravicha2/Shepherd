"""#163: `cpt seed build --gold --allow-off-pin` seeds a historical case's tree.

The benchmark's four historical cases run at a historical commit, not at the
census §5 pin (#167's gold seeds are pin-only, and `_require_pin` refuses
anything else). Their expected violations only exist on the historical tree, so
the historical tree needs its own gold seed. The pin stays the default: the
bypass is an explicit flag, and an off-pin build records itself under its own
name so it cannot overwrite the pin's record.
"""
from __future__ import annotations

import json
import re
import subprocess
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import cli.main as main
from cli.config import GlobalConfig, RepoConfig
from cli.main import app
from services.adg import gold
from services.models import ADG

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
runner = CliRunner()


def _plain(output: str) -> str:
    return ANSI_ESCAPE.sub("", output)


def _git_repo(path, sha_wanted: str = "") -> str:
    """A one-commit git repo, returning its full HEAD sha."""
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    (path / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "seed"], check=True, env={**env})
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def _invoke(tmp_path, extra_args, read_back=None):
    repo = "python-tuf"
    repo_path = tmp_path / repo
    repo_path.mkdir()
    _git_repo(repo_path)  # a real repo whose HEAD is not the census §5 pin
    config = GlobalConfig(repos=[RepoConfig(id=repo, url=str(repo_path))])
    store = MagicMock()
    store.load_adg.return_value = ADG(constraint_edges=read_back if read_back is not None else [])

    with patch.object(main, "load_config", return_value=config), \
         patch.object(main, "parse_repo", return_value=ADG()), \
         patch.object(main.GraphStore, "__new__", return_value=store), \
         patch("services.pipeline.ADGPipeline.build_seed",
               side_effect=AssertionError("resolver called on the --gold path")), \
         patch.object(main, "GOLD_SEED_RECORD_DIR", tmp_path / "records"):
        return store, runner.invoke(app, ["seed", "build", "--repo", repo, "--gold", *extra_args])


def test_an_off_pin_gold_seed_is_refused_by_default(tmp_path) -> None:
    _, result = _invoke(tmp_path, [])

    assert result.exit_code == 1
    output = _plain(result.output)
    assert "expected the census §5 pin" in output
    # Rich wraps the message, so assert on a fragment shorter than the wrap point.
    assert "Check out the pin before" in output


def test_allow_off_pin_builds_the_historical_seed(tmp_path) -> None:
    read_back = gold.load_gold_edges(gold.gold_path("python-tuf"))
    store, result = _invoke(tmp_path, ["--allow-off-pin"], read_back=read_back)

    assert result.exit_code == 0, result.output
    assert "identical to the gold" in _plain(result.output)
    stored = store.store_adg.call_args.args[0]
    assert gold.triples(stored.constraint_edges) == gold.gold_triples("python-tuf")


def test_an_off_pin_build_records_under_its_own_name(tmp_path) -> None:
    """The pin's record from #167 must survive: the historical build is separate."""
    read_back = gold.load_gold_edges(gold.gold_path("python-tuf"))
    _, result = _invoke(tmp_path, ["--allow-off-pin"], read_back=read_back)
    assert result.exit_code == 0, result.output

    records = sorted(p.name for p in (tmp_path / "records").glob("*.json"))
    # The historical build never takes the pin's file name.
    assert records != ["python-tuf.json"]
    assert records[0].startswith("python-tuf-") and records[0].endswith(".json")

    record = json.loads((tmp_path / "records" / records[0]).read_text())
    assert record["checkout_sha"] != record["pin"]
    assert record["matches_gold"] is True
    assert records[0] == f"python-tuf-{record['checkout_sha'][:10]}.json"
