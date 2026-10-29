"""Object-scope extraction (#245/#246): the object parameters a handler loads
and the guards it applies.

Framework idioms only — no case, repo, route or advisory names. Guard
extraction is the deterministic extraction core of the POC-A pre-gate, ported
file-scoped: a handler's decorators and callees are resolved within its own
module. A fetch chain is judged as one unit, a requester filter scopes only on
an ownership field (#253), and a callee parameter bound to a requester
expression at the call site is the requester inside that callee (#257).
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from services.adg.route_inventory import build_route_inventory
from services.models import ADG, Guard
from services.resolver import MatchStatus, fqn_matches_pattern

_FLASK_PARAM = re.compile(r"<(?:(?P<converter>\w+):)?(?P<name>\w+)>")
_FASTAPI_PARAM = re.compile(r"\{(?P<name>\w+)(?::(?P<converter>[^}]*))?\}")
# Converters that hand the handler a non-string, so a comparison with an int
# attribute is not an always-false guard.
_TYPED_CONVERTER = re.compile(r"(?i)^(?:int|uuid|positiveint)$")

# Generic object identifiers: every token is a framework idiom for "the object
# this request names", never a case/repo/route/advisory name (#240).
_OBJECT_PARAM = re.compile(
    r"(?i)^(?:id|pk|uuid|username|slug|key|file|token"
    r"|[a-z][a-z0-9_]*_(?:id|uuid|pk|slug|key))$"
)

# --- guard vocabulary (ported from the POC-A pre-gate) -----------------------
# Generic requester and auth idioms only. No case, repo, route or advisory
# name appears here (#240).
_REQUESTER = re.compile(
    r"(?i)(?:request\.user|request\.session|request\.auth|self\.request|"
    r"current_user)"
)
# A filter value that is the requester's identity, not merely derived from it:
# `request.user` / `request.user.id` scope, `request.user.teammate_ids` does
# not. A list/tuple must be made only of identities.
_REQUESTER_IDENTITY = re.compile(
    r"(?i)^(?:request\.user|self\.request\.user|request\.auth|"
    r"self\.request\.auth|current_user)(?:\.(?:id|pk))?$"
)
_SCOPE_CALL = re.compile(
    r"(?i)(?:has_perm|has_permission|permission_denied|perm_check|check_access|"
    r"allowed_for|object_permission|is_owner|owner_required|filter_access|"
    r"check_object|has_access|verify_access|authori[sz]e)"
)
_COARSE_AUTH = re.compile(
    r"(?i)(?:login_required|permission_required|IsAuthenticated|"
    r"get_current_user|get_verified_user|get_user|CurrentUser|"
    r"PermissionRequired|AuthenticationRequired|LoginRequired)"
)
_TYPED_PARAM = re.compile(r"(?i)\b(?:int|UUID|PositiveInt)\b")
_INT_ATTR = re.compile(r"(?i)\.(?:id|pk|[a-z][a-z0-9_]*_id)$")
# The fetch-chain shape `_assigned_objects` matches (kept in one place).
_FETCH_CALL = re.compile(
    r"(?i)(?:get_object_or_404|get_object|\.get$|\.first$|_by_id$|"
    r"\.filter|\.objects$|^select$)")

# Ownership versus tenancy (#253). Only an ownership field scopes; every other
# binding (tenant, organisation, workspace, ...) passes all members of that
# scope and is exactly the class-(ii) shape: the guard is present and wrong.
# The tenant names below are the vocabulary that shape uses, documented as a
# generic BOLA/CWE-639 idiom -- no case, repo, route or advisory name appears
# here (#240).
_OWNERSHIP_FIELD = re.compile(
    r"(?i)^(?:user|user_id|created_by|created_by_id|owner|owner_id|"
    r"shared|shared_with)$")
_TENANT_FIELD = re.compile(
    r"(?i)^(?:space|space_id|tenant|tenant_id|org|org_id|workspace|"
    r"workspace_id|account|account_id)$")


def _object_path_params(raw_paths: Iterable[str]):
    return (
        match
        for raw_path in raw_paths
        for pattern in (_FLASK_PARAM, _FASTAPI_PARAM)
        for match in pattern.finditer(raw_path)
        if _OBJECT_PARAM.match(match.group("name"))
    )


def object_parameters(raw_paths: Iterable[str]) -> tuple[str, ...]:
    """Object parameter names named by *raw_paths*, first-seen order."""
    return tuple(dict.fromkeys(
        match.group("name") for match in _object_path_params(raw_paths)))


def typed_object_parameters(raw_paths: Iterable[str]) -> tuple[str, ...]:
    """Object parameters the route declares as int/uuid, so never a raw string."""
    return tuple(dict.fromkeys(
        match.group("name") for match in _object_path_params(raw_paths)
        if _TYPED_CONVERTER.match(match.group("converter") or "")))


def object_scope_candidates(
    subject: str,
    adg: ADG,
    surface_files: Iterable[str] | None = None,
) -> int:
    """How many handler nodes with object facts *subject* matches (#255).

    A `requires_object_scope` subject that matches none cannot produce a
    violation at any revision. A row aimed that way reports nothing, so a
    lowering that emits it is a miss, not a clean pass. Pass *surface_files*
    to count only the handlers on the advisory's surface: a subject can match
    handlers elsewhere in the repo and still be aimed where the advisory has
    nothing to find.
    """
    if surface_files is not None:
        # Membership tests run per node; a one-shot iterable would be
        # exhausted by the first one.
        surface_files = set(surface_files)
    return sum(
        1
        for node in adg.nodes
        if node.object_parameters
        and (surface_files is None or node.file_path in surface_files)
        and fqn_matches_pattern(node.fqn, subject) is not MatchStatus.NO_MATCH
    )


# --- guard extraction -------------------------------------------------------
# The extraction core of the POC-A pre-gate (scope_pregate.py), file-scoped:
# handlers and their decorators/callees are resolved within the handler's own
# module. Guards whose definitions live in another module are not walked.
# ponytail: same-module linking; add a repo-wide resolver if a case needs it.

def _dotted(node: ast.AST | None) -> str | None:
    """`a.b.c` for Name/Attribute chains, else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - ast.unparse is total in 3.12
        return ""


def _names_in(node: ast.AST) -> set[str]:
    return {_dotted(n) for n in ast.walk(node)
            if isinstance(n, (ast.Name, ast.Attribute)) and _dotted(n)}


def _mentions(node: ast.AST, tokens: set[str]) -> bool:
    for name in _names_in(node):
        parts = set(re.split(r"[.\[]", name))
        if name in tokens or parts & tokens:
            return True
    return False


def _mentions_requester(node: ast.AST, requester_tokens: set[str] = frozenset()) -> bool:
    """The expression denotes the requester, directly or through a bound parameter.

    A helper receives the requester as a plain parameter (`_read_flow(...,
    current_user.id)` -> `user_id`), so inside that callee the parameter name is
    the requester even though it is not in the vocabulary (#257).
    """
    return bool(_REQUESTER.search(_text(node))) or _mentions(node, requester_tokens)


def _args(func: ast.AST) -> list[ast.arg]:
    return list(getattr(getattr(func, "args", None), "args", []))


def _assigned_objects(func: ast.AST) -> dict[str, ast.AST]:
    """Local names bound to a DB fetch: `o = get_object_or_404(...)`."""
    out: dict[str, ast.AST] = {}
    for node in ast.walk(func):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.Await)):
            continue
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        value = node.value
        if isinstance(value, ast.Await):
            value = value.value
        if not isinstance(value, ast.Call):
            continue
        name = _dotted(value.func) or ""
        if _FETCH_CALL.search(name):
            for target in targets:
                if isinstance(target, ast.Name):
                    out[target.id] = value
    return out


def _find_symbol(tree: ast.Module,
                 dotted: str) -> tuple[ast.AST | None, list[ast.AST]]:
    """Resolve `Class.method` / `func` in a module; a class yields its methods."""
    node: ast.AST = tree
    for part in dotted.split(".") if dotted else []:
        body = getattr(node, "body", [])
        node = next(
            (child for child in body
             if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and child.name == part),
            None,
        )
        if node is None:
            return None, []
    if isinstance(node, ast.ClassDef):
        methods = [n for n in node.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return node, methods
    return node, [node]


def _resolve_handler(tree: ast.Module,
                     handler_fqn: str) -> list[ast.AST]:
    """The handler's own functions, resolving the FQN's longest module suffix."""
    parts = handler_fqn.split(".")
    for cut in range(len(parts)):
        node, funcs = _find_symbol(tree, ".".join(parts[cut:]))
        if node is not None:
            return funcs
    return []


def _kwargs_object_ids(funcs: Iterable[ast.AST]) -> tuple[str, ...]:
    """Object ids a handler's fetch calls read from `kwargs[...]`.

    The key is derived from the fetch's own arguments, so an abbreviated
    identifier is accepted without a vocabulary entry: whatever `kwargs` /
    `self.kwargs` key a load-by-id call reads is an object identifier.
    """
    keys: list[str] = []
    for func in funcs:
        for fetch in _assigned_objects(func).values():
            for node in ast.walk(fetch):
                if not isinstance(node, ast.Subscript):
                    continue
                if _dotted(node.value) not in {"kwargs", "self.kwargs"}:
                    continue
                key = node.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.append(key.value)
    return tuple(dict.fromkeys(keys))


def _handler_object_parameters(tree: ast.Module, handler_fqn: str,
                               path_parameters: Iterable[str]) -> tuple[str, ...]:
    """Route path params plus the ids the handler's fetches read from kwargs."""
    return tuple(dict.fromkeys(
        (*path_parameters, *_kwargs_object_ids(_resolve_handler(tree, handler_fqn)))))


def _converted_params(funcs: list[ast.AST], params: set[str]) -> set[str]:
    """Path params coerced before comparison (`int(user_id)` / `x = int(x)`)."""
    converted: set[str] = set()
    for func in funcs:
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and _dotted(node.func) == "int":
                converted |= {a.id for a in node.args
                              if isinstance(a, ast.Name) and a.id in params}
            if isinstance(node, ast.Assign):
                if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                        and isinstance(node.value, ast.Call)
                        and _dotted(node.value.func) == "int"
                        and any(isinstance(a, ast.Name) and a.id == node.targets[0].id
                                for a in node.value.args)):
                    converted.add(node.targets[0].id)
    return converted


def _typed_params(funcs: list[ast.AST], params: set[str]) -> set[str]:
    """Path params the framework parses as int/UUID, so no string comparison."""
    typed: set[str] = set()
    for func in funcs:
        for arg in _args(func):
            if (arg.arg in params and arg.annotation is not None
                    and _TYPED_PARAM.search(_text(arg.annotation))):
                typed.add(arg.arg)
    return typed


def _parents(func: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(func):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _inside_anonymous_branch(func: ast.AST, node: ast.AST) -> bool:
    """The node sits under an `if not <x>.is_authenticated:` test."""
    parents = _parents(func)
    cur = node
    while cur in parents:
        parent = parents[cur]
        if isinstance(parent, ast.If) and any(
                n is cur or cur in ast.walk(n) for n in parent.body):
            text = _text(parent.test)
            if (re.search(r"(?i)is_authenticated", text)
                    and re.search(r"(?i)\bnot\b", text)):
                return True
        cur = parent
    return False


def _linked_edges(tree: ast.Module,
                  funcs: list[ast.AST],
                  depth: int = 2) -> list[tuple[ast.AST, ast.AST, str, ast.Call | None]]:
    """Handler functions plus decorator/callee functions defined in this module.

    Each entry is (caller, callee, origin symbol, call node): the call node is
    what the caller used, so the requester a callee receives can be read off
    the call site; it is None for a handler and a decorator applied by name.
    """
    defs = {node.name: node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}

    def functions_of(node: ast.AST) -> list[ast.AST]:
        if isinstance(node, ast.ClassDef):
            return [n for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return [node]
        return []

    out = [(func, func, func.name, None) for func in funcs]
    seen = {id(func) for func in funcs}
    frontier = list(out)
    for _ in range(depth):
        nxt: list[tuple[ast.AST, ast.AST, str, ast.Call | None]] = []
        for caller, func, _origin, _call in frontier:
            targets: list[tuple[ast.AST, ast.Call | None]] = []
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                targets.extend(
                    (d.func if isinstance(d, ast.Call) else d,
                     d if isinstance(d, ast.Call) else None)
                    for d in func.decorator_list)
            targets.extend((node.func, node) for node in ast.walk(func)
                           if isinstance(node, ast.Call))
            for target, call in targets:
                name = _dotted(target)
                if not name or "." in name:
                    continue
                node = defs.get(name)
                if node is None:
                    continue
                for callee in functions_of(node):
                    if id(callee) in seen:
                        continue
                    seen.add(id(callee))
                    nxt.append((caller, callee, name, call))
        out.extend(nxt)
        frontier = nxt
        if not nxt:
            break
    return out


def _linked(tree: ast.Module,
            funcs: list[ast.AST],
            depth: int = 2) -> list[tuple[ast.AST, str]]:
    """Handler functions plus decorator/callee functions defined in this module.

    Yields (function, origin symbol): the decorator or call name through which
    the function was reached, so a predicate inside a decorator body is named
    by the decorator the developer applied.
    """
    return [(callee, origin)
            for _caller, callee, origin, _call in _linked_edges(tree, funcs, depth)]


def _requester_bindings(
        edges: list[tuple[ast.AST, ast.AST, str, ast.Call | None]],
) -> dict[int, frozenset[str]]:
    """Per linked function, the parameters a requester expression was passed as.

    The requester is a plain value at the call site (`current_user.id`); inside
    the callee its only name is the parameter that received it. Binding is
    propagated in link order, so a requester passed through one helper reaches
    the next.
    """
    bindings: dict[int, set[str]] = defaultdict(set)
    for caller, callee, _origin, call in edges:
        if call is None:
            continue
        bindings[id(callee)] |= _bound_requester_params(
            callee, call, bindings[id(caller)])
    return {func_id: frozenset(names) for func_id, names in bindings.items()}


def _bound_requester_params(func: ast.AST, call: ast.Call,
                            requester_tokens: set[str]) -> set[str]:
    """The callee parameters the call binds to a requester expression."""
    bound: set[str] = set()
    for arg_node, param in zip(call.args, _args(func)):
        if _mentions_requester(arg_node, requester_tokens):
            bound.add(param.arg)
    for keyword in call.keywords:
        if keyword.arg and _mentions_requester(keyword.value, requester_tokens):
            bound.add(keyword.arg)
    return bound


def _conditional_guard(func: ast.AST, compare: ast.AST) -> bool:
    """A scope comparison that only runs when an object field is truthy."""
    parents = _parents(func)
    node = compare
    while node in parents:
        parent = parents[node]
        # An auth gate on the requester is not an object-field condition: the
        # check still runs for every authenticated caller.
        if (isinstance(parent, ast.If) and parent.test is not compare
                and isinstance(parent.test, (ast.Attribute, ast.Name))
                and not _REQUESTER.search(_text(parent.test))):
            return True
        node = parent
    return False


def extract_guards(source: str, handler_fqn: str,
                   object_parameters: Iterable[str] = (),
                   typed_parameters: Iterable[str] = ()) -> tuple[Guard, ...]:
    """The guards *handler_fqn* applies, as records; first-seen order.

    *typed_parameters* are path params the route converter already parses as
    int/uuid. Deterministic AST analysis only — no LLM, no network.
    """
    return _extract_guards(
        ast.parse(source), handler_fqn, object_parameters, typed_parameters)


def _comparison_guard(func: ast.AST, node: ast.Compare, origin: str,
                      tokens: set[str], params: set[str],
                      converted: set[str], typed: set[str],
                      requester_tokens: set[str]) -> Guard | None:
    text = _text(node)
    if not (_mentions_requester(node, requester_tokens) and _mentions(node, tokens)):
        return None
    conditional = _conditional_guard(func, node)
    sides = [node.left, *node.comparators]
    # The int side must be the requester's own attribute: a model id on an
    # unknown column is not provably an int.
    int_side = next(
        (s for s in sides
         if _INT_ATTR.search(_text(s))
         and _mentions_requester(s, requester_tokens)), None)
    raw_side = next(
        (s for s in sides
         if isinstance(s, ast.Name) and s.id in params
         and s.id not in converted and s.id not in typed), None)
    dead = int_side is not None and raw_side is not None
    return Guard(
        symbol=origin,
        predicate=text,
        scopes_object=not conditional and not dead,
        conditional=conditional,
        dead=dead,
    )


def _call_guard(func: ast.AST, node: ast.Call, tokens: set[str],
                requester_tokens: set[str]) -> Guard | None:
    text = _text(node)
    inner = _dotted(node.func.func) if isinstance(node.func, ast.Call) else None
    if (inner
            and (_COARSE_AUTH.search(inner) or inner.endswith("_required"))
            and any(isinstance(arg, ast.Name)
                    and arg.id in {"func", "view", "handler"}
                    for arg in node.func.args)
            and not _inside_anonymous_branch(func, node)):
        return Guard(symbol=inner, predicate=text, scopes_object=False, bypass=True)
    name = _dotted(node.func) or ""
    if _SCOPE_CALL.search(name) and (
            _mentions(node, tokens) or _mentions_requester(node, requester_tokens)):
        conditional = _conditional_guard(func, node)
        return Guard(
            symbol=name,
            predicate=text,
            scopes_object=not conditional,
            conditional=conditional,
        )
    return None


def _fetch_calls(node: ast.AST) -> list[ast.Call]:
    """The calls along a call chain's spine, outermost first."""
    calls: list[ast.Call] = []
    cur = node
    while True:
        if isinstance(cur, ast.Call):
            calls.append(cur)
            cur = cur.func
        elif isinstance(cur, ast.Attribute):
            cur = cur.value
        else:
            return calls


def _call_attr(call: ast.Call) -> str:
    """The method name a chained call applies (`filter`, `exclude`)."""
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else (_dotted(func) or "")


def _is_fetch_chain(node: ast.Call) -> bool:
    """The chain is rooted in a DB fetch, so it is guarded as one unit."""
    return any(_FETCH_CALL.search(_dotted(call.func) or "")
               for call in _fetch_calls(node))


@dataclass(frozen=True)
class _ChainFacts:
    """What one part of a fetch chain says about the object-scope verdict.

    `object` is an object-identifier selection, `covers` says which route
    object parameters that selection names, `requester` says the requester
    appears at all, and `scope` says a requester filter binds an ownership
    field on the conjunction path. Folding keeps AND/OR/negation structure
    instead of treating the chain's arguments as an unordered bag.
    """

    object: bool = False
    covers: frozenset[str] = frozenset()
    requester: bool = False
    scope: bool = False


# Django lookup suffixes, which name an operator and never a column.
_LOOKUP = re.compile(
    r"(?i)^(?:exact|iexact|contains|icontains|in|gt|gte|lt|lte|startswith|"
    r"istartswith|endswith|iendswith|range|date|year|iso_year|month|day|week|"
    r"week_day|iso_week_day|quarter|time|hour|minute|second|isnull|regex|"
    r"iregex|search|similar|trigram_similar)$")


def _bound_field(parts: list[str]) -> str:
    """The column a `relation__field__lookup` kwarg binds.

    The head names the column on the fetched model (`id__in`), the tail names
    it after relation hops (`user__tenant`). Trailing lookups are stripped so
    `created_by__in` binds `created_by`, not `in`.
    """
    trimmed = list(parts)
    while len(trimmed) > 1 and _LOOKUP.match(trimmed[-1]):
        trimmed.pop()
    return trimmed[-1]


def _referenced_params(node: ast.AST,
                       sources: dict[str, frozenset[str]]) -> frozenset[str]:
    """The route object parameters *node* names, expanding local aliases.

    `item_id`, `kwargs['item_id']`, `int(item_id)` and `oid` (an alias) refer
    to the parameter; `other.id` does not, even when a parameter is called
    `id`. String constants count so `kwargs.get('item_id')` is seen too.
    """
    if isinstance(node, ast.Name):
        return sources.get(node.id, frozenset())
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return sources.get(node.value, frozenset())
        return frozenset()
    if isinstance(node, ast.Attribute):
        name = _dotted(node)
        if name in sources:
            return sources[name]
        return _referenced_params(node.value, sources)
    if isinstance(node, ast.Subscript):
        return (_referenced_params(node.slice, sources)
                | _referenced_params(node.value, sources))
    if isinstance(node, (ast.List, ast.Tuple)):
        found = frozenset()
        for element in node.elts:
            found |= _referenced_params(element, sources)
        return found
    found = frozenset()
    for child in ast.iter_child_nodes(node):
        found |= _referenced_params(child, sources)
    return found


def _param_sources(func: ast.AST,
                   params: set[str]) -> dict[str, frozenset[str]]:
    """Each local name's route object parameters (`oid = int(item_id)`)."""
    sources = {param: frozenset({param}) for param in params}
    # Two hops covers the usual `raw = kwargs['id']; oid = int(raw)`. A longer
    # chain fails safe: the chain does not tie and the handler fires.
    for _ in range(2):
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = (node.target,), node.value
            else:
                continue
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                found = _referenced_params(value, sources)
                if found:
                    sources[targets[0].id] = found
    return sources


def _is_requester_identity(node: ast.AST, requester_tokens: set[str]) -> bool:
    """The value is the requester's identity, not just derived from it."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and all(
            _is_requester_identity(e, requester_tokens) for e in node.elts)
    if isinstance(node, ast.Name) and node.id in requester_tokens:
        return True
    return bool(_REQUESTER_IDENTITY.match(_text(node)))


def _keyword_facts(keyword: ast.keyword, sources: dict[str, frozenset[str]],
                   requester_tokens: set[str]) -> _ChainFacts:
    if not keyword.arg:
        return _ChainFacts()
    parts = keyword.arg.split("__")
    value = keyword.value
    mentions_requester = _mentions_requester(value, requester_tokens)
    selected = bool(_OBJECT_PARAM.match(parts[0])) and not mentions_requester
    return _ChainFacts(
        object=selected,
        covers=_referenced_params(value, sources) if selected else frozenset(),
        requester=mentions_requester,
        scope=(_is_requester_identity(value, requester_tokens)
               and bool(_OWNERSHIP_FIELD.match(_bound_field(parts)))),
    )


def _and_facts(facts: Iterable[_ChainFacts]) -> _ChainFacts:
    out = _ChainFacts()
    for fact in facts:
        out = _ChainFacts(out.object or fact.object, out.covers | fact.covers,
                          out.requester or fact.requester, out.scope or fact.scope)
    return out


def _binds_ownership_field(node: ast.AST) -> bool:
    """The comparison side names an ownership column (`Flow.user_id`)."""
    return bool(_OWNERSHIP_FIELD.match((_dotted(node) or "").rpartition(".")[2]))


def _compare_facts(node: ast.Compare, sources: dict[str, frozenset[str]],
                   requester_tokens: set[str]) -> _ChainFacts:
    """A comparison read as a chain part (SQLAlchemy `where(Model.col == x)`)."""
    sides = [node.left, *node.comparators]
    covers = frozenset()
    for side in sides:
        covers |= _referenced_params(side, sources)
    requester = any(_mentions_requester(side, requester_tokens) for side in sides)
    scopes = (
        len(sides) == 2 and isinstance(node.ops[0], ast.Eq)
        and any(_binds_ownership_field(field)
                and _is_requester_identity(value, requester_tokens)
                for field, value in (sides, list(reversed(sides))))
    )
    return _ChainFacts(
        object=bool(covers), covers=covers, requester=requester, scope=scopes)


def _predicate_facts(node: ast.AST, sources: dict[str, frozenset[str]],
                     requester_tokens: set[str]) -> _ChainFacts:
    """A filter argument read with Django's AND/OR/negation structure."""
    if isinstance(node, ast.keyword):
        return _keyword_facts(node, sources, requester_tokens)
    if isinstance(node, ast.Compare):
        return _compare_facts(node, sources, requester_tokens)
    if isinstance(node, ast.Call):
        name = _dotted(node.func) or ""
        if name == "Q" or name.endswith(".Q"):
            return _and_facts(
                _predicate_facts(child, sources, requester_tokens)
                for child in (*node.args, *node.keywords))
        # A queryset passed inline (`get_object_or_404(Model.objects.filter(
        # ...), pk=...)`) carries the requester filter in its own arguments.
        if _is_fetch_chain(node):
            return _and_facts(
                _predicate_facts(child, sources, requester_tokens)
                for child in (*node.args, *node.keywords))
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd):
        return _and_facts((_predicate_facts(node.left, sources, requester_tokens),
                           _predicate_facts(node.right, sources, requester_tokens)))
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _predicate_facts(node.left, sources, requester_tokens)
        right = _predicate_facts(node.right, sources, requester_tokens)
        merged = _and_facts((left, right))
        # An OR branch that selects by object id bypasses the ownership
        # branch: the object is reachable without the requester filter.
        if merged.object and merged.requester:
            merged = _ChainFacts(merged.object, merged.covers,
                                 merged.requester, False)
        return merged
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
        inner = _predicate_facts(node.operand, sources, requester_tokens)
        return _ChainFacts(False, frozenset(), inner.requester, False)
    return _ChainFacts()


def _chain_guard(func: ast.AST, node: ast.Call, origin: str,
                 params: set[str],
                 sources: dict[str, frozenset[str]],
                 requester_tokens: set[str]) -> Guard | None:
    """A fetch chain judged as one guard: object id + requester filter (#253).

    The chain is the unit a developer writes and reads. Its links are split
    across `filter(...)` / `values_list(...)` / `Q(...)` calls, so judging a
    sub-expression alone loses the pairing: a requester filter in one clause
    and an object identifier in another. A requester filter scopes only when
    it binds an ownership field; binding a tenant field passes every member of
    the tenant and is the class-(ii) shape this slice targets. `exclude(...)`
    and `~Q(...)` negate, and an OR with the object identifier lets that branch
    bypass the requester, so neither scopes (#263 review).
    """
    facts = _ChainFacts()
    for call in _fetch_calls(node):
        inner = _and_facts(
            _predicate_facts(arg, sources, requester_tokens)
            for arg in (*call.args, *call.keywords))
        if _call_attr(call) == "exclude":
            # Excluded conditions hold everywhere except the excluded set, so
            # they never scope. The chain still touches the object it names:
            # `filter(owner=request.user).exclude(pk=item_id)` scopes.
            inner = _ChainFacts(inner.object, inner.covers, inner.requester, False)
        facts = _and_facts((facts, inner))
    if not (facts.object and facts.requester):
        return None
    conditional = _conditional_guard(func, node)
    # A chain scopes the handler's own object. With route object parameters
    # present the identifier must name one; without them there is nothing to
    # tie the chain to (#263 review).
    tied = bool(facts.covers) or not params
    scopes = facts.scope and tied and not conditional
    return Guard(
        symbol=origin,
        predicate=_text(node),
        scopes_object=scopes,
        conditional=conditional,
        # Only a scoping chain covers; empty covers every parameter, which is
        # the right reading when the handler has no route object parameters.
        covers=tuple(sorted(facts.covers)) if scopes else (),
    )


def _chain_guards(func: ast.AST, chain_mid: set[int], origin: str,
                  params: set[str],
                  sources: dict[str, frozenset[str]],
                  requester_tokens: set[str]) -> dict[int, Guard | None]:
    """The outermost fetch chains of *func*, judged as units."""
    return {
        id(node): _chain_guard(func, node, origin, params, sources,
                               requester_tokens)
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and id(node) not in chain_mid
        and _is_fetch_chain(node)
    }


def _chain_parts(func: ast.AST, chain_guards: dict[int, Guard | None]) -> set[int]:
    """Comparisons inside a judged fetch chain are its parts, not its guard."""
    return {
        id(inner) for node in ast.walk(func)
        if isinstance(node, ast.Call) and chain_guards.get(id(node))
        for inner in ast.walk(node) if isinstance(inner, ast.Compare)
    }


def _guards_in(func: ast.AST, origin: str, tokens: set[str], params: set[str],
               converted: set[str], typed: set[str],
               requester_tokens: set[str]) -> list[Guard]:
    parents = _parents(func)
    # Only the outermost call of a chain carries the whole query text.
    chain_mid = {id(node) for node in ast.walk(func)
                 if isinstance(node, ast.Call)
                 and isinstance(parents.get(node), ast.Attribute)
                 and parents[node].value is node}
    chain_guards = _chain_guards(
        func, chain_mid, origin, params, _param_sources(func, params),
        requester_tokens)
    parts = _chain_parts(func, chain_guards)
    guards: list[Guard] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare):
            if id(node) in parts:
                continue
            guard = _comparison_guard(func, node, origin, tokens, params,
                                      converted, typed, requester_tokens)
        elif isinstance(node, ast.Call) and id(node) not in chain_mid:
            guard = chain_guards.get(id(node)) or _call_guard(
                func, node, tokens, requester_tokens)
        else:
            continue
        if guard is not None:
            guards.append(guard)
    return guards


def _extract_guards(tree: ast.Module, handler_fqn: str,
                    object_parameters: Iterable[str],
                    typed_parameters: Iterable[str] = ()) -> tuple[Guard, ...]:
    edges = _linked_edges(tree, _resolve_handler(tree, handler_fqn))
    bindings = _requester_bindings(edges)
    funcs = [callee for _caller, callee, _origin, _call in edges]
    params = set(object_parameters) | set(_kwargs_object_ids(funcs))
    objects = {name for func in funcs for name in _assigned_objects(func)}
    tokens = params | objects
    converted = _converted_params(funcs, params)
    typed = _typed_params(funcs, params) | set(typed_parameters)
    guards = [
        guard
        for _caller, func, origin, _call in edges
        for guard in _guards_in(
            func, origin, tokens, params, converted, typed,
            set(bindings.get(id(func), ())))
    ]
    return tuple(dict.fromkeys(guards))


def _defining_handler(adg: ADG, handler_fqn: str) -> str | None:
    """The node that defines *handler_fqn*, following INHERITS when it is absent.

    A route names `ViewSet.download`; the method may live on a mixin or base
    class. Breadth-first over the class's bases keeps the nearest definition
    first, so an override on the class itself always wins (and is found by the
    membership check before any base is visited).
    """
    if handler_fqn in adg.node_of:
        return handler_fqn
    class_fqn, _, method = handler_fqn.rpartition(".")
    if not class_fqn:
        return None
    queue = [class_fqn]
    seen = {class_fqn}
    while queue:
        cls = queue.pop(0)
        candidate = f"{cls}.{method}"
        if candidate in adg.node_of:
            return candidate
        for edge in adg.edges_from(cls, "INHERITS"):
            if edge.target not in seen:
                seen.add(edge.target)
                queue.append(edge.target)
    return None


def backfill_handler_facts(adg: ADG, repo_path: Path) -> ADG:
    """Return a new ADG with handler nodes carrying their object params + guards.

    Post-parse pass: the inventory join needs the finished ADG
    (`build_route_inventory(repo_path, adg=adg)`), so this cannot run inside
    the treesitter walk (#245). Node count and every other field are unchanged.

    Route facts are attributed to the node that defines the handler: when the
    inventory FQN has no node (a method inherited from a mixin or base class),
    the defining node is resolved through INHERITS (#254).
    """
    inventory = build_route_inventory(repo_path, adg=adg)
    paths_by_handler: dict[str, list[str]] = defaultdict(list)
    for route in inventory.routes:
        defining = _defining_handler(adg, route.handler_fqn)
        if defining is not None:
            paths_by_handler[defining].append(route.raw_path)

    trees: dict[str, ast.Module | None] = {}

    def facts(handler: str, file_path: str) -> tuple[tuple[str, ...], tuple[Guard, ...]]:
        paths = paths_by_handler[handler]
        if file_path not in trees:
            try:
                trees[file_path] = ast.parse((repo_path / file_path).read_bytes())
            except (OSError, SyntaxError):
                trees[file_path] = None
        tree = trees[file_path]
        if tree is None:
            return object_parameters(paths), ()
        params = _handler_object_parameters(tree, handler, object_parameters(paths))
        typed = typed_object_parameters(paths)
        guards = _extract_guards(tree, handler, params, typed)
        return params, guards

    updated = []
    for node in adg.nodes:
        handler = str(node.fqn)
        if handler in paths_by_handler:
            params, guards = facts(handler, node.file_path)
            updated.append(replace(node, object_parameters=params, guards=guards))
        else:
            updated.append(node)
    return adg.replace(nodes=tuple(updated))
