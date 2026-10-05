"""#190: the constraints-file round-trip must carry `scope`.

The replay serialises the resolver's rule set per ADR version and reloads it on
later samples. Without `scope` on the wire a TOOLING edge (excluded from detect,
#159) would come back RUNTIME and start being enforced.
"""
from __future__ import annotations

from services.adg.gold import dump_gold_edges, load_gold_edges
from services.models import ConstraintEdge, ConstraintScope, PredicateType


def _edge(adr_id: str, scope: ConstraintScope, subject: str = "app.api.*") -> ConstraintEdge:
    return ConstraintEdge(
        subject=subject,
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        object="app.models.*",
        justification="j",
        adr_id=adr_id,
        adr_path=f"docs/adr/{adr_id}.md",
        scope=scope,
    )


def test_roundtrip_preserves_scope(tmp_path) -> None:
    edges = [
        _edge("ADR-001", ConstraintScope.RUNTIME),
        _edge("ADR-002", ConstraintScope.TOOLING, subject="app.tools.*"),
    ]
    out = tmp_path / "constraints.json"
    dump_gold_edges(out, edges)

    got = load_gold_edges(out)
    assert {e.adr_id: e.scope for e in got} == {
        "ADR-001": ConstraintScope.RUNTIME,
        "ADR-002": ConstraintScope.TOOLING,
    }
    # the triple identity survives the round-trip unchanged
    assert {e.subject for e in got} == {"app.api.*", "app.tools.*"}


def test_missing_scope_defaults_to_runtime(tmp_path) -> None:
    out = tmp_path / "constraints.json"
    out.write_text(
        '[{"adr_id": "ADR-001", "adr_path": "docs/adr/001.md", "constraints": '
        '[{"subject": "a.*", "predicate": "prohibits_dependency", "object": "b.*", '
        '"justification": "j"}]}]'
    )
    assert load_gold_edges(out)[0].scope is ConstraintScope.RUNTIME
