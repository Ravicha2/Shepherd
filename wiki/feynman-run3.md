> **Source:** [`notes/feynman-2026-09-27/beyond-compliance-applications.md`](../notes/feynman-2026-09-27/beyond-compliance-applications.md) @ `e3f0f17` — this page is a **copy** of the file above,
> kept here for browsing. Edit the source, not this page; regenerate with the
> command in [README.md](README.md).

# Beyond-compliance applications of an architectural decision graph with persistent decision memory

**Run:** `beyond-compliance-applications` · **Date:** 2026-09-26 · **Evidence rounds:** 1 (5 parallel
researcher streams + lead anchor reads) · **Verification:** verifier pass complete (84 numbered sources, 602 inline citations, no orphan sources, no
undefined inline numbers). Adversarial reviewer pass returned **3 MAJOR / 17 MINOR, no FATAL**; all applied in
this revised file. Three identifier corrections came out of the review pass — FLABot DOI, RoleCast venue, and
the Caracciolo et al. venue (**IWESEP 2016**, not ICSM 2015). Unreachable sources are listed in §8 Blocked /
unverified URLs.

**Subject system (fixed, not re-researched).** Shepherd: an Architectural Decision Graph (ADG) over a repo
(nodes = modules/FQNs; edges = CONTAINS / IMPORTS / CALLS / INHERITS); ADRs compiled to machine-checkable
predicates (`requires_dependency`, `prohibits_dependency`, `requires_implementation`, + related); a persistent
memory of violations, dismissals and supersessions that survives graph rebuilds while the graph itself is
rebuilt from the working tree or a git ref [1][2]. Detection is finished and plateaued: blended real-repo ingestion
accuracy **0.6333** across 5 Python repos, unchanged for many commits (`eval.md:509,517`, re-checked locally in
this pass — the prior value was 0.5667) [1].

**Scope boundary.** Everything below is *not* "does this code conform to ADR X". Conformance checking,
linters and rule engines are excluded by instruction.

**Integrity notes.** Every number traces to a source fetched in this run or to a local repo artifact; the
research notes are `outputs/.drafts/beyond-compliance-applications-research-*.md` [79][80][81][82][83][84].
Absences are stated as
**search-scoped** ("not found within this review's searches"), never as existence claims. Single-source
claims are flagged. Claims inherited from the workspace's prior notes but not re-verified are labelled
`inherited, not re-verified` [4].

---

## 0. Verdict up front

1. **Yes, there are defensible applications you did not list, and they are cheaper than the four you hold.**
   The two strongest new ones are memory-only and cost days, not weeks: **settled-decision re-introduction
   detection** ("this was dismissed/superseded and it is back") and **dead-dismissal detection** ("this
   dismissal suppresses nothing"). Both are uniquely enabled by persistence across graph rebuilds, and
   both have external anchor effect sizes from adjacent domains (FSE 2025: 50.8% of 7,357 static-analysis
   suppressions suppress nothing [52]; the Exclusion Ratchet: 86.7% of security-rule exclusions still in force
   after three years [53]). Neither is on your list. Neither is a conformance check.

2. **Your candidate (b)'s key asymmetry claim is overstated, and it matters.** Unstable Interface and
   Crossing are **not** history-only: both are hybrids with a pure-graph structural half, and DV8's own
   documentation says they need "both structural relation and co-change information" (re-checked in this run
   from the DV8 catalogue [15] and from Mo et al. WICSA 2015 §VI [14], which states only *Unstable Interface*
   and *Implicit Cross-module Dependency* "crucially depend on the availability of the project's evolution
   history"). The "Package Cycle is least impactful" half **is** supported (TSE 2021 §5.5, verbatim [13]), but it
   comes with a counter-result: on practitioners' refactoring **cost** the cycle family ranks **first** [20],
   while the survival evidence [19] is metric-ambiguous. Neither supports a "cycles don't matter" reading. And the ranking is single-author-group, Java + C# only,
   correlational, and metric-convention-sensitive (the T3 note's own re-derivation from the published tables reverses
   the UIF/MVG order under the relative-increase metric) [13][81].

3. **Your candidate (c) is not novel as an idea, but it is the only candidate with a foreign oracle.** The
   concept has a published name — **"authorization context consistency"** (MACE, CCS 2014) [29] — and a
   route-level implementation with the exact CWE labels (AuthCheck, 2019: CWE-306/862/863) [30]. What is
   defensible is the *evaluation strategy*: unlike every other candidate, access control admits an
   **external ground truth** (differential/black-box authorization testing: ACtests [34], BACFuzz [35]). That is worth
   more than the framing, and the framing itself should be dropped ("by construction" is false at framework
   level: Django REST Framework defaults to `AllowAny`) [33].

4. **Your candidate (a) has the strongest raw evidence and the worst cost-to-result ratio.** Architecture-
   model-driven fault localization is **prior art you do not cite** (FLABot, CSMR 2009 [11]; Expert Systems 2015 [12],
   with a with/without user comparison), the ICSE 2014 headline rests on a **candidate pool selected from the
   bug labels** [5][80], and the nearest quantitative analogue (smell-aware bug localization, 309 systems [25]) found the
   smell signal optimal at weight **α = 0** in **49 of 224** systems [25]. The decision anchor is a real,
   unoccupied axis — but it is a *semantic* delta, not an algorithmic one [80], and the cheapest way to test it is
   an ablation, not a localization system.

5. **Recommended settlement: (1) the memory layer, (2) the security-labelled constraint with the foreign
   oracle.** Ranked by defensibility × cost-to-publishable-result. The memory layer costs days and tests your
   actual differentiator [83]; the security constraint costs 2–3 weeks and buys the one thing the whole
   application space otherwise lacks — an external, third-party adjudicator [34][35]. Your candidates (a) and (b)
   should be *gated* behind a cheap ablation and a Python replication respectively, not led with [80][81].

---

## 1. How to read the evidence

Every candidate is graded into exactly one bucket **per claim** — the strongest study design actually found
for that claim [79]:

| Bucket | Meaning |
|---|---|
| **A** | **Established by controlled study** — experiment, ablation, or paired/RCT design with a named control. |
| **B** | **Established only correlationally** — association measured, no intervention. |
| **C** | **Tried and failed** — a study tested this application and reported null/negative; the failure is described. |
| **D** | **Searched negative (search-scoped)** — not found within this review's searches. |

Three reading rules follow from the evidence, and they are not decoration:

- **Correlation is the ceiling for the whole architecture→defects line.** No study was found in which
  architecture-conformance *enforcement* was the intervention and a *defect count* was the outcome
  (searched negative) [83]; the only candidate that could close it (Knodel et al., ICSM 2008) has a paywalled body
  and is available only as a secondary description [64][83]. The two intervention studies that did measure post-detection outcomes are near-null on
  *violations*, let alone defects (§3.6) [62][63].
- **Single-author-group results must be labelled.** The entire per-family anti-pattern impact gradient traces
  to the Mo/Cai/Kazman group [13]. No independent replication was found (search-scoped) [81].
- **A negative is a result.** This review names them (§3.6), because a well-documented failure is the most
  useful thing in the corpus for a project choosing where to spend a year [59][60][61][62][63][74].

---

## 2. Q1 — The application space

### 2.1 Master ranking (defensibility × cost)

Rows = candidates, including yours. "Decision-anchored?" asks whether the application needs the *decision*
layer or would work on a bare dependency graph. Cost is time-to-first-defensible-result for a small team with
the graph and constraint engine already working (cost estimates are the researcher streams' own, in the T1 note
unless otherwise cited) [79][83].

| # | Application | Decision-anchored? | Evidence bucket | Cost | Rank |
|---|---|---|---|---|---|
| 1 | **Settled-decision re-introduction detection** (memory-only) | **Yes — memory-only** | B/C adjacent [55][78], **D** for the ADR case [83] | **Days** [79][83] | **★ Rank 1** |
| 2 | **Dead-dismissal / vacuity detection** (memory-only) | **Yes — memory-only** | **B** in adjacent domain (observational anchors, no control arm) [52][53]; **D** for ADR [83] | **Days** | **★ Rank 1** |
| 3 | **Security-labelled constraint + foreign oracle** | Yes (route→auth is a decision) | B descriptive [29][30][39]; **D** for controlled [82] | 2–3 weeks | **★ Rank 2** |
| 4 | Change-impact analysis | Partly — the graph does it; the ADR filter is the delta | **A** (prediction, non-decision) [65]; **B** (architecture→error-prone) [5] | 1–2 weeks | 4 |
| 5 | Code-review routing from violation memory | Yes (who dismissed/superseded) | **A** (routing, non-architectural) [66]; **D** (memory arm; [58] is the occupying prior art, not the negative's evidence) [79] | 2 weeks | 5 |
| 6 | Onboarding — decision-history digest | Yes | **B** (survey/SLR) [75][76] | 1–2 weeks | 6 |
| 7 | Release-risk ledger | Yes (weakly) | **B** (single case study) [70] | 1 week | 7 |
| 8 | Architecture-evolution forecasting (next violation) | Yes | **B** [28] | 1–2 weeks | 8 |
| 9 | Decision archaeology / drift timeline | Yes | **D** timeline [83]; retrieval-layer evidence only [54] | Days | 9 |
| 10 | Test selection / regression prioritisation | Partly | **A** (RTS) [68]; **D** (decision-anchored) [79] | 3–4 weeks | 10 |
| 11 | Documentation generation from decisions | Yes | **A** (template comprehension) [71]; **C** (ADR→quality) [72] | 2–3 weeks | 11 |
| 12 | **(a) decision-anchored bug localization** | Yes | **B** [5]; **D** for the decision delta [80]; prior art exists [11][12] | **6–10 weeks** | 12 |
| 13 | **(b) anti-pattern families from the graph** | **No** (decision layer unused) | **B** [13]; **D** for "adding them helps" [81] | 4–6 weeks | 13 |
| 14 | Audit-trail / regulatory-evidence bundling | Yes | **D** peer-reviewed [79] | 2 weeks | 14 |
| 15 | **(d) decision-guided migration / upgrades** | Yes | **B** descriptive [41][45]; **D** controlled [82]; scope mismatch [40] | 6–10 weeks | 15 |
| 16 | Deprecation/EOL impact of decision-anchored deps | Yes | **D** [79][77] | 1 week | 16 |
| 17 | AI-authored-code provenance gating | Yes | **B** (AI-TD) [79]; **D** (decision-anchored) | data-blocked | 17 |
| 18 | CI gating policy | Yes, but gameable | **C** — most negative lane [59][74] | n/a | ✗ |
| 19 | Incident / root-cause analysis | **No** — needs runtime graphs | **A** (runtime) [69]; **D** (static ADG) | n/a | ✗ reject |
| 20 | Supply-chain / dependency-risk | **No** — needs cross-package reachability | **D** [83]; not differentiating [73] | n/a | ✗ reject |
| 21 | Fault-tree / blast radius for SRE | **No** — runtime only | **D** [83] | n/a | ✗ reject |
| 22 | Architecture-informed fine-tuning data selection | No evidence | **D** [79] | n/a | ✗ reject |
| 23 | Architecture-aware code search | No decision anchor found | **D** [79] | n/a | ✗ reject |

### 2.2 Applications you did not list — the discoveries

Full detail in the T1 research note (§3, D1–D12) [79] and T5 (§T5.3, M1–M6) [83]. The load-bearing ones:

**A. Settled-decision re-introduction detection (memory-only).** A violation that was dismissed or fixed, and
that reappears later on the same predicate + FQN identity key. No stateless linter can say this. Prior art:
`projectmem` ships "a deterministic pre-action gate that warns an agent before it repeats a previously failed
fix" (self-reported, 10 projects / 207 events) [55]; vulnerability re-introduction has been measured in
ImageMagick (76 instances) [78]; warning-evolution tracking exists [56]. **No study of ADR-violation re-introduction was
found within this review's searches** [83]. Cheapest first result: replay history and count re-introductions, with
a survival curve of dismissals [79]. Precedent for the claim shape: 86.7% of exclusions still in force after three
years in a different domain (Exclusion Ratchet, SigmaHQ, 8,234 revisions) [53].

**B. Dead-dismissal / vacuity detection (memory-only).** What fraction of live dismissals suppress nothing
currently detectable? This is the memory layer auditing itself [83]. The external anchor is unusually strong and
directly comparable: **50.8% of 7,357 suppressions across 46 Python projects "do not affect any warning and
hence are practically useless"** (FSE 2025, DOI 10.1145/3715729 — verified verbatim) [52], and ArchUnit's own
issue tracker documents ">70 freeze files in the stored.rules" with orphaned/stale references [57] (the freeze mechanism is documented in the ArchUnit user guide [18]). A ~50% expected effect size makes
a first result interpretable rather than exploratory [83].

**C. Decision-regression as a new dependent variable.** Your memory already distinguishes *introduced*,
*dismissed*, *superseded* and *re-introduced* [1]. No reviewed study uses re-introduction of a settled decision as
a DV [83]. This is a measurement contribution available for free once (A) is instrumented, and it composes with
every other candidate (review routing, migration, agent context) as the one outcome that isolates memory [83].

**D. Decision-drift / supersession timeline.** Emit the supersession DAG: chain depth, time-to-supersede, how
many live ADRs are superseded-but-still-checked [83]. MOOSEDev (self-reported system, single-source) shows
supersession-aware retrieval is measurably
better than vector top-k (0.98–1.00 vs 6–27% on 835 typed records) [54] — evidence that supersession structure
carries real signal, though that is retrieval, not an architecture application [83].

**E. Reviewer routing from violation memory.** EASE 2023 already recommends reviewers for architecture
violations using commit path similarity + review-comment semantics, beating RevFinder [58]. The unoccupied delta
is narrow but real: route on **who dismissed/superseded this predicate before** [83] — the memory adds who *acted*,
not who *commented* [58].

**F. Release-risk ledger, onboarding digest, audit-evidence bundle, deprecation impact.** Each passes the
inclusion test but each has a weakness that should be stated up front: release risk has no agreed operational
definition and only one single-case-study anchor [70]; onboarding is measurable (a small controlled experiment is
feasible) but the evidence base is survey-level [75][76][79]; no peer-reviewed study of generating audit
evidence from a decision graph was found within this review's searches (vendor grey literature only) [79]; deprecation impact is at risk of being "`pip-audit` plus a join" [77][79].

### 2.3 Considered and rejected

- **Incident / root-cause analysis.** Published RCA uses *runtime* service call graphs with timings, errors
  and traces (TORAI, FSE 2026: 270 failure cases, 3 systems, 10 real incidents, 9 baselines — and its premise
  is that call-graph RCA fails on *blind spots*) [69][79]. A static CONTAINS/IMPORTS/CALLS/INHERITS graph carries none
  of those signals. Presenting it as an analogue would be a category error. **Reject.**
- **Supply-chain / dependency-risk.** The measured value-add over SCA is **cross-package call-graph
  reachability** — on 3M Maven packages, "less than 1% of packages have a reachable call path to vulnerable
  code in their dependencies, far lower than a naive dependency-based analysis" [73] (single-source) — and that
  graph must span
  package boundaries, which the ADG does not [83]. `requires_dependency` / `prohibits_dependency` are policy
  checks over a dependency list that is already the SBOM/SCA artefact [83]. One narrow exception exists (intra-repo
  blast radius at FQN granularity when a package is compromised), but a plain import graph gives the same
  computation [83]. **Reject as a differentiator.**
- **CI gating policy.** The most negative lane in the sweep: a 12-month industrial case study found CD
  adoption "did not favor the quality of source code" [74]; Lenarduzzi SANER 2020 found SonarQube's bug-labelled
  rules generally not fault-prone with "extremely low" predictive power [59]; and in an agentic loop a gate is
  gameable (move the import into the function, use `importlib`, a `TYPE_CHECKING` guard) [39][82]. **Reject as a
  headline; keep only as an oracle placement.**
- **Fault-tree/SRE blast radius, fine-tuning data selection, architecture-aware code search.** No anchoring
  evidence; each competes with a crowded literature for an ill-defined gain [79][83]. **Reject.**

---

## 3. Q2 — The evidence, candidate by candidate

### 3.1 Candidate (a) — decision-anchored bug localization

**What is verified (primary sources read this run).**

- **ICSE 2014 (Xiao, Cai, Kazman, *Design Rule Spaces*, DOI 10.1145/2568225.2568241) [5].** Verbatim §5.3: "by
  looking at just the top 5 DRSpaces we do nearly as well: we can cover from **52% to 89%** of a bug space."
  Table 5 cells: JBoss 57/52/78, Hadoop 59/68/76, Eclipse 71/83/89 (Bug2/Bug5/Bug10) [5]. Three **Java** systems
  (JBoss, Hadoop Common, Eclipse JDT), one target release each [5].
- **ICSE-SEIP 2015 (Kazman et al., *A Case Study in Locating the Architectural Roots of Technical Debt*,
  DOI 10.1109/ICSE.2015.146) [6].** Title correction: it is not "Architectural Roots" [6][80]. Verbatim: "only **6** root
  spaces are needed to cover **89%** of the Bug2 space, and **7** root spaces can cover **92%** of the
  Change10 space" — so the 92% figure needs **7** spaces, not 6 [6]. Titan vs Sonar: precision **31% vs 18%**
  (Bug2 oracle) and **40% vs 27%** (Change10); recall 53% vs 33% and 60% vs 41% [6]. n = **1** industrial project
  (797 files, 55 Bug2 / 63 Change10 files) [6]. Titan is the toolset the SEIP paper names [6]; it was introduced in
  its own FSE 2014 tool demo [10].
- **A caveat your summary omits:** the paper itself says "the precision numbers reported here are low because
  of the small sizes of Bug2 and Change10 … the highest possible precision value for Bug2 would be about 57%
  and the highest possible precision value for Change10 would be about 66%." [6] Titan at 31% against a 57%
  ceiling is a much smaller story than "31% vs 18%" alone [6].

**What is wrong or missing in the candidate as stated.**

1. **The prior art is not cited.** Architecture-model-driven fault localization predates DRSpace by five
   years: FLABot / Soria, Díaz Pace, Campo (CSMR 2009) [11] and its journal version (Expert Systems 32(1), 2015) [12]
   evaluated a prototype **with and without** the tool across two medium-size case studies, measuring time,
   code browsed, and faults found [12]. That is the bucket the candidate implicitly claims is empty [80].
2. **The evidence supports the wrong claim.** The DRSpace line supports **P**: "architecturally-connected
   groups capture the files that are error-prone" — correlational [5][80]. The candidate is **Q**: "a bug can be
   localized to a group implied by a recorded *decision*". P does not entail Q. Q is a **search-scoped
   negative** (13 queries, 6+ angles) and should be phrased that way [80].
3. **Label leakage in the headline number.** The ICSE 2014 candidate pool is the **30 most error-prone files
   in each project**, from which DRSpaces are selected and then scored for coverage of the error-prone set [5][80].
   The 52–89% is real but must always be quoted with the candidate-pool construction **and the group sizes**
   (the SEIP top space is 139 files; three spaces union to 291 of 797 files ≈ 37% of the project) [6]. Coverage
   of a large file set is a much weaker claim than a ranking metric like Hit@10 = 62.6% over 12,863 files [23].
4. **The nearest analogue is partly negative.** Smell-aware bug localization (Bench4BL, 309 systems) [25] is the
   one controlled ablation in this space: **α = 0 was optimal in 49 of 224** systems ("any blending of
   smell-based scores reduced the accuracy"), and where it helped the mean optimal α was **0.215** [25] and the
   improvement "slight" [25]. This is about the *intervention class*, not the decision anchor, but a reviewer will
   use it [80].

**Grade: B (primary, correlational) + D (the decision-specific delta) + an un-cited A-ish prior art (FLABot) [5][80][11][12].**
**Single-source note:** the DRSpace/ArchDebt line is one author group [5][8][9]. **Competitive frame:** the classic IR
band is Hit@1 ≈ 29–40%, Hit@10 ≈ 59–82%, MAP ≈ 0.22–0.45 (BugLocator 2012 [23]; AmaLgam 2014 [24]); LocAgent (ACL
2025) reaches up to 92.7% file-level on Loc-Bench [26]; MULocBench (1,100 issues, 46 Python repos) has SOTA Acc@5
**below 40%** [27].

### 3.2 Candidate (b) — architectural anti-pattern / risk detection from the graph

**First, a taxonomy correction.** Your family list mixes three taxonomies. The Mo/DV8 line has exactly **six**
families: Unstable Interface, Modularity Violation Group, Unhealthy/Improper Inheritance, Crossing, Clique,
Package Cycle [13][15]. "God Component", "Feature Concentration", "Hub-like Dependency", "Dependency Cycle" and
"Unstable Dependency" are **Arcan/Designite** smells [16], and Martin instability/abstractness/distance is a
package-metric family [17]. No published study ranks Arcan's smells against Mo's families [81]. Also, "TSE 2019
DOI 10.1109/tse.2019.2910856" and "TSE 2021 47(5)" are **one paper** (DOI year = early access) [13].

**Computability (verified against definitions and DV8 docs) [13][15].**

| Family | Needs | Verified threshold |
|---|---|---|
| Unstable Interface | fan-in hub **AND** co-change (hybrid) | DV8 defaults `uiCochange` 2, `uiStructImpact` 0.01; paper used StructImpact 10, cochange 2 [13][15] |
| Crossing | fan-in **AND** fan-out **AND** co-change (hybrid) | DV8 `crossingFanIn` 4, `crossingFanOut` 4, `crossingCochange` 2 [13][15] |
| Modularity Violation Group | **history-only** (absence of structure + co-change) | `mvCochange` 2 [13][15] |
| Unhealthy Inheritance | **pure graph** | `uihDepends`, `uihInheritance` [15] |
| Clique | **pure graph** (SCC) | `cliqueDepends` [15] |
| Package Cycle | **pure graph** | none [13][15] |

DV8's own tooling confirms the split operationally: with history data it detects all six; **without history,
three** [15].

**The asymmetry claim, adjudicated.** *(Verdict: **overstated** — the ordering is supported, the mechanism is
wrong.) [13][14][15]*

- **Ordering: supported, single-source.** TSE 2021 §5.5 verbatim: "Unstable Interface and Crossing have the
  largest impact, and Package Cycle has the smallest impact." [13] Subjects: **19 projects — 15 Apache (all Java)
  + 4 commercial (all C#)** [13]. **No Python** [13].
- **"Need co-change/history edges": wrong as stated.** UIF = *(# dependents > threshold)* **AND** *(those
  dependents co-change)*; Crossing = *(fan-in > 4)* **AND** *(fan-out > 4)* **AND** *co-change on both sides* [13][15].
  Both have a **pure-graph structural half** — a fan-in hub, and a fan-in+fan-out hub. DV8 says these patterns
  need "**both** structural relation and co-change information" [15]. History promotes a hub to a finding; it does
  not create the candidate [13].
- **The 2015 predecessor had a pure-structure family at #2.** WICSA 2015 (same group) found "the greatest
  impact … is attributable to **Unstable Interface and Cross-Module Cycle**" [14], and its Discussion states only
  *Unstable Interface* and *Implicit Cross-module Dependency* "crucially depend on … evolution history" [14].
  **Cross-Module Cycle is pure `depend` + module clustering** [14]. So the honest shape is *"hybrid > pure-graph"*,
  not *"history-dependent > pure-graph"* [81].
- **The ranking is metric-convention-sensitive.** The T3 note's own re-derivation from the published tables
  reproduces the paper's order under the **absolute** measure (CRS > UIF > CLQ > MVG > UIH > PKC) but **not**
  under the published relative-increase metric (which puts MVG above UIF) [13][81]. The prose ranking survives only
  under one convention. Additionally, p-values test *difference*, not *direction* [13], and the effect sizes
  against PKC are not unique to UIF/Crossing (UIH↔PKC 0.88–1.00 is comparable to UIF↔PKC 0.74–0.98) [13][81].
- **Counter-evidence on "cheapest = least impactful".** On other dependent variables, independent groups rank
  the cycle family **first**: practitioners' **refactoring cost** (ECSA 2018 — "Cycles first, followed by
  Hublike Dependencies, then Unstable Dependencies") [20] ranks it first unambiguously; smell **survival**
  (EMSE 2022, 9 industrial C/C++ projects — cyclic dependencies have the lowest survival) [19] is
  metric-ambiguous, because low survival can mean "removed soonest" as easily as "most harmful". The cost
  evidence undercuts a "cycles don't matter" reading; the survival evidence does not settle it [81].
- **DV8/Titan itself excluded cycles from the industrial comparison** — verbatim from SEIP 2015: "We did not
  report the most commonly found architecture problems, such as cyclical dependencies … because those issues
  can be easily detected by the commercial tools SoftServe is already using, such as Sonar or Structure101." [6]
  That is a *practitioner-usefulness* judgement, not an impact measurement, and it should be quoted as such [6].

**Grade: B for the gradient; D for "adding these families improves outcomes". [13][81]** Correlational, single author
group [13], Java + C#, ticket-ID bug linkage (not SZZ) [13], four proxy measures for effort [13], analyst-set thresholds with
unresolved sensitivity [14], and non-uniform per-family increases (Implicit Cross-module Dependency has *negative*
increases on some measures for Avro, Ivy, OpenJPA, PDFBox) [14][81]. **No Python replication of the six-family
gradient was found (search-scoped) [81].** The only intervention design found (ICSA 2026, refactoring architectural
smells → quality/security/performance) had its numbers blocked (publisher HTTP 403) [22] — the single most
consequential gap in this slice [81].

### 3.3 Candidate (c) — security framing

**Prior art: named, implemented, measured — twice, twelve years apart.**

| Named concept | Source | Status |
|---|---|---|
| **"authorization context consistency"** — "consistently enforces its authorization checks across the code" | MACE, CCS 2014 [29] | full text read [82]; found real vulnerabilities in **5 of 7** apps [29] |
| Route-level static check with CWE labels | AuthCheck, 2019 [30] | full text read [82]; "if no filter is specified, this is equivalent to `permitAll()`" [30]; detects CWE-306/862/863 [30]; evaluated by **injecting** faults [30]; precision deferred to industry [30] |
| Sibling-route comparison in Python/FastAPI | `enforcement-coverage` (2026) [39] | self-reported: 2,568 routes → 4 findings, 2 true positives (one CVE-2026-45316), 2 false positives; **≥72% "unknown"**; only **1 of 5** repos had a permission vocabulary supporting strength comparison [39] |

The problem class has a standards name — A01:2021 Broken Access Control [31] and, for the function-level variant,
API5:2023 Broken Function Level Authorization [32] — and 15 years of static-analysis papers [29][30][39][82].

**The only candidate novelty this review could support is the substrate** — and that is a search-scoped
negative, not a novelty proof: a reachability/dependency predicate over an architectural import graph plus
persistent decision memory was **not found within this review's searches** [82]. Even that is close to the shipped sibling-consistency heuristic [39][82].

**Evidence:** A01 has 34 mapped CWEs, average incidence 3.81%, max 55.97%, avg coverage 47.72%, 318,487
occurrences and 19,013 CVEs in the OWASP-contributed dataset [31]. Detection tools find real instances (MACE 5/7 [29];
ACtests 168 new vulnerabilities across 72 configuration images, 54 confirmed / 44 fixed [34]; BACFuzz 16/17 known
and 26 previously unknown [35]; a CCS 2024 study analysed 101 real-world BOLA vulnerabilities [36]). **No controlled
study was found that introduces architectural/static enforcement of a route→authorization constraint and
measures a reduction in A01 incidence against a control arm (search-scoped) [82].** Grade: **B descriptive** [31][29][34][35][36], with
**C-adjacent** partial failures (AuthCheck's injected-fault evaluation [30]; the Python tool's abstention and
inline-enforcement blind spot [39]), and **D** for the controlled claim [82].

**The framing verdict (this is the important part).** Security is better as an *evaluation strategy* than as a
*positioning strategy* [82]:

- **Keep:** an external, third-party oracle exists (runtime/differential authorization testing) [34][35] — the only
  candidate in the whole space with a foreign ground truth [82]. That is worth more than the framing [82].
- **Drop:** "security control" / "by construction". A route→auth-module import edge is neither necessary nor
  sufficient for per-request enforcement: the edge can exist without the control (`TYPE_CHECKING` guard,
  `importlib`, unused import, wrapper) [39][82], and the control commonly lives **inside the function body** [39][82]. A01's
  dominant real-world sub-classes — IDOR/BOLA, force browsing, JWT/metadata manipulation — are invisible to
  route-level presence [31]. And DRF defaults to `AllowAny`, so secure-by-default is a configuration fact, not an
  architectural one [33].
- **Adjacent calibration:** a CodeQL longitudinal study over 114 versions, 3,993 CVEs and 1,622 repos found
  CodeQL detected 171 CVEs [37], that 21 were no longer detected after a version change and 17 were never
  redetected [37]; a systematic review of 246 static security analyzers concludes the vulnerabilities they detect
  "are rarely exploitable" [38]. **Do not write "static/architectural enforcement reduces access-control
  incidence" on this base [82].**

### 3.4 Candidate (d) — decision-guided migration / library upgrades

- **The anchor is a scope mismatch.** Pigazzini, Arcelli Fontana, Maggioni, ECSA 2019
  (DOI 10.1007/978-3-030-29983-5_17) is **monolith→microservice decomposition** for Java, not library
  upgrade [40]. Whether it actually uses Arcan is `inherited, not re-verified` (paywalled) [40][82].
- **The JabRef anchor is real but different.** Olsson et al., **ECSA 2017 Companion** (not 2019): a
  single-project before/after observation in which "large files with violations had a significantly higher
  code churn"; after refactoring, churn normalised [41]. The refactoring and the SACC introduction happen
  together, so the causal attribution is confounded [41][82]; it is churn↔violations, not decision-guided migration [82].
- **The hard part is execution, not navigation.** MigrateLib (2026) migrates **32%** of migrations with
  complete correctness across 717 real Python applications [44]; CodeMEnv LLM pass@1 averages **26.50%** [43]. And
  practitioners already do the obvious thing: in an ICSA 2018 industrial survey (n=18), the criterion for
  the first module to migrate was "**less dependencies**" (6/18), architecture-recovery tools were used by
  **1 of 18**, and the top challenge was coupling (9/18) [45] (the T4 note's Findings summary says 13/18;
  its Table XII says 9/18 — the table value is used here).
- **Grade: B descriptive; D for any controlled claim [41][45][82].** Benchmarks exist and are Python-usable
  (PyMigBench-2.0: 3,096 changes / 335 migrations / 141 library pairs [42]) but carry **no ADR linkage**, so the
  memory's contribution has no ground truth out of the box [42][82].

### 3.5 Your process list, graded

| Application | Bucket | The one line that matters |
|---|---|---|
| Change-impact analysis | **A** (prediction) [65], **B** (arch→error-prone) [5] | Athena FSE 2024 has an ablation (+10.34/9.55/11.68 pp, statistically significant) but mAP 35.19 [65] — two-thirds of truly impacted methods missed [65]. Athena owns the non-decision task; only the *ADR filter* is the delta [79]. |
| Code-review routing | **A** (routing) [66], **B** (arch awareness) [67] | Meta ran 3 RCTs (82k/28k/12.5k units) with guardrail nulls **and** a −4.90 pp workload regression [66][79]. Feature importances are authorship/review-history, **not architecture** [66]. Paixão TSE 2021: architecture discussed in only **31%** of reviews (7 systems), and *decreased* in 33% of cases where feedback was given [67]. |
| Test selection / RTP | **A** (RTS) [68], **D** (decision-anchored) [79] | STARTS ASE 2017: 840 versions / 32 projects, 35.2% of tests selected, 81.0% of RetestAll time [68][79]. But RTS has a documented adoption gap [79] and the only DV that matters — **missed faults** — is nearly absent from the literature [79]. |
| Incident / RCA | **A** (runtime) [69], **D** (static) [79] | TORAI FSE 2026 (270 cases) exists *because* call-graph RCA fails on blind spots [69][79]. Static ADG has no timing/error signal [69][83]. |
| Supply-chain | **D**, not differentiating [83] | `<1%` of 3M Maven packages have a reachable path to vulnerable code [73]; that computation needs cross-package call graphs [83]. |
| Onboarding | **B** [75][76] | 147-developer survey (docs absent or inadequate) [75]; onboarding SLR [76]. No controlled ADG/ADR delivery study found [79]. |
| Documentation | **A** (template comprehension) [71], **C** (ADR→quality) [72] | Nygard-vs-MADR controlled experiment (undergraduates) is the only clean bucket-A result and it is about format comprehension [71]. An ICSA 2026 study of 921 repos / 5,800 ADRs (single-source, conference-program abstract — treat as provisional) found ~63% opened directly as "accepted" and "predominantly small correlations" with quality metrics [72]. |
| Release risk | **B** [70] | One WICSA 2015 industrial case study (self-evaluated, no baseline, "useful and easy to use") [70]. No architecture-anchored release-readiness predictor found [79]. |
| CI gating | **C** [59][74] | CD adoption "did not favor the quality of source code" [74]; SonarQube bug-rules not fault-prone [59]. |
| Refactoring planning | **B** [6][7] | SEIP 2015 economic model (291 files, 0.82 vs 0.33 bugs/file [6][7]) is assumption-driven; **single-source caveat:** the 0.82 bugs/file figure comes only from the SEI blog, whose project-level and DRSpace-level change totals are both stated as 2,332 (an apparent duplication in a secondary source) [7][79]. No controlled trial found [79]. |
| Agent context selection | mixed | See §3.7 and the T5 note [83]. |

### 3.6 The negatives, named

**Negative and conflicting results.** Bucket **C** (tried and failed) unless a row is marked otherwise. The
rows marked *conflicting* are **not** C — they report a different ordering on a different dependent variable.
These are results, and they constrain what you can claim.

| Study | What it tested | Result |
|---|---|---|
| Lenarduzzi et al., SANER 2020 (arXiv:1907.00376) [59] | SonarQube rule violations vs SZZ-labelled faults, 21 Java projects [59] | Of 202 rules, only **25** relatively fault-prone; violations labelled "bugs" "generally not fault-prone"; predictive power "extremely low" [59]. |
| Sultana et al., arXiv:2010.15978 [61] | Code + architectural smells vs vulnerabilities (Tomcat, CXF, Android) [61] | **"No significant relationship between architectural smells and software vulnerabilities."** Code smells did correlate; architectural ones did not [61]. |
| Tamburri et al., arXiv:2303.17862 [60] | Architectural smells vs concurrency bugs, 125 releases / 5 systems [60] | "Smells are **not correlated with concurrency** in general." Title says *Negative Results* [60]. |
| Smell-aware bug localization (309 systems) [25] | Blending smell score into IR localization, α sweep [25] | **α = 0 optimal in 49 of 224** systems; where it helped, mean optimal α = 0.215, "slight" [25]. *C-adjacent, not a full null — see §3.1.* |
| Sas et al., EMSE 2022 (arXiv:2203.08702) [19] | Smell **survival**, 9 industrial C/C++ projects [19] | Cycles die fastest — *conflicting*, **not C**; and metric-ambiguous, since low survival can mean "removed soonest" as easily as "most harmful" [19]. |
| Martini et al., ECSA 2018 [20] | Practitioner refactoring **cost** ranking [20] | "Cycles first, then Hublike Dependencies, then Unstable Dependencies" — *conflicting ordering on a different metric*, **not C**; this one is unambiguous [20]. |
| DiVA maintainability study [21] | ASAT smells vs modularity/testability, 8 OSS projects [21] | "Contrary to expectations … generally no negative correlation" at project level except Dense Structure [21]. |
| 12-month CD case study [74] | CI/CD adoption vs source quality [74] | "Did not favor the quality of source code" [74]. |
| ICSA 2026 ADR study [72] | ADR attributes vs project quality, 921 repos / 5,800 ADRs [72] | "Predominantly small correlations"; ~63% of ADRs opened directly accepted [72]. |

**The two intervention near-nulls (the most important negatives in this report).**

- **Buckley et al., IST 2015 (DOI 10.1016/j.infsof.2015.01.011), five systems, four financial-services
  organisations [62].** Verbatim: "(at least) four months after the Reflexion Modelling sessions **less than 50%
  of the architectural violations identified were removed**"; "some had removed none"; "identification of
  architectural violations in itself does not lead to their removal in the majority of instances." [62] Where
  action was taken, it was more often to change the architecture model than the code [62].
- **Caracciolo et al., IWESEP 2016** (7th Int'l Workshop on Empirical Software Engineering in Practice, DOI
  10.1109/IWESEP.2016.12), **three industrial case studies [63].** C2: 270 violations — 27 critical fixed,
  158 tracked, **85 not fixed** [63]. C3: over two months the total went **606 → 600** (10 introduced, 16 removed) [63].
  No defect outcome reported [63].

These do not refute a defect benefit; they remove the mechanism by which one would arise [83]. **No study was
found in which architecture-conformance enforcement was the intervention and a defect count was the outcome
(search-scoped) [83].** The nearest is Knodel et al., ICSM 2008 (paywalled; only a **secondary** description
retrieved) [64][83], which shows that *having* an eroded version makes an evolution task harder in effort and
correctness — a causal claim about violations as an input, not about enforcement as an intervention [64][83].

### 3.7 Searched negatives (search-scoped, labelled)

All of the following are "not found within this review's searches", not existence claims [79][80][81][82][83]:

1. Decision/ADR-anchored bug **localization** (13 queries, 6 angles) [80]. Architecture-model-driven localization
   **does** exist (FLABot) [11][12].
2. A published treatment of a security control as a **reachability predicate over an architectural import
   graph with persistent decision memory** [82].
3. A **controlled** study of route→authorization enforcement reducing A01 incidence [82].
4. A **Python** replication of the six-family anti-pattern impact gradient [81].
5. A study where **architecture-conformance enforcement** reduces defects [83].
6. **ADR-violation re-introduction** as a measured phenomenon [83].
7. The **direct** agent-context experiment in its exact Shepherd form (architectural predicates + deterministic
   analyzer oracle) [83]. The general phenomenon is now studied: arXiv:2605.08112 (2026-04-27) reports decision
   compliance 46% → 95% on 8 tasks / 41 decision points, but it is vendor-authored, unrefereed, and injects
   *product* decisions [47]. Two adjacent 2026 preprints exist (architecture-spec format for coding agents [48];
   `AGENTS.md` context files, a **null** bounded to ≤10–15 pp by equivalence testing [49]).
8. A **negative result specific to architecture-graph-guided migration** [82].
9. The **ICSA 2026 refactoring intervention** numbers (publisher 403) — the only intervention design found for
   the anti-pattern families [22][81].

**A finding that changes the agent-context design.** The "redundant context hurts" premise is real but the
mechanism is contested [83]. CodeRAG-Bench's gold-docs result is verified (GPT-4o DS-1000 52.7 → 51.2) [46] — but the
same table shows gold documents *helping* elsewhere (HumanEval 75.6 → 92.6; SWE-bench 2.3 → 30.7) [46]. A 2026
preprint found an **equal-length irrelevant** context performed the same as a *relevant* one (3/10 vs 3/10,
Fisher p = 0.0698, clean condition 8/10) [50], i.e. the damage tracked **length, not relevance** [50]; and with oracle
localization on 70 SWE-bench Verified instances, rendering a file's remainder as UML skeletons was
indistinguishable from **deleting** it (McNemar p = 0.754) [51]. Consequence: the "relevance-selected injection"
claim needs a **length-matched placebo arm** before it means anything [50][83].

---

## 4. Q3 — Ranked recommendation: where to settle

### 4.1 The ranking, and why

| Rank | Candidate | Defensibility | Cost to first result | Why here |
|---|---|---|---|---|
| **1** | **Memory-layer measurement** (settled-decision re-introduction + dead-dismissal rate) | Medium-high — novel DV [83], external anchor effect sizes [52][53], uses the actual moat; risk = descriptive + base rate [83] | **Days** [79][83] | The only candidate that needs nothing new: no model, no benchmark, no annotation, no agent. Both parts are retrospective measurements on data already persisted [83]. No prior study of ADR-violation re-introduction was found within this review's searches, and the external
anchor (~50%) makes the number interpretable [52]. |
| **2** | **Security-labelled decision constraint, evaluated against a foreign oracle** | Medium-high — mechanism is prior art [29][30], but the **external adjudicator** is unique in this whole space [82] | 2–3 weeks [82] | Buys the one thing nothing else has: a third-party ground truth (differential/black-box authorization testing) [34][35] and a standards label set (CWE-862/CWE-306) [30]. Framed as compliance-with-security-payload, not "by construction" [82]. |
| **Gate** | Decision-vs-structure ablation (not an application) | — | 1–2 weeks [80] | Cheap enough to run before committing to anything expensive [80]. If decisions add nothing over a size-matched structure-only grouping on the same bugs, (a) and (b) are dead. It does **not** test Rank 1's re-introduction DV or Rank 2's route→auth constraint — those need their own arms [80]. |

### 4.2 Rank 1 — cheapest defensible first result and evaluation

**The claim.** *"Across N Python repositories, X% of predicates that were dismissed or superseded are
violated again later (decision regression), with a median time-to-reintroduction of T commits; and Y% of live
dismissals suppress no currently-detectable violation (dead dismissals)."* [83]

**Why this is the cheapest defensible result in the whole space.** It is ledger arithmetic over the existing
memory: for each dismissal/supersession, replay the history and check whether the same predicate + FQN
identity is violated again [83]. No new graph edge, no labels, no LLM, no annotation. The T1 note estimates it
under a day [79]; the T5 note calls it "the best first result in the whole slice." [83]

**Evaluation.**
- **Data:** the five repos in the ingestion benchmark (openlobby, tuf, tamr, flask, django) [1] **and** the five
  ADR-bearing gold repos (experimenter, flowkit, home_assistant, python_tuf, structurizr) [4] — note these are
  **two different five-repo sets**; count dismissals on whichever set actually carries them — plus any further
  Python repos with ADRs you can ingest. Report
  per-repo cells, not only a pooled number [79].
- **DVs:** (i) re-introduction rate; (ii) survival curve of dismissals (Kaplan–Meier, as the Exclusion Ratchet
  does) [53]; (iii) dead-dismissal fraction; (iv) distribution of dismissal scope (predicate-only / FQN-scoped /
  repo-wide) [83].
- **The comparison that makes it more than descriptive:** compare the re-introduction hazard of
  *dismissed/superseded* predicates against a **matched control set of predicates that were never dismissed**
  (matched on node fan-in, churn, age) [83]. If a prior dismissal does not raise the hazard of re-introduction,
  the DV is measuring noise, and that is the finding [83].
- **External anchors to interpret against:** 50.8% of 7,357 suppressions affect no warning (FSE 2025) [52];
  86.7% of exclusions still in force at three years, 31% of narrowing invisible to structural comparison
  (Exclusion Ratchet) [53]. State these as *different domains* — they calibrate the expectation, they do not
  confirm it [83].
- **Minimum n:** report exact counts, not rates, below 30 events [83]. If dismissals/supersessions are too few on
  5 repos, say so — that is itself the finding [83].

### 4.3 Rank 2 — cheapest defensible first result and evaluation

**The claim (scope it exactly).** *"On N Python repositories, a route→authorization dependency constraint
recovered X of Y adjudicated missing/weakened-authorization routes at the merge commit that introduced each
one, with precision P and recall R, versus an AST-body baseline and a decorator-grep baseline."* [82] This is a
**detection/localization** claim about a security-labelled failure class. It is **not** "we prevented broken
access control" [82].

**Evaluation.**
- **Corpus:** 5–8 Python repos with a single explicit authorization idiom (FastAPI `Depends(...)` /
  router-level `dependencies=[...]`; Django `permission_classes` / `login_required`) [82]. The Python tool's
  experience is the binding constraint: five repos needed five extractors, and only one of five had a
  permission vocabulary supporting strength comparison [39] — so budget one extractor per repo [82].
- **Unit of analysis:** every commit that adds or edits a route handler (that is where the defect is created) [82].
- **Labels:** two-rater adjudication into {properly enforced, missing, weakened, different sufficient control,
  **unknown**}; report Cohen's κ [82]. "Unknown" must be an explicit reported outcome — the Python analogue
  abstained on ≥72% of routes [39].
- **Arms:** (A) ADG constraint (`requires_dependency(app.routes.*, <auth module>)`, plus a sibling-consistency
  variant); (B) AST check that the handler body/signature references an authorization symbol; (C)
  decorator-name grep [82].
- **DVs:** precision, recall, and **time-to-first-detection** (flagged at the introducing commit vs only at
  HEAD), with Wilson intervals; paired comparison against B and C [82].
- **Minimum n:** ≥5 repos, ≥50 adjudicated route-change events, ≥5 positives; below 10 positives report
  counts, not rates [82].
- **Then the two measurements that decide whether the framing survives** (see §5.2): evasion recall and a
  runtime differential oracle on the same corpus [82]. Build them into the first result, not after it [82].

### 4.4 Why (a) and (b) are not the top two

- **(a) has the strongest raw evidence and the worst cost-to-result ratio.** It inherits an un-cited prior art
  (FLABot) [11][12], a label-selected headline (the ICSE 2014 candidate pool) [5][80], a correlational-only base [5],
  a partly negative nearest analogue [25], and the heaviest evaluation in the space (ranked retrieval against a competitive
  IR band [23][24][26][27], over a corpus that does not yet exist — no Python ADR-bearing issue→fix benchmark was found [80]). Its
  defensible first result is **not** a localization system; it is the **ablation** (decision-anchored groups
  vs **size-matched** structure-only groups on the same bugs) [80]. Run that as a gate, not as the flagship [80].
- **(b) is not decision-anchored at all** [81], and its honest expectation is a **null** for the pure-graph
  families [13][81]. A Python replication of the structural/history split is a legitimate paper [81] — but it is a
  replication of a Java+C# correlational result with the decision layer switched off, in a space that already
  has a well-populated negative literature [59][60][61][21]. It scores last on "does this use the project's moat" [81].

---

## 5. Q4 — Strongest objection and killer measurement

### 5.1 Rank 1 — the memory layer

**Strongest objection.** *The dismissals are noise, so re-introductions are noise.* [83] The whole DV rests on
dismissals being meaningful. The adjacent evidence says suppression practice is sloppy: 50.8% of 7,357
suppressions affect no warning at all [52], and ArchUnit's freeze store is documented with ">70 freeze files in
the stored.rules" including references to files that no longer exist [57].
If Shepherd's dismissals are similar, then "re-introduction rate" measures the noisiness of human triage, not
decision decay [83]. There is also a **base-rate** risk: on 5 repos there may be too few dismissals for a survival
curve with any power [83].

**The measurement that kills or confirms it.** A **matched hazard comparison**: for each dismissed/superseded
predicate, sample a control predicate never dismissed, matched on node fan-in, churn and age, and compare the
hazard of subsequent violation [83]. If the hazards are indistinguishable, the DV is noise and Rank 1 must be
withdrawn [83]. A secondary, confirmatory measurement: report the fraction of Shepherd's dismissals that suppress
zero subsequent violations and compare it directly to the FSE 2025 figure of 50.8% [52] — a large deviation in
either direction is itself the finding, and agreement makes the memory layer's triage quality quantifiable [83].

### 5.2 Rank 2 — the security constraint

**Strongest objection.** *The constraint checks a proxy, not the control.* [82] A route→auth-module **import edge**
is neither necessary nor sufficient for enforcement [82]. Not sufficient: the edge can exist without the control
(`TYPE_CHECKING` guard, `importlib.import_module` in a branch, imported and never called, decorator on a
wrapper, middleware registered app-wide) [39][82]. Not necessary: the control commonly lives **inside the handler body**
or in framework configuration — the Python analogue found "216 of 608 handlers carry the decisive check inside
the function", and lists inline enforcement as an explicitly **unsolved** case [39]. And A01's dominant real-world
sub-classes (IDOR/BOLA, force browsing, JWT manipulation) are invisible to route-level presence [31].

**The measurement that kills or confirms it — two of them, both cheap.**
1. **Evasion recall.** Take the adjudicated *violating* routes and mechanically rewrite each into the standard
   Python evasions (`if TYPE_CHECKING:` import; `importlib.import_module(...)` inside the handler; decorator
   re-applied to a wrapper; control moved to app-level middleware; guard moved into a called service). Re-run
   the constraint [82]. **If recall on the rewritten set collapses, (c) is architectural hygiene, not a security
   control, and the framing must be withdrawn** — the detection claim can survive, the "by construction" claim
   cannot [82].
2. **Runtime parity.** Run a differential/black-box authorization oracle (ACtests- [34] or BACFuzz-style [35])
   against *constraint-compliant* vs *constraint-violating* repos and compare failure rates [82]. If compliant
   repos fail at the same rate, the framing is dead regardless of graph accuracy [82].

---

## 6. Correction ledger — your four candidate claims

| # | Your claim | Verdict | The correction |
|---|---|---|---|
| C1 | (a) "top-5 DRSpaces cover 52–89% of error-prone files" (ICSE 2014) [5] | **Correct, with omissions** [5] | Range verified verbatim [5]; but it is a range over 3 Java projects × 3 bug thresholds, the candidate pool is the 30 most error-prone files (label-selected) [5][80], and group sizes must be quoted (three SEIP spaces ≈ 37% of the project) [6]. |
| C2 | (a) "Kazman et al. ICSE-SEIP 2015 ... six root DRSpaces cover 89% of Bug2 / 92% of Change10" [6] | **Half wrong** [6] | Title is *"A Case Study in Locating the Architectural Roots of Technical Debt"* [6]. 6 spaces → 89% of Bug2, but **7** spaces → 92% of Change10 [6]. n = 1 project [6]. |
| C3 | (a) "Titan precision 31%/40% vs SonarQube 18%/27%" [6] | **Correct, needs the ceiling** [6] | Verified verbatim [6]; the paper states achievable precision ceilings of ~57% (Bug2) and ~66% (Change10) [6]. |
| C4 | (a) "decision-level localization was not found in the literature" [80] | **Search-scoped negative, but narrower than stated** [80] | Architecture-model-driven fault localization **is** prior art (FLABot CSMR 2009 [11]; Expert Systems 2015 [12], with a with/without user comparison). Only *decision-anchored* localization is unoccupied [80]. |
| C5 | (b) "the two MOST impactful anti-patterns (Unstable Interface, Crossing) need co-change/history edges" [13] | **Overstated / mechanism wrong** [13][14][15] | Ordering supported (TSE 2021 §5.5 [13], single author group, Java+C# [13]). But both are **hybrids** with a pure-graph structural half [13][15]; DV8 says "both" [15]; WICSA 2015's #2 was **Cross-Module Cycle, pure structure** [14]. Honest shape: *hybrid > pure-graph* [81]. |
| C6 | (b) "the cheapest to compute (Package Cycle) is the LEAST impactful" [13] | **Supported, with a counter-result** [13] | TSE 2021 §5.5 verbatim [13]. But on survival (EMSE 2022) [19] and refactoring cost (ECSA 2018) [20], independent groups rank the cycle family **first**. Also the ranking is metric-convention-sensitive (the re-derivation flips UIF/MVG under the relative-increase metric) [13][81]. |
| C7 | (b) family list: "DV8 / Mo, Cai, Kazman ... Unstable Interface, Crossing, Package Cycle, hub-like dependency, Martin instability/distance" [13][16][17] | **Taxonomy mix** [81] | The Mo/DV8 line has six families: UIF, MVG, UIH, Crossing, Clique, Package Cycle [13][15]. Hub-like Dependency/God Component/Feature Concentration are Arcan/Designite [16]; Martin metrics are a package-metric family [17]. "TSE 2019" and "TSE 2021" are one paper [13]. |
| C8 | (c) "an architectural constraint that IS a security control (OWASP A01 ... route must depend on auth middleware)" [31] | **Prior art exists; framing must change** [29][30][39] | Named concept: **"authorization context consistency"** (MACE, CCS 2014) [29]; route-level implementation with CWE-306/862/863 exists (AuthCheck 2019) [30]; a Python/FastAPI sibling-consistency tool ships today [39]. "By construction" is false (DRF defaults to `AllowAny` [33]; control often inline [39]). Novelty = substrate + memory only [82]. |
| C9 | (d) "Decision-guided migration / library upgrades", citing Arcan ECSA 2019 and JabRef churn [40][41] | **Scope mismatch + wrong year** [40][41][82] | The ECSA 2019 Arcan paper is **monolith→microservice decomposition**, not library upgrade (and whether it uses Arcan is unverified) [40]. JabRef is **ECSA 2017 Companion** [41], a single-project before/after churn observation, confounded [41][82]. |

**Where your claims were right and worth keeping:** the (b) ordering (UIF and Crossing top) is real [13]; PKC-last
is real [13]; the DRSpace coverage numbers are real [5]; the Titan-vs-Sonar precision pair is real [6]; and your instinct
that (b)'s cheap/history split is the interesting fault line is right — it is the *mechanism* that needed
correcting, not the suspicion [13][14][15].

---

## 7. Open questions

1. **Does the decision layer add anything over structure?** No study running this ablation was found within
   this review's searches [80]. It gates (a) and (b) — it does not test Rank 1's re-introduction DV or Rank 2's
   route→auth constraint. It is cheap and should be run first (§4.1 Gate) [80].
2. **Are Shepherd's dismissals meaningful?** The Rank 1 hazard test answers it [83], and the answer determines
   whether the memory moat is an asset or an artefact [52][57][83].
3. **Would a Python ADR-bearing issue→fix corpus change (a)'s ranking?** If one were constructed (Home
   Assistant is the obvious host: ADRs, tests, long merged-PR history, `cpt detect` at 4.0 s [1]), (a)'s cost
   drops sharply [80]. That is a build-vs-rank decision, not an evidence gap [80]. Two Python-usable anchors already
   exist but lack ADR linkage (MULocBench, 1,100 issues / 46 Python repos [27]; PyMigBench-2.0, 335 migrations [42]).
4. **Does the security framing survive evasion recall?** Unknown until measured; the failure modes are
   documented [39], but a recall-collapse measurement on an architectural constraint was not found within this
   review's searches [82].
5. **Is the ICSA 2026 refactoring intervention positive or null?** Blocked (403) [22][81]. If positive, (b) gains the
   intervention study the whole line lacks [81].
6. **What is the real ADR→checkable-constraint conversion rate?** 18 of 69 ADRs (26%) on Shepherd's own five
   repos (`wiki/research-brief.md:43`, `notes/extension-scenarios.md:39`) [4]; those 18 code-checkable constraints are the
   benchmark gold set [3]; no population estimate found in the literature [79]. `inherited, not re-verified` as a general rate [4].
7. **Does a foreign oracle agree with the constraint engine?** This is the general form of the self-validation
   objection, and the security slice is the only place it is cheaply answerable [34][35][82].
8. **Review-pass findings, and their resolution (for the audit record).** The adversarial review returned
   3 MAJOR and 17 MINOR findings, no FATAL. All three MAJOR items are resolved in this file: (i) §3.6's header
   over-applied bucket C to three rows that the notes grade otherwise — the section is retitled and each of
   those rows now carries its own bucket label; (ii) the audit-evidence claim was upgraded from its
   search-scoped negative to an existence claim — restored to search-scoped phrasing in §2.2 F; (iii) the
   Caracciolo et al. venue was wrong (ICSM 2015 → **IWESEP 2016**, DOI 10.1109/IWESEP.2016.12, verified via
   Crossref), corrected in §3.6 and source [63]. The 17 MINOR items were applied; the one that changed a
   verdict rather than a wording is the §3.2 survival-evidence reading, which is now marked metric-ambiguous.
   Findings file: `outputs/.drafts/beyond-compliance-applications-verification.md`.

---

## 8. Sources

Every entry below was re-checked in this pass: the URL was fetched (`fetch_content` or HTTP) and/or the DOI or
arXiv ID was resolved and its title/first author/year matched against the Crossref or arXiv index. Entries are
grouped to match the structure of the body. Entries that could not be reached are listed separately under
**Blocked / unverified URLs**, and sources verified but not cited inline are listed under
**Verified but not cited in the body** so that nothing is silently dropped.

**Workspace artifacts (local, re-checked in this pass)**

1. `eval.md` — Shepherd evaluation log (blended real-repo ingestion 0.5667 → 0.6333, `eval.md:509,517`; `detect()` = 4.0 s, `eval.md:581`; per-ADR scope labels, `eval.md:544`). Local file: `/Users/ravichasuksawasdinaayuthaya/UNSW/research/Shepherd/eval.md`.
2. `benchmark/benchmark.md` — ADRLinter research benchmark proposal (test-instance definition, CPT-vs-baseline arms, R1–R4 ablation). Local file: `benchmark/benchmark.md`.
3. `benchmark/gold/*` — gold ADR-constraint set (60 cases; 18 code-checkable constraints across 69 ADRs). Local directory: `benchmark/gold/`.
4. `wiki/research-brief.md:43` and `notes/extension-scenarios.md:39` — inherited "18 of 69 ADRs (26%) are code-checkable" figure. Local files. Cited only as `inherited, not re-verified`.

**Design-rule-space / architectural debt line**

5. L. Xiao, Y. Cai, R. Kazman, *Design rule spaces: A new form of architecture insight*, ICSE 2014, pp. 967–977. DOI: https://doi.org/10.1145/2568225.2568241 · author copy: https://personal.stevens.edu/~lxiao6/papers/ICSE-14.pdf
6. R. Kazman, Y. Cai, R. Mo, Q. Feng, L. Xiao, S. Haziyev, V. Fedak, A. Shapochka, *A Case Study in Locating the Architectural Roots of Technical Debt*, ICSE 2015 vol. 2 (SEIP), pp. 179–188. DOI: https://doi.org/10.1109/ICSE.2015.146 · author copy: https://ranmo.github.io/papers/icse2015-Seip.pdf
7. R. Kazman, *A Case Study in Locating the Architectural Roots of Technical Debt*, SEI blog (secondary; source of the "`.82` bugs per file" figure). https://www.sei.cmu.edu/blog/a-case-study-in-locating-the-architectural-roots-of-technical-debt/ — single-source and internally inconsistent (project-level and DRSpace-level change totals both stated as 2,332).
8. L. Xiao, Y. Cai, R. Kazman, R. Mo, Q. Feng, *Identifying and Quantifying Architectural Debt*, ICSE 2016. DOI: https://doi.org/10.1145/2884781.2884822 · author copy: https://ranmo.github.io/papers/icse2016-Debt.pdf
9. Y. Cai, L. Xiao, R. Kazman, R. Mo, Q. Feng, *Design Rule Spaces: A New Model for Representing and Analyzing Software Architecture*, IEEE TSE 45(7):657–682, 2019. DOI: https://doi.org/10.1109/TSE.2018.2797899
10. L. Xiao, Y. Cai, R. Kazman, *Titan: A Toolset That Connects Software Architecture with Quality Analysis*, FSE 2014 tool demo. https://personal.stevens.edu/~lxiao6/papers/FSE-TD-14.pdf
11. Á. Soria, J. A. Díaz Pace, M. R. Campo, *Tool Support for Fault Localization Using Architectural Models* (FLABot), CSMR 2009, pp. 59–68. DOI: https://doi.org/10.1109/CSMR.2009.42 *(see Verification corrections: the DOI printed in the draft, `…CSMR.2009.39`, does not resolve)*
12. Á. Soria, J. A. Díaz Pace, M. R. Campo, *Architecture-driven assistance for fault-localization tasks*, Expert Systems 32(1):1–22, 2015 (online 2013). DOI: https://doi.org/10.1111/exsy.12047 · metadata record: https://researchr.org/publication/SoriaPC15 · repository record: https://repositoriosdigitales.mincyt.gob.ar/vufind/Record/CONICETDig_f15465c7289366de17850213a049caba — publisher page 403 to automated fetches; claims rest on the Crossref abstract.

**Anti-pattern families**

13. R. Mo, Y. Cai, R. Kazman, L. Xiao, Q. Feng, *Architecture Anti-Patterns: Automatically Detectable Violations of Design Principles*, IEEE TSE 47(5):1008–1028, 2021. DOI: https://doi.org/10.1109/TSE.2019.2910856
14. R. Mo, Y. Cai, R. Kazman, L. Xiao, *Hotspot Patterns: The Formal Definition and Automatic Detection of Architecture Smells*, WICSA 2015, pp. 51–60. DOI: https://doi.org/10.1109/WICSA.2015.12 · author copy: https://ranmo.github.io/papers/wicsa2015-Pattern.pdf
15. ArchDia/DV8 documentation — *Design Anti-patterns* (https://docs.archdia.net/DesignAnti-patterns.html), *Unstable Interface* (https://docs.archdia.net/UnstableInterface.html), *CLI: Anti-pattern Commands* (https://archdia.com/pages/user-guide-cli-anti-pattern-commands), *Assessing Modular Structure Based on Evolution History* (https://docs.archdia.net/AssessingModularStructureBasedon.html).
16. Arcan architectural smell catalogue. https://docs.arcan.tech/latest/architectural_smells/
17. R. C. Martin, *OO Design Quality Metrics: An Analysis of Dependencies*, 1994. http://objectmentor.com/resources/articles/oodmetrc.pdf *(the linux.ime.usp.br mirror is byte-identical to this copy; MD5 `1d3c26d161642fe681ae945e843de30d`, checked in the T3 note [81])*
18. ArchUnit user guide (covers both §8.7.2 *Component Dependency Metrics by Robert C. Martin* and the `FreezingArchRule` freeze mechanism). https://www.archunit.org/userguide/html/000_Index.html
19. D. Sas, P. Avgeriou, U. Uyumaz, *On the evolution and impact of Architectural Smells — An industrial case study*, EMSE 27(4):86, 2022. arXiv: https://arxiv.org/abs/2203.08702
20. L. Martini, F. Arcelli Fontana, M. Biaggi, R. Roveda, *Identifying and Prioritizing Architectural Debt Through Architectural Smells: A Case Study in a Large Software Company*, ECSA 2018, pp. 320–335. DOI: https://doi.org/10.1007/978-3-030-00761-4_21
21. *Studying the Relationship between Architectural Smells and Maintainability* (independent study, 378 versions / 8 OSS projects). https://www.diva-portal.org/smash/get/diva2:1786267/FULLTEXT01.pdf
22. F. Arcelli Fontana, N. Milanese, M. Refolli, C. Trubiani, *Impact of Refactoring Architectural Smells on Quality, Security, and Performance Metrics*, ICSA 2026, pp. 213–220. Artefact: https://zenodo.org/records/18754704 — **publisher blocked (HTTP 403): results unread**; listed here for identification only.

**Fault localization / DRSpace evidence base**

23. J. Zhou, H. Zhang, D. Lo, *Where Should the Bugs Be Fixed? More Accurate Information Retrieval-Based Bug Localization Based on Bug Reports* (BugLocator), ICSE 2012, pp. 14–24. DOI: https://doi.org/10.1109/ICSE.2012.6227210 · author copy: http://www.mysmu.edu/faculty/davidlo/papers/icse12-localization.pdf
24. S. Wang, D. Lo, *Version history, similar report, and structure: putting them together for improved bug localization* (AmaLgam), ICPC 2014. DOI: https://doi.org/10.1145/2597008.2597148 · author copy: http://www.mysmu.edu/faculty/davidlo/papers/icpc14-localization.pdf
25. A. Takahashi, N. Sae-Lim, S. Hayashi, M. Saeki, *An Extensive Study on Smell-Aware Bug Localization*, JSS 178(110986):1–17, 2021. arXiv: https://arxiv.org/abs/2104.10953 · DOI: https://doi.org/10.1016/j.jss.2021.110986 *(the 309-system / α-sweep figures come from the full text read in the T2 note [80], §7.3 and §8)*
26. Z. Chen, X. Tang, G. Deng, F. Wu, J. Wu, Z. Jiang, V. Prasanna, A. Cohan, *LocAgent: Graph-Guided LLM Agents for Code Localization*, ACL 2025. arXiv: https://arxiv.org/abs/2503.09089
27. Z. Zhang, J. Wang, Q. Yang, Y. Pan, Y. Tang, Y. Li, Z. Xing, T. Zhang, *A Benchmark for Localizing Code and Non-Code Issues in Software Projects* (MULocBench), 2025. arXiv: https://arxiv.org/abs/2509.25242 · dataset: https://huggingface.co/datasets/somethingone/MULocBench
28. D. M. Le, S. Karthik, M. Schmitt Laser, N. Medvidović, *Architectural Decay as Predictor of Issue- and Change-Proneness*, ICSA 2021. arXiv: https://arxiv.org/abs/2102.09835

**Security**

29. M. Monshizadeh, P. Naldurg, V. N. Venkatakrishnan, *MACE: Detecting Privilege Escalation Vulnerabilities in Web Applications*, CCS 2014. https://www.cs.uic.edu/~venkat/research/papers/monshizadeh-ccs14.pdf
30. G. Piskachev, T. Petrasch, J. Späth, E. Bodden, *AuthCheck: Program-state Analysis for Access-control Vulnerabilities*, 2019. https://www.bodden.de/pubs/piskachev19authcheck.pdf
31. OWASP Foundation, *A01:2021 – Broken Access Control*, OWASP Top 10:2021. https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/index.html (also reachable at https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
32. OWASP Foundation, *API5:2023 Broken Function Level Authorization*, OWASP API Security Top 10 2023. https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/
33. OWASP Cheat Sheet Series, *Django REST Framework (DRF) Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/Django_REST_Framework_Cheat_Sheet.html
34. C. Xiang, L. Zhong, E. Mugnier, N. Nguyen, Y. Zhou, T. Xu, *Testing Access-Control Configuration Changes for Web Applications* (ACtests), 2025. arXiv: https://arxiv.org/abs/2505.12770
35. I. P. A. Dharmaadi, M. Alhanahnah, V.-T. Pham, F. Mohsen, F. Turkmen, *BACFuzz: Exposing the Silence on Broken Access Control Vulnerabilities in Web Applications*, 2025 (under peer review). arXiv: https://arxiv.org/abs/2507.15984
36. *Detecting Broken Object-Level Authorization Vulnerabilities in Database-Backed Applications*, ACM CCS 2024. DOI: https://doi.org/10.1145/3658644.3690227 — **ACM DL returns HTTP 403 to automated fetches**; numbers are abstract-snippet sourced [82].
37. J.-C. Noirot Ferrand, K. Domico, Y. Beugin, P. McDaniel, *Longitudinal Analyses of SAST Tools: A CodeQL Case Study*, 2026. arXiv: https://arxiv.org/abs/2605.07900
38. K. Hermann, S. Peldszus, T. Berger, *Many Tools, Few Exploitable Vulnerabilities: A Survey of 246 Static Code Analyzers for Security*, 2026. arXiv: https://arxiv.org/abs/2602.18270
39. A. Gogani, *enforcement-coverage* (Python/FastAPI sibling-consistency tool; self-reported grey literature). https://github.com/arian-gogani/enforcement-coverage

**Migration**

40. I. Pigazzini, F. Arcelli Fontana, A. Maggioni, *Tool Support for the Migration to Microservice Architecture: An Industrial Case Study*, ECSA 2019, pp. 247–263. DOI: https://doi.org/10.1007/978-3-030-29983-5_17 — metadata verified; full text paywalled [82].
41. T. Olsson, M. Ericsson, A. Wingkvist, *The relationship of code churn and architectural violations in the open source software JabRef*, ECSA 2017 Companion (not 2019), pp. 152–158. DOI: https://doi.org/10.1145/3129790.3129810
42. M. Islam, A. K. Jha, S. Nadi, I. Akhmetov, *PyMigBench: A Benchmark for Python Library Migration*, MSR 2023. DOI: https://doi.org/10.1109/MSR59073.2023.00075 · project site: https://ualberta-smr.github.io/PyMigBench/ · v2 data: https://doi.org/10.6084/m9.figshare.24216858.v2
43. K. Cheng, X. Shen, Y. Yang, T. Wang, Y. Cao, M. A. Ali, H. Wang, L. Hu, *CODEMENV: Benchmarking Large Language Models on Code Migration* (ACL 2025 Findings). arXiv: https://arxiv.org/abs/2506.00894
44. M. Islam, A. K. Jha, M. Mahmoud, S. Nadi, *MigrateLib: a tool for end-to-end Python library migration*, 2025/2026. arXiv: https://arxiv.org/abs/2510.08810
45. P. Di Francesco, P. Lago, I. Malavolta, *Migrating Towards Microservice Architectures: An Industrial Survey*, ICSA 2018. DOI: https://doi.org/10.1109/ICSA.2018.00012 · author copy: https://www.ivanomalavolta.com/files/papers/ICSA_2018.pdf

**Agent context / memory-as-signal**

46. Z. Z. Wang, A. Asai, X. V. Yu, F. F. Xu, Y. Xie, G. Neubig, D. Fried, *CodeRAG-Bench: Can Retrieval Augment Code Generation?*, NAACL 2025 Findings. arXiv: https://arxiv.org/abs/2406.14497
47. D. Dillon, K. Varanasi, *Context-Augmented Code Generation: How Product Context Improves AI Coding Agent Decision Compliance by 49%*, 2026-04-27 (vendor-authored). arXiv: https://arxiv.org/abs/2605.08112
48. A. Canedo, *Architecture as Capability Equalizer for Coding Agents*, 2026-08-22. arXiv: https://arxiv.org/abs/2608.21747
49. P. Khatri, *Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories*, 2026-07-28. arXiv: https://arxiv.org/abs/2607.27250
50. Y. Xue, *When and How Context Rot Appears in Coding Agents: A White-Box Study of Agent Skills in Code Auditing*, 2026. arXiv: https://arxiv.org/abs/2607.17937
51. B. Sam-Bodden, *What Context Does a Coding Agent Actually Need to Act?*, 2026-06-19. arXiv: https://arxiv.org/abs/2607.09691
52. H. Hu, J. Wang, A. Rubin, M. Pradel, *An Empirical Study of Suppressed Static Analysis Warnings*, Proc. ACM Softw. Eng. 2(FSE):290–311, 2025. DOI: https://doi.org/10.1145/3715729 · author PDF: https://software-lab.org/publications/fse2025_suppressions.pdf
53. S. Dhananjeyan, U. Kumaran, *The Exclusion Ratchet: False-Positive Suppression Accumulates and Persists in Detection Rule Repositories*, 2026 (submitted to *Computers & Security*). arXiv: https://arxiv.org/abs/2608.31062
54. J. Adam, *Ontology-Grounded Project Memory for Coding Agents* (MOOSEDev), NeSy 2026 industry track. arXiv: https://arxiv.org/abs/2608.13662
55. R. C. Malo, T. Qiu, *PROJECTMEM: A Local-First, Event-Sourced Memory and Judgment Layer for AI Coding Agents*, 2026. arXiv: https://arxiv.org/abs/2606.12329
56. J. Li, J. Yang, *Tracking the Evolution of Static Code Warnings: the State-of-the-Art and a Better Approach*, 2022/2024. arXiv: https://arxiv.org/abs/2210.02651
57. TNG/ArchUnit issue #1264, *Freeze files and stored.rules validation / sanity check*. https://github.com/TNG/ArchUnit/issues/1264 *(existence and content verified; current open/closed state not verified [83])*
58. R. Li, P. Liang, P. Avgeriou, *Code Reviewer Recommendation for Architecture Violations: An Exploratory Study*, EASE 2023. arXiv: https://arxiv.org/abs/2303.18058 · DOI: https://doi.org/10.1145/3593434.3593450

**Negative results and interventions**

59. V. Lenarduzzi, F. Lomio, H. Huttunen, D. Taibi, *Are SonarQube Rules Inducing Bugs?*, SANER 2020. arXiv: https://arxiv.org/abs/1907.00376
60. D. A. Tamburri, F. Arcelli Fontana, R. Roveda, V. Lenarduzzi, *Architecture Smells vs. Concurrency Bugs: an Exploratory Study and Negative Results*, 2023. arXiv: https://arxiv.org/abs/2303.17862
61. K. Z. Sultana, Z. Codabux, B. Williams, *Examining the Relationship of Code and Architectural Smells with Software Vulnerabilities*, 2020. arXiv: https://arxiv.org/abs/2010.15978
62. J. Buckley, N. Ali, M. English, J. Rosik, S. Herold, *Real-Time Reflexion Modelling in architecture reconciliation: A multi case study*, Information and Software Technology 61:107–123, 2015. DOI: https://doi.org/10.1016/j.infsof.2015.01.011 · open preprint: https://bura.brunel.ac.uk/bitstream/2438/14955/1/FullText.pdf
63. A. Caracciolo, M. Lungu, O. Truffer, K. Levitin, O. Nierstrasz, *Evaluating an Architecture Conformance Monitoring Solution*, **IWESEP 2016** (7th International Workshop on Empirical Software Engineering in Practice, March 2016). DOI: https://doi.org/10.1109/IWESEP.2016.12 · author copy: https://pure.rug.nl/ws/files/32628894/07464551.pdf *(venue corrected in the review pass; the draft and the T5 note said ICSM 2015)*
64. J. Knodel, D. Muthig, D. Rost, *Constructive architecture compliance checking — an experiment on support by live feedback*, ICSM 2008, pp. 287–296. DOI: https://doi.org/10.1109/ICSM.2008.4658077 — metadata verified via Crossref; **body paywalled**, result available only via a secondary description [83].

**Process applications**

65. Y. Yan, N. Cooper, K. Moran, G. Bavota, D. Poshyvanyk, S. Rich, *Enhancing Code Understanding for Impact Analysis by Combining Transformers and Program Dependence Graphs* (Athena), FSE 2024. DOI: https://doi.org/10.1145/3643770 · author PDF: https://www.cs.wm.edu/~denys/pubs/_FSE_24__Athena__Leveraging_Call_Graphs_Improve_Impact_Analysis.pdf
66. P. C. Rigby, S. Rogers, S. Saleem, P. Suresh, D. Suskin, P. Riggs, C. Maddila, N. Nagappan, *Improving Code Reviewer Recommendation: Accuracy, Latency, Workload, and Bystanders* (Meta), 2023/2025. arXiv: https://arxiv.org/abs/2312.17169
67. M. Paixão, J. Krinke, D. Han, C. Ragkhitwetsagul, M. Harman, *The Impact of Code Review on Architectural Changes*, IEEE TSE 47(5):1041–1059, 2021. DOI: https://doi.org/10.1109/TSE.2019.2912113 · author copy: https://mhepaixao.github.io/homepage/files/archreviews_tse.pdf
68. O. Legunsen, A. Shi, D. Marinov, *STARTS: STAtic Regression Test Selection*, ASE 2017. https://mir.cs.illinois.edu/marinov/publications/LegunsenETAL17STARTS.pdf
69. L. Pham, H. Ha, X. Zhang, H. Zhang, *TORAI: Multi-source Root Cause Analysis for Blind Spots in Microservice Service Call Graph*, FSE 2026. DOI: https://doi.org/10.1145/3808137 · arXiv: https://arxiv.org/abs/2604.13522
70. Z. Li, P. Liang, P. Avgeriou, *Architectural Technical Debt Identification Based on Architecture Decisions and Change Scenarios*, WICSA 2015. DOI: https://doi.org/10.1109/WICSA.2015.19 · record: https://research.rug.nl/en/publications/architectural-technical-debt-identification-based-on-architecture
71. F. Nogueira, N. Silva, T. Conte, *One Size Fits All? An Empirical Comparison of ADR Templates regarding Comprehension, Usability, and Ease of Adoption*, 2026. arXiv: https://arxiv.org/abs/2604.27333
72. *Architecture Decision Records: Adoption, Impact, and Developer Engagement in Open-Source Software*, ICSA 2026 (program abstract). https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou
73. A. M. Mir, M. Keshani, S. Proksch, *On the Effect of Transitivity and Granularity on Vulnerability Propagation in the Maven Ecosystem*, SANER 2023. arXiv: https://arxiv.org/abs/2301.07972
74. M. Rubert, K. Farias, *On the effects of continuous delivery on code quality: A case study in industry*, Computer Standards & Interfaces 81:103588, 2022. DOI: https://doi.org/10.1016/j.csi.2021.103588 — publisher landing page 403 to automated fetches; metadata verified via Crossref.
75. D. Rost, M. Naab, *Software Architecture Documentation for Developers: A Survey* (147 developers), Fraunhofer IESE. https://www.iese.fraunhofer.de/content/dam/iese/dokumente/alte-dateien/study_software_architecture_documentation_for_developers_survey-en-fraunhofer_iese.pdf
76. I. Santos, K. R. Felizardo, M. A. Gerosa, I. Steinmacher, *Software Solutions for Newcomers' Onboarding in Software Projects: A Systematic Literature Review*, 2024. arXiv: https://arxiv.org/abs/2408.15989
77. J. Yasmin, Y. Tian, J. Yang, *A First Look at the Deprecation of RESTful APIs: An Empirical Study*, ICSME 2020. DOI: https://doi.org/10.1109/ICSME46990.2020.00024
78. S. Shimmi, N. M. Synovic, M. Rahimi, G. K. Thiruvathukal, *Process-based Indicators of Vulnerability-Re-Introducing Code Changes: An Exploratory Case Study*, 2025/2026. arXiv: https://arxiv.org/abs/2510.26676

**Authoring artifacts (research notes produced for this run)**

79. T1 research note — application-space sweep (D1–D12; per-candidate buckets, search log, blocked list). `outputs/.drafts/beyond-compliance-applications-research-sweep-apps.md`
80. T2 research note — candidate (a), decision-anchored bug localization (number-verification table, prior-art table, 13-query search log). `outputs/.drafts/beyond-compliance-applications-research-bug-localization.md`
81. T3 research note — candidate (b), architectural anti-patterns (definitions/thresholds, impact ranking, own re-derivation, replication search). `outputs/.drafts/beyond-compliance-applications-research-antipatterns.md`
82. T4 research note — candidates (c) and (d), security framing and decision-guided migration. `outputs/.drafts/beyond-compliance-applications-research-security-migration.md`
83. T5 research note — agent context selection, supply-chain, memory-as-signal (M1–M6; standing negative; intervention check). `outputs/.drafts/beyond-compliance-applications-research-agent-context-supplychain.md`
84. Lead-anchor note — primary sources read directly by the lead in round 1 (ICSE 2014, ICSE-SEIP 2015, WICSA 2015, TSE 2021 blocked, WICSA 2016, ECSA 2019). `outputs/.drafts/beyond-compliance-applications-research-lead-anchors.md`

### Blocked / unverified URLs

These URLs were **not** retrievable in this pass. Each affected claim is marked inline (a bracketed pointer to
this list or a "publisher blocked / abstract only" note). None of these entries was silently dropped.

| # | URL / entry | Failure observed | How the claim is carried |
|---|---|---|---|
| B1 | `https://par.nsf.gov/servlets/purl/10118809` — TSE 47(5) 2021 full text | `fetch_content`: "fetch failed"; `curl`: connection failure (HTTP 000) | Replaced by the DOI `https://doi.org/10.1109/TSE.2019.2910856` (resolves, 202). All TSE 2021 numbers used here [13] were read from the full text inside the T3 note [81], not from this URL. Not retrievable in this pass; it **was** successfully fetched via `curl` + `pdftotext -layout` in the T3 pass, so treat it as flaky for automated use rather than dead. |
| B2 | `https://doi.org/10.1109/CSMR.2009.39` — FLABot CSMR 2009, as printed in the draft | DOI does not resolve to the paper | Corrected to `https://doi.org/10.1109/CSMR.2009.42` (Crossref: Soria, Díaz Pace, Campo, CSMR 2009) — see Verification corrections. |
| B3 | `https://doi.org/10.1145/2076021.2048146` — RoleCast | ACM DL returns HTTP 403 to automated fetches | Working alternates: https://2011.splashcon.org/details/oopsla-2011-papers/62/RoleCast-Finding-Missing-Security-Checks-When-You-Do-Not-Know-What-Checks-Are (200) and https://www.mimuw.edu.pl/~janusz/dydaktyka/2012-2013/info_zpo/referaty/ref_2012_05_12%20RoleCast-%20Finding%20Missing%20Security%20Checks%20When%20You%20Do%20Not%20Know%20What%20Checks%20Are.pdf (200). Also note the venue correction in Verification corrections. |
| B4 | `https://doi.org/10.1145/3658644.3690227` — CCS 2024 BOLA study | ACM DL returns HTTP 403; no alternate located | Claim carried as abstract-snippet provenance from the T4 note [82] (101 real-world BOLA vulnerabilities); marked abstract-only. |
| B5 | `https://zenodo.org/records/18754704` — ICSA 2026 refactoring artefact | `curl`: 403; `fetch_content`: succeeded (title only) | Identification only. The study's **numbers remain unread** (publisher 403) [22][81]; §3.2 and §7 Q5 state this. |
| B6 | `https://boa.unimib.it/handle/10281/619561` and `.../219091` — ICSA 2026 refactoring paper | HTTP 403 (recorded in T3 §9) [81] | Same as B5 — the single most consequential gap in the anti-pattern slice [81]. |
| B7 | `https://www.sciencedirect.com/science/article/abs/pii/S0920548921000830` — 12-month CD case study landing page | HTTP 403 (Elsevier) | Replaced by the DOI `https://doi.org/10.1016/j.csi.2021.103588` (verified via Crossref: Rubert & Farias, *Computer Standards & Interfaces*, 2022). The quoted conclusion [74] is abstract-sourced. |
| B8 | `https://doi.org/10.1111/exsy.12047` — FLABot journal version | HTTP 403 (publisher) | Metadata verified via Crossref and two independent records [12]. The "with/without user comparison, time, code browsed, faults found" claim [12] rests on the Crossref abstract as read in the T2 note [80]; PDF not fetched. |
| B9 | `https://doi.org/10.1109/ICSM.2008.4658077` — Knodel et al. ICSM 2008 | DOI resolves to metadata; body paywalled | Result available only via a **secondary** description [64][83]; §3.6 says so explicitly. |
| B10 | `https://www.diva-portal.org/smash/get/diva2:1151038/FULLTEXT01.pdf` — secondary description of the Knodel experiment | Direct fetch reported HTTP 403 in the T5 note (HTTP 200 from this pass's checker, content-secondary either way) [83] | Used only as a secondary paraphrase [64][83]; never quoted as primary. |
| B11 | `https://www.javadoc.io/static/com.tngtech.archunit/archunit/1.3.2/...ComponentDependencyMetrics.html` | HTTP 404 (page not found) | Not cited. The ArchUnit metrics claim [18] uses the user guide URL, which resolves (200). |
| B12 | Paywalled primary sources named in the research notes but not load-bearing here: WICSA 2016 security paper full text (abstract only) [84]; ECSA 2019 migration paper full text [40]; Nayebi et al. ICSE-SEIP 2019 [80]; `RoleCast` abstract [82] | HTTP 403 / paywall | Each is either uncited in the body or marked abstract/metadata-only at the point of use. |

### Verification corrections (title / ID / venue mismatches found in this pass)

These are corrections to identifiers in the draft's provisional source list; **no number in the draft was
changed**. Each was resolved against the Crossref or arXiv index during this pass.

- **FLABot DOI.** The draft gave `DOI 10.1109/CSMR.2009.39` for Soria, Díaz Pace & Campo, CSMR 2009. Crossref
  resolves that paper at `10.1109/CSMR.2009.42`; `…39` does not resolve to it. Corrected in entry [11].
- **RoleCast venue.** The draft and the T4 note label RoleCast as "CCS 2011". Crossref shows
  `10.1145/2076021.2048146` published in *ACM SIGPLAN Notices* 46(10), 2011 — i.e. **OOPSLA/SPLASH 2011**, not
  CCS. Corrected here and recorded in B3.
- **BugLocator authors.** The draft listed "Zhou, Lu, Liu". The paper is by **Zhou, Zhang, Lo** (Crossref; T2
  note [80]). Corrected in entry [23].
- **Olsson et al. venue.** Draft already said ECSA 2017 Companion; reaffirmed against Crossref (2017,
  `10.1145/3129790.3129810`) — the note's "not 2019" correction stands [41].
- **"TSE 2019" / "TSE 2021" are one paper.** Crossref returns a single record, TSE 47(5), issued 2021, DOI
  `10.1109/TSE.2019.2910856` — as the draft states [13].
- **MULocBench ID.** Draft's `arXiv:2509.25242` is correct (title: *A Benchmark for Localizing Code and
  Non-Code Issues in Software Projects*; 1,100 issues / 46 Python projects) [27]. *(An initial check of
  `2609.25242` returned an unrelated condensed-matter paper; the draft's ID was not wrong.)*
- **No fabricated identifiers.** Every DOI, arXiv ID and URL in §8 was resolved and its title/first author/year
  matched. No identifier was invented; the only changes were the three corrections above.

### Additional verified works (unnumbered — not cited in the body)

These entries were verified as reachable and correct but carry no claim in the body, so they are listed here
rather than as numbered sources (keeping Sources free of orphan citations). None is dropped. The numbered
sources [8][9][10] that an earlier draft of this section listed here are all cited inline and appear in the
main list above.

- Y. Cai, L. Xiao, R. Kazman, R. Mo, Q. Feng (TSE 45(7), 2019) is cited as [9]; the ICSE 2016 ArchDebt paper [8] and the Titan FSE 2014 tool demo [10] are cited only via the DRSpace/ArchDebt-line and Titan references, and are also verified.
- Á. Soria, J. A. Díaz Pace, M. R. Campo, *Architecture-based run-time fault diagnosis* — Casanova, Schmerl, Garlan, Abreu, ECSA 2011, pp. 261–277. DOI: https://doi.org/10.1007/978-3-642-23798-0_29 (metadata verified; not cited).
- Q. Feng, R. Kazman, Y. Cai, R. Mo, L. Xiao, *Towards an Architecture-Centric Approach to Security Analysis*, WICSA 2016, pp. 221–230. DOI: https://doi.org/10.1109/WICSA.2016.41 (DOI and abstract verified; **full text not obtained** — abstract only [84]; not cited in the body).
- F. Arcelli Fontana, V. Lenarduzzi, R. Roveda, D. Taibi, *Are Architectural Smells Independent from Code Smells?* JSS 2019. https://arxiv.org/abs/1904.11755 (verified; not cited).
- J. Lefever, Y. Cai, H. Cervantes, R. Kazman, H. Fang, *On the Lack of Consensus Among Technical Debt Detection Tools*, ICSE-SEIP 2021. https://arxiv.org/abs/2103.04506 (verified; not cited in the body).
- G. Amanatidis et al., *Evaluating the Agreement among Technical Debt Measurement Tools*, EMSE. https://sites.uom.gr/a.ampatzoglou/public_html/papers/amanatidis2020emse.pdf (verified; single-source for DV8's advertised Python support; not cited).
- F. Sun, L. Xu, Z. Su, *Static Detection of Access Control Vulnerabilities in Web Applications*, USENIX Security 2011. https://www.semanticscholar.org/paper/132f37dc511812013e4d0fab686fd4274d40db05 (metadata-only via Semantic Scholar; not cited).
- *Detecting Missing-Permission-Check Vulnerabilities in Distributed Cloud Systems* (MPChecker). https://lujie.ac.cn/files/papers/MPChecker.pdf (abstract snippet; not cited).
- OWASP Foundation, *OWASP Benchmark Project* (benchmark app is Java-only). https://owasp.org/www-project-benchmark/ (verified; not cited).
- J. Yuan, W. Qi, Y. Sun, G. Liu, *DependLoc: A Dependency-based Framework For Bug Localization*, APSEC 2020 (metadata only). https://researchr.org/publication/YuanQ0020 (not cited).
- R. Widyasari et al., *BugsInPy* (493 bugs / 17 Python programs). https://arxiv.org/abs/2401.15481 · https://github.com/soarsmu/BugsInPy (verified; not cited).
- R. Su, A. Bakhtin, N. Ahmad, M. Esposito, V. Lenarduzzi, D. Taibi, *Evaluating Large Language Models for Detecting Architectural Decision Violations* (980 ADRs / 109 repos). https://arxiv.org/abs/2602.07609 (verified; not cited).
- Z. Luo et al., *Update from Hell: Can Coding Agents Survive Hidden Breakage in Dependency Upgrades?* (DEPBENCH). https://arxiv.org/abs/2608.30300 (verified; not cited).
- J. Zhao et al., *Enhancing Automated Program Repair with Solution Design* (DRCodePilot), ASE 2024. https://arxiv.org/abs/2408.12056 (verified; not cited).
- P. Joos, I. Bouzenia, M. Pradel, *CodeCureAgent*. https://arxiv.org/abs/2509.11787 (verified; not cited).
- R.-Z. Fan et al., *An Empirical Study of Harness Design for Coding Agents*. https://arxiv.org/abs/2609.20804 (verified; not cited).
- G. Buchgeher et al., *Using Architecture Decision Records in Open Source Projects — An MSR Study on GitHub*, IEEE Access 11:63725–63740, 2023. DOI: https://doi.org/10.1109/ACCESS.2023.3287654 (verified; not cited).
- B. Uzun, B. Tekinerdogan, *Architecture conformance analysis using model-based testing*, SPE 2019. DOI: https://doi.org/10.1002/spe.2667 (listed in the T1 note's search log; not verified in this pass, not cited).
