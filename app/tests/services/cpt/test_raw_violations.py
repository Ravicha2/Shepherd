"""#190: detect records the pre-dedup violation list, with the governed module's
file path and import fan-in on every raw entry.

The replay needs the violations that fire keyed on the module the rule is about,
captured before resolve() collapses duplicates (#181 §4), each carrying fan-in
for #184's matched controls.
"""
from __future__ import annotations

from services.cpt.engine import detect
from services.cpt.resolution import governed_module
from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    DiffResult,
    Edge,
    FQNKind,
    FQNNode,
    PredicateType,
)


def _node(dotted: str, kind: FQNKind = FQNKind.MODULE, path: str | None = None) -> FQNNode:
    return FQNNode(
        fqn=FQN.from_dotted(dotted),
        kind=kind,
        file_path=path or dotted.replace(".", "/") + ".py",
        line_start=1,
        line_end=5,
    )


def _adg() -> ADG:
    """app.api.users and its function app.api.users.validate both match
    'app.api.*' and both reach app.models.thing; app.other.svc imports
    app.api.users. The module and its function collapse to one violation at
    resolve(), so the raw list is strictly larger."""
    nodes = [
        _node("app.api"),
        _node("app.api.users"),
        _node("app.api.users.validate", kind=FQNKind.FUNCTION, path="app/api/users.py"),
        _node("app.models"),
        _node("app.models.thing"),
        _node("app.other"),
        _node("app.other.svc"),
    ]
    edges = [
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.validate", kind="CONTAINS"),
        Edge(source="app.models", target="app.models.thing", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.models.thing", kind="IMPORTS"),
        Edge(source="app.other.svc", target="app.api.users", kind="IMPORTS"),
    ]
    constraint = ConstraintEdge(
        subject="app.api.*",
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        object="app.models.*",
        justification="layering",
        adr_id="ADR-003",
        adr_path="docs/adr/003.md",
    )
    return ADG(nodes=nodes, edges=edges, constraint_edges=[constraint])


def test_raw_list_keeps_the_module_and_its_function_before_dedup() -> None:
    result = detect(DiffResult(to_sha="abc", changed_fqns=[]), _adg())

    assert len(result.raw_violations) == 2
    assert len(result.violations) == 1  # same matched_fqn collapses the pair
    assert {str(v.changed_fqn) for v in result.raw_violations} == {
        "app.api.users",
        "app.api.users.validate",
    }
    # the survivor is the very object from the raw list, not a copy
    assert result.violations[0] in result.raw_violations


def test_every_raw_violation_has_a_location_and_governed_file_path() -> None:
    result = detect(DiffResult(to_sha="abc", changed_fqns=[]), _adg())

    for v in result.raw_violations:
        assert v.location is not None and v.location["file_path"]
        assert v.governed_file_path
        # a prohibits is governed by its changed_fqn (the subject it matched)
        assert governed_module(v) == v.changed_fqn
        assert v.governed_file_path == v.location["file_path"]


def test_fan_in_counts_modules_importing_the_governed_module_or_under_it() -> None:
    result = detect(DiffResult(to_sha="abc", changed_fqns=[]), _adg())

    by_fqn = {str(governed_module(v)): v.fan_in for v in result.raw_violations}
    assert by_fqn["app.api.users"] == 1  # app.other.svc imports it
    assert by_fqn["app.api.users.validate"] == 0  # nothing imports the function
