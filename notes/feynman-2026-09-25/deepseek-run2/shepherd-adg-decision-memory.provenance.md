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
