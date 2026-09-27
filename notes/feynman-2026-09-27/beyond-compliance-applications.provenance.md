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
