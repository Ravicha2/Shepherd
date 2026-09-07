"""Scorer rule pins for issue #134 (no LLM, no API key).

Two false-positive classes fixed harness-side in test_unified_resolver_eval:
- Many-to-one consolidation: a resolved fragment whose subject is a child of an
  expected row's subject prefix (same predicate, object not a miss) credits that
  row instead of counting as a false positive — tamr ADR-0009's single mandate
  arrives as 10 per-module requires edges against one broad gold row.
- Object-side ancestor tolerance: `X.*` (subtree wildcard) partial-matches the
  bare module `X`, mirroring the cpt engine's requires-satisfaction tolerance
  (engine.py: target == object or target.startswith(object + ".")). Only dotted
  namespaces qualify: `graphql_relay` is a sibling PyPI package, not a descendant
  of `graphene`, and must stay a miss.

Fragment identities below are the 2026-09-07T13-51-14 baseline's ADR-0009 edges;
the expected row is the gold constraint from tamr_client_ground_truth.json.
"""
from __future__ import annotations

from services.models import ConstraintEdge, PredicateType
from tests.services.adg import test_unified_resolver_eval as harness


ADR9_EXPECTED = {
    "subject": "tamr_client.*",
    "predicate": "requires_dependency",
    "object": "tamr_client._types",
}

ADR9_FRAGMENT_SUBJECTS = [
    "tamr_client.backup.*",
    "tamr_client.categorization.*",
    "tamr_client.dataset.*",
    "tamr_client.golden_records.*",
    "tamr_client.instance.*",
    "tamr_client.mastering.*",
    "tamr_client.operation.*",
    "tamr_client.project.*",
    "tamr_client.schema_mapping.*",
    "tamr_client.transformations.*",
]


def _edge(subject: str, predicate: PredicateType, object_: str) -> ConstraintEdge:
    return ConstraintEdge(
        subject=subject,
        predicate=predicate,
        object=object_,
        justification="pin fixture",
        adr_id="ADR-0009",
        adr_path="docs/contributor-guide/adr/0009-separate-types-and-functions.md",
    )


def _adr9_fragments() -> list[ConstraintEdge]:
    return [_edge(s, PredicateType.REQUIRES_DEPENDENCY, "tamr_client._types.*")
            for s in ADR9_FRAGMENT_SUBJECTS]


# -- Object-side ancestor tolerance -----------------------------------------


def test_subtree_wildcard_of_expected_module_is_partial() -> None:
    # tamr ADR-0009 fragments carry object tamr_client._types.* against gold
    # tamr_client._types: depending on anything inside _types satisfies
    # requires-on-_types, so this is a granularity partial, not a miss.
    assert harness._score_fqn("tamr_client._types.*", "tamr_client._types") == "partial_match"


def test_dotted_descendant_object_is_partial() -> None:
    # openlobby ADR-0012 shape: requires django.db.backends.postgresql against
    # a django.db-level expectation is descendant tolerance (cpt engine rule).
    assert harness._score_fqn("django.db.backends.postgresql", "django.db") == "partial_match"


def test_underscore_sibling_package_is_not_ancestor() -> None:
    # graphql-relay and graphene-django are sibling PyPI packages; underscore is
    # not a namespace separator, so neither is credited against graphene.
    assert harness._score_fqn("graphql_relay", "graphene") == "miss"
    assert harness._score_fqn("graphene_django", "graphene") == "miss"


# -- Many-to-one consolidation ----------------------------------------------


def test_adr9_fragments_credit_the_broad_row() -> None:
    fragments = _adr9_fragments()
    for fragment in fragments:
        assert harness._is_credited_fragment(fragment, [ADR9_EXPECTED]), fragment.subject


def test_broad_row_scores_partial_not_miss() -> None:
    # With object-side tolerance the fragments lift the broad gold row from
    # miss to partial (subject child of the prefix, object subtree wildcard).
    score, _ = harness._score_constraint(ADR9_EXPECTED, _adr9_fragments())
    assert score == "partial_match"


def test_consolidation_requires_same_predicate() -> None:
    fragment = _edge("tamr_client.backup.*", PredicateType.PROHIBITS_DEPENDENCY, "tamr_client._types.*")
    assert not harness._is_credited_fragment(fragment, [ADR9_EXPECTED])


def test_consolidation_requires_subject_under_the_expected_prefix() -> None:
    # Sibling root (policy/tooling noise rooted at the client package's sibling)
    sibling = _edge("tamr_unify_client.docs.*", PredicateType.REQUIRES_DEPENDENCY, "tamr_client._types.*")
    assert not harness._is_credited_fragment(sibling, [ADR9_EXPECTED])
    # The expected row's own base (parent, not child) must not be credited either
    parent = _edge("tamr_client", PredicateType.REQUIRES_DEPENDENCY, "tamr_client._types.*")
    assert not harness._is_credited_fragment(parent, [ADR9_EXPECTED])


def test_consolidation_requires_object_not_a_miss() -> None:
    wrong_object = _edge("tamr_client.backup.*", PredicateType.REQUIRES_DEPENDENCY, "tamr_client._beta.*")
    assert not harness._is_credited_fragment(wrong_object, [ADR9_EXPECTED])
