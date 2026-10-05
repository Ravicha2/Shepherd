"""#190: `seed build --constraints FILE` loads a pre-built rule set and never
runs the resolver; `--constraints-out FILE` dumps the built rule set in gold
format with `scope`, so a replay re-extracts ADRs only when the set changes.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import cli.main as main
from cli.config import GlobalConfig, RepoConfig
from cli.main import app
from services.adg.gold import dump_gold_edges, load_gold_edges
from services.models import ADG, ConstraintEdge, ConstraintScope, PredicateType

runner = CliRunner()


def _edge(scope: ConstraintScope) -> ConstraintEdge:
    return ConstraintEdge(
        subject="app.tools.*",
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        object="app.models.*",
        justification="j",
        adr_id="ADR-009",
        adr_path="docs/adr/009.md",
        scope=scope,
    )


def _run(tmp_path, args, build_seed=None):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    config = GlobalConfig(repos=[RepoConfig(id="repo", url=str(repo_path))])
    store = MagicMock()
    seed = build_seed if build_seed is not None else AssertionError("resolver called")
    with patch.object(main, "load_config", return_value=config), \
         patch.object(main, "parse_repo", return_value=ADG()), \
         patch.object(main, "GraphStore", return_value=store), \
         patch("services.pipeline.ADGPipeline.build_seed", side_effect=seed):
        result = runner.invoke(app, ["seed", "build", "--repo", "repo", *args])
    return store, result


def test_constraints_load_never_calls_the_resolver_and_keeps_scope(tmp_path) -> None:
    constraints = tmp_path / "constraints.json"
    dump_gold_edges(constraints, [_edge(ConstraintScope.TOOLING)])

    store, result = _run(tmp_path, ["--constraints", str(constraints)])

    assert result.exit_code == 0, result.output
    stored = store.store_adg.call_args.args[0]
    assert [(e.adr_id, e.scope) for e in stored.constraint_edges] == [
        ("ADR-009", ConstraintScope.TOOLING)
    ]


def test_constraints_out_writes_the_rule_set_with_scope(tmp_path) -> None:
    out = tmp_path / "constraints.json"

    store, result = _run(
        tmp_path,
        ["--constraints-out", str(out)],
        build_seed=lambda *a, **k: ADG(constraint_edges=[_edge(ConstraintScope.TOOLING)]),
    )

    assert result.exit_code == 0, result.output
    assert store.store_adg.call_args.args[0].constraint_edges
    assert load_gold_edges(out)[0].scope is ConstraintScope.TOOLING


def test_constraints_and_constraints_out_are_mutually_exclusive(tmp_path) -> None:
    constraints = tmp_path / "constraints.json"
    dump_gold_edges(constraints, [_edge(ConstraintScope.RUNTIME)])

    _, result = _run(
        tmp_path,
        ["--constraints", str(constraints), "--constraints-out", str(tmp_path / "o.json")],
    )

    assert result.exit_code == 1
