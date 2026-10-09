# Shepherd longitudinal decision-memory study

The COMP9992 headline study (map [#178](https://github.com/Ravicha2/Shepherd/issues/178)):
replaying the histories of pinned repositories at a sampled every-N cadence and
measuring how well ADR-governed compliance holds up over a repository's life.
This file holds the domain language the study's tickets and paper use. The
Shepherd *tool* (the `app/` codebase) is a separate context; add a
`CONTEXT-MAP.md` if its language ever needs its own file.

## Language

**Compliance durability**:
How well a *clean* state survives normal development — of the governed modules
that went clean, how many lapse back into violation, and after how long. The
study's headline object: a recurrence fraction plus a duration.
_Avoid_: decision regression, decision decay, robustness, compliance enforcement
(the histories contain no enforcing mechanism, and nothing is perturbed — the
only stress is ordinary development churn).

**Governed module**:
A module that sits under some rule's subject, so the rule can fire on it. The
unit of the study (a module × rule pair). A module outside every subject is not
governed and can never violate, so it is never a control.
_Avoid_: covered module, subject.

**Clean (compliant) state**:
A governed module that does not currently violate its rule at a given sample.

**Fix** (replay sense):
A governed module that violated its rule at one sample and does not at a later
one. Not necessarily a deliberate act — the code may have drifted clean without
anyone seeing the violation. The replay cannot observe intent.
_Avoid_: repair, resolution.

**Lapse / compliance recurrence**:
A clean governed module that violates its rule again. The study's main event.
_Avoid_: re-introduction, decision regression (both imply a decision that was
deliberately undone, which the replay cannot see). Exception: as *prior-art
vocabulary* when citing related work — never as our own word.

**Certified**:
An event the reviewer agent has confirmed true from the ADR text and the
governed module's code at the relevant commits — the study's reported numbers
count only certified events ([#183](https://github.com/Ravicha2/Shepherd/issues/183)).

**Blip**:
A violation that vanishes for one sample and returns the next; almost always a
detector miss, not a real fix-and-return. Counted on the raw records before the
two-sample rule erases them ([#181](https://github.com/Ravicha2/Shepherd/issues/181)/[#182](https://github.com/Ravicha2/Shepherd/issues/182)).

**Fake fix**:
A violation certified *true* at the absent sample — the detector missed it. Not
a fix; thrown out and counted in the error table.

**Noise floor**:
What pure detector error could fake, **measured on a repo's own records, never
simulated**: the blip rate on the raw records plus the fake-fix and
false-positive fractions from the error table. Printed beside every headline
number; "recurrence is above the floor" is tested per repo against its own
measured floor (settled [#207](https://github.com/Ravicha2/Shepherd/issues/207),
2026-10-09 — the error-only simulation that the frozen plan named is retired:
the off-panel eval-gate rates that fed it make its floor degenerate at ~100%, so
it can bound nothing on any repo).
_Avoid_: error-only simulation (retired).

**Treated module**:
A governed module with a certified fix episode. The risk-set entry for the
durability measurement.

**Matched control**:
A governed module under the *same* rule that never violated, matched to a
treated module on fan-in, churn and age. The comparison that keeps "lapse"
distinct from "busy spots get re-broken."

## Relationships

- **Compliance durability** is measured over **treated modules**, as a recurrence
  fraction and a time-to-lapse.
- One row per **governed module**; the clock runs from the module's first **fix**
  onward.
- A **lapse** counts only if **certified**; a **blip** and a **fake fix** are
  discarded before it does.
- A **matched control** shares the treated module's rule and its fan-in, churn
  and age.

## Example dialogue

> **Dev:** "So a module that goes clean and then imports the banned package again is a *decision regression*?"
> **Researcher:** "No — call it a **lapse**. We never saw anyone decide anything; the code just lapsed. What we measure is **compliance durability**, and we only count it if the reviewer **certified** it."

## Flagged ambiguities

- **"resolve" means two different things** — the expensive ADR-extraction session
  and the cheap per-pair rename lookup (census §3 vs [#181](https://github.com/Ravicha2/Shepherd/issues/181)). The code should name them differently ([#182](https://github.com/Ravicha2/Shepherd/issues/182) risk).
- **"sample"** = one commit plus the ADR set in force at that commit
  ([#182](https://github.com/Ravicha2/Shepherd/issues/182)).
- **Dismissals are out of scope** for this study — a replay manufactures none, so
  the `filter_dismissed` bug cannot corrupt these measurements ([#180](https://github.com/Ravicha2/Shepherd/issues/180)/[#181](https://github.com/Ravicha2/Shepherd/issues/181)).
