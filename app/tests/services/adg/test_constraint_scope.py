"""Constraint scope classification pins for issue #136 (decision (a), tag-not-skip).

Tooling/CI constraints live in pyproject.toml / setup.cfg / noxfile, never in
the governed package's import graph, so the eval holds them out of scope by
declaration. The classifier reads ROLE language in the ADR text, never package
names: a toolchain this suite has never seen must still classify as tooling
(the issue's generality test), and runtime ADRs whose prose brushes against
tooling vocabulary in passing must stay runtime.
"""
from __future__ import annotations

import pytest

from services.adg.unified_resolver import classify_adr_scope
from services.models import ConstraintEdge, ConstraintScope, PredicateType
from tests.services.adg import test_unified_resolver_eval as harness


# -- Generality (issue AC): unseen toolchain, no package-name matching -------

def test_unseen_tool_classifies_as_tooling() -> None:
    """A tooling ADR naming a tool outside this suite's toolchains (ruff)
    must classify as tooling. A hardcoded package list would miss this."""
    assert classify_adr_scope(
        "# 21. Linting\n\n## Decision\n\nAdopt ruff for linting."
    ) is ConstraintScope.TOOLING


# -- Positive calibration: fragments of the actual eval-repo ADRs ------------

TOOLING_ADR_FRAGMENTS = [
    pytest.param("# 2. Linting and formatting\n\nFor linting, use flake8.", id="tamr-0002-lint"),
    pytest.param("For formatting, use black.", id="tamr-0002-formatting"),
    pytest.param("# 4. Documentation and docstrings", id="tamr-0004-docstring"),
    pytest.param("Doc compilation will be done via sphinx.", id="tamr-0004-doc-compilation"),
    pytest.param("Type-check via mypy.", id="tamr-0006-type-check"),
    pytest.param("Use Black code formatter.", id="openlobby-0013-formatter"),
    pytest.param("We need to choose main programming language for this project.", id="openlobby-0005-language"),
    pytest.param("We need to choose framework for tests.", id="openlobby-0008-test-framework"),
    pytest.param("Pytest will be our test framework.", id="generic-test-framework"),
    pytest.param(
        "Manage dependencies via poetry. Define tests via nox. "
        "Run tests in automation/CI via Github Actions.",
        id="tamr-0003-ci",
    ),
]


@pytest.mark.parametrize("adr_text", TOOLING_ADR_FRAGMENTS)
def test_tooling_adr_fragments_classify_as_tooling(adr_text: str) -> None:
    assert classify_adr_scope(adr_text) is ConstraintScope.TOOLING


# -- Negative calibration: runtime ADRs that brush against tooling vocabulary --

RUNTIME_ADR_FRAGMENTS = [
    pytest.param(
        "Metadata implementations and wire formats. The wire format is decoupled "
        "from the class model.",
        id="tuf-0006-wire-formats",
    ),
    pytest.param("Strict mapping to the Document formats in the specification.", id="tuf-0009-document-formats"),
    pytest.param("Saves a lot of time of writing API documentation.", id="openlobby-0004-api-documentation"),
    pytest.param("Use Elasticsearch for fulltext search over the lobby data.", id="openlobby-0002-elasticsearch"),
    pytest.param("", id="empty"),
]


@pytest.mark.parametrize("adr_text", RUNTIME_ADR_FRAGMENTS)
def test_runtime_adr_fragments_stay_runtime(adr_text: str) -> None:
    assert classify_adr_scope(adr_text) is ConstraintScope.RUNTIME


# -- ConstraintEdge carries the tag (back-compat default) ---------------------

def _edge(predicate: PredicateType, object_: str, scope: ConstraintScope | None = None) -> ConstraintEdge:
    kwargs = {} if scope is None else {"scope": scope}
    return ConstraintEdge(
        subject="app.api.*",
        predicate=predicate,
        object=object_,
        justification="pin fixture",
        adr_id="ADR-0001",
        adr_path="docs/adr/0001-pin.md",
        **kwargs,
    )


def test_constraint_edge_defaults_to_runtime_scope() -> None:
    """Every existing constructor site (connector read-back, pipeline rebuild)
    must keep working untagged: runtime is the default."""
    assert _edge(PredicateType.PROHIBITS_DEPENDENCY, "app.db.*").scope is ConstraintScope.RUNTIME


def test_constraint_edge_carries_tooling_scope() -> None:
    assert _edge(PredicateType.REQUIRES_DEPENDENCY, "black", ConstraintScope.TOOLING).scope is ConstraintScope.TOOLING


# -- Eval accounting: tooling edges are excluded from FP by declared scope ----

def test_eval_excludes_tooling_edges_from_false_positives(monkeypatch) -> None:
    """#136 tag-not-skip at the scoring seam: an unmatched TOOLING edge lands
    in excluded_tooling_edges (itemized, reversible) instead of the FP count,
    an unmatched RUNTIME edge still counts as FP, and matching stays
    scope-blind (a tooling-tagged edge can still satisfy a gold row, e.g.
    language-version constraints gold-sanctioned in tuf ADR-0001)."""
    monkeypatch.setenv("ABLATION_SEARCH_OFF", "1")
    edges = [
        # matches the gold row; scope-blind matching must not care
        _edge(PredicateType.REQUIRES_DEPENDENCY, "app.db.*", ConstraintScope.TOOLING),
        # unmatched tooling: excluded by declared scope, not an FP
        _edge(PredicateType.REQUIRES_DEPENDENCY, "black", ConstraintScope.TOOLING),
        # unmatched runtime: still an FP
        _edge(PredicateType.PROHIBITS_DEPENDENCY, "rest_framework"),
    ]
    monkeypatch.setattr(harness, "resolve_adr_constraints", lambda **kwargs: list(edges))
    ground_truth = [{
        "adr_id": "ADR-001",
        "adr_path": "docs/adr/001-layered-architecture.md",
        "constraints": [{"subject": "app.api.*", "predicate": "requires_dependency", "object": "app.db.*"}],
    }]

    result = harness.run_eval(ground_truth, adg=None, repo_id="flask", report_to_disk=False)

    assert result.exact == 1  # the tooling-tagged edge still satisfies the gold row
    assert result.false_positives == 1  # the runtime edge only
    assert [e["object"] for e in result.excluded_tooling_edges] == ["black"]
    assert "excluded_tooling_edges" in result.to_report()
