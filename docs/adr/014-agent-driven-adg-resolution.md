# 14. Agent-Driven ADG Resolution

Date: 2026-07-26

## Status

Partially superseded by [ADR 15](./015-unified-extraction-agent.md) (extraction stage). Resolution approach (ADG tools, provenance) is retained.

## Context

ADR 8 replaced ADR 7's LLM resolution layer with a symbolic resolver that uses bounded module lists and substring matching. Testing on real repos (OpenLobby, python-tuf) shows 40-60% false positive rates. The core problem: the LLM guesses FQN patterns without seeing the code graph, and the fuzzy substring fallback produces wrong matches (e.g., "metadata" substring-matching `tuf.api.metadata.Metadata`).

When an agent manually explores the ADG and code, it resolves the same constraints correctly and finds genuine violations the symbolic resolver misses entirely. The symbolic resolver cannot see the graph; the agent can.

Additionally, the `role_general`/`role_specific` split in extraction forces the LLM to pick module names from a bounded list before it has seen the code structure. This is unreliable because natural language does not map 1:1 to code structure.

## Decisions

### 1. Extraction produces prose constraints, not FQN patterns

Replace the 7-field `SymbolicConstraint` with a 5-field schema:

```python
@dataclass
class SymbolicConstraint:
    subject: str          # prose from ADR (e.g., "route handlers")
    predicate: PredicateType  # enum, unchanged
    object: str            # prose from ADR (e.g., "data models")
    justification: str     # verbatim from ADR
    adr_id: str
    adr_path: str
```

The extractor never sees the module list. It pulls the constraint directly from ADR text. `subject` and `object` are natural language, not FQN patterns.

### 2. Agent-driven resolution replaces symbolic resolver

The agent receives a `SymbolicConstraint` and traverses the ADG using tool calls to resolve prose to FQN patterns:

```
SymbolicConstraint(prose)
    |
    v
[Agent: list_modules() -> list_children() -> ...]
    |   subject="app.routes.*", object="app.models.*"
    v
ConstraintEdge(FQN patterns)
```

The agent uses a raw SDK tool-calling loop (OpenAI-compatible API). No framework dependency.

### 3. Four ADG query tools

| Tool | Returns | Purpose |
|------|---------|---------|
| `list_modules()` | Top-level module FQNs | Entry point |
| `list_children(fqn)` | All contained nodes (classes, methods, functions) | Drill into structure. Replaces both `list_classes` and `list_contains`. |
| `list_imports(fqn)` | Modules this module imports | Identify dependency targets |
| `list_inherits(fqn)` | Classes this class inherits from | Identify inheritance targets |

Tools query the in-memory ADG object. No Neo4j dependency during resolution. Each tool is a thin Python function wrapping the ADG data model.

### 4. One agent session per constraint

Each `SymbolicConstraint` gets its own agent session. Tool call cap of ~20 per constraint (~10 per side). If the cap is hit, log for human review and produce the best-effort match so far.

### 5. Best-effort resolution, never null

The agent always produces `subject` and `object` FQN patterns. If exact resolution fails, climb to the nearest ancestor with a wildcard (e.g., `app.services.*` if `UserService` isn't found). Never produce null.

Prefer false positives over false negatives. Broad matches can be dismissed via existing CLI mechanisms. Dropped constraints are invisible and hard to audit.

### 6. Open-weight models for resolution

Use Gemma 4 or Qwen 3.5 for agent resolution. Cost per run is negligible at these prices. Upgrade to frontier models only if accuracy is insufficient.

### 7. Self-loop constraints remain filtered

No change to the CPT engine or `ConstraintEdge.__post_init__`. Self-loop constraints (subject == object) are still filtered. Implementation-predicate self-loops are out of scope.

### 8. EXTERNAL nodes handled by existing logic

When the agent resolves a side to an external dependency, it produces the FQN pattern and the existing `EXTERNAL` node creation in the CPT pipeline handles it. No special agent output format.

### 9. Review agent is future scope

The demo outputs raw CPT results with resolution provenance (which tool calls led to each FQN). A future review agent can dismiss false positives using the existing `dismiss` CLI command.

## Consequences

- `SymbolicConstraint` drops `subject_role_general`, `subject_role_specific`, `object_role_general`, `object_role_specific`. Replaced by single `subject` and `object` prose fields.
- `symbolic_resolver.py` is replaced by `agent_resolver.py`.
- Extraction prompt drops the module list context and `role_general`/`role_specific` output format.
- The agent adds an LLM call per constraint (~50-100 calls for 10 constraints). Cost is acceptable with open-weight models.
- False positives may increase from broad wildcard fallbacks, but are dismissable. False negatives decrease because nothing is silently dropped.
- No new framework dependency. The agent loop is raw OpenAI-compatible tool calling.
- ADR 7's LLM resolution layer and ADR 8's symbolic resolver are both replaced.

## Superseded decisions

| ADR 7 Decision | New Status |
|----------------|------------|
| LLM remaps orphan FQN patterns | Replaced by agent-driven resolution |
| Candidate collection via prefix-scoped walk | Replaced by ADG tool traversal |
| One LLM call per orphaned side | Replaced by agent tool-calling loop |
| `gather_candidates` function | Removed |
| `_call_resolution_llm` | Removed |
| In-place constraint modification | Replaced; `SymbolicConstraint` produces `ConstraintEdge` via agent |

| ADR 8 Decision | New Status |
|----------------|------------|
| LLM picks from module list | Removed; extraction is prose-only |
| Kind-filtered resolution | Removed; agent resolves by exploring the graph |
| Substring matching fallback | Removed; agent climbs to ancestors with wildcards |
| `role_general` / `role_specific` fields | Removed; single `subject` / `object` prose fields |
| External dependency shortcut | Unchanged; agent produces FQN, existing EXTERNAL logic handles it |
| `ResolvedConstraint.match_source` tracking | Replaced by resolution provenance in agent output |