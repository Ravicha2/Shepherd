# #158 batch: LLM per-edge scope triage, k=2 node_on, post-#157 + post-#159

Baseline of record for movement: `benchmark/reports/2026-09-16T23-56-00/` (post-#146, node_on, k=1).
Protocol: #149 registration otherwise unchanged (4 repos x node_on x k=2 = 8 cells, traces
`logs/benchmark-arms-158/`), worst run per ADR 018 where a single number is needed.
Ground truth: `benchmark/scope_labels.json` (47/47 labeled: 18 none, 18 tooling, 11 runtime).

Readers in this dir: `_movement.md` (axis 1, FP/detection vs baseline), `_triage.md`
(axis 2, pooled), `_triage_run1.md` / `_triage_run2.md` (per-k), `_tables.md` (raw aggregate).

## Axis 1: FP movement (worst run) with the zero-gold / has-gold split

| repo | base FP (zero/has) | new r1 | new r2 | worst (zero/has) | excl. tooling edges | detection violation e/p/m |
|---|---|---|---|---|---|---|
| python-tuf | 4 (3/1) | 1 (1/0) | 4 (4/0) | 4 (4/0) | 0 | 6/0/0 (base 6/0/0) |
| flowkit | 45 (43/2) | 14 (12/2) | 15 (12/3) | **15 (12/3)** | 32 / 40 | r1 6/0/6, r2 9/0/3 (base 9/0/3) |
| experimenter | 10 (8/2) | 14 (12/2) | 13 (12/1) | **14 (12/2)** | 1 / 0 | 1/0/17 (base 0/0/18) |
| structurizr-python | 7 (7/0) | 0 (0/0) | 0 (0/0) | **0 (0/0)** | 13 / 13 | 4/0/2 (base 4/0/2) |
| **total** | **66 (61/5)** | | | **33 (28/5)** | | **17/0/25** (base 19/0/23) |

Worst run is per-metric, not per-cell: flowkit's worst FP is r2 (15) while its worst
detection is r1 (6/0/6, r2 recovers the same units at 9/0/3), so the detection total is
19 -> 17 exact on run variance, not on any scope change (same ADRs, same predicates).

92% of the baseline mass was zero-gold ADRs (61/66); the movement is zero-gold mass leaving
accounting by scope tag, exactly as #136's `excluded_tooling_edges` seam is built to record.

Detection fires: the two named families both fall, `flowkit ADR-0010 airflow 117 -> 0` and
`flowkit ADR-0012 Scope 65 -> 0`, but NOT by the scope filter (those edges are `runtime`-tagged
in these runs): their subject/predicate drifted (`flowetl.*` -> `flowmachine.*`,
`prohibits_implementation` -> `requires_implementation`), so they no longer match any case FQN.
The fires #159 actually kills are visible elsewhere: `structurizr ADR-0004 versioneer 6 -> 0`
(tooling-tagged, previously runtime). New fire families: `experimenter ADR-0002 react /
react-bootstrap 0 -> 44` each, `tuf ADR-0004 securesystemslib 0 -> 98`, `tuf ADR-0008
prohibits_implementation Signed 0 -> 12`.

## Axis 2: triage accuracy vs the labels

Pooled over both runs (182 edges): `runtime->runtime 26, runtime->tooling 1, tooling->tooling
102, tooling->runtime 34, none->runtime 19`. **Zero `none` verdicts were emitted in any cell**,
so `none`-precision is undefined (nothing predicted) and 19 edges on `none`-labeled ADRs stay
charged as runtime FPs. `tooling`-recall 102/136 = 0.750 pooled; 47/64 = 0.734 (r1) and
55/72 = 0.764 (r2), so the worst run is 0.734.

Recall-safety: **no runtime edge on any has-gold ADR was dropped or tagged `none`**. Two has-gold
ADRs emitted nothing at all (`python-tuf ADR-0006`, `structurizr-python ADR-0008`); `_triage.md`
reports both under its recall-safety block, but that block cannot see prior runs — each was
verified against the post-#146 baseline and is already missing there, so neither is a scope loss.
One demotion is the legitimate mixed-ADR aside (`experimenter ADR-0010` `prohibits typescript` ->
tooling, next to its runtime gold row).
The experimenter ADR-0008 trap passes in all four run-ADRs (verdicts all `runtime`, nothing dropped).

## Legacy eval set (openlobby / tuf / tamr), k=2, both runs identical

| repo | committed baseline | new | movement |
|---|---|---|---|
| openlobby | 3/6/1, FP 5 | 3/6/1, FP 8 | FP +3, same gold tallies |
| python-tuf | 3/0/1, FP 4 | 3/0/1, FP 4 | none |
| tamr-client | 0/1/0, FP 2 | 0/1/0, FP 2 | none |
| flask / django (smoke) | 1/1/2 FP 0 / 3/0/1 FP 1 | identical | none |

Blended 0.6333 unchanged. The triage reproduces the regex's three legacy tooling tags
(openlobby ADR-0005 `javascript`, ADR-0008 `pytest`/`unittest`) and adds openlobby ADR-0013
`black` (correct). The +3 openlobby FPs are prompt-side class-A edges, all `runtime`-tagged and
unrelated to scope: ADR-0002 `django_elasticsearch_dsl`, ADR-0004 `graphene_django.views` and
`graphql_relay` — the Rule-1 family #146 cleared, back in both runs. Real-repo FP sum 11 -> 14,
which would trip the ADR 018 ratchet (`INGESTION_MAX_FP = 11`) if this run were re-baselined.
No re-baseline is made here.

## Verdict: KEEP the LLM triage

FP 66 -> 33 worst-run with zero gold loss, zero dropped edges, the trap passing, and the legacy
tooling tags reproduced; reverting to the regex restores flowkit 45 and structurizr 7. Conditions
recorded rather than paid away: the `none` arm is inert (19 residual FPs it was meant to remove),
`tooling`-recall 0.73 leaves ~26% of tooling edges charged, experimenter FP regressed 10 -> 14,
and the legacy class-A FP regression is prompt-side and needs its own fix.
