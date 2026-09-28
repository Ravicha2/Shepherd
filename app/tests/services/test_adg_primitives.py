"""ADG as a frozen value: tuple coercion, lossless transforms, one EXTERNAL sentinel (#172).

Public interface under test:
    ADG.__post_init__   list kwargs still accepted, sequences become tuples
    ADG.replace / map_constraints / with_nodes / with_edges / with_constraints
    FQNNode.external    the only synthetic-EXTERNAL constructor
"""

from __future__ import annotations

from dataclasses import fields, replace

import pytest

from services.adg.merge import add_external_nodes, merge_constraint_edges
from services.commit_update import merge_preserved_constraints
from services.cpt.diff_processor import augmented
from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    ConstraintScope,
    DependencyRole,
    Diff,
    Edge,
    FileChange,
    FQNKind,
    FQNNode,
    PredicateType,
)
from services.pipeline import adg_with_specificity


def _module(name: str) -> FQNNode:
    return FQNNode(
        fqn=FQN.from_dotted(name),
        kind=FQNKind.MODULE,
        file_path=f"{name.replace('.', '/')}.py",
        line_start=1,
        line_end=20,
        start_byte=0,
        end_byte=400,
    )


def _constraint(subject: str, obj: str, adr_id: str = "ADR-001", scope: ConstraintScope = ConstraintScope.RUNTIME) -> ConstraintEdge:
    return ConstraintEdge(
        subject=subject,
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        object=obj,
        justification=f"{subject} must not reach {obj}.",
        adr_id=adr_id,
        adr_path=f"docs/adr/{adr_id}.md",
        specificity=2.5,
        scope=scope,
    )


def _graph() -> ADG:
    """One node of each kind, two edges, two constraints with non-default fields."""
    return ADG(
        nodes=[
            _module("app"),
            _module("app.service"),
            FQNNode(fqn=FQN.from_dotted("app.service.UserService"), kind=FQNKind.CLASS,
                    file_path="app/service.py", line_start=4, line_end=18, start_byte=80, end_byte=300),
            FQNNode(fqn=FQN.from_dotted("app.service.UserService.load"), kind=FQNKind.METHOD,
                    file_path="app/service.py", line_start=6, line_end=9, start_byte=120, end_byte=200),
        ],
        edges=[
            Edge(source="app", target="app.service", kind="CONTAINS"),
            Edge(source="app.service", target="app.repo", kind="IMPORTS"),
        ],
        constraint_edges=[
            _constraint("app.service.*", "app.repo.*", adr_id="ADR-001"),
            _constraint("app.service.UserService", "app.repo", adr_id="ADR-002", scope=ConstraintScope.TOOLING),
        ],
    )


def _signature(item, skip: frozenset[str] = frozenset()) -> tuple:
    """Every field of a dataclass instance, as a comparable value."""
    return tuple((f.name, getattr(item, f.name)) for f in fields(item) if f.name not in skip)


# ===========================================================================
# Freeze: tuple coercion, tuple-only writes
# ===========================================================================


class TestFrozen:
    def test_list_kwargs_are_still_accepted_and_coerced(self) -> None:
        """The ~101 existing ADG(nodes=[...], edges=[...]) call sites keep working."""
        adg = ADG(nodes=[_module("app")], edges=[Edge(source="a", target="b", kind="IMPORTS")],
                  constraint_edges=[_constraint("app.*", "app.repo")])
        assert isinstance(adg.nodes, tuple)
        assert isinstance(adg.edges, tuple)
        assert isinstance(adg.constraint_edges, tuple)

    def test_append_is_a_loud_type_error(self) -> None:
        adg = _graph()
        with pytest.raises(TypeError, match="ADG is frozen"):
            adg.nodes.append(_module("app.other"))
        with pytest.raises(TypeError, match="ADG is frozen"):
            adg.edges.append(Edge(source="a", target="b", kind="IMPORTS"))
        with pytest.raises(TypeError, match="ADG is frozen"):
            adg.constraint_edges.append(_constraint("a.*", "b"))

    def test_has_dict_for_cached_property(self) -> None:
        """ADG must stay non-slots: the derived indexes memoise into __dict__."""
        assert hasattr(_graph(), "__dict__")


# ===========================================================================
# Derived indexes (#173): each agrees with the linear scan it replaces
# ===========================================================================


def _duplicate_fqn_graph() -> ADG:
    """Two nodes sharing one FQN — the HA case (88,508 nodes, 88,405 FQNs)."""
    return ADG(
        nodes=[
            _module("app"),
            FQNNode(fqn=FQN.from_dotted("app.dup"), kind=FQNKind.MODULE,
                    file_path="app/dup/__init__.py", line_start=1, line_end=1, start_byte=0, end_byte=0),
            FQNNode(fqn=FQN.from_dotted("app.dup"), kind=FQNKind.CLASS,
                    file_path="app/dup.py", line_start=1, line_end=9, start_byte=0, end_byte=40),
        ],
        edges=[
            Edge(source="app", target="app.dup", kind="CONTAINS"),
            Edge(source="app.dup", target="os", kind="IMPORTS"),
            Edge(source="app.dup", target="pkg.Base", kind="INHERITS"),
        ],
    )


class TestIndexes:
    def test_fqns_is_sorted_and_deduped(self) -> None:
        assert _duplicate_fqn_graph().fqns == (FQN.from_dotted("app"), FQN.from_dotted("app.dup"))

    def test_fqns_matches_the_linear_sort(self) -> None:
        adg = _graph()
        assert adg.fqns == tuple(sorted({node.fqn for node in adg.nodes}, key=str))

    def test_fqn_set_matches_the_linear_scan(self) -> None:
        adg = _graph()
        assert adg.fqn_set == frozenset(str(node.fqn) for node in adg.nodes)
        assert isinstance(adg.fqn_set, frozenset)

    def test_node_of_matches_the_linear_scan(self) -> None:
        assert _graph().node_of == {str(node.fqn): node for node in _graph().nodes}

    def test_node_of_last_wins_on_a_duplicate_fqn(self) -> None:
        """The dict comprehension it replaces was last-wins; keep that, not first."""
        adg = _duplicate_fqn_graph()
        assert adg.node_of["app.dup"] is adg.nodes[-1]

    def test_role_of_matches_the_linear_scan(self) -> None:
        adg = ADG(nodes=[_module("app"), FQNNode.external("requests", role=DependencyRole.DEV_TOOL)])
        assert adg.role_of == {str(node.fqn): node.role for node in adg.nodes}
        assert adg.role_of["requests"] is DependencyRole.DEV_TOOL

    def test_out_edges_matches_the_linear_scan(self) -> None:
        adg = _duplicate_fqn_graph()
        expected: dict[str, list[Edge]] = {}
        for edge in adg.edges:
            expected.setdefault(edge.source, []).append(edge)
        assert {k: list(v) for k, v in adg.out_edges.items()} == expected

    def test_out_edges_omits_sources_with_no_out_edges(self) -> None:
        assert "app.repo" not in _graph().out_edges

    def test_edges_from_matches_the_linear_filter(self) -> None:
        adg = _duplicate_fqn_graph()
        assert adg.edges_from("app.dup") == tuple(adg.edges[1:])
        assert adg.edges_from("app.dup", "INHERITS") == (Edge(source="app.dup", target="pkg.Base", kind="INHERITS"),)
        assert adg.edges_from("app.dup", "IMPORTS", "INHERITS") == tuple(adg.edges[1:])
        assert adg.edges_from("app.dup", "CALLS") == ()
        assert adg.edges_from("nonexistent") == ()

    def test_indexes_are_read_only(self) -> None:
        """A memoised index that a caller can mutate is the invalidation bug the
        frozen-value design exists to avoid."""
        adg = _graph()
        with pytest.raises(TypeError):
            adg.node_of["app"] = _module("app")  # type: ignore[index]
        with pytest.raises(TypeError):
            adg.out_edges["app"] = ()  # type: ignore[index]

    def test_memoisation_does_not_leak_across_a_transform(self) -> None:
        """A transform returns a NEW value: the parent's index is not inherited,
        and the child's index is not stale."""
        parent = _graph()
        other = FQN.from_dotted("app.other")
        assert other not in parent.fqns  # warm the parent's index
        child = parent.with_nodes(_module("app.other")).with_edges(
            Edge(source="app.other", target="os", kind="IMPORTS")
        )
        assert child.fqns != parent.fqns
        assert other in child.fqns
        assert other not in parent.fqns
        assert child.out_edges["app.other"] == (Edge(source="app.other", target="os", kind="IMPORTS"),)
        assert "app.other" not in parent.out_edges
        assert child.node_of is not parent.node_of


# ===========================================================================
# Primitives
# ===========================================================================


class TestPrimitives:
    def test_replace_returns_a_new_equal_graph(self) -> None:
        adg = _graph()
        copy = adg.replace()
        assert copy == adg
        assert copy is not adg

    def test_replace_recoerces_lists(self) -> None:
        assert isinstance(_graph().replace(nodes=[_module("app.other")]).nodes, tuple)

    def test_original_is_never_touched(self) -> None:
        adg = _graph()
        before = _signature(adg)
        adg.with_nodes(_module("app.other"))
        adg.with_edges(Edge(source="app", target="app.other", kind="CALLS"))
        adg.with_constraints(_constraint("app.other.*", "app.repo"))
        adg.map_constraints(lambda e: replace(e, specificity=99.0))
        assert _signature(adg) == before

    def test_with_nodes_dedups_by_fqn_first_wins(self) -> None:
        """A real node already in the graph beats a stale EXTERNAL placeholder."""
        real = _module("app.repo")
        adg = ADG(nodes=[real])
        result = adg.with_nodes(FQNNode.external("app.repo"), FQNNode.external("app.repo"))
        assert result.nodes == (real,)

    def test_with_nodes_appends_only_the_new(self) -> None:
        result = _graph().with_nodes(_module("app.other"))
        assert [str(n.fqn) for n in result.nodes].count("app.other") == 1
        assert len(result.nodes) == 5  # 4 original + 1

    def test_with_edges_dedups_by_triple(self) -> None:
        adg = ADG(edges=[Edge(source="a", target="b", kind="IMPORTS")])
        result = adg.with_edges(
            Edge(source="a", target="b", kind="IMPORTS"),   # dup
            Edge(source="a", target="b", kind="CALLS"),     # same endpoints, other kind
        )
        assert result.edges == (Edge(source="a", target="b", kind="IMPORTS"),
                                Edge(source="a", target="b", kind="CALLS"))

    def test_with_constraints_dedups_on_the_value_key_first_wins(self) -> None:
        """The same key #171 matches on: (adr_id, predicate, subject, object)."""
        first = _constraint("app.*", "app.repo", adr_id="ADR-001")
        twin = _constraint("app.*", "app.repo", adr_id="ADR-001", scope=ConstraintScope.TOOLING)
        assert first != twin  # structurally different, same identity key
        adg = ADG(constraint_edges=[first])
        assert adg.with_constraints(twin).constraint_edges == (first,)

    def test_with_constraints_keeps_different_adrs(self) -> None:
        adg = ADG(constraint_edges=[_constraint("app.*", "app.repo", adr_id="ADR-001")])
        result = adg.with_constraints(_constraint("app.*", "app.repo", adr_id="ADR-002"))
        assert len(result.constraint_edges) == 2

    def test_map_constraints_reruns_post_init(self) -> None:
        """dataclasses.replace re-validates, so a transform cannot smuggle a
        self-loop (or any other invalid edge) into the graph."""
        with pytest.raises(ValueError, match="subject and object must differ"):
            _graph().map_constraints(lambda e: replace(e, object=e.subject))


# ===========================================================================
# Losslessness: every field of every edge survives every transform (#159)
# ===========================================================================


class TestLossless:
    def test_specificity_transform_preserves_every_other_field(self) -> None:
        adg = _graph()
        result = adg_with_specificity(adg)
        assert len(result.constraint_edges) == len(adg.constraint_edges)
        for before, after in zip(adg.constraint_edges, result.constraint_edges):
            assert _signature(after, frozenset({"specificity"})) == _signature(before, frozenset({"specificity"}))
            assert after.specificity > 0.0
        assert result.nodes == adg.nodes
        assert result.edges == adg.edges

    def test_tooling_scope_survives_the_specificity_transform(self) -> None:
        """The #159 regression, as a test rather than a docstring: the old
        hand-written field-by-field rebuild dropped `scope` and reverted every
        edge to RUNTIME."""
        result = adg_with_specificity(_graph())
        scopes = [e.scope for e in result.constraint_edges]
        assert scopes == [ConstraintScope.RUNTIME, ConstraintScope.TOOLING]

    def test_external_node_transform_preserves_existing_members(self) -> None:
        adg = _graph()
        result = add_external_nodes(adg)
        assert tuple(_signature(n) for n in result.nodes[:len(adg.nodes)]) == \
            tuple(_signature(n) for n in adg.nodes)
        assert result.edges == adg.edges
        assert result.constraint_edges == adg.constraint_edges

    def test_augmented_preserves_every_field_and_leaves_the_input_alone(self) -> None:
        adg = _graph()
        before = _signature(adg)
        diff = Diff(
            to_sha="abc123",
            from_sha="def456",
            changed_files=[FileChange(path="app/new_module.py", status="added")],
            file_contents={"app/new_module.py": b"def hello():\n    return 1\n"},
            from_contents={},
        )
        result = augmented(adg, diff)
        assert _signature(adg) == before
        assert adg.nodes == result.nodes[:len(adg.nodes)]
        assert result.edges[:len(adg.edges)] == adg.edges
        assert result.constraint_edges == adg.constraint_edges
        assert any(str(n.fqn) == "app.new_module" for n in result.nodes)


# ===========================================================================
# One EXTERNAL sentinel: all five hand-built spellings agree field-for-field
# ===========================================================================


class TestExternalSentinel:
    def test_sentinel_fields(self) -> None:
        node = FQNNode.external("requests")
        assert node.fqn == FQN.from_dotted("requests")
        assert node.kind is FQNKind.EXTERNAL
        assert (node.file_path, node.line_start, node.line_end) == ("", -1, -1)
        assert (node.start_byte, node.end_byte) == (0, 0)
        assert node.role is DependencyRole.UNKNOWN

    def test_role_overridable(self) -> None:
        assert FQNNode.external("pytest", role=DependencyRole.DEV_TOOL).role is DependencyRole.DEV_TOOL

    def test_dev_tool_root_and_config_extra_and_unknown(self, tmp_path) -> None:
        """The three role answers the sentinel must give, from one graph."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\n\n[project.optional-dependencies]\ndev = ["custom_linter"]\n'
        )
        adg = ADG(nodes=[_module("app")],
                  edges=[Edge(source="app", target=name, kind="IMPORTS")
                         for name in ("pytest", "custom_linter", "requests")])
        roles = {str(n.fqn): n.role for n in add_external_nodes(adg, project_root=tmp_path).nodes
                 if n.kind is FQNKind.EXTERNAL}
        assert roles == {
            "pytest": DependencyRole.DEV_TOOL,       # hardcoded registry
            "custom_linter": DependencyRole.DEV_TOOL,  # config-declared dev extra
            "requests": DependencyRole.UNKNOWN,      # unknown package
        }

    def test_every_placeholder_path_produces_the_sentinel_exactly(self, tmp_path) -> None:
        """The five spellings used to disagree; they are now one constructor."""
        adg = ADG(nodes=[_module("app")],
                  edges=[Edge(source="app", target="requests", kind="IMPORTS")])
        ce = _constraint("app", "requests")

        produced = [
            *add_external_nodes(adg).nodes,
            *merge_constraint_edges(adg, [ce]).nodes,
            *merge_preserved_constraints(adg, [ce]).nodes,
            *augmented(adg, Diff(to_sha="a", from_sha="b",
                                 changed_files=[FileChange(path="app/new.py", status="added")],
                                 file_contents={"app/new.py": b"import requests\n"},
                                 from_contents={})).nodes,
        ]
        placeholders = [n for n in produced if n.kind is FQNKind.EXTERNAL]
        assert placeholders
        for node in placeholders:
            assert node == FQNNode.external(str(node.fqn))

    def test_preserved_constraints_path_moves_orphans_internal_to_unknown(self) -> None:
        """This path never classified, so its orphans used to arrive as INTERNAL.
        UNKNOWN is the correct direction — pin it. Since #174 it shares the seed
        chain, so it externalizes unresolved imports as well as orphan endpoints."""
        merged = merge_preserved_constraints(_graph(), [_constraint("app", "some_unclassified_pkg")])
        orphan = [n for n in merged.nodes if n.kind is FQNKind.EXTERNAL and str(n.fqn) == "some_unclassified_pkg"]
        assert len(orphan) == 1
        assert orphan[0].role is DependencyRole.UNKNOWN
        assert orphan[0].role is not DependencyRole.INTERNAL
