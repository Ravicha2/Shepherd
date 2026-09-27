> **Source:** [`notes/feynman-2026-09-25/deepseek-run2/shepherd-adg-decision-memory.md`](../notes/feynman-2026-09-25/deepseek-run2/shepherd-adg-decision-memory.md) @ `e3f0f17` — this page is a **copy** of the file above,
> kept here for browsing. Edit the source, not this page; regenerate with the
> command in [README.md](README.md).

# Shepherd's Architectural Decision Graph: evidence review and ranked experiments

**Topic:** persistent architectural-decision-memory over source code (tool: Shepherd) — an Architectural Decision Graph (ADG) built from a Python repo plus its ADRs, with constraint-path traversal over commit diffs, persisted dismissals, and decision supersession tiers.

**Date:** 2026-09-25
**Deliverable type:** cited research brief with ranked, evidence-backed experiments
**Slug:** `shepherd-adg-decision-memory`

---

## Citation verification log

Verified 2026-09-25 by the verifier pass. Method: `curl -L` with a browser user-agent against every distinct URL in the brief (190, including 4 URLs added by this pass across 3 new source entries — see the addendum below); the arXiv API (`id_list`) for every arXiv ID (43); Crossref REST (`api.crossref.org/works/<doi>`) plus doi.org content negotiation for every DOI (40); record lookups against Crossref/OpenAlex/DataCite for the load-bearing papers; and direct fetch of the primary artefact for five claims whose research note recorded a second-hand or auto-report provenance.

### URL checks (190 distinct URLs)

| Class | Count | Status | Action |
|---|---|---|---|
| HTTP 200 | 151 | live | kept as-is (incl. the 3 URLs added by this pass) |
| HTTP 202 (bot-wall, redirect-in-progress) | 16 | live | kept; 14 `doi.org/10.1109/...` (IEEE) + 2 `ieeexplore.ieee.org`. All 16 confirmed to resolve to the cited *record* via Crossref metadata (title/year match — this confirms the record, not that the record supports every claim drawn from it) |
| HTTP 403 (bot-wall) | 21 | live | kept; enumerated breakdown 8 `dl.acm.org`, 10 `doi.org/10.1145/...`, 1 Wiley (`10.1002/smr.2398`), 1 ScienceDirect, 1 `techrxiv`, 1 `lattix.com` PDF — **note: this enumeration sums to 22 against a counted 21; one entry appears to be double-classified. Row totals still reconcile to 190 (151 + 16 + 21 + 2).** All confirmed live via Crossref/doi.org metadata |
| HTTP 404 (dead) | 2 | dead | corrected — see below |

Corrected entries (wrong URL in the draft, replaced in [41]/[60]):

| URL as drafted | Status | Corrected to | Status |
|---|---|---|---|
| `https://www.javadoc.io/static/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/freeze/TextFileBasedViolationStore.html` | 404 | `https://javadoc.io/doc/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/freeze/TextFileBasedViolationStore.html` | 200 |
| `https://www.javadoc.io/static/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/metrics/ComponentDependencyMetrics.html` | 404 | `https://javadoc.io/doc/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/metrics/ComponentDependencyMetrics.html` | 200 |

No other dead or wrong-target URL was found. Two URLs resolve but must not be read as ordinary sources: `https://www.techrxiv.org/doi/10.36227/techrxiv.177205025.54351571` returns 403 (the draft already marks `sqlew` full text blocked and cites no numbers from it), and `https://www.lattix.com/wp-content/uploads/2024/03/DesignRules.pdf` returns 403 (the same Lattix claims are also carried by two `docs.lattix.com` pages that return 200).

Sources added by this pass (claims whose support existed in the research notes but had no entry in the draft's source list): `https://w3c.github.io/sdw/UseCases/SDWUseCasesAndRequirements.html#ValidTime` (200) → [107]; `https://codeql.github.com/docs/ql-language-reference/about-the-ql-language/` and `.../ql-language-specification/` (200) → [108]; `https://github.com/jqassistant-plugin/jqassistant-jmolecules-plugin` (200) → [109].

Sources demoted by this pass: 14 entries that were listed in §10 but carry no inline citation in §1–§9 (PredicateFix, StaticFixer, Redemption, RepairBench, LLM APR survey, ADR extraction from commits, ADR text mining/classification, specification-format × model, THEMIS, Brunet WCRE 2012, pydeps, Garcia QoSA 2009, Le architectural decay, Li erosion survey). They keep their verified URLs in an unnumbered list at the end of §10 so that no numbered source is an orphan; no claim was deleted to achieve this.

### arXiv ID checks (43 IDs)

All 43 resolve through the arXiv API; every one returns the work the draft attributes to it. No title mismatch was found. Three entries are the *deliberate* corrections the brief carries: `2103.14295` = "Reinforcement Learning for Robust Parameterized Locomotion Control of Bipedal Robots", `1604.05976` = "Computational Drug Repositioning Using Continuous Self-controlled Case Series", `1703.10562` = "Relative magnetic helicity as a diagnostic of solar eruptivity" — i.e. the draft's statements that these IDs are wrong are confirmed.

Record-matching notes (preprint vs venue records):

| Case | Records matched | Result |
|---|---|---|
| DRCodePilot, `2408.12056` / `10.1145/3691620.3695537` | arXiv record **and** Crossref venue record both return the title "Enhancing Automated Program Repair with Solution Design" (2024) | System name *DRCodePilot* confirmed; the research note's second title variant ("…with Design Rationales") attaches to the same work — both recorded, neither asserted alone |
| InferFix, `2303.07263` / `10.1145/3611643.3613892` | arXiv preprint (2023-03-13) **and** OpenAlex venue record `W4389158474` (FSE 2023, pages 1646–1656) | Same title in both records; matched |
| `2608.21747` | arXiv title is "Architecture as Capability Equalizer for Coding Agents", not the §10 label "Specification-format × model interaction" | Label is descriptive, not a title claim; the entry carries no inline citation (see §10 note) |
| `2609.14913` | arXiv title "Externalizing Requirement-to-Repair Artifacts as Observable Traces for LLM-Based Program Repair"; system name **THEMIS** confirmed in the abstract | Matched; entry carries no inline citation (see §10 note) |
| `10.5281/zenodo.19247588` | DataCite: "SmellBench: Evaluating LLM Agents on Architectural Code Smell Repair - ExperimentsReproductionPackage" (2026) | Matches the draft's SmellBench data DOI |
| `10.58012/tfvg-1k55` | doi.org content negotiation: "Redemption: A Prototype for Automated Repair of Static Analysis Alerts" (2024) | Matches; entry carries no inline citation |

### DOI checks (40 DOIs)

Crossref returned a title, year and container for 37 of 40 directly; the remainder were resolved through doi.org content negotiation (DataCite/TechRxiv). Every returned title and year matches the attribution in the draft. Two recorded oddities, both already in the draft: `10.1145/3786583.3786910` is registered as an ICSE 2026 proceedings paper (the draft calls it "the Tencent industrial study", which matches the returned title *Reducing False Positives in Static Bug Detection with LLMs: An Empirical Study in Industry*), and the Wang et al. ICPC 2022 DOI printed in the source is inconsistent (draft already says to cite the computer.org URL instead).

### Quantitative spot-checks (claim → source → result)

| Claim | Source checked | Result |
|---|---|---|
| InferFix top-1 exact-match 76.8% Java / 65.6% C# | arXiv 2303.07263 abstract; Crossref/OpenAlex [1] | Confirmed in abstract |
| CodeCureAgent 96.8% plausible / 86.3% correct | arXiv 2509.11787 abstract; Crossref [2] | Confirmed in abstract |
| CodeCureAgent approver ablation 0 / 9 / 123 / 249 false accepts per 1,000 | research note rq1a §2.2 (full-text read) [2] | Traceable to the full-text read; paper tables not re-read this pass |
| SmellBench 47.7% resolved, 63.1% detector false positives | arXiv 2605.07001 abstract [3] | Confirmed in abstract |
| SmellBench 140 new smells / net −109 | research note rq1a §2.2 (paper body; tables did not extract) [3] | Traceable; the draft already records that the arXiv tables did not extract |
| DRCodePilot 4.7× / 3.6× and −81.65% / −94.44% ablation | arXiv 2408.12056 abstract (4.7×); rq1a/rq1b full-text reads (ablation) [8] | Abstract confirms 4.7×; ablation figures traceable to the full-text read |
| Repilot +27% / +47% more bugs | arXiv 2309.00608 abstract [7] | Confirmed in abstract |
| Li et al. 25.9% → 64.7% developer detection | arXiv 2306.08616 abstract [22] | Confirmed in abstract |
| PredicateFix +27.1%–69.3% | arXiv 2503.12205 abstract (entry now uncited) | Confirmed; no inline claim depends on it |
| DRMiner F1 65%, +7% over GPT-4.0 | arXiv 2405.19623 abstract [99] | Confirmed in abstract |
| 24.7% "Code is Insufficient to Answer" class frequency (980 ADRs / 109 repos) | arXiv 2602.07609 **HTML v1** [21] | Confirmed first-hand: "the average agreement for label 'CIA' is only 0.1574, with a relative frequency of 24.7%". Provenance upgraded from the lead's alphaXiv auto-report to the paper's own text |
| AeonG 5.73× storage / 2.57× latency / 9.74% overhead | arXiv 2304.12212 abstract (9.74%); rq2 PVLDB PDF read [53] | Abstract confirms 9.74%; the other two traceable to the PDF read |
| Context-file ablation bounded to ≤10–15pp | arXiv 2607.27250 abstract [25] | Confirmed in abstract |
| `promtool test rules --coverage` / `--coverage-threshold` / "Coverage here is assertion presence, not expression branch coverage." | GitHub `prometheus/prometheus` PR 18432, fetched directly [46] | Confirmed first-hand, verbatim |
| "removal-based tool … deleting one rule at a time in isolated worktrees" | `Yiwit/rulecov` README, fetched directly [46] | Confirmed first-hand ("it removes one rule at a time, runs your agent on the same small task in isolated git worktrees") |
| System name **AssistRA** | author-hosted PDF `riccardorubei.github.io/files/W_2025_1.pdf`, fetched directly [9] | Confirmed first-hand; ICSA-C DOI title is the paper title, not the system name |
| Defects4J "835 bugs, 17 systems" | research note rq1b §Q3.1 — records an **unresolved discrepancy** (secondary sources say 17 systems; the repo's own table names 11 projects) | Kept, with the discrepancy noted inline at §3.4 |

Result — **split by assurance level.** **Link-verified:** all 190 URLs resolve, and all 43 arXiv IDs and 40 DOIs return the work the brief attributes to them (two dead javadoc URLs corrected, above). **Claim-verified:** the quantitative claims in the spot-check table below were re-checked against the primary artefact. **Not claim-verified in this pass:** (i) CodeCureAgent's change-approver ablation table (research note rq1a §2.2, full-text read; paper tables not re-read here), (ii) DRCodePilot's `-DR` ablation figures (research-note full-text reads; not re-read here), (iii) the five ADR-error-taxonomy percentages in §5.6/E16 and §8 (**auto-report-mediated only** — now marked `UNVERIFIED` inline). No claim was found untraceable *to a source*; claim-level re-reading was limited to the spot-check table below. The draft's existing `UNVERIFIED` and "searched negative" markers are preserved verbatim, and the requester's ~25% ADR-convertibility premise remains unverified.

Final arithmetic: 109 numbered sources; 109 cited at least once in §1–§9; 0 numbered sources without a citation; 0 inline citations without a numbered source; 14 verified-but-uncited entries listed without numbers.

---

## 1. Executive summary

1. **RQ1 — repair is well evidenced, but for warnings, not for architectural decisions.** The literature contains three load-bearing systems: **InferFix** (top-1 exact-match 76.8% Java / 65.6% C#, analyzer re-validated in CI) [1], **CodeCureAgent** (96.8% plausible / 86.3% correct over 1,000 SonarQube warnings, with a TP/FP classification stage first) [2], and **SmellBench** (best LLM agent resolves 47.7% of architectural smells but the most aggressive agent introduces 140 new smells — net −109) [3]. Every analyzer-conditioned system reviewed feeds **structured analyzer metadata, never a bare warning message**; and each of those with a *documented* acceptance oracle (InferFix, CodeCureAgent, SmellBench, Patch Space Exploration) re-runs the analyzer (or an analyzer-equivalent) for acceptance [1, 2, 3, 10]. The two deployed vendor systems (**Copilot Autofix**, **Semgrep Autofix**) document no **automated** acceptance oracle (Copilot Autofix documents human review only), so the re-run pattern holds for **4 of the 6 analyzer-conditioned systems reviewed here, not universally** [13, 14]. The one ablation that removes the analyzer/approval gate shows falsely-accepted patches rising from **0 to 123 per 1,000** [2].

2. **The exact experiment Shepherd needs has not been run.** **Exactly one *readable* system** feeds design-rationale text into a *repair* prompt — **DRCodePilot** (the one ADR-to-persistent-context system, the `sqlew` preprint, is characterised as generation-side from its abstract/landing page only, its full text being HTTP 403 — see §3.3) — and its leave-one-out ablation is dramatic: removing the rationale section collapsed full-match counts by **81.65% and 94.44%**. But DRCodePilot uses *issue-log* rationale, an exact-match metric, **no tests, and no analyzer** [8]. Among works whose **full text could be read**, no study feeds **ADR / architectural-decision** text as a distinct repair input to fix an **architecture-rule violation** with a deterministic analyzer oracle, and none isolates *(a) verdict alone vs (b) verdict + graph evidence path vs (c) verdict + evidence path + rationale* [8, 9]. That cell is **unoccupied within the readable corpus — not proven empty**: three nearest candidates could not be read (the `sqlew` ADR-to-context preprint, full text HTTP 403 [19]; the three Schröder ontology papers, metadata only [104]; the ICSM 2008 live-feedback experiment, authors and results not retrievable [105]). See §3.3 and §9.

3. **RQ2 — temporal rule validity is a real, documented gap, and there is direct evidence that silence is ambiguous.** **Maffort et al. (EMSE 2016)** found that in one subject system **53% of "Insert Missing Dependency" changes happened in the first year**, and after discarding four years of revisions **no violations at all were detected**; in another subject, entrenched violations were missed because the *rule had gone stale* [32]. No mainstream conformance tool implements `valid_from`/`valid_to` — verified against ArchUnit, SonarQube, import-linter, jQAssistant and mainstream ADR templates, and against DCL/DCLsuite at **abstract/tool-page level only** [41, 42, 43, 44, 45, 33]. **Freezing** (ArchUnit; can only shrink, never expire) and **expiry** (nobody) are different axes and no reviewed tool has both [41, 42, 43]. **Vacuous-rule detection has no academic literature** (**searched negative**) [46, 47, 48], but the failure mode is documented as *engine behaviour*: `grimp` (the engine behind import-linter) states that rule targets which no longer exist "will be silently ignored." [67]

4. **RQ3 — the ADG's four predicates sit at the narrow end of a much larger rule vocabulary space.** ArchUnit documents cycles, layer conformance, slice independence, Ca/Ce, instability `I = Ce/(Ca+Ce)`, abstractness `A`, distance `D`, and visibility metrics [60]; jQAssistant exposes the whole Neo4j graph via Cypher plus an OOD-metrics plugin [44, 61, 72]. **A pure `IMPORTS`/`CALLS`/`INHERITS` graph over FQNs is sufficient** for coupling, cycle, layer and independence predicates, **insufficient** for abstractness/distance unless abstractness and visibility are node attributes, and **insufficient for the entire co-change anti-pattern family** (Modularity Violation, Crossing, Unstable Interface) which DV8 states require structural *and* co-change information (— this whole Tier A/B/C consequence is an **inference**, argued in full at §5.2) [60, 69, 67].

5. **The claimed evidence for "richer vocabulary improves outcomes" is weak and observational.** No study was found that tests the causal claim. The strongest available is a **count-of-anti-patterns gradient**: Mo et al. (TSE 2021, 19 projects) report bug-file rate rising from **0.3 (0 patterns) to 12.0 (6 patterns)** on one project, Pearson `r` 0.61–0.98, project-level bug-rate increases of 117%–11,968% [80]. That is correlation, not a rule-count intervention.

6. **Shepherd's own quantitative premise (~25% of real ADRs convertible to checkable constraints) is UNVERIFIED.** No source reports an ADR→checkable-constraint conversion rate. The nearest data point is a *different* measurement: in 980 ADRs across 109 repos, an LLM judged 24.7% of sampled cases "Code is Insufficient to Answer" [21] — an analogy, not a confirmation, and it must not be presented as one (and the same source reports low inter-model agreement for that label, average agreement 0.1574, so the figure is soft even on its own terms).

7. **Several named systems in the brief do not exist as described.** "SAND" is not an LLM-repair system (it is a fuzzing framework, arXiv 2402.16497) [15]; "Repilot" is not analyzer-assisted repair (it fuses an LLM with a *completion engine* for type-aware token pruning) [7]; two arXiv IDs in the brief point at unrelated papers [16, 17]; and Sourcetrail's "timeline" capability is **not substantiated** by its documentation (the project is discontinued/archived as of 2021) [58]. Details in §6.

---

## 2. Method, scope, and how to read confidence

**Approach.** Five parallel evidence-gathering streams (RQ1a repair systems; RQ1b rationale + experiment design + benchmarks; RQ2 temporal; RQ3a tooling/vocabulary; RQ3b metrics/DSL failure modes) plus lead-owned anchor verification. Research notes:

- `outputs/.drafts/shepherd-adg-decision-memory-research-rq1a-repair.md`
- `outputs/.drafts/shepherd-adg-decision-memory-research-rq1b-rationale-bench.md`
- `outputs/.drafts/shepherd-adg-decision-memory-research-rq2-temporal.md`
- `outputs/.drafts/shepherd-adg-decision-memory-research-rq3a-tools.md`
- `outputs/.drafts/shepherd-adg-decision-memory-research-rq3b-metrics-dsl.md`
- `outputs/.drafts/shepherd-adg-decision-memory-research-direct.md` (lead-owned searches)
- `outputs/.plans/shepherd-adg-decision-memory.md` (plan, ledger, verification log)

**Reading the confidence labels.**

| Label | Meaning |
|---|---|
| **Established** | Multiple independent primary sources agree, or a primary source reports it directly and it has been read in full text. |
| **Reported** | A single primary source states it; the number is quoted as reported, not independently replicated. |
| **Single-study** | One study, often small n; do not generalise. |
| **Searched negative** | Targeted queries found nothing. This is *evidence of absence within the search*, not proof of global absence. |
| **Unverified** | Asserted by the requester or a vendor/preprint and not checkable from primary text. |

**Scope limits of this review.** Paywalled venues (IEEE, Elsevier, Springer, ACM) were read at abstract/landing-page level where no green-OA copy existed; that is flagged per claim in the research notes. No claim here rests solely on a paywalled abstract without being marked as abstract- or snippet-level; the §5.3–§5.4 consolidation tables carry per-row read-level markers. Two named systems in the brief ("EvoGraph", "GitGraph") could not be located as documented code-evolution graph systems and are therefore excluded rather than described (**searched negative**, RQ2 research note §Coverage Status).

---

## 3. RQ1 — Finding actionability and agentic repair

### 3.1 What is established about LLM repair of analyzer findings

| System | Input signal | Headline result (as reported) | Oracle | Source |
|---|---|---|---|---|
| **InferFix** (ESEC/FSE 2023) | 5 blocks: 2 retrieved similar fixes, bug-type annotation, eWASH syntactic hierarchy + peer methods, focal method from the **Infer stack trace**, buggy method marked with Infer line numbers | top-1 exact-match **76.8% Java / 65.6% C#** | build + tests + **re-run Infer** in CI | arXiv 2303.07263; DOI 10.1145/3611643.3613892 — [1] |
| **CodeCureAgent** (PACMSE/FSE 2026) | 6 sections; warning = **7 SonarQube fields** (Repository, RuleKey, FilePath, StartLine, RuleName, SpecificMessage, RuleType) + agent history; repair agent also receives the classifier's verdict **and its explanation** | **96.8% plausible** / **86.3% correct** on 1,000 warnings; classification TP 97.4%, FP 81.0% | build + **target warning gone + no new warnings** + tests | arXiv 2509.11787; DOI 10.1145/3808140 — [2] |
| **SmellBench** (architectural smells, scikit-learn, 65 hard-severity) | smell type/name, **PyExamine detection report (instance, entities, severity metrics)**, affected files/modules, smell-specific playbook, 3 few-shot demos | best agent **47.7% resolved**, but most aggressive agent introduces **140 new smells → net −109**; **63.1% of detected smells are expert-verified false positives** | **re-run PyExamine** + full test suite + expert review of all 715 outcomes | arXiv 2605.07001 — [3] |
| **RepairAgent** (ICSE 2025) | 8-section dynamic prompt over a finite state machine, 14 tools; **no analyzer warning** | 164 correct / 186 plausible of 835 Defects4J bugs; 39 fixed by no baseline | **tests only** | arXiv 2403.17134; DOI 10.1109/ICSE55347.2025.00157 — [5] |
| **ChatRepair** (ISSTA 2024) | buggy code + failing-test feedback, conversational | 162/337 Defects4J bugs at **$0.42 each** | tests | arXiv 2304.00385; DOI 10.1145/3650212.3680323 — [6] |
| **Repilot** (ESEC/FSE 2023) | LLM + Eclipse JDT **completion engine** for type-aware token pruning | +27% / +47% more bugs fixed on Defects4J 1.2 / 2.0 | tests | arXiv 2309.00608 — [7] |
| **Copilot Autofix** (deployed) | SARIF alert data, ~10 lines from each involved file, **CodeQL query help text** | not stated in the responsible-use doc | **human review only — no automated acceptance oracle documented** | GitHub docs — [13] |

**Two patterns are established:**

- **P1 — Every analyzer-conditioned system feeds more than the message.** InferFix feeds location and stack trace [1]; CodeCureAgent feeds seven structured fields [2]; SmellBench feeds a detection report with severity *metrics* [3]; Copilot Autofix feeds alert + query help + bounded file context [13]. No reviewed system conditions on a bare warning string (**searched negative**) [1, 2, 3, 13].
- **P2 — Every analyzer-conditioned system with a *documented* acceptance oracle re-runs the analyzer for acceptance** (InferFix, CodeCureAgent, SmellBench, Patch Space Exploration). **This is 4 of the 6 analyzer-conditioned systems reviewed here, not universal:** Copilot Autofix and Semgrep Autofix are analyzer-conditioned but document no automated acceptance oracle [1, 2, 3, 10, 13, 14]. (Auditability note: Patch Space Exploration [10] is analyzer-validated but has no row in the table above; Semgrep Autofix [14] is documented only from its Autofix page.) The single strongest quantitative support for this design: CodeCureAgent's change-approver ablation per 1,000 warnings — full approval **968 (96.8%) plausible, 0 false accepts**; without tests **961 (96.1%), 9 false accepts**; without static analysis *and* tests **861 (86.1%), 123 false accepts**; no approval at all **751 (75.1%), 249 false accepts**. Source: arXiv 2509.11787 [2].

**Shepherd's "re-check the constraint after the fix" gate is therefore consistent with the strongest evidence base, not an unvalidated risk** [2, 3]. **The evidence-path component is *not* evidence-backed:** no reviewed system feeds a graph evidence path [1, 2, 3, 13, 67], and whether a path adds anything over the verdict is unknown (§7 Q2; E6 is exploratory). The two components of the design must be described separately.

### 3.2 What is reported but not replicated

- **CodeCureAgent's costs:** mean **2.9¢ per warning**, mean 4.4 min end-to-end (median 2.8), unfixed warnings mean 14.0 min and **21¢**, mean **139K tokens/warning** (78.8% cached input), 40-cycle repair budget (fixed warnings average 8 cycles; failures consume all 40) [2].
- **RepairAgent's budget:** median ~**270K tokens ≈ 14¢/bug**, median 920 s/bug, 35 tool calls/bug; `write_fix` yields plausible patches on ~7% of invocations for unfixed bugs vs 44% for fixed bugs [5].
- **SmellBench's regression mechanics:** the −109 net result is attributed to "module consolidations that create new dependency violations"; agents converge on ~18 resolved (27.7%) — four of ten non-baseline agents land at exactly 18, and among the top eight agents no pair differs significantly (p>0.05, Cliff's |δ|<0.13; Kendall's W = 0.939, χ²=65.71, df=10, p<0.001) [3].
- **Patch-overfitting background:** correct patches are sparse, and incorrect patches that pass all tests are "orders of magnitude more abundant" (arXiv 1602.05643) [18].

### 3.3 Rationale-fed repair: the single precedent, and the gap

**DRCodePilot** (ASE 2024, arXiv 2408.12056, DOI 10.1145/3691620.3695537) injects a **"Design Rationale"** section — solution–argument pairs mined from **Jira issue logs** by DRMiner [99] — as one of five prompt sections [8].

- 938 issue–patch pairs (Flink 714, Solr 224). Full-match: **109/714** and **18/224**, vs GPT-4's 23/714 and 5/224 (**4.7× / 3.6×**). CodeBLEU +5.4% / +3.9% [8].
- **The isolating ablation:** `DRCodePilot-DR` (rationale removed) — full-match **−81.65% / −94.44%**, CodeBLEU **−9.17% / −4.87%**. Weaker ablations: `-ID` (identifiers) −3.67% / −5.55%; `-PF` (patch feedback) unchanged on Flink [8].
- **Caveats the authors state themselves:** rationale is "often abstract and can sometimes be conflicting"; it "offer[s] only high-level recommendations"; **no test oracle** was used ("less than 1% are amenable to executable evaluations"); and the benchmark is **conditioned on issues that have rationale** [8].

**Everything else is a negative.** No design-intent, rationale, ADR or decision text appears in InferFix [1], RepairAgent [5], CodeCureAgent [2], ChatRepair [6], Repilot [7], Copilot Autofix [13] or Semgrep Autofix [14] prompts. SmellBench's agents get a detector report and a hand-written playbook; the paper itself frames the gap — architectural smells "require reasoning about design intent, dependency structures, and framework conventions" involving "design invariants that are **nowhere explicitly documented**." [3]

**Two near-misses worth knowing about, neither of which is the experiment Shepherd needs:**

- **AssistRA** (ICSA-C 2025, DOI 10.1109/ICSA-C65153.2025.00063) is the nearest *architectural* analogue: it feeds an LLM the reference-architecture model, the as-implemented model and a violation tuple, over 16 mutated faulty architectures, reporting **90% (Gemini) / 70% (ChatGPT)** success. It **deliberately withholds** extra information "to ensure a generic and unbiased query", reports **no ablation**, and puts rationale in the *output*, not the input [9].
- **CodeCureAgent** consumes a rationale — but the **classifier's** rationale, not a project decision's. Its classification agent explicitly asks whether "the developer may have intentionally violated the rule (e.g., for **functional or design reasons**)" [2] — i.e. the field's current answer to "the rule conflicts with intent" is **classify-and-suppress**, not feed intent and repair toward it.
- **sqlew** (TechRxiv preprint, DOI 10.36227/techrxiv.177205025.54351571) is the only located work that operationalises *ADR → persistent context → LLM code generation* (ADRs via MCP + Claude Code Hooks) — **a characterisation drawn from the abstract/landing page only; the full text returned HTTP 403, was re-checked this pass and is still 403, and no numbers may be cited from it** [19]. Because it is unreadable, its exclusion from the "repair prompt" category in §1.2 is a judgement about an abstract, not a verified finding.

### 3.4 Benchmarks and harnesses: what exists, and the exact gap

**General Python repair benchmarks** (host for a fix loop, but not architecture-scoped): SWE-bench (2,294 problems) [26], SWE-bench Verified (**500**, human-validated) [26], SWE-Gym (2,438 tasks / 11 repos, executable envs; Lite 234) [27], SWE-smith (**50,137** training instances / 128 repos) [28], BugsInPy (**493 real bugs / 17 projects**) [29], QuixBugs (40 programs, Python *and* Java) [30], plus C/C++ and language-specific sets. Defects4J (**835 bugs**; the system count is reported inconsistently — secondary citations say 17 systems, the project's own table names 11) [31] is Java-only and cannot host a Python experiment directly.

**Warning-level static-analysis benchmarks** (closest task unit to a rule violation): **CQPy** — 2,752 Python files, **5,389 CodeQL static-check violations** from 52 checks (used by CORE) [12]; the Sorald/SonarQube Java set (CodeCureAgent sampled **1,000 warnings over 106 projects, 291 rules**) [2].

**Architectural benchmarks — the near misses:**
- **SmellBench (arXiv 2605.07001):** 65 expert-validated hard-severity architectural smells in scikit-learn v1.7.2; smell re-detection + net-smell-delta oracle. Smell-centric, single repo, detector-defined (not declared) rules [3].
- **SmellBench (GitHub `critical88/SmellBench`) — a *different* work with the same name:** 147 injected instances → **294 evaluation cases**, 7 smell types × 21, 7 projects, 3 difficulties, 2 instruction types, ground-truth refactor diffs, `testsuites`, per-instance `commit_hash`. Do **not** cite the two interchangeably [4].
- **Design-constraint compliance** (arXiv 2604.05955): **495 issues, 1,787 validated constraints, 6 repos**, constraints mined from real PRs — but judged by an **LLM verifier**, not a deterministic analyzer. Finding: fewer than half of resolved issues are fully design-satisfying and functional correctness has "negligible statistical association" with design satisfaction [20].
- **Li et al.** (arXiv 2306.08616): controlled experiment where supplying *detected* violation symptoms raised developer detection from **25.9% → 64.7%** — the closest measured causal effect of supplying architectural-violation evidence, but the outcome is *human detection*, not agent repair [22].

**Plain answer: no benchmark exists for repairing author-declared architecture-rule violations with a deterministic analyzer oracle** (**searched negative**) [3, 4, 20]. The missing artefact is *"pinned Python repo commit + declarative architecture rule set + real or injected violation + analyzer-clean oracle + ground-truth compliant patch."*

**Analyzer-clean gates are cheap and available for Python** and all return machine-readable output/exit codes: `import-linter` (contracts incl. `forbidden`, `layers`, `independence`, `protected`, `acyclic_siblings`) [43], `pytest-archon` (rules as pytest tests, with toplevel/`TYPE_CHECKING`/transitive/direct import modes and custom predicates) [63], `ArchUnitPython` [64], `pytestarch` [65]; plus SARIF-producing `semgrep ci` (rule modes Monitor/Comment/**Block**, Block = exit code 1) [14] and the **CodeQL CLI** for diffing pre/post finding sets [62]. Note: **none of these ships an out-of-the-box "did the fix introduce a previously-unreported violation" diff** (**searched negative**) [43, 62, 63, 64, 65] — CodeCureAgent's line-mapping logic is the published example of building one [2].

### 3.5 RQ1 — ranked experiments

Ranked by (defensibility of the evidence base × contribution × cost).

**E1. Three-arm conditioning ablation with a content placebo — the highest-value experiment.**
Design: paired, same pinned commit SHAs and identical task set, four arms — (a) verdict only, (b) verdict + graph evidence path, (c) verdict + evidence path + governing ADR text, (d) verdict + evidence path + **length-matched irrelevant ADR text** (placebo). Oracle = **analyzer-clean re-run + no new violations + tests** (multi-oracle, following CodeCureAgent's gate).
Evidence base: DRCodePilot's `-DR` ablation shows the rationale section can dominate the **exact-match** metric (−81.65% / −94.44%), but on a benchmark conditioned on rationale-bearing issues, with **no test or analyzer oracle** and two Java projects — so transfer to a verified-correct, analyzer-clean objective is untested [8]; CodeCureAgent's approver ablation (0 → 123 false accepts) justifies the gate [2]; **we found no length-matched placebo arm among the ablation studies reviewed** (a systematic search of the conditional-prompting literature was not performed) [23, 24, 25], so a positive result would otherwise be attributable to token count rather than rationale content.
Metrics to report: analyzer-clean rate, plausible/correct split (CodeCureAgent's terminology) [2], **net new-violation delta** (SmellBench's framing, which is what caught the −109 regression) [3], and false-accept rate.
Cost: medium-high; requires building the architecture-rule task set (see E4).

**E2. Reproduce the "no-new-violations" gate's value inside an architecture-rule loop.**
Design: A/B the approval gate (gate vs no gate) on the same rule-violation tasks.
Evidence base: CodeCureAgent's four-way ablation is the strongest single quantitative result in this review (0 / 9 / 123 / 249 false accepts per 1,000) [2]. Reproducing the *shape* of that result on architecture rules would be a small, low-risk contribution.
Cost: low once E4's harness exists.

**E3. TP/FP classification before repair, measured on ADR-derived constraints.**
Design: two-stage agent (classify constraint violation as real/false-positive → repair only true positives), vs single-stage repair.
Evidence base: CodeCureAgent's classification stage (TP 97.4%, FP 81.0%) plus its stated bias toward "missed repairs rather than unwanted changes" [2]; SmellBench's **63.1% detector false-positive rate** [3]; the Tencent industrial study's 94–98% FP reduction with hybrid LLM+static analysis (DOI 10.1145/3786583.3786910) [11]. For ADR-derived constraints this is especially load-bearing, because 2602.07609 [21] found LLMs fail most on deployment/implicit ADRs — i.e. exactly the ones likely to be false positives.
Cost: low-medium.

**E4. Build the missing benchmark (this is infrastructure, but it is the bottleneck).**
Design: a *"Shepherd-bench"* of pinned Python repos + declarative rule sets (import-linter/`pytest-archon` syntax) + real ADR-derived violations and injected ones + ground-truth compliant patches + analyzer-clean oracle.
Evidence base: every benchmark-side requirement is already specified by an existing artefact — SmellBench-GitHub's per-instance schema (`smell_content`, `gt_content`, `testsuites`, `commit_hash`, `settings`) is directly reusable [4]; SmellBench-arXiv supplies the expert-FP-validation methodology [3]; 2604.05955 supplies the constraint-mining-from-PRs method [20]; CodeCureAgent supplies the gate [2].
Note: without E4, E1–E3 have no host. This should be sequenced first.
Cost: high.

**E5. Adopt the EMSE reporting discipline and the equivalence-testing null-result protocol.**
Design: report model version + system fingerprint + run date, full prompt/harness, session traces, an open-LLM baseline, human validation on a sample, `n` repeats; if a null is plausible, pre-declare equivalence bounds and include a manipulation probe.
Evidence base: the EMSE LLM-study guidelines (arXiv 2508.15503) prescribe exactly these, and warn that seeds do not guarantee reproducibility [23]; the two-agent context-file ablation (arXiv 2607.27250) is the worked example of a bounded null result ("bounded to ≤10–15pp via equivalence testing") plus a positive control [25]. The program-repair settings study (arXiv 2609.17993) supplies the confound taxonomy (task unit, fault-localisation assumptions, initial input, tool access, repair-time feedback, final validation, resource budget) [24].
Cost: near-zero; do this regardless.

**E6 (exploratory). Test whether the evidence path helps *localisation* even when the verdict alone suffices for repair.**
Design: measure agent time-to-locate / tool-call count / tokens with and without the graph path.
Evidence base: weak — this is genuinely unstudied (**searched negative**). InferFix's component ablation increments (bug-type annotation +2.7–5.6% relative; location markers up to +3.4%; extended context +7.2–7.8%) are the closest analogue and they measure *accuracy*, not cost [1].
Marked **unverified**: treat as an exploratory arm, not a confirmatory one.

---

## 4. RQ2 — Temporal and retroactive analysis

### 4.1 Mining architectural violations from version history

**Maffort, Valente, Terra, Bigonha, Anquetil, Hora — "Mining architectural violations from version history," *Empirical Software Engineering* 21(3):854–895 (online 2015; issue 2016), DOI 10.1007/s10664-014-9348-2.** Full text read at `rmod-files.lille.inria.fr/Team/Texts/Papers/Maff14a-ArchitecturalViolations-EMSE.pdf`.

Two corrections to the common summary: it is **not** a DCL paper (DCL appears only as related work / a future formalisation target), and its tool is **ArchLint**, with heuristics implemented as **SQL queries over a relational database of inter-class dependencies extracted with VerveineJ/Moose** [32].

Method: static + historical analysis; **one heuristic for absences** (dependencies that should exist but never appeared) and **three for divergences** (dependencies that should not exist but were inserted and later removed). Premise: violations are "rare events in the space-time domain." Thresholds (`DepScaRate`, `DepInsRate`, `DepDelRate`, `DepDirWeight`, `HeavyUser`) start rigid and are iteratively relaxed after architect review; a batch is emitted only at ≥10 new warnings (`MIN_RESULTS`); warnings are ranked (`ScoreAbsence`/`ScoreDiv1..3`) and evaluated with **nDCG** [32].

Reported precision is uneven and honestly so: divergence #1 and #3 reach **100%**; divergence #2 reaches only **34.2%** on SGA and **7.9%** on Lucene. **Recall is not measured at all** [32].

### 4.2 The strongest empirical argument that a rule's silence is ambiguous

This is the single most decision-relevant result for a persistent rule memory:

- In **SGA**, **53% of "Insert Missing Dependency" changes occurred in the first year**, and after discarding four years of revisions **no violations whatsoever were detected** [32].
- In **Lucene**, entrenched-but-unauthorised dependencies were **missed** because the rule had gone stale [32].
- Independently, OpenStack review data show erosion-symptom comments **declining** over 2014–2018 as the architecture stabilised (20,211 review comments; violation symptoms = 75, 15.9%; arXiv 2201.01184) [40].

**Single-study (strong).** *A rule reporting clean is ambiguous — it may mean compliance, or obsolescence.* Maffort's result shows that, in one subject system, most violations occurred before the conformance rules were written, so discarding early history eliminated detection entirely: evidence that silence **can** mean obsolescence, **not** that it usually does. Caveats from the same paper: precision is measured unevenly (divergence #2 at 34.2% on SGA and 7.9% on Lucene), **recall is not measured at all**, thresholds are relaxed iteratively after architect review, the study covers two systems, and its authors state the result is not generalisable [32]. The OpenStack finding [40] measures review-comment symptom *trends*, not rule silence — declining symptoms are equally consistent with genuine compliance. No reviewed source resolves the ambiguity automatically (**searched negative**) [32, 40]. **Inference (labelled as such):** a rule-age / last-matched metadata field is the minimum mechanism needed to tell the two apart.

### 4.3 Erosion and drift trajectories: measurable, and already per-instance

The smell-evolution literature has independently converged on per-instance temporal attributes that map almost exactly onto rule-validity modelling. Gnoyke et al. (JSS 2024, DOI 10.1016/j.jss.2024.112170) define **"age"** as versions since a smell's first predecessor appeared and **"remaining age"** as versions until removal of the last successor [35] — crediting Sas et al. (ICSME 2019) [34]. Corpora available as comparison points: **524 versions / 14 projects** [34]; **485 releases / 14 systems** [35]; **421 versions / 8 OSS systems** [37]; **378 versions / 8 projects** [38]; **368,847 commits / 2,571 releases / 16 Apache projects** [39]; and an industrial set of **9 C/C++ projects, >30 releases each, >20 MLOC** (with 273 Unstable-Dependency instances splitting 49/37/14% by size trajectory) [36].

### 4.4 Rule validity over time: freeze ≠ expiry, and `valid_from`/`valid_to` does not exist

| Mechanism | Tool | Semantics | Time dimension | Documented failure mode |
|---|---|---|---|---|
| **Freezing** | ArchUnit `FreezingArchRule` | Records all current violations in a `ViolationStore`; first run passes; only *new* violations fail; store auto-shrinks as violations are fixed | **None** — no expiry, owner or review date in the store format | >70 freeze files with empty/orphan entries and references to deleted tests; **open** issue, no validation support merged [41] |
| **Baseline / waiver** | SonarQube `Accepted` / `False positive` | Indefinite waiver of specific findings; **excluded from quality reports and ratings** | Only the **New Code Definition** (default: previous version; also N days / specific version / reference branch) — this bounds *what the gate inspects*, not what is waived | Docs name the anti-pattern: heavy FP/Won't-Fix volume "means that some coding rules are not appropriate for your context" [42] |
| **Waiver by pair** | import-linter `ignore_imports` | Explicit import-pair exceptions | **None** | Mitigated by `unmatched_ignore_imports_alerting` (surfaces ignore-entries matching nothing) [43] |
| **Graph-native rules** | jQAssistant | Cypher concepts (enrich) + constraints (violations) over Neo4j | **None documented** | None documented [44] |

**Searched negative (medium confidence)** — the search covered ArchUnit, SonarQube, import-linter, jQAssistant, DCL/DCLsuite and mainstream ADR templates: **no implementation of rule-level `valid_from`/`valid_to`** [41, 42, 43, 44, 33, 45]. Interval semantics appear only in temporal *graph databases* (`VAL_FROM`/`VAL_TO`/`TX_FROM`/`TX_TO` in the `TPGM+` bitemporal model, arXiv 2111.13499) [52] and in anchor-based temporal stores (AeonG, PVLDB 17(6):1515–1527, 2024) [53]. The one "valid time" hit in an architecture-tooling search was the W3C geospatial requirement — not software architecture (**searched negative**) [107].

**ADR side:** ADRs carry a supersession chain (Proposed/Accepted/Deprecated/Superseded/Rejected) and the guidance is explicit that accepted records should be **superseded rather than edited**, but the reviewed ADR templates and guidance (Microsoft Azure WAF, MADR, community templates, GOV.UK framework) define **no `valid_from`/`valid_to` fields** [45]. So the architecturally correct statement *"this rule held for releases 5–12 and was superseded in release 13"* is expressible in prose and **not machine-checkable in any reviewed conformance tool**. **Terminology note:** the topic line says Shepherd models "supersession tiers". No reviewed source uses a tier vocabulary — what exists is a linear supersession *status* chain (Proposed/Accepted/Deprecated/Superseded/Rejected). "Tiers" would be Shepherd's own extension, not an inherited standard, and should be defined explicitly if retained.

**Finding: freezing and expiry are different axes and no reviewed tool has both** [41, 42, 43, 44]. Freezing answers *"should this finding block CI?"*; expiry answers *"when must a human re-justify this decision?"* Shepherd's dismissal persistence is on the freezing axis only, unless it adds expiry.

### 4.5 Vacuous / dead conformance rules

**Searched negative:** no peer-reviewed study of vacuous/dead/rotted *conformance* rules was found under any of "vacuous conformance", "dead rule", "rule rot", "ruleset drift", "unused rule", "rule coverage" (**searched negative**) [46, 47, 48]. Recorded as an open research gap, not as proof of nonexistence.

**But the failure mode is documented as engine behaviour, which is stronger than folklore:**

- **`grimp`** (the import-graph engine behind import-linter), primary doc, on `find_illegal_dependencies_for_layers`: *"Any modules specified that don't exist in the graph will be silently ignored."* Rename or delete a layer's package and **the rule passes forever**. Even within the same product family the mitigation is inconsistent: import-linter's `independence` contract validates module existence and raises, while the `layers` contract's `exhaustive` option catches *undeclared new* modules rather than *missing declared* ones [67, 43].
- **`grimp`, same doc, a second problem:** violation evidence paths are **not deterministic** — *"If there are multiple illegal Routes of the same length, it is not predictable which one will be found first… the PackageDependencies returned can vary for the same graph."* This directly undermines any design that **persists an evidence path** and reasons over it across commits (which is Shepherd's design); paths must be canonicalised or stored as a full route set [67].
- **Structure101:** *"only violations between visible cells are enforced … if you collapse a cell, any rules implied by its contained cells are not checked."* Collapsing the model silently disables rules [71].
- **ArchUnit:** verdicts depend on graph completeness, not only rule text — if `Throwable`'s subclasses are not imported, a call of `RuntimeException` is not considered a violation [60].

**Adjacent-domain analogues that do measure it** (practitioner evidence, not academic, and re-fetched first-hand during citation verification): `promtool test rules --coverage` reports which alerting/recording rules are exercised by unit-test assertions, with `--coverage-threshold` to fail CI on an untested rule; a removal-based tool measures which agent-instruction rules "actually do nothing" by deleting one rule at a time in isolated worktrees. Prometheus's PR note is precise about the limit: *"Coverage here is assertion presence, not expression branch coverage."* [46]

**Three mechanisms across two tools ship an explicit empty/stale-selector guard, plus two adjacent drift-reconciliation mechanisms** (all doc-cited). *Explicit guards:* import-linter `exhaustive` [43]; import-linter `unmatched_ignore_imports_alerting` (default `error`) [43]; ArchUnitPython's fail-on-empty-check ("helps catch typos in file and folder patterns before they silently make your architecture tests meaningless") [64]. *Adjacent drift reconciliation (not anti-vacuity features as such):* tach `sync` ("Sync constraints with the actual dependencies in your project") [66]; ArchUnit's violation for classes matching no declared package identifier, which is a side effect of its modularisation rule rather than a vacuity check [60].

**Theoretical framing worth borrowing:** Okun's **"consistent mutants"** — specification mutants that are "true over all possible traces" and therefore useless for mutation analysis — is precisely a rule whose predicate every input satisfies: vacuous by construction [48]. And Wang et al. (ICPC 2022) found **46 bugs in static-analysis rule implementations/designs, 30 fixed or confirmed, across 2,728 projects** in SonarQube/PMD/SpotBugs/ErrorProne — the *rules were wrong, not the code* [47]. (Note: the DOI printed in the source is inconsistent with the ICPC 2022 proceedings prefix; cite the computer.org URL, not the DOI.)

**Also relevant to false-confidence:** Ruff's `RUF100` (`unused-noqa`) detects a **stale suppression** — "a noqa directive that no longer matches any diagnostic violations is likely included by mistake, and should be removed" — which is the *opposite* direction from what a conformance tool needs (a stale rule), and it is autofixable [46]. And for calibration on how loose "clean" is: an ISSTA 2024 study found **≥76% of warnings in vulnerable functions were irrelevant** to the vulnerability-contributing commits, and **22% of VCCs went undetected due to SAST rule limitations** [49].

### 4.6 Temporal code knowledge graphs: three designs with stated costs

| Design | Real implementation | Documented tradeoff / numbers |
|---|---|---|
| **Snapshot-per-commit** | **Compass history** — "complete, immutable graph realizations for exact Git commits in a SQLite-backed Prolly store outside normal Git history", keyed by commit SHA + extraction fingerprint; deltas are **computed views** | GC defaults **1 GiB / 30 days**; quality bar that topology-only diff be **≥2× faster** than full diff; no absolute total-history size or latency published [50]. **Software Heritage** is the same idea at scale: content-addressed Merkle DAG, ~**5 TB** fast storage for the graph DB, ~**200 TB** including file contents, ~**1 TB** per bulk download format; 5 B files, 1 B commits, 80 M projects [55] |
| **Delta / change-based** | **TGI** (EDBT 2016) — Eventlist Partitions / Derived Snapshot Partitions / Version Chain over DeltaGraph + Cassandra | The cleanest statement of the core tradeoff: *"Log requires minimal information to encode the graph's history, but incurs large reconstruction costs. Copy, on the other hand, provides direct access, but at the cost of excessive storage."* Scale: 266.7 M events (Wikipedia), up to ~1 B synthetic; snapshot retrieval up to ~**300 s** on EC2 4 cores/15 GB [51]. Analysis-side analogues: incremental call-graph reanalysis; incremental algebraic program analysis warns that "existing APA algorithms **do not guarantee that small code changes lead to small incremental updates**" [56] |
| **Temporal / interval edges (bitemporal)** | **`TPGM+`** — valid-time *and* transaction-time on vertices, edges and properties via `VAL_FROM`/`VAL_TO`/`TX_FROM`/`TX_TO`; prototype `BiTeGra` on an RDBMS with `T-PGQL` on PGQL 1.3 [52]. **AeonG** — hybrid current+historical storage with **adaptive anchoring** interval `u` | AeonG: **up to 5.73× lower storage**, **up to 2.57× lower temporal query latency**, only **9.74%** overhead vs non-temporal, **up to 2.82×/10.11×** better graph-op latency than Clock-G/T-GQL [53]. Dissent: **PETGraphDB** argues naive temporal-on-graph-DB "introduce[s] extra vertices and edges, which not only increase storage consumption but also hinder the performance of time-related operations", measuring **~19.6×** cost for analytical temporal queries touching all entities [54] |

**Which tools are actually closest to a versioned code graph:** Compass history is the only reviewed system that materialises a code knowledge graph per commit with explicit history commands and GC semantics [50]. jQAssistant is the only mainstream conformance tool whose store is already a graph DB with a general query language — the natural host for interval edges, but **no rule-level valid-time is documented** [44]. **CodeCompass** documents incremental re-parse of the *current workspace only* (experimental; threshold default 10% of changed files) — it should **not** be described as a versioned graph store [57]. **Sourcetrail** is discontinued (repo archived Dec 2021) and no commit-history/timeline feature is documented — the brief's "Sourcetrail (timeline)" framing is **not substantiated** [58]. **Gevol** is the historical precedent for time-sliced code graphs (inheritance/call/CFG graphs from CVS, default **1-day slices**, coloured by staleness) [59].

**Unresolved:** no published absolute storage/latency figure exists for a per-commit *code* knowledge graph (as opposed to generic temporal graphs) (**searched negative**) [50, 51, 53]. Generic temporal-graph numbers are not measured on code graphs.

### 4.7 RQ2 — ranked experiments

**E7. Rule-vitality tracking: last-matched, match-count, and a vacuity alarm — the highest-value RQ2 experiment.**
Design: store per-rule `last_matched_commit`, `match_count`, and the selector's resolved node set; alarm when (i) a rule's selector resolves to an empty/near-empty set, or (ii) a rule has not matched for N commits while its subject package has changed.
Evidence base: Maffort's SGA result (**53% of violations in year 1; zero after 4 years discarded**) and the Lucene stale-rule miss are the direct empirical justification [32]; `grimp`'s documented silent-ignore is the engine-level mechanism [67]; the fixture-based countermeasures (ESLint `RuleTester`, Semgrep `--test` with `ruleid:`/`ok:`/`todoruleid:`/`todook:`, CodeQL `test run` with `.expected`/`.actual` + `--learn`) each prove a rule fires **once, on author-written fixtures** [46] — none detects "matched nothing in 20 releases."
Cost: low; it is a schema addition (3 fields) plus a query.

**E8. Measure the vacuity rate on a real ADR-derived constraint set.**
Design: instrument the ADG to record, per rule per commit, whether the constraint's selector set is non-empty and whether it *could* fire; report the fraction of rules that become vacuous after a rename/reorg, and the distribution of time-to-vacuity.
Evidence base: this is a **measured gap** — no academic study exists (**searched negative**) [46, 47]; the mechanism is doc-confirmed (`grimp`, Structure101) [67, 71]; a corpus of 980 ADRs/109 repos exists to build on (arXiv 2602.07609) [21]; ArchUnit's open staleness issue (>70 freeze files) shows even a mature tool has no answer [41].
Contribution: this would be the first empirical measurement of conformance-rule vacuity that this review could locate (**searched negative**).
Cost: medium.

**E9. Freeze vs expiry: add and evaluate an expiry/justification mechanism.**
Design: extend dismissal persistence with an owner + review-by date + justification, and A/B against pure freezing on (i) rule-set survival, (ii) re-justification rate, (iii) regressions escaping the freeze.
Evidence base: ArchUnit's freeze semantics are documented as *can only shrink* — the maintainer's own words: "There is no support to allow new violations to occur… the whole premise… is 'okay, we have a bad state right now, but from now on we only want to get better'" — and its staleness failure mode is an open issue with no validation support [41]. SonarQube's `Accepted` issues are excluded from ratings, which is a documented blind spot [42]. **No tool has both axes** [41, 42, 43].
Cost: medium; the evaluation design is the hard part (there is no existing benchmark).

**E10. Cost-profile a temporal ADG design on a real Python repo.**
Design: implement snapshot-per-commit, delta, and interval-edge variants over the same history and measure build time, storage, and query latency for (a) "as-of commit X" constraint evaluation and (b) "violations introduced/removed between X and Y".
Evidence base: Compass history gives the snapshot design and its GC/diff bars [50]; TGI gives the log-vs-copy framing and 266.7 M–1 B event scale [51]; AeonG gives 5.73×/2.57×/9.74% as the anchor to beat [53]; PETGraphDB gives the ~19.6× counter-warning [54]; incremental-APA's "small changes → small updates" non-guarantee is the delta design's key risk [56]. **No such measurement exists for a code graph** (**searched negative**) [50] — this is a genuine, bounded, publishable systems result.
Cost: high.

**E11. As-of / retroactive evaluation of dismissed violations.**
Design: for each persisted dismissal, re-evaluate the constraint at each subsequent commit and report the "dismissal debt" trajectory (was the dismissal still justified? did the dismissed pattern spread?).
Evidence base: Maffort's premise that violations are transient in time [32]; Gnoyke's "age"/"remaining age" per-instance attributes are the direct methodological template [35]; OpenStack's declining-symptom trend gives an expected shape [40].
Cost: low-medium.

---

## 5. RQ3 — Generalising the graph into a query surface

### 5.1 The tool landscape and its rule vocabularies

| Tool | Expression mechanism | Vocabulary beyond pairwise prohibition |
|---|---|---|
| **jQAssistant** | **Cypher** in XML/AsciiDoc over **Neo4j**; *concepts* (enrich) vs *constraints* (violations) | Whole graph schema is the predicate surface; jMolecules plugin ships named styles (`jmolecules-layered`, `-hexagonal`, `-onion-classical`, `-onion-simplified`, `-cqrs`, `-ddd`, each `:Default`/`:Strict`) that aggregate type-level deps to layer-level `:DEPENDS_ON`; metrics plugin writes `ca`/`ce`/`instability`/`abstractness`/`distance`/`normalizeDistance` onto `:Java:Package` [44, 61, 72, 109] |
| **ArchUnit** (Java) | fluent Java API; Core/Lang/Library layering | **The richest documented architecture vocabulary**: `beFreeOfCycles()`, `notDependOnEachOther()`, layered architecture, `GeneralCodingRules` (no field injection, no `java.util.logging`, no JodaTime), plus a metrics API documenting **Ca, Ce, I = Ce/(Ca+Ce), A, D**, Dowalil visibility metrics (RV/ARV/GRV), and Lakos cumulative dependency (CCD/ACD/RACD/NCCD) [60] |
| **CodeQL** | **QL** (Datalog dialect) over a relational code database | Expressible by recursion + aggregates; no architecture-specific vocabulary shipped — the user writes it [108, 62] |
| **import-linter** (Python) | INI contract DSL + CLI; engine `grimp` | `forbidden`, `protected`, `layers` (with `exhaustive`), `independence`, `acyclic_siblings`, custom types; `as_packages`, `allow_indirect_imports`, `ignore_imports` semantics [43, 67] |
| **pytest-archon** (Python) | rules as pytest tests | `should_not_import`, `should_import`, `may_import`, custom predicates; four-way options matrix (toplevel / `TYPE_CHECKING` / in-function / transitive) [63] |
| **ArchUnitPython** (Python) | fluent ArchUnit-style API | cycles, layers (`project_layers`), naming (`have_name`), metric thresholds (`should_be_below`), zone-of-pain, external-library bans, `adhere_to` for custom checks, PlantUML-derived rules [64] — metric claims are the tool author's own README (self-reported) |
| **pytestarch** (Python) | pytest rules + PlantUML | layer rules, PlantUML diagram-derived rules [65] |
| **tach** (Python) | TOML config + CLI | declared dependency allowlist (`depends_on`), public interfaces, `tach sync`, `# tach-ignore`, and **deprecated-dependency state** (surfaces usage without erroring — a staged-removal state) [66] |
| **Sonargraph** | purpose-built architecture DSL + Groovy | "hundreds of metrics", per-language metric chapters (language-independent, Java, C#, C/C++, **Python**), cycle-group metrics incl. relative cyclicity, **quality gates + baselines** [68] — vendor-documented and self-reported except where a metric formula is published |
| **DV8** | CLI + DSM analysis | fixed catalogue of named anti-patterns with thresholds: Package Cycle, Clique, Crossing, Unstable Interface, Modularity Violation, Improper Inheritance; **Decoupling Level** and **Propagation Cost**; **3 structural + 3 history-dependent** [69] |
| **Lattix** | tabular Design Rules on DSM cells | ordered, typed, hierarchical rules with layering, independent-component rules, external-dependency rules [70] |
| **Structure101** | visual Structure Spec / diagram | layering, strict layering, tangle groups, containment, private cells — with the documented trap that collapsing a cell disables its implied rules [71] |
| **Sourcetrail** | none (exploration UI) | **no conformance rule vocabulary**; archived/discontinued 2021 [58] |
| **Joern / CPG** | Scala DSL over a custom graph DB | "code as data" lineage; foundational paper is **Yamaguchi, Golde, Arp, Rieck, IEEE S&P 2014, DOI 10.1109/SP.2014.44** (not arXiv 1604.05976 — see §6) [74, 73] |
| **grimp** | Python library API | graph primitives + layers + **cycle-breaking nomination** (feedback arc set), evidence routes, shortest chains [67] |
| **PyCG** | Python call-graph construction (**arXiv 2103.00587**, ICSE 2021, DOI 10.1109/ICSE43902.2021.00146) | the `CALLS`-edge enabler, and its accuracy is the accuracy ceiling for `CALLS`-based rules [75] |

**Two structural observations.** First, the field splits into three camps with a real trade-off: general query languages (Cypher, QL) maximise expressiveness at the cost of schema knowledge; purpose-built DSLs (Sonargraph, import-linter, Lattix, Structure101) minimise authoring cost but pin the user to a closed predicate set; host-language APIs (ArchUnit family) sit between. **The Joern team documents migrating *away from* Gremlin + a general-purpose graph DB to their own DSL and OverflowDB because "the limitations of this approach became more apparent over the years"** [73] (the CodeQL QL reference [108] supports only the adjacent "QL is expressible by recursion + aggregates" claim, not Joern's engineering history). This is **one documented instance, not a ranked result**: the docs do not state *which* limitation drove it (storage, performance and plumbing are equally consistent with the sentence), and the replacement is itself a DSL over a custom store. Treat it as an existence proof that "just use Cypher/QL" is not cost-free.

Second, **all four ADG predicates sit at the narrow end of this space.** Positive *obligation* predicates exist but are rare and are documented concretely only in pytest-archon (`should_import`) [63], import-linter's `layers` (ordering implies obligation) [43] and tach's `depends_on` allowlist [66]. `requires_implementation`/`prohibits_implementation` are closest to ArchUnit's `implement`-oriented conditions [60], tach's public-interface rule [66], and DV8's Improper Inheritance [69] — **none of the reviewed tools documents a first-class "must implement interface X" predicate as a named rule type** (**searched negative**).

### 5.2 What is computable from a *pure* dependency graph

This tiering matters more than the smell names, because it determines what an ADG can express without adding schema.

**Tier A — pure dependency/type-hierarchy graph (no source text, no history):**
Cycles / strongly-connected components and therefore Package Cycle and Clique [69]; **hub-like dependency** (fan-in/fan-out — DV8's *Crossing* uses fan-in ≥4 **and** fan-out ≥4, so the structural half is pure-graph) [69]; **unstable dependency** (Martin's instability inequality) [76, 77]; **Ce / Ca** [60, 76]; **instability `I = Ce/(Ca+Ce)`** [60, 76]; Propagation Cost (reachability/density) [69]; cyclic/deep/wide inheritance hierarchies [77].

**Tier B — graph + token/size/cohesion/type attributes:**
**Abstractness `A = num(abstract)/num(all)`** (needs a node property; ArchUnit further restricts to *public* classes, so visibility is also needed) [60, 76]; **Distance `D = |A + I − 1|`** and zone-of-pain / zone-of-uselessness [60, 64]. **Note the formula convention:** sources disagree on whether Martin (1994) divides by 2 — the research note records `D = |(A+I−1) ÷ 2|` from its read of the paper (rq3b note §1.2), while the widely implemented form omits the ÷2 and ArchUnit's javadoc does not state a divisor. This review does **not** resolve which is canonical. The actionable point stands regardless: the ADG must pin one convention and store it as rule metadata (cf. E15), or thresholds become non-comparable across tools [76, 60]; God Component (Arcan uses LOC only, with a data-driven threshold from 100+ Qualitas Corpus systems; Designite uses LOC or class count) [77, 78]; feature concentration (Designite's Lack of Component Cohesion, computed from method-level access patterns) [78]; Improper Inheritance (needs edge *types* to separate inheritance from other dependencies) [69]; containment/packaging rules (need containment as a *separate* relation from dependency edges) [71].

**Tier C — graph + revision history (co-change) — NOT computable from a pure dependency graph:**
**Modularity Violation**, the **full** definition of **Crossing**, and **Unstable Interface** — DV8 states these "can only be detected using both structural relation and co-change information" [69]. Also any drift/erosion metric across releases [68].

**Independent confirmation that Tier A+B is implementable as graph post-processing:** both ArchUnit and the **archived** jQAssistant Java metrics plugin (contrib 1.8.0, pinned to jQAssistant 1.8.0 — historical capability, possibly stale against the 2.x line) derive a component-level dependency relation from element-level dependencies and write results back as node properties [60, 72]. ArchUnit states the derivation explicitly; jQAssistant writes `ca`/`ce`/`instability`/`abstractness`/`distance`/`normalizeDistance` [72]. ArchUnit's `MetricsComponent` can also be built package-agnostically (`MetricsComponents.from(..)`), so componentisation need not follow package structure [60].

**Consequence for the ADG (inference, labelled):** a pure `IMPORTS`/`CALLS`/`INHERITS` graph over FQNs is **sufficient** for coupling, cycle, layer and independence predicates; **insufficient** for abstractness/distance-from-main-sequence unless the graph models abstract/concrete and visibility; and **insufficient for the entire co-change anti-pattern family** unless history edges are added. Note also that `CALLS`-edge accuracy is bounded by the Python call-graph extractor (PyCG-class) [75], and both `grimp`'s own documentation [67] and ArchUnit's documented False-negative mode [60] show that **verdicts depend on graph completeness, not only rule text**.

### 5.3 Is there evidence that a richer rule vocabulary improves outcomes?

**No study was found that tests the causal claim "a larger/richer rule vocabulary reduces defects."** (**searched negative**) What exists:

- **Correlational, same-group corroboration (Reported; *not* independent replication).** Mo et al., IEEE TSE 47(5), 2021 (19 projects): files in architecture anti-patterns are more bug- and change-prone and severity scales with the **count** of distinct anti-patterns — Avro bug-file rate **0.3 (0 patterns) → 12.0 (6 patterns)**; Pearson `r` 0.61–0.98, per-project p-values 2E-4–0.05; project-level bug-rate increases **117%–11,968%**; **Unstable Interface and Crossing most impactful, Package Cycle least** [80]. The 2021 paper's *detector* requires **structural + revision history**, but two of its six anti-patterns (**Clique**, **Package Cycle**) are structural-only [80, 69].
- **Correlational, earlier/smaller (Reported).** Mo et al., WICSA 2015 (9 OSS + 1 commercial): bug/change rates rise monotonically over 0→4 file-level patterns; Unstable Interface most significant [79].
- **Graph-only defect prediction (Reported).** Wong et al. (Clio, ICSE 2011) on 15 releases of Hadoop Common; the abstract states "a strong correlation between software defects and eroding design structure" [81]. Zimmermann & Nagappan (ICSE 2008) report graph-derived network metrics improving recall by ~10 pp over complexity-metric models on Windows Server 2003 — **but this is a second-hand figure; the primary PDF was not obtained** [82].
- **Single small study (do not generalise).** Kouroshfar (ICSE 2013) — a **2-page ACM SRC paper**, four Apache projects (Camel, OpenJPA, Hive, HBase), 3-month co-change vs next-3-month bug-fix window [83].
- **Architectural smells are not reducible to code smells (Reported; abstract + preprint excerpts).** Arcelli Fontana et al., JSS 2019: "Architectural smells are not correlated with code smells… cannot be derived from code smells" — i.e. graph-level rules capture something code smells do not. Also documents that Marinescu's inFusion tool is "no longer available." [84]
- **On explicit "conformance checking reduces defects": the closest longitudinal field evaluation reports a *failure* mode, not a defect reduction.** Caracciolo et al., IWESEP 2016: *"attempts at automating architectural conformance checking often ended with failure, given that the resources invested in the task often exceeded the allocated budget. Practitioners are open to adopt quality assessment tools, but are not willing to pay the cost of deployment and maintenance activities."* [87]
- **The nearest proactive result is predictive, not rule-based:** ArchGuard (ICSA 2026) predicts smell-inducing issues from issue text with SVM + embeddings: F1 ≤ 0.506, recall ≈ 0.74 — on **three** GitLab projects [96].
- **Unverified pointer, flagged for follow-up:** *"Constructive architecture compliance checking — an experiment on support by live feedback"* (ICSM 2008) is the only located **controlled experiment** on compliance feedback. Authors and results were **not retrievable**. Do not treat as evidence [105].

**Also mixed/negative on the smell↔effort link:** Sas et al. (JSM 2022) state in their own abstract that architectural smells' "impact on maintenance effort has not been thoroughly investigated" [85] — the field flags the gap itself. The field is, however, moving from boolean detection toward **graded severity** (Pigazzini et al., MSR4SA 2021: PageRank + severity derived from how far metric thresholds are exceeded) [86], and the EMSE 2022 industrial case study records Arcan precision of 70–100% (a separate secondary source quotes 100% precision / 63% recall from Arcan validation on ten OSS + two industrial projects) — treat these as reported figures of **mixed provenance** (one peer-reviewed case study, one secondary abstract), not as measured here [36].

### 5.4 Documented failure modes of hand-written rule DSLs

**The strongest evidence is a three-case industrial evaluation, and the headline is attrition, not defect reduction: one of three cases ended after a month, the second left 85 of 270 violations unfixed, and the third moved 606 → 600.**

**Caracciolo, Lungu, Truffer, Levitin, Nierstrasz — *Evaluating an Architecture Conformance Monitoring Solution*, IWESEP 2016** (full PDF read):

| Case | Rules | Violations | Outcome | Duration |
|---|---|---|---|---|
| **C1** | 3 rules (46 Maven modules) | Only **3 of 18** package cycles were reported by the incumbent tool (SonarQube); **15** ignored cycles manually validated as real | **"C1 ended prematurely after 1 month"**; team "failed to convince them of the full utility"; "preferred not to invest any additional resources" | 1 month |
| **C2** | 17 rules | **270** violations: 27 critical/fixed immediately, 158 tracked, **85 unfixed** | "Not addressed violations were mainly ignored because of the high complexity involved in the refactoring task"; 5 false negatives found by cross-tool comparison | ~1 year |
| **C3** | 16 rules (1M LOC, 18 years) | **606 → 600** (10 introduced, 16 removed) | net improvement of 10; slow churn | ~1 year monitoring |

(all three rows: [87]; C1's rule count and the 46-module Maven scope are from the paper's example listing)

Also from that paper: *"Architectural rules are often defined but rarely tested"*; tool-integration effort is *"often considerable"*; and its expressiveness finding — DSM/Lattix-class tools: *"Basically only dependency rules can be explicitly formulated. Hence, more complex architectural rules — for example, for different patterns — cannot be captured. Moreover, the dependency rules inside the LDM tool have to be kept manually consistent with an existing architectural model, causing additional maintenance efforts."* Prior work it cites identifies "a set of conformance rules that are not supported by any of the analyzed tools (e.g., naming conventions, subclass inheritance)." [87]

**Quantified false-positive / warning-treatment evidence:**

| Finding | Numbers | Source |
|---|---|---|
| Coverage-vs-effort perception | 55% of developers do **no** pattern filtering; 25% filter "Not A Bug", 17% use `@SuppressWarnings`, 5% use a tracker; **81%** have no policy on how soon an issue must be human-reviewed; 60% run the tool only occasionally by hand (n=252) | Ayewah et al., IEEE Software 25(5), 2008 [89] |
| Warnings are not simply FP/TP | Google FindBugs: 1,127 medium/high correctness warnings; **193 (~17%) "impossible"**, 127 trivial, 289 open, **518 (~46%) fixed**; the authors argue the FP/TP dichotomy "oversimplifies the issue" | Ayewah et al., 2007 [89] |
| Recall, not just precision, is the problem | 594 real-world bugs / 15 projects / 3 detectors: "current bug detectors miss the large majority of the studied bugs"; detectors are "mostly complementary" | Habib & Pradel, ASE 2018 [90] |
| Alert actionability and latency **(abstract-level)** | **27.4–49.5% (median 36.7%)** of alerts actionable across 5 projects; fixes are small (**2–7 LOC, median 4**) but take **36–245 days (median 96)** to land | Imtiaz et al., ISSRE 2019 [91] |
| Suppression is the dominant escape valve, and much of it is noise **(abstract-level)** | **7,357 suppressions in 46 Python projects**; **50.8%** affect no warning and are "practically useless"; **26.8%** are understood-and-accepted-but-unfixed | Hu et al., PACMSE 2025 [92] |
| Barriers are perceived value + presentation | 20 developer interviews: all found tools beneficial, yet "false positives and the way in which the warnings are presented… are barriers to use" | Johnson et al., ICSE 2013 [93] |
| Configuration is a one-off, not a practice **(search-surfaced full text)** | **56%** configure static-analysis tools only at project start; **16% never** configure them | ESEM 2024 survey [94] |
| Rules/documentation are abandoned in practice **(page-text level)** | 65% use *informal reviews* for compliance; a participant prefers live tooling over "a page somewhere that may not have been updated in six months" | Ali et al., EMSE 2017 [88] |
| "Rule rot" itself | **no dedicated empirical study found** | searched negative |

**Two more failure surfaces worth naming:** metric-definition churn (Sonargraph changed "Entangled code (%)" and "Relative Entanglement (%)" definitions in 15.2.0, with one project moving from ~79% to ~16% entangled and relative entanglement from ~33% to <15% **purely from the definition change**) [68] — meaning **storing a metric threshold without storing the tool/metric-definition version is unsafe**; and import-semantics divergence across tools (pytest-archon documents four different notions of "importing" [63]; import-linter documents `as_packages`/`allow_indirect_imports`/wildcards [43]; ArchUnitPython claims `TYPE_CHECKING`- and dynamic-import-awareness [64]), so the *same written rule text* means materially different things in different tools — a portability hazard for any rule store.

**Conceptual vocabulary the field uses for these:** Ford/Parsons/Kua's **"architectural fitness function"** — "any mechanism that provides an objective integrity assessment of some architectural characteristic(s)" — with named instantiations (Cyclic Dependency Function, Coupling Fitness Function) and a classification (atomic/holistic, batch/continuous) [106]. **Practitioner literature; no effect size available.**

### 5.5 Deriving rules from prose: the weakest-covered area

This is reported as a **gap**, not padded with adjacent work.

**Precedents that derive rules from a *model* rather than prose** (all doc-cited): ArchUnit derives rules from **PlantUML** component diagrams ("ArchUnit can derive rules straight from PlantUML diagrams and check to make sure that all imported `JavaClasses` abide by the dependencies of the diagram") [60]; ArchUnitPython (`adhere_to_diagram`) [64], pytestarch [65] and jQAssistant (archived plugin, "the elements of such diagrams are interpreted as graph patterns and translated into Cypher queries") [72] do the same. Lattix [70] and Structure101 [71] *levelize* the spec from actual dependencies (bootstrapping from code, not prose).

**The closest documented instance of documentation → machine-checkable constraint** is a jQAssistant pattern (Kontext E AsciiDoc plugin) that converts a documented "Unwanted Module Dependencies" **table** into a `:TECHNICAL_DEBT` relation which a Cypher constraint then excludes [72]. Note the direction: documented debt becomes an **allowed exception** (a suppression mechanism), **not** a prohibition generator.

**Prose→decision extraction (real, but extraction ≠ checkable rules):** UnArch (arXiv 1704.04798) recovers architectural design decisions from code + commits + issues, applied to >100 versions of two systems [98]; Bhat et al. (ECSA 2017) detect design decisions in issue trackers with a two-phase supervised ML pipeline [97]; **DRMiner** (arXiv 2405.19623) mines design rationales with **F1 65%** (+7% over GPT-4.0) and reports that rationales "are often obsolete or even missing" — the **prose-rot analogue of rule rot** [99]; Dhar et al. (ICSA 2024, arXiv 2403.01709) find GPT-4 0-shot generates "relevant and accurate" ADR Decisions but below human level [100]. **Su et al. (arXiv 2602.07609)** is the single closest published work to "ADR prose → architectural conformance" — 980 ADRs / 109 repos, multi-LLM screen+validate — and it *detects* violations rather than generating checkable rules, with accuracy strong for "explicit, code-inferable decisions" and weak for "implicit or deployment-oriented decisions." [21]

**Formalising architectural rules as ontologies** — Schröder & Riebisch (DOI 10.1145/3241403.3241457), Schröder & Buchgeher (APSEC 2019, DOI 10.1109/apsec48747.2019.00017), Schröder & Buchgeher (DOI 10.1145/3344948.3344956) — are the most on-target hits, but **only metadata was obtained**; no claims are made here about their methods or results [104]. A follow-up should read them.

**The older formal cousin is specification mining:** Ammons, Bodík & Larus (POPL 2002, DOI 10.1145/503272.503275) infer protocol state machines with temporal **and data** dependencies from execution traces and "discovered serious bugs" [101]; CSight (ICSE 2014) mines LTL invariants from logs and infers a CFSM guaranteed to satisfy them [102]; ARSENAL (arXiv 1403.3142) transforms NL requirements into analyzable formal models checked for consistency and implementability [103]. The pipeline shape of ARSENAL is the template; the *architectural-decision* instance of it does not appear to exist (**searched negative**).

### 5.6 RQ3 — ranked experiments

**E12. Widen the predicate vocabulary along the Tier-A axis first, and measure whether it changes anything.**
Design: add cycle, layer-conformance, slice-independence, Ce/Ca and instability predicates to the ADG (all pure-graph, all Tier A), then A/B whether added predicate families surface violations that pairwise prohibition misses on the same commit set.
Evidence base: all four families are shipped and documented by ArchUnit [60], import-linter [43] and DV8 [69]; **no study tests whether adding them improves outcomes** (**searched negative**) — so the contribution is the *measurement*, and the honest expectation is a null or modest result (Mo et al.'s Package Cycle was the *least* impactful anti-pattern) [80]. Tier A is also the cheapest to implement because it needs no new node attributes.
Cost: low-medium.

**E13. Add history edges and measure the co-change predicate family.**
Design: add co-change edges to the ADG and evaluate the Tier-C predicates (Modularity Violation, Crossing, Unstable Interface) that DV8 states are impossible without them [69].
Evidence base: DV8's explicit statement that these "can only be detected using both structural relation and co-change information" [69]; Mo et al.'s TSE 2021 finding that UIF and Crossing were the **most impactful** of six anti-patterns (with Package Cycle least) [80] — i.e. if any added predicate family is worth the schema cost, it is this one, and the evidence for it is the strongest observational evidence in this review.
Cost: medium-high (history ingestion + co-change computation).

**E14. Instrument rule-vocabulary *usage*, not rule-vocabulary *size*.**
Design: log which predicates actually fire per commit, per rule; treat "rules that never fire" as the dependent variable (link to E7/E8).
Evidence base: Ayewah et al.'s 2008 survey (55% do no filtering; 60% run only occasionally) [89] and Hu et al.'s 2025 suppression study (**50.8% of 7,357 suppressions affect no warning**) [92] establish that dead configuration is the norm, not the exception, in adjacent tooling; Caracciolo et al.'s C2 (85 of 270 violations never fixed) and C3 (606→600 net 10) [87] show the same for conformance.
Cost: low.

**E15. Treat metric-definition version as part of a stored rule.**
Design: every metric-threshold constraint in the ADG stores tool + metric-definition version + the resolved value; flag re-evaluation when the definition version changes.
Evidence base: Sonargraph's documented 15.2.0 definition change moved one project from ~79% to ~16% entangled with no code change [68] — a stored threshold silently becomes a different rule. This is a small engineering change with a documented failure mode behind it.
Cost: near-zero.

**E16. Measure whether ADR text predicts which constraints are worth creating (feeds E4).**
Design: for a corpus of real ADRs, compare (i) LLM extraction of candidate `(subject, predicate, object)` constraints against (ii) which constraints actually fire on subsequent commits, stratified by ADR textual features (explicitness, presence of a named technology/module, deployment-or-configuration content).
Evidence base: 2602.07609's error taxonomy gives the predicted strata — infrastructure/deployment-specific ADRs = **42.39%** of errors, principle/intent-oriented **26.09%**, system/module interaction **17.4%**, logic/condition-intensive **9.78%**, context-dependent **4.35%** (**auto-report-mediated / UNVERIFIED** — these five percentages come from an LLM-generated summary of [21], not a line-by-line read of the paper's tables; re-check before relying on them, cf. §7) [21]; and the 980-ADR/109-repo corpus plus Buchgeher et al.'s MSR study (ADR adoption "still low"; ~50% of repos with ADRs have only **1–5**) [95, 21] bound the population. This is the experiment that would *test* Shepherd's ~25% convertibility premise instead of asserting it.
Cost: medium.

---

## 6. Corrections to the premise (must not be inherited)

| Brief statement | Verified reality | Evidence |
|---|---|---|
| "InferFix … arXiv 2305.12050?" | 2305.12050 is CodeCompose (Meta), unrelated. InferFix is **arXiv 2303.07263**, DOI 10.1145/3611643.3613892 | rq1a note §0; [1, 16] |
| "RepairAgent … arXiv 2403.03954?" | 2403.03954 is "3D Diffusion Policy" (robot learning). RepairAgent is **arXiv 2403.17134**, ICSE 2025, DOI 10.1109/ICSE55347.2025.00157 | rq1a note §0; [5, 17] |
| "InferFix" attribution | Fine — but the arXiv ID in the brief was wrong (above) | rq1a note §0; [1] |
| "Repilot (IDE-integrated / analyzer-assisted repair)" | **Mischaracterised.** Repilot fuses an LLM with an **Eclipse JDT completion engine** for type-aware token pruning; there is no analyzer *finding* in the loop. Repo: `github.com/ise-uiuc/Repilot` | rq1a note §0; [7] |
| "SAND" as an LLM repair system | **No such system.** The identifier resolves to a fuzzing framework (arXiv 2402.16497, ICSE 2025) and a Sandia report number | rq1a note §0; [15] |
| "jQAssistant … arXiv 1604.05976" implied for CPG | 1604.05976 is a drug-repositioning paper. The CPG paper is **Yamaguchi et al., IEEE S&P 2014, DOI 10.1109/SP.2014.44** | rq3a note §0; [74] |
| "PyCG (arXiv 2103.14295)" | 2103.14295 is a bipedal-locomotion RL paper. PyCG is **arXiv 2103.00587**, ICSE 2021, DOI 10.1109/ICSE43902.2021.00146 | rq3a note §0; [75] |
| "Mo et al. (Eco)Architecture smells (arXiv 1703.10562?)" | 1703.10562 is a solar-physics paper. No paper titled "(Eco)Architecture smells" was found; the real work is the **Mo–Cai–Kazman design-rule-space line** (WICSA 2015; TSE 2021) | rq3b note §0; [79, 80] |
| "Maffort et al. ESE 2015" | Correct, with two refinements: **issue year 2016** (EMSE 21(3):854–895; online 2015), and **it is not a DCL paper** — the tool is ArchLint, heuristics as SQL over a dependency DB | rq2 note F1; [32] |
| "Sourcetrail (timeline)" | **Not substantiated.** Sourcetrail is a dependency-graph explorer, discontinued, repo archived Dec 2021; no commit-history/timeline feature documented | rq2 note F8; [58] |
| "Maffort … e.g. Maffort et al. ESE 2015" as "architectural erosion/drift" | Maffort is *violation mining from history*; erosion/drift trajectories are a separate literature (Sas 2019; Gnoyke 2024; EMSE 2022; Jolak 2025) | rq2 note F3; [32, 34, 35, 36, 38] |
| "Roughly a quarter of real ADRs are convertible into checkable constraints" | **UNVERIFIED.** No source reports a conversion rate. Nearest (different) data: 24.7% of sampled cases judged "Code is Insufficient to Answer" in a 980-ADR corpus | §1.6, §5.6/E16; [21] |
| "EvoGraph", "GitGraph" as code-evolution graph systems | **Not found** with verifiable documentation; excluded rather than described (**searched negative**) | rq2 note, coverage §6 |
| Kouroshfar ICSE 2013 as a study | It is a **2-page ACM Student Research Competition paper**, not a full study | rq3b note §0; [83] |
| Wang et al. ICPC 2022 DOI | DOI printed in the source is inconsistent with the ICPC 2022 proceedings prefix; cite the computer.org URL instead | rq2 note, coverage §3; [47] |

**Not a correction, but a warning:** there are two distinct artefacts named **SmellBench** (an arXiv paper on PyExamine-detected smells in scikit-learn, and a GitHub injection-based benchmark with 147 instances/294 cases). Neither cites the other. Do not cite them interchangeably [3, 4].

---

## 7. Disagreements, gaps, and what is *not* established

**Genuine disagreements / tensions in the evidence:**
1. **Test oracle vs analyzer oracle.** RepairAgent, ChatRepair and Repilot use tests only [5, 6, 7]; InferFix, CodeCureAgent, SmellBench and Patch Space Exploration use the analyzer [1, 2, 3, 10]. These are different task families and their numbers are not comparable. Any claim that "LLM repair works" must specify which oracle.
2. **Repair aggressiveness.** SmellBench's most aggressive agent resolves the most smells **and** regresses the codebase net −109; conservative agents net +15/+16. "Resolution rate" alone is a misleading metric — a point the paper itself makes [3].
3. **Temporal graph cost.** AeonG reports **up to 5.73× lower storage** and **up to 2.57× lower latency** [53]; PETGraphDB reports **~19.6×** cost for analytical temporal queries [54]. These are not contradictory (different workloads and designs) but they mean no single temporal-KG cost figure can be quoted without naming the workload.
4. **Whether smells matter.** Mo et al. find strong bug-rate gradients, corroborated by their own earlier smaller study (same author group — corroboration, not independent replication) [80]; Sas et al. state that smells' impact on maintenance effort "has not been thoroughly investigated" [85]; Arcelli Fontana et al. find architectural smells are not derivable from code smells (implying they carry independent signal) [84]. Treat "architectural smells predict defects" as established *correlationally* and "more conformance rules reduce defects" as **not established at all** (**searched negative**).
5. **Freezing as a solution vs a trap.** ArchUnit's freeze design is deliberately monotone-improvement-only; the same property means a frozen store can silently rot (its own open issue: >70 files with orphans and references to deleted tests) [41].

**Fragility analysis — what collapses if a load-bearing single-source result is wrong.** Three results carry most of the brief's weight, and each is single-source: (i) **CodeCureAgent's change-approver ablation** (0 / 9 / 123 / 249 false accepts) is the sole quantitative justification for E1's and E2's analyzer-clean gate — if it does not replicate, the gate becomes a design preference rather than an evidence-backed requirement, and no other reviewed source measures the cost of removing analyzer validation. (ii) **DRCodePilot's `-DR` ablation** (−81.65% / −94.44%) is the sole evidence that rationale text can move repair outcomes — if it fails to transfer off its exact-match, rationale-conditioned benchmark, E1's arm (c) becomes exploratory and the "rationale matters" hypothesis rests only on Maffort-style prose-rot observations. (iii) **Maffort's SGA result** (53% of violations in year 1; zero detected after discarding four years) is the sole empirical basis for E7's rule-vitality tracking and E8's vacuity measurement — if it is an artefact of one proprietary subject system with unmeasured recall, RQ2's experiments lose their motivating evidence and become exploratory instrumentation rather than hypothesis tests. Everything in RQ3's *documentation-layer* findings (tool semantics, rule vocabularies, the Tier A/B/C boundary) is robust to these failures because it is quoted from primary documentation rather than measured.

**Searched negatives (evidence of absence within search, not proof):**
- No peer-reviewed study of **vacuous / dead / rotted conformance rules** [46, 47].
- No study testing whether **richer rule vocabulary** improves outcomes [80].
- No **architecture-rule-violation repair** benchmark [3, 4, 20].
- No implementation of `valid_from`/`valid_to` on an architecture rule in any mainstream tool [41, 42, 43, 44, 33, 45].
- No published absolute storage/latency figures for a **per-commit code** knowledge graph [50, 51].
- No ablation isolates **ADR/decision text** as a repair input *within the readable corpus* (the mechanism is precedented by DRCodePilot; the domain is not; three nearest candidates were unread — `sqlew` [19], Schröder et al. [104], ICSM 2008 [105]) [8, 9].

**Blocked / unverified items carried forward:**
- **InferFix's per-bug-type table** (arXiv HTML renders Tables 2–7 as images) → per-category exact values blocked; only the abstract's 76.8%/65.6% and narrative ranges were obtained [1].
- **InferFix's numeric analyzer-clean rate** → not reported in the accessible text; recorded as "not reported in accessible text", **not** as zero [1].
- **`sqlew` full text** → HTTP 403; **no numbers cited** [19].
- **CORE's headline** ("could revise 59.2% Python files…") → publisher abstract only, and its per-1,000 numbers are quoted *via* CodeCureAgent's baseline table; do not cite bare [12, 2].
- **ICSM 2008 live-feedback experiment** → authors/results not retrieved [105].
- **Schröder ontology papers (×3)** → metadata only; no method/result claims [104].
- **Wang et al. ICPC 2022 DOI** → inconsistent; cite URL [47].
- **Zimmermann & Nagappan ICSE 2008 "+10 pp recall"** → second-hand; primary PDF not obtained [82].
- **SmellBench (arXiv) Table 4–7 rows** → HTML tables did not extract; per-agent "new smells" values available only for agents discussed in prose [3].

---

## 8. Open questions

1. **What *is* the ADR→checkable-constraint conversion rate?** Shepherd asserts ~25% (requester claim, **UNVERIFIED**); no source located in this review measures it. E16 is the experiment that would settle it. The relevant variable is likely not "ADR" but ADR *content class* — deployment/infrastructure and principle-driven ADRs dominate LLM failure modes (42.39% + 26.09% of errors — **auto-report-mediated / UNVERIFIED**, see §7) [21]. The nearest available measurement of the same population, the 24.7% CIA frequency, is likewise soft (agreement 0.1574).
2. **Does the graph evidence path add anything beyond the verdict?** Unknown (**searched negative**). The closest positive signal is Li et al.'s 25.9% → 64.7% improvement in *human* detection when symptoms are supplied [22] — suggestive, but a different actor and outcome.
3. **Is evidence-path persistence sound when the upstream engine's paths are non-deterministic?** `grimp` documents run-to-run variability for equal-length illegal routes [67]. Shepherd must canonicalise; no published canonicalisation scheme was found (**searched negative**).
4. **Can rule vacuity be detected cheaply and exactly?** Empty-selector detection catches renames; it does **not** catch "selector still resolves, predicate no longer discriminates" (the consistent-mutant case) [48]. Is there a workable mutation-style test (synthesise a violating edit, assert the rule fires) that scales?
5. **Does dismissal persistence decay rule quality?** ArchUnit's monotone freeze [41] and SonarQube's rating exclusion [42] both suggest persisted waivers create blind spots. No measurement found (**searched negative**).
6. **Which temporal design is right at Shepherd's scale?** Snapshot-per-commit is simplest and Compass-like [50]; delta is cheapest in theory but the incremental-APA non-guarantee is a real risk [56]; interval edges give as-of queries natively at a measured storage premium [53]. No code-graph measurement exists (**searched negative**) [50].
7. **Is `CALLS` accuracy good enough to make `CALLS`-based constraints trustworthy?** PyCG-class extraction has a known accuracy ceiling [75], and ArchUnit's documented False-negative mode shows verdicts depend on graph completeness [60].

**Reviewer-flagged items recorded rather than resolved.** Two internal review passes were run on this brief. The following were *marked* rather than fully closed, and are recorded here so a reader does not mistake the marking for a finding: (a) the five ADR-error-taxonomy percentages in §5.6/E16 are **auto-report-mediated and remain UNVERIFIED** — they should be re-derived from 2602.07609's own tables before use (its HTML was readable first-hand for the 24.7% figure, so this is feasible); (b) the Martin `D` divisor convention is **unresolved** in this review (see §5.2) and must be pinned before the ADG computes `D`; (c) two load-bearing ablations — CodeCureAgent's approver table and DRCodePilot's `-DR` table — were verified from full-text research notes and one lead re-read of the paper text, but not re-tabulated line-by-line in the final pass (see the citation log); (d) the "searched negative" claims rest on the query sets recorded in the research notes rather than a documented multi-database protocol, so they are search-scoped, not exhaustive.

---

## 9. Next steps (sequenced)

1. **Read the three Schröder ontology papers** (DOI 10.1145/3241403.3241457; 10.1109/apsec48747.2019.00017; 10.1145/3344948.3344956). They are the most on-target unread work for "documenting and validating architecture rules." [104]
2. **Obtain the ICSM 2008 live-feedback experiment** (computer.org/csdl/proceedings-article/icsm/2008/04658077/12OmNvAAtJJ). It is the only located controlled experiment on compliance feedback [105].
3. **Build E4's benchmark before running E1–E3.** Without it, the RQ1 experiments have no host [3, 4, 20].
4. **Implement E7 (rule vitality) and E15 (metric-definition versioning) immediately.** Both are small schema changes with documented failure modes behind them [32, 67, 68], and E7 is the prerequisite for E8.
5. **Run E10 (temporal cost profile) early** if the ADG is to persist history, because the design choice constrains the schema and is expensive to change later [50, 51, 53, 54].
6. **Adopt E5's reporting discipline before any experiment runs, not after.** Retro-fitting model fingerprints and run dates is impossible [23].

---

## 10. Sources

Direct URLs for every claim above. Numbered in the order cited; every number below is cited at least once in §1–§9, and every inline citation resolves to an entry here. Grouped by role. Research-note files are listed in §2.

**RQ1 — repair systems and benchmarks**
[1] InferFix: https://arxiv.org/abs/2303.07263 · DOI https://doi.org/10.1145/3611643.3613892
[2] CodeCureAgent: https://arxiv.org/abs/2509.11787 · DOI https://doi.org/10.1145/3808140
[3] SmellBench (arXiv): https://arxiv.org/abs/2605.07001 · data DOI https://doi.org/10.5281/zenodo.19247588
[4] SmellBench (GitHub, distinct work): https://github.com/critical88/SmellBench/
[5] RepairAgent: https://arxiv.org/abs/2403.17134 · DOI https://doi.org/10.1109/ICSE55347.2025.00157
[6] ChatRepair: https://arxiv.org/abs/2304.00385 · DOI https://doi.org/10.1145/3650212.3680323
[7] Repilot: https://arxiv.org/abs/2309.00608 · repo https://github.com/ise-uiuc/Repilot
[8] DRCodePilot: https://arxiv.org/abs/2408.12056 · DOI https://doi.org/10.1145/3691620.3695537
[9] AssistRA: https://riccardorubei.github.io/files/W_2025_1.pdf · DOI https://doi.org/10.1109/ICSA-C65153.2025.00063
[10] Patch Space Exploration using Static Analysis Feedback: https://arxiv.org/abs/2308.00294
[11] Tencent FP-reduction study: https://dl.acm.org/doi/full/10.1145/3786583.3786910
[12] CORE: https://dl.acm.org/doi/10.1145/3643762
[13] Copilot Autofix (responsible use): https://docs.github.com/en/code-security/responsible-use/responsible-use-autofix-code-scanning
[14] Semgrep Autofix: https://docs.semgrep.dev/semgrep-code/triage-remediation/autofix
[15] SAND (fuzzing, the negative result): https://arxiv.org/abs/2402.16497
[16] CodeCompose (what 2305.12050 actually is): http://arxiv.org/abs/2305.12050v2
[17] 3D Diffusion Policy (what 2403.03954 actually is): http://arxiv.org/abs/2403.03954v7
[18] Generate-and-validate patch search spaces: https://arxiv.org/abs/1602.05643
[19] `sqlew` (blocked full text): https://www.techrxiv.org/doi/10.36227/techrxiv.177205025.54351571

**RQ1 — design constraints, ADRs, experiment methodology, benchmarks**
[20] Design-constraint compliance: https://arxiv.org/abs/2604.05955
[21] ADR violation detection (980 ADRs / 109 repos): https://arxiv.org/abs/2602.07609
[22] Li et al., erosion violation symptoms: https://arxiv.org/abs/2306.08616
[23] EMSE LLM study guidelines: https://arxiv.org/abs/2508.15503
[24] Program-repair experimental settings: https://arxiv.org/abs/2609.17993
[25] Context-file ablation (equivalence testing): https://arxiv.org/abs/2607.27250
[26] SWE-bench: https://www.swebench.com/ · Verified https://www.swebench.com/verified
[27] SWE-Gym: https://arxiv.org/abs/2412.21139
[28] SWE-smith: https://arxiv.org/abs/2504.21798 · dataset https://huggingface.co/datasets/SWE-bench/SWE-smith
[29] BugsInPy: https://arxiv.org/abs/2401.15481 · reproducibility DOI https://doi.org/10.1109/scam59687.2023.00036
[30] QuixBugs: https://jkoppel.github.io/QuixBugs/quixbugs.pdf
[31] Defects4J: https://github.com/afonsohfontes/defects4j

**RQ2 — history mining, erosion, temporal validity, temporal graphs**
[32] Maffort et al. (DOI): https://doi.org/10.1007/s10664-014-9348-2 · full text https://rmod-files.lille.inria.fr/Team/Texts/Papers/Maff14a-ArchitecturalViolations-EMSE.pdf · HAL mirror https://inria.hal.science/hal-01075642/file/2015_emse.pdf
[33] DCL 2.0: https://doi.org/10.1186/s13173-017-0061-z · DCLsuite http://rterrabh.github.io/DCL/
[34] Sas et al., ICSME 2019: https://www.computer.org/csdl/proceedings-article/icsme/2019/309400a557/1fHlIl3XxpS
[35] Gnoyke et al., JSS 2024: https://doi.org/10.1016/j.jss.2024.112170
[36] EMSE 2022 industrial smell evolution: https://doi.org/10.1007/s10664-022-10132-7
[37] Le et al., ICSA 2018: https://ieeexplore.ieee.org/document/8417151
[38] Jolak et al., JSS 2025: https://www.sciencedirect.com/science/article/pii/S0164121225000500
[39] Architectural changes in commits (Internetware 2021): https://dl.acm.org/doi/fullHtml/10.1145/3457913.3457924
[40] Erosion symptoms in code reviews (OpenStack): https://arxiv.org/pdf/2201.01184
[41] ArchUnit freezing: https://www.archunit.org/userguide/html/000_Index.html · javadoc https://javadoc.io/doc/com.tngtech.archunit/archunit/latest/com/tngtech/archunit/library/freeze/FreezingArchRule.html · store layout https://javadoc.io/doc/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/freeze/TextFileBasedViolationStore.html · issue 1264 https://github.com/TNG/ArchUnit/issues/1264 · issue 510 https://github.com/TNG/ArchUnit/issues/510
[42] SonarQube: new code https://docs.sonarsource.com/sonarqube-server/user-guide/about-new-code · NCD config https://docs.sonarsource.com/sonarqube-server/project-administration/adjusting-analysis/configuring-new-code-calculation · issues (10.1) https://docs.sonarsource.com/sonarqube-server/10.1/user-guide/issues · 2025.2 managing https://docs.sonarsource.com/sonarqube-server/2025.2/user-guide/issues/managing
[43] import-linter: https://import-linter.readthedocs.io/en/latest/contract_types/ · repo https://github.com/seddonym/import-linter
[44] jQAssistant: https://jqassistant.github.io/jqassistant/current/ · https://github.com/jqassistant
[45] ADR guidance: Microsoft https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record · MADR https://adr.github.io/madr/ · community repo https://github.com/architecture-decision-record/architecture-decision-record · GOV.UK https://www.gov.uk/government/publications/architectural-decision-record-framework · Nygard 2011 https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
[46] Rule-testing fixtures: ESLint https://eslint.org/docs/head/integrate/nodejs-api · Semgrep https://docs.semgrep.dev/writing-rules/testing-rules · CodeQL https://docs.github.com/en/code-security/codeql-cli/using-the-advanced-functionality-of-the-codeql-cli/testing-custom-queries · Ruff RUF100 https://docs.astral.sh/ruff/rules/unused-noqa · promtool coverage https://github.com/prometheus/prometheus/pull/18432 · rulecov https://github.com/Yiwit/rulecov
[47] Wang et al. ICPC 2022: https://www.computer.org/csdl/proceedings-article/icpc/2022/929800a516/1EpKKbUIfPG
[48] Okun, specification mutation: https://csrc.nist.gov/CSRC/media/Presentations/Specification-Mutation-for-Test-Generation-and-Ana/images-media/thesis_vadim.pdf
[49] Secure-code-review SAST study (ISSTA 2024): https://dl.acm.org/doi/10.1145/3650212.3680313
[50] Compass versioned history: https://compass.crab.build/docs/guides/versioned-history
[51] TGI (EDBT 2016): https://openproceedings.org/2016/conf/edbt/paper-29.pdf
[52] Bitemporal graph model (`TPGM+`): https://arxiv.org/html/2111.13499v1
[53] AeonG: https://www.vldb.org/pvldb/vol17/p1515-lu.pdf · https://arxiv.org/pdf/2304.12212
[54] PETGraphDB: https://arxiv.org/pdf/2512.05417
[55] Software Heritage: https://www.softwareheritage.org/wp-content/uploads/2020/01/msr-2019-swh.pdf · https://arxiv.org/pdf/2011.07824
[56] Incremental algebraic program analysis: https://arxiv.org/pdf/2412.10632
[57] CodeCompass: https://codecompass.net/ · DOI https://doi.org/10.1145/3196321.3196352 · usage doc https://github.com/Ericsson/CodeCompass/blob/master/doc/usage.md
[58] Sourcetrail (archived): https://github.com/CoatiSoftware/Sourcetrail
[59] Gevol/Tgrip: http://www2.cs.arizona.edu/~kobourov/tgrip.pdf

**RQ3 — tools, vocabularies, metrics, DSL failure modes, prose→rules**
[60] ArchUnit user guide + library API: https://www.archunit.org/userguide/html/000_Index.html · metrics javadoc https://javadoc.io/doc/com.tngtech.archunit/archunit/1.3.2/com/tngtech/archunit/library/metrics/ComponentDependencyMetrics.html · Architectures.java https://github.com/TNG/ArchUnit/blob/master/archunit/src/main/java/com/tngtech/archunit/library/Architectures.java
[61] jQAssistant jMolecules plugin + metrics plugin: https://jqassistant.github.io/jqassistant/current/ · https://central.sonatype.com/artifact/org.jqassistant.contrib.plugin/jqassistant-java-metrics-plugin
[62] CodeQL CLI: https://docs.github.com/en/code-security/codeql-cli/getting-started-with-the-codeql-cli/about-the-codeql-cli
[63] pytest-archon: https://pypi.org/project/pytest-archon · https://github.com/jwbargsten/pytest-archon
[64] ArchUnitPython: https://pypi.org/project/archunitpython/ · https://github.com/LukasNiessen/ArchUnitPython/blob/main/README.md
[65] PyTestArch: https://pypi.org/project/PyTestArch
[66] tach: https://github.com/tach-org/tach · https://github.com/tach-org/tach/blob/main/README.md · docs https://docs.gauge.sh/
[67] grimp (import-linter's engine): https://grimp.readthedocs.io/en/latest/usage.html
[68] Sonargraph: https://hello2morrow.com/products/sonargraph/architect · metric definitions https://eclipse.hello2morrow.com/doc/standalone/content/metric_definitions.html · metric-definition churn (15.2.0) https://blog.hello2morrow.com/2025/06/changes-to-the-sonargraph-dashboard/
[69] DV8: anti-patterns https://docs.archdia.net/DesignAnti-patterns.html · CLI anti-pattern commands https://archdia.com/pages/user-guide-cli-anti-pattern-commands · Modularity Violation https://archdia.com/pages/modularity-violation
[70] Lattix: Design Rules https://www.lattix.com/wp-content/uploads/2024/03/DesignRules.pdf · enforce architecture https://docs.lattix.com/lattix/whyUseLattixArchitect/Specify_and_Enforce_Architecture.html · monitoring/enforcing https://docs.lattix.com/lattix/userGuide/Monitoring_and_Enforcing_Architecture.html
[71] Structure101: spec editor https://www.sonarsource.com/structure101/docs/java/studio6/content/Spec%20Editor.htm · architecture diagrams https://structure101.com/help/java/studio5/Content/perspectives/architecture-diagrams.html
[72] jQAssistant metrics plugin https://github.com/jqassistant-contrib/jqassistant-java-metrics-plugin · PlantUML rule plugin (archived) https://github.com/jqassistant-archive/jqassistant-plantuml-rule-plugin
[73] Joern / CPG: https://docs.joern.io/code-property-graph/ · CPG spec 1.1 https://cpg.joern.io/
[74] CPG foundations: Yamaguchi et al., IEEE S&P 2014, DOI https://doi.org/10.1109/SP.2014.44 · language-independent CPG platform https://arxiv.org/abs/2203.08424
[75] PyCG: https://arxiv.org/abs/2103.00587 · DOI https://doi.org/10.1109/ICSE43902.2021.00146
[76] Martin, OO design quality metrics (1994): https://condor.depaul.edu/dmumaugh/OOT/Design-Principles/oodmetrc.pdf
[77] Arcan smells: https://docs.arcan.tech/latest/architectural_smells/
[78] Designite smells: https://www.designite-tools.com/docs/features_cs.html
[79] Mo et al., WICSA 2015: https://ranmo.github.io/papers/wicsa2015-Pattern.pdf · DOI https://doi.org/10.1109/WICSA.2015.12
[80] Mo et al., TSE 2021: https://www.cs.drexel.edu/~yfcai/papers/2019/tse2019.pdf · DOI https://doi.org/10.1109/TSE.2019.2910856
[81] Wong et al., Clio (ICSE 2011): https://www.cs.drexel.edu/~yc349/CS575/Week9/ICSE11.ModularityViolation.pdf · DOI https://dl.acm.org/doi/10.1145/1985793.1985850
[82] Zimmermann & Nagappan, ICSE 2008: https://dl.acm.org/doi/10.1145/1368088.1368161
[83] Kouroshfar, ICSE 2013 SRC: https://mason.gmu.edu/~ekourosh/icse13src.pdf
[84] Arcelli Fontana et al., JSS 2019: https://arxiv.org/abs/1904.11755 · DOI https://doi.org/10.1016/j.jss.2019.04.066
[85] Sas et al., JSM 2022: https://doi.org/10.1002/smr.2398
[86] Pigazzini et al., MSR4SA 2021: https://ceur-ws.org/Vol-2978/msr4sa-paper2.pdf
[87] Caracciolo et al., IWESEP 2016: https://pure.rug.nl/ws/files/32628894/07464551.pdf · DOI https://doi.org/10.1109/IWESEP.2016.12 · Caracciolo et al., WICSA 2015 (unified approach) https://doi.org/10.1109/wicsa.2015.11
[88] Ali et al., EMSE 2017: https://link.springer.com/article/10.1007/s10664-017-9515-3
[89] Ayewah et al., 2007: https://findbugs.cs.umd.edu/FindBugsExperiences07.pdf · 2008: https://research.google.com/pubs/archive/34339.pdf
[90] Habib & Pradel, ASE 2018: https://software-lab.org/publications/ase2018_static_bug_detectors_study.pdf · DOI https://doi.org/10.1145/3238147.3238213
[91] Imtiaz et al., ISSRE 2019: https://www.microsoft.com/en-us/research/publication/how-do-developers-act-on-static-analysis-alerts-an-empirical-study-of-coverity-usage
[92] Hu et al., PACMSE 2025: https://dl.acm.org/doi/10.1145/3715729
[93] Johnson et al., ICSE 2013: https://people.cs.gmu.edu/~johnsonb/docs/icse2013.pdf · DOI https://doi.org/10.1109/ICSE.2013.6606613
[94] ESEM 2024 SAST survey: https://dl.acm.org/doi/10.1145/3674805.3690750
[95] Buchgeher et al., IEEE Access 2023: https://ieeexplore.ieee.org/document/10155430 · DOI https://doi.org/10.1109/ACCESS.2023.3287654
[96] ArchGuard (ICSA 2026): https://publikationen.bibliothek.kit.edu/1000191263
[97] Bhat et al., ECSA 2017: https://link.springer.com/content/pdf/10.1007/978-3-319-65831-5_10.pdf
[98] UnArch: https://arxiv.org/abs/1704.04798
[99] DRMiner: https://arxiv.org/abs/2405.19623
[100] Dhar et al., ICSA 2024: https://arxiv.org/abs/2403.01709
[101] Ammons et al., POPL 2002: https://doi.org/10.1145/503272.503275
[102] CSight, ICSE 2014: https://people.cs.umass.edu/~brun/pubs/pubs/Beschastnikh14icse.pdf
[103] ARSENAL: https://arxiv.org/abs/1403.3142
[104] Schröder & Riebisch: https://doi.org/10.1145/3241403.3241457 · Schröder & Buchgeher APSEC 2019: https://doi.org/10.1109/apsec48747.2019.00017 · Discovering architectural rules: https://doi.org/10.1145/3344948.3344956
[105] ICSM 2008 (unverified lead): https://www.computer.org/csdl/proceedings-article/icsm/2008/04658077/12OmNvAAtJJ
[106] Fitness functions: https://nealford.com/downloads/Evolutionary_Architecture_Keynote_by_Neal_Ford.pdf · https://www.infoq.com/articles/fitness-functions-architecture/

**Added during citation verification** (claims in §4.4, §5.1 and §5.2 whose support existed in the research notes but had no entry in the draft's source list):
[107] W3C Spatial Data on the Web "valid time" use case (the only "valid time" hit for architecture tooling; geospatial, not software architecture): https://w3c.github.io/sdw/UseCases/SDWUseCasesAndRequirements.html#ValidTime
[108] CodeQL QL language reference (Datalog dialect; recursion and aggregates): https://codeql.github.com/docs/ql-language-reference/about-the-ql-language/ · https://codeql.github.com/docs/ql-language-reference/ql-language-specification/
[109] jQAssistant jMolecules plugin (named style rule groups; layer-level `:DEPENDS_ON`): https://github.com/jqassistant-plugin/jqassistant-jmolecules-plugin

**Present in the research notes but not cited above.** These sources were verified reachable but no claim in §1–§9 depends on them, so they carry no number and no inline citation. They are listed for completeness rather than as support for any statement.

- PredicateFix: https://arxiv.org/abs/2503.12205
- StaticFixer: https://arxiv.org/abs/2307.12465
- Redemption: https://doi.org/10.58012/tfvg-1k55
- RepairBench: https://arxiv.org/abs/2409.18952 · DOI https://doi.org/10.1109/LLM4Code66737.2025.00006
- LLM APR survey: https://arxiv.org/abs/2506.23749
- ADR extraction from commits: https://arxiv.org/abs/2609.03721
- ADR text mining/classification: https://arxiv.org/abs/2609.07375
- Specification-format × model interaction (ADRs/ArchUnit-style specs): https://arxiv.org/abs/2608.21747
- THEMIS (requirement-code graph): https://arxiv.org/abs/2609.14913
- Brunet et al., WCRE 2012: https://doi.org/10.1109/WCRE.2012.35
- pydeps: https://pydeps.readthedocs.io/en/latest/
- Garcia et al., architectural bad smells (QoSA 2009): https://jgarcia.ics.uci.edu/wp-content/uploads/10.1.1.183.9958.pdf · DOI https://doi.org/10.1007/978-3-642-02351-4_10
- Le et al., architectural decay: https://arxiv.org/abs/2102.09835
- Li et al., erosion survey (2112.10934): https://arxiv.org/pdf/2112.10934v2

**Citation-numbering note.** Numbers run in the order of this list and are unique per source entry. Two tools appear under more than one role heading because they are cited for different claims: ArchUnit ([41] freezing/time semantics, [60] rule vocabulary and metrics) and jQAssistant ([44] store/temporal semantics, [61] and [72] rule/metric plugins; note that [61] and [109] carry the *same* jMolecules plugin URL, cited in two roles — treat as one source). Research-note files are not numbered sources; they are listed in §2.

**Verified first-hand during citation verification.** These quantitative claims were re-checked against the primary artefact for this pass and are now first-hand rather than note-mediated: the `promtool` coverage quote and `--coverage-threshold` (pull request text, [46]); the `rulecov` removal-in-isolated-worktrees mechanism (tool README, [46]); the 24.7% "Code is Insufficient to Answer" class frequency (arXiv 2602.07609 HTML, [21]); the *AssistRA* system name (author-hosted PDF, [9]); the *THEMIS* system name (arXiv 2609.14913 abstract — one of the uncited entries above).
