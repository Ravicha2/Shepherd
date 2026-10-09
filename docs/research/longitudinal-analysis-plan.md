# Longitudinal analysis plan — issue #184

**What this is.** The plan for turning the longitudinal replay (map
[#178](https://github.com/Ravicha2/Shepherd/issues/178)) into numbers and claims.
It is written **before** the replay runs and then frozen: after the run starts,
nothing here changes silently. If a change is ever truly needed, it gets a dated
note saying what changed and why.

It is written in plain language on purpose. Every statistical word is explained
the first time it appears. The study's vocabulary (governed module, fix, lapse,
certified, blip, fake fix) lives in [`CONTEXT.md`](../../CONTEXT.md).

---

## 1. The question

Shepherd's pitch is memory: it can say *"this spot was fixed before, and it has
broken again."* A tool without memory can never say that sentence — it sees
today's violation, not the history behind it.

This study asks whether that sentence is ever worth saying:

- After a violation is fixed, does it come back? How often?
- Once fixed, how long does the fix hold?

If come-backs are rare, the memory layer has little to do — that is a finding.
If they are common, the memory layer's reason to exist is confirmed — also a
finding. Either way, the study sizes the **phenomenon**.

**What this study does not ask:** whether Shepherd detects well. That is the
benchmark's job (prior work, reported alongside). Mixing the two would be a
category error: this study is about the world (do real projects' rules get
re-broken?), not about the tool.

The object of study has a name — **compliance durability** — chosen deliberately.
The histories contain no enforcing mechanism and the replay cannot observe
intent, so we do not say "decision regression," "re-introduction," "robustness,"
or "enforcement." A governed module was clean, and then it wasn't. That is all
we can honestly claim to see.

## 2. A worked example

Rule R says: *modules under `homeassistant.components.*` must not import
`requests`.*

At every sampled commit we check every module under that subject:

- Module `foo` imports `requests` at sample 12 → **violation**.
- At sample 13 it has stopped → a **fix** (we never assume anyone *meant* to fix it).
- At sample 20 it imports `requests` again → a **lapse** (a come-back) — but only
  if the reviewer agent **certifies** it true from the code, since the detector
  is known to make mistakes.
- If the module gets renamed and we cannot find where it went → the watch is
  **censored**: we stop following it and we count that we did.

Everything below is this example, repeated over three repositories and hundreds
of samples.

## 3. What one row is

**One row = one module × one rule.** The clock starts at the module's *first*
certified fix and runs until:

| how the watch ends | what we call it |
|---|---|
| the violation comes back | **lapse** (the event) |
| the history ends | censored (normal) |
| the rule is withdrawn (HA's single amendment) | censored, counted |
| the module is renamed away / lost track of | censored, counted |

One row per module-rule, not one row per fix episode. A module that is fixed,
lapses, is fixed again, and lapses again still contributes one row — its first
fix and its first come-back. (Counting every episode separately would look like
more data but the rows would be correlated — same module, same rule — and with
small counts that correlation cannot be corrected for. Episode-level numbers are
reported as a secondary readout only if the counts turn out large.)

**Time is measured in commits** (settled in #182), with calendar days saved
alongside for comparison with other studies.

## 4. The two measurements, per repository

1. **Of the governed modules that were fixed, how many lapsed?**
   Reported as a count over a denominator (e.g. `2/6`), never as a bare
   percentage.
2. **How long did the fixes hold?**
   The survival picture — for each fix, how long until the come-back, or until
   the watch was censored.

The survival picture is drawn with the standard method for time-to-event data
(**Kaplan–Meier**), the same family the Exclusion Ratchet used. Censored watches
stay in the picture until the day they leave; that is what censoring means.

**What we report from the curve — deliberately not the median.** If most fixes
never come back (the good case!) the curve never drops below 50%, and the median
time-to-come-back does not exist. So instead, per repository:

- **Retention at a common horizon**: "of the fixes, X% were still holding after
  1,000 commits" — the same ruler for every repo.
- **Retention at the end of the window**: how many held to the end of that repo's
  observed history (windows differ; stated).
- **Average clean-time**: the average time a fix held, up to the end of the
  window (the "restricted mean" — always computable, unlike the median).
- The same retention number expressed in **days at ~3 years**, so the Exclusion
  Ratchet's "86.7% still in force at three years" has a direct comparison point —
  as a *shape* comparison only: their object is a human decision persisting,
  ours is a code state persisting. Different things; we say so.

## 5. The two tests — the only two

Everything else in the study is reported as plain numbers with ranges, no
significance language. Only these two claims are tested, because only these two
can be wrong in ways a test catches:

**Test 1 — "Are the come-backs real?" (vs the noise floor).**
The detector has known error (recall 0.63, ~10–11 false positives per run). A
missed detection at one sample looks exactly like a fix, and its reappearance
looks exactly like a come-back — one miss fakes a whole event. So #180's
simulation asks: *with no real come-backs at all, what come-back rate could pure
detector error produce?* That is the noise floor, and it is printed next to
every headline number. The claim "recurrence is above the floor" means: what we
see is more than the instrument could invent.

> **Dated note (2026-10-10) — the noise floor is measured, never simulated.**
> The error-only simulation named above is retired. It is fed by the eval
> gate's error rates, which are measured on repos outside this panel: with a
> ~37% miss rate, a violation present at every sample is missed for two
> samples — surviving the two-sample rule — about 14% of the time per pair of
> samples, so over hundreds of samples the simulation says pure error could
> fake a come-back for essentially every fix. A floor near 100% sits above
> every possible observation and can bound nothing, on any repo: it is
> degenerate by arithmetic, before any panel repo runs.
>
> Test 1 remains a test, per repository, against a floor measured on that
> repo's own records: its **blip rate** (present→absent transitions that
> return one sample later — the channel the two-sample rule exists to kill),
> joined by the fake-fix and false-positive fractions from the error table
> once adjudication (#196) runs. The flowkit pilot, raw records,
> pre-adjudication (`research-exp-setup/records/events/flowkit.json`): 6
> blips across 1,935 present→absent transitions (1,679 fixes, 225
> rule-withdrawals, 31 lost-track) — 0.31% — while 23.2% of absences return
> at all, median gap 87 samples. Nothing is generalised from the pilot: each
> repo's floor cell holds its own measured numbers, and the Holm correction
> across the pair is unchanged.

**Test 2 — "Do fixed modules lapse more than similar never-broken ones?"
(the matched comparison).**
Maybe `foo` came back not because fixes are fragile but because `foo` is simply
a busy, central module that breaks rules all the time. So for each treated
module (fixed once), take a **control**: a module under the *same rule* that
never violated, matched on fan-in (how many modules import it), churn (how often
it is edited) and age — the three things #182 records for every violation. The
control must be governed: a module outside the rule's subject can never violate,
so it would hand us a fake contrast. If treated modules come back much more
than matched controls break in the first place, the spot's history genuinely
predicts its future. If both behave the same, come-backs are just background
churn and the durability number measures busyness — that would withdraw the DV.

> **Dated note (2026-10-10) — Test 2 is conditional, and its fallback is a
> permutation test over the fixed modules alone.**
> The design above assumes a pool of never-violated governed modules to use
> as controls. Flowkit's records show that pool is empty there: no governed
> module of usable size under the fired rules never fires (derived from the
> replay records and saved as a checkable number like the rest). Rather than
> rewrite the design for the whole panel on one repo's evidence, the test is
> conditional, decided per repo by that repo's own records:
>
> - A never-violated governed module counts as a **control** for a treated
>   module if its fan-in, churn and age each fall within **half the typical
>   spread** (half the standard deviation) of the treated modules' values on
>   that measure, and it sits under the same rule. Treated modules with no
>   such control are dropped and counted, shown like censored watches.
> - If at least one treated module has a control, the frozen matched design
>   runs on the matched subset. If none do — flowkit's case — the repo runs
>   the **fallback**: a permutation test over the fixed violations alone.
>   (A "fixed vs persistent" comparison was considered and retired: a
>   persistent violation fires at every sample by definition, so any firing
>   number for it is 100% with no variance, and a fixed violation's pre-fix
>   firing rate has the same flaw in mirror image — there is nothing to
>   compare against. Persistent violations are reported as a count, the
>   ceiling, not as an arm.)
> - **The fallback's machine:** for each fixed violation, take its own
>   sample string (fires/cleans), cut out the clean window — the fix — and
>   glue the ends together, so the module's busyness is untouched (same
>   firing samples, same clean samples). Re-insert the window at a random
>   spot, chosen only among spots that leave at least as much history after
>   it as the real fix had: follow-up length is equalised, so a placement
>   near the end cannot vote "no recurrence" for a cheap reason — the same
>   logic as censoring. Read whether a firing follows within the equalised
>   follow-up. One draw = one re-insertion per fixed violation plus one
>   pooled come-back rate; 10,000 draws (or all distinct placements, if
>   fewer — reported) give the band, built from the modules' own dynamics.
>   Observed come-backs inside the band → the fix's timing carries no
>   information; recurrence is busyness (outcome 2). Below the band → the
>   aftermaths of real fixes are cleaner than the modules' own histories
>   predict; fixes hold (outcome 1) — "held" meaning cleaner than own
>   dynamics, still no claim about intent.
> - **Runnability:** a repo's Test 2, in either design, is **not run** when
>   its certified lapse count is below 10; the fixed template then shows one
>   line with the counts. Certification can only shrink counts, never grow
>   them, so flowkit (1 genuine raw lapse after de-contamination: ADR-0003,
>   `flowmachine.core.query.Query.query_id`, fixed sample 38, back at
>   sample 41) is safely pre-declared not-run. The Holm correction across
>   the pair is unchanged; the HR 0.67–1.5 margin applies where the matched
>   design runs, and where the fallback runs the permutation band plays the
>   equivalence role.
> - **What is lost, and where:** where the pool is empty, the
>   history-predicts-future contrast — do spots that broke rules differ
>   from matched spots that never did, the deterrence-shaped question — is
>   not measurable. What stands there is the durability question the memory
>   layer actually claims: do fixes hold. Where the pool exists, nothing is
>   lost.

Two tests is a small family: a standard **Holm correction** across the pair
keeps the "you ran many tests" objection quiet. (Holm correction: a standard
recipe that demands stronger evidence when more than one claim is tested.)

## 6. The reporting template — one shape, always

Every repository gets the **same table**, whatever its counts are. A small-count
repo does not get a different format — it gets the same template plus a note.

The template always shows:

| cell | what it holds |
|---|---|
| fixes | count of certified fixes |
| lapses | count of certified lapses |
| recurrence | `lapses / fixes` **with both counts visible** (2/6), plus a Wilson interval |
| retention | % still holding at 1,000 commits, at window end, and average clean-time |
| censored | counts of rule-withdrawals, renames/lost-track — beside the curve, never hidden |
| noise floor | what pure detector error could fake, from #180's simulation |

(Wilson interval: a range that honestly reflects small counts — at 2/6 it is
very wide, and that width *is the message*.)

**The note rule.** Below 30 events in a cell, a standing note is attached:
*"based on N events — read this as a count, not a rate."* The number is still
shown; it is never silently dropped, never shown without its n.

Per-repo cells are the results; a pooled three-repo figure is reported as a
convenience (the pool is built per-repo then combined, never by mashing raw rows
together), and each repo's sampling resolution is stated (HA's ruler is ±500
commits, flowkit's ±50 — the same "300 commits" means different precision in
each). The study also draws the recurrence result against repository size —
three points, and their spread is reported as three points, not as a trend.

## 7. What a null looks like — decided before the run

With few events, "we found nothing" is not a result; it usually means "we
couldn't tell." To make a null mean something, this study commits up front to
three possible outcomes:

1. **The two groups differ clearly** (fixed modules come back more than matched
   controls) → durability is real. The headline stands.
2. **The two groups are within the small band** → recurrence is background
   churn; the memory DV is measuring noise. **This is a finding, and it is
   publishable** — a real question got a real answer.
3. **Too few events to tell** → we say exactly that: "indeterminate at this n,"
   with the interval width shown. Publishable as an honest small-scale result —
   but only because we said in advance that it counts.

The "small band" is fixed now, not after the numbers: if the two groups'
lapse rates differ by less than roughly a **hazard ratio of 0.67–1.5** — the
usual "small effect" bounds; a hazard ratio is simply the relative pace at
which the two groups break — they are called equivalent.

Intervals are reported, not p-values. A claim needs its interval, and the
error-only noise floor rides next to every number, so even "indeterminate" says
*"our numbers sit inside the noise band"* — a measurement, not a shrug.

One asymmetry to carry into the paper: fixes shorter than two sample gaps are
invisible (#182's 2N rule), so the study **undercounts** short fixes and short
come-backs. A **high** recurrence result is therefore solid — undercounting
cannot manufacture events. A **low** recurrence result is a floor, and is
labelled as one.

## 8. What is frozen, what is deferred

**Frozen here, before the run:** the row definition, the censoring rules, the two
tests, the Holm correction, the equivalence margin, the 30-event note rule, the
template, the horizons (1,000 commits / window end / ~3 years in days), and the
note text.

**Deliberately not frozen:**

- Whether the matched comparison (Test 2) is *reported* in the paper or kept in
  the appendix — decided after seeing how many events there are; measuring it is
  unconditional.
- Power specifics (what n would be needed to shrink the intervals) — computed
  once the pilot repos (#182's run-cheapest-first order) yield real counts.
- The claim's wording — #185.

**The escape hatch, unchanged from #182:** if the cheap repos come back
near-silent, that is itself the finding, and python-tuf (minutes to add) is the
pre-agreed add-back. It is *not* added now — the panel stays three.

## 9. What this study does not claim

- Not *"Shepherd is good"* — the benchmark carries system quality.
- Not *"decisions decay"* — we cannot see intent or decisions; we see compliance
  states come and go.
- Not *"enforcement is robust/weak"* — nothing in these histories enforced
  anything; we measure what a future memory-checking system would face.
- Not comparability with the FSE 2025 number (50.8% dead suppressions) — that
  measures human suppression practice, which a replay contains none of
  (#180). The Exclusion Ratchet stays as a shape comparison only.