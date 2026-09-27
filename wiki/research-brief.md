> **Source:** [`notes/extension-scenarios.md`](../notes/extension-scenarios.md) @ `e3f0f17` — this page is a **copy** of the file above,
> kept here for browsing. Edit the source, not this page; regenerate with the
> command in [README.md](README.md).

# Shepherd — extension scenarios beyond compliance checking

Research brief, 2026-09-25. Companion to `benchmark/benchmark.md`, `benchmark/commit_set.md`, `eval.md`.

Sources: repo docs + code as read on this date, plus two Feynman `deepresearch` runs, both
archived under `notes/feynman-2026-09-25/`:
- **run 1** (`arch-decision-memory-scenarios.md`) — the scenario/benchmark sweep; source keys like
  `[T2-S7]` refer to its per-RQ files (`T1`–`T4`).
- **run 2** (`deepseek-run2/shepherd-adg-decision-memory.md`) — a citation-verified evidence review
  and 16 ranked experiments (E1–E16), including a corrections table. Its §7 fragility analysis and
  §6 corrections are the authority for §7–§9 here.
Claims marked **UNVERIFIED** were flagged as such by those runs and should be re-checked before
citing; §9 collects the residues.

Driving question: the base technique is solid, so move the weight to case studies and application
scenarios — bug finding / fixing rather than compliance. Which extensions are defensible, and
what specific bugs can this engine catch?

> **Superseded in part — 2026-09-27.** A third run re-tested this brief's claims and corrected
> several; its full ledger is `notes/feynman-2026-09-27/beyond-compliance-applications.md` §6
> (C1–C9). **Where the two disagree, run 3 wins.** The corrections that affect what you cite:
>
> - **§8.2's Tier-C asymmetry is overstated, and the mechanism is wrong.** Unstable Interface and
>   Crossing are *hybrids* with a pure-graph structural half, not history-only; DV8's wording is
>   "both", and WICSA 2015's second-ranked pattern was Cross-Module Cycle — pure structure. The
>   "Package Cycle is least impactful" half holds (TSE 2021 §5.5), but on refactoring **cost**
>   (ECSA 2018) and smell **survival** (EMSE 2022) independent groups rank the cycle family
>   **first**. The gradient is also single-author-group, Java + C# only, and
>   metric-convention-sensitive (a re-derivation from the published tables flips UIF/MVG).
> - **§2.2 item 3 (ICSE-SEIP 2015) is half wrong.** It is **7** root DRSpaces that cover 92% of
>   Change10, not six; six cover 89% of Bug2. n = 1 project. The paper's title is *"A Case Study
>   in Locating the Architectural Roots of Technical Debt"*.
> - **§4 S4's negative is narrower than stated.** "Decision-level localization was not found" is
>   search-scoped and true only for the *decision* anchor — architecture-model-driven fault
>   localization **is** prior art (FLABot, CSMR 2009; Expert Systems 2015). The nearest
>   quantitative analogue is partly negative: smell-aware localization was optimal at weight
>   α = 0 in 49 of 224 systems.
> - **§5.1 class 1's security framing has prior art.** The concept is named — "authorization
>   context consistency" (MACE, CCS 2014) — and implemented at route level with the exact CWEs
>   (AuthCheck 2019: CWE-306/862/863). "By construction" is false: Django REST Framework
>   defaults to `AllowAny`, and the control often lives inline in the handler.
> - **§4 S6's migration anchor is a scope mismatch.** The ECSA 2019 Arcan paper is
>   monolith→microservice decomposition, not library upgrade; JabRef is **ECSA 2017** Companion,
>   a single-project before/after observation.
> - **§7.4's ICSA 2026 refactoring-intervention numbers were not retrievable** (publisher 403) —
>   still the only intervention design found for the anti-pattern families.
>
> §2.1's negative results, §2.2 items 1, 2, 4 and 5, and §3's convertibility measurement stand
> as written.

---

## TL;DR

1. **The pivot is right.** Detection-side return is flat: `eval.md:509,517` show blended real-repo
   ingestion at **0.6333 unchanged since #146** (from 0.5667) with every real-repo match tally
   held, and `benchmark/benchmark.md` still defines only its two comparison subtasks (Subtask 2
   *CPT vs Pi+LLM*, line 22; Subtask 3 *R1–R4 ablation*, line 52) with Phase 3 evaluation
   unexecuted (line 103) and five Open Items unticked (line 142). Reallocating to case studies is
   correct. (Earlier drafts of this brief carried a "last planned work on this gold set" quote
   attributed to line 179 of `benchmark/benchmark.md` — **that citation was fabricated**: the file
   is 148 lines and the phrase appears nowhere in it.)
2. **Do not frame it as defect prediction.** Every violation↔defect result in the literature is
   *correlational or predictive*; no controlled experiment shows conformance checking reduces
   defect rates. Frame it as **invariant enforcement where the ADR is the spec** — a violation is
   a bug by construction — plus the **memory** differentiator.
3. **There is an open lane.** A 2025 systematic literature review of LLM×software architecture
   found *no* LLM work on architecture conformance checking, and the only LLM ADR-violation study
   is a single 2026 paper, weak on implicit decisions. `[T1-S24][T2-S31]`
4. **The binding constraint is not the engine — it's ADR→constraint convertibility.** Across the
   five benchmark repos, **18 of 69 ADRs (26%) are code-checkable**, yielding 18 constraints in
   total, and **every one complies at HEAD**. Expansion should prioritise *what a constraint can
   express* over *what task we point it at*.
5. **Two scenarios are cheap and defensible now:** (S1) CPT as an automatic oracle for agentic
   bug *repair*, and (S2) history-mined violation↔fix linking. (S3) the memory-layer bug classes
   — vacuous guards, stale dismissals — is the most *novel* and is nearly free to measure.
6. **The versioning answer is "diff side yes, graph side no"** (§7). `cpt detect --commit` is
   already SHA-addressable and dismissals survive `cpt update`; but `parse_repo` reads the working
   tree, no rule carries a validity interval, and no reviewed tool has both freezing and expiry.
   Two engine-level traps hit this design directly: silent vacuity (`grimp`) and **non-deterministic
   evidence paths**, which threaten the stored `evidence`/`path_hops` across commits.
7. **Generalising the graph is real but not a contribution** (§8). Computability tiers A/B/C over
   the ADG; the co-change anti-pattern family (Unstable Interface, Crossing) needs history edges —
   and those are precisely the two with the strongest evidence, while Package Cycle (Tier A, the
   cheapest) is the *least* impactful. Shepherd's moat stays decision-anchoring + memory.
8. **As written, most of §5 is observability, and ignoring a finding is free** (§4, "Where the
   finding lands"). The actionable artifact is the **constraint set injected at task start**, with
   violations as the failure path — polarity inverted. Injection must be **relevance-selected**:
   over-injecting measurably hurts, and Shepherd already has half the machinery (constraint→code
   reachability); the missing half is issue→code localization, for which the ADG is already the
   right shape. The decisive experiment is a 3-arm A/B/C (none / all / relevance-selected).

---

## 1. What the pivot gets right, and the one way it can go wrong

Right: the eval has plateaued. Headline retrieval numbers are stable since #146 (blended
real-repo ingestion accuracy 0.6333), and the ablation programme (#131, #140, #149, #158) has
wrung the tool surface dry. Further optimisation has poor marginal return.

The failure mode: **pitching this as defect prediction.** That claim lands in a literature that
has largely failed to support it, and will be reviewed against that literature (§2.1). The
reframe that survives:

> Shepherd does not predict defects from architecture smells. It **enforces architectural
> invariants whose violation constitutes a defect**, and it **remembers** which invariants were
> violated, dismissed, or repaired across a project's history.

"All endpoints depend on the auth middleware" (flask ADR-002) is not a smell — it is a spec. An
endpoint that does not, is broken. Causation, not correlation.

---

## 2. The evidence base

### 2.1 The negative results (do not build the story on these)

| Study | Test | Result |
|---|---|---|
| Lenarduzzi et al., *Are SonarQube Rules Inducing Bugs?*, SANER 2020 | SonarQube rules marked "bug" vs SZZ-labelled fault-inducing commits | Violations SonarQube calls bugs were **generally not fault-prone**; fault-prediction power "extremely low"; only 25 rules relatively fault-prone. |
| *Architecture Smells vs. Concurrency Bugs*, arXiv:2303.17862 | 125 releases, 5 data-intensive systems | Smells "are not correlated with concurrency in general". Largely negative. |
| *Code and Architectural Smells vs. Software Vulnerabilities*, arXiv:2010.15978 | Smells vs. vulnerabilities | "No significant relationship". |

Reproducing this design — "we detect architectural problems, therefore we find bugs" — is
already-tested and weak, for both lint rules and architecture smells.

### 2.2 The positive result (the one to stand on)

The **design-rule-space** line is stronger than the smell literature and is the right citation:

- Xiao, Cai, Kazman, *Design Rule Spaces*, ICSE 2014 — top-5 DRSpaces cover **52–89% of
  error-prone files** across three large OSS systems; within each Bug2 DRSpace, an average of
  **62% of files have more than 2 bug fixes** (note: >2, averaged within each space — not "≥2 in
  a top space"). `[T2-S3][T2-S4]`
- Xiao, Cai, Kazman, Mo, Feng, *Identifying and Quantifying Architectural Debt*, ICSE 2016 —
  formalises architectural debt and shows architecturally-connected components carry the
  error-proneness. `[T2-S1]`
- Kazman et al., *Architectural Roots*, ICSE-SEIP 2015 — six root DRSpaces cover **89% of Bug2
  and 92% of Change10 files**; architects verified 5/6 debt instances; **Titan precision 31%/40%
  vs SonarQube 18%/27%**; predicted ~295% year-1 refactoring ROI. N=1 industrial, but the most
  detailed evidence available. `[T2-S2]`
- Mo, Cai, Kazman, Xiao, Feng, *Architecture Anti-Patterns*, TSE 2019 — infected files are far
  more error-prone and change-prone; anti-patterns are **dependency-structure** violations
  (unstable / hub-like / cyclic dependency). `[T2-S5]`
- Le et al., ICSA 2021 — current architectural decay **predicts future** issue- and
  change-proneness, across 10 systems. `[T2-S7]`

The ICSE-SEIP 2015 study is the direct counterweight to SANER 2020: same question, better-grounded
structural model, and it **beats SonarQube on defect-localization precision**. That is the gap
Shepherd's structural (not syntactic) knowledge occupies — and note the ADG already stores
exactly the edge kinds (`CONTAINS`/`IMPORTS`/`CALLS`/`INHERITS`, `app/services/models.py`) these
anti-patterns are computed from.

### 2.3 The method to borrow: history mining and SZZ

- **Maffort et al.** already **mine architectural violations from version history** `[T4-17]`.
  Two refinements from the verification pass: the **issue year is 2016** (EMSE 21(3):854–895,
  online 2015), and the tool is **ArchLint** — heuristics expressed as SQL over a dependency
  database, **not** a DCL/dependency-constraint-language paper. History mining is therefore a
  *known method*, not a novel one — it is new only in being driven by ADR constraints.
- **SZZ** labels fault-inducing commits from fix commits; modern variants: LLM4SZZ
  (arXiv:2504.01404), AgentSZZ (arXiv:2604.02665). SANER 2020 above is the template.
- **Specification mutation** (Budd & Gopal 1985; Black et al., ASE 2000) is the precedent for
  injected-violation ground truth `[T4-12][T4-13]`. The run found **no precedent for
  injected-violation ground truth in architecture conformance specifically** — that control would
  be the novel methodological element.

### 2.4 Benchmarks and datasets (Python-labelled)

| Benchmark | Task | Size | Python? |
|---|---|---|---|
| SWE-bench (arXiv:2310.06770) | issue→patch bug fixing | 2,294 test / 19,008 train | **Yes** |
| SWE-bench Verified / Lite | validated subsets | 500 / 300 | **Yes** |
| SWE-Gym (arXiv:2412.21139) | executable agent env | 2,438 tasks | **Yes** |
| SWE-smith (arXiv:2504.21798) | synthetic training tasks | 59,136 | **Yes** |
| BugsInPy (arXiv:2401.15481) | bug fixing / APR | 493 bugs, 17 repos | **Yes** |
| MULocBench (arXiv:2509.25242) | issue localization | 1,100 issues, 46 repos | **Yes** |
| LocBench (arXiv:2503.09089 — the benchmark introduced by **LocAgent**) | code localization | 560 issues, 163 repos | **Yes** |
| SWR-Bench (arXiv:2509.01494) | PR review-comment generation | 1,000 PRs | **Yes** |
| **CodeFuse-CR-Bench** (arXiv:2509.14856; the artefact is released as **SWE-CARE**) | repo-level code review | 601 instances, 70 repos | **Yes** |
| PyMigBench (MSR 2023) | library migration | 3,096 changes / 141 lib pairs | **Yes** |
| CodeMEnv (arXiv:2506.00894) | migration across environments | 922 (587 Python) | partly |
| RepoBench / RepoEval / CodeRAG-Bench | repo-level retrieval | — | **Yes** |
| Defects4J (835 bugs) / MigrationBench / Bench4BL | Java | — | No |

ADR / architecture corpora: ADR-Study-Dataset (921 repos, metadata only, IEEE Access 2023);
LLM4ADR/DRAFT (4,911 ADRs, arXiv:2504.08207); the ADR-violation study itself (980 ADRs / 109
repos, arXiv:2602.07609 — methodological precedent, no released benchmark); Arcan + one
ECSA-2025 Zenodo dataset (Java/C/C++); erosion-symptom review study on OpenStack Nova/Neutron
(Python) — **replication package access UNVERIFIED** `[T3-30]`.

**The shape of the gap — stated precisely.** The bug benchmarks have no architecture component;
the ADR corpora have no bug labels. The defensible claim is:

> No **released, code-level, labelled ADR/decision-violation** benchmark exists — in Python or
> in any language.

Note the scope. It is *not* "no Python architecture benchmark": two Python-adjacent
counterexamples exist and should be positioned as nearest prior work —

- **SmellBench** (arXiv:2605.07001) — 65 expert-validated architectural code **smells** (not
  decisions) in scikit-learn; evaluates 11 LLM-agent configurations; best agent resolves 47.7%;
  and **63.1% of tool-detected smells were expert-judged false positives** (κ=0.94). `[T2-S32]`
  This is the closest prior work *and* it is the strongest external motivation for Shepherd's
  dismissal memory — a stateless smell detector produced a majority-false-positive stream that
  humans had to triage, which is exactly the alert-fatigue problem persistent dismissal solves.
  **Disambiguation warning:** two distinct artefacts carry the name *SmellBench* — this arXiv
  paper (PyExamine-detected smells in scikit-learn) and a GitHub **injection-based** benchmark
  (147 instances / 294 cases). Neither cites the other; do not cite them interchangeably.
  Also note the aggressiveness lesson: the agent that resolves the *most* smells is the one that
  introduces 140 new ones (net **−109**), while the conservative agents net +15/+16 — so a
  resolution-rate headline alone is a misleading metric, and any Shepherd repair arm must be
  scored net, not gross.
- **Li et al. erosion-symptom datasets** `[T3-30]` — 606 labelled violation-symptom review
  comments from Python OpenStack (Nova/Neutron), but ground truth is review *text*, not code.

That intersection is where Shepherd sits, and building the labelled set is simultaneously the
contribution and the validity risk.

---

## 3. The real ceiling: convertibility, not capability

Measured over `benchmark/gold/*_gold.json` **by me, on these five repos** — this is a
5-repository measurement, **not** a literature-established general rate, and it must not be
presented as one (see the caveat below the table):

| Repo | ADRs | With constraints | Convertible | Constraints |
|---|---|---|---|---|
| experimenter | 16 | 3 | 19% | 4 |
| flowkit | 12 | 4 | 33% | 6 |
| home-assistant | 22 | 2 | 9% | 2 |
| python-tuf | 10 | 3 | 30% | 4 |
| structurizr-python | 9 | 2 | 22% | 2 |
| **Total** | **69** | **14** | **26%** | **18** |

**Caveat — the 26% is unverified as a general rate.** No source in the reviewed literature
reports an ADR→checkable-constraint conversion rate, so "roughly a quarter of real ADRs are
convertible" is **UNVERIFIED** as a population claim; it is an n=5 measurement on Shepherd's own
benchmark repos. The nearest *published* data point is a **different measurement** and must not
be quoted as confirmation: in 980 ADRs across 109 repos, an LLM judged **24.7%** of sampled cases
"Code is Insufficient to Answer" (arXiv:2602.07609) — and that label's inter-model agreement is
only 0.1574, so it is soft even on its own terms. §10.1 is the experiment that would settle it.

Three quarters of ADRs are process, tooling, strategy, or data-representation decisions that
cannot be expressed as a dependency edge — and the gold notes say so deliberately
(`benchmark/gold/census.md`: "Process ADR … Emit no edges" recurs on almost every zero row).

Two consequences for the pivot:

- **Adding task types does not add data.** Pointing the same 18 constraints at bug fixing instead
  of compliance gives 18 constraints' worth of signal regardless of framing.
- **Every constraint is `COMPLY` at HEAD** in all five repos (census: "Total: N constraints, 0
  violations at pin"). Clean repos yield no positive cases. Any case study needs injected
  violations or history.

So the highest-headroom lever is **widening what the 4-predicate ontology can express**
(ADR-004), not adding tasks. Known valuable-but-inexpressible classes: configuration/feature-flag
mandates (`eval.md:454`, tamr ADR-0007), interpreter/version floors (currently fake FQNs
`python2.7`/`python3.5`, which the census itself recommends never firing), runtime numeric
policies (flowkit ADR-0011 redaction ≥ 15), process rules ("we don't merge PRs that add data
selectors", HA ADR-0003).

---

## 4. Ranked extension scenarios

Ranked by *defensibility × cost to a publishable result* — and, because the scenarios below are
only as good as the point at which their finding reaches an actor, by **where the finding lands**
below.

### Where the finding lands — memory, not linter

A linter is **stateless and exhaustive**: it checks everything, every time, and reports everything
it finds. A memory is **stateful and selective**: it knows what happened before, and speaks only
when it is relevant. That difference decides whether a finding is actionable at all, because
**ignoring a finding is free**. A report with no actor, no forcing point, and no cheap resolution
is a log entry, not a result — which is the correct criticism of most of §5 as written.

There are three ways to make resolution cheaper than ignoring: (1) arrive **before** the mistake,
(2) arrive **with** a proposed resolution, (3) make ignoring **cost**. SonarQube takes (3), which
is why teams turn it off. Every analyzer-conditioned repair system in §2 takes (2). (1) needs no
new machinery at all — and it is what turns the detector into memory.

**The polarity inversion.** Shepherd currently emits *violations*. The actionable artifact is the
**constraint set**, with violations as the failure path of that mechanism:

| When | What is injected | Actor acts by |
|---|---|---|
| Task start | constraints covering the files this task will touch, **with the ADR rationale** | writing compliant code the first time |
| Verify | CPT as oracle on the agent's own diff | iterating before a human sees it |
| Handoff | surviving findings + proposed resolution + provenance ("resolved in #1234, reintroduced here") | accepting or waiving, once |
| Dismissal | "known-noise here" / "you are about to reintroduce a fix" | not re-raising, not regressing |

**Gate last, not first.** A gate is the weakest of the three, and in an agentic loop it is
**gameable**: told "no route may import a model," an agent can move the import inside the function,
use `importlib`, or a `TYPE_CHECKING` guard. The graph edge disappears, the architecture does not
improve, and the gate goes green. A human treats a gate as a speed bump; an agent treats it as an
obstacle to route around. The CPT re-check on the diff is what closes this — another reason the
oracle placement matters more than the gate.

**Relevance is the whole problem.** Injecting all 18 constraints defeats the purpose twice: it
spends context, and redundant context measurably *hurts*. CodeFuse-CR-Bench found models vary in
robustness to redundant context, and CodeRAG-Bench found gold documents **lowered** GPT-4o on
DS-1000 (52.7 → 51.2). "Inject only what is related" is therefore not a refinement — it is the
mechanism.

Relevance decomposes into two problems of very different cost:

1. **Constraint → code.** "Does this constraint's subject set cover the files this task will
   touch?" This is a graph reachability query and Shepherd **already has it** — `_build_adjacency`,
   `_reachable_paths`, wildcard subject matching, and the specificity ordering (R2).
2. **Issue → code.** "Which files will this task touch?" This is code localization and it is the
   expensive half. LocAgent (arXiv:2503.09089) localizes over exactly **files, classes, functions
   and their imports/invocations/inheritance** — the ADG's syntactic node and edge kinds. That
   overlap is not a coincidence to ignore: the ADG is already shaped like a localization index.

**A third route, and it is the actual memory argument.** Relevance can be *learned from the repo's
own violation history* rather than predicted from issue text: which FQNs have violated which
constraints before, and which files change together (the co-change edges of §8.2). That is
empirical about *this* repository, needs no issue-text localization, and is available only because
Shepherd kept the history. This is where "memory, not linter" pays for itself concretely — and it
makes S2 (history mining) a prerequisite for the injection path, not just an end in itself.

**Policy: recall-biased, but bounded.** The failure costs are asymmetric — omitting an applicable
constraint fails **silently** (the agent violates it, and nothing says so), while injecting an
inapplicable one costs tokens and risks anchoring the agent on an irrelevant concern. So the
operating point sits further toward recall than a linter's, but is still cut by the specificity
ordering against a context budget. Consequence for metrics: **precision is the wrong headline**
for the injection path. The question is what was *left out*.

**What this repurposes.** The memory already built gets a second job: a dismissal stops being only
a suppression and becomes a *scoping* signal ("do not inject this constraint for this FQN"); the
specificity tier becomes injection *ordering*, not just match ranking; and supersession decides
*which version* of a constraint is stated to the agent.

**The experiment — reuse the two-arm apparatus, change the object.**

The existing two-arm comparison (CPT vs Pi+LLM, issues #162–#164) asks the agent to **review** a
commit and measures precision + relative coverage. The author-side experiment keeps the same repos,
pins, gold constraint set and cost-matching discipline, and changes only what the agent is asked to
do: **implement a task**, not judge a diff. Do **not** pool the two — they are different claims
with different metrics (review: *can it find it?*; author: *does its own code respect it?*).

The roles shift as well. In review, CPT is one of the two arms being compared. In authorship CPT
plays **two** roles at once — **injector** (constraints as context, the treatment) and **oracle**
(judges the agent's diff, the measurement) — and the oracle validates the injector with no human
annotation. That is the cost advantage, and it is S1's argument applied to construction.

**The task set already exists — it is `benchmark/gold/*_instances.json`, and it needs no new
curation.** 60 cases across the five repos. Each case already carries everything this experiment
needs: a `description` (the intent, already phrased close to a task prompt), a `diff` (the
reference outcome), `expected_violations` (the compliance ground truth), and a `grading_note`
recording the correct oracle behaviour *including its subtleties* — e.g. that sibling modules at a
historical pin fire the same way and must be scored as true firings, not false positives.

**The existing `type` split is, without modification, the three strata above:**

| type | n | role in this experiment |
|---|---|---|
| `injected` | 26 | **in scope** — a constraint is deliberately violated |
| `historical` | 5 | **in scope with a real human baseline** — the recorded commit is what a developer actually did, reusing its real parent state and message |
| `compliant_probe` | 25 | **out of scope — the anchoring control.** This is the expensive half of any benchmark, and it already exists |
| `known_limitation` | 4 | excluded (documented tool limits, not ground truth) |

**This also deletes the expensive half of relevance.** Each case names its target path
(`diff[].path`, or the expected `matched_fqn`), so the "constraint → code" reachability query has
its input **for free**. Issue→code localization — § above's costly half — is only needed when
moving to real issue-shaped tasks, not for a first result. The reuse is therefore not just cheaper
than curating; it removes the hardest open problem from the critical path.

**What is genuinely missing, and the free substitute for it.** There are no fail-to-pass tests, so
the correctness half of the two-part oracle has no curated source here. Two substitutes require no
curation: (i) a **non-degeneracy check** — the agent's diff must touch the case's intended path,
which detects comply-by-doing-nothing trivially; (ii) run the repo's **existing** test suite at the
pin as a break-nothing floor. Neither is a SWE-bench-grade oracle, so the claim must be scoped to
**compliance**, not correctness, and stated that way.

**Honest limits of the reuse.** The 26 `injected` cases are synthetic edits written to violate a
constraint, not tasks real developers faced — only the 5 `historical` cases carry that provenance,
and they should be reported as their own stratum. n=31 in-scope is small, but the design is
**paired** (same case, three arms), which buys back much of the power, and the 25 controls are what
make the comparison interpretable at all. Ceiling-effect risk (S1) applies with force to synthetic
edits: an agent may find a deliberate violation obvious, which is a further argument for reporting
the two in-scope strata separately.

**"Why not SWE-bench?" — its repos and ADR-bearing repos are disjoint sets, and the reason is the
ontology, not the benchmark format.** Three findings, checked against the tree:

1. **The name collision is not a bridge.** `repos/flask` and `repos/django` are purpose-built
   fixtures (11 and 7 Python files; `app/routes`, `app/services`, `app/models`; commit
   `base: compliant Flask app with ADRs`), not `flask-dev/flask` or `django/django`. The ADRs in
   them are synthetic — as `benchmark.md`'s risk table already states. Neither upstream repo has
   a `docs/adr/` directory at all.
2. **SWE-bench's 12 repos are libraries and frameworks, and library architecture is not
   layer-shaped.** Real Flask is `src/flask/{app,ctx,globals,helpers,sessions,signals,view}.py` —
   there is no `routes`→`models` edge for `prohibits_dependency` to forbid. A framework's
   architectural decisions are about **API stability, deprecation policy and dependency policy**,
   which the 4-predicate ontology cannot express. Getting onto SWE-bench is therefore gated by
   §3's ontology widening, not by the benchmark's format.
3. **The general gap** is the one §2.4 already names: bug benchmarks carry no architecture
   component, and ADR corpora carry no task labels. SWE-bench sits on one side, the five benchmark
   repos on the other.
   *(Decision corpora do exist in those repos under other names — Django's DEPs, scikit-learn's
   SLEPs, astropy's APEs — but they are forward-looking **proposals**, a different genre from a
   decision record, and their convertibility would sit well below the 26% of §3.)*

**So do not build a new dataset at all.** The 60 existing cases supply the tasks, the strata and
the controls; a SWE-bench-shaped set is the *scaling* path, not a prerequisite. If scale is ever
needed, build it on the repos that have ADRs, using SWE-bench's own recipe (merged PR + linked
issue + modified test files → fail-to-pass) — Home Assistant is the obvious host, since it has
ADRs, a test suite, a long merged-PR history, and `cpt detect` runs at 4.0 s on it (#165). SWE-Gym
and SWE-smith were built this way from other repos; nothing in the recipe requires SWE-bench's
twelve.

**What forgoing SWE-bench costs, and why it is affordable:** comparability with published numbers.
But the claim here is not *"we resolve issues better than SWE-agent"* — it is *"injecting the right
constraints changes whether the agent's own code respects the architecture."* That claim needs a
**control group**, not a leaderboard, and the 25 `compliant_probe` controls supply it.

**Stratify tasks into three kinds — the third is not optional:**

1. **In scope** — touches a constraint's subject *and* object. Injection should help here.
2. **Near** — touches the subject but not the object. Tests discrimination, not just recall.
3. **Out of scope** — no constraint applies. This is the **anchoring control**: if injection
   degrades these tasks, the cost of over-injection is measured rather than assumed away by the
   recall bias above.

**The degenerate case — compliance alone is not a valid metric.** An agent can satisfy every
constraint by doing nothing, or by writing code that is compliant and useless. The oracle must be
**two-part**: the task's fail-to-pass tests for correctness, *and* CPT for compliance. Either alone
is gameable — tests alone miss the architecture; CPT alone rewards inaction.

**Arms.** (A) agent alone; (B) agent + all constraints; (C) agent + relevance-selected constraints;
with the recorded human commit as a reference point. (A) vs (B) is the null check that injection
does anything at all; **(B) vs (C) is the claim**.

**Dependent variables** — note these are **not** §5's observability metrics, and precision is not
among them:

- **violation rate in the agent's own diff** — did it write compliant code the first time?
- **missed-constraint rate** — a violation occurred whose constraint was *not* injected. The direct
  measure of relevance recall, computable **only** because CPT re-checks: the detector becomes the
  instrument that measures whether the memory's selection worked.
- **constraint tokens as a share of context** — relevance efficiency.
- **scope creep** — diff size and files touched, to catch anchoring.
- **correctness** — fail-to-pass pass rate, so compliance cannot be bought with inaction.

**Status.** The precedent is strong: DRCodePilot's rationale ablation collapsed full-match counts
by 81.65% / 94.44%, and every analyzer-conditioned system reviewed feeds structured metadata
rather than a bare warning. The **direct test is absent** — no study measures whether
constraint-as-context improves agent outcomes (§8.2, searched negative). That makes it an
experiment rather than a finding, and a cheap one.

### S1 — CPT as an automatic oracle for agentic bug repair  ★ best evaluation story

Give an agent a broken change plus the ADR set; the agent repairs the code; **CPT decides
pass/fail**, exactly as SWE-bench's fail-to-pass tests do.

**Why it is strong.** The oracle already exists and is automated — no annotation, no human
grading, no LLM judge, which is the single biggest cost advantage over every other scenario. It
converts the detector from *the thing evaluated* into *the evaluation apparatus*, sidestepping the
precision problem entirely (0.326 as-scored becomes irrelevant when the constraint is ground
truth). It answers the "bug fixing, not just compliance" ask directly.

**Evidence.** SWE-bench established the fail-to-pass oracle; SWE-agent's ablations drop
resolved% by 1.7–7.7 points on SWE-bench Lite (3.0–7.7 over its five named components), and a
plain-RAG baseline resolves **2.67–4.33% vs 18.00%** on Lite (1.31% on full SWE-bench) at 8–13×
lower cost `[T4-1]` — flat retrieval is weaker, so arms must be **cost-matched**. That gap is the
room the structural approach occupies.

**What it needs.** A small harness: apply an injected violation from the existing
`commit_set.md` cases, ask the agent to fix it with and without the ADG/ADR context, gate with
`cpt detect`. **See §4's "The experiment" for the full design** — it supersedes this sketch: the
commit-set-as-task-set framing needs no violation injection at all, and the oracle must be
two-part (tests + CPT) so compliance cannot be bought with inaction.

**Risk.** Ceiling effect — a competent agent may fix a layering violation without the ADG, and
the study then shows nothing. Mitigate by using *transitive* violations, where `benchmark.md:40`
already predicts CPT should dominate.

### S2 — History-mined violation ↔ fix linking  ★ cheapest, real bugs

Run `cpt detect --commit` across a repo's history; every commit that introduced an ADR violation
is a candidate bug-by-construction. Then ask: *did a later commit fix it?*

**Why it is strong.** Real bugs, real provenance, **zero injection, zero annotation**. It dodges
§3's worst consequence (clean HEADs) because history contains the violations HEAD already cleaned
up. It reuses `cpt detect --commit` verbatim; #165 cut detect from ~48.6 min to 4.0 s on
home-assistant, so a full-history sweep is feasible. `commit_set.md:92` ("Real commits that do
violate") already anticipates
the tier (home-assistant `e4b01b65`, experimenter `a2de3aeb`, `9857c48a`).

**Correction to the framing:** this is **not novel** — Maffort et al. (EMSE 2016; ArchLint) mine
architectural violations from version history already `[T4-17]`. It is new only in being
constraint-driven. Present it as an accepted method applied to ADRs.
Its **SGA result is the empirical justification for S2's whole premise**: 53% of violations
found in year 1, and **zero** detected once four years of history were discarded — violations are
*transient in time*, which is exactly why a clean HEAD (§3) does not mean a clean history.
Single-source, one proprietary subject system, recall unmeasured — treat it as motivating, not
established.

**Risk.** Attribution — a later fix may be unrelated. Require the fix commit to touch the
violating FQN. Precedent for a null result exists (SANER 2020 found it for lint rules), so
**pre-register that possibility**; a well-run null against the lint-rule precedent is still a
contribution.

### S3 — Memory-layer bug classes  ★ most novel, nearly free

Constraints that are **green but enforcing nothing**. The R4 orphan path
(`app/services/cpt/resolution.py`) detects the symptom; nobody has framed it as a bug class, and
the deep-research run confirmed **no direct published precedent** for a re-introduction guard
`[T4-16]`.

- **Vacuous guard** — a rename makes a constraint match nothing; the check reports "clean"
  forever. A one-shot linter cannot distinguish "no violations" from "rule no longer applies".
- **Wildcard coverage gap** — `app.api.*` auto-inherits for new submodules, but a new *top-level*
  package is silently out of scope.
- **Stale dismissal** — see §5.3 item 14; a live correctness gap.
- **Fix regression** — a violation repaired in the past is reintroduced. The memory makes the
  finding *provenanced*: "this was resolved in #1234", which no stateless tool can say.

**What it needs.** Almost nothing to *measure*: report per repo the count of constraints whose
subject set is empty at HEAD, and how long each has been vacuous. That is a table, not a system.

### S4 — Decision-constrained bug localization  (strongest raw evidence, heaviest evaluation)

Localize a bug to the architecturally-connected group, not a single file. DRSpaces covering
52–89% of error-prone files (ICSE 2014; ICSE-SEIP 2015) is the most direct evidence of anything in
this brief — Shepherd's delta is decision semantics + transitive traversal + dismissals reducing
alert fatigue.

**Caveat.** Localization tooling itself is IR/history-based (BugLocator ICSE 2012; AmaLgam ICPC
2014; DependLoc APSEC 2020), and **decision-level localization was not found** `[T2-S16..S19]`.
Evaluation needs localization@k over MULocBench/LocBench — heavier than S1's pass/fail gate.

### S5 — Review-time decision conformance in diffs

Stronger than the draft suggested — the key study resolved in feynman's verification pass.
**Paixao et al., TSE 2021** (7 Java systems, 18,400 reviews, 51,889 revisions, 103,778 extracted
structural-architecture snapshots): developers discussed their change's architectural impact in
only **31%** of reviews; architectural awareness was ~29%; and among reviews where developers *did*
give architectural feedback, the patch's architectural quality **decreased in 33% of cases**
`[T2-S20]` (open-access UCL copy read).

That last number is the argument for this scenario in one figure: **human architectural review,
even when it happens, degrades the architecture a third of the time.** Automated per-commit
conformance checking is the obvious complement.

The gap otherwise: rationale is fragmented across ADRs, PR discussions and review comments
`[T1-S20]`; ArDoCo/LiSSA do **whole-artifact-set** consistency (acc 0.93/0.75) but nothing
per-commit `[T1-S5][T1-S6]`; violation symptoms are detectable from review text (arXiv:2306.08616)
`[T2-S21]`. Benchmarks: SWR-Bench, SWE-CARE.

Worth noting from the existing eval: restricting the reviewer corpus to "wrong *about the code*"
gives precision **72/76 = 0.947** vs 0.326 as-scored (`eval.md:647`) — the low headline number is
a scope-convention artefact, not reviewer error. That is a strong result to report.

### S6 — Decision-guided migration / library upgrades

Arcan-guided industrial microservice migration (ECSA 2019) `[T2-S24]`; churn↔violations in JabRef
`[T2-S25]`. Benchmarks: PyMigBench, CodeMEnv. Moderate — the benchmarks mine migration pairs, not
decision compliance.

### Deprioritised

- **Onboarding / architecture Q&A.** Weakest evidence, and much of it negative: an N=65 controlled
  study found documentation *format* does not significantly affect newcomers' architectural
  understanding, with prior source-code exposure dominating `[T2-S22]`. Keep as a qualitative
  section at most.
- **Test generation from decisions.** No published support found.
- **Design-drift trend monitoring as a headline.** This is precisely the design §2.1 tested.

---

## 5. Specific bugs Shepherd can catch

### 5.1 Catchable today

| # | Bug class | Constraint shape | Real instance |
|---|---|---|---|
| 1 | **Unauthenticated endpoint** (broken access control) | `requires_dependency(app.routes.*, app.middleware.auth.*)` | flask ADR-002 — graded `flask-violating-route` case. OWASP A01 by construction. |
| 2 | **Service-layer / gateway bypass** — data access skipping the sanctioned path, so transactions, validation and business rules are skipped | `prohibits_dependency(app.routes.*, app.models.*)` | flask ADR-001; django ADR-001. |
| 3 | **Backend coupling past an API boundary** — client reaches into the backend directly, escaping the single access point (auth, rate limiting, versioning) | `prohibits_dependency(flowclient.*, flowmachine)` | flowkit ADR-0003. |
| 4 | **Library-family divergence** — a second path using a different library, so behaviour diverges | `requires_dependency(openlobby.core.search.*, elasticsearch)`, `(openlobby.core.api.*, graphene)` | openlobby ADR-0002/0004. |
| 5 | **Banned third-party mechanism** (supply chain / ToS / security) | `prohibits_dependency(homeassistant.components.*, selenium)` | home-assistant ADR-0004. |
| 6 | **Missing implementation obligation** | `requires_implementation(...)` | openlobby ADR-0004 (Graphene). |
| 7 | **Dead-interpreter dependency** | `prohibits_dependency(tuf.*, python2.7)` | python-tuf ADR-0001 — fires but has **zero firing potential**; census says never use it. Shown for the ontology's edge, not as a real catch. |

Classes 1–3 are strongest: security or correctness bugs **by construction**, not smells. Class 1
is worth its own case study — an architectural constraint that *is* a security control.

### 5.2 Catchable with a small engine extension

| # | Bug class | Why it needs work | Extension |
|---|---|---|---|
| 8 | **Import cycle introduced** | No cycle predicate | `_build_adjacency` already runs in `detect()`; a cycle check over `IMPORTS` is a few lines. Cyclic dependency is one of Mo/Cai's error-prone anti-patterns. |
| 9 | **Blocking IO in an async path** (event-loop stall) | Needs `async` awareness | `_reachable_paths` already walks `CALLS`; add an async entry marker + `prohibits_dependency(async_subtree, requests)`. |
| 10 | **Config / feature-flag mandate** | 4-predicate ontology cannot express it | `eval.md:454` — ontology extension + full re-baseline. |
| 11 | **Version-floor constraint** | Currently fake FQNs | Needs a real version predicate instead of `python2.7` as a node. |

### 5.3 Bugs in the memory layer itself (the novel contribution)

| # | Bug class | Mechanism present | Missing |
|---|---|---|---|
| 12 | **Vacuous guard** — rename makes a constraint match nothing; "clean" forever | R4 orphan detection | Framing it as a bug class + a vacuity-duration measure |
| 13 | **Wildcard coverage gap** — new top-level package silently unchecked | Wildcard subjects | A checked-FQN coverage assertion |
| 14 | **Stale dismissal masks a true violation** | `dismissal.py` identity-key suppression | Re-validation against the current graph |
| 15 | **Fix regression** — a repaired violation reintroduced | Per-commit history + dismissals | "Previously resolved" annotation on a new finding |
| 16 | **Orphaned supersession** — superseding ADR withdrawn, original never returns | R1/R2/R3 tiers | Propagation rules on decision withdrawal |

**Why item 14 is concrete** (verified in `app/services/cpt/dismissal.py:80-86`): `filter_dismissed`
matches on the identity tuple `(subject, predicate, object, matched_fqn, adr_id)` and nothing else
— no timestamp, no code-state check, no expiry. A dismissal is a permanent, un-revalidated
judgement about a *location*. If the code at `matched_fqn` later changes so that it genuinely
violates, the tuple is unchanged and the violation stays suppressed: correct when made, silently
wrong afterwards. A narrower second version: an ADR rewrite keeping the same
`(subject, predicate, object)` triple but tightening the rule leaves the old dismissal applying to
the stricter rule.

This is a different question from `eval.md:647`'s whole-repo-vs-change-scoped scoring issue — that
is about what the reviewer was asked; this is about whether a decision made once is still valid.

Items 12–15 belong in a "why memory matters" section. Item 14 should be **filed as an issue
against the current implementation regardless of the research direction** — it is a correctness
gap, not just a research idea.

---

## 6. Case-study design (from the Feynman run's RQ4)

**Cases.** 2–3 mature Python repos with ADRs (multi-case replication logic); embedded units = bug-fix
tasks mined SWE-bench-style.

**RQs.** RQ1 efficacy (full system vs baselines on violation-linked bug tasks); RQ2 attribution
(gains specifically from persistent decision memory?); RQ3 persistence (re-introduction suppression
across commits).

**Baselines** — all cost-matched. B1 BM25/dense RAG over repo+ADR text (with a gold-doc oracle arm
per CodeRAG-Bench); B2 LLM-only; B3 import-linter / pydeps static checkers (implementable Python
dependency-rule checkers, but carrying no decision semantics — no dismissal or supersession)
`[T4-14][T4-15]`.

**Ablations.** M0 memory removed (traversal kept; dismissals/supersessions wiped); T0 traversal
removed (memory as flat RAG documents); S1 ADRs shuffled/replaced (negative control).

**Controls.** C1 ADR mutation → labelled violation mutants (spec-mutation precedent); C2
dismissed-violation re-introduction probes; C3 synthetic violation injection (**no published
precedent** — the novel methodological element); C4 history-mined real violations + manual
labelling.

**Attribution decision rule.** Attribute to memory only if (1) Δ(full−M0) > 0 on violation-linked
tasks; (2) Δ(full−S1) large — perturbed ADRs destroy the benefit, so it is not generic text
retrieval; (3) Δ(full−T0) > 0; (4) B3 ≈ 0 on dismissal/supersession-only cases; (5) full suppresses
re-alerts on C2 while M0 does not. **If (2) fails, report the gains as retrieval-driven** —
CodeRAG-Bench shows retrieval saturates and can even *hurt* (GPT-4o DS-1000 52.7→51.2 with gold
docs), so S1 is the decisive control `[T4-6]`.

**Metrics.** localization@k; resolved rate pass@1/@3; violation F1 with manual adjudication;
re-introduction rate; cost USD/task.

---

## 7. Retroactive violation checking: what the current model supports

Asked directly: *does retroactive/historical violation checking work with the code/graph
versioning as built?* Answer, verified against the code: **half of it is already there, and the
half that is missing is not versioning — it is a temporal model.**

### 7.1 What works today

- **The diff side is fully commit-addressable.** `app/services/cpt/git_adapter.py:13-57,168-175`
  resolves any ref or SHA and reads blobs with `git show`, so **no checkout is required** and no
  working-tree state is needed to ask "what changed in commit Y". `commit_update.py:128` calls
  `get_diff(repo_path, to_sha=to_sha)`.
- **Dismissals survive a graph rebuild** — deliberately. `commit_update` loads them
  (`commit_update.py:103`), then wipes structural data with `delete_structural_data()`, which
  deletes `:FQNNode` and structural edges **only** (`app/services/graph/connector.py:383-392`,
  docstring: "Dismissal nodes are unaffected"). They are then re-applied at
  `commit_update.py:136`.
- **History mining needs no new plumbing.** `cpt detect --commit <sha>` already accepts a SHA, and
  #165 cut detect from ~48.6 min to 4.0 s on home-assistant — a full-history sweep is a `git log`
  driver, not a new subsystem. This is why S2 is the cheapest scenario in §4.

### 7.2 The two real gaps

**Gap 1 — the graph side reads the working tree, not the commit.** `parse_repo`
(`app/services/adg/treesitter.py:343-363`) walks `repo_path.rglob("*.py")` and `read_bytes()`.
So `cpt update --commit Y` diffs at Y but *rebuilds structure from whatever is checked out*. The
graph is therefore only ever correct for HEAD-of-working-tree; asking "run detection as of
Y" against an old SHA returns that commit's diff traversed over today's structure. Snapshotting
per commit (§7.4) is what fixes this; it is also the design choice that is expensive to
retrofit.

**Gap 2 — no rule carries a validity interval.** A rule holding "for releases 5–12, superseded in
13" is expressible in ADR prose and **not machine-checkable in any reviewed conformance tool**.
The search covered ArchUnit, SonarQube, import-linter, jQAssistant, DCLsuite and mainstream ADR
templates: **no implementation of rule-level `valid_from`/`valid_to` exists** (searched negative;
interval semantics appear only in temporal *graph databases* — `VAL_FROM`/`VAL_TO`/`TX_FROM`/
`TX_TO` in TPGM+, and AeonG's anchor intervals). ADR templates *do* carry a supersession status
chain (Proposed/Accepted/Deprecated/Superseded/Rejected) but no validity dates.

Two consequences worth holding onto:

- **Freezing ≠ expiry, and no reviewed tool has both.** Freezing (ArchUnit `FreezingArchRule`)
  answers *"should this finding block CI?"*; expiry answers *"when must a human re-justify this
  decision?"* Shepherd's dismissal persistence is on the **freezing axis only**. SonarQube's
  `Accepted` waivers are the documented blind spot: indefinitely waived findings are excluded from
  quality ratings entirely.
- **A fresh `seed build` destroys dismissals.** `clear_all()` (`connector.py:90-94`,
  `MATCH (n) DETACH DELETE n`) is called from `app/cli/main.py:641`. Dismissals survive
  `cpt update` but not a re-seed. Worth documenting as intended-vs-surprising, because it is the
  one path where "persistent memory" is not persistent.
- **Terminology warning:** the phrase "supersession tiers" is Shepherd's own extension. **No
  reviewed source uses a tier vocabulary** — what exists industrially is a linear supersession
  *status* chain. Define the term explicitly if it is retained in the thesis.

### 7.3 Two engine-level traps that hit this design specifically

1. **Vacuous rules are silent by construction.** `grimp` (the engine behind import-linter),
   primary doc, on `find_illegal_dependencies_for_layers`: *"Any modules specified that don't
   exist in the graph will be silently ignored."* Rename a package and the rule **passes
   forever**. Mitigations exist but are inconsistent even inside one product family:
   import-linter's `independence` contract validates module existence and raises, while its
   `layers` contract's `exhaustive` option catches *undeclared new* modules, not *missing declared*
   ones. Structure101 has the same shape ("only violations between visible cells are enforced …
   if you collapse a cell, any rules implied by its contained cells are not checked").
2. **Persisted evidence paths are non-deterministic.** Same `grimp` doc: *"If there are multiple
   illegal Routes of the same length, it is not predictable which one will be found first… the
   PackageDependencies returned can vary for the same graph."* This is a **direct threat to
   Shepherd's design**, which stores an `evidence` path summary and `path_hops`
   (`engine.py:318-327`) and would reason over them across commits. Either canonicalise the path
   (sorted, minimum-length, tie-broken deterministically) or store the full route set. **No
   published canonicalisation scheme was found** (searched negative) — this is a small, real,
   citable engineering contribution sitting inside the memory layer.

Calibration on how loose "clean" is: an ISSTA 2024 study found **≥76% of warnings in vulnerable
functions were irrelevant** to the vulnerability-contributing commits, and **22% of VCCs went
undetected because of SAST rule limitations**. "No violation reported" is weak evidence.

### 7.4 Three temporal designs, with measured costs

| Design | Real implementation | Documented tradeoff |
|---|---|---|
| **Snapshot-per-commit** | **Compass history** — immutable graph realisations per commit in a SQLite/Prolly store outside git, keyed by SHA + extraction fingerprint; deltas are *computed views* | GC defaults 1 GiB / 30 days; quality bar topology-diff ≥2× faster than full diff; no absolute history size published. Software Heritage is the same idea at scale (~5 TB graph, ~200 TB with contents) |
| **Delta / change-based** | **TGI** (EDBT 2016) — Eventlist Partitions over DeltaGraph + Cassandra | The cleanest statement of the core tradeoff: *"Log requires minimal information to encode the graph's history, but incurs large reconstruction costs. Copy, on the other hand, provides direct access, but at the cost of excessive storage."* 266.7 M events; snapshot retrieval up to ~300 s. Risk: incremental analysis "does not guarantee that small code changes lead to small incremental updates" |
| **Interval / bitemporal edges** | **TPGM+** (`VAL_FROM`/`VAL_TO`/`TX_FROM`/`TX_TO`); **AeonG** hybrid current+historical with adaptive anchoring | AeonG: up to **5.73× lower storage**, **2.57× lower latency**, **9.74%** overhead. Dissent: **PETGraphDB** measures **~19.6×** cost for analytical temporal queries, arguing naive temporal-on-graph-DB "introduce[s] extra vertices and edges" |

**No published absolute storage/latency figure exists for a per-commit *code* knowledge graph**
(searched negative) — generic temporal-graph numbers are not measured on code graphs, so quoting
one without naming the workload is unsound. Closest reviewed system to a versioned code graph is
Compass history; jQAssistant is the natural host for interval edges (its store *is* a graph DB
with a general query language) but documents no rule-level valid-time. **CodeCompass should not
be described as a versioned graph store** — it documents incremental re-parse of the *current
workspace* only.

### 7.5 Ranked experiments for this section

- **E7 (highest value, low cost) — rule-vitality tracking.** Store per-rule `last_matched_commit`,
  `match_count`, and the selector's resolved node set; alarm when the selector resolves to an
  empty/near-empty set, or a rule has not matched for N commits while its subject package changed.
  Directly subsumes S3's "vacuous guard". This is a **3-field schema addition plus a query**.
- **E8 (medium) — measure the vacuity rate on the real constraint set.** The first empirical
  measurement of conformance-rule vacuity this review could locate (searched negative). S1's
  harness and this share the corpus.
- **E9 (medium) — add expiry to dismissals and A/B against pure freezing.** Owner + review-by date
  + justification; measure rule-set survival, re-justification rate, and regressions escaping the
  freeze. Hard part is the evaluation design, not the code.
- **E11 (low-medium) — "dismissal debt" trajectory.** For each persisted dismissal, re-evaluate the
  constraint at each subsequent commit: was it still justified, did the dismissed pattern spread?
  Methodological template is Gnoyke's per-instance "age"/"remaining age".
- **E10 (high) — cost-profile the three temporal designs** on a real Python repo over the same
  history: build time, storage, and (a) as-of-commit evaluation vs (b) violations introduced/
  removed between X and Y. A genuine bounded systems result, and the design choice constrains the
  schema, so it must be run **before** history is ingested at scale.

---

## 8. Generalising the graph beyond the four predicates

Asked: *the ADG is a graph; constraints are only one thing you can ask it; can the pattern and
structure be generalised?* Yes — and the useful result is a **tiering of what is computable
without changing the schema**, not a list of smells.

### 8.1 What is computable from a pure dependency graph

**Tier A — pure dependency / type-hierarchy graph (needs nothing new):** cycles and
strongly-connected components (hence Package Cycle, Clique); hub-like dependency (fan-in/fan-out —
DV8's *Crossing* uses fan-in ≥4 **and** fan-out ≥4, so its structural half is pure-graph); Martin's
instability inequality; Ce / Ca; instability `I = Ce/(Ca+Ce)`; Propagation Cost; cyclic/deep/wide
inheritance hierarchies.

**Tier B — graph plus token/size/cohesion/type attributes (needs node properties):** abstractness
`A`, and therefore distance `D = |A + I − 1|`, zones of pain and uselessness; God Component
(LOC-based); feature concentration (Lack of Component Cohesion); Improper Inheritance (needs edge
*types*, which the ADG has); containment/packaging rules (needs containment as a relation separate
from dependency edges — the ADG's `CONTAINS` already is).

**Tier C — graph + revision history (needs co-change edges):** **Modularity Violation**, the full
definition of **Crossing**, and **Unstable Interface**. DV8 states these "can only be detected
using both structural relation and co-change information". Any drift/erosion metric across
releases also lands here.

**Consequences for the ADG (these are inferences, labelled as such).** A pure
`IMPORTS`/`CALLS`/`INHERITS` graph over FQNs is **sufficient** for coupling, cycle, layer and
independence predicates; **insufficient** for abstractness/distance unless abstractness and
visibility are node attributes; and **insufficient for the entire co-change anti-pattern family**
unless history edges are added. Two further bounds: `CALLS` accuracy is capped by the Python
call-graph extractor (PyCG-class), and both `grimp`'s documentation and ArchUnit's documented
false-negative mode show **verdicts depend on graph completeness, not only on rule text**.

**Unresolved convention.** Sources disagree on whether Martin (1994) divides by 2 in
`D = |A + I − 1|`; this review does not settle it. The ADG must **pin one convention and store it
as rule metadata**, or thresholds become non-comparable across tools.

### 8.2 Is there evidence that a richer vocabulary helps?

**No study was found that tests the causal claim** (searched negative). The strongest available
evidence is a count-of-anti-patterns gradient, and it is correlational: Mo et al. (TSE 2021,
19 projects) report bug-file rate rising **0.3 (0 patterns) → 12.0 (6 patterns)** on one project,
Pearson `r` 0.61–0.98, project-level bug-rate increases of 117%–11,968%. Their two **most
impactful** anti-patterns are **Unstable Interface** and **Crossing** — both Tier C — and their
*least* impactful is Package Cycle, which is Tier A. That ordering is the single most useful
result in this section: **the predicates that need history edges are the ones with the strongest
observational evidence**, while the cheapest predicates to add have the weakest.

### 8.3 Precedent, and where Shepherd's moat actually is

Generalising a code graph into a query surface is **well-trodden**: jQAssistant exposes the whole
Neo4j graph via Cypher; CodeQL is a general relational query language over a code database;
ArchUnit documents cycles, layer conformance, slice independence, Ca/Ce, `I`, `A`, `D` and
visibility metrics. ArchUnit and the archived jQAssistant metrics plugin both derive
component-level dependency relations from element-level dependencies and write results back as
node properties — i.e. **Tier A+B is implementable as pure graph post-processing**.

So the graph substrate is **not** a contribution. Shepherd's moat is **decision anchoring +
memory**: the constraint is traceable to a specific ADR, and dismissals/supersession persist
across commits. A vocabulary extension is defensible only as *the thing that makes the decision
layer expressible*, never as "we built a code query language".

### 8.4 Ranked experiments for this section

- **E12 (low-medium) — widen along the Tier-A axis first and measure whether it changes anything.**
  All four families ship in ArchUnit, import-linter and DV8; no study tests whether adding them
  improves outcomes — so **the contribution is the measurement**, and the honest expectation is a
  null or modest result (Mo et al.'s Package Cycle was the *least* impactful). Cheapest because it
  needs no new node attributes.
- **E13 (medium-high) — add history edges and measure the co-change family.** The schema cost is
  real (history ingestion + co-change computation) but it is the one addition with strong
  observational evidence behind it (§8.2). Natural pairing with E10 — both need an ingested
  history, so build it once.
- **E14 (low) — instrument rule-vocabulary *usage*, not size.** Log which predicates actually fire
  per commit per rule; treat "rules that never fire" as the dependent variable. Dead configuration
  is the norm in adjacent tooling (a 2025 suppression study found **50.8% of 7,357 suppressions
  affect no warning**; a 2008 survey found 55% of teams do no filtering at all), so a bigger
  vocabulary mostly buys more dead rules unless usage is measured.

---

## 9. Caveats

1. **Correlation ≠ causation.** Every violation↔defect result is correlational or predictive; the
   only causal-flavoured data is a single-repo longitudinal paydown `[T2-S30]`. Do not claim
   conformance checking reduces defect rates.
2. **Java dominates the evidence.** DRSpace, anti-pattern, Arcan, ArDoCo and API-misuse lines are
   Java or C/C++. Python coverage is unverified — Shepherd's Python focus is a differentiator, but
   the evidence must be re-established for Python.
3. **Technical debt ≠ defects uniformly.** Zazworka et al. found only a *subset* of TD correlates
   with defect-proneness `[T2-S14]`; Martini's industrial work ties architectural debt to
   effort/rework, not defect counts `[T2-S12]`. Do not overclaim.
4. **No released, code-level, labelled ADR/decision-violation benchmark exists** (any language) —
   the case study must construct its own labelled set (history-mined + injected), which is both
   the contribution and the validity risk. Scope this claim carefully: SmellBench covers
   Python architectural *smells*, and the OpenStack datasets cover review *text* (§2.4).
5. **Rejected leads** (do not cite): "DREd" — no such tool/paper; "ADRam" — unverifiable; Arcan is
   Arcelli Fontana et al. (ICSAW 2017), not de Silva & Balasubramaniam; BugsInPy is arXiv
   **2401.15481**, not 2005.01176; SpecRover is arXiv 2408.02232, not 2408.01832.
6. **UNVERIFIED residues:** the TSE 2019 anti-pattern subject languages `[T2-S5]`; the OpenStack
   erosion replication package download URL `[T3-30]`; the Archie DOI; the Bench4BL language
   label; Defects4J's version-pinned count (v2.0.0: 835 vs current v3.0.1: 854 — and note the
   secondary-source claim of "17 systems" conflicts with the repo's own table naming 11 projects).
   Paixao et al. TSE 2021 is **no longer** on this list — resolved in the verification pass via the
   open-access UCL copy (§5/S5).
7. **The five ADR-error-taxonomy percentages (42.39 / 26.09 / 17.4 / 9.78 / 4.35) are
   auto-report-mediated and remain UNVERIFIED.** They come from an LLM-generated summary of
   arXiv:2602.07609, not a line-by-line read of its tables — re-derive before use. The paper's
   HTML *was* readable first-hand for the 24.7% CIA figure, so this is feasible.
8. **"Searched negative" is search-scoped, not proof of absence.** Those claims rest on the query
   sets recorded in the research notes, not on a documented multi-database protocol. Read them as
   "not found within this review's searches", never as "does not exist".
9. **Martin's `D` divisor is unresolved** (`D = |A + I − 1|` vs `|(A + I − 1) ÷ 2|`). Pin one
   convention and store it as rule metadata before the ADG computes distance (§8.1).
10. **Several results in this brief are single-source and load-bearing** — the fragility analysis
    is in the reviewer report (`notes/feynman-2026-09-25/deepseek-run2/`). The three that matter
    most: CodeCureAgent's change-approver ablation (sole quantitative justification for an
    analyzer-clean gate), DRCodePilot's `-DR` ablation (sole evidence that rationale text moves
    repair outcomes), and Maffort's SGA result (sole empirical basis for rule-vitality). Each is
    named inline where it is used.
11. **Claim-level verification was bounded.** All URLs, arXiv IDs and DOIs in the underlying
    review were link-verified; quantitative re-reading was limited to a spot-check table. Two
    load-bearing ablations were read from full-text notes but not re-tabulated line-by-line.

---

## 10. What I would do next (smallest useful steps)

1. **Quantify the addressable fraction at scale (this is the experiment that tests §3's premise,
   not a confirmation of it).** Run the census over the ADR-Study-Dataset / 980-ADR / 4,911-ADR
   corpora and report the convertible-ADR rate. If 26% holds, that single number reframes the
   paper from "detector" to "the ADR-to-checkable gap is the bottleneck" — and justifies the
   ontology work. **If it does not hold, §3's framing changes and the ontology argument loses its
   quantitative base** — so pre-register the direction of interest. Cheap; census is already a
   script. Stratify by ADR content class, since the predicted drivers are infrastructure/
   deployment and principle-oriented ADRs (42.39% + 26.09% of extraction errors — but see §9
   item 7: those five percentages are **auto-report-mediated / UNVERIFIED**).
2. **Build S2 first** — a `git log` driver over `cpt detect --commit`, reusing everything.
   Pre-register the null hypothesis before running it.
3. **Measure S3 as a table** (vacuous constraints per repo at the pinned commits) before building
   anything.
4. **File the stale-dismissal gap (§5.3 item 14) as an issue** — independent of the research
   direction and affects current users.
5. **Build S1's harness** — the oracle is `cpt detect`; the only new component is the ADG-on/off
   agent harness, which `commit_set.md` and the Pi baseline half-supply.
6. **Canonicalise the evidence path (§7.3 item 2) before persisting or comparing any path.**
   `grimp`'s documented non-determinism means two runs over the same graph can name different
   equal-length routes; any experiment that diffs evidence paths across commits is unsound until
   this is pinned. Small, and it gates E7/E11.
7. **Implement E7's three fields (§7.5)** — `last_matched_commit`, `match_count`, resolved selector
   set. Smallest change with a documented failure mode behind it, and it is a prerequisite for E8.
8. **Run the author-side experiment (§4)** — reuse the two-arm apparatus, but ask the agent to
   *implement* the change rather than review it. **No new arm, no new dataset, no new annotation:**
   the task set is the existing `benchmark/gold/*_instances.json` (60 cases; 31 in scope, 25
   controls), the oracle is CPT applied to the agent's own diff, and arm (C)'s relevance input is
   the case's own target path — no localization work. Scope the claim to **compliance**, not
   correctness (no fail-to-pass tests exist here), and pair it with the non-degeneracy check. Build
   the non-degeneracy check *before* the first run, not after.

---

## Sources

**Verified in this pass:** Lenarduzzi et al., SANER 2020 (*Are SonarQube Rules Inducing Bugs?*);
Xiao/Cai/Kazman, ICSE 2014 (DOI 10.1145/2568225.2568241); Xiao/Cai/Kazman/Mo/Feng, ICSE 2016
(*Identifying and Quantifying Architectural Debt*); Kazman et al., ICSE-SEIP 2015 (DOI
10.1109/ICSE.2015.146); Mo/Cai/Kazman/Xiao/Feng, TSE 2019 (DOI 10.1109/tse.2019.2910856); Le et al.,
ICSA 2021 (arXiv:2102.09835); arXiv:2303.17862; arXiv:2010.15978; Jimenez et al., SWE-bench
(arXiv:2310.06770); Widyasari et al., BugsInPy (arXiv:2401.15481); Wang et al., CodeRAG-Bench
(arXiv:2406.14497); Tang et al., LLM4SZZ (arXiv:2504.01404); Yang et al., SWE-agent
(arXiv:2405.15793); Xia et al., Agentless (arXiv:2407.01489); Maffort et al., EMSE 2016 (online
2015; DOI 10.1007/s10664-014-9348-2; tool: ArchLint); Paixao et al., TSE 2021 (DOI
10.1109/tse.2019.2912113; OA copy at UCL Discovery); SmellBench (arXiv:2605.07001).

**From the Feynman run 1 (per-RQ files `T1`–`T4`, source keys above):** DRSpaces/ArchRoots, ArDoCo
(ICSA 2023), LiSSA (ICSE 2025), CogniCrypt (ASE 2017), MUDetect (MSR 2019), Paixao et al. (TSE
2021, UNVERIFIED), MULocBench (arXiv:2509.25242), LocAgent/LocBench (arXiv:2503.09089), SWR-Bench
(arXiv:2509.01494), CodeFuse-CR-Bench / SWE-CARE (arXiv:2509.14856), PyMigBench (MSR 2023),
CodeMEnv (arXiv:2506.00894), SWE-Gym (arXiv:2412.21139), SWE-smith (arXiv:2504.21798), the
LLM×architecture SLR (arXiv:2505.16697), the LLM ADR-violation study (arXiv:2602.07609),
ADR-Study-Dataset (IEEE Access 2023), LLM4ADR/DRAFT (arXiv:2504.08207), AgentSZZ
(arXiv:2604.02665).

**Added by Feynman run 2 (citation-verified; full reference list in that report's §10):** ArchUnit
(`FreezingArchRule`, metrics, false-negative mode); SonarQube `Accepted`/New Code Definition;
import-linter (`ignore_imports`, `exhaustive`, `unmatched_ignore_imports_alerting`); `grimp`
(illegal-route non-determinism; silent-ignore of missing modules); jQAssistant; Structure101; DV8
(anti-pattern catalogue, three structural + three history-dependent); Mo et al., TSE 47(5), 2021
(19 projects; UIF and Crossing most impactful); Mo et al., WICSA 2015; Compass history
(snapshot-per-commit); TGI (EDBT 2016); TPGM+ (arXiv:2111.13499); AeonG (PVLDB 17(6), 2024;
arXiv:2304.12212); PETGraphDB; Software Heritage; Gevol; CodeCompass; Okun (consistent mutants);
Wang et al., ICPC 2022 (46 static-analysis rule bugs) — **cite the computer.org URL, the printed
DOI is inconsistent**; Hu et al. 2025 (50.8% of suppressions affect no warning); Ayewah et al.
2008; Sonargraph 15.2.0 metric-definition change; InferFix (arXiv:2303.07263, not 2305.12050);
RepairAgent (arXiv:2403.17134, not 2403.03954); CodeCureAgent; DRCodePilot (arXiv:2408.12056);
SmellBench (two distinct artefacts — see §2.4).

**Rejected as non-existent or mischaracterised (do not cite):** "SAND" as an LLM-repair system
(it is a fuzzing framework, arXiv:2402.16497); "Repilot" as analyzer-assisted repair (it fuses an
LLM with an *Eclipse JDT completion engine* — no analyzer finding in the loop); Sourcetrail
"timeline" (discontinued, repo archived Dec 2021, no history feature documented); "EvoGraph" and
"GitGraph" (not found with verifiable documentation); PyCG as arXiv:2103.14295 (it is
arXiv:2103.00587); the CPG paper as arXiv:1604.05976 (that is a drug-repositioning paper; the CPG
work is Yamaguchi et al., IEEE S&P 2014); a paper titled "(Eco)Architecture smells" as
arXiv:1703.10562 (solar physics — the real line is Mo/Cai/Kazman design-rule-space).
