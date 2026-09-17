"""ConstraintEdge scope pins + the eval-accounting seam (issue #136 decision (a)).

Tooling/CI constraints live in pyproject.toml / setup.cfg / noxfile, never in
the governed package's import graph, so the eval holds them out of scope by
declaration. Scope is now a per-edge verdict produced by the resolver's LLM
session (ADR 019, issue #157); the old whole-ADR `classify_adr_scope` regex and
its role-word calibration tests are deleted. The calibration *intentions* moved
to the corpus pins in `test_scope_corpus.py`; what stays here is the
scoring-side seam that never depended on the classifier:

- `ConstraintEdge` carries the tag with a back-compat `runtime` default;
- an unmatched TOOLING edge lands in `excluded_tooling_edges` (itemized,
  reversible), an unmatched RUNTIME edge still counts as FP, and matching stays
  scope-blind (a tooling-tagged edge can still satisfy a gold row).
"""
from __future__ import annotations

from services.models import ConstraintEdge, ConstraintScope, PredicateType
from tests.services.adg import test_unified_resolver_eval as harness


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
