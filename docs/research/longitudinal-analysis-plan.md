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

> **Dated note (2026-10-15, owner) — the study's population is opened as a question, before HA
> runs.** The panel so far — flowkit, experimenter, home-assistant — is human-managed: humans write
> the changes, and human review culture is where the ADRs live. The sentence at the top of this
> section, though, is said to an **agent** working agent-written code, and the owner's hypothesis
> is that the two populations differ: AI-assisted development drifts from ADRs more, precisely
> because the actor lacks the memory this study is about. A probe of prominent public repos found
> the intersection (AI-assisted + ADR-carrying + Python) essentially unoccupied; the
> best-documented instance is **Shepherd itself** — 248 commits since 2026-05-28, 18 ADRs since
> 2026-06-08 of which **11 carry explicit supersession pointers**, and **80 of 248 commits (32%)
> co-authored by Claude**, the first one the day after the first ADR. These are the #193 ticket's
> figures; the frozen-clone re-derivation in
> `research-exp-setup/docs/issue-212-shepherd-self-ingestion.md` §4 gives **249** commits and **6**
> supersession pointers under the implemented status rule — the ticket's 11 is the union, a
> rule-and-scope difference rather than a miscount.
>
> **Pre-registered before any run of it** ([#212](https://github.com/Ravicha2/Shepherd/issues/212)):
> a pilot replay of Shepherd's own history, as a viability probe of the AI-assisted population —
> **not a panel addition**. Both readings are declared now, per §7's discipline:
>
> - **If the history is louder than the human panel's** — more violations, more lapses — the
>   phenomenon the memory layer exists for is real in the population it serves. What that confirms
>   is the **premise** (there is something for memory to do), not the performance: detection
>   quality stays the benchmark's job, per the category-error rule in this section.
> - **If the history is quiet** — even the most on-point case leaves the memory layer little to
>   do. Also a finding, per this section: *"if come-backs are rare, the memory layer has little to
>   do."*
>
> Neither reading upgrades itself after the fact, and the panel decision is made on **construct
> grounds** — whether the AI-assisted population is the one the problem statement targets — not on
> this pilot's outcome. The pilot determines whether that population is measurable, and what its
> machinery needs: authorship labels (the 80/248 in-history markers), and tier-1 supersession,
> which was empty in both cheap repos and is present here (11 ADRs with pointers).

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

> **Dated note (2026-10-15) — on the `requires` side, the "rule" in one module × one rule is
> satisfied by "the module changed".** The experimenter pilot's evaluation
> ([#193](https://github.com/Ravicha2/Shepherd/issues/193); evidence in
> `research-exp-setup/docs/issue-193-experimenter-evaluation.md`) measured what the rules in that
> product actually are, now that two repos have run.
>
> - **The rows are dominated by one pattern.** 3,840 of experimenter's 3,984 rows and 1,253 of
>   flowkit's 1,254 come from `requires_dependency <subject>.* → <library>` rules whose firing
>   condition is "the changed module does not import `<library>`" — met by ~99% of modules in both
>   repos (experimenter: `graphene_django` 3 of 664 modules, `kinto_http` 3, `celery` 4,
>   `pydantic` 5; flowkit: `redis` 1 of 577, `flask_jwt_extended` 0); experimenter's other 5
>   `requires` rows are `requires_implementation`. The source ADRs are
>   system-level statements — flowkit 0005's "API-backend communication will be via zeromq, IPC in
>   the backend will be mediated by redis", experimenter 0002's graphene-django "would be used in
>   the back-end" — lowered to per-module dependency assertions over a repo-wide subject.
> - **So on that side a row's "fix" and "lapse" are not repair and regression.** Under the
>   two-sample rule a certified fix is two consecutive samples in which the governed node did not
>   change, and a lapse is two consecutive samples in which it did: the row tracks change
>   alignment, and resampling at a different N pairs different changes up. The worked case: the
>   rule × module behind 7 of experimenter's 8 lapses fires at samples
>   `[0, 11, 31, 37, 56, 125, 142, 143, 188]`, and only 142/143 are consecutive — so only that pair
>   is a sustained presence, and therefore the only lapse.
> - **The `prohibits` side is unaffected.** Those rules are state-checked, so presence is a
>   property of the code rather than of what changed, and fix and lapse are genuine state
>   transitions. Experimenter's other lapse is exactly that one: `prohibits_dependency cirrus.* →
>   experimenter.*` (ADR 0009). flowkit has no `prohibits` firing at all, so its table is the
>   exposed case in full — and this is the split §5's note requires being reported separately.
>
> **Three decisions this note opens rather than makes** (each wants its own dated note; the row
> definition above stays as written until one lands):
>
> 1. **May a broad-wildcard change-triggered rule carry the headline denominator?** Either report
>    that family separately and compute recurrence on semantically bounded rows — state-checked
>    `prohibits`, plus `requires` rules whose subject is a bounded module set — or keep the
>    definition as frozen and pre-declare the caveat in the reporting template.
> 2. **Supersession.** `requires experimenter.* → graphene_django` (ADR 0002) and `prohibits
>    experimenter.* → graphene_django` (ADR 0008, the later move off GraphQL) are both in force in
>    the same versions: the detector applies every ADR as binding and does not model a later one
>    retiring an earlier one.
> 3. **Sampling alignment.** Whether the lapse rule needs a persistence criterion that a change in
>    N cannot manufacture.
>
> **What this changes, and what it does not.** Changed: *what the study may divide by* — and
> therefore what the recurrence rate is a rate **of** — has to be settled before HA runs, because
> HA inherits the extraction pipeline and the plan does not permit re-interpreting a headline
> afterwards. §8's power note reasons over these same rates; its n-arithmetic is unchanged (it is
> a property of the counts), but the denominator it divides by is the one decided here. Not
> changed: the detector, the pinning, the re-derivation and the events model did exactly what they
> claim — the run reproduces at all 30 repeat-check sites — and the two tests' mechanics, Holm, the
> 0.67–1.5 margin, the 30-event note rule, the template, the horizons, the runnability gate (both
> cheap repos stay not-run) and the three-repo panel all stand.
>
> **Reason.** A cheap-repo pilot exists to decide whether the measurement means what the plan
> assumes, before the expensive run is bought. The cheap repos' tables are a pure function of
> saved records and pinned caches — no re-run is needed to settle this — so it is cheap now and
> expensive to discover after HA.
>
> **Dated note (2026-10-15, owner) — two of those three decisions are taken: the §3 table is
> reported as two lists, and contradictions between ADRs resolve by precedence rather than being
> enforced side by side.** Decided on the owner's call in the [#193](https://github.com/Ravicha2/Shepherd/issues/193)
> evaluation thread. Decision 3 (whether the lapse rule needs a criterion a change in N cannot
> manufacture) stays open, with the note above.
>
> **Decision 1 — two lists.** Every §3 row is assigned to one list at reporting time, by what the
> violation's presence actually is a property of:
>
> - **Compliance list** — the violation is a property of the *code state*: `prohibits_*` rules
>   (state-checked at every sample), plus `requires_*` rules whose subject names a bounded module
>   subtree rather than the whole repository. This list carries the plan's two tests, the headline
>   recurrence cell, the floors, the Holm correction and the equivalence band.
> - **Change-firing list** — everything else, headed by the repo-wide wildcard `requires_dependency`
>   family. Reported in the same template beside the compliance list, under a standing label:
>   *a row here means the governed node changed, not that compliance failed.*
>
> What the pilot's own tables become under this split: experimenter's compliance list is **149 rows
> / 1 lapse** (0.67%, Wilson 0.12–3.70%) against 3,835 / 7 on the change-firing side; flowkit's is
> **1 row / 0 lapses** against 1,253 / 144. This split and §8's per-predicate split (139 `prohibits`
> / 3,845 `requires`) are two cuts of the same 3,984 rows, bridged by the 10 bounded-subject
> `requires` rules (5 `requires_dependency` + 5 `requires_implementation`, all
> `experimenter.experimenter.visualization.*`): 139 + 10 = 149 compliance, 3,845 − 10 = 3,835
> change-firing. Both cheap repos fall further below the 10-certified-lapse
> gate on the list that carries the tests, so the gate's verdict and #207's number are unchanged —
> and the compliance-list intervals are now readings of what the sentence above says they are. A
> bounded-subject `requires_*` rule earns its compliance place only where its requirement is one
> most governed modules actually meet; the implementation reports that specificity check beside the
> split, and any near-tautological bounded rule moves to the change-firing list rather than staying
> in it.
>
> **Decision 2 — precedence, not side-by-side enforcement.** The detector applies every ADR as
> binding and models no supersession; the pilot caught the direct case, ADR 0002 requiring
> graphene_django (878 change-firing rows) while the later ADR 0008 prohibits it (111 compliance
> rows). From the pilot on, contradictions resolve by tier:
>
> - **Tier 1 — explicit.** An ADR whose own status metadata marks it superseded, deprecated or
>   retracted makes its constraints non-binding; the constraint is retired and the change is
>   counted in §3's existing rule-withdrawal censoring category, not as an amendment. The pilot
>   found this tier nearly empty: experimenter's ADRs carry MADR-style `- Status: accepted` lines,
>   flowkit's carry `## Status` headers, and neither repo's ADRs contain a supersession pointer
>   anywhere in their text.
> - **Tier 2 — implicit, and reported.** Where two ADRs state directly opposite constraints on the
>   same subject and object and neither carries status metadata, the later-numbered ADR wins, and
>   the conflict is reported as a checkable finding beside the tables rather than resolved silently
>   — because an ADR can also specialise rather than supersede, "later wins" is a heuristic whose
>   every application is visible.
>
> **What this changes, and what it does not.** The §3 row-definition sentence above ("one row = one
> module × one rule") now names two lists, and every template cell that carries a test reads from
> the compliance list; the change-firing list is context, never an arm. Unchanged: the tests'
> mechanics, Holm, the 0.67–1.5 margin, the 30-event note rule, the horizons, the runnability gate,
> the three-repo panel, and the published artifacts — the split is a classification of the saved
> rows, computed from the committed tables and rule sets with no detect re-run. Applying tier 2 to
> the rule sets themselves (retiring constraints before detection rather than filtering rows after)
> would need re-detection and is **not** part of this decision; the HA prep decides it.
>
> **Reason.** The pilot's finding was that one list was carrying two different things; the cheap
> fix is to stop pretending they are the same number, not to re-cut the data. And precedence is how
> human readers already resolve the 0002/0008 case — the machine should do the same, visibly.

> **Dated note (2026-10-15, owner) — decision 3 is closed without action.** The owner's call: no
> sampling-robustness work — no redefinition of the lapse rule, no denser resampling of the
> existing repos. The data agrees: on the compliance lists the cheap repos hold **1** lapse
> (experimenter) and **0** (flowkit), so no redefinition of the lapse rule can manufacture events;
> and §8's power note already showed that denser sampling clears the runnability gate but not the
> verdict. The two-sample/sampling-alignment property stays documented as the caveat it already is
> (the note above), not as work to do. A *new* repo entering the study still chooses its sampling
> N once, at registration — that is a design choice, not resampling ([#212](https://github.com/Ravicha2/Shepherd/issues/212)).

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

> **Dated note (2026-10-15) — the pool-emptiness number is computed; the branch is set by a clock the
> plan does not name.** The note above rests the Test 2 branch on a measured claim: "Flowkit's records
> show that pool is empty there: no governed module of usable size under the fired rules never fires."
> #193's body corrected *where* it comes from — **code, not records**, since records persist firing
> violations only — and it is now computed and committed
> (`research-exp-setup/records/pool_emptiness/{flowkit,experimenter}.json`; method and caveats in
> `research-exp-setup/docs/issue-193-pool-emptiness.md`). One half of the sentence needs correcting;
> the other half carries the claim.
>
> - **The pool is not empty.** Under the pinned re-derivation (the reading the note above is written
>   against), flowkit has **324** never-fired governed-module instances under its 5 fired rules
>   (**163** distinct modules); experimenter has **4,261** (**569** distinct) under its 11 fired rules.
>   The "never fires" half of the sentence is false as literally stated.
> - **The load-bearing half is "of usable size."** A pool member is usable only if it matches a treated
>   module under the same rule within 0.5 SD on fan-in, churn and age. Whether any member is usable
>   depends on the reference clock chosen for the control's **own** measures — a control has no fix
>   sample, and the note above never names one:
>   - flowkit — 0 usable at the module's last appearance (⇒ fallback), 12 at its first appearance,
>     **23** at the rule's median fix sample (⇒ the matched design runs);
>   - experimenter — 0 usable at first appearance (⇒ fallback), 3 at last appearance, **5** at the
>     median fix sample (⇒ the matched design runs).
>
>   The two repos flip at *opposite* clocks, so the branch is set by an unstated clock choice rather
>   than by the data alone.
> - **What changes in the arithmetic:** the conditional is real, but it is not decided by emptiness.
>   The clock for a control's measures must be named — or both readings reported — before either repo's
>   branch is quoted. Flowkit's fallback survives only under the last-appearance clock; under the
>   fix-era clock flowkit has 23 usable controls and the matched design would run.
> - **What does not change:** Test 2's runnability gate (below 10 certified lapses ⇒ not-run; flowkit
>   n=1, experimenter 8 raw of which 1 genuine) is untouched — this number decides which branch *would*
>   run, not whether it runs. And a never-fired module is not yet a never-*violated* one where the rule
>   is change-triggered: the pool splits into **touched** (in some sample commit's diff ⇒ genuinely
>   clean) and **untouched** (never in a diff ⇒ merely unobserved), measured at 310/14 for flowkit and
>   4,010/251 for experimenter. For both repos **every usable control is in the touched part**, so the
>   split does not move either verdict; it matters only because it is the difference between the plan's
>   wording ("never-violated") and what the number can support.

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

> **Dated note (2026-10-14) — the python-tuf escape hatch is withdrawn; the
> panel is three repos, finally.** The paragraph above is superseded in place
> and is not a live requirement. Decided on the owner's call ([#193](https://github.com/Ravicha2/Shepherd/issues/193),
> 2026-10-14): python-tuf is **not** re-added at the pilot gate or at any later
> point. Its add-back is withdrawn, not deferred, so it is no longer a
> pilot-gate decision at all — what §8 *defers* is unchanged otherwise (the
> paper-vs-appendix placement of Test 2, per design; power specifics; #185's
> wording).
>
> **What this changes in the arithmetic, and what it does not.** Nothing about
> the row definition, the censoring rules, the two tests, the Holm correction,
> the equivalence margin, the 30-event note rule, the template or the horizons.
> What it removes is one branch of the interpretation: a near-silent cheap-repo
> result can no longer be answered by substituting a repo with different
> history. It is reported as the finding it is — counts over denominators with
> Wilson intervals, under the plan's standing note below 30 events (§6) — and
> the low-recurrence reading stays a **floor**, per §7's 2N-undercounting
> asymmetry. The panel is flowkit + experimenter + home-assistant, and the
> census's "nearly free to add back" line for python-tuf
> ([`longitudinal-replay-census.md`](./longitudinal-replay-census.md) §4) is
> read as available-and-declined, not as a pending option.
>
> **Reason.** A panel chosen after seeing how quiet the first two repos were is
> a panel chosen on the outcome; adding a third repo specifically because the
> others came back silent makes the recurrence estimate partly a function of
> which histories were admitted. With three repos fixed up front, the
> "phenomenon is rare" and "phenomenon is common" outcomes are both clean reads
> of the same pre-declared panel.

> **Dated note (2026-10-15) — power specifics, computed: both cheap repos land in outcome 3, and
> the 10-lapse gate is measured, not revised.** §8 defers "power specifics (what n would be needed
> to shrink the intervals) — computed once the pilot repos yield real counts." Both cheap repos now
> have counts — experimenter ran 2026-10-14/15 ([#193](https://github.com/Ravicha2/Shepherd/issues/193));
> flowkit's re-derivation is on the books (#208) — so the deferral is discharged here. Every figure,
> the per-predicate split and the derivations live in
> `research-exp-setup/docs/issue-193-power-note.md`; this note is the decision it settles.
>
> **The counts.** experimenter (204 samples, 0 merges; raw, pinned and re-derived tables
> byte-identical — no extraction drift): `lapses/fixes` 8/4,413 = 0.18% (Wilson 0.09–0.36%), §3 rows
> 8/3,984 = 0.20% (0.10–0.40%), split 139 `prohibits` rows / 1 lapse (0.72%) and 3,845 `requires`
> rows / 7 lapses (0.18%). flowkit canonical (#208): 144/1,254 §3 lapses, **all** on the sample-21
> merge artefact; off-artefact 0/1,110 = 0.00%.
>
> **Test 1 is indeterminate on both — and not for want of samples.** experimenter's recurrence point
> estimate sits **below its own measured floor** (14/4,685 = 0.30%, §5's 2026-10-10 note); when the
> estimate is already under the floor, no n clears it — more samples narrow the interval onto a
> value below the floor instead of pushing it above. flowkit's raw reading (9.96%) looks clearable,
> but 144 of its 145 raw lapses are the artefact; de-artefacted it sits at the floor too. The
> sensitivity is steep: under a constant-rate assumption it takes a genuine rate of **≥2–3× the
> floor** before the required n comes anywhere near a pilot's reach.
>
> **Test 2 is not run on either repo, and the pre-named gate holds.** Both sit below 10 certified
> lapses on every reading — experimenter 8 raw, of which 1 is genuine; flowkit 1 raw / 0 re-derived
> — and since certification can only shrink counts, the gate's verdict is robust and #207's number
> 10 needs **no revision**. Were the gate lifted, the design would still be indeterminate: the
> 0.67–1.5 band needs roughly **47 events per arm** (`SE(log HR) ≈ sqrt(2/D)`, so
> `1.96·sqrt(2/D) < |ln 1.5|`), and each cheap repo is one to two orders of magnitude short of that
> before the control side is counted at all.
>
> **What this changes, and what it does not.** Changed: the deferred power question is answered, and
> the runnability gate is now a measured number rather than an argument. Unchanged: the row
> definition, the censoring rules, the two tests, the Holm correction, the 0.67–1.5 margin, the
> 30-event note rule, the template, the horizons, and the three-repo panel. The recurrence readings
> stay a **floor** (§7's 2N-undercounting). The cheapest lever that changes a *state* is denser
> sampling of experimenter (~44 min at N=20 buys 255 samples and clears the gate); the only lever
> that can change the *verdict* is running home-assistant — which is exactly why HA's interpretation
> is fixed here, before it runs.
>
> **Reason.** Power is only meaningful against counts that exist. Both cheap repos' intervals are
> too wide to clear either the noise floor or the gate, and the only larger history in the
> pre-declared panel is HA's. If HA also lands in outcome 3, that is the finding — the phenomenon is
> rare at this sampling resolution — not a reason to re-cut the panel.

> **Dated note (2026-10-15) — Test 2's placement is decided per design, before HA runs.** The
> deferred-decision bullet above ("whether the matched comparison (Test 2) is *reported* in the
> paper or kept in the appendix") names one thing. #207's note made it two designs — a matched
> primary where a never-violated governed pool exists, and a permutation fallback where it does not
> — so the placement is decided **per design, not per study**, as #193's body requires.
>
> - **The matched design goes to the paper, wherever on the panel it runs.** It is the
>   pre-registered primary, and it is the only design that carries the history-predicts-future claim
>   the DV is about: spots that broke a rule against matched spots under the same rule that never
>   did. A primary analysis that runs on one panel repo is a per-repo cell in the paper (§6), not an
>   appendix robustness check.
> - **The permutation fallback goes to the appendix**, with one pre-declared exception: if the
>   matched design runs on **no** panel repo, the fallback *is* the study's Test 2 and is reported
>   in the paper, labelled as the fallback, with its restricted-null (exchangeability) caveat stated
>   in the text. The default is appendix because the fallback is not a matched comparison at all —
>   it compares each fixed module to its own dynamics, so it cannot carry the deterrence-shaped
>   claim — and because a substitute belongs beside the thing it substitutes for, not in its place.
>
> **What this changes in the arithmetic, and what it does not.** Nothing about the row definition,
> the censoring rules, the two tests' mechanics, the Holm correction, the 0.67–1.5 margin, the
> 30-event note rule, the template or the horizons. It fixes the paper/appendix call in advance for
> each design, so the call cannot be made after the numbers are seen — which is the whole reason it
> was deferred.
>
> **Evidence at the time of the call, and why the call is still live.** Both cheap repos sit below
> the pre-named 10-certified-lapse gate, so neither design is exercised on them: flowkit has 1
> genuine raw lapse (0 in the canonical re-derivation), experimenter has 8 raw §3 lapses of which 7
> sit on one sample (142) and 1 is genuine (sample 41). The placement is therefore live only if
> home-assistant clears the gate, and it is pre-declared now so that HA's pool result cannot choose
> its own venue. The pool-emptiness number that gates the matched design is committed at
> `research-exp-setup/records/pool_emptiness/`.

## 9. What this study does not claim

- Not *"Shepherd is good"* — the benchmark carries system quality.
- Not *"decisions decay"* — we cannot see intent or decisions; we see compliance
  states come and go.
- Not *"enforcement is robust/weak"* — nothing in these histories enforced
  anything; we measure what a future memory-checking system would face.
- Not comparability with the FSE 2025 number (50.8% dead suppressions) — that
  measures human suppression practice, which a replay contains none of
  (#180). The Exclusion Ratchet stays as a shape comparison only.