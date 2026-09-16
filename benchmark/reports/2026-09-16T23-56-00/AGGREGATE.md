# #154 detection-scorer convention: post-#146 node_on k=1 read

> Instrument read to decide the #154 moot clause (moot vs adopt), NOT the ADR-018 k=3
> re-baseline. The k=3 instrumented unoptimized re-run is the baseline of record and
> now carries the violation-level key. See eval.md row "issue #154 detection-scorer convention".

- **Protocol:** #149 registration otherwise unchanged; node_on only, k=1, 4 cells (~$0.35, ~12 min).
  Harness `app/tests/services/adg/test_benchmark_arms_eval.py` post-#154, model `google/gemini-3.1-flash-lite`,
  `PYTHONHASHSEED=0`. Pins as in #149 (tuf `6889cfbf`, flowkit `24d88247`, experimenter `d61a2b8e`,
  structurizr `31f1dcad`).
- **Traces:** `logs/benchmark-arms-154/<repo>-node_on-run1/resolver_traces.jsonl` (local, gitignored).

## What changed (harness-side only)

The detection scorer's comparison key. `_score_case_units` matches on
`(adr_id, predicate, matched_fqn exact/partial, object)` — **subject-pattern string equality dropped**.
Object: external = literal string equality, internal = expansion overlap against the pinned ADG.
Kept alongside: per-unit `pattern_score` (the old key) and per-case constraint-level expansion diagnostics
(`overlap`, `stale_gold_units`).

## Reading

| repo | violation e/p/m | pattern e/p/m | diag overlap | stale |
|---|---|---|---|---|
| python-tuf | 6/0/0 | 6/0/0 | 1064 | 0 |
| flowkit | 9/0/3 | 0/0/12 | 1721 | 0 |
| experimenter | 0/0/18 | 0/0/18 | 0 | 0 |
| structurizr-python | 4/0/2 | 0/0/6 | 60 | 0 |

**Decision: ADOPT, not moot.** The moot clause required Rule 3 to make the resolver emit gold-anchored
patterns, so the two keys would agree. Post-#146 the pattern column is still 0 on flowkit/structurizr,
so they do not agree and the switch is not eval-neutral.

- Movement matches the pilot's pre-registered counterfactual direction: flowkit 0→9/12, structurizr 0→4/6,
  tuf unchanged 6/6. **experimenter stays 0/18**, confirming the pilot split exactly: the subject-side
  13-unit family recovers (subject-pattern equality dropped), the object-side 17-unit family does not
  (external objects stay literal — object grounding is #146's scope, not a scorer tolerance).
- Over-breadth discipline holds: recovered units are exact fires at the gold FQN; flowkit's 45-FP mass
  (merge-mechanism + decoy residue) is unchanged and charged as before.
- `pattern_score` is the bridge column: it reproduces the pilot's pattern-equality reading on the same
  runs, so the movement is attributable to the key alone, not to #146's prompt.
