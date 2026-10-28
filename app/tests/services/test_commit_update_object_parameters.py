"""#245: `cpt update` re-parses and restores handler object parameters.

The incremental path must not silently drop the facts the seed build gained.
Integration tests — require the test Neo4j instance.
"""

from __future__ import annotations

import pytest

from services.adg.treesitter import parse_repo
from services.commit_update import commit_update
from services.models import ADG, ConstraintEdge, PredicateType


@pytest.mark.integration
def test_object_parameters_survive_commit_update(neo4j_store, flask_repo) -> None:
    adg = parse_repo(flask_repo)
    guard = ConstraintEdge(
        subject="app.routes.*",
        predicate=PredicateType.PROHIBITS_DEPENDENCY,
        object="logging",
        justification="No bare logging.",
        adr_id="ADR-005",
        adr_path="docs/adr/005.md",
        specificity=2.0,
    )
    neo4j_store.store_adg(ADG(nodes=adg.nodes, edges=adg.edges, constraint_edges=[guard]))

    commit_update(neo4j_store, flask_repo, to_sha=None)

    loaded = neo4j_store.load_adg().node_of["app.routes.users.get_user_route"]
    assert loaded.object_parameters == ("user_id",)
