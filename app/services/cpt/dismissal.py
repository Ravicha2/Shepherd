"""Dismissal model and identity key logic for violation persistence.

ADR 012: Dismissals-Only Persistence Model.
Identity key: (subject, predicate, object, adr_id, code_fingerprint) — #186.
A dismissal is a judgement about a *code state*, not a location: it applies
only while the violation's causal code surface (governed module + evidence
route) still hashes to the recorded fingerprint. matched_fqn is provenance
only: the evidence location moves under unrelated churn, so it must not be
identity. Legacy rows recorded before #186 carry no fingerprint and never
match — the violations they suppressed re-surface once for re-review.
Short ID: first 5 hex chars of SHA-256(identity_key).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from services.cpt.resolution import Violation, governed_module


def compute_identity_key(subject: str, predicate: str, object: str, adr_id: str, code_fingerprint: str) -> str:
    """Canonical identity string for a violation/dismissal. Pipe-delimited."""
    return f"{subject}|{predicate}|{object}|{adr_id}|{code_fingerprint}"


def compute_identity_hash(identity_key: str) -> str:
    """SHA-256 hex digest of the identity key."""
    return hashlib.sha256(identity_key.encode("utf-8")).hexdigest()


def compute_short_id(identity_hash: str) -> str:
    """First 5 hex chars of the identity hash. ponytail: 5-char hex, upgrade if collisions observed."""
    return identity_hash[:5]


def violation_identity(violation: Violation) -> str:
    """Identity key string from a Violation object."""
    # "none" for fingerprint-less violations: deterministic short IDs for
    # display, but no dismissal can ever match it (from_violation refuses
    # to record a dismissal without a fingerprint).
    return compute_identity_key(
        subject=violation.constraint.subject,
        predicate=violation.constraint.predicate.value,
        object=violation.constraint.object,
        adr_id=violation.constraint.adr_id,
        code_fingerprint=violation.code_fingerprint or "none",
    )


def violation_short_id(violation: Violation) -> str:
    """Short ID (5 hex chars) for a Violation."""
    return compute_short_id(compute_identity_hash(violation_identity(violation)))


@dataclass
class Dismissal:
    """A persisted dismissal of a CPT violation.

    Flat node in Neo4j, decoupled from FQNNode/ConstraintEdge
    to survive ADG updates. Applies only while the code fingerprint it was
    recorded against still holds (#186).
    """

    short_id: str
    identity_hash: str
    subject: str
    predicate: str
    object: str
    adr_id: str
    code_fingerprint: str | None = None  # None = pre-#186 legacy row: never matches
    matched_fqn: str = ""                # provenance only, not identity
    governed_fqn: str = ""               # provenance only, not identity
    dismissed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_violation(cls, violation: Violation) -> Dismissal:
        if violation.code_fingerprint is None:
            raise ValueError(
                "cannot dismiss: violation has no code fingerprint "
                "(governed module or anchor not in the graph)"
            )
        id_key = violation_identity(violation)
        id_hash = compute_identity_hash(id_key)
        return cls(
            short_id=compute_short_id(id_hash),
            identity_hash=id_hash,
            subject=violation.constraint.subject,
            predicate=violation.constraint.predicate.value,
            object=violation.constraint.object,
            adr_id=violation.constraint.adr_id,
            code_fingerprint=violation.code_fingerprint,
            matched_fqn=str(violation.matched_fqn),
            governed_fqn=str(governed_module(violation)),
        )


def filter_dismissed(violations: list[Violation], dismissals: list[Dismissal]) -> list[Violation]:
    """Remove violations whose (constraint, code state) matches a dismissal.

    A dismissal suppresses only while the code it judged still stands: a
    material change at the governed module or evidence route changes the
    fingerprint and the violation re-surfaces for review (#186). Unrelated
    churn — rebuilds, renames, neighbours moving — keeps the fingerprint
    and the dismissal valid (#181 §8, ADR 012). Legacy rows without a
    fingerprint never match.
    """
    dismissed_hashes = {d.identity_hash for d in dismissals if d.code_fingerprint}
    return [
        v for v in violations
        if compute_identity_hash(violation_identity(v)) not in dismissed_hashes
    ]