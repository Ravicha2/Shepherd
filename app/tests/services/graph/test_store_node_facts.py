"""#245/#246: handler object parameters and guards survive the Neo4j round-trip.

Integration tests — require the test Neo4j instance (`neo4j_store`).
"""

from __future__ import annotations

import pytest

from services.fqn import FQN
from services.models import FQNKind, FQNNode, Guard


@pytest.mark.integration
def test_handler_facts_round_trip(neo4j_store) -> None:
    handler = FQNNode(
        fqn=FQN.from_dotted("app.views.get_user"),
        kind=FQNKind.FUNCTION,
        file_path="app/views.py",
        line_start=0,
        line_end=3,
        object_parameters=("user_id", "pk"),
        guards=(
            Guard(
                symbol="self.perm_check",
                predicate="self.perm_check(request, obj)",
                scopes_object=True,
            ),
            Guard(
                symbol="login_required",
                predicate="login_required(func)(request, user_id)",
                scopes_object=False,
                bypass=True,
            ),
        ),
    )
    plain = FQNNode(
        fqn=FQN.from_dotted("app.views.index"),
        kind=FQNKind.FUNCTION,
        file_path="app/views.py",
        line_start=4,
        line_end=7,
    )

    neo4j_store.store_node(handler)
    neo4j_store.store_node(plain)
    loaded = neo4j_store.load_adg().node_of

    assert loaded["app.views.get_user"].object_parameters == ("user_id", "pk")
    assert loaded["app.views.get_user"].guards == handler.guards
    assert loaded["app.views.index"].object_parameters == ()
    assert loaded["app.views.index"].guards == ()
