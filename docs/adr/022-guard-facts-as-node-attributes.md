# 22. Guard Facts as Node Attributes, Not Graph Structure

Date: 2026-10-28

## Status

Accepted — representation choice for the #240 A6 ingestion PoC (predicate + per-handler facts).
The ontology supersede of [ADR 004](./004-predicate-ontology-expansion.md) lands only if the
PoC passes its detect-side gate; this ADR records the *placement* decision, which holds either way.

Landed 2026-10-30: the gate passed on the amended check with owner sign-off (Shepherd#250), and
[ADR 023](./023-requires-object-scope-predicate.md) supersedes ADR 004 for the authorization
clause. The predicate's final name is `requires_object_scope`; the placement decided here is
unchanged.

## Context

The A6 diagnosis (Shepherd#240) is that `requires_dependency` is a presence rule over import
edges and cannot express the evasion class (class (ii)): a guard exists but does not scope the
object the route loads to the requester. The structural fix adds a predicate — working name
`requires_object_scope`, to be settled in the ontology ADR — and per-handler facts: the object
parameter(s) the handler loads from its routes, and its guards (symbol, predicate text, whether
the predicate mentions the object — the dead-guard and bypass checks from the object-scope rule
family). Two placements were considered:

**(A) Node attributes** — two optional fields on `FQNNode`, populated by the treesitter
ingestion (the extractor ported from `research-exp-setup/security/scope_pregate.py`, which
already computes these facts deterministically).

**(B) Graph structure** — a `GUARDS` edge kind plus synthetic guard-symbol nodes.

B's blast radius was measured with ripwire on 2026-10-28 (`Edge` resolves at ≥299 static sites,
`FQNKind` at ≥283 — the breaks concentrate in the round-trip and mapping dicts):

- `connector.py::store_node` `KIND_TO_LABEL[node.kind]` and `store_edge`
  `EDGE_KIND_TO_REL[edge.kind]` raise KeyError on any new kind — every guard store crashes.
- `store_edge` MATCHes both endpoints and silently drops the edge when the target node is not
  stored, so `GUARDS` edges *cannot exist* without guard nodes: the node-kind change is not
  optional under B.
- `load_adg` reconstructs `Edge(source, target, kind)` — the triple only. The guard's
  load-bearing content (predicate text, scoped flag) has no home without extending the `Edge`
  dataclass, which shifts frozen equality, merge dedup keys and store round-trip assertions.
- `match_constraints` iterates every FQN against every constraint's subject/object patterns;
  synthetic guard pseudo-FQNs (`request.user` as a dotted name) enter those buckets and
  contaminate matching across the whole graph — silently.
- Guard nodes inflate `adg_nodes`/`external_nodes`, the regression signal ADR 016 (B4) put in
  place — every recorded baseline resets. B4 was exactly this class of mistake and had to be
  unwound.
- The content work (extractor, predicate, evaluator, lowering) is identical under both options.
  B adds ~2–3× total workload (~10–13 days vs ~4–5), paid before any PoC signal — contradicting
  the agreed gating that the graph integration follows a clear detect-side signal.

## Decision

**A.** Guard facts are optional fields on `FQNNode` (object parameters + guards), populated at
treesitter ingestion. CPT traversal is untouched: nothing existing reads node fields, the new
predicate gets its own small evaluator (no BFS — it reads the fields directly), and route paths
for reporting still come from the derived route inventory ([ADR 021](./021-route-inventory-derived-view.md)
is unchanged). Neo4j persistence is additive (`SET` clause + `props.get` in the load); node
counts stay comparable with frozen baselines; `commit_update` deletes and restores the fields
with the handler node for free.

This is a property-graph modeling choice, not a side-channel: the facts are persisted on the
node and round-trip through the store. What A does *not* give is traversal into guards.

**Promotion contract (the circle-back path):** guard facts promote to traversable structure —
a `GUARDS` edge kind and guard nodes — when a guard-centric *query* need exists (e.g.
`node_search` traversal into guards, cross-handler guard-sharing analysis). Same ladder as
ADR 021's route promotion: the record schema here is the migration contract. The trigger is a
real query consumer, never eval convenience.

## Consequences

- The PoC and the reader rendering get identical capability under A; B's only marginal gain is
  guard-centric traversal, which nothing in the current experiment consumes.
- Guard-centric questions ("which handlers share this guard") are property scans until
  promotion — O(handlers), fine at 18-case scale.
- Sibling asymmetry (comparing guard predicates across handlers) reads the same fields and
  needs no traversal.

## Risks

- **Property-model ceiling.** If a future predicate needs guards as joinable structure, that is
  the promotion trigger — not a re-litigation of this decision.
- The extractor populates fields only for handlers it can resolve; non-route handlers carry
  defaults and never match the new predicate's subject filter.