"""Agent resolver: resolves SymbolicConstraints to ConstraintEdges via
OpenAI-compatible SDK tool-calling loop against the ADG.

One LLM session per constraint. Best-effort: always produces a FQN pattern,
falling back to ancestor + wildcard if exact match fails. External dependencies
pass through to existing EXTERNAL node logic.
"""
from __future__ import annotations

import json
import logging

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


def _system_prompt(constraint: SymbolicConstraint, adg: ADG) -> str:
    modules = list_modules(adg)
    module_hint = ", ".join(modules[:20])
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
) -> list[ConstraintEdge]:
    """Resolve a single SymbolicConstraint via tool-calling loop."""
    messages = [
        {"role": "system", "content": _system_prompt(constraint, adg)},
        {"role": "user", "content": f"Resolve this constraint: {constraint.subject} {constraint.predicate.value} {constraint.object}"},
    ]

    tool_call_count = 0

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
                    return [edge]
            # LLM returned empty content with no tool calls
            log.warning("agent_resolver: LLM returned empty response for %s", constraint.adr_id)
            return []

        # Process tool calls
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            tool_call_count += 1
            result = _execute_tool(tc, adg)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # Hit cap: send one final message requesting best-effort resolution
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
                return [edge]
    except Exception:
        log.warning("agent_resolver: best-effort request failed for %s", constraint.adr_id)
    return []


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


def resolve_agent_constraints(
    symbolic: list[SymbolicConstraint],
    adg: ADG,
    config: LangExtractConfig,
) -> list[ConstraintEdge]:
    """Resolve SymbolicConstraints to ConstraintEdges via agent tool-calling.

    One LLM session per constraint. External dependencies pass through to
    existing EXTERNAL node logic. Best-effort: always try to produce a FQN
    pattern, falling back to ancestor + wildcard if exact match fails.
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
        edges = _resolve_one(constraint, adg, client, config.model_id)
        all_edges.extend(edges)

    return all_edges