"""Object grounding at the pinned BAC-BENCH revisions (#256).

Two #249 gate rows were called orphans for grounding reasons, not because the
rows were wrong:

- langflow emits `langflow.services.auth.service`, which exists at the SHA but
  below the repo's `src.backend.base` root — a unique suffix, not an orphan.
- tandoor emits `rest_framework.permissions`, a genuine third-party package —
  external, not an orphan.

`ground_object` is the shared classifier: exact > unique suffix > internal
prefix > external package > unknown. Every label except `unknown` counts as
grounded (an external package is a label, not an orphan). These tests pin the
two real shapes; the classifier's unit behaviour is in test_unified_resolver.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.adg import parse_repo
from services.adg.route_inventory import repo_at_sha
from services.adg.unified_resolver import ground_object

BACBENCH_REPOS = (
    Path(__file__).resolve().parents[5]
    / "research-exp-setup" / "security" / "data" / "repos"
)

LANGFLOW_OBJECT = "langflow.services.auth.service"
LANGFLOW_RESOLVED = "src.backend.base.langflow.services.auth.service"
TANDOOR_OBJECT = "rest_framework.permissions"


def _adg(repo: str, sha: str):
    root = BACBENCH_REPOS / repo
    if not root.exists():
        pytest.skip(f"{root} is not present (run #221's mirror)")
    with repo_at_sha(root, sha) as tree:
        return parse_repo(tree)


@pytest.mark.integration
def test_langflow_object_grounds_by_unique_suffix() -> None:
    """#249 cause 2: the object is real, just not rooted where the ADG is."""
    adg = _adg("langflow", "73c1f203b0205d00928a0af7fa0e0fc93170f03e")

    grounding = ground_object(LANGFLOW_OBJECT, adg)

    assert grounding.label == "unique_suffix"
    assert grounding.resolved_fqn == LANGFLOW_RESOLVED
    assert grounding.grounded is True


@pytest.mark.integration
def test_tandoor_object_is_external_not_orphan() -> None:
    """#249 cause 3: a third-party package is external, the honest label."""
    adg = _adg("recipes", "0b363fb6100e0c5d0044f60f64c0c285f86c786b")

    grounding = ground_object(TANDOOR_OBJECT, adg)

    assert grounding.label == "external"
    assert grounding.package == "rest_framework"
    assert grounding.resolved_fqn is None
    assert grounding.grounded is True


@pytest.mark.integration
def test_an_invented_object_stays_ungrounded() -> None:
    """The check that must keep failing: a name that matches nothing."""
    adg = _adg("langflow", "73c1f203b0205d00928a0af7fa0e0fc93170f03e")

    grounding = ground_object("totally_invented.module", adg)

    assert grounding.label == "unknown"
    assert grounding.grounded is False
