from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from functools import cached_property
from types import MappingProxyType

from services.fqn import FQN


class FQNKind(Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    EXTERNAL = "external"


class DependencyRole(Enum):
    INTERNAL = "internal"
    DEV_TOOL = "dev_tool"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    UNKNOWN = "unknown"


class ADRStatus(Enum):
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ConstraintScope(Enum):
    """#136 decision (a): runtime constraints govern the import graph;
    tooling/CI constraints (linters, formatters, type checkers, doc tooling,
    test frameworks, language choice) live in pyproject/setup.cfg/noxfile and
    are out of the import graph's declared scope. Tagged, never silently
    dropped: scoring/reporting excludes them by declared scope."""

    RUNTIME = "runtime"
    TOOLING = "tooling"


@dataclass
class FQNNode:
    fqn: FQN
    kind: FQNKind
    file_path: str
    line_start: int
    line_end: int
    start_byte: int = 0
    end_byte: int = 0
    role: DependencyRole = DependencyRole.INTERNAL

    @classmethod
    def external(cls, fqn: str, role: DependencyRole = DependencyRole.UNKNOWN) -> FQNNode:
        """The ONE synthetic-EXTERNAL constructor: sentinel spans, no file.

        Every placeholder site used to hand-write these fields, and they had
        drifted apart (role silently defaulting to INTERNAL, byte spans left
        off). `role` is load-bearing, not cosmetic: engine.detect filters
        DEV_TOOL nodes out of reachability, so a mis-defaulted placeholder
        changes the answer for the same external package.
        """
        return cls(
            fqn=FQN.from_dotted(fqn),
            kind=FQNKind.EXTERNAL,
            file_path="",
            line_start=-1,
            line_end=-1,
            start_byte=0,
            end_byte=0,
            role=role,
        )


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str  # "CALLS" | "INHERITS" | "CONTAINS" | "IMPORTS"


class _FrozenSeq(tuple):
    """A tuple that names the mistake instead of just lacking the method.

    __post_init__ wraps ADG's three sequences in this, so the migration's
    characteristic slip — `adg.nodes.append(...)` — says which transform to
    reach for instead of a bare "'tuple' object has no attribute 'append'".
    """

    def append(self, *args) -> None:
        raise TypeError("ADG is frozen: build a new graph with with_nodes / with_edges / with_constraints")


def _extend(existing, extra, key) -> tuple:
    """*existing* plus the members of *extra* whose key is unseen (first wins)."""
    seen = {key(item) for item in existing}
    added = []
    for item in extra:
        k = key(item)
        if k not in seen:
            added.append(item)
            seen.add(k)
    return tuple(existing) + tuple(added)


@dataclass(frozen=True)
class ADG:
    """The architectural dependency graph, as a frozen value.

    Do NOT add `slots=True` (FQN has it; this must not). The derived indexes
    that hang off ADG are `functools.cached_property`, which needs an instance
    ``__dict__`` to memoise into — slots would silently turn every index into a
    recompute-per-access, or raise outright.
    """

    nodes: tuple[FQNNode, ...] = ()
    edges: tuple[Edge, ...] = ()
    constraint_edges: tuple[ConstraintEdge, ...] = ()

    def __post_init__(self) -> None:
        # Accepts the existing ADG(nodes=[...], edges=[...]) list-kwarg call
        # sites, then makes `adg.nodes.append(...)` a loud TypeError.
        object.__setattr__(self, "nodes", _FrozenSeq(self.nodes))
        object.__setattr__(self, "edges", _FrozenSeq(self.edges))
        object.__setattr__(self, "constraint_edges", _FrozenSeq(self.constraint_edges))

    # -- derived indexes: built once, memoised, never stale (#173) -----------
    # Nothing mutates an ADG after construction — every transform returns a NEW
    # graph — so a fresh value has a fresh index and no invalidation protocol
    # exists to get wrong. The mappings are read-only proxies for the same
    # reason: `adg.node_of[f] = ...` would corrupt a memoised index silently.
    #
    # Only the asks with several hot call sites are here. by_file,
    # module_scope, children_of, edges_of_kind, nodes_of_kind, has and node()
    # are deferred until a second consumer shows up; each is a one-line
    # cached_property at no invalidation cost.

    @cached_property
    def fqns(self) -> tuple[FQN, ...]:
        """Every node FQN, deduped and sorted by `str` — #165's process-
        independent order, which used to be a `sorted(set(...), key=str)`
        comment re-stated at every consumer. Duplicate FQNs are real: the HA
        full graph carries 88,508 nodes over 88,405 distinct FQNs."""
        return tuple(sorted({node.fqn for node in self.nodes}, key=str))

    @cached_property
    def fqn_set(self) -> frozenset[str]:
        """The FQN universe as `str`, for membership tests."""
        return frozenset(str(node.fqn) for node in self.nodes)

    @cached_property
    def node_of(self) -> Mapping[str, FQNNode]:
        """fqn -> node. Last wins on a duplicate FQN, exactly as the dict
        comprehension it replaces did."""
        return MappingProxyType({str(node.fqn): node for node in self.nodes})

    @cached_property
    def role_of(self) -> Mapping[str, DependencyRole]:
        """fqn -> role. `detect` filters DEV_TOOL targets through this, so a
        missing role would change reachability, not just a label."""
        return MappingProxyType({str(node.fqn): node.role for node in self.nodes})

    @cached_property
    def out_edges(self) -> Mapping[str, tuple[Edge, ...]]:
        """Adjacency: source fqn -> its out-edges, in graph order."""
        buckets: dict[str, list[Edge]] = defaultdict(list)
        for edge in self.edges:
            buckets[edge.source].append(edge)
        return MappingProxyType({source: tuple(edges) for source, edges in buckets.items()})

    def edges_from(self, fqn: str, *kinds: str) -> tuple[Edge, ...]:
        """Out-edges of *fqn*, optionally restricted to *kinds*: one bucket
        read instead of a scan of every edge in the graph."""
        edges = self.out_edges.get(fqn, ())
        if not kinds:
            return edges
        return tuple(edge for edge in edges if edge.kind in kinds)

    # -- lossless transforms: each returns a NEW ADG, never mutates ---------

    def replace(self, **fields) -> ADG:
        """Copy with named fields replaced.

        __post_init__ re-runs, so a transform cannot smuggle an invalid
        ConstraintEdge past its validation.
        """
        return replace(self, **fields)

    def map_constraints(self, fn) -> ADG:
        """Apply *fn* to every ConstraintEdge, returning a new ADG."""
        return self.replace(constraint_edges=tuple(fn(edge) for edge in self.constraint_edges))

    def with_nodes(self, *extra: FQNNode) -> ADG:
        """Copy with *extra nodes, deduped by fqn.

        First wins, so a real node already in the graph beats a stale EXTERNAL
        placeholder offered later.
        """
        return self.replace(nodes=_extend(self.nodes, extra, lambda n: n.fqn))

    def with_edges(self, *extra: Edge) -> ADG:
        """Copy with *extra edges, deduped by (source, target, kind)."""
        return self.replace(edges=_extend(self.edges, extra, lambda e: (e.source, e.target, e.kind)))

    def with_constraints(self, *extra: ConstraintEdge) -> ADG:
        """Copy with *extra constraints, deduped first-wins on the value key
        (adr_id, predicate, subject, object) — the same key the engine's
        matched map uses (#171), so uniqueness holds by construction."""
        return self.replace(constraint_edges=_extend(
            self.constraint_edges,
            extra,
            lambda c: (c.adr_id, c.predicate, c.subject, c.object),
        ))


@dataclass
class MDSResult:
    hubs: list[str] = field(default_factory=list)
    dominance_counts: dict[str, int] = field(default_factory=dict)


# Diff Processor data models

@dataclass
class FileChange:
    path: str
    status: str  # "added" | "modified" | "deleted" | "renamed"
    old_path: str | None = None  # for renames


@dataclass
class Diff:
    to_sha: str
    from_sha: str | None  # None for first commit
    changed_files: list[FileChange] = field(default_factory=list)
    file_contents: dict[str, bytes] = field(default_factory=dict)  # path -> content at to_sha
    from_contents: dict[str, bytes] = field(default_factory=dict)  # path -> content at from_sha


@dataclass
class ChangedFQN:
    fqn: FQN
    change_type: str  # "added" | "modified" | "deleted"
    file_path: str
    enclosing_module: FQN
    enclosing_class: FQN | None = None


@dataclass
class DiffResult:
    to_sha: str
    from_sha: str | None = None
    changed_files: list[FileChange] = field(default_factory=list)  # for ADG Update
    changed_fqns: list[ChangedFQN] = field(default_factory=list)  # for CPT


# ADR Constraint Extraction data models
class PredicateType(Enum):
    PROHIBITS_DEPENDENCY = "prohibits_dependency"
    REQUIRES_IMPLEMENTATION = "requires_implementation"
    REQUIRES_DEPENDENCY = "requires_dependency"
    PROHIBITS_IMPLEMENTATION = "prohibits_implementation"


@dataclass
class ConstraintEdge:
    """Deliberately NOT frozen, unlike ADG/Edge/FQN.

    An edge that comes back from the store never went through __post_init__
    here, so a self-loop can exist in memory after construction; making this
    frozen would leave no way to build one. The self-loop regression test
    (test_engine.py TestSelfLoopConstraint) mutates one after construction for
    exactly that reason.
    """

    subject: str
    predicate: PredicateType
    object: str
    justification: str
    adr_id: str
    adr_path: str
    specificity: float = 0.0
    scope: ConstraintScope = ConstraintScope.RUNTIME

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("subject must be non-empty")
        if not self.object:
            raise ValueError("object must be non-empty")
        if self.subject == self.object:
            raise ValueError(f"subject and object must differ, got self-loop: {self.subject}") # FIXME not always the case, recursion?
        if not self.justification:
            raise ValueError("justification must be non-empty")
        if not self.adr_id:
            raise ValueError("adr_id must be non-empty")
        if not self.adr_path:
            raise ValueError("adr_path must be non-empty")


