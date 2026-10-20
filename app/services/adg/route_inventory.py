"""Route inventory: a deterministic derived view over the ADG (ADR 021).

Enumerates the HTTP request surface as route -> handler -> module. Decorator
registration only for now (FastAPI and Flask). Guards are deliberately not
extracted: decorator stacks and permission classes are the reading agent's job.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from tree_sitter import Parser

from services.adg.treesitter import PY_LANGUAGE, parse_repo, python_files
from services.fqn import FQN
from services.models import ADG

PARAM = "{}"

# Flask: <int:user_id>, <path:filename>, <any(css,js):filename>, <name>.
_FLASK_PARAM = re.compile(r"<[^<>]+>")
# FastAPI/Starlette: {user_id}, {file_path:path}.
_FASTAPI_PARAM = re.compile(r"\{[^{}]+\}")
# Django re_path: (?P<id>\d+) and unnamed alternatives (live|latest). Groups
# are matched innermost-first so a simple regex need not balance parentheses.
# ponytail: `[^()]*` stops at any inner paren, and named/non-capturing groups
# are not revisited after `_REGEX_GROUP` strips their interior, so a nested
# `(?P<slug>(a|b))` stays uncanonicalised. Ceiling is flat Django patterns;
# upgrade to a paren-counting scanner if nested named groups start mattering.
_REGEX_NAMED_GROUP = re.compile(r"\(\?P<[^>]+>[^()]*\)")
_REGEX_NONCAPTURING = re.compile(r"\(\?:[^()]*\)")
_REGEX_GROUP = re.compile(r"\((?!\?)[^()]*\)")
_REGEX_ESCAPE = re.compile(r"\\(.)")

_HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options"}
_ROUTE_DECORATORS = {"route", "api_route"}
_DEFINITION_TYPES = {"function_definition", "class_definition"}
# Registrations made by a call in a body rather than a decorator. They are out
# of scope for the decorator enumerator, but must still be visible as gaps.
_CALL_FORM_REGISTRATIONS = {
    "add_url_rule", "add_api_route", "add_api_websocket_route", "add_route",
}
_PATH_KEYWORDS = ("path", "rule")


def canonical_path(raw_path: str) -> str:
    """Strip converter types and parameter names; literal segments survive.

    `<int:user_id>`, `{user_id}` and Django's `(?P<id>\\d+)` all become `{}`,
    so a path() route and a re_path() route with the same shape canonicalize
    identically. Anchors and regex escapes are stripped; an empty path is `/`.
    """
    if raw_path.startswith("^"):
        raw_path = raw_path[1:]
    if raw_path.endswith("$"):
        raw_path = raw_path[:-1]
    pattern = raw_path
    for group in (_REGEX_NAMED_GROUP, _REGEX_NONCAPTURING, _REGEX_GROUP):
        while group.search(pattern):
            pattern = group.sub(PARAM, pattern)
    pattern = _REGEX_ESCAPE.sub(r"\1", pattern)
    pattern = _FASTAPI_PARAM.sub(PARAM, _FLASK_PARAM.sub(PARAM, pattern))
    if not pattern.startswith("/"):
        pattern = "/" + pattern
    return pattern


def structural_match(path_a: str, path_b: str) -> bool:
    """Compare canonical paths segment by segment.

    Literal segments must be equal; a parameter segment matches a parameter
    segment regardless of its name or converter. Never raw-string equality.
    """
    segments_a = canonical_path(path_a).split("/")
    segments_b = canonical_path(path_b).split("/")
    return len(segments_a) == len(segments_b) and all(
        left == right or (left == PARAM and right == PARAM)
        for left, right in zip(segments_a, segments_b)
    )


@dataclass(frozen=True)
class RouteEvidence:
    file_path: str
    line: int  # 1-based, pointing at the decorator


@dataclass(frozen=True)
class RouteRecord:
    methods: tuple[str, ...]
    raw_path: str
    canonical_path: str
    handler_fqn: str
    module: str
    registration_kind: str
    evidence: RouteEvidence


@dataclass(frozen=True)
class RouteGap:
    """A registration site the decorator enumerator could not resolve.

    Gaps are reported, never guessed: the #220 plan's stop-and-report gate.
    """

    file_path: str
    line: int
    handler_fqn: str
    registration: str
    raw_path: str | None
    reason: str


@dataclass(frozen=True)
class RouteInventory:
    routes: tuple[RouteRecord, ...] = ()
    gaps: tuple[RouteGap, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@contextmanager
def repo_at_sha(repo_path: Path, sha: str) -> Iterator[Path]:
    """Materialize tracked files at *sha* in a temp tree; never a checkout.

    The BAC-BENCH clones are `--no-checkout` full-history mirrors (#221), so
    reading a pinned commit means `git archive`, not switching the working tree.
    """
    resolved = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0:
        raise ValueError(f"Unknown commit SHA {sha!r} in {repo_path}")
    commit = resolved.stdout.strip()
    archive = subprocess.run(
        ["git", "-C", str(repo_path), "archive", "--format=tar", commit],
        capture_output=True,
    )
    if archive.returncode != 0:
        detail = archive.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(detail or f"git archive failed for commit SHA {sha!r}")
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(tmp, filter="data")
        yield Path(tmp)


# --- Django URLconf and DRF router enumeration ------------------------------

_PATH_CALLS = {"path", "re_path", "url", "service_url"}
_INCLUDE_CALLS = {"include"}
_GROUPING_CALLS = {"i18n_patterns"}
# Helpers that decorate a url list and return the same routes (Wagtail uses
# `decorate_urlpatterns` to attach cache settings to every view).
_PATTERN_WRAPPERS = {"decorate_urlpatterns"}
_STANDARD_ACTIONS = {
    "list": ("GET", ""),
    "create": ("POST", ""),
    "retrieve": ("GET", "{pk}/"),
    "update": ("PUT", "{pk}/"),
    "partial_update": ("PATCH", "{pk}/"),
    "destroy": ("DELETE", "{pk}/"),
}
_VIEWSET_BASE_ACTIONS = {
    "ModelViewSet": tuple(_STANDARD_ACTIONS),
    "ReadOnlyModelViewSet": ("list", "retrieve"),
    "ListModelMixin": ("list",),
    "CreateModelMixin": ("create",),
    "RetrieveModelMixin": ("retrieve",),
    "UpdateModelMixin": ("update", "partial_update"),
    "DestroyModelMixin": ("destroy",),
}


@dataclass
class _Registration:
    prefix: object  # ast expression
    viewset: object  # ast expression
    line: int


@dataclass
class _ClassInfo:
    fqn: str
    bases: tuple[str, ...]
    base_names: tuple[str, ...]
    methods: tuple[str, ...]
    actions: dict[str, object]  # action method name -> decorator node


@dataclass
class _Router:
    module: str
    name: str
    registrations: list[_Registration]


@dataclass
class _Module:
    fqn: str
    rel_path: str
    is_package: bool
    tree: object
    imports: dict[str, str]
    assignments: dict[str, object]
    routers: dict[str, _Router]
    classes: dict[str, _ClassInfo]


class _UrlconfModel:
    """Static model of every in-repo urlconf module and router registration."""

    def __init__(self, modules: dict[str, _Module], classes: dict[str, _ClassInfo]):
        self.modules = modules
        self.classes = classes

    @classmethod
    def build(cls, repo_path: Path) -> _UrlconfModel:
        modules: dict[str, _Module] = {}
        classes: dict[str, _ClassInfo] = {}
        for py_file in python_files(repo_path):
            rel_path = str(py_file.relative_to(repo_path))
            try:
                tree = ast.parse(py_file.read_bytes())
            except (SyntaxError, ValueError):
                continue  # stay on the same file set as parse_repo
            fqn = str(FQN.from_path(rel_path))
            module = _Module(
                fqn=fqn,
                rel_path=rel_path,
                is_package=py_file.name == "__init__.py",
                tree=tree,
                imports=_collect_imports(tree, fqn, py_file.name == "__init__.py"),
                assignments={},
                routers={},
                classes={},
            )
            _collect_module_statements(module)
            modules[fqn] = module
            classes.update(module.classes)
        return cls(modules, classes)

    def module_for(self, dotted: str | None) -> _Module | None:
        """Find a repo module by import-rooted name.

        Real repos put source roots below the clone root (`src/pretix`,
        `apps/api/plane`), so an import names `plane.api.views` while the ADG
        module is `apps.api.plane.api.views`. Exact match wins; otherwise the
        shortest module whose FQN ends with the import name at a dot boundary.
        """
        if not dotted:
            return None
        exact = self.modules.get(dotted)
        if exact is not None:
            return exact
        suffix = "." + dotted
        matches = [
            module for fqn, module in self.modules.items() if fqn.endswith(suffix)
        ]
        return min(matches, key=lambda module: (len(module.fqn), module.fqn)) if matches else None

    def fqn_for(self, dotted: str | None, seen: frozenset[str] = frozenset()) -> str | None:
        """Map an import-rooted dotted name onto the repo-rooted ADG FQN.

        Follows package re-exports (`from .asset import Endpoint` in an
        `__init__`) so a handler names the module that defines it, not the
        package that re-exports it.
        """
        if not dotted:
            return None
        parts = dotted.split(".")
        for end in range(len(parts), 0, -1):
            module = self.module_for(".".join(parts[:end]))
            if module is not None:
                tail = parts[end:]
                if len(tail) == 1 and tail[0] in module.imports and dotted not in seen:
                    imported = module.imports[tail[0]]
                    if imported != dotted:
                        return self.fqn_for(imported, seen | {dotted})
                return ".".join([module.fqn, *tail])
        return dotted

    def roots(self) -> list[_Module]:
        """Urlconf modules nothing else includes, test files already excluded."""
        included = {
            target
            for module in self.modules.values()
            for target in _included_modules(module, self)
        }
        return [
            module for fqn, module in sorted(self.modules.items())
            if fqn not in included and "urlpatterns" in module.assignments
        ]


def _resolve_from(module_fqn: str, is_package: bool, level: int,
                  module: str | None) -> str | None:
    if level == 0:
        return module
    parts = list(FQN.from_dotted(module_fqn).parts)
    base = parts if is_package else parts[:-1]
    drop = level - 1
    if drop >= len(base) and module is None:
        return None
    base = base[:len(base) - drop]
    if module:
        base.extend(module.split("."))
    return ".".join(base) or None


def _collect_imports(tree, module_fqn: str, is_package: bool) -> dict[str, str]:
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    imports[alias.asname] = alias.name
                else:
                    imports[alias.name.split(".")[0]] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(module_fqn, is_package, node.level, node.module)
            if base is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                imports[alias.asname or alias.name] = f"{base}.{alias.name}"
    return imports


def _module_level(body, conditional: bool = False):
    """Yield module-level statements, descending through control flow.

    Descendants of a branch are marked conditional: two branches assigning the
    same name are alternatives, and both must be enumerated rather than the
    last one silently winning.
    """
    for stmt in body:
        yield stmt, conditional
        if isinstance(stmt, (ast.If, ast.For, ast.While)):
            yield from _module_level(stmt.body, True)
            yield from _module_level(stmt.orelse, True)
        elif isinstance(stmt, ast.With):
            yield from _module_level(stmt.body, True)
        elif isinstance(stmt, ast.Try):
            yield from _module_level(stmt.body, True)
            for handler in stmt.handlers:
                yield from _module_level(handler.body, True)
            yield from _module_level(stmt.orelse, True)
            yield from _module_level(stmt.finalbody, True)


def _latest(values: list) -> object | None:
    return values[-1] if values else None


def _bind(module: _Module, name: str, value, conditional: bool) -> None:
    """Record an assignment, keeping branch alternatives and prior bindings."""
    values = module.assignments.get(name)
    if conditional and values:
        values.append(value)
    else:
        module.assignments[name] = [value]


def _self_referential(value, name: str, module: _Module):
    """Replace a self-reference on either side of an assignment.

    Covers `urlpatterns = urlpatterns + X`, `urlpatterns = X + urlpatterns`
    and wrappers such as `urlpatterns = decorate_urlpatterns(urlpatterns, f)`.
    """
    previous = _latest(module.assignments.get(name, []))
    if previous is None:
        return value
    if isinstance(value, ast.BinOp):
        if isinstance(value.left, ast.Name) and value.left.id == name:
            return ast.BinOp(left=previous, op=value.op, right=value.right)
        if isinstance(value.right, ast.Name) and value.right.id == name:
            return ast.BinOp(left=value.left, op=value.op, right=previous)
    if (isinstance(value, ast.Call) and value.args
            and isinstance(value.args[0], ast.Name) and value.args[0].id == name):
        return ast.Call(
            func=value.func, args=[previous, *value.args[1:]],
            keywords=value.keywords,
        )
    return value


def _collect_module_statements(module: _Module) -> None:
    for stmt, conditional in _module_level(module.tree.body):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    _bind(
                        module, target.id,
                        _self_referential(stmt.value, target.id, module),
                        conditional,
                    )
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            previous = _latest(module.assignments.get(stmt.target.id, []))
            value = stmt.value
            if previous is not None:
                value = ast.BinOp(left=previous, op=ast.Add(), right=value)
            _bind(module, stmt.target.id, value, conditional)
        elif (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
              and _append_target(stmt.value) is not None):
            name, appended = _append_target(stmt.value)
            previous = _latest(module.assignments.get(name, []))
            if previous is not None:
                _bind(
                    module, name,
                    ast.BinOp(left=previous, op=ast.Add(), right=appended),
                    conditional,
                )
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            _collect_registration(stmt.value, module)
        elif isinstance(stmt, ast.ClassDef):
            _collect_class(stmt, module, module.fqn)


def _append_target(call):
    """`urlpatterns.append(X)` -> ("urlpatterns", X); `.extend` likewise."""
    function = call.func
    if not (isinstance(function, ast.Attribute)
            and function.attr in {"append", "extend"}
            and isinstance(function.value, ast.Name)):
        return None
    if not call.args:
        return None
    argument = call.args[0]
    if function.attr == "extend":
        argument = ast.List(elts=[argument], ctx=ast.Load())
    return function.value.id, argument


def _collect_registration(call, module: _Module) -> None:
    function = call.func
    if not (isinstance(function, ast.Attribute) and function.attr == "register"):
        return
    if not isinstance(function.value, ast.Name):
        return
    name = function.value.id
    router = module.routers.setdefault(name, _Router(module.fqn, name, []))
    if len(call.args) >= 2:
        router.registrations.append(_Registration(
            prefix=call.args[0], viewset=call.args[1], line=call.lineno,
        ))


def _collect_class(node: ast.ClassDef, module: _Module, scope: str) -> None:
    fqn = f"{scope}.{node.name}"
    bases = tuple(
        resolved for base in node.bases
        if (resolved := _resolve_expr(base, module)) is not None
    )
    base_names = tuple(_tail(base) for base in node.bases)
    methods: list[str] = []
    actions: dict[str, object] = {}
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(child.name)
            decorator = _action_decorator(child.decorator_list)
            if decorator is not None:
                actions[child.name] = decorator
        elif isinstance(child, ast.ClassDef):
            _collect_class(child, module, fqn)
    module.classes[fqn] = _ClassInfo(
        fqn=fqn, bases=bases, base_names=base_names,
        methods=tuple(methods), actions=actions,
    )


def _action_decorator(decorators: list) -> object | None:
    for decorator in decorators:
        call = decorator if isinstance(decorator, ast.Call) else None
        target = call.func if call is not None else decorator
        if _tail(target) == "action":
            return call or decorator
    return None


def _tail(expr) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    if isinstance(expr, ast.Call):
        return _tail(expr.func)
    return ""


def _resolve_expr(expr, module: _Module) -> str | None:
    """Resolve a Name/Attribute chain to a dotted FQN using the module imports."""
    if isinstance(expr, ast.Name):
        return module.imports.get(expr.id) or f"{module.fqn}.{expr.id}"
    if isinstance(expr, ast.Attribute):
        base = _resolve_expr(expr.value, module)
        return f"{base}.{expr.attr}" if base else None
    if isinstance(expr, ast.Call):
        return _resolve_expr(expr.func, module)  # `ViewSet().as_view()`
    return None


def _literal_ast(expr) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def _expand_patterns(expr, module: _Module, model: _UrlconfModel,
                     seen: frozenset[int]) -> list[tuple[object, _Module]] | None:
    """Flatten a urlpatterns expression to (entry call, defining module) pairs.

    The defining module travels with the entry: a shared list imported from
    another urlconf keeps that module's imports for handler resolution.
    """
    if expr is None or id(expr) in seen:
        return None
    seen = seen | {id(expr)}
    if isinstance(expr, (ast.List, ast.Tuple)):
        entries: list = []
        for element in expr.elts:
            value = element.value if isinstance(element, ast.Starred) else element
            expanded = _expand_patterns(value, module, model, seen)
            if expanded is None:
                return None
            entries.extend(expanded)
        return entries
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        left = _expand_patterns(expr.left, module, model, seen)
        right = _expand_patterns(expr.right, module, model, seen)
        return None if left is None or right is None else left + right
    if isinstance(expr, ast.Name):
        stored = module.assignments.get(expr.id)
        if stored is not None:
            entries: list = []
            for value in stored:
                expanded = _expand_patterns(value, module, model, seen)
                if expanded is None:
                    return None
                entries.extend(expanded)
            return entries
        binding = _imported_binding(expr.id, module, model)
        if binding is not None:
            other, attribute = binding
            return _expand_patterns(
                _binding_expr(other, attribute), other, model, seen,
            )
        return None
    if isinstance(expr, ast.Call):
        if _tail(expr.func) in _GROUPING_CALLS:
            entries = []
            for argument in expr.args:
                expanded = _expand_patterns(argument, module, model, seen)
                if expanded is None:
                    return None
                entries.extend(expanded)
            return entries
        if _tail(expr.func) in _PATTERN_WRAPPERS and expr.args:
            return _expand_patterns(expr.args[0], module, model, seen)
        return [(expr, module)]  # a path/re_path/url registration entry
    if isinstance(expr, ast.Attribute) and expr.attr == "urlpatterns":
        other = model.module_for(_resolve_expr(expr.value, module))
        if other is not None:
            return _expand_patterns(
                _binding_expr(other, "urlpatterns"), other, model, seen,
            )
        return None
    return None


def _binding_expr(module: _Module, name: str):
    """One AST expression for a name's current binding(s)."""
    values = module.assignments.get(name)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return ast.copy_location(
        ast.Tuple(elts=list(values), ctx=ast.Load()), values[0],
    )


def _imported_binding(name: str, module: _Module,
                      model: _UrlconfModel) -> tuple[_Module, str] | None:
    """Resolve an imported module-level list: `from .shared import patterns`."""
    imported = module.imports.get(name)
    if not imported:
        return None
    parent, _, attribute = imported.rpartition(".")
    other = model.module_for(parent)
    if other is None or attribute not in other.assignments:
        return None
    return other, attribute


def _imported_urlpatterns(name: str, module: _Module,
                          model: _UrlconfModel) -> _Module | None:
    """`from .asset import urlpatterns as asset_patterns` -> asset module."""
    binding = _imported_binding(name, module, model)
    if binding is None or binding[1] != "urlpatterns":
        return None
    return binding[0]


def _resolve_include(arg, module: _Module, model: _UrlconfModel):
    """Classify include()'s argument: module, router, or inline patterns."""
    if arg is None:
        return None
    if isinstance(arg, ast.Tuple) and arg.elts:
        arg = arg.elts[0]
    if isinstance(arg, (ast.List, ast.BinOp, ast.Tuple)):
        return ("patterns", arg, module)
    if isinstance(arg, ast.Constant):
        value = _literal_ast(arg)
        other = model.module_for(value)
        return ("module", other.fqn) if other is not None else None
    if isinstance(arg, ast.Name):
        binding = _imported_binding(arg.id, module, model)
        if binding is not None:
            other, attribute = binding
            if attribute == "urlpatterns":
                return ("module", other.fqn)
            return ("patterns", _binding_expr(other, attribute), other)
        imported = module.imports.get(arg.id)
        other = model.module_for(imported)
        if other is not None:
            return ("module", other.fqn)
        if arg.id in module.routers:
            return ("router", module.fqn, arg.id)
        if arg.id in module.assignments:
            return ("patterns", _binding_expr(module, arg.id), module)
        return None
    if isinstance(arg, ast.Attribute):
        if arg.attr == "urls" and isinstance(arg.value, ast.Name):
            name = arg.value.id
            if name in module.routers:
                return ("router", module.fqn, name)
            imported = module.imports.get(name)
            other = model.module_for(imported)
            if other is not None and name in other.routers:
                return ("router", other.fqn, name)
        target = _resolve_expr(arg, module)
        other = model.module_for(target)
        if other is not None:
            return ("module", other.fqn)
        parent, _, name = (target or "").rpartition(".")
        other = model.module_for(parent)
        if other is not None and name in other.routers:
            return ("router", other.fqn, name)
    return None


def _is_include(call) -> bool:
    return isinstance(call, ast.Call) and _tail(call.func) in _INCLUDE_CALLS


def _included_modules(module: _Module, model: _UrlconfModel) -> set[str]:
    found: set[str] = set()
    for stmt, _ in _module_level(module.tree.body):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if _is_include(node):
                target = _resolve_include(node.args[0] if node.args else None, module, model)
                if target is not None and target[0] == "module":
                    found.add(target[1])
            elif isinstance(node, ast.Name):
                # `urlpatterns = [*asset_patterns]` also mounts a module; it
                # must not be treated as an independent root.
                other = _imported_urlpatterns(node.id, module, model)
                if other is not None:
                    found.add(other.fqn)
    return found


def _strip_anchors(path: str) -> str:
    return path.lstrip("^").removesuffix("$")


def _compose(*segments: str) -> str:
    """Join url fragments the way Django's include() nests them."""
    out = ""
    for segment in segments:
        segment = _strip_anchors(segment)
        if not segment:
            continue
        segment = segment.lstrip("/")
        if out and not out.endswith("/"):
            out += "/"
        out += segment
    return out


def _pattern_gap(module: _Module, line: int, reason: str,
                 registration: str = "urlpatterns") -> RouteGap:
    return RouteGap(
        file_path=module.rel_path,
        line=line,
        handler_fqn=module.fqn,
        registration=registration,
        raw_path=None,
        reason=reason,
    )


def _enumerate_urlconf_routes(
    repo_path: Path, known_fqns: frozenset[str],
) -> tuple[list[RouteRecord], list[RouteGap]]:
    model = _UrlconfModel.build(repo_path)
    routes: list[RouteRecord] = []
    gaps: list[RouteGap] = []
    for root in model.roots():
        _walk_urlpatterns(
            _binding_expr(root, "urlpatterns"), root, model, "", known_fqns,
            routes, gaps, frozenset({root.fqn}),
        )
    return routes, gaps


def _walk_urlpatterns(expr, module: _Module, model: _UrlconfModel, prefix: str,
                      known_fqns: frozenset[str], routes: list[RouteRecord],
                      gaps: list[RouteGap], visited: frozenset[str]) -> None:
    entries = _expand_patterns(expr, module, model, frozenset())
    if entries is None:
        gaps.append(_pattern_gap(module, getattr(expr, "lineno", 1),
                                 "unresolved_urlpatterns"))
        return
    for entry, owner in entries:
        _walk_pattern_entry(
            entry, owner, model, prefix, known_fqns, routes, gaps, visited,
        )


def _walk_pattern_entry(entry, module: _Module, model: _UrlconfModel,
                        prefix: str, known_fqns: frozenset[str],
                        routes: list[RouteRecord], gaps: list[RouteGap],
                        visited: frozenset[str]) -> None:
    if not isinstance(entry, ast.Call):
        gaps.append(_pattern_gap(module, getattr(entry, "lineno", 1),
                                 "unresolved_url_pattern"))
        return
    name = _tail(entry.func)
    if name in _INCLUDE_CALLS:
        _walk_include(entry, module, model, prefix, known_fqns,
                      routes, gaps, visited)
        return
    if name not in _PATH_CALLS:
        gaps.append(_pattern_gap(module, entry.lineno, "unresolved_url_pattern"))
        return
    if not entry.args:
        gaps.append(_pattern_gap(module, entry.lineno, "non_literal_path"))
        return

    view = entry.args[1] if len(entry.args) > 1 else None
    raw = _literal_ast(entry.args[0])
    if raw is None:
        gaps.append(_pattern_gap(module, entry.lineno, "non_literal_path"))
        # The mount prefix is unknown, but the mounted urlconf is still part
        # of the surface; enumerate it at the parent prefix rather than drop it.
        if view is not None and _is_include(view):
            _walk_include(view, module, model, prefix, known_fqns,
                          routes, gaps, visited)
        return

    if view is not None and _is_include(view):
        _walk_include(view, module, model, _compose(prefix, raw),
                      known_fqns, routes, gaps, visited)
        return
    if view is None:
        gaps.append(_pattern_gap(module, entry.lineno, "unresolved_url_pattern"))
        return

    handler_fqn = model.fqn_for(_view_fqn(view, module))
    if handler_fqn is None:
        gaps.append(_pattern_gap(module, entry.lineno, "unresolved_view"))
        return
    _emit_route(
        module=module,
        raw_path=_compose(prefix, raw),
        methods=_view_methods(view, module, model),
        handler_fqn=handler_fqn,
        registration_kind="urlconf",
        line=entry.lineno,
        known_fqns=known_fqns,
        routes=routes,
        gaps=gaps,
    )


def _walk_include(include_call, module: _Module, model: _UrlconfModel,
                  prefix: str, known_fqns: frozenset[str],
                  routes: list[RouteRecord], gaps: list[RouteGap],
                  visited: frozenset[str]) -> None:
    target = _resolve_include(
        include_call.args[0] if include_call.args else None, module, model,
    )
    if target is None:
        gaps.append(_pattern_gap(module, include_call.lineno, "unresolved_include"))
        return
    kind = target[0]
    if kind == "module":
        other = model.modules.get(target[1])
        if other is None:
            gaps.append(_pattern_gap(module, include_call.lineno, "unresolved_include"))
            return
        if other.fqn in visited:
            return
        _walk_urlpatterns(
            _binding_expr(other, "urlpatterns"), other, model, prefix,
            known_fqns, routes, gaps, visited | {other.fqn},
        )
    elif kind == "router":
        _emit_router(target[1], target[2], prefix, model, known_fqns, routes, gaps)
    else:
        _walk_urlpatterns(
            target[1], target[2], model, prefix, known_fqns, routes, gaps, visited,
        )


def _view_fqn(view, module: _Module) -> str | None:
    if isinstance(view, ast.Call):
        if _tail(view.func) == "as_view":
            return _resolve_expr(view.func.value, module)
        return _resolve_expr(view.func, module)
    return _resolve_expr(view, module)


def _view_methods(view, module: _Module, model: _UrlconfModel) -> tuple[str, ...]:
    if not (isinstance(view, ast.Call) and _tail(view.func) == "as_view"):
        return ()  # a function view accepts any method; unknown statically
    for argument in view.args:
        if isinstance(argument, ast.Dict):
            methods = {
                key.value.upper() for key in argument.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            return tuple(sorted(methods))
    keywords = {kw.arg: kw.value for kw in view.keywords if kw.arg}
    if "http_method_names" in keywords:
        return _literal_methods(keywords["http_method_names"]) or ()
    return _class_methods(
        model.fqn_for(_resolve_expr(view.func.value, module)), model,
    ) or ()


def _class_methods(fqn: str | None, model: _UrlconfModel,
                   seen: frozenset[str] = frozenset()) -> tuple[str, ...] | None:
    fqn = model.fqn_for(fqn)
    if fqn is None or fqn in seen:
        return None
    info = model.classes.get(fqn)
    if info is None:
        return None
    declared = tuple(sorted(
        method.upper() for method in info.methods if method in _HTTP_VERBS
    ))
    if declared:
        return declared
    for base in info.bases:
        inherited = _class_methods(base, model, seen | {fqn})
        if inherited:
            return inherited
    for base_name in info.base_names:
        known = _DJANGO_GENERIC_METHODS.get(base_name)
        if known:
            return known
    return None


_DJANGO_GENERIC_METHODS = {
    "TemplateView": ("GET",),
    "ListView": ("GET",),
    "DetailView": ("GET",),
    "CreateView": ("POST",),
    "UpdateView": ("GET", "POST"),
    "DeleteView": ("GET", "POST"),
    "FormView": ("GET", "POST"),
}


def _literal_methods(expr) -> tuple[str, ...] | None:
    if not isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
        return None
    values = [_literal_ast(element) for element in expr.elts]
    if any(value is None for value in values):
        return None
    return tuple(sorted({value.upper() for value in values}))


def _emit_route(module: _Module, raw_path: str, methods: tuple[str, ...],
                handler_fqn: str, registration_kind: str, line: int,
                known_fqns: frozenset[str], routes: list[RouteRecord],
                gaps: list[RouteGap], validate_handler: bool = True) -> None:
    raw_path = "/" + raw_path.lstrip("/")
    if validate_handler and handler_fqn not in known_fqns:
        # A handler whose module the ADG knows is a real resolution failure; a
        # handler from an unparsed third-party module (django.contrib.admin) is
        # simply outside the graph and reported separately.
        reason = "handler_not_in_adg" if _has_known_prefix(handler_fqn, known_fqns) \
            else "external_handler"
        gaps.append(RouteGap(
            file_path=module.rel_path,
            line=line,
            handler_fqn=handler_fqn,
            registration=registration_kind,
            raw_path=raw_path,
            reason=reason,
        ))
        return
    routes.append(RouteRecord(
        methods=methods,
        raw_path=raw_path,
        canonical_path=canonical_path(raw_path),
        handler_fqn=handler_fqn,
        module=module.fqn,
        registration_kind=registration_kind,
        evidence=RouteEvidence(file_path=module.rel_path, line=line),
    ))


def _has_known_prefix(fqn: str, known_fqns: frozenset[str]) -> bool:
    parts = fqn.split(".")
    return any(".".join(parts[:end]) in known_fqns for end in range(1, len(parts)))


def _emit_router(module_fqn: str, router_name: str, prefix: str,
                 model: _UrlconfModel, known_fqns: frozenset[str],
                 routes: list[RouteRecord], gaps: list[RouteGap]) -> None:
    module = model.modules.get(module_fqn)
    router = module.routers.get(router_name) if module is not None else None
    if module is None or router is None:
        return
    for registration in router.registrations:
        viewset = model.fqn_for(_resolve_expr(registration.viewset, module))
        route_prefix = _literal_ast(registration.prefix)
        if viewset is None or route_prefix is None:
            gaps.append(RouteGap(
                file_path=module.rel_path, line=registration.line,
                handler_fqn=viewset or module.fqn, registration="register",
                raw_path=None,
                reason="non_literal_viewset" if viewset is None else "non_literal_path",
            ))
            continue
        if viewset not in known_fqns:
            gaps.append(RouteGap(
                file_path=module.rel_path, line=registration.line,
                handler_fqn=viewset, registration="register",
                raw_path="/" + _compose(prefix, route_prefix).lstrip("/"),
                reason="viewset_not_in_adg",
            ))
            continue
        info = model.classes.get(viewset)
        base = _compose(prefix, route_prefix)
        for action, methods in _viewset_actions(info, model).items():
            suffix = _STANDARD_ACTIONS[action][1]
            raw_path = _compose(base, suffix) if suffix else _compose(base) + "/"
            _emit_route(
                module=module, raw_path=raw_path,
                methods=methods, handler_fqn=f"{viewset}.{action}",
                registration_kind="router", line=registration.line,
                known_fqns=known_fqns, routes=routes, gaps=gaps,
                validate_handler=False,
            )
        for action, decorator in _decorated_actions(info, model).items():
            parsed = _action_route(decorator, action)
            if parsed is None:
                gaps.append(RouteGap(
                    file_path=module.rel_path, line=registration.line,
                    handler_fqn=f"{viewset}.{action}", registration="action",
                    raw_path=None, reason="non_literal_action",
                ))
                continue
            detail, url_path, methods = parsed
            tail = f"{{pk}}/{url_path}" if detail else url_path
            _emit_route(
                module=module, raw_path=_compose(base, tail) + "/",
                methods=methods, handler_fqn=f"{viewset}.{action}",
                registration_kind="router", line=registration.line,
                known_fqns=known_fqns, routes=routes, gaps=gaps,
                validate_handler=False,
            )


def _viewset_actions(info: _ClassInfo | None, model: _UrlconfModel,
                     seen: frozenset[str] = frozenset()) -> dict[str, tuple[str, ...]]:
    if info is None or info.fqn in seen:
        return {}
    actions: dict[str, set[str]] = {}
    for method in info.methods:
        if method in _STANDARD_ACTIONS:
            actions.setdefault(method, set()).add(_STANDARD_ACTIONS[method][0])
    for base_fqn in info.bases:
        for action, methods in _viewset_actions(
            model.classes.get(model.fqn_for(base_fqn)), model, seen | {info.fqn},
        ).items():
            actions.setdefault(action, set()).update(methods)
    for base_name in info.base_names:
        for action in _VIEWSET_BASE_ACTIONS.get(base_name, ()):
            actions.setdefault(action, set()).add(_STANDARD_ACTIONS[action][0])
    return {action: tuple(sorted(methods)) for action, methods in actions.items()}


def _decorated_actions(info: _ClassInfo | None, model: _UrlconfModel,
                       seen: frozenset[str] = frozenset()) -> dict[str, object]:
    if info is None or info.fqn in seen:
        return {}
    actions = dict(info.actions)
    for base_fqn in info.bases:
        actions.update(_decorated_actions(
            model.classes.get(model.fqn_for(base_fqn)), model, seen | {info.fqn},
        ))
    return actions


def _action_route(decorator, name: str):
    call = decorator if isinstance(decorator, ast.Call) else None
    keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg} if call else {}
    detail_expr = keywords.get("detail")
    detail = detail_expr.value if isinstance(detail_expr, ast.Constant) else False
    if not isinstance(detail, bool):
        return None
    methods = ("GET",)
    if "methods" in keywords:
        methods = _literal_methods(keywords["methods"])
        if methods is None:
            return None
    url_path = _literal_ast(keywords["url_path"]) if "url_path" in keywords else name
    if url_path is None:
        return None
    return detail, url_path.strip("/"), methods


def build_route_inventory(repo_path: Path, adg: ADG | None = None) -> RouteInventory:
    """Enumerate decorator- and URLconf-registered routes at *repo_path*.

    Deterministic: files are walked in sorted order and both output lists are
    sorted, so a rerun over the same bytes is identical. Handler FQNs are built
    with the same FQN machinery as the ADG and checked against its node set.
    """
    adg = adg if adg is not None else parse_repo(repo_path)
    known_fqns = adg.fqn_set
    parser = Parser(PY_LANGUAGE)
    routes: list[RouteRecord] = []
    gaps: list[RouteGap] = []

    for py_file in python_files(repo_path):
        rel_path = str(py_file.relative_to(repo_path))
        source = py_file.read_bytes()
        tree = parser.parse(source)
        if tree.root_node.has_error:
            # parse_repo skips unparseable files; stay on the same file set.
            continue
        module_fqn = FQN.from_path(rel_path)
        _walk(tree.root_node, module_fqn, rel_path, known_fqns, routes, gaps)

    urlconf_routes, urlconf_gaps = _enumerate_urlconf_routes(repo_path, known_fqns)
    routes.extend(urlconf_routes)
    gaps.extend(urlconf_gaps)

    # The same module can be reachable from several roots (or included twice);
    # an identical record carries no extra information.
    routes = list(dict.fromkeys(routes))
    gaps = list(dict.fromkeys(gaps))

    routes.sort(key=lambda r: (
        r.evidence.file_path, r.evidence.line, r.handler_fqn, r.raw_path, r.methods,
    ))
    gaps.sort(key=lambda g: (
        g.file_path, g.line, g.handler_fqn, g.registration, g.reason,
        g.raw_path or "",
    ))
    return RouteInventory(routes=tuple(routes), gaps=tuple(gaps))


def _walk(node, scope_fqn: FQN, rel_path: str,
          known_fqns: frozenset[str], routes: list[RouteRecord],
          gaps: list[RouteGap]) -> None:
    if node.type in _DEFINITION_TYPES:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        child_fqn = scope_fqn.child(name_node.text.decode("utf-8"))
        for child in node.children:
            _walk(child, child_fqn, rel_path, known_fqns, routes, gaps)
        return

    if node.type == "decorated_definition":
        definition = next(
            (child for child in node.children if child.type in _DEFINITION_TYPES),
            None,
        )
        if definition is None:
            return
        name_node = definition.child_by_field_name("name")
        if name_node is None:
            return
        handler_fqn = scope_fqn.child(name_node.text.decode("utf-8"))
        if definition.type == "function_definition":
            _emit_routes(
                node, handler_fqn, rel_path, known_fqns, routes, gaps
            )
        for child in definition.children:
            _walk(child, handler_fqn, rel_path, known_fqns, routes, gaps)
        return

    _emit_call_form_gap(node, scope_fqn, rel_path, gaps)

    for child in node.children:
        _walk(child, scope_fqn, rel_path, known_fqns, routes, gaps)


def _emit_routes(decorated, handler_fqn: FQN, rel_path: str,
                 known_fqns: frozenset[str], routes: list[RouteRecord],
                 gaps: list[RouteGap]) -> None:
    for child in decorated.children:
        if child.type != "decorator":
            continue
        expression = next((c for c in child.children if c.is_named), None)
        if expression is None or expression.type != "call":
            continue
        callee = expression.child_by_field_name("function")
        attribute = _callee_attribute(callee)
        if attribute not in _HTTP_VERBS and attribute not in _ROUTE_DECORATORS:
            continue

        line = child.start_point[0] + 1
        arguments = expression.child_by_field_name("arguments")
        path_node = _path_argument(arguments)
        raw_path = _literal_string(path_node)
        if raw_path is None:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                registration=attribute,
                raw_path=None,
                reason="non_literal_path",
            ))
            continue

        methods = _methods(attribute, arguments)
        if methods is None:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                registration=attribute,
                raw_path=raw_path,
                reason="non_literal_methods",
            ))
            continue

        if str(handler_fqn) not in known_fqns:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                registration=attribute,
                raw_path=raw_path,
                reason="handler_not_in_adg",
            ))
            continue

        routes.append(RouteRecord(
            methods=methods,
            raw_path=raw_path,
            canonical_path=canonical_path(raw_path),
            handler_fqn=str(handler_fqn),
            module=str(FQN.from_path(rel_path)),
            registration_kind="decorator",
            evidence=RouteEvidence(file_path=rel_path, line=line),
        ))


def _emit_call_form_gap(node, scope_fqn: FQN, rel_path: str,
                        gaps: list[RouteGap]) -> None:
    """Report a body-level registration such as `bp.add_url_rule(...)`.

    These are not decorators, so the enumerator cannot resolve their handler
    statically; the enclosing scope is the best anchor and the registry must
    still see the site instead of losing it.
    """
    if node.type != "call":
        return
    attribute = _callee_attribute(node.child_by_field_name("function"))
    if attribute not in _CALL_FORM_REGISTRATIONS:
        return
    arguments = node.child_by_field_name("arguments")
    gaps.append(RouteGap(
        file_path=rel_path,
        line=node.start_point[0] + 1,
        handler_fqn=str(scope_fqn),
        registration=attribute,
        raw_path=_literal_string(_path_argument(arguments)),
        reason="non_decorator_registration",
    ))


def _callee_attribute(callee) -> str:
    """The rightmost name of `app.get`, or "" for a bare decorator."""
    if callee is None or callee.type != "attribute":
        return ""
    attribute = callee.child_by_field_name("attribute")
    return attribute.text.decode("utf-8") if attribute is not None else ""


def _keyword_arguments(arguments) -> dict[str, object]:
    """Map keyword-argument names to their value nodes."""
    return {
        child.child_by_field_name("name").text.decode("utf-8"):
            child.child_by_field_name("value")
        for child in (arguments.children if arguments is not None else ())
        if child.type == "keyword_argument"
        and child.child_by_field_name("name") is not None
    }


def _path_argument(arguments):
    """The route path: first positional, else `path=` or `rule=`."""
    if arguments is not None:
        for child in arguments.children:
            if child.is_named and child.type not in ("keyword_argument", "comment"):
                return child
    keywords = _keyword_arguments(arguments)
    for name in _PATH_KEYWORDS:
        if name in keywords:
            return keywords[name]
    return None


def _literal_string(node) -> str | None:
    """Decode a string literal (including implicit concatenation), else None."""
    if node is None or node.type not in ("string", "concatenated_string"):
        return None
    try:
        value = ast.literal_eval(node.text.decode("utf-8"))
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


def _methods(attribute: str, arguments) -> tuple[str, ...] | None:
    """Methods declared by the decorator; None when they cannot be read."""
    if attribute in _HTTP_VERBS:
        return (attribute.upper(),)

    declared = _keyword_arguments(arguments).get("methods")
    if declared is None:
        return ("GET",)  # Starlette/Flask default when methods is omitted
    if declared.type not in ("list", "tuple", "set"):
        return None  # a name or call: declared methods are not statically known
    values = []
    for element in declared.children:
        if not element.is_named:
            continue
        value = _literal_string(element)
        if value is None:
            return None
        values.append(value.upper())
    return tuple(sorted(set(values)))
