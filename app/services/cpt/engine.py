from __future__ import annotations

import logging
from dataclasses import dataclass, field

from services.fqn import FQN
from services.models import ADG, ChangedFQN, ConstraintEdge, DependencyRole, DiffResult, Edge, FQNKind, PredicateType
from services.cpt.resolution import Violation, resolve, suppress_outweighed_prohibits, suppress_outweighed_requires
from services.resolver import MatchStatus, fqn_matches_pattern
from collections.abc import Iterable
from collections import deque, defaultdict

log = logging.getLogger(__name__)

_PRIORITY = {MatchStatus.EXACT: 3, MatchStatus.WILDCARD: 2}

_DEPENDENCY_EDGE_KINDS = frozenset({"IMPORTS", "CALLS", "INHERITS"})


def _outgoing_dependency_edges(fqn_str: str, adjacency: dict[str, list[Edge]]) -> list[dict]:
    # ponytail: uncapped; cap if large modules flood the reviewer context
    return [
        {"kind": edge.kind, "target": edge.target}
        for edge in adjacency.get(fqn_str, ())
        if edge.kind in _DEPENDENCY_EDGE_KINDS
    ]


@dataclass
class CPTResult:
    violations: list[Violation] = field(default_factory=list)
    orphans: list[ConstraintEdge] = field(default_factory=list)
    self_loop_constraints: list[ConstraintEdge] = field(default_factory=list)


@dataclass
class MatchedConstraint:
    constraint: ConstraintEdge
    subject_matches: list[tuple[FQN, MatchStatus]]
    object_matches: list[tuple[FQN, MatchStatus]]


def _build_adjacency(edges: Iterable[Edge]) -> dict[str, list[Edge]]:
    adjacency: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source].append(edge)
    return adjacency


def _enclosing_module_map(adg: ADG) -> dict[str, str]:
    """function/method FQN -> enclosing module FQN (nearest MODULE ancestor)."""
    module_kinds = {str(node.fqn) for node in adg.nodes if node.kind == FQNKind.MODULE}
    scope: dict[str, str] = {}
    for node in adg.nodes:
        if node.kind not in (FQNKind.FUNCTION, FQNKind.METHOD):
            continue
        parts = str(node.fqn).split(".")
        for i in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in module_kinds:
                scope[str(node.fqn)] = candidate
                break
    return scope


def _reachable_paths(
    start: str,
    adjacency: dict[str, list[Edge]],
    kinds: set[str],
    node_roles: dict[str, DependencyRole] | None = None,
    skip_roles: set[DependencyRole] | None = None,
    seed_module: str | None = None,
) -> dict[str, list[Edge]]:
    """BFS: O(V+E) per node. Value is the shortest edge-path from start to that node.
    Skips edges whose target has a role in skip_roles.
    seed_module: module whose module-level edges (all kinds except CONTAINS) are
    visible from start's function scope: a function inherits its module's imports,
    not its siblings' bodies.
    # ponytail: only the shortest path per target is kept; a longer alternate path is never reported."""
    paths: dict[str, list[Edge]] = {}
    queue: deque[str] = deque([start])

    if seed_module:
        for edge in adjacency.get(seed_module, ()):
            if edge.kind not in kinds or edge.kind == "CONTAINS":
                continue
            if node_roles and skip_roles and node_roles.get(edge.target) in skip_roles:
                continue
            if edge.target not in paths:
                paths[edge.target] = [edge]
                queue.append(edge.target)

    while queue:
        current = queue.popleft()
        for edge in adjacency.get(current, ()):
            if edge.kind not in kinds:
                continue
            if node_roles and skip_roles:
                target_role = node_roles.get(edge.target)
                if target_role and target_role in skip_roles:
                    continue
            if edge.target in paths:
                continue
            paths[edge.target] = paths.get(current, []) + [edge]
            queue.append(edge.target)

    return paths


def _path_excused(path: list[Edge], object_str: str, requires: list[ConstraintEdge]) -> bool:
    """True when every intermediary on the path is itself required to depend on the
    object ('via connector' pattern): services -> connector -> db is allowed when a
    requires constraint covers the connector for db."""
    if len(path) <= 1:
        return False
    object_fqn = FQN.from_dotted_safe(object_str)
    for intermediary in [edge.source for edge in path[1:]]:
        intermediary_fqn = FQN.from_dotted_safe(intermediary)
        if not any(
            fqn_matches_pattern(intermediary_fqn, require.subject) != MatchStatus.NO_MATCH
            and fqn_matches_pattern(object_fqn, require.object) != MatchStatus.NO_MATCH
            for require in requires
        ):
            return False
    return True


def match_constraints(adg: ADG) -> dict[int, MatchedConstraint]:
    """
    match all constraint with all nodes O(c x n) 
    TODO: do we need to check all constraints? optimize?
    """
    matched: dict[int, MatchedConstraint] = {}
    for constraint in adg.constraint_edges:
        subject_matches: list[tuple[FQN, MatchStatus]] = []
        object_matches: list[tuple[FQN, MatchStatus]] = []
        all_fqns = {node.fqn for node in adg.nodes}
        for fqn in all_fqns:
            subj_status = fqn_matches_pattern(fqn, constraint.subject)
            if subj_status != MatchStatus.NO_MATCH:
                subject_matches.append((fqn, subj_status))
            obj_status = fqn_matches_pattern(fqn, constraint.object)
            if obj_status != MatchStatus.NO_MATCH:
                object_matches.append((fqn, obj_status))
        # Skip constraints where either bucket is empty (orphan)
        if subject_matches and object_matches:
            matched[id(constraint)] = MatchedConstraint(
                constraint=constraint,
                subject_matches=subject_matches,
                object_matches=object_matches,
            )
    return matched


def check_structural_predicates(
    matched_constraints: dict[int, MatchedConstraint],
    adjacency: dict[str, list[Edge]],
    node_roles: dict[str, DependencyRole] | None = None,
    module_scope: dict[str, str] | None = None,
) -> list[Violation]:
    """
    PROHIBITS_*: evaluate once per constraint, no changed_fqn needed.
    TODO: cache BFS result, all prohibit can reuse same full graph reachability
    """
    violations: list[Violation] = []
    requires_by_predicate: dict[str, list[ConstraintEdge]] = {}
    for matched_constraint in matched_constraints.values():
        constraint_pred = matched_constraint.constraint.predicate
        if constraint_pred in (PredicateType.REQUIRES_DEPENDENCY, PredicateType.REQUIRES_IMPLEMENTATION):
            requires_by_predicate.setdefault(constraint_pred.value, []).append(matched_constraint.constraint)

    for matched_constraint in matched_constraints.values():
        pred = matched_constraint.constraint.predicate

        if pred not in (PredicateType.PROHIBITS_DEPENDENCY, PredicateType.PROHIBITS_IMPLEMENTATION):
            continue

        kinds = {"CONTAINS", "IMPORTS", "CALLS", "INHERITS"} if pred == PredicateType.PROHIBITS_DEPENDENCY else {"CONTAINS", "CALLS", "INHERITS"}
        label = "has dependency path to" if pred == PredicateType.PROHIBITS_DEPENDENCY else "implements"
        counterpart = PredicateType.REQUIRES_DEPENDENCY.value if pred == PredicateType.PROHIBITS_DEPENDENCY else PredicateType.REQUIRES_IMPLEMENTATION.value
        excusing_requires = requires_by_predicate.get(counterpart, [])

        # ponytail: DEV_TOOL objects are not architecturally meaningful for prohibits
        non_dev_object_matches = [
            (fqn, status) for fqn, status in matched_constraint.object_matches
            if not (node_roles and node_roles.get(str(fqn)) == DependencyRole.DEV_TOOL)
        ]
        if not non_dev_object_matches:
            continue

        for subject_fqn, subject_status in matched_constraint.subject_matches:
            subject_str = str(subject_fqn)
            # function/method subjects cannot see module-level edges from their own
            # frontier; re-anchor to the enclosing module so its imports count and
            # the violation reports once at module level (issue 115, B1)
            scope_str = (module_scope or {}).get(subject_str, subject_str)
            paths = _reachable_paths(scope_str, adjacency, kinds, node_roles=node_roles, skip_roles={DependencyRole.DEV_TOOL})
            for object_fqn, object_status in non_dev_object_matches:
                higher = subject_status if _PRIORITY[subject_status] >= _PRIORITY[object_status] else object_status
                object_str = str(object_fqn)
                for target, path in paths.items():
                    if not (target == object_str or target.startswith(object_str + ".")):
                        continue
                    if _path_excused(path, object_str, excusing_requires):
                        continue
                    path_summary = " -> ".join(f"{edge.kind} {edge.target}" for edge in path)
                    violations.append(Violation(
                        constraint=matched_constraint.constraint,
                        changed_fqn=subject_fqn,
                        matched_fqn=FQN.from_dotted_safe(scope_str),
                        match_status=higher,
                        evidence=f"{scope_str} {label} {object_str} via {path_summary}",
                        change_type="structural",
                        path_hops=[{"kind": edge.kind, "target": edge.target} for edge in path],
                    ))
                    break
    return violations


def check_change_triggered_predicates(
    matched_constraints: dict[int, MatchedConstraint],
    adjacency: dict[str, list[Edge]],
    changed_fqns: list[ChangedFQN],
    node_roles: dict[str, DependencyRole] | None = None,
    module_scope: dict[str, str] | None = None,
) -> list[Violation]:
    """
    REQUIRES_*: evaluate per changed_fqn, pre-filtered by subject_matches.
    TODO: 2-hops traversal?
    """
    violations: list[Violation] = []
    for changed in changed_fqns:
        changed_str = str(changed.fqn)
        for matched_constraint in matched_constraints.values():
            pred = matched_constraint.constraint.predicate
            if pred not in (PredicateType.REQUIRES_DEPENDENCY, PredicateType.REQUIRES_IMPLEMENTATION):
                continue

            if matched_constraint.constraint.subject.endswith(".*"):
                prefix = matched_constraint.constraint.subject[:-2]
                # Check if the changed FQN falls under this wildcard prefix
                if not (changed_str == prefix or changed_str.startswith(prefix + ".")):
                    continue
                # Package-root BFS finds dependencies through sibling modules
                # For function-level FQNs that lack IMPORTS,
                # walk up to enclosing module first.
                relevant_subjects = [(changed.fqn, MatchStatus.WILDCARD)]
            else:
                relevant_subjects = [
                    (subject_fqn, subject_status) for subject_fqn, subject_status in matched_constraint.subject_matches
                    if subject_fqn == changed.fqn or changed_str.startswith(str(subject_fqn) + ".")
                ]

            if not relevant_subjects:
                continue

            kinds = {"CONTAINS", "IMPORTS", "CALLS", "INHERITS"} if pred == PredicateType.REQUIRES_DEPENDENCY else {"CONTAINS", "CALLS", "INHERITS"}
            label = "has no dependency on any module matching" if pred == PredicateType.REQUIRES_DEPENDENCY else "does not implement any module matching"
            # ponytail: DEV_TOOL objects are not architecturally meaningful for requires
            non_dev_object_matches = [
                (fqn, status) for fqn, status in matched_constraint.object_matches
                if not (node_roles and node_roles.get(str(fqn)) == DependencyRole.DEV_TOOL)
            ]
            if not non_dev_object_matches:
                continue
            for subject_fqn, subject_status in relevant_subjects:
                subject_str = str(subject_fqn)
                # function-scope frontier inherits the enclosing module's
                # module-level edges, so a module that already satisfies the
                # dependency does not over-trigger the function (issue 115, B2)
                reachable = _reachable_paths(
                    subject_str, adjacency, kinds,
                    node_roles=node_roles, skip_roles={DependencyRole.DEV_TOOL},
                    seed_module=(module_scope or {}).get(subject_str),
                )
                object_reachable = False
                for object_fqn, _ in matched_constraint.object_matches:
                    object_str = str(object_fqn)
                    for reachable_object_str in reachable:
                        if reachable_object_str == object_str or reachable_object_str.startswith(object_str + "."):
                            object_reachable = True
                            break
                    if object_reachable:
                        break
                if not object_reachable:
                    highest_status = subject_status
                    for _, object_status in matched_constraint.object_matches:
                        if _PRIORITY[object_status] > _PRIORITY[highest_status]:
                            highest_status = object_status

                    changed_module_str = str(changed.enclosing_module)
                    scope_snapshots = [
                        {"scope": "changed", "fqn": changed_str, "outgoing": _outgoing_dependency_edges(changed_str, adjacency)}
                    ]
                    if changed_module_str != changed_str:
                        scope_snapshots.append(
                            {"scope": "enclosing_module", "fqn": changed_module_str, "outgoing": _outgoing_dependency_edges(changed_module_str, adjacency)}
                        )
                    violations.append(Violation(
                        constraint=matched_constraint.constraint,
                        changed_fqn=changed.fqn,
                        matched_fqn=subject_fqn,
                        match_status=highest_status,
                        evidence=f"{subject_str} {label} {matched_constraint.constraint.object}",
                        change_type=changed.change_type,
                        scope_snapshots=scope_snapshots,
                    ))
    return violations


def detect(diff_result: DiffResult, adg: ADG) -> CPTResult:
    adjacency = _build_adjacency(adg.edges)
    node_roles = {str(node.fqn): node.role for node in adg.nodes}

    # filter self-loop constraints (subject == object), surface as informational
    self_loop_constraints: list[ConstraintEdge] = [
        constraint for constraint in adg.constraint_edges if constraint.subject == constraint.object
    ]

    if self_loop_constraints:
        log.warning(
            "detect: %d self-loop constraint(s) filtered: %s",
            len(self_loop_constraints),
            [(constraint.adr_id, constraint.subject) for constraint in self_loop_constraints],
        )

    safe_edges = [constraint for constraint in adg.constraint_edges if constraint.subject != constraint.object] # filter self loop
    safe_adg = ADG(nodes=adg.nodes, edges=adg.edges, constraint_edges=safe_edges)
    matched = match_constraints(safe_adg)

    all_violations: list[Violation] = []
    all_violations.extend(check_structural_predicates(matched, adjacency, node_roles=node_roles))
    all_violations.extend(check_change_triggered_predicates(matched, adjacency, diff_result.changed_fqns, node_roles=node_roles))

    violations = resolve(all_violations)

    active_requires: list[ConstraintEdge] = []
    for match_constraint in matched.values():
        if match_constraint.constraint.predicate.value.startswith("requires_"):
            active_requires.append(match_constraint.constraint)
    violations = suppress_outweighed_prohibits(violations, active_requires)

    active_prohibits: list[ConstraintEdge] = []
    for match_constraint in matched.values():
        if match_constraint.constraint.predicate.value.startswith("prohibits_"):
            active_prohibits.append(match_constraint.constraint)
    violations = suppress_outweighed_requires(violations, active_prohibits)

    node_by_fqn = {str(node.fqn): node for node in adg.nodes}
    for violation in violations:
        node = node_by_fqn.get(str(violation.changed_fqn))
        if node:
            violation.location = {"file_path": node.file_path, "line_start": node.line_start, "line_end": node.line_end}
        for hop in violation.path_hops or ():
            hop_node = node_by_fqn.get(hop["target"])
            if hop_node:
                hop["file_path"] = hop_node.file_path

    orphans: list[ConstraintEdge] = []
    for constraint in adg.constraint_edges:
        if id(constraint) not in matched:
            orphans.append(constraint)

    return CPTResult(violations=violations, orphans=orphans, self_loop_constraints=self_loop_constraints)


if __name__ == "__main__":
    from services.models import ADG, ChangedFQN, ConstraintEdge, DiffResult, Edge, FQNKind, FQNNode, PredicateType

    adg = ADG(
        nodes=[
            FQNNode(fqn=FQN.from_dotted_safe("app.service.UserService"), kind=FQNKind.CLASS, file_path="app/service.py", line_start=1, line_end=10),
            FQNNode(fqn=FQN.from_dotted_safe("app.repo.UserRepo"), kind=FQNKind.CLASS, file_path="app/repo.py", line_start=1, line_end=10),
        ],
        edges=[
            Edge(source="app.service.UserService", target="app.repo.UserRepo", kind="CALLS"),
            Edge(source="app.service.UserService", target="app.repo.UserRepo", kind="IMPORTS"),
        ],
        constraint_edges=[
            ConstraintEdge(
                subject="app.service.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.repo.*",
                justification="Services must not depend on repositories directly",
                adr_id="ADR-001",
                adr_path="docs/adr/001.md",
            ),
        ],
    )

    diff = DiffResult(
        to_sha="abc123",
        changed_fqns=[
            ChangedFQN(
                fqn=FQN.from_dotted_safe("app.service.UserService"),
                change_type="modified",
                file_path="app/service.py",
                enclosing_module=FQN.from_dotted_safe("app.service"),
            ),
        ],
    )

    result = detect(diff, adg)
    for v in result.violations:
        print(f"  {v.constraint.predicate.value}: {v.evidence}")