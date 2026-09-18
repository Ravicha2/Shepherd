"""#167: `cpt seed build --gold` merges the benchmark gold and skips the resolver.

Neo4j, the repo parse and the resolver are all stubbed; what is under test is
the branch itself: --gold reads benchmark/gold/<repo>_gold.json, the resolver
is never called, the read-back is compared to the gold, and the build is
recorded.
"""
from __future__ import annotations

import json
import re
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


def _run(tmp_path, repo="python-tuf", read_back=None):
    """Invoke `seed build --gold` with the graph, Neo4j and the resolver stubbed."""
    repo_path = tmp_path / repo
    repo_path.mkdir()
    config = GlobalConfig(repos=[RepoConfig(id=repo, url=str(repo_path))])
    store = MagicMock()
    store.load_adg.return_value = ADG(constraint_edges=read_back if read_back is not None else [])

    with patch.object(main, "load_config", return_value=config), \
         patch.object(main, "parse_repo", return_value=ADG()), \
         patch.object(main.GraphStore, "__new__", return_value=store), \
         patch("services.pipeline.ADGPipeline.build_seed",
               side_effect=AssertionError("resolver called on the --gold path")), \
         patch.object(main, "GOLD_SEED_RECORD_DIR", tmp_path / "records"):
        return store, runner.invoke(app, ["seed", "build", "--repo", repo, "--gold"])


def test_gold_merges_gold_constraints_and_never_calls_the_resolver(tmp_path) -> None:
    read_back = gold.load_gold_edges(gold.gold_path("python-tuf"))
    store, result = _run(tmp_path, read_back=read_back)

    assert result.exit_code == 0, result.output
    assert _plain(result.output).count("identical to the gold") == 1
    stored = store.store_adg.call_args.args[0]
    assert gold.triples(stored.constraint_edges) == gold.gold_triples("python-tuf")


def test_a_seed_that_disagrees_with_the_gold_is_named(tmp_path) -> None:
    _, result = _run(tmp_path, read_back=[])  # read back nothing

    assert result.exit_code == 1
    output = _plain(result.output)
    assert "does not match the gold" in output
    assert "in gold, not in seed" in output
    # Rich wraps the tuple, so assert on the values, not the rendered line.
    assert "'ADR-0001'" in output and "'python2.7'" in output
    assert "'tuf.repository.*'" in output


def test_the_build_is_recorded(tmp_path) -> None:
    read_back = gold.load_gold_edges(gold.gold_path("python-tuf"))
    _, result = _run(tmp_path, read_back=read_back)

    record = json.loads((tmp_path / "records" / "python-tuf.json").read_text())
    assert record["repo"] == "python-tuf"
    assert record["pin"] == gold.GOLD_PINS["python-tuf"]
    assert record["constraints_loaded"] == record["constraints_read_back"] == 4
    assert record["matches_gold"] is True
    assert result.exit_code == 0, result.output


def test_gold_constraints_are_not_asked_for_a_repo_without_gold(tmp_path) -> None:
    _, result = _run(tmp_path, repo="flask")

    assert result.exit_code == 1
    assert "no benchmark gold" in _plain(result.output)
