"""ADG query tools for agent tool-call consumption.

Thin wrappers over the in-memory ADG. Each function returns structured data
suitable for LLM tool-call responses. No Neo4j dependency.
"""

from __future__ import annotations

from services.models import ADG, FQNKind


def list_modules(adg: ADG) -> list[str]:
    """Return FQN strings for all MODULE nodes in the ADG."""
    return [str(n.fqn) for n in adg.nodes if n.kind == FQNKind.MODULE]


def list_children(fqn: str, adg: ADG) -> list[dict[str, str]]:
    """Return direct children of `fqn` via CONTAINS edges."""
    child_targets = {e.target for e in adg.edges if e.source == fqn and e.kind == "CONTAINS"}
    result = []
    for node in adg.nodes:
        if str(node.fqn) in child_targets:
            result.append({"fqn": str(node.fqn), "kind": node.kind.value})
    return result


def list_imports(fqn: str, adg: ADG) -> list[str]:
    """Return target FQNs that `fqn` imports (IMPORTS edges)."""
    return [e.target for e in adg.edges if e.source == fqn and e.kind == "IMPORTS"]


def list_inherits(fqn: str, adg: ADG) -> list[str]:
    """Return target FQNs that `fqn` inherits from (INHERITS edges)."""
    return [e.target for e in adg.edges if e.source == fqn and e.kind == "INHERITS"]


if __name__ == "__main__":
    # ponytail: self-check, not a test framework
    from services.fqn import FQN
    from services.models import Edge, FQNNode

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
    assert list_modules(adg) == ["app", "app.mod"]
    assert list_children("app", adg) == [{"fqn": "app.mod", "kind": "module"}]
    assert list_children("app.mod", adg) == [{"fqn": "app.mod.Foo", "kind": "class"}]
    assert list_imports("app.mod", adg) == ["os"]
    assert list_inherits("app.mod.Foo", adg) == ["bar.Baz"]
    assert list_children("nonexistent", adg) == []
    assert list_imports("nonexistent", adg) == []
    assert list_inherits("nonexistent", adg) == []
    print("OK")