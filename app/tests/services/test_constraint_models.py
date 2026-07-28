"""Tests for constraint models and PredicateType.

Public interface under test:
    PredicateType: enum with PROHIBITS_DEPENDENCY, REQUIRES_IMPLEMENTATION,
                         REQUIRES_DEPENDENCY, PROHIBITS_IMPLEMENTATION
    ConstraintEdge: dataclass with subject, predicate, object, justification,
                     adr_id, adr_path
"""

from __future__ import annotations

import pytest

from services.models import (
    ConstraintEdge,
    PredicateType,
)


# ===========================================================================
# 1. PredicateType enum
# ===========================================================================


class TestPredicateType:
    """PredicateType has four values for ADR constraint predicates."""

    def test_prohibits_dependency_value(self) -> None:
        assert PredicateType.PROHIBITS_DEPENDENCY.value == "prohibits_dependency"

    def test_requires_implementation_value(self) -> None:
        assert PredicateType.REQUIRES_IMPLEMENTATION.value == "requires_implementation"

    def test_requires_dependency_value(self) -> None:
        assert PredicateType.REQUIRES_DEPENDENCY.value == "requires_dependency"

    def test_prohibits_implementation_value(self) -> None:
        assert PredicateType.PROHIBITS_IMPLEMENTATION.value == "prohibits_implementation"

    def test_enum_membership(self) -> None:
        """PredicateType has exactly four members."""
        assert len(PredicateType) == 4

    def test_from_value(self) -> None:
        """PredicateType can be constructed from its string value."""
        assert PredicateType("prohibits_dependency") is PredicateType.PROHIBITS_DEPENDENCY
        assert PredicateType("requires_implementation") is PredicateType.REQUIRES_IMPLEMENTATION
        assert PredicateType("requires_dependency") is PredicateType.REQUIRES_DEPENDENCY
        assert PredicateType("prohibits_implementation") is PredicateType.PROHIBITS_IMPLEMENTATION

    def test_invalid_value_raises(self) -> None:
        """Invalid predicate string raises ValueError."""
        with pytest.raises(ValueError):
            PredicateType("invalid_predicate")


# ===========================================================================
# 2. ConstraintEdge construction
# ===========================================================================


class TestConstraintEdgeConstruction:
    """ConstraintEdge holds an ADR-sourced constraint with traceability."""

    def test_prohibits_dependency_constraint(self) -> None:
        edge = ConstraintEdge(
            subject="app.services.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.db.mysql",
            justification="Direct MySQL connections are prohibited for services.",
            adr_id="ADR-001",
            adr_path="docs/adr/ADR-001-mysql-storage.md",
        )
        assert edge.subject == "app.services.*"
        assert edge.predicate is PredicateType.PROHIBITS_DEPENDENCY
        assert edge.object == "app.db.mysql"
        assert edge.adr_id == "ADR-001"

    def test_requires_implementation_constraint(self) -> None:
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            object="app.auth.middleware",
            justification="All API endpoints must implement authentication.",
            adr_id="ADR-003",
            adr_path="docs/adr/ADR-003-auth-middleware.md",
        )
        assert edge.predicate is PredicateType.REQUIRES_IMPLEMENTATION
        assert edge.object == "app.auth.middleware"

    def test_requires_dependency_constraint(self) -> None:
        edge = ConstraintEdge(
            subject="app.api.*",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            object="app.auth.middleware",
            justification="All API endpoints must use the auth middleware.",
            adr_id="ADR-004",
            adr_path="docs/adr/ADR-004-auth-required.md",
        )
        assert edge.predicate is PredicateType.REQUIRES_DEPENDENCY
        assert edge.object == "app.auth.middleware"

    def test_prohibits_implementation_constraint(self) -> None:
        edge = ConstraintEdge(
            subject="app.services.*",
            predicate=PredicateType.PROHIBITS_IMPLEMENTATION,
            object="app.auth.middleware",
            justification="No service shall implement its own authentication logic.",
            adr_id="ADR-005",
            adr_path="docs/adr/ADR-005-auth-centralized.md",
        )
        assert edge.predicate is PredicateType.PROHIBITS_IMPLEMENTATION
        assert edge.subject == "app.services.*"

    def test_nonexistent_fqn_object(self) -> None:
        """ConstraintEdge accepts FQNs that don't exist in the codebase yet."""
        edge = ConstraintEdge(
            subject="app.services.new.*",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            object="app.db.postgres",
            justification="New services must use PostgreSQL.",
            adr_id="ADR-004",
            adr_path="docs/adr/ADR-004-postgres-migration.md",
        )
        assert edge.object == "app.db.postgres"

    def test_wildcard_subject_and_object(self) -> None:
        """Both subject and object can contain wildcards."""
        edge = ConstraintEdge(
            subject="app.services.*",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            object="app.services.<other_service>.*",
            justification="Services must not depend on other services.",
            adr_id="ADR-005",
            adr_path="docs/adr/ADR-005-microservices-boundary.md",
        )
        assert ".*" in edge.subject
        assert ".*" in edge.object


# ===========================================================================
# 3. ConstraintEdge validation
# ===========================================================================


class TestConstraintEdgeValidation:
    """ConstraintEdge rejects invalid or missing fields."""

    def test_empty_subject_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            ConstraintEdge(
                subject="",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.db.mysql",
                justification="Test",
                adr_id="ADR-001",
                adr_path="docs/adr/ADR-001.md",
            )

    def test_empty_object_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            ConstraintEdge(
                subject="app.services.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="",
                justification="Test",
                adr_id="ADR-001",
                adr_path="docs/adr/ADR-001.md",
            )

    def test_empty_justification_rejected(self) -> None:
        """Justification must be non-empty; it provides auditability."""
        with pytest.raises((ValueError, TypeError)):
            ConstraintEdge(
                subject="app.services.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.db.mysql",
                justification="",
                adr_id="ADR-001",
                adr_path="docs/adr/ADR-001.md",
            )

    def test_missing_adr_id_rejected(self) -> None:
        """adr_id is required for traceability back to the source ADR."""
        with pytest.raises((ValueError, TypeError)):
            ConstraintEdge(
                subject="app.services.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.db.mysql",
                justification="Test justification",
                adr_path="docs/adr/ADR-001.md",
            )

    def test_missing_adr_path_rejected(self) -> None:
        """adr_path is required for traceability."""
        with pytest.raises((ValueError, TypeError)):
            ConstraintEdge(
                subject="app.services.*",
                predicate=PredicateType.PROHIBITS_DEPENDENCY,
                object="app.db.mysql",
                justification="Test justification",
                adr_id="ADR-001",
            )

    def test_self_loop_rejected(self) -> None:
        """subject == object is a self-loop and must be rejected."""
        with pytest.raises(ValueError, match="subject and object must differ"):
            ConstraintEdge(
                subject="app.auth.middleware",
                predicate=PredicateType.REQUIRES_IMPLEMENTATION,
                object="app.auth.middleware",
                justification="Only app.auth.middleware may implement authentication.",
                adr_id="ADR-010",
                adr_path="docs/adr/010.md",
            )

