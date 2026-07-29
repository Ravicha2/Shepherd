"""Unified ADR-to-ConstraintEdge resolver.

One LLM session per ADR. Reads full ADR text (including Decision Outcome),
uses list_modules and dive tools to map prose concepts to FQN patterns,
and produces ConstraintEdge objects directly. No SymbolicConstraint intermediate.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field

from openai import OpenAI

from services.adg.adg_tools import dive, list_modules
from services.extract.config import LangExtractConfig
from services.models import ADG, ConstraintEdge, FQNKind, PredicateType

log = logging.getLogger(__name__)

TOOL_CALL_CAP = 20

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_modules",
            "description": "List all module FQNs in the codebase graph. Use this first to find relevant modules, then dive into promising ones.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dive",
            "description": (
                "Explore the neighborhood around an FQN. Returns all nodes and edges "
                "within `depth` hops via CONTAINS, IMPORTS, and INHERITS edges "
                "(bidirectional). Use depth=1 for direct neighbors, depth=2-3 for "
                "broader context. Start with modules from list_modules, then dive "
                "into the ones that match the constraint's prose description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fqn": {"type": "string", "description": "Fully qualified name to explore around"},
                    "depth": {"type": "integer", "description": "Number of hops to explore (default 3)", "default": 3},
                },
                "required": ["fqn"],
            },
        },
    },
]

_TOOL_FUNCTIONS = {
    "list_modules": lambda args, adg: json.dumps(list_modules(adg)),
    "dive": lambda args, adg: json.dumps(dive(args["fqn"], adg, depth=args.get("depth", 3))),
}


@dataclass
class ResolutionTrace:
    tool_calls: list[dict] = field(default_factory=list)
    hit_cap: bool = False
    parse_failed: bool = False
    pre_validation_edges: list[dict] = field(default_factory=list)


_SYSTEM_PROMPT_TEMPLATE = """
You are an architectural decision resolver. Given a full ADR document, identify 
architectural constraints and map them to FQN patterns in the codebase graph.

CRITICAL: Distinguish prescriptive decisions from prohibitions.
- A PRESCRIPTIVE decision says "we chose option X" or "we will build Y". These are 
  the ADR's chosen solution. They produce REQUIRES_IMPLEMENTATION or REQUIRES_DEPENDENCY 
  constraints, NOT prohibitions.
- A PROHIBITION says "we must not use X" or "X is forbidden". These produce
  PROHIBITS_DEPENDENCY or PROHIBITS_IMPLEMENTATION constraints.

Do NOT extract a prohibition from a prescriptive decision. If the ADR says "we chose
to build a minimal repository abstraction", that means the repository abstraction IS the
decision outcome, not something to be prohibited.

## Required exploration

Before producing any output, you MUST call list_modules at least once, and dive into any \
module referenced by the ADR before writing a constraint about it. list_modules only shows \
top-level modules — submodules and classes are only visible once you dive into a module, and \
sometimes only after diving more than one level deep. Do not guess FQNs from the ADR's prose \
alone or from what a typical project of this kind usually looks like. Output produced without \
a preceding list_modules call will be rejected.

## ADR Document

{adr_text}

## Module list

The following modules exist in the codebase graph. Internal FQN patterns MUST come from this list. Do NOT invent internal module names.

{module_hint}

## Subject and object rules

- subject: MUST be an internal FQN pattern from the module list (internal codebase module).
  If you cannot map the ADR's subject concept to a module, return an empty array.
- object: depends on predicate:
  - `requires_dependency` / `requires_implementation`: object is either (a) an
    internal FQN pattern from the module list, or (b) an external package name. Prefer
    names from the External packages list when the ADR names one directly. For
    transitive dependencies reached through a wrapper package (e.g. PostgreSQL reached
    via `django.db`), use the access-path package (`django.db`), not the underlying
    engine. Do NOT invent internal FQNs for external packages.
  - `prohibits_dependency` / `prohibits_implementation`: object MAY be an internal FQN
    pattern, OR any external package name, including packages NOT imported by the
    codebase (e.g., `rest_framework`, `mysql`). The linter checks for absence, so
    naming an absent package is a valid prohibition.

Example: ADR requires Elasticsearch for fulltext search.
  subject: openlobby.core.*  (internal, from module list)
  object:  elasticsearch     (external package, from External packages list)
  predicate: requires_dependency

Example: ADR prohibits REST framework use (REST is not imported in the codebase).
  subject: openlobby.core.api.*  (internal, from module list)
  object:  rest_framework        (external package, absent from imports)
  predicate: prohibits_dependency

## External packages

External packages imported by the codebase. Use these as the `requires_*` object when the ADR names one of them directly. For transitive dependencies reached through a wrapper (e.g., `postgresql` via `django.db`), use the access-path package (`django.db`). `prohibits_*` object may be any external name.

{external_packages_hint}

## Predicate types

- prohibits_dependency: subject must not depend on (import) object
- requires_dependency: subject must depend on (import) object
- prohibits_implementation: subject must not implement (inherit from, subclass) object
- requires_implementation: subject must implement (inherit from, subclass) object

## Wildcard

The `.*` suffix denotes a wildcard pattern: it matches the prefix itself **and** every descendant FQN that starts with `prefix.`.
For example, `app.routes.*` matches `app.routes`, `app.routes.user`, and `app.routes.user.get_handler`.

When generating constraints, use wildcards for architectural rules that apply to an entire module or layer (for example, "no route handler may import any model class" becomes `app.routes.*` → `app.models.*`). Use exact FQNs when the rule targets one specific entity (for example, "all services must inherit from `app.services.base.ServiceBase`"). External package objects never take a `.*` wildcard.

## Specificity (general rule + specific exception)

CPT resolves conflicts by subject specificity on the same object. Specificity is computed from the SUBJECT pattern: depth of the dotted path, plus a 1.0 bonus for exact FQNs (no `.*`). Wildcards get depth only. So `app.*` = 1.0, `app.api.*` = 2.0, `app.api` = 3.0, `app.api.users` = 4.0. A `requires_*` edge with higher subject specificity suppresses a `prohibits_*` edge on the same object (and vice versa). This is how exceptions get expressed.

When an ADR says "only X may do Y" or "only through X", emit TWO edges: a general prohibition with a wildcard subject, plus a specific requirement on X. The specific subject is the exception; the wildcard subject is the rule.

Example: ADR says "the only way to instantiate `app.repository.UnitOfWork` is through `app.services.TransactionManager`".
- subject `app.*` predicate `prohibits_implementation` object `app.repository.UnitOfWork` (general: nobody implements UnitOfWork, specificity 1.0)
- subject `app.services.TransactionManager` predicate `requires_implementation` object `app.repository.UnitOfWork` (specific exception: TransactionManager implements UnitOfWork, specificity 5.0; suppresses the general prohibit when TransactionManager implements it)

Example: ADR says "only `app.api` may import `flask`".
- subject `app.*` predicate `prohibits_dependency` object `flask` (general: nobody depends on flask, specificity 1.0)
- subject `app.api.*` predicate `requires_dependency` object `flask` (specific exception: app.api depends on flask, specificity 2.0)

Use the narrowest wildcard that still captures the general rule (`app.*` over `app.api.*` if the prohibition spans the whole codebase).

## Negative constraints from prescriptive decisions

A prescriptive decision ("we chose X") often implies a prohibition on the alternatives it replaced. If the ADR names the rejected option, emit a `prohibits_*` edge for it too. Example: ADR says "we replace Flask with Django" -> emit `app.* requires_dependency django` AND `app.* prohibits_dependency flask`.

## Output format

Respond with a JSON array of constraint objects. Each object has:
- subject: FQN pattern
- object: FQN pattern
- predicate: one of the four predicate types above
- justification: short explanation citing the ADR text
- adr_id: "{adr_id}"
- adr_path: "{adr_path}"

If the ADR contains no enforceable architectural constraints, return an empty array [].

## Examples

The examples below use the actual module list for this codebase graph — app.routes,
app.models, app.services, app.middleware.auth — not generic names from a typical project.
**Always ground your FQNs in the module list you were actually given**, not these examples.

Example 1: ADR prohibits route handlers from accessing models directly.

Step 1: Call list_modules → see app.routes, app.models, app.services, app.middleware.auth
Step 2: Call dive("app.routes", depth=1) → see route handler functions
Step 3: Call dive("app.models", depth=1) → see model classes

Result:
[{{"subject": "app.routes.*", "object": "app.models.*", "predicate": "prohibits_dependency", "justification": "ADR states route handlers must not import model classes directly; data access must go through the service layer", "adr_id": "{adr_id}", "adr_path": "{adr_path}"}}]

Example 2: ADR requires every endpoint to enforce auth middleware.

Step 1: Call list_modules → see app.routes, app.models, app.services, app.middleware.auth
Step 2: Call dive("app.middleware.auth", depth=1) → see the auth decorator/class
Step 3: Call dive("app.routes", depth=1) → see route handler functions

Result:
[{{"subject": "app.routes.*", "object": "app.middleware.auth.*", "predicate": "requires_dependency", "justification": "ADR states every endpoint must apply the auth middleware before handling a request", "adr_id": "{adr_id}", "adr_path": "{adr_path}"}}]

Example 3: ADR requires all service classes to inherit from a shared base service class.
The base class isn't visible from a depth=1 dive — it lives inside a submodule that only
appears once you go one level deeper.

Step 1: Call list_modules → see app.routes, app.models, app.services, app.middleware.auth
Step 2: Call dive("app.services", depth=1) → see submodules app.services.user, 
app.services.order, app.services.base (no classes visible yet at this depth)
Step 3: Call dive("app.services", depth=2) → see classes inside each submodule, including 
app.services.base.ServiceBase

Result:
[{{"subject": "app.services.*", "object": "app.services.base.ServiceBase", "predicate": "requires_implementation", "justification": "ADR states all service classes must inherit from the shared base service class to standardize transaction handling", "adr_id": "{adr_id}", "adr_path": "{adr_path}"}}]
"""


def _extract_json(text: str) -> str:
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    # Try array first (our output is an array)
    start = stripped.find("[")
    if start >= 0:
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] in ("[", "{"):
                depth += 1
            elif stripped[i] in ("]", "}"):
                depth -= 1
                if depth == 0:
                    return stripped[start : i + 1]
    # Fallback to single object
    start = stripped.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(stripped)):
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    return stripped[start : i + 1]
    return stripped


def _parse_edges(response_content: str, adr_id: str, adr_path: str) -> list[ConstraintEdge]:
    cleaned = _extract_json(response_content)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        log.warning("unified_resolver: failed to parse LLM response as JSON: %s", response_content[:200])
        return []

    if isinstance(data, dict):
        data = [data]

    edges: list[ConstraintEdge] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject", "")
        object_ = item.get("object", "")
        predicate_str = item.get("predicate", "")
        if not subject or not object_:
            log.warning("unified_resolver: skipping edge with empty subject or object: %s", item)
            continue
        try:
            predicate = PredicateType(predicate_str)
        except ValueError:
            log.warning("unified_resolver: unknown predicate %s, skipping", predicate_str)
            continue
        try:
            edge = ConstraintEdge(
                subject=subject,
                predicate=predicate,
                object=object_,
                justification=item.get("justification", ""),
                adr_id=item.get("adr_id", adr_id),
                adr_path=item.get("adr_path", adr_path),
            )
            edges.append(edge)
        except ValueError:
            log.warning("unified_resolver: invalid edge skipped: %s", item)
            continue
    return edges


def _add_wildcard_for_modules(fqn_pattern: str, adg: ADG) -> str:
    for node in adg.nodes:
        if str(node.fqn) == fqn_pattern and node.kind == FQNKind.MODULE:
            return fqn_pattern + ".*"
    return fqn_pattern


def _is_internal(fqn_pattern: str, adg: ADG) -> bool:
    base = fqn_pattern.rstrip(".*").rstrip(".*")
    for node in adg.nodes:
        if str(node.fqn) == base:
            return True
        if str(node.fqn).startswith(base + "."):
            return True
    return False


def _root_segments(adg: ADG) -> set[str]:
    # ponytail: top-level modules = MODULE nodes with no CONTAINS parent
    children = {e.target for e in adg.edges if e.kind == "CONTAINS"}
    return {
        str(n.fqn).split(".")[0]
        for n in adg.nodes
        if n.kind == FQNKind.MODULE and str(n.fqn) not in children
    }


def _external_packages(adg: ADG) -> set[str]:
    # ponytail: external import roots = first segments of IMPORTS targets not in roots
    roots = _root_segments(adg)
    return {
        e.target.split(".")[0]
        for e in adg.edges
        if e.kind == "IMPORTS" and e.target.split(".")[0] not in roots
    }


def _validate_edge(edge: ConstraintEdge, adg: ADG, external_packages: set[str]) -> bool:
    """Return True if edge passes root-namespace-aware validation.

    Subject: internal pattern (first segment in roots) must match an ADG node;
    external subject passes (rare, e.g., framing the ADR from the package's POV).
    Object: predicate-aware.
      - `requires_*`: external object passes (LLM grounded by prompt's
        External packages section; transitive deps like `postgresql` reached
        via `django.db` are not in IMPORTS but should not be dropped).
        Internal object must match the ADG.
      - `prohibits_*`: external object passes unvalidated (linter checks absence);
        internal object must match the ADG.
    """
    all_fqns = {str(n.fqn) for n in adg.nodes}
    roots = _root_segments(adg)
    _ = external_packages  # ponytail: kept for API stability; strict-list check removed (transitive deps)

    # Subject
    subj_first = edge.subject.split(".")[0].rstrip(".*")
    if subj_first in roots:
        subj_base = edge.subject.rstrip(".*")
        if not (subj_base in all_fqns or any(f.startswith(subj_base + ".") for f in all_fqns)):
            return False
    # External subject passes (no ADG check).

    # Object: only validate if it looks internal (first segment in roots).
    # External objects pass for both requires_* (transitive deps) and prohibits_* (absent pkgs).
    obj_first = edge.object.split(".")[0].rstrip(".*")
    if obj_first in roots:
        obj_base = edge.object.rstrip(".*")
        if not (obj_base in all_fqns or any(f.startswith(obj_base + ".") for f in all_fqns)):
            return False
    return True


def _log_trace(
    adr_id: str,
    adr_path: str,
    edges: list[ConstraintEdge],
    trace: ResolutionTrace,
) -> None:
    from pathlib import Path

    trace_dir = Path(os.environ.get("RESOLVER_TRACE_DIR", "."))
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "resolver_traces.jsonl"

    record = {
        "resolver": "unified",
        "adr_id": adr_id,
        "adr_path": adr_path,
        "num_edges": len(edges),
        "edges": [{"subject": e.subject, "object": e.object, "predicate": e.predicate.value} for e in edges],
        "pre_validation_edges": trace.pre_validation_edges,
        "hit_cap": trace.hit_cap,
        "parse_failed": trace.parse_failed,
        "tool_calls": trace.tool_calls,
    }
    with open(trace_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def resolve_adr_constraints(
    adr_text: str,
    adr_id: str,
    adr_path: str,
    adg: ADG,
    config: LangExtractConfig,
) -> list[ConstraintEdge]:
    """Resolve a single ADR's full text to ConstraintEdge objects.

    One LLM session per ADR. The agent reads the complete ADR, uses list_modules
    and dive tools to map prose concepts to FQN patterns, and outputs constraint
    edges directly. No SymbolicConstraint intermediate.
    """
    api_key = config.api_key
    if not api_key:
        raise ValueError(f"API key not found in environment variable {config.api_key_env}")

    client = OpenAI(api_key=api_key, base_url=config.model_url)

    modules = list_modules(adg)
    module_hint = ", ".join(f"{m['fqn']}({m['kind']})" for m in modules[:20])
    if len(modules) > 20:
        module_hint += ", ..."

    external_packages = _external_packages(adg)
    external_packages_hint = ", ".join(sorted(external_packages)) if external_packages else "(none)"

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        adr_text=adr_text, adr_id=adr_id, adr_path=adr_path,
        module_hint=module_hint, external_packages_hint=external_packages_hint,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Identify architectural constraints in this ADR and resolve them to FQN patterns."},
    ]

    tool_call_count = 0
    tool_call_trace: list[dict] = []
    last_tool_signature: tuple[str, str] | None = None
    hit_cap = False

    while tool_call_count < TOOL_CALL_CAP:
        response = client.chat.completions.create(
            model=config.model_id,
            messages=messages,
            tools=_TOOLS,
            temperature=config.temperature,
        )
        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            if msg.content:
                edges = _parse_edges(msg.content, adr_id, adr_path)
                edges = [
                    ConstraintEdge(
                        subject=_add_wildcard_for_modules(e.subject, adg),
                        predicate=e.predicate,
                        object=_add_wildcard_for_modules(e.object, adg) if _is_internal(e.object, adg) else e.object,
                        justification=e.justification,
                        adr_id=e.adr_id,
                        adr_path=e.adr_path,
                    )
                    for e in edges
                ]
                valid_edges = [e for e in edges if _validate_edge(e, adg, external_packages)]
                if len(valid_edges) < len(edges):
                    dropped = [e for e in edges if e not in valid_edges]
                    log.warning("unified_resolver: dropped %d edges with nonexistent FQNs for %s", len(dropped), adr_id)
                pre_val = [{"subject": e.subject, "object": e.object, "predicate": e.predicate.value, "valid": e in valid_edges} for e in edges]
                trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=False, parse_failed=False, pre_validation_edges=pre_val)
                _log_trace(adr_id, adr_path, valid_edges, trace)
                return valid_edges
            log.warning("unified_resolver: LLM returned empty response for %s", adr_id)
            trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=False, parse_failed=True)
            _log_trace(adr_id, adr_path, [], trace)
            return []

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            tool_call_count += 1
            args = json.loads(tc.function.arguments)
            tool_call_trace.append({"name": tc.function.name, "arguments": args})
            signature = (tc.function.name, tc.function.arguments)
            if signature == last_tool_signature:
                messages.append({
                    "role": "user",
                    "content": "You just called the same function with identical arguments again. Stop repeating tool calls and produce your final answer as a JSON array now.",
                })
            last_tool_signature = signature
            result = _TOOL_FUNCTIONS[tc.function.name](args, adg)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    # Hit cap: request best-effort resolution
    hit_cap = True
    log.warning("unified_resolver: hit tool call cap (%d) for %s, requesting best-effort", TOOL_CALL_CAP, adr_id)
    messages.append({
        "role": "user",
        "content": "You have reached the tool call limit. Based on the graph context you have already gathered, provide your best-effort constraints now as a JSON array. Do not make any more tool calls.",
    })
    try:
        response = client.chat.completions.create(model=config.model_id, messages=messages, temperature=config.temperature)
        content = response.choices[0].message.content
        if content:
            edges = _parse_edges(content, adr_id, adr_path)
            edges = [
                ConstraintEdge(
                    subject=_add_wildcard_for_modules(e.subject, adg),
                    predicate=e.predicate,
                    object=_add_wildcard_for_modules(e.object, adg) if _is_internal(e.object, adg) else e.object,
                    justification=e.justification,
                    adr_id=e.adr_id,
                    adr_path=e.adr_path,
                )
                for e in edges
            ]
            valid_edges = [e for e in edges if _validate_edge(e, adg, external_packages)]
            if len(valid_edges) < len(edges):
                dropped = [e for e in edges if e not in valid_edges]
                log.warning("unified_resolver: dropped %d edges with nonexistent FQNs for %s", len(dropped), adr_id)
            pre_val = [{"subject": e.subject, "object": e.object, "predicate": e.predicate.value, "valid": e in valid_edges} for e in edges]
            trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=True, parse_failed=False, pre_validation_edges=pre_val)
            _log_trace(adr_id, adr_path, valid_edges, trace)
            return valid_edges
    except Exception:
        log.warning("unified_resolver: best-effort request failed for %s", adr_id)

    trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=hit_cap, parse_failed=True)
    _log_trace(adr_id, adr_path, [], trace)
    return []


if __name__ == "__main__":
    # ponytail: self-check
    from services.fqn import FQN
    from services.models import Edge, FQNNode

    nodes = [
        FQNNode(fqn=FQN.from_dotted("app"), kind=FQNKind.MODULE, file_path="app/__init__.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.api"), kind=FQNKind.MODULE, file_path="app/api.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
        FQNNode(fqn=FQN.from_dotted("app.db"), kind=FQNKind.MODULE, file_path="app/db.py", line_start=0, line_end=0, start_byte=0, end_byte=0),
    ]
    edges_list = [
        Edge(source="app", target="app.api", kind="CONTAINS"),
        Edge(source="app", target="app.db", kind="CONTAINS"),
    ]
    adg = ADG(nodes=nodes, edges=edges_list)

    # _extract_json tests
    assert _extract_json('```json\n[{"subject": "app.api.*"}]\n```') == '[{"subject": "app.api.*"}]'
    assert _extract_json('[{"x": 1}]') == '[{"x": 1}]'
    assert _extract_json('some text {"a": 1} more') == '{"a": 1}'
    print("_extract_json OK")

    # _add_wildcard_for_modules tests
    assert _add_wildcard_for_modules("app.api", adg) == "app.api.*"
    assert _add_wildcard_for_modules("app.api.*", adg) == "app.api.*"
    assert _add_wildcard_for_modules("app.db.Foo", adg) == "app.db.Foo"
    print("_add_wildcard_for_modules OK")

    # _parse_edges tests
    edges_out = _parse_edges(
        json.dumps([{"subject": "app.api.*", "object": "app.db.*", "predicate": "prohibits_dependency", "justification": "API must not import DB", "adr_id": "ADR-1", "adr_path": "docs/adr/1.md"}]),
        "ADR-1", "docs/adr/1.md",
    )
    assert len(edges_out) == 1
    assert edges_out[0].subject == "app.api.*"
    assert edges_out[0].predicate == PredicateType.PROHIBITS_DEPENDENCY
    print("_parse_edges OK")

    # empty array
    assert _parse_edges("[]", "ADR-1", "docs/adr/1.md") == []
    print("empty array OK")

    # single dict instead of array
    edges_out = _parse_edges(
        json.dumps({"subject": "app.api.*", "object": "app.db.*", "predicate": "prohibits_dependency", "justification": "test", "adr_id": "ADR-1", "adr_path": "docs/adr/1.md"}),
        "ADR-1", "docs/adr/1.md",
    )
    assert len(edges_out) == 1
    print("single dict OK")

    # invalid predicate skipped
    edges_out = _parse_edges(
        json.dumps([{"subject": "app.api.*", "object": "app.db.*", "predicate": "unknown_predicate", "justification": "test", "adr_id": "ADR-1", "adr_path": "docs/adr/1.md"}]),
        "ADR-1", "docs/adr/1.md",
    )
    assert len(edges_out) == 0
    print("invalid predicate skipped OK")

    # _root_segments tests
    assert _root_segments(adg) == {"app"}
    print("_root_segments OK")

    # _external_packages: empty (no IMPORTS edges in test ADG)
    assert _external_packages(adg) == set()
    print("_external_packages OK")

    ext_pkgs = {"elasticsearch"}  # simulated imports list

    # _validate_edge: requires_* external object in list passes
    ext_obj_edge = ConstraintEdge(subject="app.api.*", predicate=PredicateType.REQUIRES_DEPENDENCY, object="elasticsearch", justification="ext", adr_id="ADR-1", adr_path="docs/adr/1.md")
    assert _validate_edge(ext_obj_edge, adg, ext_pkgs) is True
    print("_validate_edge requires_* external object in list OK")

    # _validate_edge: requires_* external object NOT in list passes (transitive deps, e.g. postgresql via django.db)
    req_transitive_edge = ConstraintEdge(subject="app.api.*", predicate=PredicateType.REQUIRES_DEPENDENCY, object="postgresql", justification="transitive", adr_id="ADR-1", adr_path="docs/adr/1.md")
    assert _validate_edge(req_transitive_edge, adg, ext_pkgs) is True
    print("_validate_edge requires_* external object not in list (transitive) OK")

    # _validate_edge: prohibits_* external object NOT in list passes (linter checks absence)
    pro_absent_edge = ConstraintEdge(subject="app.api.*", predicate=PredicateType.PROHIBITS_DEPENDENCY, object="rest_framework", justification="absent", adr_id="ADR-1", adr_path="docs/adr/1.md")
    assert _validate_edge(pro_absent_edge, adg, ext_pkgs) is True
    print("_validate_edge prohibits_* external object not in list OK")

    halluc_obj_edge = ConstraintEdge(subject="app.api.*", predicate=PredicateType.REQUIRES_DEPENDENCY, object="app.hallucinated.*", justification="halluc", adr_id="ADR-1", adr_path="docs/adr/1.md")
    assert _validate_edge(halluc_obj_edge, adg, ext_pkgs) is False
    print("_validate_edge hallucinated internal object dropped OK")

    valid_internal_edge = ConstraintEdge(subject="app.api.*", predicate=PredicateType.PROHIBITS_DEPENDENCY, object="app.db.*", justification="valid", adr_id="ADR-1", adr_path="docs/adr/1.md")
    assert _validate_edge(valid_internal_edge, adg, ext_pkgs) is True
    print("_validate_edge valid internal OK")

    print("All self-checks passed")