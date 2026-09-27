# Next steps — recommendation

**Written 2026-09-27.** Supersedes the 2026-09-26 version, which settled on the author-side
experiment alone. Start here.

Two expansion approaches are recommended, written up in §1 and §2. Everything else that was
considered — including the candidates this page used to lead with — is in
[Considered candidates](#considered-candidates).

Supporting material: the [research brief](research-brief.md) is the evidence and the argument;
[run 3](feynman-run3.md) re-tested that brief and **corrected** it (its §6 ledger C1–C9 — where
they disagree, run 3 wins); the earlier runs, the [provenance](feynman-provenance.md) and the
node-search contracts are the sources behind them.

---

## 1. A security-labelled decision constraint, judged by a foreign oracle

*2–3 weeks.*

### The claim

> On N Python repositories, a route→authorization dependency constraint recovered X of Y
> adjudicated missing-or-weakened-authorization routes at the merge commit that introduced each
> one, with precision P and recall R, against an AST-body baseline and a decorator-grep baseline.

### Why this one

It is the only candidate in the entire application space with an **external adjudicator**. Every
other direction we could publish carries the same reviewer objection — *the detector is its own
oracle* — and that objection is fatal to any claim of the form "we detect architectural problems".
Access control is the exception: it admits a third-party ground truth, in CWE-306/862/863 labels
plus differential / black-box authorization testing (ACtests, BACFuzz). That is worth more than
the framing.

It also reuses everything we have built. The constraint is the existing predicate
(`requires_dependency(app.routes.*, <auth module>)`), evaluated by the existing engine over the
existing graph. The new work is the corpus, the labels, and the two adjudicators.

### What it needs

- **Corpus.** 5–8 Python repos with a single explicit authorization idiom: FastAPI `Depends(...)`
  or router-level `dependencies=[...]`; Django `permission_classes` / `login_required`. Budget one
  extractor per repo — five repos needed five last time, and only one of five carried a permission
  vocabulary rich enough to compare control *strength*.
- **Unit of analysis.** Every commit that adds or edits a route handler. That is where the defect
  is created, and it is why this is a *detection-at-introduction* claim rather than a HEAD-state
  check.
- **Labels.** Two-rater adjudication into {properly enforced, missing, weakened, different
  sufficient control, **unknown**}, reporting Cohen's κ. "Unknown" must be a reported outcome, not
  a discarded case — the Python analogue abstained on ≥72% of routes.
- **Arms.** (A) the ADG constraint; (B) an AST check that the handler body or signature references
  an authorization symbol; (C) a decorator-name grep.
- **Dependent variables.** Precision, recall, and **time-to-first-detection** — flagged at the
  introducing commit versus only at HEAD — with Wilson intervals, paired against B and C.
- **Minimum n.** ≥5 repos, ≥50 adjudicated route-change events, ≥5 positives. Below 10 positives,
  report counts rather than rates.

### What decides it

Two measurements, and they must be built into the first result rather than bolted on after:

1. **Evasion recall.** Mechanically rewrite each adjudicated *violating* route into the standard
   Python evasions — `if TYPE_CHECKING:` import; `importlib.import_module(...)` inside the handler;
   decorator re-applied to a wrapper; control moved to app-level middleware; guard moved into a
   called service — and re-run the constraint. **If recall on the rewritten set collapses, this is
   architectural hygiene, not a security control, and the framing must be withdrawn.** The
   detection claim can survive that; the "by construction" claim cannot.
2. **Runtime parity.** Run a differential authorization oracle against constraint-compliant versus
   constraint-violating repos. If compliant repos fail at the same rate, the framing is dead
   regardless of how good the graph is.

### Cost and risk

The cost is not the code. It is the **adjudication** — human, two-rater, ≥50 events — and the
extractors. The adjudication is the schedule risk, and it is the reason this approach does not sit
alongside the flagship harness in the same weeks (§ Also live).

### What is new, and what is not

The idea is **not** new and must not be claimed as such. The concept is named — *authorization
context consistency* (MACE, CCS 2014) — and there is a route-level implementation carrying the
exact CWE labels (AuthCheck, 2019). "By construction" is false at framework level: Django REST
Framework defaults to `AllowAny`, and the decisive check often lives inline in the handler (216 of
608 handlers in the Python analogue).

What is novel is narrow and defensible: the **decision-anchored substrate**, the **persistence
across graph rebuilds**, and above all the **external adjudication**. Claim the evaluation
strategy, not the idea. Scope the paper as *detection and localization of a security-labelled
failure class*, never as "we prevented broken access control".

---

## 2. Memory-layer measurement — decision regression and dead dismissals

*Days.*

### The claim

> Across N Python repositories, X% of predicates that were dismissed or superseded are violated
> again later (decision regression), with a median time-to-reintroduction of T commits; and Y% of
> live dismissals suppress no currently-detectable violation (dead dismissals).

### Why this one

It is **ledger arithmetic over data we already persist**: for each dismissal or supersession,
replay the history and check whether the same predicate + FQN identity is violated again. No
model, no benchmark, no annotation, no agent. The T1 research note estimates it under a day.

And it is the only candidate that tests the actual **moat**. Persistence across graph rebuilds is
the thing a stateless linter structurally cannot do, and nobody has measured it. Every other
approach on the table can be evaluated with the memory layer switched off; this one cannot exist
without it.

It also produces a new dependent variable — re-introduction of a settled decision — that composes
with every other candidate as the one outcome that isolates memory from retrieval.

### What it needs

- **Data.** The five ingestion-benchmark repos and the five ADR-bearing gold repos — **two
  different five-repo sets**; count dismissals on whichever set actually carries them — plus any
  further Python repos with ADRs we can ingest. Report per-repo cells, not only a pooled number.
- **Dependent variables.** (i) re-introduction rate; (ii) a survival curve of dismissals
  (Kaplan–Meier, as the Exclusion Ratchet does); (iii) dead-dismissal fraction; (iv) the
  distribution of dismissal scope — predicate-only, FQN-scoped, repo-wide.
- **Minimum n.** Report exact counts, not rates, below 30 events. **If dismissals or supersessions
  are too few on five repos, say so — that is itself the finding.**

### What decides it

**A matched hazard comparison.** For each dismissed or superseded predicate, sample a control
predicate that was never dismissed, matched on node fan-in, churn and age, and compare the hazard
of subsequent violation.

**If a prior dismissal does not raise the hazard of re-introduction, the dependent variable is
measuring noise — and that is the finding.** This is not a robustness check; it is the difference
between a result and a table.

Secondarily: report the fraction of live dismissals that suppress zero subsequent violations, and
compare it directly against the FSE 2025 figure. A large deviation in either direction is itself
interesting; agreement makes the memory layer's triage quality quantifiable.

### Cost and risk

Days, and the risk is stated in the claim: **the dismissals may be noise, so re-introductions may
be noise.** The adjacent evidence says suppression practice is sloppy — 50.8% of 7,357
static-analysis suppressions across 46 Python projects "do not affect any warning and hence are
practically useless", and ArchUnit's freeze store is documented with orphaned references. If ours
are similar, the rate measures the noisiness of human triage rather than decision decay. The
matched hazard comparison is precisely the measurement that separates the two.

There is also a **base-rate** risk: on five repos there may be too few dismissals for a survival
curve with any power. That is why the counts-first rule above matters.

### External anchors

Different domains, so they *calibrate* the expectation rather than confirm it. **50.8%** of 7,357
static-analysis suppressions suppress nothing (FSE 2025). **86.7%** of security-rule exclusions are
still in force after three years, with 31% of narrowing invisible to structural comparison
(Exclusion Ratchet, 8,234 revisions). A ~50% expected effect size is what makes a first result
interpretable rather than exploratory — without it, a number like "34% of dismissed predicates
were violated again" means nothing.

---

## Also live — not candidates, but do not let them slip

Neither of these is an expansion approach, and neither should wait on §1 or §2.

**The flagship's arm design has a confound, and it must be fixed before the first run.** The
author-side experiment's arms B (all constraints) and C (relevance-selected) differ in **length**,
not only in relevance — B injects more tokens than C, and A fewer. A 2026 preprint found an
**equal-length irrelevant** context performed the same as a relevant one (3/10 vs 3/10, Fisher
p = 0.0698; clean condition 8/10): the measured damage tracked length, not relevance.
CodeRAG-Bench's gold-docs result is real (GPT-4o DS-1000 52.7 → 51.2), but the same table shows
gold documents *helping* elsewhere (HumanEval 75.6 → 92.6; SWE-bench 2.3 → 30.7). **B vs C needs a
length-matched placebo arm before the "relevance" claim means anything.** That is a design change
made now and a re-run made later. The novelty claim narrows with it: arXiv:2605.08112 reports
decision compliance 46% → 95% on 8 tasks / 41 decision points, though it is vendor-authored,
unrefereed, and injects *product* decisions rather than architectural ones.

**Two items that are not candidates at all.** *Census at scale* — run the existing census script
over the ADR-Study / 980-ADR / 4,911-ADR corpora and report the convertible-ADR rate, which
*tests* §3's 26% premise rather than confirming it (pre-register the direction of interest, because
if 26% does not hold the ontology argument loses its quantitative base). And *file the
stale-dismissal gap*: `filter_dismissed` (`app/services/cpt/dismissal.py:80`) matches on the
identity tuple alone, so a dismissal is a permanent, un-revalidated judgement about a *location* —
correct when made, silently wrong once the code at `matched_fqn` changes to genuinely violate. That
affects current users, is unrelated to the research direction, and is a live bug.

---

## Considered candidates

Everything else that was on the table, with the reason it is not in §1 or §2. Full detail in
[run 3 §2](feynman-run3.md#2-q1--the-application-space).

### Viable, but not now

| Candidate | Why not now |
|---|---|
| **Decision-vs-structure gate** — decision-anchored groups vs *size-matched* structure-only groups on the same bugs, 1–2 weeks | Not an application and produces no result on its own. It is the cheap way to close a question: if the decision layer adds nothing over structure once size is matched, the localization and anti-pattern lines are both dead — learned in two weeks rather than ten. Worth running *before* committing to anything expensive. It does **not** test §1's route→auth constraint or §2's re-introduction DV. |
| **Change-impact analysis**, 1–2 weeks | The graph already does it; the ADR filter is the only delta, and it is a small one. Evidence is for *prediction*, not for decision-anchoring. |
| **Review routing from violation memory**, 2 weeks | Well-populated prior art (EASE 2023 routes reviewers for architecture violations, beating RevFinder). The unoccupied delta — route on *who dismissed or superseded this predicate before* — is real but narrow. |
| **Onboarding digest / documentation generation**, 1–2 and 2–3 weeks | Measurable, but the evidence base is survey-level, and one controlled study found documentation *format* does not significantly affect newcomers' architectural understanding. |
| **Release-risk ledger**, 1 week | No agreed operational definition, and one single-case-study anchor. |
| **Architecture-evolution forecasting**, 1–2 weeks | Correlational only. |
| **Decision archaeology / supersession timeline**, days | No comparable timeline work; only retrieval-layer evidence that supersession structure carries signal. |
| **Test selection / regression prioritisation**, 3–4 weeks | RTS evidence is strong but non-architectural; nothing decision-anchored was found. |
| **Audit-evidence bundling**, 2 weeks | No peer-reviewed study found; vendor grey literature only. |
| **Deprecation / EOL impact of decision-anchored deps**, 1 week | At risk of being "`pip-audit` plus a join". |
| **AI-authored-code provenance gating** | Data-blocked. |

### Rejected

| Candidate | Why rejected |
|---|---|
| **Decision-anchored bug localization** *(the brief's S4, previously a headline)* | 6–10 weeks, and there is **no Python ADR-bearing issue→fix benchmark** — the corpus would have to be built before the experiment could run. The headline evidence is also weaker than the brief states: the ICSE 2014 candidate pool was selected from the bug labels, the nearest quantitative analogue is partly negative (smell-aware localization optimal at weight α = 0 in **49 of 224** systems), and architecture-model-driven localization is prior art (FLABot, CSMR 2009). Its defensible first result is the ablation — which is the gate above, not a localization system. |
| **Anti-pattern families straight off the graph** *(the brief's §8)* | 4–6 weeks and it **does not use the decision layer at all**. The per-family impact gradient is single author group, Java + C# only, correlational and metric-convention-sensitive; the honest expectation for the pure-graph families is a null. A replication of someone else's result with our moat switched off. |
| **CI gating policy** | Most negative lane in the evidence. Also gameable in an agentic loop — an agent routes around a gate rather than improving the architecture. |
| **Incident / root-cause analysis; fault-tree and SRE blast radius** | Both need runtime graphs, which we do not have. |
| **Supply-chain / dependency-risk scoring** | Needs cross-package reachability; not differentiating. `pip-audit` plus a join. |
| **Architecture-aware code search** | No decision anchor found. |
| **Architecture-informed fine-tuning data selection** | No evidence found. |

---

## Where the detail is

| Question | Section |
|---|---|
| The application space, ranked — 23 candidates, 3 rejected | [run 3 §2](feynman-run3.md#2-q1--the-application-space) |
| §1 in full: corpus, arms, DVs, minimum n | [run 3 §4.3](feynman-run3.md#43-rank-2--cheapest-defensible-first-result-and-evaluation) |
| §2 in full: DVs, the matched hazard comparison, minimum n | [run 3 §4.2](feynman-run3.md#42-rank-1--cheapest-defensible-first-result-and-evaluation) |
| The killer measurement for each | [run 3 §5](feynman-run3.md#5-q4--strongest-objection-and-killer-measurement) |
| The corrections to the brief (C1–C9) | [run 3 §6](feynman-run3.md#6-correction-ledger--your-four-candidate-claims) |
| The negatives, named | [run 3 §3.6](feynman-run3.md#36-the-negatives-named) |
| The author-side experiment in full: arms, DVs, degenerate case | [brief §4](research-brief.md#4-ranked-extension-scenarios) |
| Why the ceiling is convertibility, not capability | [brief §3](research-brief.md#3-the-real-ceiling-convertibility-not-capability) |
| What could invalidate all of it | [brief §9](research-brief.md#9-caveats) |
