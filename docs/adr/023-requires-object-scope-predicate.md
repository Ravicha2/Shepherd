# 23. The Object-Scope Predicate `requires_object_scope`, Superseding the Presence Rule for Authorization

Date: 2026-10-30

## Status

Accepted — supersedes [ADR 004](./004-predicate-ontology-expansion.md) for the authorization
clause. The #240 A6 ingestion PoC passed its detect-side gate on the amended check with owner
sign-off (Shepherd#250): fires 6/6 on the gold class-(ii) handlers; clears 5/6 under the #266
paired-handler amendment, tandoor the one honest red. Standing record:
`research-exp-setup/security/records/a6_gate_267/` (merge `fc81a82`); write-up:
[`docs/research/issue-259-gate-write-up.md`](../research/issue-259-gate-write-up.md).

## Context

The A2/A4/A5 arms flatlined on class (ii) (Shepherd#240): `requires_dependency` is a presence
rule over import edges, so a guard that exists but does not scope the object the route loads to
the requester is invisible, and detection fires identically at the vulnerable and fixing
commits. The memory could not express the evasion class at all.

The PoC (#244) set out to prove two things at a detect-side gate before any reader session or
schema promotion was funded: that the graph can represent the class, and that the real lowering
pipeline emits the predicate from prose (k≥2, no hand-written rows). Both held: the predicate
fired on every gold handler for all six class-(ii) cases, from lowered rows, with the seven
registered checks reported on all 18 pinned cases (0 model calls). The one registered criterion
not met was `clears` 6/6: under the amended paired-handler contrast it is 5/6, with tandoor red
because its fixing diff scopes ownership through an `or` with a requester-less disjunct
(`Q(private=False) | …`), which the #258 soundness stance rejects by design, and its fire is
sibling-carried and unattributed (amendment arm 4). The amendment trail is dated and on record
(#255 critique before the FAIL, #252 target amendment before the run, #266 check amendment,
#267 standing record); the frozen #259 FAIL record stands untouched.

## Decision

1. **Final predicate name: `requires_object_scope`.** It names the constraint, not a
   mechanism, and reads correctly in the ontology sentence: the subject handler requires the
   object it loads to be scoped to the requester. The working name becomes the final name;
   every frozen artifact already cites it (the #248/#249/#255 lowering corpora, three gate
   records, the tests), and a rename would break that byte-comparability for no gain.

2. **Place in the ontology: a named member outside ADR 004's 2×2.** The 2×2
   (prohibits/requires × dependency/implementation) governs module-level constraints over
   import and definition structure. `requires_object_scope` is a different kind: a scoping
   predicate over a triple (subject handler, object, requester). It subsumes presence for this
   clause — a handler with no guards at all also fails — so it replaces, not extends, the
   presence arm for authorization.

3. **Replacement, not side-by-side.** The v2 lowering emits `requires_object_scope` instead of
   `requires_dependency` for the authorization clause. The gate checks this directly: zero
   presence rows in the v2 lowering output (replacement PASS, all cases).

4. **Extraction-prompt contract.** The predicate's definition for the extraction prompt: a
   route handler that loads an object from its route must scope that object to the requester
   through the project's authorization mechanism. Subjects are handler-namespace FQN patterns
   (wildcards allowed at namespace level, per ADR 004's scoping rules); objects are the
   authorization module or service FQN; the subject filter joins to route handlers that carry
   object facts. Absence of guards also violates.

5. **Guard facts stay node attributes** per [ADR 022](./022-guard-facts-as-node-attributes.md);
   its promotion contract is unchanged. The predicate's evaluator reads the fields directly
   (no BFS); route paths for reporting come from the derived route inventory
   ([ADR 021](./021-route-inventory-derived-view.md)).

6. **The 2×2 remains for the four frozen predicates.** A1–A5 comparability is intact: the gate
   asserted frozen comparability on all 18 cases, detect outputs byte-identical.

## Limitations

Levers were derived from three traced misses, so the six-case development subset is not blind;
confirmatory weight rests on the frozen full-18 run. The detect-side gate clears 5/6: tandoor's
fix scopes ownership through an `or` with a requester-less disjunct, which the soundness
stance rejects by design, so the case stays red as an honest detection limit. Detect-side
evidence is a precondition for reader recall, not a measurement of it.

## Consequences

- The memory can express and detect the class the A2–A5 arms were blind to, with precision by
  construction: candidate files ran 1–2 orders below the presence rule on all six class-(ii)
  cases (3<329, 11<31, 17<195, 8<201, 1<3, 1<213).
- Reader-side recall (the #252 amended target, 14/18 total) is Stage 1's to measure; this ADR
  funds that aggregation. Every A6 reader session runs sandboxed per #239 with a valid session
  record.
- Weakening the `or` rule to clear tandoor is deliberately not taken; the case is recorded as
  a conservative-rejection limitation, with the fix visible and the fire unattributed.
- A guard-centric query need remains the promotion trigger for guard structure (ADR 022);
  nothing in this ADR reopens that.