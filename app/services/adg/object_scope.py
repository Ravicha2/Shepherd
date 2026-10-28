"""Object-scope extraction (#245): the object parameters a handler loads.

Framework idioms only — no case, repo, route or advisory names. Slice 1
covers parameters named by the route path; guards land in a later slice.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from services.adg.route_inventory import build_route_inventory
from services.models import ADG

_FLASK_PARAM = re.compile(r"<(?:\w+:)?(?P<name>\w+)>")
_FASTAPI_PARAM = re.compile(r"\{(?P<name>\w+)(?::[^}]*)?\}")

# Generic object identifiers: every token is a framework idiom for "the object
# this request names", never a case/repo/route/advisory name (#240).
_OBJECT_PARAM = re.compile(
    r"(?i)^(?:id|pk|uuid|username|slug|key|file|token"
    r"|[a-z][a-z0-9_]*_(?:id|uuid|pk|slug|key))$"
)


def object_parameters(raw_paths: Iterable[str]) -> tuple[str, ...]:
    """Object parameter names named by *raw_paths*, first-seen order."""
    names = (
        match.group("name")
        for raw_path in raw_paths
        for pattern in (_FLASK_PARAM, _FASTAPI_PARAM)
        for match in pattern.finditer(raw_path)
        if _OBJECT_PARAM.match(match.group("name"))
    )
    return tuple(dict.fromkeys(names))


def backfill_object_parameters(adg: ADG, repo_path: Path) -> ADG:
    """Return a new ADG with handler nodes carrying their route object params.

    Post-parse pass: the inventory join needs the finished ADG
    (`build_route_inventory(repo_path, adg=adg)`), so this cannot run inside
    the treesitter walk (#245). Node count and every other field are unchanged.
    """
    inventory = build_route_inventory(repo_path, adg=adg)
    paths_by_handler: dict[str, list[str]] = defaultdict(list)
    for route in inventory.routes:
        paths_by_handler[route.handler_fqn].append(route.raw_path)

    facts = {fqn: object_parameters(paths) for fqn, paths in paths_by_handler.items()}
    return adg.replace(nodes=tuple(
        replace(node, object_parameters=facts[str(node.fqn)])
        if str(node.fqn) in facts else node
        for node in adg.nodes
    ))
