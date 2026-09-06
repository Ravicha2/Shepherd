"""ADG query tools for agent tool-call consumption.

Thin wrappers over the in-memory ADG. Each function returns structured data
suitable for LLM tool-call responses (ADR 017: bounded, typed tools; dive and
list_modules are deleted). No Neo4j dependency.
"""

from __future__ import annotations

from services.models import ADG

NEIGHBORHOOD_CAP = 150


def _capped(entries: list[dict], cap: int, prefix: str) -> dict:
    result: dict = {"entries": entries[:cap], "truncated": len(entries) > cap}
    if result["truncated"]:
        result["note"] = f"truncated at {cap}; use search_code to find specific members within {prefix}"
    return result


def list_children(fqn: str, adg: ADG, cap: int = NEIGHBORHOOD_CAP) -> dict:
    """Return direct children of `fqn` via CONTAINS edges, capped."""
    child_targets = {e.target for e in adg.edges if e.source == fqn and e.kind == "CONTAINS"}
    entries = [
        {"fqn": str(node.fqn), "kind": node.kind.value}
        for node in adg.nodes
        if str(node.fqn) in child_targets
    ]
    return _capped(entries, cap, fqn)


def list_imports(fqn: str, adg: ADG) -> list[str]:
    """Return target FQNs that `fqn` imports (IMPORTS edges)."""
    return [e.target for e in adg.edges if e.source == fqn and e.kind == "IMPORTS"]


def list_dependencies(fqn: str, adg: ADG, cap: int = NEIGHBORHOOD_CAP) -> dict:
    """Return what `fqn` uses: IMPORTS + INHERITS edges out, labeled with edge kind.

    CALLS excluded (matches dive semantics; named extension point in ADR 017 decision 2).
    """
    entries = [
        {"fqn": e.target, "edge": e.kind}
        for e in adg.edges
        if e.source == fqn and e.kind in ("IMPORTS", "INHERITS")
    ]
    return _capped(entries, cap, fqn)


def list_inherits(fqn: str, adg: ADG) -> list[str]:
    """Return target FQNs that `fqn` inherits from (INHERITS edges)."""
    return [e.target for e in adg.edges if e.source == fqn and e.kind == "INHERITS"]


if __name__ == "__main__":
    # ponytail: self-check, not a test framework
    from services.fqn import FQN
    from services.models import Edge, FQNKind, FQNNode

    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.mod"), kind=FQNKind.MODULE, file_path="app/mod.py", line_start=0, line_end=10, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.mod.Foo"), kind=FQNKind.CLASS, file_path="app/mod.py", line_start=1, line_end=10, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="app", target="app.mod", kind="CONTAINS"),
        Edge(source="app.mod", target="app.mod.Foo", kind="CONTAINS"),
        Edge(source="app.mod", target="os", kind="IMPORTS"),
        Edge(source="app.mod.Foo", target="bar.Baz", kind="INHERITS"),
    ]
    adg = ADG(nodes=nodes, edges=edges)
    assert list_children("app", adg) == {"entries": [{"fqn": "app.mod", "kind": "module"}], "truncated": False}
    assert list_children("app.mod", adg) == {"entries": [{"fqn": "app.mod.Foo", "kind": "class"}], "truncated": False}
    assert list_imports("app.mod", adg) == ["os"]
    assert list_inherits("app.mod.Foo", adg) == ["bar.Baz"]
    assert list_dependencies("app.mod", adg) == {"entries": [{"fqn": "os", "edge": "IMPORTS"}], "truncated": False}
    assert list_dependencies("app.mod.Foo", adg) == {"entries": [{"fqn": "bar.Baz", "edge": "INHERITS"}], "truncated": False}
    print("OK")