"""Tests for ADG query tools: list_modules, list_children, list_imports, list_inherits.

These tools wrap the in-memory ADG for agent tool-call consumption.
No Neo4j dependency; pure list/set operations on ADG.nodes and ADG.edges.
"""

from __future__ import annotations

import pytest

from services.fqn import FQN
from services.models import ADG, Edge, FQNKind, FQNNode
from services.adg.adg_tools import list_modules, list_children, list_imports, list_inherits


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture
def sample_adg() -> ADG:
    """ADG with modules, classes, methods, functions, imports, and inherits."""
    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users"), kind=FQNKind.MODULE, file_path="app/api/users.py", line_start=0, line_end=50, start_byte=0, end_byte=1000),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView"), kind=FQNKind.CLASS, file_path="app/api/users.py", line_start=5, line_end=40, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.UserView.get"), kind=FQNKind.METHOD, file_path="app/api/users.py", line_start=10, line_end=20, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api.users.list_users"), kind=FQNKind.FUNCTION, file_path="app/api/users.py", line_start=45, line_end=50, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth"), kind=FQNKind.MODULE, file_path="app/auth/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware"), kind=FQNKind.MODULE, file_path="app/auth/middleware.py", line_start=0, line_end=60, start_byte=0, end_byte=1200),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware"), kind=FQNKind.CLASS, file_path="app/auth/middleware.py", line_start=5, line_end=55, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.auth.middleware.AuthMiddleware.check"), kind=FQNKind.METHOD, file_path="app/auth/middleware.py", line_start=15, line_end=25, start_byte=0, end_byte=0),
    ]
    edges = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app.api", target="app.api.users", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.UserView", kind="CONTAINS"),
        Edge(source="app.api.users.UserView", target="app.api.users.UserView.get", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.api.users.list_users", kind="CONTAINS"),
        Edge(source="app", target="app.auth", kind="CONTAINS"),
        Edge(source="app.auth", target="app.auth.middleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware", target="app.auth.middleware.AuthMiddleware", kind="CONTAINS"),
        Edge(source="app.auth.middleware.AuthMiddleware", target="app.auth.middleware.AuthMiddleware.check", kind="CONTAINS"),
        Edge(source="app.api.users", target="app.auth.middleware", kind="IMPORTS"),
        Edge(source="app.auth.middleware.AuthMiddleware", target="app.api.users.UserView", kind="INHERITS"),
    ]
    return ADG(nodes=nodes, edges=edges)


@pytest.fixture
def empty_adg() -> ADG:
    return ADG(nodes=[], edges=[])


# -- list_modules -----------------------------------------------------------

class TestListModules:
    def test_returns_top_level_module_fqns(self, sample_adg: ADG) -> None:
        result = list_modules(sample_adg)
        assert "app" in result
        # All results are strings
        assert all(isinstance(fqn, str) for fqn in result)

    def test_includes_all_modules(self, sample_adg: ADG) -> None:
        result = list_modules(sample_adg)
        expected = {"app", "app.api", "app.api.users", "app.auth", "app.auth.middleware"}
        assert set(result) == expected

    def test_empty_adg(self, empty_adg: ADG) -> None:
        assert list_modules(empty_adg) == []

    def test_excludes_non_modules(self) -> None:
        nodes = [
            FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.MyClass"), kind=FQNKind.CLASS, file_path="app/mod.py", line_start=0, line_end=10, start_byte=0, end_byte=0),
        ]
        adg = ADG(nodes=nodes, edges=[])
        result = list_modules(adg)
        assert result == ["app"]


# -- list_children -----------------------------------------------------------

class TestListChildren:
    def test_returns_contained_nodes(self, sample_adg: ADG) -> None:
        result = list_children("app.api.users", sample_adg)
        fqns = {r["fqn"] for r in result}
        assert "app.api.users.UserView" in fqns
        assert "app.api.users.list_users" in fqns

    def test_children_include_kind(self, sample_adg: ADG) -> None:
        result = list_children("app.api.users", sample_adg)
        by_fqn = {r["fqn"]: r for r in result}
        assert by_fqn["app.api.users.UserView"]["kind"] == "class"
        assert by_fqn["app.api.users.list_users"]["kind"] == "function"

    def test_nested_children_only_direct(self, sample_adg: ADG) -> None:
        """Only direct children, not grandchildren."""
        result = list_children("app.api.users", sample_adg)
        fqns = {r["fqn"] for r in result}
        # UserView.get is a child of UserView, not of users module directly
        assert "app.api.users.UserView.get" not in fqns

    def test_leaf_node_no_children(self, sample_adg: ADG) -> None:
        result = list_children("app.api.users.UserView.get", sample_adg)
        assert result == []

    def test_nonexistent_fqn_returns_empty(self, sample_adg: ADG) -> None:
        result = list_children("does.not.exist", sample_adg)
        assert result == []

    def test_empty_adg(self, empty_adg: ADG) -> None:
        assert list_children("app", empty_adg) == []


# -- list_imports -----------------------------------------------------------

class TestListImports:
    def test_returns_import_targets(self, sample_adg: ADG) -> None:
        result = list_imports("app.api.users", sample_adg)
        assert result == ["app.auth.middleware"]

    def test_no_imports(self, sample_adg: ADG) -> None:
        result = list_imports("app.auth.middleware", sample_adg)
        assert result == []

    def test_multiple_imports(self) -> None:
        nodes = [
            FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.mod"), kind=FQNKind.MODULE, file_path="app/mod.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("os"), kind=FQNKind.EXTERNAL, file_path="", line_start=-1, line_end=-1, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("sys"), kind=FQNKind.EXTERNAL, file_path="", line_start=-1, line_end=-1, start_byte=0, end_byte=0),
        ]
        edges = [
            Edge(source="app.mod", target="os", kind="IMPORTS"),
            Edge(source="app.mod", target="sys", kind="IMPORTS"),
        ]
        adg = ADG(nodes=nodes, edges=edges)
        result = list_imports("app.mod", adg)
        assert set(result) == {"os", "sys"}

    def test_nonexistent_fqn_returns_empty(self, sample_adg: ADG) -> None:
        assert list_imports("nonexistent", sample_adg) == []

    def test_empty_adg(self, empty_adg: ADG) -> None:
        assert list_imports("app", empty_adg) == []


# -- list_inherits -----------------------------------------------------------

class TestListInherits:
    def test_returns_inheritance_targets(self, sample_adg: ADG) -> None:
        result = list_inherits("app.auth.middleware.AuthMiddleware", sample_adg)
        assert result == ["app.api.users.UserView"]

    def test_no_inheritance(self, sample_adg: ADG) -> None:
        result = list_inherits("app.api.users.UserView", sample_adg)
        assert result == []

    def test_multiple_inherits(self) -> None:
        nodes = [
            FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.Base1"), kind=FQNKind.CLASS, file_path="app/b.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.Base2"), kind=FQNKind.CLASS, file_path="app/b.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.Child"), kind=FQNKind.CLASS, file_path="app/b.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        ]
        edges = [
            Edge(source="app.Child", target="app.Base1", kind="INHERITS"),
            Edge(source="app.Child", target="app.Base2", kind="INHERITS"),
        ]
        adg = ADG(nodes=nodes, edges=edges)
        result = list_inherits("app.Child", adg)
        assert set(result) == {"app.Base1", "app.Base2"}

    def test_nonexistent_fqn_returns_empty(self, sample_adg: ADG) -> None:
        assert list_inherits("nonexistent", sample_adg) == []

    def test_empty_adg(self, empty_adg: ADG) -> None:
        assert list_inherits("app", empty_adg) == []

    def test_only_inherits_edges_not_other_kinds(self, sample_adg: ADG) -> None:
        """CONTAINS edges for the same source should not appear."""
        result = list_inherits("app.api", sample_adg)
        assert result == []  # app.api has CONTAINS edges but no INHERITS