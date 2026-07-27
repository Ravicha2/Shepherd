# 15. Unified Extraction Agent

Date: 2026-07-27

## Status

Accepted (supersedes ADR 14 extraction stage, retains ADR 14 resolution tools and provenance)

## Context

ADR 14 replaced ADR 8's symbolic resolver with an agent-driven resolver. The pipeline remained two-stage: extraction produces `SymbolicConstraint` prose, then a per-constraint agent resolves prose to FQN patterns.

Testing the full pipeline on python-tuf (5 ADRs, 5 detected violations) revealed that the **extraction stage** is the dominant source of error, not the resolution stage:

| Violation | ADR | Predicate | Verdict | Root Cause |
|-----------|-----|-----------|---------|------------|
| 1 | ADR 0004, `tuf.*` prohibits_dependency on `securesystemslib.formats` | Borderline | Extraction correctly identifies the prohibition but over-scopes `tuf.*` |
| 2 | ADR 0004, `tuf.ngclient` prohibits_dependency on `securesystemslib.formats` | False positive | Resolution stage matched incorrectly: no such import exists in ngclient |
| 3 | ADR 0006, `tuf.api.serialization.*` prohibits_dependency on `tuf.api.metadata.Metadata` | False positive | Extraction misclassified: importing Metadata as a type hint in a separate serialization module is the ADR's intended design, not a violation |
| 4 | ADR 0006, `tuf.api.serialization.*` prohibits_implementation of `tuf.api.metadata.Metadata` | False positive | Extraction misclassified: serialization classes inherit from Deserializer/Serializer interfaces, not Metadata |
| 5 | ADR 0010, `tuf.repository.*` prohibits_implementation of `Repository` | False positive | Extraction misclassified: ADR 0010 **prescribes** building a minimal repository abstraction. The Repository class IS the decision outcome, not a violation of it |

Precision: ~20% (1 borderline out of 5). The extraction stage misclassifies **prescriptive decisions** ("we chose to build X") as **prohibitions** ("we prohibit X") because it processes ADR text without the Decision Outcome section context. The resolver then faithfully resolves the wrong constraints.

Separating extraction from resolution forces the extractor to guess constraint semantics from fragments. An agent that reads the full ADR, including Decision Outcome and consequences, can distinguish prescription from prohibition.

## Decisions

### 1. Single unified agent replaces two-stage pipeline

One LLM session per ADR. The agent reads the full ADR text (including Context, Decision Outcome, Pros, Cons) and produces `ConstraintEdge` objects directly. No intermediate `SymbolicConstraint`.

```
ADR text → [Unified Agent: reads full text, explores ADG via tools] → list[ConstraintEdge]
```

### 2. Agent sees full ADR text

The system prompt includes the complete ADR document. This lets the agent:

- Read the Decision Outcome section to distinguish prescriptive decisions from prohibitions
- Use Consequences/Pros/Cons as evidence for constraint predicates
- Avoid extracting constraints that are the ADR's chosen solution, not its rules

### 3. Same ADG tools as ADR 14

The agent uses `list_modules` and `dive` (renamed from `list_children`) to map prose concepts to FQN patterns. No change to the ADG tool interface.

### 4. One session per ADR, not per constraint

ADR 14 used one agent session per `SymbolicConstraint`. The unified agent uses one session per ADR. Within that session, the agent may produce multiple constraints, each with its own tool calls. Tool call cap of 20 per session with best-effort fallback.

### 5. Extraction prompt module is removed

The `SymbolicConstraint` dataclass, extraction prompt, and per-constraint agent resolver are all replaced by the unified agent. `SymbolicConstraint` no longer exists in the data model.

### 6. Resolution provenance preserved

Each `ConstraintEdge` includes provenance: which tool calls led to the subject and object FQN patterns. Same auditability as ADR 14, just produced in a single pass.

## Consequences

- Extraction and resolution are no longer separate stages. The unified agent does both.
- `SymbolicConstraint` is removed from the data model. `ConstraintEdge` is the only constraint type.
- False positive rate should drop significantly: the agent can read "we chose option 3" and not extract a prohibition from it.
- `services/extract/` module is removed. `services/adg/unified_resolver.py` replaces both extraction and resolution.
- The pipeline (`pipeline.py`) calls one function instead of two: `resolve_adr_constraints` instead of `extract_all_adrs` + `resolve_agent_constraints`.
- Cost: one LLM session per ADR (not per constraint). For repos with ~10 ADRs, ~10 sessions. Cheaper than ADR 14's ~50-100 sessions for 10 constraints.

## Superseded decisions

| ADR 14 Decision | New Status |
|-----------------|------------|
| Extraction produces 5-field `SymbolicConstraint` prose | Removed; no intermediate type |
| One agent session per constraint | Replaced by one session per ADR |
| Agent receives pre-extracted `SymbolicConstraint` | Replaced by agent reading full ADR text |
| 7-field extraction prompt with module list | Removed entirely |