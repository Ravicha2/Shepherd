# 16. Retrieval Blind-Spot Disposition (B1–B4)

Date: 2026-08-31

## Status

Accepted (extends [ADR 009](./009-sound-cpt-reachability.md))

## Context

The retrieval eval gold (`tests/ground_truth/cpt_detect_ground_truth.json`, baselines in `eval.md`) surfaced four blind spots where CPT detection diverges from ADR semantics. A grilling session (#108, decision comment 5472616138) walked each one and decided: fix the detection semantics, or accept and document as a limitation. The disposition matters because fixing a blind spot changes what the expanded gold set (#107) can claim to detect; documenting it bakes the blind spot into future GT as a known miss.

The four blind spots:

1. **B1**: `prohibits` never fired for django `users.views.*` because the subject pattern didn't match the module itself.
2. **B2**: function-level subjects couldn't see module-level imports, so `requires` over-triggered on any function whose module already satisfied the dependency.
3. **B3**: attribute-chained calls (`User.objects.create(...)`) resolved to no CALLS edge at all, so any dependency expressed through an ORM/fluent call was invisible to reachability.
4. **B4**: `merge_preserved_constraints` and `merge_constraint_edges` created EXTERNAL nodes from raw wildcard pattern strings (e.g. `users.views.*`), inflating node counts.

## Decisions

### 1. B4 — fixed trivially (#114)

Strip the trailing `.*` from wildcard patterns before EXTERNAL node creation. Harmless for detection; fixes node-count inflation (retrieval eval prints `adg_nodes`/`external_nodes` per repo as the regression signal).

### 2. B1 + B2 — fixed together (#115)

Same root cause: function/method scopes had no visibility of their enclosing module's edges. One fix: when BFS starts from a function/method FQN, seed the frontier with the enclosing module's module-level edges (`_enclosing_module_map` + `seed_module` in `services/cpt/engine.py`).

- The seed excludes CONTAINS and the module's own subtree, so a package `__init__` importing its child does not upstage the child's violation.
- Structural function subjects report at the enclosing module (module-level dedup).
- Kills a false-negative class (B1 `prohibits`) and a false-positive class (B2 `requires` over-trigger) at once.

**Accepted tradeoff:** decorator application is syntactically indistinguishable from a module-level import of the decorator function. Flask auth.py's module-level `require_auth` import satisfies the function-scope `requires` even when the decorator is not applied; the affected endpoints stay unauthenticated per ADR-002. Recorded as expected-but-missed in the gold; mechanically identical to the tuf/openlobby cases the fix was for, so it cannot be separated without decorator application tracking (future work).

### 3. B3 — fixed via root resolution (#116)

For a chained call `X.y.z(...)`, when full callee resolution fails, resolve only the leftmost name `X` and add a CALLS edge from the caller to `X`'s FQN (`_leftmost_name` + fallback in `walk_calls`, `services/adg/treesitter.py`).

Rationale: constraints are FQN-pattern rules between namespaces (`users.views.*` PROHIBITS `users.models.*`); they care that a view depends on `User` at all, not which method was called. Full descriptor-chain resolution (`Model.objects` → manager → `.create`) is type inference, out of scope for tree-sitter.

Guardrails:

1. Skip resolution when `X` is rebound anywhere in the enclosing function's text (regex `\bX\s*=(?!=)`, so `==` comparisons don't false-positive the shadowing check).
2. Skip `self` / `cls` roots; non-name roots (`super()`, subscripts, literals) produce no edge.
3. Unresolvable roots (parameters, locals) produce no edge — status quo, no regression.

### 4. Acceptance gate: eval FP tallies vs baseline

The B3 approximation's accepted risk is syntactic overmatch (a shadowing case the textual check misses would draw a spurious edge). The gate: retrieval eval false-positive tallies vs the recorded baseline in `eval.md`. FP jump ⇒ approximation rejected, B3 reverts to documented limitation.

**Gate outcome (2026-08-31):** flask 1 FP (unchanged), python-tuf 0, openlobby 3 (unchanged), django 0 → 3. Adjudicated as **not a regression**: the 3 FPs are one firing repeated across three cases (ADR-002 `project.*` prohibits `users.models.*` at `project.urls`), caused by a factually correct new edge completing a transitive path the pre-#116 graph could not express. Even full descriptor-chain resolution would produce the same edge and the same firing. Kept, with the firing recorded as a documented over-trigger in the gold grading notes and the `eval.md` baseline.

## Documented limitations (stay)

- **Method-level precision on chained calls:** `User.objects.create` and `User.objects.filter` produce identical CALLS edges; a constraint distinguishing create from filter is inexpressible. Needs descriptor-chain inference; future work.
- **Wildcard-subject `prohibits` fires on transitive paths:** ADR-002 fires at `project.urls` because `urls.py` imports view functions that call the model, even though the ADR governs direct imports. The over-match is traversal semantics meeting an over-broad subject, the same class as the openlobby elasticsearch/django.db FPs already tolerated in the baseline. Candidate future work: constrain prohibits traversal to direct edges, or narrow constraint subjects at ingestion.
- **Over-broad constraint subjects** (openlobby elasticsearch, django.db) over-trigger on `requires`; documented in gold grading notes rather than treated as detection bugs.

## Consequences

- django `django-violating-view` and `django-compliant-view-via-connector` stay in the gated retrieval set — no denominator exclusion needed, since B3 is fixed rather than documented.
- Retrieval baselines pre-#115, post-#115, and post-#116 are recorded in `eval.md`; the post-#116 django row carries 3 documented FPs, so future changes must not be confused by the jump from the post-#115 row.
- The eval remains report-only: accuracy is printed and written, never gated; thresholds are deferred to the #107 expanded gold set.