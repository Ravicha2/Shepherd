"""Agent resolver: resolves SymbolicConstraints to ConstraintEdges via
OpenAI-compatible SDK tool-calling loop against the ADG.

One LLM session per constraint. Best-effort: always produces a FQN pattern,
falling back to ancestor + wildcard if exact match fails. External dependencies
pass through to existing EXTERNAL node logic.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from services.adg.adg_tools import dive, list_modules
from services.extract.config import LangExtractConfig
from services.fqn import FQN
from services.models import (
    ADG,
    ConstraintEdge,
    FQNKind,
    FQNNode,
    PredicateType,
    SymbolicConstraint,
)

log = logging.getLogger(__name__)


@dataclass
class ResolutionTrace:
    """Record of tool calls and outcomes during a single resolution."""
    tool_calls: list[dict]  # [{name, arguments}]
    hit_cap: bool = False
    parse_failed: bool = False


@dataclass
class ResolutionResult:
    """Result of resolving a single constraint, including trace for diagnosis."""
    edge: ConstraintEdge | None
    trace: ResolutionTrace

TOOL_CALL_CAP = 20

# Tool schemas for the LLM
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
                "(bidirectional: follows edges in both directions). Use depth=1 for "
                "direct neighbors, depth=2-3 for broader context. Start with modules "
                "from list_modules, then dive into the ones that match the constraint's "
                "prose description. Implementation predicates (e.g. 'rate limiting', "
                "'caching') may map to conceptual labels not present as graph nodes: "
                "infer the nearest structural FQN from the neighborhood context."
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


def _execute_tool(tool_call, adg: ADG) -> str:
    """Execute a tool call against the ADG and return the result string."""
    name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    return _TOOL_FUNCTIONS[name](arguments, adg)


_FEWSHOT_EXAMPLES = """\
Example 1: Resolving a prose subject to a module-level wildcard.

Constraint: subject="the API module", object="database module", predicate=prohibits_dependency

Step 1: Call list_modules
Result: [{"fqn": "app", "kind": "module"}, {"fqn": "app.api", "kind": "module"}, {"fqn": "app.api.users", "kind": "module"}, {"fqn": "app.database", "kind": "module"}, ...]

Step 2: "the API module" matches app.api(module). Call dive("app.api", depth=2)
Result: nodes include app.api, app.api.users, app.api.routes; edges show CONTAINS relationships.

Step 3: "database module" matches app.database(module). Call dive("app.database", depth=1)
Result: nodes include app.database, app.database.query; edges show CONTAINS.

Final answer:
{"subject": "app.api.*", "object": "app.database.*", "predicate": "prohibits_dependency", "justification": "API module must not depend on database module", "adr_id": "ADR-001", "adr_path": "docs/adr/001.md"}

Example 2: Resolving a prose concept to a specific class.

Constraint: subject="modules outside the auth module", object="authentication logic", predicate=prohibits_implementation

Step 1: Call list_modules
Result: [{"fqn": "app", "kind": "module"}, {"fqn": "app.auth", "kind": "module"}, {"fqn": "app.auth.middleware", "kind": "module"}, ...]

Step 2: "auth module" suggests app.auth or app.auth.middleware. Call dive("app.auth.middleware", depth=2)
Result: nodes include app.auth.middleware(module), app.auth.middleware.AuthMiddleware(class), app.auth.middleware.AuthMiddleware.check(method).

Step 3: "authentication logic" maps to AuthMiddleware and its check method. The subject "modules outside the auth module" means everything except app.auth, so use app.* minus auth.

Final answer:
{"subject": "app.*", "object": "app.auth.middleware.AuthMiddleware", "predicate": "prohibits_implementation", "justification": "Only app.auth.middleware may implement authentication", "adr_id": "ADR-008", "adr_path": "docs/adr/008.md"}
"""


def _system_prompt(constraint: SymbolicConstraint, adg: ADG) -> str:
    modules = list_modules(adg)
    module_hint = ", ".join(f"{m['fqn']}({m['kind']})" for m in modules[:20])
    if len(modules) > 20:
        module_hint += ", ..."
    return (
        "You are an architectural decision resolver. Given a SymbolicConstraint "
        "with prose subject/object, traverse the codebase graph using the provided tools "
        "to find the exact FQN patterns that match.\n\n"
        f"Constraint to resolve:\n"
        f"  subject: {constraint.subject}\n"
        f"  object: {constraint.object}\n"
        f"  predicate: {constraint.predicate.value}\n"
        f"  justification: {constraint.justification}\n"
        f"  adr_id: {constraint.adr_id}\n\n"
        f"Available modules (use list_modules for the full list): {module_hint}\n\n"
        "Use list_modules to see all modules, then dive into the ones matching the "
        "constraint's prose description. Implementation predicates (e.g. 'rate limiting', "
        "'caching', 'authentication') describe concepts, not necessarily graph node names. "
        "Map prose concepts to the nearest structural FQN using neighborhood context from dive.\n\n"
        f"Examples:\n{_FEWSHOT_EXAMPLES}\n\n"
        "Respond with a JSON object:\n"
        '{"subject": "<fqn_pattern>", "object": "<fqn_pattern>", '
        '"predicate": "<predicate_value>", "justification": "<text>", '
        '"adr_id": "<id>", "adr_path": "<path>"}\n\n'
        "For module-level FQNs, append .* to match descendants. "
        "For external packages not in the graph, use the package name as-is."
    )


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, stripping markdown fences and surrounding text."""
    import re
    stripped = text.strip()
    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    # Find the first { and match to its closing } by brace counting
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


def _parse_resolution(response_content: str, constraint: SymbolicConstraint) -> ConstraintEdge | None:
    """Parse the LLM's final JSON response into a ConstraintEdge."""
    cleaned = _extract_json(response_content)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        log.warning("agent_resolver: failed to parse LLM response as JSON: %s", response_content[:200])
        return None

    subject = data.get("subject", "")
    object_ = data.get("object", "")
    predicate_str = data.get("predicate", constraint.predicate.value)

    # Map predicate string back to enum
    try:
        predicate = PredicateType(predicate_str)
    except ValueError:
        predicate = constraint.predicate

    if not subject or not object_:
        log.warning("agent_resolver: empty subject or object in resolution")
        return None

    # ponytail: skip self-loop check here, ConstraintEdge.__post_init__ handles it
    try:
        return ConstraintEdge(
            subject=subject,
            predicate=predicate,
            object=object_,
            justification=data.get("justification", constraint.justification),
            adr_id=data.get("adr_id", constraint.adr_id),
            adr_path=data.get("adr_path", constraint.adr_path),
        )
    except ValueError:
        return None


def _add_wildcard_for_modules(fqn_pattern: str, adg: ADG) -> str:
    """If fqn_pattern matches a MODULE node exactly (no wildcard), append .*"""
    for node in adg.nodes:
        if str(node.fqn) == fqn_pattern and node.kind == FQNKind.MODULE:
            return fqn_pattern + ".*"
    return fqn_pattern


def _resolve_one(
    constraint: SymbolicConstraint,
    adg: ADG,
    client: OpenAI,
    model: str,
) -> ResolutionResult:
    """Resolve a single SymbolicConstraint via tool-calling loop."""
    messages = [
        {"role": "system", "content": _system_prompt(constraint, adg)},
        {"role": "user", "content": f"Resolve this constraint: {constraint.subject} {constraint.predicate.value} {constraint.object}"},
    ]

    tool_call_count = 0
    tool_call_trace: list[dict] = []
    hit_cap = False
    parse_failed = False

    while tool_call_count < TOOL_CALL_CAP:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=_TOOLS,
        )

        choice = response.choices[0]
        msg = choice.message

        # No tool calls: final answer
        if not msg.tool_calls:
            if msg.content:
                edge = _parse_resolution(msg.content, constraint)
                if edge:
                    # Enforce wildcard for module-level FQNs
                    edge = ConstraintEdge(
                        subject=_add_wildcard_for_modules(edge.subject, adg),
                        predicate=edge.predicate,
                        object=_add_wildcard_for_modules(edge.object, adg) if _is_internal(edge.object, adg) else edge.object,
                        justification=edge.justification,
                        adr_id=edge.adr_id,
                        adr_path=edge.adr_path,
                    )
                    return ResolutionResult(edge=edge, trace=ResolutionTrace(tool_calls=tool_call_trace, hit_cap=False, parse_failed=False))
                else:
                    parse_failed = True
            # LLM returned empty content with no tool calls
            log.warning("agent_resolver: LLM returned empty response for %s", constraint.adr_id)
            return ResolutionResult(edge=None, trace=ResolutionTrace(tool_calls=tool_call_trace, hit_cap=False, parse_failed=parse_failed))

        # Process tool calls
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            tool_call_count += 1
            tool_call_trace.append({"name": tc.function.name, "arguments": json.loads(tc.function.arguments)})
            result = _execute_tool(tc, adg)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # Hit cap: send one final message requesting best-effort resolution
    hit_cap = True
    log.warning("agent_resolver: hit tool call cap (%d) for %s, requesting best-effort", TOOL_CALL_CAP, constraint.adr_id)
    messages.append({
        "role": "user",
        "content": (
            "You have reached the tool call limit. Based on the graph context you have "
            "already gathered, provide your best-effort resolution now as a JSON object. "
            "Do not make any more tool calls."
        ),
    })
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            # No tools: force text response
        )
        content = response.choices[0].message.content
        if content:
            edge = _parse_resolution(content, constraint)
            if edge:
                edge = ConstraintEdge(
                    subject=_add_wildcard_for_modules(edge.subject, adg),
                    predicate=edge.predicate,
                    object=_add_wildcard_for_modules(edge.object, adg) if _is_internal(edge.object, adg) else edge.object,
                    justification=edge.justification,
                    adr_id=edge.adr_id,
                    adr_path=edge.adr_path,
                )
                return ResolutionResult(edge=edge, trace=ResolutionTrace(tool_calls=tool_call_trace, hit_cap=True, parse_failed=False))
            else:
                parse_failed = True
    except Exception:
        log.warning("agent_resolver: best-effort request failed for %s", constraint.adr_id)
    return ResolutionResult(edge=None, trace=ResolutionTrace(tool_calls=tool_call_trace, hit_cap=hit_cap, parse_failed=parse_failed))


def _is_internal(fqn_pattern: str, adg: ADG) -> bool:
    """Check if an FQN pattern refers to an internal (in-graph) node."""
    # Strip wildcard suffix for lookup
    base = fqn_pattern.rstrip(".*")
    # Also handle patterns like "app.auth.middleware.*"
    base = base.rstrip(".*")
    for node in adg.nodes:
        if str(node.fqn) == base:
            return True
    # Check if it's a prefix of any node (partial match)
    for node in adg.nodes:
        if str(node.fqn).startswith(base + "."):
            return True
    return False


def classify_failure(trace: ResolutionTrace, adg: ADG | None = None) -> str:
    """Classify a miss into a failure mode based on the resolution trace.

    Priority: parse_failure > missing (cap hit/empty) > no_dive > wrong_fqn > wrong_specificity.
    """
    if trace.parse_failed:
        return "parse_failure"
    if trace.hit_cap or (not trace.tool_calls):
        return "missing"
    dive_calls = [tc for tc in trace.tool_calls if tc["name"] == "dive"]
    if not dive_calls:
        return "no_dive"
    if adg is not None:
        valid_fqns = {str(n.fqn) for n in adg.nodes}
        all_dive_fqns_valid = all(tc["arguments"].get("fqn", "") in valid_fqns for tc in dive_calls)
        if not all_dive_fqns_valid:
            return "wrong_fqn"
    return "wrong_specificity"


def _log_trace(
    constraint: SymbolicConstraint,
    result: ResolutionResult,
    adg: ADG,
) -> None:
    """Append a JSONL trace record for the resolution attempt."""
    import os as _os
    from pathlib import Path as _Path

    trace_dir = _Path(_os.environ.get("RESOLVER_TRACE_DIR", "."))
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "resolver_traces.jsonl"

    failure_mode = None if result.edge is not None else classify_failure(result.trace, adg)

    record = {
        "adr_id": constraint.adr_id,
        "subject": constraint.subject,
        "object": constraint.object,
        "predicate": constraint.predicate.value,
        "resolved_subject": result.edge.subject if result.edge else None,
        "resolved_object": result.edge.object if result.edge else None,
        "failure_mode": failure_mode,
        "hit_cap": result.trace.hit_cap,
        "parse_failed": result.trace.parse_failed,
        "tool_calls": result.trace.tool_calls,
    }
    with open(trace_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def resolve_agent_constraints(
    symbolic: list[SymbolicConstraint],
    adg: ADG,
    config: LangExtractConfig,
) -> list[ConstraintEdge]:
    """Resolve SymbolicConstraints to ConstraintEdges via agent tool-calling.

    One LLM session per constraint. External dependencies pass through to
    existing EXTERNAL node logic. Best-effort: always try to produce a FQN
    pattern, falling back to ancestor + wildcard if exact match fails.
    Traces are logged as JSONL to RESOLVER_TRACE_DIR/resolver_traces.jsonl.
    """
    if not symbolic:
        return []

    import os

    api_key = config.api_key
    if not api_key:
        raise ValueError(f"API key not found in environment variable {config.api_key_env}")

    client = OpenAI(
        api_key=api_key,
        base_url=config.model_url,
    )

    all_edges: list[ConstraintEdge] = []

    for constraint in symbolic:
        result = _resolve_one(constraint, adg, client, config.model_id)
        _log_trace(constraint, result, adg)
        if result.edge is not None:
            all_edges.append(result.edge)

    return all_edges