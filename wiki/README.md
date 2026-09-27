# Shepherd — research wiki

## Start here

**[→ Next steps — recommendation](next-steps.md)** — what to do next and why, the
order to do it in, and what to skip. One page.

Everything else is supporting material. The [research brief](research-brief.md) is the
evidence and the argument; the Feynman runs and the node-search contracts are the
sources behind it.

## The two literature reviews

| | what it covers | when | pages |
|---|---|---|---|
| **New** | What to build beyond compliance checking: ranked extension scenarios, the memory-not-linter reframe, the author-side experiment, retroactive violation checking, generalising the graph | 2026-09-25 → 2026-09-27 | [Research brief](research-brief.md) · [Run 3](feynman-run3.md) |
| **Old** | Node/symbol-search response contracts — LSP, ctags/universal-ctags/tree-sitter, SWE-agent & Aider; the pass that designed the `node_search` resolver tool | 2026-09-10 | [Contracts](node-search-contracts.md) · [Plan](node-search-plan.md) |

The two are independent. The old one is a narrow, closed design pass (issue #141);
the new one is the broad research direction.

## Pages

### New review — [Research brief](research-brief.md)

The main deliverable. Section index:

- [TL;DR](research-brief.md#tldr) — 8 items, start here
- [§1 What the pivot gets right](research-brief.md#1-what-the-pivot-gets-right-and-the-one-way-it-can-go-wrong)
- [§2 The evidence base](research-brief.md#2-the-evidence-base) — the negative results, the one positive result, history mining + SZZ, Python benchmarks
- [§3 The real ceiling: convertibility](research-brief.md#3-the-real-ceiling-convertibility-not-capability)
- [§4 Ranked extension scenarios](research-brief.md#4-ranked-extension-scenarios) — **the memory-not-linter reframe and the experiment live here**
- [§5 Specific bugs Shepherd can catch](research-brief.md#5-specific-bugs-shepherd-can-catch)
- [§6 Case-study design](research-brief.md#6-case-study-design-from-the-feynman-runs-rq4)
- [§7 Retroactive violation checking](research-brief.md#7-retroactive-violation-checking-what-the-current-model-supports)
- [§8 Generalising the graph](research-brief.md#8-generalising-the-graph-beyond-the-four-predicates)
- [§9 Caveats](research-brief.md#9-caveats)
- [§10 What I would do next](research-brief.md#10-what-i-would-do-next-smallest-useful-steps)

### New review — evidence base

- **[Feynman run 1](feynman-run1.md)** — first deep-research pass, RQ1–RQ4, `[T1]`–`[T4]`
  source keys resolved to numbered citations.
- **[Feynman run 2](feynman-run2.md)** — second pass, on `deepseek-v4.1-flash:cloud`.
  Its §6 citation-correction log and §7 fragility analysis are the authority for the
  brief's §7–§9 — where they disagree, run 2 wins.
- **[Feynman run 3](feynman-run3.md)** — third pass (2026-09-27), scoped to
  **beyond-compliance applications**: the ranked application space, the two settlements,
  and a correction ledger (C1–C9) that overrides specific claims in the brief — where they
  disagree, run 3 wins. Its §3.7 also carries the finding that forces a length-matched
  placebo arm into the author-side experiment.
- **[Provenance](feynman-provenance.md)** — model, prompts, dates and the verification
  log for the runs, concatenated.

### Old review — [Contracts](node-search-contracts.md)

- **[Node/symbol-search response contracts](node-search-contracts.md)** — the canonical
  artifact: ranking rules, response caps, kind labelling, signature policy, drawn from
  three tool families.
- **[The plan and its ledger](node-search-plan.md)** — objective, extraction axes,
  deliverables, and the outcome record including the UNVERIFIED register.

## Not here

Eval and benchmark material is deliberately out of scope. These stay in the repo:

- `eval.md`, `ablation_plan.md`, `tool_impact_plan.md` — evaluation and ablation design
- `benchmark/` — test instances, commit set, census, arm reports
- `tests/ground_truth/` — gold data and provenance

## Regenerating

Every page except [next-steps.md](next-steps.md) is a **copy** of a file elsewhere in the
repo, so it can drift. `next-steps.md` is the one original page — it lives here, and
summarises the brief rather than duplicating it. To re-copy the rest from the repo root,
keeping each page's existing source stamp:

```sh
while read -r page src; do
  { sed -n '1,3p' "wiki/$page"; echo; cat "$src"; } > /tmp/wikipage && mv /tmp/wikipage "wiki/$page"
done <<'MAP'
research-brief.md notes/extension-scenarios.md
feynman-run1.md notes/feynman-2026-09-25/arch-decision-memory-scenarios.md
feynman-run2.md notes/feynman-2026-09-25/deepseek-run2/shepherd-adg-decision-memory.md
node-search-contracts.md docs/node-search-response-contracts.md
node-search-plan.md notes/node_search_lit_review_plan.md
feynman-run3.md notes/feynman-2026-09-27/beyond-compliance-applications.md
MAP
```

The stamp carries the commit each copy was taken at; re-running after an edit to a
source doc is the whole maintenance story.
