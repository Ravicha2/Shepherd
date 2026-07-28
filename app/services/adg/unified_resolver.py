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

The following modules exist in the codebase graph. You MUST use FQN patterns from this list. Do NOT invent module names.

{module_hint}

**CRITICAL**: You MUST use FQN patterns from the module list above. Do NOT invent module names. If the ADR refers to "routes" and the module list shows `app.routes`, use `app.routes.*`. If no module matches a concept from the ADR, return an empty array.

## Predicate types

- prohibits_dependency: subject must not depend on (import) object
- requires_dependency: subject must depend on (import) object
- prohibits_implementation: subject must not implement (inherit from, subclass) object
- requires_implementation: subject must implement (inherit from, subclass) object

## Wildcard

The `.*` suffix denotes a wildcard pattern: it matches the prefix itself **and** every descendant FQN that starts with `prefix.`.
For example, `app.routes.*` matches `app.routes`, `app.routes.user`, and `app.routes.user.get_handler`.

When generating constraints, use wildcards for architectural rules that apply to an entire module or layer (for example, "no route handler may import any model class" becomes `app.routes.*` → `app.models.*`). Use exact FQNs when the rule targets one specific entity (for example, "all services must inherit from `app.services.base.ServiceBase`").

## Output format

Respond with a JSON array of constraint objects. Each object has:
- subject: FQN pattern
- object: FQN pattern
- predicate: one of the four predicate types above
- justification: short explanation citing the ADR text
- adr_id: "{adr_id}"
- adr_path: "{adr_path}"

For external packages not in the graph, use the package name as-is (no wildcard).
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


def _validate_edge(edge: ConstraintEdge, adg: ADG) -> bool:
    """Return True if edge subject and object patterns match at least one node in the ADG."""
    all_fqns = {str(n.fqn) for n in adg.nodes}
    for pattern in (edge.subject, edge.object):
        base = pattern.rstrip(".*")
        if base in all_fqns:
            continue
        if any(f.startswith(base + ".") for f in all_fqns):
            continue
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

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        adr_text=adr_text, adr_id=adr_id, adr_path=adr_path, module_hint=module_hint,
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
                valid_edges = [e for e in edges if _validate_edge(e, adg)]
                if len(valid_edges) < len(edges):
                    dropped = [e for e in edges if e not in valid_edges]
                    log.warning("unified_resolver: dropped %d edges with nonexistent FQNs for %s", len(dropped), adr_id)
                trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=False, parse_failed=False)
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
            valid_edges = [e for e in edges if _validate_edge(e, adg)]
            if len(valid_edges) < len(edges):
                dropped = [e for e in edges if e not in valid_edges]
                log.warning("unified_resolver: dropped %d edges with nonexistent FQNs for %s", len(dropped), adr_id)
            trace = ResolutionTrace(tool_calls=tool_call_trace, hit_cap=True, parse_failed=False)
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

    print("All self-checks passed")