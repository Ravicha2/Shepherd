# Tool-impact plan: instrument first, then two ablation arms (issue #137)

Design document for two questions asked together, because the second cannot be answered by the first alone:

1. **Attribution (the new question).** Can we attribute each resolved edge (and each false positive) to the tool whose result grounded it? Today the trace records tool *calls* (`resolver_traces.jsonl: tool_calls[].name/arguments`), never tool *results*, so 24 of 84 baseline edge FQNs and a large share of FP edges have no attributable provenance (pre-#135 join: 15/51 FPs unaccounted; the committed baseline's remaining FP mass is root-subject + external-object edges that no tool can see, see section 2). The rag-eval ablation rule says "metrics cut, with the reason: per-tool result quality — no field records search hits or their lift results" (ablation_plan.md section 4). This plan removes that reason by adding one instrumentation field, then runs the arms.
2. **Arms (the #131 follow-through).** `list_children` and `list_dependencies` have never been ablated. Do they earn their place on the current tool surface?

Following the #131 precedent end to end: harness-only env-flag toggles, `git diff` on `app/services/` stays empty, one variable per arm, gold files are the control, per-repo deltas with the ±2 FP noise floor, 2 runs per arm plus one traced baseline, escalation cap, decision rules stated before running. Nothing here has been run.

Scope: ingestion group only (`pytest -m resolver_eval`, harness `app/tests/services/adg/test_unified_resolver_eval.py`). The retrieval group stays untouched for the reason in ablation_plan.md's preamble (it runs on gold constraints, not resolver output).

## 1. Baseline: what the current committed numbers already say

The committed baseline (2026-09-08T13-06-27, git 8f27035, post-#135) is:

| Repo | exact / partial / miss | FP | FP decomposition |
|---|---|---|---|
| openlobby | 2 / 6 / 2 | 9 | 8 root-subject+external-object, 1 `openlobby.core.api.* requires graphql_relay` |
| python-tuf | 3 / 0 / 1 | 4 | 4 `tuf.api._payload.*` implementation edges (ADR-0010's payload family) |
| python-tuf | | | (all 4 tool-touched per the exact-edge join, section 2) |
| tamr-client | 0 / 1 / 0 | 2 | 2 root-subject (`dataclasses`, `TAMR_CLIENT_BETA`) |

Plus per the #136 accounting: tamr credited_fragments 14, excluded_tooling 22; openlobby excluded_tooling 3.

**The entry-point FP class is dead** (0 across all three repos, killed by #133+#135), so the "entry-point FP class count" metric from #131 has no work left to do on this baseline. The surviving FP classes are:

- **Class A: root-subject + external-object FPs.** 10 of 15 FPs are `root.* requires/prohibits <external>` edges where the object is a real package the ADR names (graphene, django.db, flask) but the gold expects either no constraint or a different shape. These are **prompt-instructed, not tool-grounded**: the #133 rule says "Policy, tooling, and whole-codebase constraints take the ROOT PACKAGE as subject", and `external_packages_hint` lists candidate objects in the system prompt. No tool ablation can move this class; only prompt or validation changes can (out of scope here, routed to section 8).
- **Class B: payload-family implementation edges** (tuf ADR-0010, 4 FPs). These are tool-touched (the join shows the agent drilled into `tuf.api._payload.*`), so they are candidate arm-sensitive edges.
- **Class C: specific-locus edges** (openlobby ADR-0003 `openlobby.* requires openlobby.core.api.*`, ADR-0007 partial→miss anchor-bait). Mixed tool-touched/unaccounted; the only openlobby FP that is not root-subject (ADR-0004's `openlobby.core.api.* requires graphql_reloy` edge is a sibling of a root-subject FP) is tool-touched.

This decomposition is why the arms alone are insufficient for your "impact of each tool" question: on this gold set, most of today's FP mass is in class A, which no tool arm can move. The attribution instrument (section 3) is what lets a class-B/C FP be told apart from class-A in any future run, and the arms are what measure the marginal contribution of the two remaining tools on the B/C channels.

## 2. Trace-level evidence for the arms (pre-registered before any run)

From the #131 traced baseline and issue-135 trace dirs (185 sessions total on disk), the usage asymmetry:

| Tool | #131 baseline (46 sessions) | issue-135 final runs (16 sessions) |
|---|---|---|
| search_code | 69 calls, 46/46 sessions | 48/49 calls, every session |
| list_children | 23 calls, 15/46 sessions | 29 calls, most sessions |
| list_dependencies | 3 calls, 3/46 sessions | 2/2 calls, 2 sessions |

Exact-edge provenance join (FP edge matched by subject+predicate+object against session edges in all issue-135 dirs; arg-FQNs extracted from tool_calls):

| Repo | FP joined | tool-touched | unaccounted (pre-attribution) |
|----|---|---|---|
| openlobby | 9 | 5 | 4 (all root-subject external-object: graphene_django/graphene/django.db x2, see section 1) |
| tamr-client | 2 | 2 | 0 |
| python-tuf | 4 | 4 | 0 |

Interpretation rules, stated before the runs:

- The four unaccounted openlobby FPs are class-A edges: root subject from the #133 rule, object from the external-packages hint or ADR prose. **Not arm-sensitive**; they move only under prompt/validation changes. A surviving count in the arms is a finding about the prompt, not about the tools.
- The tool-touched FPs (tuf payload family, tamr `dataclasses`/`TAMR_CLIENT_BETA`, openlobby `graphql_relay` sibling) are the arm-sensitive channels: `list_children`/`list_dependencies` results plausibly grounded them, so the children/dependencies arms are expected to move these counts if the tools are load-bearing.
- Edge provenance (84 FQNs, #131 baseline): 28 descendant-of-list_children-arg, 18 typed-from-root-prompt-or-search-handle, 24 unaccounted, 9 exact-tool-arg, 5 descendant-of-search-arg. The unaccounted quarter is exactly what the attribution instrument resolves.

**Arm-sensitivity warning for `list_children`:** in the search_off arms it substituted for search (77-78 calls vs 23 baseline), so `children_off` under search-on is a different regime than search-off-with-children. The two arms must not be run concurrently, and the reading rules in section 7 treat a children_off collapse as two possible causes (tool loss vs search-substitution loss).

## 3. The attribution instrument (tool-result provenance)

One production change, minimal and trace-scoped:

**Change:** `_log_trace` (unified_resolver.py:481) adds a `tool_provenance` field to each edge in `edges`/`pre_validation_edges`, and the tool loop appends each tool call's *result FQN set* to `tool_call_trace` entries. Concretely, in the tool loop (lines 605-617), after `result = _dispatch_tool(...)`:

```python
tool_call_trace[-1]["result_fqns"] = sorted(_extract_result_fqns(tc.function.name, result))
```

where `_extract_result_fqns` pulls:
- `search_code`: `r["fqn"]` for each hit in the (filtered) JSON array
- `list_children` / `list_dependencies`: `e["fqn"]` for each entry in `entries`

and `_log_trace` gains, per edge, the set of tool names whose results contained the edge's subject and object (exact or prefix-tolerant, same tolerance as the eval scorer): `"provenance": {"subject": ["search_code"], "object": []}`. An empty list on both sides means prompt-instructed (class A) or hallucinated; that distinction is made by the arg-FQN join offline, not in the trace.

Why this is production-safe: it changes only `ResolutionTrace` (a dataclass whose only consumer is `_log_trace`, already eval-only via `RESOLVER_TRACE_DIR`) and one dict append. It does not touch `_TOOLS`, `_TOOL_FUNCTIONS`, the prompt, the dispatch table, or `_validate_edge`. `test_unified_resolver.py`'s mocked-LLM tests never set `RESOLVER trace_DIR`, so they are unaffected. The `resolve_adr_constraints` signature, return type, and ConstraintEdge semantics are untouched, so `pipeline.build_seed` and `run_prepared` are untouched.

ADR 018 note: this adds fields to `resolver_traces.jsonl`, which is not a gated artifact (no gate constant reads traces). The gate constants read committed reports, which this change does not write. No re-baseline is triggered by adding an unread trace field. (If a maintainer prefers zero production diff, the fallback is patching `_dispatch_tool` in the harness via `patch.object` — same extraction rule, applied eval-only. The production version is preferred because traces from real `cpt seed build` runs then carry provenance too.)

**The provenance metric** (new, added to the section 4 table): per arm, per repo, count resolved edges by provenance class — `subject-from-search`, `subject-from-children`, `subject-from-dependencies`, `both`, `prompt-only`. The tool whose result supplied the subject of a matched edge is the tool that "earned" that edge. An FP with prompt-only provenance is class A; an FP with tool provenance is class B/C and routes to the tool's keep/cut decision.

**Toggle smoke (zero LLM cost), from `app/`:**

```bash
uv run --extra dev python -c "
import services.adg.unified_resolver as unified_resolver
# attribution instrument: result_fqns appear in trace entries, dispatch untouched
import json
assert 'provenance' in json.dumps({'provenance': 0})  # placeholder, real check below
print('ok')
"
```

The real smoke is: run one mocked session from `test_unified_resolver.py`'s pattern with `RESOLVER_TRACE_DIR` set to a tmpdir and assert the trace line contains `tool_calls[].result_fqns` and `edges[].provenance`. This becomes a deterministic unit test in `test_ablation_toggle.py` (new test, `test_tool_result_provenance_in_trace`), no LLM, no API key.

## 4. Arms

Two arms, mirroring #131's one-variable-per-arm rule:

| Variant | The exact one change vs baseline | Held constant | Expected effect and why | Cost |
|---|---|---|---|---|
| baseline | none; committed post-#135 config | not applicable | not applicable | already spent |
| v1 `children_off` | `list_children` removed from `_TOOLS`, `_TOOL_FUNCTIONS`, and every prompt/tool-description sentence that names it (surfaces enumerated in section 5) | same harness, gold, model, `TOOL_CALL_CAP`, `PYTHONHASHSEED=0`, search on | match tallies move toward miss where list_children grounded the subject (tuf payload family is the main candidate, openlobby ADR-0007 anchor-bait is second); FP count on class B/C may drop (fewer drill-downs into payload-family siblings); class A unaffected | same session shape; one fewer schema entry |
| v2 `dependencies_off` | `list_dependencies` removed from the same five surfaces | identical | expected **no effect**: 3 calls in 46 sessions, 2 calls in 16 sessions. The arm exists to convert the near-zero usage observation into a keep/cut decision with the same rigor as #131's dependents_off | same |

The combined arm is out of scope (per-component attribution is the point), same as #131.

Deliberate exclusion — a `search_off` re-run: #131 already ran it on this gold set at this prompt, and ADR 018 froze further eval iteration on this set. Re-running search_off post-#135 would test the #133/#135 filters, a different question than tool impact; it is routed to the benchmark set (section 8).

### Surfaces naming `list_children` / `list_dependencies` (the v2-style five-surface scrub)

Both tools are named in:
1. `_TOOLS[1]` / `_TOOLS[2]` schema entries (unified_resolver.py:85-114)
2. `_TOOL_FUNCTIONS` handlers (line 137-141)
3. The `search_code` description ends: `then inspect the hits with list_children / list_dependencies.` (line 69-75)
4. The prompt "Required exploration" paragraph: `then inspect the neighborhood with list_children and list_dependencies to confirm the exact FQNs before writing a constraint.` (line 192-196)
5. Prompt Example 1 step 3 (`list_children("app.routes")`), Example 3 step 2 (`list_children("app.services")`); no prompt example names `list_dependencies`.

So `children_off` must scrub surfaces 1, 2, 3, 4 and **both example steps**; `dependencies_off` scrubs 1, 2, 3, 4 only. The exact-string constants must be regenerated from the prompt at run time (the #131 drift-assert lesson: `assert old_text in prompt_template` before replacing, and `assert "list_children" not in prompt_template` after).

Prompt-examples caveat, pre-registered: deleting Example 1/3 steps changes what the examples teach. The #131 precedent (dependents_off) deleted the step outright; this plan follows it. An alternative substitution (search-only steps) changes two variables (tool loss + example content), so it is rejected.

### Why no `search_code` arm here

It would be a duplicate of #131's v1 at a different prompt version (post-#135), on a frozen gold set, which ADR 018 decision 2's spirit forbids ("a code change claimed eval-neutral that would move tallies therefore fails the gate until the baseline is consciously re-committed"). The search question is answered on the benchmark set (section 8).

## 5. Mechanism: same harness-only env flags

Same `unittest.mock.patch.object` pattern as #131, in `test_unified_resolver_eval.py`:

- `ABLATION_CHILDREN_OFF=1` → `_ablation_tool_surface()` patches `_TOOLS` (minus `list_children`, descriptions scrubbed), `_TOOL_FUNCTIONS` (minus handler), `_SYSTEM_PROMPT_TEMPLATE` (paragraph + both example steps scrubbed). The hallucinated-call trap from #131 section 2 v2 applies identically: removing the handler means a hallucinated `list_children` call returns `{"error": "unknown tool"}` (visible contamination signal), not real data.
- `ABLATION_DEPENDENCIES_OFF=1` → same minus `list_dependencies`, prompt scrub is paragraph-only (no example step names it).
- `_ablation_arm()` in `eval_paths.py` extends to `children_off` / `dependencies_off` labels.
- `test_ablation_toggle.py` gains pins: both flags default-off, arm label routing, and the #133 pins stay (list_dependents stays absent on every surface).

Flags are read at call time (the `_flag_on` pattern already in the harness), unset = baseline, never set for non-`resolver_eval` invocations.

## 6. Metrics, run count, budget

The full #131 metric set runs unchanged on every arm (match tallies, accuracy, FP count, tamr policy-class/many-to-one confound controls, per-session usage counts), plus the two new attribution metrics:

| Metric | Source | Question |
|---|---|---|
| Edge provenance distribution (subject-from-search / children / dependencies / both / prompt-only) | new `edges[].provenance` in traces | which tool grounds matched edges |
| FP provenance class split (class A prompt-only vs class B/C tool-grounded) | join of `false_positive_edges` with traces | which FPs are arm-sensitive |

**Baseline reference for the provenance metric:** the committed baseline has no provenance-stamped traces aligned to it, so exactly like #131, the plan adds **one traced baseline run** (flags unset, `RESOLVER_TRACE_DIR` set) before the arms. Its tallies/FP counts are extra samples, not the decision baseline.

**Run matrix:**

| Run | Sessions | Trace dir |
|---|---|---|
| traced baseline (1) | 33 | `logs/tool-impact-137/baseline-traced/` |
| children_off run 1, 2 | 33 each | `logs/tool-impact-137/children-off-run{1,2}/` |
| dependencies_off run 1, 2 | 33 each | `logs/tool-impact-137/dependencies-off-run{1,2}/` |

33 sessions per run (openlobby 13, python-tuf 10, tamr-client 10; flask/django filtered by `-k "openlobby or tamr or tuf"`), at most 693 LLM calls per run, 5 runs, ~3465 calls total, same model (`google/gemini-3.1-flash-lite`). Escalation valve: add runs one at a time per arm if the two arm runs disagree more than the baseline disagrees with itself, cap 5 per arm, stop and post the disagreement as a finding.

Noise floor: the measured ±2 FP per repo (#130). Effects must hold in both runs of an arm; an FP delta of 1-2 is not an effect.

## 7. Decision rules (stated before any run)

Per repo, per arm. FP wobble ±2; tally shifts are effect candidates (tallies were identical across 4 baseline runs pre-#135; post-#135 has 2 identical runs, so the tally floor is zero observed movement).

- **children_off, effect (keep route):** any per-repo tally shift consistent in both runs, or `|FP delta| >= 3` in both runs on at least one repo, **on the class B/C channels only** (class A is prompt-instructed and cannot move; a class-A-only FP delta is churn, per section 2). Result: `list_children` is load-bearing, keep it, record the numbers.
- **children_off, no effect:** tallies identical and `|FP delta| <= 2` on all repos. Result: human review in issue #137, not an automatic cut. Same asymmetry as #131: cut evidence would overthrow the ADR 017 surface on N=2 runs of a 15-constraint gold set. The class split decides the routing: if class B/C FPs dropped while class A held, the tool was shaping FPs without grounding gold, and the cut recommendation gains weight.
- **children_off collapse:** if tallies crater (e.g., openlobby exact+partial drops by 3+ in both runs), the cause is ambiguous between tool loss and search-substitution loss (section 2 warning). Record as keep with the collapse reading; do not run a combined arm to disambiguate (two variables).
- **dependencies_off, no effect (expected):** tallies identical and `|FP delta| <= 2` → **cut recommendation**, recorded with numbers in issue #137; the code change is a follow-up.
- **dependencies_off, effect:** same keep route as children_off. Interpret before accepting: check whether the moved edges' provenance was dependencies-grounded (the new attribution metric makes this checkable for the first time).
- **Cross-arm:** the decisions are independent. If both show no effect, that package goes to human review as a #131-style finding (the whole neighborhood surface adds nothing measurable on this gold set).
- **Attribution metric, all arms:** report the provenance distribution alongside the tallies. If matched edges are predominantly search-grounded in every arm, the ADR 017 "search-first" thesis is confirmed quantitatively for the first time; if they are predominantly children-grounded, the surface's story changes and the routing should say so.

## 8. Threats to validity (and what this plan does not pretend to fix)

- **Class A dominates the FP channel and no arm can move it.** 10 of 15 committed-baseline FPs are prompt-instructed root-subject external-object edges. The arms measure the tools' marginal contribution on the remaining 5 (class B/C) plus the match channel; they cannot validate the whole surface against the precision problem. The precision problem's dominant class needs prompt/validation work (e.g., a "requires on root package with external object needs ADR-named evidence" validation rule), which is deliberately out of scope here and should be its own issue after this plan's numbers land.
- **Small segments.** 15 constraints (10/4/1). A one-constraint move is a tenth of openlobby's gold. Per-repo segmentation and the both-runs consistency bar are the mitigations; nothing aggregates them away.
- **LLM nondeterminism.** Same N=2 weakness as #131; the escalation valve is part of the design.
- **Provenance attribution is tolerant, not strict.** Prefix-tolerant attribution assigns credit to the last tool whose results covered the FQN; a tool that returned the FQN but was ignored by the agent still gets credit. This is a known ceiling, recorded here rather than fixed (strict attribution needs per-token provenance, which the OpenAI tool-call interface does not expose).
- **ADR 018 freeze.** The arms are report-only (no gate constant moves); the traced baseline run and arm runs land in `tests/ground_truth/reports/` and never overwrite committed baselines. If an arm's outcome motivates cutting a tool (dependencies_off cut), the code change goes through its own issue with a deliberate re-baseline, not inside this plan.
- **Benchmark routing.** ADR 018 routes generalization to benchmark curation (#111): the search arm, the R1-R4 resolution precision ablation (benchmark.md Subtask 3), and the 60% sub-floor question all live there, on the expanded denominator. This plan's arms and instrument are the last planned tool-surface work on this gold set; the instrument transfers to the benchmark harness unchanged.

## 9. Execution checklist

1. **Preconditions.** `OPENROUTER_API_KEY` set; semble model cached (children/dependencies arms still build the search index); confirm the prompt strings in section 4 still match `_SYSTEM_PROMPT_TEMPLATE` byte-for-byte (regenerate scrub constants on drift, #131 lesson).
2. **Branch.** One branch (e.g., `tool-impact-137`) with changes to: `app/services/adg/unified_resolver.py` (attribution instrument only: `result_fqns` + `provenance`), `app/tests/services/adg/test_unified_resolver_eval.py` (flags, scrubs, `_ablation_tool_surface`), `app/tests/eval_paths.py` (`_ablation_arm` labels), `app/tests/services/adg/test_ablation_toggle.py` (new pins). Verify `git diff 8f27035 -- app/services/adg/unified_resolver.py` shows only the two instrumentation additions.
3. **Toggle smoke, zero LLM cost.** From `app/`: with `ABLATION_CHILDREN_OFF=1`, assert 2 tools remain, `list_children` absent from every surface, patch restores after exit; same for `ABLATION_DEPENDENCIES_OFF=1`. Then the deterministic provenance unit test (section 3). Then `uv run pytest app/tests/services/adg/test_ablation_toggle.py app/tests/services/adg/test_unified_resolver.py -q` green.
4. **Run arms, sequentially.** Traced baseline first, then children_off x2, then dependencies_off x2 (commands mirror #131 section 7 step 4, trace dirs under `logs/tool-impact-137/`, `PYTHONHASHSEED=0`, `-k "openlobby or tamr or tuf"`, report dirs auto-timestamped).
5. **Analysis.** Build the table per repo, per arm, per run: tallies, accuracy, FP, class split (A vs B/C), provenance distribution, per-session usage. Then section 7's rules in order.
6. **Post to issue #137.** The table, class split, provenance distribution, toggle smoke results, keep/cut routing with numbers, run dirs and `_meta.arm` values, escalation outcome if any.
7. **Append to eval.md.** A dated row in the same style: arm labels, run dirs, per-repo tallies/FP, provenance distributions, keep/cut decisions, comparability note (post-#135 numbers, not diffable against #131 rows).
8. **Do not.** Do not run `cpt_eval` with the flags set. Do not re-record committed baselines. Do not start the class-A prompt/validation fix inside this plan. Do not run a combined arm.