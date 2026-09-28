"""Commit update orchestration: full structural rebuild preserving constraints and dismissals.

Per ADR 013: wipe structural data, re-parse repo, re-insert constraints,
recompute specificity, re-run CPT detection, filter dismissals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from services.adg.treesitter import parse_repo
from services.cpt.dismissal import Dismissal, filter_dismissed
from services.cpt.engine import CPTResult, Violation, detect as cpt_detect
from services.cpt.diff_processor import augmented, process_diff
from services.cpt.git_adapter import GitAdapter
from services.graph.connector import GraphStore
from services.models import ADG, ChangedFQN, Diff, ConstraintEdge, DiffResult, FileChange, FQNNode
from services.pipeline import adg_with_specificity

log = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    violations: list[Violation]
    orphans: list[ConstraintEdge]
    self_loop_constraints: list[ConstraintEdge]
    changed_file_list: list[FileChange]
    changed_fqns: list[ChangedFQN]
    dismissals_applied: int
    constraint_edges_preserved: int
    to_sha: str
    from_sha: str | None


def merge_preserved_constraints(adg: ADG, constraint_edges: list[ConstraintEdge], project_root: Path | None = None) -> ADG:
    """Merge preserved constraint edges into a fresh ADG.

    Creates EXTERNAL nodes for any constraint endpoint FQN not present in
    the ADG. Returns a new ADG with constraint_edges attached.

    project_root is accepted for API compatibility but not used here;
    this function replaces the LLM-based merge_constraint_edges step with
    a direct merge of already-resolved constraint edges.
    """
    # Wildcard patterns (users.views.*) are not concrete FQNs; resolve to the
    # base namespace. with_nodes drops the ones already in the graph and the
    # duplicates. Note the role: this path never classified, so these used to
    # land as INTERNAL; FQNNode.external defaults them to UNKNOWN.
    endpoints = [
        raw_fqn.removesuffix(".*")
        for ce in constraint_edges
        for raw_fqn in (ce.subject, ce.object)
    ]
    new_nodes = [FQNNode.external(fqn_str) for fqn_str in endpoints if fqn_str]

    return adg.with_nodes(*new_nodes).with_constraints(*constraint_edges)


def commit_update(
    store: GraphStore,
    repo_path: Path,
    to_sha: str | None = None,
) -> UpdateResult:
    """Orchestrate the full commit update flow per ADR 013.

    1. Guard: constraint edges must exist (user must run seed build first)
    2. Load dismissals
    3. Wipe structural data (constraint edges removed, caller re-inserts)
    4. Re-parse repo
    5. Store structural nodes + edges
    6. Re-insert constraint edges (MERGE finds real code nodes)
    7. Merge preserved constraints in-memory
    8. Compute specificity
    9. Get commit diff + process
    10. CPT detect
    11. Filter dismissals
    """
    # 1. Guard: constraint edges must exist
    constraint_edges = store.load_all_constraint_edges()
    if not constraint_edges:
        raise RuntimeError("No ADG found. Run 'seed build' first.")

    # 2. Load dismissals (survive the wipe because :Dismissal, not :FQNNode)
    dismissals = store.load_dismissals()

    # 3. Wipe structural data
    store.delete_structural_data()

    # 4. Re-parse repo
    adg = parse_repo(repo_path)

    # 5. Store structural nodes + edges (MERGE upgrades EXTERNAL placeholders)
    for node in adg.nodes:
        store.store_node(node)
    for edge in adg.edges:
        store.store_edge(edge)

    # 6. Re-insert constraint edges (MERGE finds real code nodes, EXTERNAL for orphans)
    for ce in constraint_edges:
        store.store_constraint_edge(ce)

    # 7. Merge preserved constraints in-memory (adds EXTERNAL nodes for orphans)
    merged = merge_preserved_constraints(adg, constraint_edges)

    # 8. Compute specificity
    merged = adg_with_specificity(merged)

    # 9. Get commit diff + process
    diff = GitAdapter().get_diff(repo_path, to_sha=to_sha)
    diff_result = process_diff(diff)
    merged = augmented(merged, diff)

    # 10. CPT detect
    cpt_result = cpt_detect(diff_result, merged)

    # 11. Filter dismissals
    active_violations = filter_dismissed(cpt_result.violations, dismissals)

    return UpdateResult(
        violations=active_violations,
        orphans=cpt_result.orphans,
        self_loop_constraints=cpt_result.self_loop_constraints,
        changed_file_list=diff_result.changed_files,
        changed_fqns=diff_result.changed_fqns,
        dismissals_applied=len(cpt_result.violations) - len(active_violations),
        constraint_edges_preserved=len(constraint_edges),
        to_sha=diff.to_sha,
        from_sha=diff.from_sha,
    )