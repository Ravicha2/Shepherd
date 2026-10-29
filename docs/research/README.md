# Research — status and index

**Status: live index, 2026-10-19.** The COMP9992 programme forked on 2026-10-17/18
(`research-exp-setup/docs/issue-triage-2026-10-17.md` §10):

| Experiment | Status | Issue | Home |
|---|---|---|---|
| Security eval — graph-anchored access-control falsification on BAC-BENCH | **ACTIVE** | [#220](https://github.com/Ravicha2/Shepherd/issues/220) | `research-exp-setup/security/` |
| Longitudinal decision-memory study (compliance durability) | **PARKED** — fallback spine, not running | [#178](https://github.com/Ravicha2/Shepherd/issues/178) | this directory + `research-exp-setup/superseded/harness/records/` |

The security eval does **not** use the durability vocabulary, DVs or artifacts. Its register is
`research-exp-setup/docs/README.md`; start at `research-exp-setup/security/README.md`.

## In this directory

| Doc | Study | Status | What it is |
|---|---|---|---|
| `longitudinal-analysis-plan.md` | longitudinal | **parked** (frozen plan) | the analysis plan: row definition, two tests, note rule, equivalence band |
| `longitudinal-replay-census.md` | longitudinal | **parked** | replay viability and run cost of the pinned 5 (#179) |
| `issue-207-decision-log.md` | longitudinal | **parked** | the 2026-10-10 grill session behind the plan's §5 dated notes |
| `node_search_lit_review_plan.md` | tool | delivered (ADR 017) | lit-review plan for the `node_search` response contracts |
| `issue-259-gate-write-up.md` | security eval (A6) | delivered (#259 closed) | the #249 gate verdict from the #267 record: tandoor limitation, the 14-case attribution, recall arithmetic |

Paths were not moved when the study was parked. Closed issues, the RFC bundle in `lit-rev/`, the
frozen plan and `research-exp-setup/docs/` all quote them; each parked doc carries a scope banner
instead.

**One exception, 2026-10-19.** The harness scripts, their data and their tests moved from the
`research-exp-setup/` root into `research-exp-setup/superseded/harness/`, so a path like
`research-exp-setup/records/events/flowkit.json` quoted below is now
`research-exp-setup/superseded/harness/records/events/flowkit.json`. Frozen docs keep the old
text; the mapping table is `research-exp-setup/superseded/README.md` §3.

## Vocabulary

`CONTEXT.md` at the repo root is the longitudinal study's domain language — *compliance durability*,
*lapse*, *fix*, *treated module*. It is not the tool's glossary and not the security eval's. The
security eval's terms are in `research-exp-setup/security/GLOSSARY.md`; a CPT "violation" (a rule
firing) is not a security "finding" (a hypothesis confirmed by adjudication).
