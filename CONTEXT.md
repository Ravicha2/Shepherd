# Shepherd longitudinal decision-memory study

> **Scope: PARKED longitudinal study ([#178](https://github.com/Ravicha2/Shepherd/issues/178)).**
> This file is the domain language of the durability line only — not of Shepherd the
> tool, and not of the active security eval ([#220](https://github.com/Ravicha2/Shepherd/issues/220)),
> whose vocabulary is `../research-exp-setup/security/GLOSSARY.md`. Do not extend it
> for #220.

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

**Equivalence band (HR 0.67–1.5)**:
The pre-declared margin inside which treated and control lapse rates are
called equivalent (outcome 2) on Test 2's matched design. It is a borrowed
small-effect convention, not derived from the memory-layer claim; its
smallest-effect justification (SESOI) is a **pre-HA obligation** — decided
2026-10-16 to justify it in a dated note rather than drop it, so outcome 2
stays reachable. Anchoring it to magnitudes measured elsewhere (e.g. the
benchmark's own effect sizes) calibrates the threshold; it does not mix the
study's claim with system quality (§1's category-error rule forbids the
conflation, not the calibration).
_Avoid_: presenting 0.67–1.5 as derived; editing the band after HA's
numbers are seen.

**Outcome 3, informative vs uninformative**:
The plan's "too few events to tell" verdict (§7) is a real finding only when
the cell's Wilson interval excludes rates that would matter for the claim.
A cell compatible with every rate is honest uncertainty, not a finding:
report the counts, claim nothing. Experimenter's compliance cell (1/149,
Wilson 0.12–3.70%) rules out visible-lapse recurrence (lapses persisting
≥2 sample gaps) above ~3.7% — informative, thinly. Flowkit's (0 events over
1 watch, Wilson 0–79%) is compatible with any rate — uninformative. The
standard is external: an indeterminate is a finding only if it constrains
(Altman & Bland 1995; Lakens, *Statistical Inferences* §9 — both tests
failing is "inconclusive").
_Avoid_: "outcome 3 is a finding" without the informative/uninformative
qualification; reading an uninformative cell as evidence of absence.
(Settled in the 2026-10-16 evaluation grilling.)

## Relationships

- **Compliance durability** is measured over **treated modules**, as a recurrence
  fraction and a time-to-lapse.
- One row per **governed module**; the clock runs from the module's first **fix**
  onward.
- A **lapse** counts only if **certified**; a **blip** and a **fake fix** are
  discarded before it does.
- A **matched control** shares the treated module's rule and its fan-in, churn
  and age.
- An **outcome 3** cell carries a conclusion only where it is informative —
  its interval excludes rates that would matter; an uninformative cell
  reports counts and claims nothing.

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
