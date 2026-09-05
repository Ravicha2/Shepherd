from __future__ import annotations

from dataclasses import dataclass

from services.fqn import FQN
from services.resolver import MatchStatus, fqn_matches_pattern
from services.models import ConstraintEdge


def _subject_covers(subject_pattern: str, fqn: FQN) -> bool:
    # ponytail: subject-keyed suppression, see issue #105
    if fqn_matches_pattern(fqn, subject_pattern) != MatchStatus.NO_MATCH:
        return True
    # wildcard pattern X.* also covers X itself (the containing module),
    # since a prohibit can fire on X via transitive reach through X's children
    if subject_pattern.endswith(".*") and str(fqn) == subject_pattern[:-2]:
        return True
    return False


@dataclass
class Violation:
    constraint: ConstraintEdge
    changed_fqn: FQN
    matched_fqn: FQN
    match_status: MatchStatus
    evidence: str
    change_type: str
    # Informational provenance for reviewer context; never part of identity/dismissal
    location: dict | None = None           # {"file_path", "line_start", "line_end"} of changed_fqn's node
    path_hops: list[dict] | None = None    # prohibits: traversal from subject to object, [{"kind", "target", "file_path"?}]
    scope_snapshots: list[dict] | None = None  # requires: [{"scope", "fqn", "outgoing": [{"kind", "target"}]}]


def resolve(violations: list[Violation]) -> list[Violation]:
    """Deduplicate violations and suppress lower-specificity conflicts."""
    seen: set[tuple[str, str]] = set()
    deduped_violation: list[Violation] = []

    for violation in violations:
        # adr_id is part of identity: two ADRs can carry the same live mandate
        # (same subject/predicate/object); each attribution is its own finding (#125)
        key = (violation.constraint.adr_id, violation.constraint.subject, violation.constraint.predicate, violation.constraint.object, str(violation.matched_fqn))
        if key not in seen:
            seen.add(key)
            deduped_violation.append(violation)

    # Module-level dedup: parent matched_fqn covers child for same constraint
    # O(n²) per constraint group, fine for typical violation counts
    by_constraint: dict[tuple, list[int]] = {}
    for i, violation in enumerate(deduped_violation):
        constraint_key = (violation.constraint.adr_id, violation.constraint.subject, violation.constraint.predicate, violation.constraint.object)
        by_constraint.setdefault(constraint_key, []).append(i)

    to_remove: set[int] = set()
    for indices in by_constraint.values():
        for i in indices:
            if i in to_remove:
                continue
            parent_prefix = str(deduped_violation[i].matched_fqn) + "."
            for j in indices:
                if j != i and j not in to_remove and str(deduped_violation[j].matched_fqn).startswith(parent_prefix):
                    to_remove.add(j)

    surviving: list[Violation] = []
    for i, violation in enumerate(deduped_violation):
        if i not in to_remove:
            surviving.append(violation)
    deduped_violation = surviving

    suppress: set[int] = set()

    for i, violation_i in enumerate(deduped_violation):
        for j, violation_j in enumerate(deduped_violation):
            if i == j or i in suppress or j in suppress:
                continue

            if violation_i.constraint.object != violation_j.constraint.object:
                continue

            violation_i_prohibit = violation_i.constraint.predicate.value.startswith("prohibits_")
            violation_i_require = violation_i.constraint.predicate.value.startswith("requires_")
            violation_j_prohibit = violation_j.constraint.predicate.value.startswith("prohibits_")
            violation_j_require = violation_j.constraint.predicate.value.startswith("requires_")

            if violation_i_prohibit and violation_j_require:
                if _subject_covers(violation_j.constraint.subject, violation_i.matched_fqn):
                    if violation_j.constraint.specificity > violation_i.constraint.specificity:
                        suppress.add(i)
                if _subject_covers(violation_i.constraint.subject, violation_j.matched_fqn):
                    if violation_i.constraint.specificity > violation_j.constraint.specificity:
                        suppress.add(j)

            elif violation_i_require and violation_j_prohibit:
                if _subject_covers(violation_i.constraint.subject, violation_j.matched_fqn):
                    if violation_i.constraint.specificity > violation_j.constraint.specificity:
                        suppress.add(j)
                if _subject_covers(violation_j.constraint.subject, violation_i.matched_fqn):
                    if violation_j.constraint.specificity > violation_i.constraint.specificity:
                        suppress.add(i)

    return [violation for i, violation in enumerate(deduped_violation) if i not in suppress]


def suppress_outweighed_prohibits(
    violations: list[Violation],
    active_requires: list[ConstraintEdge],
) -> list[Violation]:
    """Remove prohibits violations outweighed by a higher-specificity requires on the same object AND whose matched_fqn falls under the require's subject."""
    return [
        violation for violation in violations
        if not (
            violation.constraint.predicate.value.startswith("prohibits_")
            and any(
                requires.object == violation.constraint.object
                and requires.specificity > violation.constraint.specificity
                and _subject_covers(requires.subject, violation.matched_fqn)
                for requires in active_requires
            )
        )
    ]


def suppress_outweighed_requires(
    violations: list[Violation],
    active_prohibits: list[ConstraintEdge],
) -> list[Violation]:
    """Remove requires violations outweighed by a higher-specificity or newer prohibits on the same object AND whose matched_fqn falls under the prohibit's subject."""
    return [
        violation for violation in violations
        if not (
            violation.constraint.predicate.value.startswith("requires_")
            and any(
                prohibits.object == violation.constraint.object
                and (prohibits.specificity > violation.constraint.specificity or (prohibits.specificity == violation.constraint.specificity and prohibits.adr_id > violation.constraint.adr_id))
                and _subject_covers(prohibits.subject, violation.matched_fqn)
                for prohibits in active_prohibits
            )
        )
    ]