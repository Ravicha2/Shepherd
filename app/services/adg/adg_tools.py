"""ADG query tools for agent tool-call consumption.

Thin wrappers over the in-memory ADG. Each function returns structured data
suitable for LLM tool-call responses (ADR 017: bounded, typed tools; dive and
list_modules are deleted; list_dependencies replaced by node_search per
#143). No Neo4j dependency.
"""

from __future__ import annotations

from services.models import ADG

NEIGHBORHOOD_CAP = 150
NODE_SEARCH_CAP = 20


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

    Removed from the LLM tool surface per #143 (kept as a library function for
    ad-hoc analysis; the ablation harness still references the name pattern).
    CALLS excluded (matches dive semantics).
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


# -- node_search (#143) --------------------------------------------------------
# Contract per docs/node-search-response-contracts.md (#141): server-side
# pre-ranked tiers exact > dotted-prefix > substring > relaxed subsequence
# (case-insensitive); hard cap with `truncated` + per-tier counts + narrow
# guidance; empty/over-broad queries refuse instead of returning everything
# (SWE-agent's refuse-don't-dump shape); every hit kind-labeled, with IMPORTS
# edge targets indexed as kind `external_import` (no precedent system indexes
# import-statement targets; it is the #142 anchor-bait fix). External hits
# never resolve to an ADG node behind them.


def _node_search_candidates(adg: ADG) -> list[tuple[str, str]]:
    """(fqn, kind) candidates: ADG nodes verbatim + IMPORTS edge targets
    labeled `external_import` when no node backs them (dedup, node wins)."""
    candidates: list[tuple[str, str]] = [(str(n.fqn), n.kind.value) for n in adg.nodes]
    node_fqns = {f for f, _ in candidates}
    seen = set(node_fqns)
    candidates += [
        (e.target, "external_import")
        for e in adg.edges
        if e.kind == "IMPORTS" and not (e.target in seen or seen.add(e.target))
    ]
    return candidates


def _relaxed_subsequence(query: str, fqn: str) -> bool:
    """LSP 3.18 relaxed way: query characters appear in order in the candidate
    (case-insensitive), non-contiguously."""
    it = iter(fqn)
    return all(ch in it for ch in query)


def node_search(query: str, adg: ADG, cap: int = NODE_SEARCH_CAP) -> dict:
    """Name/prefix existence check over ADG nodes + IMPORTS edge targets.

    Tiers: exact > dotted-prefix > substring > relaxed subsequence, all
    case-insensitive. Empty or over-broad queries (no exact/prefix hit,
    everything over cap) return a bounded refusal with per-tier counts and a
    narrow-by-prefix hint; never the whole-repo dump.
    """
    q = query.strip().lower()
    if not q:
        return {
            "entries": [],
            "truncated": False,
            "counts": {"exact": 0, "prefix": 0, "substring": 0, "relaxed": 0},
            "note": "empty query; narrow by prefix or kind",
        }
    candidates = _node_search_candidates(adg)

    exact = [c for c in candidates if c[0].lower() == q]
    prefix = [c for c in candidates if c[0].lower() != q and (c[0].lower().startswith(q) or c[0].lower().startswith(q + "."))]
    substring = [c for c in candidates if not exact and not prefix and q in c[0].lower()]
    relaxed = [
        c for c in candidates
        if not exact and not prefix and not substring and _relaxed_subsequence(q, c[0].lower())
    ]

    counts = {
        "exact": len(exact),
        "prefix": len(prefix),
        "substring": len(substring),
        "relaxed": len(relaxed),
    }
    tiered = exact + prefix + substring + relaxed
    if not tiered:
        return {"entries": [], "truncated": False, "counts": counts, "note": "no match"}
    if not (exact or prefix) and len(tiered) > cap:
        # generic/over-broad query: refusal shape, never the repo dump
        return {
            "entries": [],
            "truncated": True,
            "counts": counts,
            "note": f"{len(tiered)} nodes match; narrow by prefix or kind",
        }
    payload: dict = {
        "entries": [{"fqn": f, "kind": k} for f, k in tiered[:cap]],
        "truncated": len(tiered) > cap,
        "counts": counts,
    }
    if payload["truncated"]:
        payload["note"] = f"{len(tiered)} nodes match; narrow by prefix or kind"
    return payload


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