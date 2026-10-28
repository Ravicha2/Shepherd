"""Object-scope extraction (#245/#246): the object parameters a handler loads
and the guards it applies.

Framework idioms only — no case, repo, route or advisory names. Guard
extraction is the deterministic extraction core of the POC-A pre-gate, ported
file-scoped: a handler's decorators and callees are resolved within its own
module.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from services.adg.route_inventory import build_route_inventory
from services.models import ADG, Guard

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
        if re.search(r"(?i)(?:get_object_or_404|get_object|\.get$|\.first$|_by_id$|"
                     r"\.filter|\.objects$|^select$)", name):
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


def _linked(tree: ast.Module,
            funcs: list[ast.AST],
            depth: int = 2) -> list[tuple[ast.AST, str]]:
    """Handler functions plus decorator/callee functions defined in this module.

    Yields (function, origin symbol): the decorator or call name through which
    the function was reached, so a predicate inside a decorator body is named
    by the decorator the developer applied.
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

    out = [(func, func.name) for func in funcs]
    seen = {id(func) for func in funcs}
    frontier = list(out)
    for _ in range(depth):
        nxt: list[tuple[ast.AST, str]] = []
        for func, _origin in frontier:
            targets: list[ast.AST] = []
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                targets.extend(d.func if isinstance(d, ast.Call) else d
                               for d in func.decorator_list)
            targets.extend(node.func for node in ast.walk(func)
                           if isinstance(node, ast.Call))
            for target in targets:
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
                    nxt.append((callee, name))
        out.extend(nxt)
        frontier = nxt
        if not nxt:
            break
    return out


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
                      converted: set[str], typed: set[str]) -> Guard | None:
    text = _text(node)
    if not (_REQUESTER.search(text) and _mentions(node, tokens)):
        return None
    conditional = _conditional_guard(func, node)
    sides = [node.left, *node.comparators]
    # The int side must be the requester's own attribute: a model id on an
    # unknown column is not provably an int.
    int_side = next(
        (s for s in sides
         if _INT_ATTR.search(_text(s)) and _REQUESTER.search(_text(s))), None)
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


def _call_guard(func: ast.AST, node: ast.Call, tokens: set[str]) -> Guard | None:
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
            _mentions(node, tokens) or _REQUESTER.search(text)):
        conditional = _conditional_guard(func, node)
        return Guard(
            symbol=name,
            predicate=text,
            scopes_object=not conditional,
            conditional=conditional,
        )
    return None


def _guards_in(func: ast.AST, origin: str, tokens: set[str], params: set[str],
               converted: set[str], typed: set[str]) -> list[Guard]:
    parents = _parents(func)
    # Only the outermost call of a chain carries the whole query text.
    chain_mid = {id(node) for node in ast.walk(func)
                 if isinstance(node, ast.Call)
                 and isinstance(parents.get(node), ast.Attribute)
                 and parents[node].value is node}
    guards: list[Guard] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare):
            guard = _comparison_guard(func, node, origin, tokens, params, converted, typed)
        elif isinstance(node, ast.Call) and id(node) not in chain_mid:
            guard = _call_guard(func, node, tokens)
        else:
            continue
        if guard is not None:
            guards.append(guard)
    return guards


def _extract_guards(tree: ast.Module, handler_fqn: str,
                    object_parameters: Iterable[str],
                    typed_parameters: Iterable[str] = ()) -> tuple[Guard, ...]:
    linked = _linked(tree, _resolve_handler(tree, handler_fqn))
    funcs = [func for func, _origin in linked]
    params = set(object_parameters) | set(_kwargs_object_ids(funcs))
    objects = {name for func in funcs for name in _assigned_objects(func)}
    tokens = params | objects
    converted = _converted_params(funcs, params)
    typed = _typed_params(funcs, params) | set(typed_parameters)
    guards = [
        guard
        for func, origin in linked
        for guard in _guards_in(func, origin, tokens, params, converted, typed)
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
