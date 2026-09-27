> **Sources:** the two `.provenance.md` files beside the run briefs, concatenated.
> See [README.md](README.md).


---

## Run 1 — `arch-decision-memory-scenarios`

*Source: [`notes/feynman-2026-09-25/arch-decision-memory-scenarios.provenance.md`](../notes/feynman-2026-09-25/arch-decision-memory-scenarios.provenance.md) @ `e3f0f17`*

# Provenance: Adjacent Application Scenarios for a Persistent Architectural Decision Memory (Shepherd)

- **Date:** 2026-09-25
- **Rounds:** 2 research rounds + 2 review passes. Round 1: four parallel researcher subagents (T1–T4, one per research question) in one async workflow (`2f4c8f19`, 4/4 ok). Round 2: verifier pass (96 citation keys resolved, every distinct source checked) → reviewer pass (PASS WITH REVISIONS: 0 FATAL, 2 MAJOR, 7 MINOR) → lead revision (W1–W9 applied, documented in §Revision notes) + lead verification of SmellBench full text (alpha_get_paper 2605.07001).
- **Sources consulted:** ~110 distinct records across the four research files (T1: 28, T2: 37, T3: 30, T4: 19, overlap between files); ~35 primary artifacts independently re-fetched in the reviewer pass; all 40 arXiv IDs API-verified; 11 sample DOIs OpenAlex-resolved; HF/GitHub/Zenodo artifacts fetched.
- **Sources accepted:** 99 (numbered list in the final brief, including 3 added during revision: [97] Xiao et al. ICSE 2016, [98] PyExamine MSR 2025, [99] Karan et al. 2026).
- **Sources rejected:** 9 candidate leads rejected with documented reasons: DREd tool (misattributed), ADRam tool (unverifiable), Akond Rahman architectural-knowledge attribution (misattributed), Arcan=de Silva authorship (incorrect; Arcan is Arcelli Fontana et al.), Decalog (not found), "decaying architectural cohesion" (not found), BugsInPy=arXiv 2005.01176 (wrong ID; correct 2401.15481), SpecRover=arXiv 2408.01832 (wrong ID; correct 2408.02232), PRCBench (not found after 3+ query rounds). Details: research files' rejected sections + cited brief §Rejected.
- **Verification:** PASS WITH NOTES. All load-bearing quantitative claims reproduce from primary sources (two PDF anchors re-read twice: Kazman ICSE-SEIP 2015, Xiao ICSE 2014; SmellBench full text read in revision). Remaining flagged residues (UNVERIFIED, non-load-bearing): [95] Archie DOI; [3] TSE-2019 subject languages; [72] Bench4BL Java label inferred; [78][79] replication-package download URL; [76] Defects4J version-pinned count (v2.0.0: 835 vs current v3.0.1: 854); [99] T1-S25 metadata-only; ~15 low-load DOIs accepted on OpenAlex-verification claims (listed in reviewer's acceptance evidence); 2026-dated venue records verified via OpenAlex/arXiv metadata only.
- **Plan:** outputs/.plans/arch-decision-memory-scenarios.md (with briefs -T1..-T4, task ledger, verification log, decision log)
- **Research files:** outputs/.drafts/arch-decision-memory-scenarios-T1.md; -T2.md; -T3.md; -T4.md
- **Supporting artifacts:** outputs/.drafts/arch-decision-memory-scenarios-draft.md (pre-citation draft); -cited.md (verifier's cited brief); -verification.md (reviewer report); -revised.md (final candidate)
- **Final deliverable:** outputs/arch-decision-memory-scenarios.md

---

## Run 2 — `shepherd-adg-decision-memory`

*Source: [`notes/feynman-2026-09-25/deepseek-run2/shepherd-adg-decision-memory.provenance.md`](../notes/feynman-2026-09-25/deepseek-run2/shepherd-adg-decision-memory.provenance.md) @ `e3f0f17`*

# Provenance: Shepherd — persistent architectural-decision-memory over source code (ADG)

- **Date:** 2026-09-25
- **Slug:** `shepherd-adg-decision-memory`
- **Rounds:** 2 evidence rounds + 2 verification rounds
  - Round 1: 5 parallel `researcher` subagents (T1–T5) + lead-owned anchor verification
  - Round 2: lead re-read of 3 load-bearing primary sources (`alpha_get_paper` 2605.07001; `alpha_ask_paper` 2408.12056 and 2509.11787)
  - Verification round 1: `verifier` subagent (citation pass)
  - Verification round 2: `reviewer` subagent (audit) + `reviewer` subagent (focused post-fix re-check)
- **Verification:** PASS WITH NOTES
  - Citation verification: PASS — 190 distinct URLs, 43 arXiv IDs, 40 DOIs checked; 2 dead javadoc URLs corrected; 3 source entries added (4 URLs); 109 numbered sources, every one cited inline, zero undefined inline numbers, zero orphan sources (re-checked by the lead with a script).
  - Review pass 1: 2 FATAL, 10 MAJOR, 24 MINOR found.
  - Review pass 2 (post-fix): W1 closed; W2 closed in 3 of 4 locations at that time, with a narrowed residual (M1) since fixed; **no new FATAL**; M1–M4 and minors M5–M15 fixed; the contested Martin divisor attribution was softened rather than asserted, and is recorded as unresolved.
  - Unresolved items are recorded in §8 of the deliverable under "Reviewer-flagged items recorded rather than resolved" and are marked inline rather than hidden.

## Sources

- **Consulted:** 109 distinct numbered sources in the deliverable plus research-note-only sources; 190 distinct URLs, 43 arXiv IDs, 40 DOIs link-verified.
- **Accepted (primary anchors):** Maffort et al. (EMSE 2016, DOI 10.1007/s10664-014-9348-2, full text read); InferFix (arXiv 2303.07263); CodeCureAgent (arXiv 2509.11787, tables re-read); SmellBench (arXiv 2605.07001, re-read); DRCodePilot (arXiv 2408.12056, tables re-read); RepairAgent (arXiv 2403.17134); ChatRepair (arXiv 2304.00385); AssistRA (DOI 10.1109/ICSA-C65153.2025.00063); Su et al. ADR violations (arXiv 2602.07609); Mo et al. TSE 2021 (DOI 10.1109/TSE.2019.2910856); Caracciolo et al. IWESEP 2016 (DOI 10.1109/IWESEP.2016.12); DV8/Arcan/Designite tool docs; ArchUnit/import-linter/grimp/jQAssistant/Sonargraph/Lattix/Structure101 docs; Compass/TGI/TPGM+/AeonG/PETGraphDB/Software Heritage for temporal graph design.
- **Rejected / dead:** 2 dead javadoc URLs replaced (`www.javadoc.io/static/...` → `javadoc.io/doc/...` for `TextFileBasedViolationStore` and `ComponentDependencyMetrics`). Sources explicitly rejected as irrelevant or non-existent: the arXiv IDs `2305.12050`, `2403.03954`, `1604.05976`, `2103.14295`, `1703.10562` (each identified as a different paper than the brief implied); "SAND" as an LLM repair system (does not exist — the identifier is a fuzzing framework); "EvoGraph" and "GitGraph" as code-evolution graph systems (not locatable with verifiable documentation); "(Eco)Architecture smells" (no such paper located).
- **Blocked (no numbers cited from these):** `sqlew` TechRxiv preprint (HTTP 403, full text never read — characterised from abstract/landing page only); InferFix per-bug-type table and numeric analyzer-clean rate (arXiv HTML renders tables as images); SmellBench arXiv Tables 4–7 rows (tables did not extract); three Schröder ontology papers (metadata only); ICSM 2008 live-feedback experiment (authors and results not retrievable); CORE headline (publisher abstract only, quoted via CodeCureAgent's baseline table); the five ADR-error-taxonomy percentages in §5.6/E16 (auto-report-mediated, marked UNVERIFIED inline).

## Artifacts

- **Final deliverable:** `outputs/shepherd-adg-decision-memory.md` (687 lines, 112 KB)
- **Plan:** `outputs/.plans/shepherd-adg-decision-memory.md`
- **Per-researcher briefs:** `outputs/.plans/shepherd-adg-decision-memory-T1.md` … `-T5.md`
- **Research files (5 subagent streams + lead):**
  - `outputs/.drafts/shepherd-adg-decision-memory-research-rq1a-repair.md`
  - `outputs/.drafts/shepherd-adg-decision-memory-research-rq1b-rationale-bench.md`
  - `outputs/.drafts/shepherd-adg-decision-memory-research-rq2-temporal.md`
  - `outputs/.drafts/shepherd-adg-decision-memory-research-rq3a-tools.md`
  - `outputs/.drafts/shepherd-adg-decision-memory-research-rq3b-metrics-dsl.md`
  - `outputs/.drafts/shepherd-adg-decision-memory-research-direct.md`
- **Draft chain:** `-draft.md` → `-cited.md` (verifier output) → `-revised.md` (final candidate, after both review passes)
- **Review artifacts:** `-verification.md` (review pass 1), `-review2.md` (focused re-check)

## Child-run receipts

| key | runId | status | artifact | lines |
|---|---|---|---|---|
| T1 RQ1a repair | 3319e63b-3950-4eae-88c2-b29db5fabcc0 | completed, ok | research-rq1a-repair | 282 |
| T2 RQ1b rationale/benchmarks | c3fb0737-d4c3-4bba-b829-198f69c37cdf | completed, ok | research-rq1b-rationale-bench | 641 |
| T3 RQ2 temporal | 5080fdbc-5a68-47ac-bda0-bcc45af1d5f1 | completed, ok | research-rq2-temporal | 614 |
| T4 RQ3a tools | 602a861a-be4f-40c1-a6f4-24b1a2cfb152 | completed, ok | research-rq3a-tools | 1116 |
| T5 RQ3b metrics/DSL | ce13ecc8-c54f-4c70-a9b2-f1e0adbf8e96 | completed, ok | research-rq3b-metrics-dsl | 359 |
| Verifier | c042ef23-6089-49e8-97f1-33c08ca5c4c5 | completed | `-cited.md` | 683 |
| Reviewer (pass 1) | 0e309141-19b3-49bb-876c-deae914ff94d (revived from 8608a136) | completed | `-verification.md` | 372 |
| Reviewer (pass 2) | 40cdd699-a67b-4d37-a752-af7f97cf8776 | completed | `-review2.md` | 203 |

**Infrastructure note.** Reviewer pass 1 stalled on a `find /` filesystem search; it was interrupted, revived with explicit read-tool guidance, and completed. Reviewer pass 2 could not locate `-verification.md` on its own filesystem view, so it could not check the pass-1 findings item-by-item; it instead re-audited every universal/negative in §1–§9 from the revised text, which is why that limitation is recorded rather than treated as a clean pass.

## Notes on integrity

- No number, table, dataset, sample size, or ablation in the deliverable is invented. Every quantitative claim traces to a source URL or a research-note read, and the ones that could not be traced were marked rather than removed or softened.
- The requester's ~25% ADR-convertibility premise is reported as **UNVERIFIED** and is the target of proposed experiment E16 rather than an assumption of the report.
- The requester's premise errors (five wrong arXiv IDs, "SAND", "Repilot" characterisation, "Sourcetrail timeline") are corrected in §6 rather than inherited.
- Three quantitative claims were independently re-read from primary text by the lead after the subagent research and after the citation pass: DRCodePilot's `-DR` ablation (−81.65% / −94.44%), CodeCureAgent's change-approver ablation (968/0 → 961/9 → 861/123 → 751/249), and SmellBench's results (47.7% resolved; 140 new smells → net −109; 63.1% expert-verified false positives; Kendall's W = 0.939). All matched the draft verbatim.

---

## Run 3 — `beyond-compliance-applications`

*Source: [`notes/feynman-2026-09-27/beyond-compliance-applications.provenance.md`](../notes/feynman-2026-09-27/beyond-compliance-applications.provenance.md) @ `e3f0f17`*

# Provenance: Beyond-compliance applications of an architectural decision graph with persistent decision memory

- **Date:** 2026-09-26
- **Slug:** `beyond-compliance-applications`
- **Plan:** `outputs/.plans/beyond-compliance-applications.md` (approved verbatim; all five pre-registered suspicions in plan §7 checked and given verdicts in the deliverable §6)
- **Rounds:** 3
  1. **Evidence gathering (round 1):** one async `workflowScript` with 5 parallel `researcher` children (`runs.all`, `globalConcurrencyLimit: 4`), run `b1a417d7-da33-460b-b6f9-6afcdb3027fd`, 5/5 `ok: true`, wall time 7m14s — plus lead-owned anchor reads of the four load-bearing primary sources.
  2. **Verification (round 2):** `verifier` subagent, run `247fddff-27d0-4676-9804-74c9e623b781` — added 84 numbered inline citations and a verified Sources section, produced the cited file.
  3. **Review (round 3):** `reviewer` subagent, run `57b48ca1-6238-44cd-a5ca-e7d7157c9c01` — adversarial evidence audit; 3 MAJOR / 17 MINOR, **no FATAL**, all applied.

- **Verification:** **PASS WITH NOTES**
  - **Citation integrity (scripted, reproducible):** body contains 602 inline citations spanning exactly numbers 1–84; Sources contains exactly 84 numbered entries 1–84; **zero undefined inline numbers, zero orphan sources** (re-checked by the lead after the revision; see `experiments/apply-review-fixes.py`).
  - **Numerals:** the reviewer reconciled every numeral in the body against the research notes and local artifacts and re-derived the load-bearing values independently (0.6333/0.5667 at `eval.md:509,517`; `detect()` 4.0 s at `eval.md:581`; 60 cases / 18 constraints / 69 ADRs in `benchmark/gold/`; ICSE 2014 Table 5 cells; SEIP 2015 6-vs-7 / 31-vs-18 / 40-vs-27 / 57%–66%; TSE 2021 median-of-medians reversal; 50.8% / 7,357). All exact. No numeral was changed in review.
  - **Reviewer findings applied:** MAJOR (i) §3.6 header over-applied bucket C → section retitled, each affected row labelled; MAJOR (ii) audit-evidence search-scoped negative had been upgraded to an existence claim → restored to search-scoped phrasing (§2.2 F); MAJOR (iii) Caracciolo et al. venue was **ICSM 2015**, verified via Crossref as **IWESEP 2016** (DOI 10.1109/IWESEP.2016.12) → corrected in §3.6 and source [63]; 17 MINOR applied (bucket definition restated as "one bucket per claim"; the indefensible bucket-A half of the memory-layer anchor dropped; three single-source flags added at point of use; four existence claims restored to search-scoped phrasing; the §3.2 survival-evidence reading marked metric-ambiguous; §4.1 gate scope narrowed; the two distinct five-repo sets disambiguated).
  - **Verification corrections made by the verifier pass:** FLABot DOI (`10.1109/CSMR.2009.39` → `…42`); RoleCast venue (CCS 2011 → OOPSLA/SPLASH 2011); BugLocator authors (Zhou, Lu, Liu → Zhou, Zhang, Lo).
  - **Residual notes (not failures):**
    - The TSE 2021 full text was **not** retrievable directly by the lead (`par.nsf.gov` fetch + `curl` failed; computer.org JS-rendered; Exa 429). It was read as full text inside the T3 researcher stream and the numbers are cited from that read. Recorded in the deliverable §8 (B1) as "flaky for automated use", not dead.
    - The only intervention study found for the anti-pattern families (ICSA 2026 refactoring) had its **numbers blocked** (publisher HTTP 403). This is the single most consequential evidence gap and is disclosed in §3.2 and §7 Q5.
    - The T5 stream's `projectmem` and `enforcement-coverage` evidence is self-reported/grey literature and is labelled as such.
    - Rank cost estimates ("days" vs "2–3 weeks") are researcher judgements, disclosed as such in §2.1.
    - `outputs/.drafts/beyond-compliance-applications-revised.md` is the final candidate; `outputs/beyond-compliance-applications.md` is a byte-identical copy of it.

- **Sources consulted:** the six research notes (below) plus everything cited in them; the two child-stream notes that report coverage counts record 12 `web_search` queries (T1), 13 queries across 6+ angles (T2), 18 logged searches (T3), and 8+ angles with 2 refutation-only (T5).
- **Sources accepted:** **84 numbered sources** in the deliverable + approximately 20 additional verified-but-uncited works listed in §8 + 6 local workspace artifacts.
- **Sources rejected / dead / unverifiable:** 12 entries in the deliverable's **Blocked / unverified URLs** table (B1–B12) — including the ACM DL 403s (RoleCast, CCS 2024 BOLA), the Elsevier 403s, the paywalled Knodel ICSM 2008 body, the `boa.unimib.it` 403s, and two dead/incorrect identifiers. The Exa provider hit HTTP 429 mid-run in two streams and is recorded there as a tool limitation.
- **Plan:** `outputs/.plans/beyond-compliance-applications.md` (+ per-stream briefs `…-T1.md` … `…-T5.md`)
- **Research files used:**
  - `outputs/.drafts/beyond-compliance-applications-research-lead-anchors.md` (lead; ICSE 2014, ICSE-SEIP 2015, WICSA 2015 read in full; WICSA 2016 abstract; ECSA 2019 metadata)
  - `outputs/.drafts/beyond-compliance-applications-research-sweep-apps.md` (T1, 78,176 B)
  - `outputs/.drafts/beyond-compliance-applications-research-bug-localization.md` (T2, 64,270 B)
  - `outputs/.drafts/beyond-compliance-applications-research-antipatterns.md` (T3, 55,750 B)
  - `outputs/.drafts/beyond-compliance-applications-research-security-migration.md` (T4, 57,704 B)
  - `outputs/.drafts/beyond-compliance-applications-research-agent-context-supplychain.md` (T5, 79,403 B)
- **Draft chain:** `-draft.md` → `-cited.md` (verifier) → `-revised.md` (review fixes applied; final candidate)
- **Review artifacts:** `outputs/.drafts/beyond-compliance-applications-verification.md` (338 stated / 408 on disk lines, reviewer pass)
- **Patch script:** `experiments/apply-review-fixes.py` — 31 asserted replacements; every target required exactly one match, so a mis-anchored edit fails loudly rather than silently no-op'ing.

## Child-run receipts

| key | runId | status | artifact | bytes |
|---|---|---|---|---|
| sweep-apps | 6701cf61-e784-4b0f-be74-5b8fbab62703 | completed, ok | `…-research-sweep-apps.md` | 78,176 |
| bug-localization | 07e4bc35-dca1-49d7-9303-1ace1b08cc61 | completed, ok | `…-research-bug-localization.md` | 64,270 |
| antipatterns | 420dff47-d9f0-42f3-b8ee-3852dfe88f6a | completed, ok | `…-research-antipatterns.md` | 55,750 |
| security-migration | 021cd3b1-aa0f-4ca6-a7f7-d7f6403e5040 | completed, ok | `…-research-security-migration.md` | 57,704 |
| agent-context-supplychain | 269a60e0-04d4-4104-bdf8-567bb82bf909 | completed, ok | `…-research-agent-context-supplychain.md` | 79,403 |
| verifier | 247fddff-27d0-4676-9804-74c9e623b781 | completed | `…-cited.md` | 84,820 |
| reviewer | 57b48ca1-6238-44cd-a5ca-e7d7157c9c01 | completed | `…-verification.md` | ~25,300 |

## Notes on integrity

- No number, table, dataset, sample size or ablation in the deliverable is invented. Three of the requester's four candidate claims are corrected rather than confirmed (see §6 correction ledger C1–C9), and the requester's pre-registered suspicion #2 (the anti-pattern asymmetry) is returned as **overstated / mechanism wrong**.
- Every absence is labelled **search-scoped**; the reviewer's one MAJOR finding on this axis (audit evidence) was fixed, and four further existence claims were downgraded.
- Single-author-group results (the Mo/Cai/Kazman anti-pattern gradient, the DRSpace/ArchDebt line) are flagged as single-source wherever they carry weight.
- One load-bearing evidence gap remains open and is disclosed rather than papered over: the ICSA 2026 refactoring-intervention numbers (publisher 403).
