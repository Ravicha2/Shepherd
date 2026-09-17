# 19. LLM Per-Edge Scope Triage Replaces Keyword-Regex Scope Classification

Date: 2026-09-17

## Status

Accepted (decided on issue #156; supersedes the scope-classification mechanism of ADR 011's #136 decision (a) implementation — `classify_adr_scope` / `_TOOLING_ROLE_PATTERN` in `app/services/adg/unified_resolver.py`. ADR 011's node-side `DependencyRole` classification is NOT superseded and stays live.)

## Context

`ConstraintScope` (`RUNTIME` | `TOOLING`) tags whether a constraint belongs on the import graph or in the dev toolchain. Since #136, that tag has been produced by `classify_adr_scope`: a single whole-ADR keyword regex (`_TOOLING_ROLE_PATTERN`), one scope per ADR, applied identically to every edge the resolver emits.

The regex fails in both directions, for different reasons:

1. **Vocabulary blindness (the measured failure).** On the post-#146 benchmark read (`benchmark/reports/2026-09-16T23-56-00/`), flowkit emitted 53/53 edges `runtime` across all 12 ADRs. Its four tooling ADRs (ADR-0001 pipenv, ADR-0002 pytest, ADR-0008/0009/0010 papermill/asciidoctor/prefect) contain none of the regex's calibrated role words — "package and dependency management", "notebook conversion", "workflow engine" are role language the pattern never learned. ~30 tooling edges went untagged and were charged as runtime FPs. This is exactly the generality failure #136's own anti-overfitting comment predicted for package-name tables; a role-word regex is one.
2. **Granularity blindness (the structural failure).** One verdict per ADR cannot represent a mixed ADR. experimenter ADR-0008 carries a runtime gold edge (`nimbus_ui.* prohibits graphene`) and two runtime FPs (`experimenter.* requires graphene/graphene_django`) from the same document; a whole-ADR `tooling` tag would shelter the FPs inside `excluded_tooling_edges` while gold matching (scope-blind) still counted the hit — precision moves dishonestly.

Two corrections to the original #156 framing, verified against the code and corpus during the design interview:

- The regex does NOT currently fail the experimenter ADR-0008 "Jest aside" trap — `"Keep using Jest for the frontend testing frameworks"` does not match `_TOOLING_ROLE_PATTERN` (verified on the ADR text). The trap is prospective: it is the argument against a per-ADR *LLM* verdict (the alternative design), not a failure of the status quo.
- Scope-blind matching means a TOOLING tag never drops a gold unit at ingestion today (`test_constraint_scope.py:101` pins this). Nothing is "lost" by a whole-ADR tag; the damage is FP-sheltering (ingestion) and would be gold-loss only in a future where detect() filters by scope.

## Decision

### 1. Per-edge verdict, same extraction session

The resolver emits a `scope` verdict as one more key in the per-edge JSON it already produces: `{"subject", "predicate", "object", "justification", "scope", ...}`. No second LLM session, no new agent step, no new tools — the verdict is a property of the final answer, decided at formulation time like predicate choice or wildcard granularity. `classify_adr_scope` and `_TOOLING_ROLE_PATTERN` are deleted.

The signal for the verdict is the ADR's **decision role** (what the constraint governs), never package names and never import-graph presence — tooling packages ARE imported (test modules import pytest), so "is it in the graph" is the wrong test.

Self-classification caveat, accepted: the session that judged an edge worth extracting also judges its scope, a bias toward `runtime`. Accepted as a measured risk (issue #158's triage-accuracy confusion matrix is the instrument), not a paid-away cost — the alternative, an independent classification pass, costs a session per ADR for marginal accuracy on a three-way judgment.

### 2. Vocabulary and boundaries

- `runtime` — governs how the shipped/importable code depends on or implements something. Default.
- `tooling` — a real constraint governing the dev toolchain instead of the imported code: linters, formatters, type checkers, doc build tools, test frameworks, package managers, CI, and **language-version / interpreter-support decisions**. The edge is kept and itemized in `excluded_tooling_edges` (eval accounting excludes it; scope-blind matching still lets it satisfy gold).
- `none` — not a dependency or implementation relation at all: process/documentation conventions, business policy or thresholds, naming conventions, configuration values, data-model redesigns. Emits no edge.

Language-version → `tooling` is the counterintuitive call: tuf ADR-0001's gold rows (`tuf.* prohibits python2.7/3.5`) are language-version prohibitions. `ConstraintScope`'s own docstring already declares language choice as tooling (`models.py:33`), and scope-blind matching keeps the gold rows scored — so the divergence (tooling-tagged edge satisfying gold) is accepted and pinned by test.

### 3. `none` drops at parse, with trace residue; missing/invalid key defaults `runtime`

A `none` edge never materializes as a `ConstraintEdge` — dropped in `_parse_edges`. But dropped edges are recorded in the resolution trace (`none_verdict_edges`, alongside `pre_validation_edges`): a wrong `none` silently deletes a real constraint, the worst failure mode, and must be auditable by #158's confusion matrix.

An edge with a missing or invalid `scope` key defaults to `runtime`. This fails loud: an untagged edge stays in FP accounting (charged, never sheltered), matches the `ConstraintEdge` dataclass default so legacy constructor sites keep working, and blocks the dishonest direction — a prompt regression that drops the key cannot lower the FP count by silently parking edges in `excluded_tooling_edges`.

### 4. Scope stays an accounting concept; enforcement filtering is deliberately deferred

Detect() and the CPT engine remain scope-blind — unchanged behavior, carried over. Tooling edges still fire violations (flowkit ADR-0010: 118 detect fires in the committed post-#146 report) until issue #159 (engine-side TOOLING filter) lands; #159 is sequenced before #158's k-runs so the eval's detection leg carries no phantom fires.

### 5. What transfers out of the deleted classifier

- The calibration tests' **intentions** move to #157 corpus pins: generality (an unseen toolchain — "adopt ruff for linting" — must triage via role language, now a property of the prompt instruction, which uses role nouns only) and the Jest-aside negative calibration (the experimenter ADR-0008 per-edge recall-safety pin).
- The eval-accounting pin (`test_constraint_scope.py:101`: scope-blind matching + itemized `excluded_tooling_edges`) survives unchanged — it pins the scoring seam, not the classifier.

## Consequences

- Mixed ADRs triage correctly per edge: the runtime gold edge survives ADR-0008's tooling aside; its class-A FPs stay charged.
- Vocabulary generality: an unseen toolchain with role language ("adopt X for the notebook build") tags `tooling` where the regex could not learn a new role word without a code change.
- The only tooling detector is now the LLM. A prompt regression fails loud (untagged edges become counted FPs), never silent — but #158 must measure triage accuracy (confusion matrix, `none`-precision, `tooling`-recall) before the verdict is trusted as a replacement.
- Legacy reproduction risk: the regex currently excludes openlobby ADR-0005 (`javascript`) and ADR-0008 (`pytest`, `unittest`) edges; the verdict must reproduce those tags or they return as loud FPs, and the ADR-018 gate reads red until #158's re-baseline records the movement.
- Determinism is lost by design: the regex was deterministic but wrong on this corpus (53/53 runtime on flowkit); the verdict varies but is judged. k≥2 worst-run protocol (ADR 018 decision 4) is the variance discipline.
- Prompt surface grows ~180 tokens (`## Scope verdict` section, role nouns, no tool names, no copyable literals — the #146 Rule 3 lesson).

## Test / recall-safety strategy (issue #157)

Two layers: #157 pins plumbing with recorded zero-LLM session fixtures over all 46 benchmark ADRs (scope key → `ConstraintEdge.scope` → trace → accounting; all three verdicts + missing-key default; fixture-level recall-safety). #158 measures live triage accuracy, k≥2.

Recall-safety enumeration — six has-gold ADRs brush tooling language (verified against the ADR texts), not the four the issue named:

| ADR | Tooling language | Required verdict |
|---|---|---|
| experimenter ADR-0008 | "Keep using Jest for the frontend testing frameworks" | gold edge stays `runtime` (the named trap) |
| experimenter ADR-0010 | "Refactor test cases using serializers" | gold edges stay `runtime` |
| python_tuf ADR-0010 | "in python-tuf tests is an in-memory implementation" | gold edge stays `runtime` |
| structurizr ADR-0008 | "Our unit tests" | gold edge stays `runtime` |
| python_tuf ADR-0001 | language-version Decision | gold edges tagged `tooling` **and still match gold** (scope-blind pin) |
| flowkit ADR-0004 | "# Quart as HTTP Framework" | stays `runtime` — the reverse trap: framework language, runtime verdict |

## Related

- #156 (design issue; the interview record and decision log)
- #157 (implementation: verdict + corpus pin), #158 (eval: re-baseline + triage accuracy), #159 (engine-side TOOLING filter, sequenced before #158's k-runs)
- ADR 011 (node-side `DependencyRole` classification stays; this ADR supersedes only the edge-scope mechanism), ADR 018 (eval gate; #158 re-commits baselines), #136 (tag-not-skip, scope-blind matching)

## Landed implementation (issue #157)

Per-edge verdict shipped as designed: `_parse_edges` reads the `scope` key (`runtime`|`tooling`|`none`), `none` drops with `none_verdict_edges` trace residue, missing/invalid defaults loud to `runtime`, `classify_adr_scope`/`_TOOLING_ROLE_PATTERN` deleted, and the `## Scope verdict` prompt section added after `## Mandate, not mention`. One real recorded session per benchmark ADR is committed at `benchmark/scope_fixtures/<repo>.json` (47 ADRs; captured by `record_scope_corpus.py`) and replayed zero-LLM by `test_scope_corpus.py`.

**Layer-1 result (one run, plumbing + recall-safety):** all recorded edges carry a scope; `none` never materializes; no recall-safety ADR receives a `none` verdict; the tuf ADR-0001 language-version gold rows tag `tooling` and still match (scope-blind). `benchmark/scope_fixtures/TRIAGE_REPORT.json` records triage quality as data: **8/13** #157 named expectations matched on this single run.

**Honest quality gap, deferred to #158 (k>=2) by design:** the one committed run returns `runtime` for flowkit ADR-0008/0009/0010 (papermill/nbconvert/prefect) and ADR-0011/0012 (redaction policy, claims/roles) where #157 expected `tooling`/`none`. Two causes, both Layer-2 material: (a) #157's named list calls workflow-engine and notebook-execution decisions "tooling", which sits outside this ADR's dev-toolchain vocabulary (decision 2 names linters, formatters, type checkers, doc build, test frameworks, package managers, CI, language-version) and the verdict followed decision 2; (b) flowkit's gold notes say ADR-0008/0009/0010 should emit no edges (AutoFlow is an absent component, ungroundable subject) — the run grounded `flowmachine.*` instead, a subject-grounding miss, not a scope-classification one. Layer 1 pins plumbing and recall-safety; the triage-accuracy gate is #158's confusion matrix, as decision "Test / recall-safety strategy" states.