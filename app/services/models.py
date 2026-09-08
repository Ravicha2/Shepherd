from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

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


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str  # "CALLS" | "INHERITS" | "CONTAINS" | "IMPORTS"


@dataclass
class ADG:
    nodes: list[FQNNode] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    constraint_edges: list[ConstraintEdge] = field(default_factory=list)


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


