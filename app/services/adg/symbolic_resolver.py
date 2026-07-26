"""Symbolic Constraint Resolver (ADR 008 + prose model).

Resolves SymbolicConstraints against the ADG via substring/prefix matching,
producing ConstraintEdges ready for merge.
"""
from __future__ import annotations

import logging

from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    FQNKind,
    FQNNode,
    PredicateType,
    SymbolicConstraint,
)

log = logging.getLogger(__name__)


def _prose_match(prose: str, candidates: list[FQNNode]) -> list[FQNNode]:
    """Match a prose subject/object against ADG nodes.

    Strategy (in priority order):
    1. Exact FQN match: prose equals a node's full FQN string
    2. Prefix match: prose matches the start of a node's FQN (e.g., "services" matches "app.services")
    3. Substring match: prose is contained in the last segment of a node's FQN (case-insensitive)
    """
    if not candidates:
        return []

    prose_lower = prose.lower()

    # 1. Exact match
    exact = [n for n in candidates if str(n.fqn) == prose]
    if exact:
        return exact

    # 2. Prefix match: prose matches start of dotted FQN segment
    # e.g., "services" matches "app.services", "app.auth" matches "app.auth.middleware"
    prefix = [n for n in candidates if str(n.fqn).endswith("." + prose_lower) or str(n.fqn) == prose_lower]
    # Also match if prose is a full prefix of the FQN (e.g., "app" matches "app.services")
    prefix += [n for n in candidates if str(n.fqn).lower().startswith(prose_lower + ".")]
    # Deduplicate
    seen = set()
    deduped = []
    for n in prefix:
        if id(n) not in seen:
            seen.add(id(n))
            deduped.append(n)
    if deduped:
        return deduped

    # 3. Substring match on last segment (case-insensitive)
    substring = []
    for node in candidates:
        short_name = (node.fqn.parts[-1] if node.fqn.parts else "").lower()
        if prose_lower in short_name or short_name in prose_lower:
            substring.append(node)
    if substring:
        return substring

    return []


def resolve_symbolic_constraints(
    symbolic: list[SymbolicConstraint], adg: ADG,
    project_root: Path | None = None,
) -> list[ConstraintEdge]:
    """Resolve SymbolicConstraints against the ADG into ConstraintEdges.

    For each SymbolicConstraint:
    1. Match subject/object prose against ADG nodes
    2. External dependencies (dependency predicates with no ADG match) create EXTERNAL nodes
    3. No match: skip and log

    project_root: optional path to repo root for dev-tool classification.
    """
    from pathlib import Path
    from services.adg.merge import add_external_nodes, _classify_external_role, _load_dev_packages_from_config

    extra_dev_packages = _load_dev_packages_from_config(project_root)
    adg = add_external_nodes(adg, project_root=project_root)
    edges: list[ConstraintEdge] = []

    for sym_constraint in symbolic:
        pred_value = sym_constraint.predicate.value

        subject_nodes = _prose_match(sym_constraint.subject, adg.nodes)
        object_nodes = _prose_match(sym_constraint.object, adg.nodes)

        # External dependency shortcut: if object has no ADG match and this is
        # a dependency predicate, create an EXTERNAL node
        if not object_nodes and pred_value in ("requires_dependency", "prohibits_dependency"):
            ext_fqn = FQN.from_dotted(sym_constraint.object)
            ext_role = _classify_external_role(str(ext_fqn), extra_dev_packages)
            ext_node = FQNNode(
                fqn=ext_fqn,
                kind=FQNKind.EXTERNAL,
                file_path="",
                line_start=-1,
                line_end=-1,
                role=ext_role,
            )
            adg = ADG(
                nodes=adg.nodes + [ext_node],
                edges=adg.edges,
                constraint_edges=adg.constraint_edges,
            )
            object_nodes = [ext_node]

        if not subject_nodes:
            log.warning(
                "resolve: [%s] subject '%s' matched nothing, skipping",
                sym_constraint.adr_id, sym_constraint.subject,
            )
            continue

        if not object_nodes:
            log.warning(
                "resolve: [%s] object '%s' matched nothing, skipping",
                sym_constraint.adr_id, sym_constraint.object,
            )
            continue

        # Module nodes get wildcard suffix so CPT matches descendants;
        # non-module (class, function, external) stay exact.
        def _pattern(n: FQNNode) -> str:
            return str(n.fqn) + (".*" if n.kind == FQNKind.MODULE else "")

        subject_fqns = sorted({_pattern(n) for n in subject_nodes})
        object_fqns = sorted({_pattern(n) for n in object_nodes})

        for subj_fqn in subject_fqns:
            for obj_fqn in object_fqns:
                # Skip self-loops
                if subj_fqn == obj_fqn:
                    continue
                edge = ConstraintEdge(
                    subject=subj_fqn,
                    predicate=sym_constraint.predicate,
                    object=obj_fqn,
                    justification=sym_constraint.justification,
                    adr_id=sym_constraint.adr_id,
                    adr_path=sym_constraint.adr_path,
                )
                edges.append(edge)

        log.info(
            "resolve: [%s] '%s' -[%s]-> '%s'",
            sym_constraint.adr_id,
            sym_constraint.subject, sym_constraint.predicate.value,
            sym_constraint.object,
        )

    return edges