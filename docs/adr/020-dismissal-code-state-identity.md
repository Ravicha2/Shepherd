# 20. Dismissal Identity Carries the Code State It Judged

Date: 2026-10-03

## Status

Accepted (decided on issues #186 + #181 §8; supersedes [ADR 012](./012-violation-lifecycle.md) §2 (identity key) and §4's "code changes" cleanup rule. ADR 012's dismissals-only persistence model, flat Neo4j node and CLI surface are NOT superseded and stay live.)

## Context

ADR 012 keyed a dismissal to `(subject, predicate, object, matched_fqn, adr_id)` — a permanent judgement about a *location*. Nothing in the tuple captures the code state that made the violation a false positive, so once a reviewer dismisses, the dismissal wins forever: ~500 commits later the middleware can be removed, the route rewritten without auth, and the now-genuine violation at the same location is silently suppressed on every production path (`pipeline.run_with_dismissals`, `commit_update`, `cpt violation list`). ADR 012's own Risks section named this and deferred it.

Issue #181 settled the semantics for the fix (#186): a dismissal is tied to the governed module plus a fingerprint of that module's code — it must survive *unrelated* churn (graph rebuilds, renames, neighbours moving) and break on *material* change, so the violation re-surfaces for review. Granularity was #186's to choose.

## Decision

### 1. Identity key: (subject, predicate, object, adr_id, code_fingerprint)

`matched_fqn` drops out of identity: the evidence location moves for reasons unrelated to the governed code (issue #126 reporting, neighbour refactors), so keying on it breaks dismissals under unrelated churn. It is kept on the Dismissal node as provenance only, alongside `governed_fqn` (the module the rule is about: `changed_fqn` for prohibits, `matched_fqn` for requires — #181 §4).

### 2. The fingerprint hashes normalized content, so renames survive by construction

Every `FQNNode` carries `code_hash`: SHA-256 of the node's own source span, computed by the treesitter parser (whole file for modules, byte span for classes/functions) and persisted through Neo4j. The span is normalized before hashing, so only material change shows:

* **comment descendants are excised by AST byte range** — not by pattern matching, so a `#`-shaped *string literal* survives excision and edits to it are material;
* **the definition's own name is cut** — a pure rename (only the def line changes) keeps the hash at every anchor kind, including classes and functions, per #181 §8's "a rename never invalidates it by accident". A rename that also edits the body is renamed-and-edited; re-surfacing it matches #181 §6's lost-track censoring;
* **whitespace runs collapse** — blank lines, tab-vs-space indentation and line endings are not material.

A violation's `code_fingerprint` is SHA-256 over the ordered code hashes of its causal surface — governed module, reported anchor, and the prohibits evidence route (path hops). So:

* a rename or move of any node on the surface keeps the fingerprint — no git rename-tracking machinery;
* a material edit at the governed module or on the evidence route changes it — the dismissal stops applying and the violation re-surfaces;
* churn anywhere else in the repo leaves it untouched.

`scope_snapshots` are deliberately **not** in the fingerprint: they are reviewer context, and the enclosing module's edits are neighbour churn, which #181 §8 says must not invalidate a dismissal. Granularity choice: the full causal surface, not the governed module's own span alone — the reviewer's judgement rests on the whole route that produced the false positive, and a child module edited on the path is material change to what was judged.

### 3. No code state, no dismissal

`Dismissal.from_violation` refuses violations whose anchors have no code in the graph (missing or EXTERNAL placeholder): a dismissal without a recordable code state is exactly the permanent-suppression bug. `cpt violation dismiss` exits with an error; the violation stays visible.

### 4. Legacy rows never match

Dismissals recorded before this ADR carry no `code_fingerprint`; they cannot be checked against the code state, so they stop suppressing. Every violation they hid re-surfaces exactly once for re-review. Old nodes are inert until cleaned by the existing rules (seed rebuild, ADR deletion).

## Consequences

- Suppression is now sound: it can never hide a genuine, newly-introduced violation at a dismissed location — a material change re-surfaces it.
- Dismissals still survive graph rebuilds and unrelated churn (ADR 012's premise), now by matching on content instead of by ignoring content.
- `short_id`s change once at upgrade (the key composition changed); any in-flight dismissal workflow must re-list.
- Two violations with byte-identical causal code under the same constraint share a dismissal. Judging identical code identically is defensible, and the collision requires literally identical source spans.
- The longitudinal study (#178) can now observe re-introductions at dismissed locations: the dismissal no longer always wins (#186's measurement blocker).

## Risks

- **False invalidations are the failure mode, not false suppressions.** Chosen deliberately: the safe direction is the one that cannot hide a real violation. What still over-invalidates: edits that insert or remove space *between* tokens (some formatter diffs — whitespace runs collapse, but token separation does not), and any edit at the governed module's own code that is somehow irrelevant to the judgement.
- **Rename survival is for pure renames.** A rename that also edits the body (e.g. updating self-references) changes the hash and re-surfaces — the same treatment #181 §6 gives renamed-and-heavily-edited modules.
- **Whole-file granularity for module-anchored dismissals**: a MODULE-node anchor fingerprints the entire file's normalized content, so a token-level edit anywhere in the file invalidates. Class/function anchors are tighter.
- **Decorator-only edits escape the class span hash** (tree-sitter spans exclude decorators; the enclosing module node still covers them). Cosmetic edge, noted for completeness.