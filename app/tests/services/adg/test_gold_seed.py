"""#167: the gold seed path carries exactly the benchmark gold, per repo.

No LLM, no Neo4j, no repo checkout: this pins the gold -> ConstraintEdge
conversion that `cpt seed build --gold` uses, the repo -> gold file map, and
the census §5 pins, so a seed that drifts from the gold is caught before a
two-arm run is spent on it.
"""
from __future__ import annotations

import pytest

from services.adg import gold
from services.models import ADG, ConstraintEdge, PredicateType
from services.pipeline import ADGPipeline

BENCHMARK_REPOS = ["python-tuf", "flowkit", "experimenter", "structurizr-python", "home-assistant"]

# census §5 / issue #167: 4 + 6 + 4 + 2 + 2 = 18
GOLD_COUNTS = {
    "python-tuf": 4,
    "flowkit": 6,
    "experimenter": 4,
    "structurizr-python": 2,
    "home-assistant": 2,
}


@pytest.mark.parametrize("repo", BENCHMARK_REPOS)
def test_build_gold_seed_carries_exactly_the_gold(repo: str) -> None:
    """The seed's constraint set == the gold's, subject/predicate/object identical."""
    seed = ADGPipeline.build_gold_seed(ADG(), gold.gold_path(repo))

    assert len(seed.constraint_edges) == GOLD_COUNTS[repo]
    assert gold.triples(seed.constraint_edges) == gold.gold_triples(repo)
    assert gold.triple_differences(gold.gold_triples(repo), gold.triples(seed.constraint_edges)) == ([], [])


def test_gold_total_is_18() -> None:
    total = sum(len(gold.gold_triples(repo)) for repo in BENCHMARK_REPOS)
    assert total == 18


@pytest.mark.parametrize("repo", BENCHMARK_REPOS)
def test_every_repo_has_a_full_sha_pin(repo: str) -> None:
    assert len(gold.GOLD_PINS[repo]) == 40


def test_home_assistant_adrs_have_their_own_pin() -> None:
    """HA's ADRs come from the separate ADR repo (census §5), so both pins exist."""
    assert len(gold.GOLD_ADR_PINS["home-assistant"]) == 40
    assert gold.GOLD_ADR_PINS["home-assistant"] != gold.GOLD_PINS["home-assistant"]


def test_a_disagreeing_seed_is_named_not_counted() -> None:
    """A seed missing a gold constraint and carrying a stranger names both."""
    expected = gold.gold_triples("python-tuf")
    stranger = ConstraintEdge(
        subject="tuf.*", predicate=PredicateType.PROHIBITS_DEPENDENCY, object="numpy",
        justification="not in the gold", adr_id="ADR-9999", adr_path="docs/adr/9999.md",
    )
    actual = gold.triples(gold.load_gold_edges(gold.gold_path("python-tuf"))[1:] + [stranger])

    missing, extra = gold.triple_differences(expected, actual)

    assert missing == [("ADR-0001", "prohibits_dependency", "tuf.*", "python2.7")]
    assert extra == [("ADR-9999", "prohibits_dependency", "tuf.*", "numpy")]
