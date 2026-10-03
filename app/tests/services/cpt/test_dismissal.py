"""Tests for dismissal model, identity key, and filter logic (#186 semantics)."""

import pytest

from services.cpt.dismissal import (
    Dismissal,
    compute_identity_hash,
    compute_identity_key,
    compute_short_id,
    filter_dismissed,
    violation_identity,
    violation_short_id,
)
from services.cpt.resolution import Violation, governed_module
from services.fqn import FQN
from services.models import ConstraintEdge, PredicateType
from services.resolver import MatchStatus


def _make_violation(
    subject: str = "app.service.*",
    predicate: PredicateType = PredicateType.PROHIBITS_DEPENDENCY,
    object: str = "app.repo.*",
    matched_fqn: str = "app.service.UserService",
    adr_id: str = "ADR-001",
    code_fingerprint: str | None = "fp-abc123",
) -> Violation:
    return Violation(
        constraint=ConstraintEdge(
            subject=subject,
            predicate=predicate,
            object=object,
            justification="test",
            adr_id=adr_id,
            adr_path="docs/adr/001.md",
        ),
        changed_fqn=FQN.from_dotted_safe("app.service.UserService"),
        matched_fqn=FQN.from_dotted_safe(matched_fqn),
        match_status=MatchStatus.EXACT,
        evidence="test evidence",
        change_type="structural",
        code_fingerprint=code_fingerprint,
    )


class TestGovernedModule:
    """#181 §4: the dismissal anchor is the module the rule is about."""

    def test_prohibits_governed_is_changed_fqn(self):
        v = _make_violation(predicate=PredicateType.PROHIBITS_DEPENDENCY)
        assert str(governed_module(v)) == "app.service.UserService"  # changed_fqn

    def test_requires_governed_is_matched_fqn(self):
        v = _make_violation(
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            matched_fqn="app.service.OrderService",
        )
        assert str(governed_module(v)) == "app.service.OrderService"  # matched_fqn


class TestComputeIdentityKey:
    def test_deterministic(self):
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        assert key1 == key2

    def test_different_predicate(self):
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "requires_dependency", "app.external.*", "ADR-003", "fp-1")
        assert key1 != key2

    def test_different_adr_id(self):
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-004", "fp-1")
        assert key1 != key2

    def test_different_fingerprint(self):
        # #186: the code-state component is identity — a material change at
        # the governed module is a different violation for dismissal purposes.
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-2")
        assert key1 != key2

    def test_pipe_delimited(self):
        key = compute_identity_key("a", "b", "c", "d", "e")
        assert key == "a|b|c|d|e"


class TestComputeIdentityHash:
    def test_sha256_hex_length(self):
        key = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        h = compute_identity_hash(key)
        assert len(h) == 64  # SHA-256 hex digest

    def test_deterministic(self):
        key = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        assert compute_identity_hash(key) == compute_identity_hash(key)

    def test_different_keys_different_hashes(self):
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "requires_dependency", "app.external.*", "ADR-003", "fp-1")
        assert compute_identity_hash(key1) != compute_identity_hash(key2)


class TestComputeShortId:
    def test_five_hex_chars(self):
        sid = compute_short_id("abcdef1234567890" * 4)
        assert len(sid) == 5

    def test_different_hashes_different_short_ids(self):
        key1 = compute_identity_key("app.auth", "prohibits_dependency", "app.external.*", "ADR-003", "fp-1")
        key2 = compute_identity_key("app.auth", "requires_dependency", "app.external.*", "ADR-003", "fp-1")
        assert compute_short_id(compute_identity_hash(key1)) != compute_short_id(compute_identity_hash(key2))


class TestViolationIdentity:
    def test_roundtrip(self):
        v = _make_violation()
        id_key = violation_identity(v)
        expected = compute_identity_key("app.service.*", "prohibits_dependency", "app.repo.*", "ADR-001", "fp-abc123")
        assert id_key == expected

    def test_predicate_stored_as_value(self):
        v = _make_violation(predicate=PredicateType.REQUIRES_IMPLEMENTATION)
        id_key = violation_identity(v)
        assert "requires_implementation" in id_key

    def test_fingerprintless_violation_has_stable_identity(self):
        # deterministic short ID for display, but never matchable by a
        # dismissal (from_violation refuses fingerprint-less violations)
        v1 = _make_violation(code_fingerprint=None)
        v2 = _make_violation(code_fingerprint=None)
        assert violation_identity(v1) == violation_identity(v2)
        assert "none" in violation_identity(v1)


class TestViolationShortId:
    def test_deterministic(self):
        v = _make_violation()
        assert violation_short_id(v) == violation_short_id(v)

    def test_different_violations_different_ids(self):
        v1 = _make_violation(adr_id="ADR-001")
        v2 = _make_violation(adr_id="ADR-002")
        assert violation_short_id(v1) != violation_short_id(v2)


class TestDismissalFromViolation:
    def test_populates_all_fields(self):
        v = _make_violation()
        d = Dismissal.from_violation(v)
        assert d.subject == v.constraint.subject
        assert d.predicate == v.constraint.predicate.value
        assert d.object == v.constraint.object
        assert d.adr_id == v.constraint.adr_id
        assert d.code_fingerprint == "fp-abc123"
        assert d.matched_fqn == str(v.matched_fqn)
        assert d.governed_fqn == str(governed_module(v))
        assert d.identity_hash == compute_identity_hash(violation_identity(v))
        assert d.short_id == compute_short_id(d.identity_hash)

    def test_dismissed_at_is_iso(self):
        v = _make_violation()
        d = Dismissal.from_violation(v)
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(d.dismissed_at)

    def test_refuses_violation_without_fingerprint(self):
        # #186: a dismissal without a code state would suppress forever —
        # the exact bug this closes. Refuse instead.
        v = _make_violation(code_fingerprint=None)
        with pytest.raises(ValueError, match="code fingerprint"):
            Dismissal.from_violation(v)


class TestFilterDismissed:
    def test_removes_matching(self):
        v = _make_violation()
        dismissals = [Dismissal.from_violation(v)]
        result = filter_dismissed([v], dismissals)
        assert result == []

    def test_keeps_non_matching(self):
        v1 = _make_violation(adr_id="ADR-001")
        v2 = _make_violation(adr_id="ADR-002")
        dismissals = [Dismissal.from_violation(v1)]
        result = filter_dismissed([v1, v2], dismissals)
        assert len(result) == 1
        assert result[0].constraint.adr_id == "ADR-002"

    def test_material_code_change_resurfaces_violation(self):
        """#186 headline: the same location re-firing after the code at the
        governed module changed is NOT suppressed by the old dismissal."""
        before = _make_violation(code_fingerprint="fp-before")
        after = _make_violation(code_fingerprint="fp-after")
        dismissals = [Dismissal.from_violation(before)]
        result = filter_dismissed([after], dismissals)
        assert result == [after]

    def test_evidence_location_move_still_suppressed(self):
        """Unrelated churn that moves the evidence location (matched_fqn)
        keeps the dismissal valid — evidence is provenance, not identity."""
        dismissed = _make_violation(matched_fqn="app.service.UserService")
        moved = _make_violation(matched_fqn="app.service.helpers.UserService")
        dismissals = [Dismissal.from_violation(dismissed)]
        result = filter_dismissed([moved], dismissals)
        assert result == []

    def test_legacy_dismissal_never_suppresses(self):
        """Pre-#186 rows carry no code fingerprint: they cannot be checked
        against the code state, so the violation re-surfaces for re-review."""
        v = _make_violation()
        legacy = Dismissal(
            short_id="abc12",
            identity_hash="abc12" + "0" * 59,
            subject=v.constraint.subject,
            predicate=v.constraint.predicate.value,
            object=v.constraint.object,
            matched_fqn=str(v.matched_fqn),
            adr_id=v.constraint.adr_id,
            code_fingerprint=None,
        )
        result = filter_dismissed([v], [legacy])
        assert result == [v]

    def test_empty_dismissals_returns_all(self):
        v = _make_violation()
        result = filter_dismissed([v], [])
        assert len(result) == 1

    def test_empty_violations_returns_empty(self):
        result = filter_dismissed([], [Dismissal.from_violation(_make_violation())])
        assert result == []

    def test_partial_dismissal(self):
        v1 = _make_violation(adr_id="ADR-001")
        v2 = _make_violation(adr_id="ADR-002")
        v3 = _make_violation(adr_id="ADR-003")
        dismissals = [Dismissal.from_violation(v2)]
        result = filter_dismissed([v1, v2, v3], dismissals)
        assert len(result) == 2
        assert all(v.constraint.adr_id != "ADR-002" for v in result)