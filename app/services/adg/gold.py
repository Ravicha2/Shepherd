"""Benchmark gold: the single reader of benchmark/gold/<repo>_gold.json.

`cpt seed build --gold` and the benchmark/*.py harnesses both build their
ConstraintEdges through `load_gold_edges` so the two paths cannot drift
(issue #167). The gold JSON is the source of truth for the two-arm run.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from services.models import ConstraintEdge, ConstraintScope, PredicateType

GOLD_DIR = Path(__file__).resolve().parents[3] / "benchmark" / "gold"

# census.md §5 commit pin table: gold seeds are built from these checkouts,
# never HEAD.
GOLD_PINS: dict[str, str] = {
    "python-tuf": "6889cfbffbb90a17930fbdedf12ae050be775fe3",
    "flowkit": "24d88247d57987fe33f6b8915540d7bf09b58033",
    "experimenter": "d61a2b8efcb7fd77a849c9f9dc163130473b7f16",
    "structurizr-python": "31f1dcadb3ff113d8a77ce132657237ea01c307b",
    "home-assistant": "e4b01b65d306cf4ffcd692b9eb7c7d2ce4f794e4",
}

# home-assistant's ADRs live in a separate repo (census §5).
GOLD_ADR_PINS: dict[str, str] = {
    "home-assistant": "0c4f7dbf21c9e1279bea23a1eb2f9ab295d0e9e9",
}


def gold_path(repo_id: str) -> Path:
    """repo id -> its gold file (python-tuf -> python_tuf_gold.json)."""
    return GOLD_DIR / f"{repo_id.replace('-', '_')}_gold.json"


def load_gold_edges(gold_file: Path) -> list[ConstraintEdge]:
    """Gold JSON -> ConstraintEdges. Every field the seed carries comes from here."""
    rows = json.loads(Path(gold_file).read_text())
    edges: list[ConstraintEdge] = []
    for adr in rows:
        for constraint in adr["constraints"]:
            edges.append(ConstraintEdge(
                subject=constraint["subject"],
                predicate=PredicateType(constraint["predicate"]),
                object=constraint["object"],
                justification=constraint["justification"],
                adr_id=adr["adr_id"],
                adr_path=adr["adr_path"],
                # #190: carry scope on the wire. Missing or invalid -> RUNTIME,
                # matching the Neo4j reader (connector.py); a dropped TOOLING
                # edge would come back enforced (#159).
                scope=ConstraintScope(constraint.get("scope", "runtime")),
            ))
    return edges


def dump_gold_edges(path: Path, edges) -> None:
    """ConstraintEdges -> the gold JSON shape, grouped by (adr_id, adr_path).

    The writer twin of `load_gold_edges`, for `cpt seed build --constraints-out`
    (#190): the replay caches the resolver's rule set per ADR version and loads
    it back on later samples. `scope` rides along so TOOLING edges stay TOOLING.
    """
    groups: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for edge in edges:
        key = (edge.adr_id, edge.adr_path)
        if key not in groups:
            groups[key] = {"adr_id": edge.adr_id, "adr_path": edge.adr_path, "constraints": []}
            order.append(key)
        groups[key]["constraints"].append({
            "subject": edge.subject,
            "predicate": edge.predicate.value,
            "object": edge.object,
            "justification": edge.justification,
            "scope": edge.scope.value,
        })
    Path(path).write_text(json.dumps([groups[k] for k in order], indent=2) + "\n")


def triples(edges) -> list[tuple[str, str, str, str]]:
    """Comparable identity of an edge list: (adr_id, predicate, subject, object)."""
    return sorted((e.adr_id, e.predicate.value, e.subject, e.object) for e in edges)


def gold_triples(repo_id: str) -> list[tuple[str, str, str, str]]:
    return triples(load_gold_edges(gold_path(repo_id)))


def triple_differences(expected, actual) -> tuple[list, list]:
    """(missing, extra) as sorted lists, so a disagreement is named, not counted."""
    missing = sorted((Counter(expected) - Counter(actual)).elements())
    extra = sorted((Counter(actual) - Counter(expected)).elements())
    return missing, extra
