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
from dataclasses import dataclass
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

_HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options"}
_ROUTE_DECORATORS = {"route", "api_route"}
_DEFINITION_TYPES = {"function_definition", "class_definition"}


def canonical_path(raw_path: str) -> str:
    """Strip converter types and parameter names; literal segments survive.

    `<int:user_id>` and `{user_id}` both become `{}`, so a Flask route and a
    FastAPI route with the same shape canonicalize identically.
    """
    return _FASTAPI_PARAM.sub(PARAM, _FLASK_PARAM.sub(PARAM, raw_path))


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
    decorator: str
    reason: str


@dataclass(frozen=True)
class RouteInventory:
    routes: tuple[RouteRecord, ...] = ()
    gaps: tuple[RouteGap, ...] = ()

    def to_dict(self) -> dict:
        return {
            "routes": [
                {
                    "methods": list(route.methods),
                    "raw_path": route.raw_path,
                    "canonical_path": route.canonical_path,
                    "handler_fqn": route.handler_fqn,
                    "module": route.module,
                    "registration_kind": route.registration_kind,
                    "evidence": {
                        "file_path": route.evidence.file_path,
                        "line": route.evidence.line,
                    },
                }
                for route in self.routes
            ],
            "gaps": [
                {
                    "file_path": gap.file_path,
                    "line": gap.line,
                    "handler_fqn": gap.handler_fqn,
                    "decorator": gap.decorator,
                    "reason": gap.reason,
                }
                for gap in self.gaps
            ],
        }


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


def build_route_inventory(repo_path: Path, adg: ADG | None = None) -> RouteInventory:
    """Enumerate decorator-registered routes at *repo_path*.

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

    routes.sort(key=lambda r: (
        r.evidence.file_path, r.evidence.line, r.handler_fqn, r.raw_path, r.methods,
    ))
    gaps.sort(key=lambda g: (
        g.file_path, g.line, g.handler_fqn, g.decorator, g.reason,
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
        path_node = _first_positional(arguments)
        raw_path = _literal_string(path_node)
        if raw_path is None:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                decorator=attribute,
                reason="non_literal_path",
            ))
            continue

        methods = _methods(attribute, arguments)
        if methods is None:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                decorator=attribute,
                reason="non_literal_methods",
            ))
            continue

        if str(handler_fqn) not in known_fqns:
            gaps.append(RouteGap(
                file_path=rel_path,
                line=line,
                handler_fqn=str(handler_fqn),
                decorator=attribute,
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


def _callee_attribute(callee) -> str:
    """The rightmost name of `app.get`, or "" for a bare decorator."""
    if callee is None or callee.type != "attribute":
        return ""
    attribute = callee.child_by_field_name("attribute")
    return attribute.text.decode("utf-8") if attribute is not None else ""


def _first_positional(arguments):
    """First positional argument node, or None."""
    if arguments is None:
        return None
    for child in arguments.children:
        if child.is_named and child.type not in ("keyword_argument", "comment"):
            return child
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

    kwargs = {
        child.child_by_field_name("name").text.decode("utf-8"): child.child_by_field_name("value")
        for child in (arguments.children if arguments is not None else ())
        if child.type == "keyword_argument"
        and child.child_by_field_name("name") is not None
    }
    declared = kwargs.get("methods")
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
