# 17. Search-First Resolution Tools

Date: 2026-09-05

## Status

Accepted (supersedes the ADR 14/15 tool surface: `list_modules` and `dive`; retains ADR 15's one-session-per-ADR unified agent and ADR 14's provenance/trace approach)

## Context

Issue #121 problem 3: `cpt seed build` overflows the LLM context window on home-assistant (84,851 nodes / 345,097 edges, ~20K MODULE nodes). One `list_modules()` call serializes to ~400-500K tokens (half the 1M window); `dive()` is an unbounded bidirectional BFS whose result stays in the message history and is re-sent every turn. The observed request was 4.5M tokens. The system prompt *mandates* `list_modules` as the first call, so overflow is the required first move, not an edge case.

Root cause is not output size but interaction model: the tool contracts have unbounded fan-out, designed when graphs were O(hundreds) of nodes (ADR 14: "list_modules returns top-level module FQNs"). At O(tens of thousands), enumeration is both impossible (context) and useless (a flat 20K-row list is not navigable). The agent's actual job — mapping ADR prose ("passive update coordinator") to FQN patterns (`homeassistant.components.bluetooth.passive_update_coordinator`) — is a lookup, not a browse. External evidence supports the same conclusion: shift agent interaction from raw data to pointers (Labate et al. 2025, arXiv:2511.22729), and rank a few relevant results instead of stuffing many (retrieval-quality scaling).

## Decisions

### 1. Search is the entry point; semble is the recall backend

New `search_code(query)` tool backed by [semble](https://github.com/MinishLab/semble) (MinishLab; static Model2Vec `potion-code-16M-v2` embeddings + BM25 fused with RRF; local CPU, no API keys, deterministic). Flow: agent emits a prose query → semble retrieves source snippets (file_path, lines) from the repo → results are **lifted** to graph handles via `FQNNode.file_path` → bounded `{fqn, kind, file, snippet}` list (top_k=10, snippet ≤500 chars).

Semble is recall; the ADG remains truth. Constraint FQNs still terminate in graph nodes or are dropped by `_validate_edge` (unchanged). A semble hit that lifts to no ADG node (e.g., a file skipped by the parse-error policy) filters out naturally.

### 2. Typed directional neighborhood tools replace `dive`

`dive` is deleted. An unsorted N-hop blast radius answers no question precisely; a capped one is safe but low signal density. The agent gets one tool per question it actually asks:

| Tool | Answers | Shape |
|---|---|---|
| `list_children(fqn)` | what is inside? (wildcard-level choice) | CONTAINS down, capped + `truncated` flag |
| `list_dependencies(fqn)` | what does it use? (predicate choice) | IMPORTS+INHERITS out, hits labeled with edge kind |
| `list_dependents(fqn)` | who uses it? (subject scoping) | same edges reversed |

Every response is bounded by construction (direct neighborhood), with a cap + `truncated` flag for pathological hubs (truncation guidance: search within the prefix). CALLS edges remain excluded, matching `dive`'s traversal semantics; CALLS visibility is the named extension point. Implementation is strictly less code than `dive`'s BFS: `list_children`/`list_imports`/`list_inherits` already exist in `services/adg/adg_tools.py`; the new tools aggregate and reverse them.

### 3. `list_modules` is deleted

Its two jobs move where they always belonged: root packages (via existing `_root_segments()`) and external packages are baked into the system prompt. The "must call list_modules first" mandate is replaced by "FQNs must come from tool results or the root package list".

### 4. Dispatch-layer budget backstop

The tool-result choke point in `unified_resolver.py` enforces a serialized-length ceiling on every tool response, replacing oversized results with a truncated notice. This is the extensibility invariant: any future tool inherits the bound automatically; graph growth cannot reintroduce overflow.

### 5. Loud failure when the search backend is unavailable

If the semble model is not cached and cannot be downloaded, `seed build` fails with a clear message instead of degrading silently. This deliberately narrows ADR 14's "best-effort, never null" (which governs individual constraints) — an invisibly degraded retrieval backend across a whole eval run corrupts baselines. The cost is one network-dependent run per machine (HF caches the model afterwards).

### 6. Index once per seed, backend injected

`pipeline.build_seed` builds the semble index once and passes a search callable into `resolve_adr_constraints`. The seam doubles as the unit-test boundary (tests inject a stub; no abstract interface, no plugin registry).

### 7. Eval re-recorded in the same change; ablation noted

The resolver behavior change moves the 2026-09-01 ingestion baselines; the eval is re-run and `eval.md` re-recorded in the same change (gold set #117 is not yet curated, so nothing downstream pins the old numbers). The eval track notes an ablation dimension for the new surface (search on/off, `list_dependents` on/off) to be designed before the re-record.

## Consequences

- New dependency: `semble` (MIT, pure CPU). First run downloads the 16M-param embedding model from Hugging Face (cached thereafter). Docker-compatible; bake or volume-mount the HF cache for the `api` service if cold starts must avoid network.
- `resolve_adr_constraints` signature gains the search backend (and transitively `project_root`, already available in `build_seed`).
- System prompt rewritten: root/external packages replace `module_hint`; exploration examples become search → lift → inspect.
- Worst-case tool traffic per session ≈ 20 calls × ~4K tokens ≈ 80K tokens; the multi-million-token blowup is structurally impossible.
- `dive` and `list_modules` tests are replaced by tests for the new tools, lift, caps, and the backstop (TDD).
- Resolution traces (`resolver_traces.jsonl`) record the new tool calls unchanged in shape.
- Resolution quality on small repos (flask/django smoke, eval group) is expected to shift; the re-recorded baseline captures it.

## Superseded decisions

| ADR 14/15 Decision | New Status |
|---|---|
| `list_modules()` entry-point tool | Removed; root packages in system prompt |
| `dive` neighborhood exploration | Replaced by `list_children` / `list_dependencies` / `list_dependents` |
| Agent sees module list in prompt (`module_hint`) | Removed; replaced by root packages + external packages |
| Best-effort resolution, never null (backend scope) | Narrowed to per-constraint scope; backend failures are loud |
| `search_code` did not exist | New; semble-backed, the scale-entry-point |
