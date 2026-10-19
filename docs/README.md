# Docs

Single home for Shepherd's documentation. Live docs are maintained; `archive/`
holds superseded artifacts kept for provenance.

## Live

| Doc | What |
|---|---|
| `adr/` | Architectural Decision Records (numbered, append-only) |
| `diagrams/` | Pipeline diagrams (`.drawio` + rendered `.png`) |
| `eval.md` | Evaluation methodology: harness, gold provenance, baseline rows |
| `node-search-response-contracts.md` | `node_search` response contracts (ADR 017) |

## Research programme — see `research/README.md`

The programme forked on 2026-10-17/18. The **active** experiment is the security
eval ([#220](https://github.com/Ravicha2/Shepherd/issues/220)), whose working area is
`research-exp-setup/security/`; the longitudinal decision-memory study
([#178](https://github.com/Ravicha2/Shepherd/issues/178)) is **parked** as the
fallback spine. Shepherd's own paths were not moved — issue text, the RFC bundle and
the frozen plan quote them — so each parked doc carries a scope banner. Inside
`research-exp-setup/`, the harness and data did move on 2026-10-19, into that repo's
`superseded/harness/`; its `superseded/README.md` §3 maps every old path.

| Doc | Study | Status |
|---|---|---|
| `research/longitudinal-analysis-plan.md` | longitudinal (#178) | **parked** — frozen analysis plan (#184) |
| `research/longitudinal-replay-census.md` | longitudinal (#178) | **parked** — replay viability + run cost (#179) |
| `research/issue-207-decision-log.md` | longitudinal (#178) | **parked** — dated notes behind plan §5 |
| `research/node_search_lit_review_plan.md` | tool (ADR 017) | delivered |

## Archive — superseded, kept as artifacts

| Doc | Superseded by |
|---|---|
| `archive/issue-35-plan.md`, `archive/issue-35-design.md` | Shipped in issue #35; per-source BFS + REQUIRES semantics |
| `archive/ablation_plan.md` | Executed in issue #131 (search / `list_dependents` on/off); rows of 2026-09-06 in `eval.md` |
| `archive/tool_impact_plan.md` | Executed in issue #140 (the #137-attributed instrument; `list_children` / `list_dependencies` on/off); rows of 2026-09-09 in `eval.md` |

## Not in git

Two untracked roots, both deliberately out of version control:

| Path | Holds |
|---|---|
| `scratch/` (repo root) | merge context, one-off codemods |
| `papers/` (repo root) | paper drafts, their plans and provenance records — these predate the fork and mix both experiments; check a draft's scope before quoting it |

Both are ignored in `.gitignore`; nothing under them is part of a commit.

