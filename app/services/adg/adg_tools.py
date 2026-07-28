"""ADG query tools for agent tool-call consumption.

Thin wrappers over the in-memory ADG. Each function returns structured data
suitable for LLM tool-call responses. No Neo4j dependency.
"""

from __future__ import annotations

from collections import deque

from services.models import ADG, FQNKind

_TRAVERSAL_EDGE_KINDS = frozenset({"CONTAINS", "IMPORTS", "INHERITS"})


def list_modules(adg: ADG) -> list[dict[str, str]]:
    """Return module nodes as dicts with fqn and kind."""
    return [{"fqn": str(n.fqn), "kind": n.kind.value} for n in adg.nodes if n.kind == FQNKind.MODULE]


def dive(fqn: str, adg: ADG, depth: int = 3) -> dict:
    """Return all nodes and edges within `depth` hops of `fqn` via BFS on
    CONTAINS/IMPORTS/INHERITS edges. Bidirectional: follows edges in both
    directions to capture parents, children, imports, and inheritance."""
    node_map = {str(n.fqn): n for n in adg.nodes}
    if fqn not in node_map:
        return {"nodes": [], "edges": []}

    visited_nodes: set[str] = {fqn}
    visited_edges: set[tuple[str, str, str]] = set()
    queue: deque[tuple[str, int]] = deque([(fqn, 0)])

    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in adg.edges:
            if edge.kind not in _TRAVERSAL_EDGE_KINDS:
                continue
            neighbor = None
            if edge.source == current:
                neighbor = edge.target
            elif edge.target == current:
                neighbor = edge.source
            if neighbor is None:
                continue
            visited_edges.add((edge.source, edge.target, edge.kind))
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)
                queue.append((neighbor, current_depth + 1))

    nodes_out = []
    for n_fqn in sorted(visited_nodes):
        if n_fqn in node_map:
            n = node_map[n_fqn]
            nodes_out.append({"fqn": str(n.fqn), "kind": n.kind.value})
    edges_out = [
        {"source": s, "target": t, "kind": k}
        for s, t, k in sorted(visited_edges)
    ]
    return {"nodes": nodes_out, "edges": edges_out}


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
    assert list_modules(adg) == [{"fqn": "app", "kind": "module"}, {"fqn": "app.mod", "kind": "module"}]
    assert list_children("app", adg) == [{"fqn": "app.mod", "kind": "module"}]
    assert list_children("app.mod", adg) == [{"fqn": "app.mod.Foo", "kind": "class"}]
    assert list_imports("app.mod", adg) == ["os"]
    assert list_inherits("app.mod.Foo", adg) == ["bar.Baz"]
    assert dive("app", adg, depth=0)["nodes"] == [{"fqn": "app", "kind": "module"}]
    assert dive("app", adg, depth=1)["nodes"] == [{"fqn": "app", "kind": "module"}, {"fqn": "app.mod", "kind": "module"}]
    assert dive("nonexistent", adg, depth=3) == {"nodes": [], "edges": []}
    print("OK")