# Decision log — plan §5 dated notes (issue #207)

The grill session of 2026-10-10 that produced the two dated notes in
[`longitudinal-analysis-plan.md`](./longitudinal-analysis-plan.md) §5
(Test 1 close-out, Test 2 redesign). Every number cited was verified against
the committed event table `research-exp-setup/records/events/flowkit.json`;
the statistical practice was checked against the permutation-inference
literature (Permutation Inference in Factorial Survival Designs, Biometrics
2021, arXiv 2004.10818).

## Decisions

| # | Question | Answer | Status |
|---|---|---|---|
| 1 | Does Test 1 stop being a test? | **No.** The error-only simulation is retired (degenerate by arithmetic: off-panel eval-gate rates make its floor ~100% for *any* repo — 37% miss → 14% per sample-pair for two-sample misses that survive the 2N rule). The floor is **measured per repo from its own records**: blip rate now, adjudicated fake-fix/FP fractions once #196 runs. Holm across the pair unchanged. Flowkit's numbers are labelled pilot evidence for the retirement only — never generalized (the issue originally bundled both; the generalization was caught and rejected). | agreed |
| 2 | Does the Test 2 redesign bind HA before HA's records exist? | **Conditional, not rewritten.** Per repo, by its own records: matched never-violated design where the pool exists; fallback where it's empty. Flowkit → fallback (pool empty, measured) *and* not-run (n=1) — two separate facts. | agreed |
| 3 | What is the fallback comparison? | **Permutation test over the fixed violations alone.** The issue's "fixed vs persistent" arms were retired as degenerate: a persistent violation fires at every sample *by definition*, so any firing-rate baseline is 100% with zero variance; the pre/post self-control has the same flaw mirrored. Persistent violations become a reported context count (the ceiling). | agreed |
| 4 | Permutation mechanics | Cut the clean window out of each module's own sample string, glue the ends (busyness literally held fixed), re-insert only where **at least the observed follow-up length** remains (equalized follow-up — a placement near the end can't vote "no recurrence" for a cheap reason; same logic as censoring). One draw = one re-insertion per fixed violation + one pooled come-back rate; **10,000 draws or all distinct placements if fewer** (reported). Pure arithmetic over saved records. | agreed |
| 5 | Flowkit not-run: one-off or rule? | **Pre-named gate: below 10 certified lapses → not-run**, one template line with counts. At ≥10, run; the three plan outcomes (differ / equivalent / indeterminate) apply. Not-run ≠ indeterminate: the first is "can't attempt credibly," the second is "ran, interval too wide." Flowkit safely pre-declared because **certification only shrinks counts, never grows them** (1 genuine raw lapse → certified ≤ 1). | agreed |
| 6 | "Within matching distance," numerically | Within **half the typical spread (0.5 SD)** on each of fan-in, churn, age, same rule; nearest 1:1. Unmatched treated modules dropped and counted like censored watches. Original design runs when the matched subset is **nonempty**; fallback only when **empty**. (The word "caliper" was rejected as jargon.) | agreed |
| 7 | Note's numbers re-checkable? | Verified against the committed table: 6 blips ✓; 1,935 = 1,679 fixes + 225 rule-changed + 31 lost-track ✓; 449/1,935 = 23.2% ✓; 1 genuine lapse after the sample-21 artifact exclusion (the sample-41 `flowmachine.core.query.Query.query_id` comeback) ✓. The note cites the table + `events.py`; the denominator's composition is stated in the note. | agreed, verified |
| 8 | Cross-reference mechanics | **Pointers only** — the plan is the source of truth; #197's superseded Test-1/Test-2 bullet replaced with a pointer line, #185 got a References section. No design content duplicated across tickets. | agreed |

## Open Items

- **Pool-emptiness is not a saved number.** "No governed module of usable size
  never fires" is not in the committed event table — it must be computed and
  committed like the rest (extend `events.py`), or the Test 2 note justifies
  itself with an un-checkable claim. The note already promises it "saved as a
  checkable number."
- **HA (#194) and experimenter replays haven't run.** Their pool checks,
  measured floors, and not-run gates are decided — their *numbers* aren't.
  Everything is now mechanical: run records → count matches → count lapses →
  design and runnability fall out.
- **Uncommitted work.** Plan notes + CONTEXT.md noise-floor entry live in the
  working tree.
- #207 resolved in body; close after review.

## Risk Register

- **Permutation validity** (Biometrics 2021, arXiv 2004.10818): permutation
  tests in time-to-event settings are exact only under a restricted null —
  exchangeability requires comparable baseline/censoring across what's
  shuffled. Our scheme conditions on each module's own composition and
  equalizes follow-up, which addresses the main channels, but at small n the
  band is coarse and "indeterminate" is the likely honest verdict — covered by
  the pre-named outcome 3.
- **Sample-21 artifact:** the raw records carried a bulk artifact (144 fake
  "lapses" in one sample). De-contamination rules must live in the saved
  analysis, not be handled ad-hoc per repo — if HA's run produces a similar
  artifact and it is handled differently, the cross-repo comparison corrupts.
- **0.5 SD match window is conventional, not derived.** If HA's pool exists
  but matches poorly, the original design degenerates toward a small matched
  subset in practice — accepted, drops counted, no silent fallback.
- **The 10-lapse gate and 0.5 SD window are pre-named numbers chosen without
  pilot data for them.** Both were argued, not measured. If either proves
  wrong, that is a *new* dated note, not an edit to this one.

## Assumptions

- The simulation's retirement rests on the eval-gate rates being roughly
  right — the degeneracy conclusion doesn't hinge on the exact number (any
  miss rate near this magnitude degenerates), but a wildly better recall would
  change the arithmetic.
- `events.py`'s disappearance classes and the hand-checks documented in
  `records/events/README.md` are correct.
- Fan-in, churn and age were recorded for every violation (#182) so the match
  window is computable on both arms.
- The panel stays three repos; the python-tuf add-back clause is untouched.
- Certification can only shrink event counts — the linchpin of flowkit's
  pre-declared not-run.