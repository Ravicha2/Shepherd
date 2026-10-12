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
| `research/longitudinal-replay-census.md` | Replay viability + run cost of the pinned repos (#179) |
| `research/longitudinal-analysis-plan.md` | Frozen analysis plan for the longitudinal study (#184) |
| `research/node_search_lit_review_plan.md` | Lit-review plan feeding the contract above |

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
| `papers/` (repo root) | paper drafts, their plans and provenance records |

Both are ignored in `.gitignore`; nothing under them is part of a commit.

