"""Tests for the Symbolic Resolver: prose matching, CONTAINS walks,
external dependency bypass, and end-to-end resolution."""

from __future__ import annotations

import pytest

from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    Edge,
    FQNKind,
    FQNNode,
    PredicateType,
    SymbolicConstraint,
)
from services.adg.symbolic_resolver import (
    _prose_match,
    resolve_symbolic_constraints,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sample_adg() -> ADG:
    """A small ADG with module, class, function, and method nodes."""
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=1000),
        FQNNode(fqn=FQN.from_dotted("app.api.orders"), kind=FQNKind.MODULE, file_path="app/api/orders.py", line_start=0, line_end=40, start_byte=0, end_byte=800),
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.Middleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=1200),
        FQNNode(fqn=FQN.from_dotted("app.auth.Middleware.authenticate"), kind=FQNKind.METHOD, file_path="app/auth/middleware.py", line_start=10, line_end=30, start_byte=0, end_byte=500),
        FQNNode(fqn=FQN.from_dotted("app.services"), kind=FQNKind.MODULE, file_path="app/services/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.services.user"), kind=FQNKind.MODULE, file_path="app/services/user.py", line_start=0, line_end=80, start_byte=0, end_byte=2000),
    ]
    edges = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.orders", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.Middleware", kind="CONTAINS"),
        Edge(source="app.auth.Middleware", target="app.auth.Middleware.authenticate", kind="CONTAINS"),
        Edge(source="app", target="app.services", kind="CONTAINS"),
        Edge(source="app.services", target="app.services.user", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.auth.middleware", kind="IMPORTS"),
        Edge(source="app.services.user", target="app.auth.middleware", kind="IMPORTS"),
    ]
    return ADG(nodes=nodes, edges=edges)


# ===========================================================================
# 1. _prose_match
# ===========================================================================


class TestProseMatch:
    def test_exact_fqn_match(self, sample_adg: ADG) -> None:
        result = _prose_match("app.api", sample_adg.nodes)
        assert len(result) >= 1
        assert any(str(n.fqn) == "app.api" for n in result)

    def test_prefix_match_by_segment(self, sample_adg: ADG) -> None:
        """'services' matches 'app.services' via prefix/suffix match."""
        result = _prose_match("services", sample_adg.nodes)
        assert len(result) >= 1
        assert any(str(n.fqn) == "app.services" for n in result)

    def test_no_match(self, sample_adg: ADG) -> None:
        result = _prose_match("nonexistent", sample_adg.nodes)
        assert len(result) == 0

    def test_substring_match_on_last_segment(self) -> None:
        """Prose substring matches last segment of FQN."""
        nodes = [
            FQNNode(fqn=FQN.from_dotted("app.Handler"), kind=FQNKind.CLASS, file_path="", line_start=0, line_end=0, start_byte=0, end_byte=0),
        ]
        result = _prose_match("handler", nodes)
        assert len(result) == 1
        assert str(result[0].fqn) == "app.Handler"

    def test_empty_candidates_returns_empty(self) -> None:
        result = _prose_match("Handler", [])
        assert result == []

    def test_natural_language_subject_matches_nodes(self, sample_adg: ADG) -> None:
        """Prose like 'API endpoints' matches app.api via substring."""
        result = _prose_match("API endpoints", sample_adg.nodes)
        assert len(result) >= 1
        assert any("api" in str(n.fqn).lower() for n in result)

    def test_natural_language_object_matches_nodes(self, sample_adg: ADG) -> None:
        """Prose like 'auth module' matches app.auth via substring."""
        result = _prose_match("auth module", sample_adg.nodes)
        assert len(result) >= 1
        assert any("auth" in str(n.fqn).lower() for n in result)


# ===========================================================================
# 2. resolve_symbolic_constraints: integration tests
# ===========================================================================


class TestResolveSymbolicConstraints:
    def test_dependency_predicate_creates_external_node(self, sample_adg: ADG) -> None:
        """Dependency predicate with no ADG match creates EXTERNAL node."""
        sc = SymbolicConstraint(
            subject="app.api",
            object="mysql",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="No direct MySQL.",
            adr_id="ADR-001",
            adr_path="docs/adr/001.md",
        )
        resolved = resolve_symbolic_constraints([sc], sample_adg)
        assert len(resolved) >= 1
        # Object should be external (mysql.* or mysql)
        assert any("mysql" in e.object for e in resolved)

    def test_implementation_predicate_matches_class(self, sample_adg: ADG) -> None:
        """requires_implementation matches class nodes via prose."""
        sc = SymbolicConstraint(
            subject="app",
            object="app.auth",
            predicate=PredicateType.REQUIRES_IMPLEMENTATION,
            justification="Must implement auth.",
            adr_id="ADR-010",
            adr_path="docs/adr/010.md",
        )
        resolved = resolve_symbolic_constraints([sc], sample_adg)
        assert len(resolved) >= 1
        object_fqns = {e.object for e in resolved}
        assert any("app.auth" in fqn for fqn in object_fqns)

    def test_no_match_skips_constraint(self, sample_adg: ADG) -> None:
        """Unresolved constraints are logged and skipped (no crash)."""
        sc = SymbolicConstraint(
            subject="nonexistent",
            object="mysql",
            predicate=PredicateType.REQUIRES_DEPENDENCY,
            justification="Phantom module.",
            adr_id="ADR-999",
            adr_path="docs/adr/999.md",
        )
        resolved = resolve_symbolic_constraints([sc], sample_adg)
        assert len(resolved) == 0

    def test_self_loop_skipped(self) -> None:
        """Subject and object resolving to the same FQN produces no edge."""
        nodes = [
            FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        ]
        adg = ADG(nodes=nodes, edges=[])

        sc = SymbolicConstraint(
            subject="app",
            object="app",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="Self-loop test.",
            adr_id="ADR-SELF",
            adr_path="docs/adr/self.md",
        )
        resolved = resolve_symbolic_constraints([sc], adg)
        # Both resolve to "app", which is a self-loop, so no edges
        assert len(resolved) == 0

    def test_multiple_subjects_and_objects_produce_cross_product(self, sample_adg: ADG) -> None:
        """Multiple subject and object matches produce edges for each pair."""
        sc = SymbolicConstraint(
            subject="app",
            object="logging",
            predicate=PredicateType.PROHIBITS_DEPENDENCY,
            justification="No bare logging.",
            adr_id="ADR-005",
            adr_path="docs/adr/005.md",
        )
        resolved = resolve_symbolic_constraints([sc], sample_adg)
        # "app" matches multiple nodes, "logging" creates external
        assert len(resolved) >= 1
        subjects = {e.subject for e in resolved}
        assert len(subjects) >= 1