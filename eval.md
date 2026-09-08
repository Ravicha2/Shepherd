# Evaluation

Two eval groups, both run against gold data in `tests/ground_truth/` (from `app/`):

## Repo provenance

- **Real (defensible gold):** openlobby, python-tuf, tamr-client: actual repositories with their actual ADR sets. Only these count toward gold-set scale and gated thresholds.
- **Synthetic (smoke fixtures):** flask, django: locally authored fixtures (`repos/flask`, `repos/django`) with hand-written ADRs and built-in violation commits (`base: compliant` → `violation`). They give deterministic pipeline smoke signal and deterministic detection cases, but are excluded from every gated denominator and must not be reported as gold-set results.

```bash
# Ingestion eval: ADR -> constraint extraction quality (real LLM, needs OPENROUTER_API_KEY)
PYTHONHASHSEED=0 uv run --extra dev pytest -m resolver_eval -s

# Retrieval eval: CPT detection against gold constraints + mock diffs (no LLM, no Neo4j)
PYTHONHASHSEED=0 uv run --extra dev pytest -m cpt_eval -s
```

## Ingestion group (`resolver_eval`)

Harness: `app/tests/services/adg/test_unified_resolver_eval.py`

Scores the unified resolver against `tests/ground_truth/<repo>_ground_truth.json` (human-curated expected constraints per ADR) for all four repos: openlobby, python-tuf (real gold), flask, django (synthetic smoke, see provenance above).

- Gold coverage is complete: every ADR in every eval repo has an entry, including process/style ADRs with zero constraints (notes explain why). Zero-constraint entries exist so that anything the resolver extracts from them is counted as a false positive instead of being silently unmeasured.
- Scoring: each expected constraint is matched against resolved edges by predicate, with subject/object FQN patterns scored exact / partial (ancestor-descendant tolerance) / miss. Accuracy = (exact + 0.5*partial) / total; false positives = resolved edges matched to no expectation. Since #134, an unmatched edge whose subject sits under an expected row's subject prefix (same predicate, object not a miss) credits that row instead of counting as a false positive (many-to-one consolidation, itemized in `credited_fragments`), and `X.*` / dotted descendants partial-match the bare module `X` on the object side (cpt engine tolerance mirrored). Since #136, edges from tooling/CI ADRs (tagged `ConstraintScope.TOOLING` at resolution from ADR role language, never package names) are excluded from the FP count by declared scope and itemized in `excluded_tooling_edges`; matching stays scope-blind.
- Reports: every run writes `tests/ground_truth/reports/<timestamp>/<repo>_eval_report.json` (never overwritten; `_meta` records the git commit plus the LLM stack versions: semble package, semble model, resolver model id). The top-level `tests/ground_truth/<repo>_eval_report.json` files are the committed baselines, updated only by deliberate re-baselines: diff against a run to see drift.

## Retrieval group (`cpt_eval`)

Harness: `app/tests/services/cpt/test_cpt_detect_eval.py`

Scores CPT detect against `tests/ground_truth/cpt_detect_ground_truth.json`: per-repo deterministic mock diffs (append code to real files) with expected violations.

- Constraints come from the ingestion ground truth (gold constraints), so extraction variance never leaks into retrieval scores. No LLM, no Neo4j.
- Each case's `expected_violations` record the correct outcome per the ADRs, not current system behavior:
  - Function/method subjects inherit their enclosing module's module-level edges (#115), so module-import-only dependencies count at module scope. Known remaining misses are recorded in `grading_note` with their cause, e.g. the two flask middleware expectations (auth.py's module-level `require_auth` import satisfies the function-scope requires even though the decorator is not applied, so the endpoints stay unauthenticated per ADR-002).
  - Over-triggers are deliberately listed in `grading_note` as false positives rather than expected. Post-#125 the openlobby over-broad-subject class is resolved at the gold level (see baselines); the one remaining instance is tamr ADR-0009 `tamr_client.*` firing on non-function modules (`_beta.py`), kept because the ADR's own scope ("all function modules") is not expressible in kind-blind FQN-prefix subjects.
- Scoring matches on (adr_id, predicate, subject, object); matched_fqn is scored exact / partial with the same ancestor tolerance, since module-level dedup can shift which namespace level a violation is reported at.
- Aggregate report: `tests/ground_truth/reports/<timestamp>/cpt_detect_eval_report.json` (same versioning as the ingestion group).

## Reference baselines

Entries are chronological, newest last. Every entry uses the same shape: **Change** (what landed or why the run exists), **Numbers** (per-repo table), **Impact**, **Problems**, **Decision** where applicable, and **Comparability** (whether the row's numbers may be diffed against other rows).

Shorthand: match tallies are exact / partial / miss per expected constraint; FP = false positives; acc = accuracy = (exact + 0.5 * partial) / total. A "cases / expected" pair gives gold-set size, not scores.

Standing notes:

- flask and django rows are synthetic-fixture results (smoke signal, not gold). On real repos alone the retrieval gold holds 20 cases with 13 expected violations (#117); per-repo counts were scaled to constraint density rather than the indicative 20/20/10 in that issue.
- Both groups are report-only: accuracy is printed and written, never gated. Thresholds can be added later by gating on the aggregate tallies in the report JSONs.

### 2026-08-30: pre-#115 retrieval reference

**Numbers**

| repo       | exact | partial | miss | FP |
|------------|-------|---------|------|----|
| flask      | 8     | 0       | 0    | 1  |
| django     | 1     | 0       | 2    | 0  |
| python-tuf | 0 (0 expected) | 0 | 0 | 1 |
| openlobby  | 1     | 0       | 0    | 4  |

**Impact:** motivated #115.

**Problems:** the django misses (function-level subjects cannot see module-level imports) and the tuf/openlobby B2 over-triggers.

### 2026-08-31: post-#115 (function scopes see enclosing module's module-level edges)

**Numbers**

| repo       | exact | partial | miss | FP |
|------------|-------|---------|------|----|
| flask      | 6     | 0       | 2    | 1  |
| django     | 4     | 0       | 0    | 0  |
| python-tuf | 0 (0 expected) | 0 | 0 | 0 |
| openlobby  | 1     | 0       | 0    | 3  |

**Impact:** django 4/4 exact, 0 FP (settings-assignment gained the same baseline prohibits as the other django cases).

**Problems:** the two flask misses are the auth.py middleware tradeoff, recorded in grading notes; openlobby elasticsearch/django.db over-triggers remain (over-broad subjects).

### 2026-08-31: post-#116 (chained-call root resolution B3)

**Numbers**

| repo       | exact | partial | miss | FP | vs prior |
|------------|-------|---------|------|----|----------|
| flask      | 6     | 0       | 2    | 1  | unchanged |
| django     | 4     | 0       | 0    | 3  | FP 0 → 3 |
| python-tuf | 0 (0 expected) | 0 | 0 | 0 | unchanged |
| openlobby  | 1     | 0       | 0    | 3  | unchanged |

**Problems:** the 3 django FPs are all one firing repeated across cases: ADR-002 prohibits `project.*` -> `users.models.*` at project.urls, because the imported view functions gained correct CALLS edges to `users.models.User` (User.objects.all/filter now resolve to their root), completing a transitive path the pre-#116 graph could not express. ADR-002 governs direct imports (urls.py imports views only), so this is a documented over-trigger in the same class as the openlobby wildcard-subject FPs, recorded in the gold grading notes rather than treated as a #116 regression.

### 2026-09-01: post-#117 (real-repo gold expanded 3x)

**Change:** openlobby 10 cases, tamr-client 5, python-tuf 5; tamr-client ingestion GT authored. Real-repo gold = 20 cases, 13 expected violations.

**Numbers (real repos)**

| repo        | exact | partial | miss | FP |
|-------------|-------|---------|------|----|
| openlobby   | 7     | 1       | 0    | 28 |
| tamr-client | 2     | 0       | 0    | 1  |
| python-tuf  | 3     | 0       | 0    | 0  |
| **total**   | 12    | 1       | 0    | 29 |

Synthetic rows unchanged from the committed report: flask 2 exact + 4 partial + 2 miss, 1 FP; django 4 exact, 3 FP. (The 2026-08-31 eval.md note said flask 6 exact; the committed report already showed 2 exact + 4 partial at that point.)

**Problems:** all FPs are documented classes in grading notes:
1. Over-broad wildcard subjects (ADR-0002 `openlobby.core.*` -> elasticsearch, ADR-0010/0012 `openlobby.*` -> django / django.db, ADR-0009 `tamr_client.*` on non-function modules).
2. Class-scope firing: class-level FQNs do not inherit their enclosing module's imports (#115 seeds function/method scopes only), so appended classes fire every requires constraint even when compliant.
3. `from graphene import relay` does not register a `graphene.relay` dependency (ADR-0007 only satisfiable via `from graphene.relay import ...` style).

**Also documented:** supersession holds (ADR-0006 requires flask stays quiet on no-flask changes); TYPE_CHECKING-guarded imports are credited (guard-agnostic walk_imports, aligns with ADR-0009's sanctioned pattern); transitive imports do NOT satisfy requires (tuf.repository.__init__ -> _repository -> tuf.api.metadata fires ADR-0010 correctly); dotted prohibits objects (mysql.connector) report one level above the importing module via CONTAINS traversal (partial match).

### 2026-09-01: E1-E5 edge-case probes (report pinned at PYTHONHASHSEED=0)

**Change:** edge-case probes added; real-repo gold = 25 cases, 14 expected violations.

**Numbers (real repos)**

| repo        | cases / expected | exact | partial | miss | FP |
|-------------|------------------|-------|---------|------|----|
| openlobby   | 12 / 8           | 7     | 1       | 0    | 31 |
| tamr-client | 7 / 3            | 3     | 0       | 0    | 1  |
| python-tuf  | 6 / 3            | 3     | 0       | 0    | 0  |

**Impact (edge-case verdicts):**
- relay via `from graphene import relay` scores clean: the augment pass resolves from-imports against existing EXTERNAL FQNs, so the parse-path blind spot does not manifest.
- ORM access (`User.objects.filter`) does NOT register django.db: openlobby-middleware-orm-access fires 3 FPs (ADR-0012 is the discriminating one; an ORM-resolution fix collapses all three).
- Object-side ancestor matching WORKS: a `from tamr_client._types.dataset import Dataset` runtime import satisfies requires on `tamr_client._types` via `startswith` tolerance (tamr-submodule-types-import scores clean).
- Plain `import tuf.api.metadata` registers the dotted target verbatim (tuf-serialization-dotted-import scores clean).
- Class-scope firing is dual-caused and fragile in both directions (tamr-operation-local-type: the genuine misplaced-type violation fires ONLY because class FQNs do not inherit module imports, so a class-scope seeding fix flips it to a miss; same fragility as tuf-metadata-handrolled-codec, recorded in grading notes).

**Problems (fixed in #122, nondeterminism):** the eval was nondeterministic across processes: `NameResolver.resolve` returned `matches[0]` of a hash-ordered suffix index, so ambiguous bare names (`json` -> external json vs tuf.api.serialization.json; `type` -> 6 candidate FQNs) resolved differently per PYTHONHASHSEED: tuf-repository-stdlib-role-files flipped to 2 misses at seed 1, tamr-exception-local-types lost to_payload at seed 3.

**Decision:** deterministic tie-breaking in `resolve` (exact FQN match > fewest parts > lexical) plus a builtins allowlist (bare builtin names never resolve to repo-internal FQNs); cpt_eval tallies are now identical across PYTHONHASHSEED 0-9. PYTHONHASHSEED=0 stays pinned in the run commands as belt-and-suspenders. Full details in GH #117 comment 5491397425.

### 2026-09-03: post-#126 + #124

**Change:** two fixes landed.
- #126 (prohibits report at the evidence-owning node): when a subject's evidence path descends via CONTAINS, the violation now reports at the source of the first non-CONTAINS edge (the node owning the decisive dependency edge) instead of the containing ancestor; structural prohibits' `location` follows the reported FQN.
- #124 (requires-satisfaction scoping, HITL decision: option (a) uniform seeding): the #115 scope-inheritance rule is now kind-uniform: any nested scope (function, method, class) inherits its enclosing module's module-level edges, implemented by adding CLASS to `_enclosing_module_map`.

**Numbers (real repos)**

| repo        | cases / expected | exact | partial | miss | FP | vs prior |
|-------------|------------------|-------|---------|------|----|----------|
| openlobby   | 12 / 8           | 8     | 0       | 0    | 19 | FP 31 → 19 |
| tamr-client | 7 / 3            | 2     | 0       | 1    | 1  | exact 3 → 2, miss 0 → 1 |
| python-tuf  | 6 / 3            | 2     | 0       | 1    | 0  | exact 3 → 2, miss 0 → 1 |

Synthetic flask/django unchanged.

**Impact:** openlobby-admin-mysql-export scores exact (was the one partial, via #126). Openlobby class-scope FPs collapse (the OpenIdClientSerializer/DeleteReportDraft firings vanish entirely, Ping keeps only the over-broad-subject FPs, via #124).

**Problems:** two genuine violations whose firings depended on the class-scope gap flip to permanent documented misses per the issue's recommendation: tamr-operation-local-type (misplaced frozen dataclass, ADR-0009) and tuf-metadata-handrolled-codec (hand-rolled JSON codec, ADR-0006); grading notes updated, expectations kept (eval.md rule: expectations record correct behavior, not system output).

**Known limitation kept:** satisfaction is import-presence-based, so an imported-but-never-applied dependency still satisfies (the two flask decorator-miss cases stay misses; usage-based satisfaction is the issue 124 option (b) follow-up).

**Remaining FP classes:** over-broad gold subjects (#125, HITL pending) and the ORM/chained-call django.db dead-end (#123, generalized fix recorded in the issue, not yet implemented).

### 2026-09-05: post-#123 ingestion re-baseline

**Numbers (ingestion, deltas)**

| repo      | miss    | FP      | acc          |
|-----------|---------|---------|--------------|
| openlobby | 2 → 3   | 11 → 12 | 0.50 → 0.45  |
| tamr      | (0/0/1) | 23 → 28 |              |

Retrieval group unchanged (cpt report byte-identical post-#123).

**Cause:** external INHERITS anchors baited the resolver: ADR-0007's object flipped graphene→graphql_relay, plus extra `requires graphene_django`/`graphql_relay` edges. Tamr FPs are mixed: some anchor-driven, some LLM prose noise (flake8/black/nox/sphinx on `tamr_unify_client.*`).

**Note:** ingestion FPs are itemized in the reports for triage; the prose-noise class needs prompt rules or #117 curation, see ADR 017.

**Comparability: NON-COMPARABLE.** Every ingestion number in this row is pre-ADR-017; the resolver tool surface changed in #128 (dive/list_modules deleted, search_code + typed neighborhood tools added), so do not diff these against the post-#128 ingestion baseline.

### 2026-09-05: post-#125 (over-broad gold subjects resolved; report pinned at PYTHONHASHSEED=0)

**Decision (HITL criterion recorded on #125):** gold encodes the post-resolution live mandate (what governs the codebase given the full ADR set), not the per-ADR literal extraction target. Concretely:
- ADR-0002 subject narrowed `openlobby.core.*` -> `openlobby.core.search.*` (the "database for all data" clause is content-superseded by ADR-0011's re-scoping; the surviving mandate is Elasticsearch-for-fulltext, same locus as ADR-0011's constraint; the two GT rows are now subject-identical by design and both ADR attributions must fire).
- ADR-0010 `openlobby.* requires django` and ADR-0012 `openlobby.* requires django.db` dropped as non-FQN-checkable (ADR-0003/0005 precedent: framework/DB choice has no FQN-derivable requires subject, and settings.py is compliant without importing django; checkable content survives as the flask prohibition and the models-locus django.db requires).
- Tamr ADR-0009 kept broad (see grading notes).

**Engine fix the narrowing exposed:** `resolve()` dedup had no adr_id in its key, so the subject-identical ADR-0002/ADR-0011 constraints collapsed to one violation attributed by GT file order; adr_id added to the dedup and module-level-dedup keys (regression test pins dual attribution).

**Numbers (retrieval)**

| repo        | exact | partial | miss | FP | vs prior |
|-------------|-------|---------|------|----|----------|
| openlobby   | 8     | 0       | 0    | 0  | FP 19 → 0 |
| tamr-client | 2     | 0       | 1    | 1  | unchanged |
| python-tuf  | 2     | 0       | 1    | 0  | unchanged |
| **real-repo totals** | 12 | 0 | 2 | 1 | FP 20 → 1 |

Synthetic flask/django unchanged.

**Impact:** the #123 ORM/chained-call django.db dead-end is now eval-invisible: its probe was structurally coupled to the dropped broad subject (the surviving `openlobby.core.models.*` subject can never manifest it because models.py imports django.db at module level); the gap stays tracked in #123 and its unit tests, and openlobby-middleware-orm-access is re-graded as a compliant probe (supersession + subject-scoping discrimination).

**Numbers (ingestion openlobby, baseline shift from the GT edits, NOT a resolver regression):** 2 exact / 6 partial / 2 miss / 11 FP (was 5/5/2/10). ADR-0002 is now a permanent documented partial (the resolver is per-ADR and cannot see ADR-0011 when extracting ADR-0002: resolved `openlobby.core.*` vs expected `openlobby.core.search.*`), and the resolver still emits the dropped `requires django` edge (+1 FP) while its broad `openlobby.*` -> `django.db` edge scores partial against the surviving models.* expectation. These rows are the standing measurement of the resolver's over-broad subject extraction (extraction is per-ADR while mandates are corpus-level) and are deliberately kept visible as the documented limitation; closing them means corpus-aware extraction, out of #125's gold-side scope.

**Numbers (same-day ingestion FP capture; the harness now itemizes `false_positive_edges` in every report, since LLM runs do not reproduce):** tamr-client 0 exact / 0 partial / 1 miss / 23 FP (committed baseline was 24: ±1 LLM run variance), identities now recorded in the report. Triage of the 23:
- 14 policy-class: requires edges from tooling ADRs the GT holds as zero-constraint (flake8/black/nox/sphinx-*/mypy/dataclasses/feature-flag, including one bare `*` subject); unaffected by search-grounding (#127).
- 9 grounding-class, all ADR-0009's single mandate fragmented into per-module subjects (`tamr_client.backup.*`, `.dataset.*`, ... -> `tamr_client._types.*`) which jointly embody the gold constraint but score as FPs while the one broad expectation scores miss: a many-to-one scoring gap, not an extraction failure (the fragmentation is arguably more precise than the gold's kind-blind prefix, it excludes `_beta.py` by construction).

**Forecast from this triage (pre-search):** #127 follow-ups should move the openlobby subject-locus partials, leave tamr's 14 policy FPs alone, and leave tamr's 9+1 to a scoring/consolidation fix, not search.

**Comparability: NON-COMPARABLE for ingestion.** The ingestion numbers quoted mid-row (openlobby 2/6/2/11, tamr 23-24 FP) are pre-ADR-017; the resolver tool surface changed in #128, so do not diff them against the post-#128 ingestion baseline. The cpt numbers in this row stay comparable (retrieval group is byte-identical across #128; it runs on gold constraints, not the resolver).

### 2026-09-05: post-#128 (ADR 017 search-first resolver surface re-record; run dir `reports/2026-09-05T22-31-58`)

**Numbers (ingestion, pinned at PYTHONHASHSEED=0)**

| repo      | exact | partial | miss | FP | acc  | vs prior |
|-----------|-------|---------|------|----|------|----------|
| openlobby | 2     | 5       | 3    | 16 | 0.45 | match tallies identical, FP 12 → 16 |
| tamr      | 0     | 0       | 1    | 32 |      | FP 28 → 32 |
| tuf       | 3     | 0       | 1    | 3  |      | unchanged |
| flask     | 1     | 0       | 3    | 1  |      | |
| django    | 3     | 0       | 1    | 3  |      | |

Retrieval group byte-identical (runs on gold constraints; #128 touches the resolver only).

**Impact (FP identity triage):**
1. The #125 forecast held: tamr's 14 policy-class tooling requires and the 9+1 many-to-one scoring gap are unchanged, and openlobby's subject-locus partials did NOT resolve to exact (ADR-0004's subject got broader, `openlobby.core.*` → `openlobby.*`, not narrower).
2. NEW class, search-grounded entry-point subjects: `search_code` lifts snippets from `manage.py`/`setup.py`/`noxfile.py`/`docs/`/`examples/`, and the agent grounds whole-codebase policy constraints on those file-derived roots (`manage.* prohibits javascript`, `noxfile.* requires black`) instead of the package root: openlobby +6 of this class, tamr +9. Remedy candidate is a prompt rule (policy/tooling constraints take the root package as subject, never file-entry-point FQNs).
3. Genuine improvements: openlobby's `requires python` meta-edge and the ADR-0003 views→api prohibit FP are gone; tamr's `TAMR_CLIENT_BETA`/`warnings`/self-prohibit noise edges are gone; tuf subjects got more precise (`tuf.api.*` vs `tuf.api._payload.*`).

**Next (designed, not yet run):** ablation dimension, two arms × the three real repos: search on/off (stub backend returning `[]` vs real backend: isolates whether lift-grounding helps or the neighborhood tools alone suffice) and `list_dependents` on/off (tool omitted from `_TOOLS`: isolates subject-scoping value). Both are one-flag runs of the same harness; run before the next prompt change so its effect isn't confounded. The entry-point class is the named post-data candidate for the next prompt pass.

**Comparability: NON-COMPARABLE post-#133.** The resolver tool surface and prompt changed in #133; do not diff future runs against this row's numbers.

### 2026-09-06: #130 baseline confirmation (versions stamped)

**Change:** the committed ingestion baselines remain the 2026-09-05T22-31-58 run (same resolver code, only harness stamping changed since). Versions now recorded per run in report `_meta` (`app/tests/eval_paths.py`, both eval groups): semble 0.5.6, semble model `minishlab/potion-code-16M-v2` (`SEMBLE_MODEL_NAME` default), resolver LLM `google/gemini-3.1-flash-lite` (`LANGEXTRACT_MODEL_ID` default, OpenRouter).

**Numbers (noise floor, four runs at identical code: 2026-09-05T22-31-58 committed, 22-50-14, 22-53-37, 2026-09-06T09-40-13 stamped):**

| repo      | match tallies | FP wobble |
|-----------|---------------|-----------|
| openlobby | identical (2/5/3) | 16 / 16 / 18 / 16 |
| tamr      | identical (0/0/1) | 32 / 36 / 31 / 32 |
| tuf       | identical (3/0/1) | 3 / 3 / 3 / 4 |
| flask     | identical (1/0/3) | (within ±2) |
| django    | identical (3/0/1) | 3 / 3 / 3 / 2 |

The tuf +1 is subject-locus churn within ADR-0008's mandate (`requires_implementation` re-anchored `tuf.api.*` to a `MetaFile` self-requires), not a new class.

**Decision (effect bar):** any future prompt tweak must move match tallies or FP counts beyond this ±2 floor to count as an effect.

**Comparability: NON-COMPARABLE post-#133.** This floor was measured on pre-#133 code; the 2026-09-07 row is the comparable record for #133's effect, and a fresh floor is needed before judging any later prompt tweak.

### 2026-09-06: issue #131 ablation (search_code / list_dependents on/off)

**Change:** design signed off on the issue before any run; harness-only env-flag toggles (`ABLATION_SEARCH_OFF`, `ABLATION_DEPENDENTS_OFF`) scoped to the resolver_eval loop, `git diff 40b1c9f -- app/services/` empty, `_meta.arm` stamped. Report dirs: 2026-09-06T15-00-27 traced baseline, 15-03-14 + 15-08-47 search_off, 15-14-39 + 15-17-25 dependents_off; the aborted dir 14-58-43 is a killed invocation, one repo only, superseded.

**Numbers, search_off arm (2 runs, content-identical to each other: same tallies, same resolved subjects, same FP identity sets):**

| repo      | exact | partial | miss | FP | acc  | vs baseline |
|-----------|-------|---------|------|----|------|-------------|
| openlobby | 2     | 7       | 1    |    | 0.55 | was 2/5/3, 0.45 |
| tamr      | 0     | 0       | 1    | 15 |      | FP 32 → 15 |
| tuf       | 3     | 0       | 1    | 2  |      | FP 3 → 2 (within floor) |

- ADR-0004 and ADR-0007 miss→partial because with search blind the agent emits the constraints at all (baseline: no predicate-matching edge) with root-fallback subjects `openlobby.*`.
- Tamr FP class deltas: entry-point 12→4, policy-class 21→13, many-to-one fragmentation 10→0 (without snippets the agent stops fragmenting ADR-0009 into per-module requires).
- Deprived of hits the agent retries `search_code` ~2x more (128 calls/33 sessions vs baseline 69 calls/46 logged lines incl. retries).

**Numbers, dependents_off arm (2 runs, tallies stable, FP overlap 31/36 tamr, 10/14 openlobby):**

| repo      | exact | partial | miss | FP      | acc  | vs baseline |
|-----------|-------|---------|------|---------|------|-------------|
| openlobby | 2     | 6       | 2    | 13 / 11 | 0.50 | FP 16 → 13/11 (beyond the ±2 floor, consistent) |
| tamr      |       |         |      | 33 / 34 |      | within floor |
| tuf       |       |         |      | 1 / 2   |      | within floor |

- ADR-0007 miss→partial (subject exact at `openlobby.core.api.*`, object one level shallow `graphene`).
- Openlobby entry-point class 9→4/2. Contamination clean (0 `list_dependents` attempts, scrub asserts green).

**Key finding (usage evidence from the traced baseline):** `list_dependents` was called 0 times in 33 sessions: the tool is never used when available.

**Key finding (class split):** both arms produced effects in the direction of REMOVAL helping, and the entry-point FP class splits by repo: tamr's is search-lift-driven (12→4 with search off, 12/12 with it on), openlobby's is NOT (9→9 with search off) and instead tracks the `list_dependents` surface (9→4/2 with it off). The #128 attribution "search-grounded entry-point subjects" is incomplete: the class has two repo-dependent mechanisms.

**Decision (AC 3):**
- `search_code` kept: the arm's effect is opposite-direction and the plan's asymmetry rationale holds (cut evidence would overturn ADR 017's core on a 15-constraint gold set). The honest finding: search's measured contribution here is output-shaping (FP composition, subject specificity) not gold-matching (no exact gained by removing it anywhere), so the entry-point prompt rule should target both search-lift over-specificity and the root-package list.
- `list_dependents`: cut recommended: 0 baseline usage, and its presence measurably degrades openlobby grounding and its entry-point FP class; the pre-registered "effect→keep" route is overridden by its own interpret clause (the effect direction is anti-value); cut is a follow-up commit pending confirmation on the issue.

**Comparability: report-only, NON-COMPARABLE post-#133.** None of these runs are re-baselines; committed baselines remain the 2026-09-05T22-31-58 run. The arms ran on pre-#133 code (the #133 combined-minus-arm attribution is recorded in the 2026-09-07 row); do not diff future runs against the arm numbers.

### 2026-09-07: issue #133 landed (`list_dependents` cut everywhere + entry-point prompt rule)

**Change:** commits 5bf6fdc/ac99cf6; two fresh `resolver_eval` runs at PYTHONHASHSEED=0, report dirs `2026-09-07T13-51-14` (committed as the new baselines) and `2026-09-07T13-57-06`, trace dirs `logs/issue-133/run1|2`; `_meta.arm` baseline, git ac99cf6. Runs content-identical: same tallies, same FP identity sets, 100% overlap on every repo.

**Numbers (ingestion)**

| repo      | exact | partial | miss | FP | acc  | vs prior |
|-----------|-------|---------|------|----|------|----------|
| openlobby | 2     | 7       | 1    | 19 | 0.55 | was 2/5/3, 0.45, FP 16 |
| tamr      | 0     | 0       | 1    | 23 |      | FP 32 → 23 |
| tuf       | 3     | 0       | 1    | 3  |      | unchanged, within floor |
| flask     | 1     | 0       | 3    | 1  |      | unchanged |
| django    | 2     | 0       | 2    | 4  |      | was 3/0/1, FP 3 |

**Gate (#130 effect bar): PASSED.** Tamr FP −9 beyond the ±2 floor in the intended direction, and openlobby match tallies moved (miss 3→1: ADR-0004 and ADR-0007 miss→partial).

**Anchors vs actuals (2/4 hit):**
- tamr entry-point FPs 12→0: HIT, better than the low-single-digit forecast (the prompt rule eliminated tamr's entire search-lift class: docs/examples/noxfile subjects gone, tooling requires re-rooted to `tamr_client.*`/`tamr_unify_client.*`).
- openlobby ADR-0007 ≥partial: HIT (partial: subject exact `openlobby.core.api.*`, object `graphene` one level shallow of `graphene.relay`).
- openlobby entry-point FPs 9→8: MISS (the class churned rather than shrank: pytest/django/flask grounding at manage/setup eliminated, but black/elasticsearch/javascript re-grounded at the same roots, plus `openlobby.* requires black`, the rule's intended root-package subject, still an FP because gold holds tooling ADRs as zero-constraint).
- openlobby acc >0.55: MISS by a hair (0.55 exactly, ties the search_off arm rather than beating it).

**Honest negatives:**
- Openlobby FP 16→19 (+3 beyond floor, wrong direction): the new edges are the re-rooted policy class (`openlobby.* requires black`, `openlobby.* requires django.db.backends.postgresql`, the `graphql_relay` #123 anchor-bait recurrence, a self-edge `openlobby.* requires openlobby.core.api.*`, over-specific `openlobby.core.api.*` requires).
- Synthetic django lost one exact (`users.services.* requires users.models.*` resolved null, stable across both runs) and gained a duplicate over-broad prohibits FP (manage.*): small but real, beyond the floor in the wrong direction on a 4-constraint gold.

**Attribution (combined minus the #131 dependents_off arm; scrub-equivalence held: landed `_TOOLS` byte-identical to the arm's, prompt differs by one blank line in Example 2, whitespace-only):**
- On tamr the prompt rule did all the work (arm kept entry-point 12/12, combined 0; FP 33/34→23).
- On openlobby the cut took ADR-0007 miss→partial and the prompt rule took the remaining ADR-0004 row miss→partial, but FP rose above even the pre-cut baseline (arm 13/11→19): the rule fixes the wrong-root class, and the zero-constraint-gold policy class absorbs the relocations as new FPs.

**Usage (#121 scaling axis, from traces):** 73/75 tool_calls at 4.56/4.69 per distinct ADR session (search_code 44/45, list_children 25/26, list_dependencies 4), vs the #131 traced baseline's 95 calls at ~6.8 per session (~32% fewer); `list_dependents` absent from every trace in both runs.

**Iteration cap:** not triggered: the floor is cleared on the gate, so the one allowed prompt revision was not spent; the openlobby FP +3 and the django flip are recorded as-is.

**Baseline status:** new committed ingestion baselines = the 2026-09-07T13-51-14 run; retrieval group untouched (resolver_eval writes no cpt report; cpt baselines unchanged and comparable).

### 2026-09-07: issue #134 (scorer-side FP fixes: many-to-one consolidation + object-side ancestor tolerance)

**Change:** harness-only at commit 6ce7d1e, `git diff 6ce7d1e^..6ce7d1e -- app/services/` clean, keyless unit pins in `app/tests/services/adg/test_resolver_eval_scorer.py`; two fresh `resolver_eval` runs at PYTHONHASHSEED=0, report dirs `2026-09-07T21-17-11` (run1, committed as the new baselines) and `2026-09-07T21-19-59`, trace dirs `logs/issue-134/run1|2`, `_meta.arm` baseline, git 6ce7d1e.

**Numbers (ingestion)**

| repo      | exact | partial | miss | FP | acc  | vs prior |
|-----------|-------|---------|------|----|------|----------|
| tamr      | 0     | 1       | 0    | 13 | 0.50 | was 0/0/1, acc 0.00, FP 23 |
| openlobby | 2     | 7       | 1    | 19 | 0.55 | unchanged (run1 FP set identical to the 13-51-14 baseline) |
| tuf       | 3     | 0       | 1    | 3  |      | unchanged |
| flask     | 1     | 0       | 3    | 1  |      | unchanged |
| django    | 2     | 0       | 2    | 4  |      | unchanged |

**Impact (tamr, the exact predicted move):** the 10 ADR-0009 per-module fragments are credited to the broad gold row (identical 10-edge credit set in both runs, itemized in the new `credited_fragments` report field), the broad row goes miss to partial (subject `tamr_client.<mod>.*` is a child of `tamr_client.*`, object `tamr_client._types.*` is a subtree wildcard of `tamr_client._types`), and the remaining 13 FPs are the untouched policy class.

**Run agreement:** match tallies identical on every repo; tamr/tuf/flask/django FP identity sets identical; openlobby differs only by run2 omitting the 3-edge ADR-0013 black trio (`manage.*`/`openlobby.*`/`setup.*` requires black), i.e. resolver omission variance inside the documented policy class. That Δ3 sits just past the stale ±2 pre-#133 floor, which still needs re-measuring (per the #133 row).

**Rules added:**
1. Consolidation: an unmatched resolved edge whose subject is a child of an expected row's subject prefix, same predicate, object not a miss, credits that row (no double counting, the row keeps its own score).
2. Object-side tolerance: `X.*` (subtree wildcard) or a dotted descendant partial-matches the bare module `X` (mirrors the cpt engine's requires-satisfaction tolerance at engine.py), while underscore siblings stay miss (`graphql_relay`/`graphene_django` vs `graphene`: distinct PyPI packages, underscore is not a namespace separator; pinned).

**Known boundary (per the issue):** consolidation never credits a different predicate (guarded, unit-tested), but it cannot detect an expected row adversarially broader than the ADR's mandate; gold prefixes are kind-blind, so ADR-0009's "all function modules" scope would equally credit a `_beta`-module fragment if the resolver emitted one. Accepted, not guarded.

**Comparability: NON-COMPARABLE for earlier ingestion FP counts and tamr match tallies (pre-#134 scorer).** The resolver itself is unchanged since #133, so resolver-output comparisons across the boundary remain valid. New committed ingestion baselines = the 2026-09-07T21-17-11 run; retrieval group untouched by #134 (the session's full-suite run wrote one cpt report at 2026-09-07T21-12-28 without the pinned seed: tallies and violation identities identical to the committed cpt baseline, only `_meta` stamps and one django evidence-path string differ, hash-order path enumeration).

### 2026-09-08: issue #136 (tooling/CI ADR edges classified out of import-graph scope; decision (a), tag-not-skip)

**Change:** commit a15e60a; `ConstraintEdge.scope` (`ConstraintScope.RUNTIME` default, `TOOLING` tag) classified at resolution by `classify_adr_scope` in the unified resolver: one scope per ADR from ROLE language in the ADR text (`lint`, `formatt`, `type[ -]?check`, `docstring`, `doc compilation`, `framework for tests`/`test framework`, `programming language`, `\bci\b`/`continuous integration`), never package names. Keyless pins in `app/tests/services/adg/test_constraint_scope.py`, including the issue's generality test ("adopt ruff for linting" classifies as tooling) and negative calibration (tuf "wire formats", openlobby "writing API documentation" stay runtime). Eval FP accounting order: matched → credited (#134) → tooling-scoped → FP, with tooling exclusions itemized in the new `excluded_tooling_edges` report field (reversible, auditable); matching itself stays scope-blind. Two fresh `resolver_eval` runs at PYTHONHASHSEED=0, report dirs `2026-09-08T10-30-28` (committed as the new baselines) and `2026-09-08T10-33-25`, trace dirs `logs/issue-136/run1|2`, `_meta.arm` baseline, git a15e60a. Earlier same-day dirs 10-13-47/10-20-09/10-23-08 are superseded mid-protocol runs (pre-commit stamps / pre-CI-pattern code), kept as records.

**Numbers (ingestion)**

| repo      | exact | partial | miss | FP | acc  | vs prior |
|-----------|-------|---------|------|----|------|----------|
| tamr      | 0     | 1       | 0    | 1  | 0.50 | FP 13 → 1 |
| openlobby | 2     | 7       | 1    | 10 | 0.55 | FP 19 → 10 |
| tuf       | 3     | 0       | 1    | 3  |      | unchanged |
| flask     | 1     | 0       | 3    | 1  |      | unchanged |
| django    | 2     | 0       | 2    | 4  |      | unchanged |

Match tallies identical to the #134 baseline on every repo; the change is FP-only, as designed.

**Impact:** the tooling/CI FP class is excluded by declared scope, itemized: tamr 12 edges (ADR-0002 flake8/flake8-import-order/black, ADR-0004 sphinx/recommonmark, ADR-0006 mypy over both package roots), openlobby 9 edges (ADR-0005 javascript, ADR-0008 unittest, ADR-0013 black at root/entry-point subjects). Tamr's survivor is ADR-0007's old-name edge (a rename ADR, no tooling signal, outside the tooling scope claim); openlobby's 10 survivors are the entry-point (#135) and subject-granularity classes. #134 credits untouched (tamr 10 fragments still credited; the credit branch runs before the scope branch).

**Run agreement:** match tallies identical on every repo; tuf/flask/django FP, exclusion, and credit identity sets identical. Tamr differs only on ADR-0007's edge choice (run 1 the old-name prohibit, run 2 a `requires tamr_client._beta.check`; FP=1 either way). Openlobby differs only by run 2 omitting the 3-edge ADR-0013 black trio, the same resolver omission variance #134 recorded inside this class (excluded 9 vs 6).

**Variance-exposed classifier gap, fixed mid-protocol:** an intermediate run emitted 4 tamr ADR-0003 edges (`requires nox/poetry`, a reproducibility/CI ADR with no lint/format/type-check language) that stayed FPs; `\bci\b`/`continuous integration` were added to the role pattern (collision scan: only tamr ADR-0004, already tooling via `docstring`) and the final two runs above are on the amended commit.

**Known boundaries:** classification is per-ADR, so a mixed ADR tags wholesale (eval-invisible today: the mistagged ADRs, tuf 0005/tamr 0008-0009, have no FP-class edges and scope-blind matching keeps their gold rows scored); the role list is calibrated to this corpus, and an ADR governing a tool without any role word (as ADR-0003 nearly was) stays runtime. Neo4j persistence of `scope` is not implemented (connector round-trip defaults to RUNTIME); add when deployed output needs the tag.

**Decision (HITL, recorded on the issue):** option (a) with tag-not-skip at comparable effort. Rejecting (c) was the anti-overfitting call: curating the gold toward system output would have hidden the scope disagreement instead of declaring it.

**Comparability: NON-COMPARABLE for earlier ingestion FP counts (pre-#136 scorer scope rule).** The resolver's extraction behavior is unchanged (same prompt, same tools; only tagging was added), so resolved-edge comparisons across the boundary remain valid. New committed ingestion baselines = the 2026-09-08T10-30-28 run; retrieval group untouched (resolver_eval writes no cpt report).

### 2026-09-08: issue #135 (file-entry-point roots filtered from the evidence; entry-point FP class killed)

**Change:** commits b8d2326, e4887e9, 5523cb9, 8f27035. Two evidence surfaces now filter file-entry-point module roots (`manage`, `setup`, `noxfile`, `conftest`): `search_code` results (hits lifted from `setup.py`/`manage.py` never reach the agent) and the prompt's root-packages list. A third fix landed mid-protocol: module-wildcarding could equalize subject and object the LLM kept distinct (`tamr_client.*` requires `tamr_client`), crashing the session on ConstraintEdge's self-loop guard; both reconstruction paths now drop self-loops per-edge (unit-pinned, red-checked). Two fresh final runs at PYTHONHASHSEED=0, report dirs `2026-09-08T13-06-27` (committed as the new baselines) and `2026-09-08T13-10-26`, trace dirs `logs/issue-135/narrowed-run1|2`, `_meta.arm` baseline, git 8f27035.

**Guard narrowing (the pre-registered no-op guard fired):** the first implementation also excluded `docs`/`examples` (the #133 prompt-rule list verbatim). Tamr held (FP 1→1, tallies identical) but tuf breached deterministically: FP 3→6, exact 3→2, identical across both runs at temperature 0, and a 3-trial causal test isolated the cause: tuf's `examples/` holds the reference implementation of the very ADRs being resolved, so hiding those hits starved ADR-0010 (emitted nothing where the baseline resolved the exact edge) and reshaped ADR-0008. `docs`/`examples` have repo-dependent semantics (scaffolding in tamr, substance in tuf), so the exclusion was narrowed to the four roots whose entry-point role is convention-fixed in every Python repo; docs/examples went back to agent judgment on both surfaces (search hits and root list). The narrowed runs restore tuf exactly (tallies identical to baseline, ADR-0010 exact back, FP 4/5 vs 3: within floor).

**Numbers (ingestion)**

| repo      | exact | partial | miss | FP  | acc  | vs prior |
|-----------|-------|---------|------|-----|------|----------|
| openlobby | 2     | 6       | 2    | 9 / 8 | 0.50 | partial 7→6, miss 1→2, FP 10→9/8 |
| tamr      | 0     | 1       | 0    | 2   | 0.50 | FP 1→2 (within/near floor) |
| tuf       | 3     | 0       | 1    | 4 / 5 | 0.75 | unchanged tallies, FP 3→4/5 |
| flask     | 2     | 0       | 2    | 1   | 0.50 | miss 3→2, exact 1→2 |
| django    | 3     | 0       | 1    | 2   | 0.75 | exact 2→3, miss 2→1, FP 4→2 |

**Impact (the class is dead):** zero entry-point-root subjects in any FP edge on any repo (was: openlobby `manage.*`/`setup.*` requires elasticsearch, ADR-0013 black trio at entry-point subjects; django `manage.*` prohibits users.models.* ×2). Django's gone FPs include its whole entry-point class, and its ADR-001 miss became exact (`users.services.*` requires `users.models.*`, stable both runs). Flask's ADR-001 miss became exact too (`app.routes.*` requires `app.services.*`, stable both runs). The re-rooted openlobby policy edges landed where #136's scope rule expected: excluded_tooling shrank 9→3 (the manage/setup-rooted duplicates are gone; only root-package subjects remain, one per tooling ADR), and tamr's excluded set moved 12→22/10 with ADR-0002's tooling requires re-rooted to package roots (subject churn only, all still scope-excluded).

**Honest negatives:**
- Openlobby ADR-0007 partial→miss (both runs): the object flipped `graphene`→`graphene_django` (the #123 anchor-bait class resurfacing under the changed prompt), subject still exact.
- Openlobby match tallies moved partial→miss on ADR-0004 in the six-root run; under narrowing ADR-0004 holds partial while ADR-0007 drops, net partial 7→6.
- Tuf FP +1/+2 (4/5 vs baseline 3): ADR-0008's `prohibits_implementation` fragments on `_payload` classes and run-2's ADR-0006 `MetadataSerializer` edge, subject-locus/omission variance within the documented classes, beyond the stale ±2 floor only on run-2's reading.
- Tamr FP 1→2: ADR-0005's `dataclasses` requires is the old policy class (tooling ADR, but "composable functions" language stays runtime-scope by design); ADR-0007 churned to a `TAMR_CLIENT_BETA` requires. Both are the known zero-constraint-gold policy class absorbing relocations, not new classes.

**Run agreement:** match tallies identical on every repo; FP/exclusion/credit identity sets identical on flask and django; deltas elsewhere are the documented resolver variance classes: openlobby Δ1 (a run-1-only self-referential `openlobby.*` requires `openlobby.core.api.*`), tamr Δ1 subject churn + the ADR-0002 tooling-edge omission (excluded 22 vs 10), tuf Δ1 (run-2's ADR-0006 edge).

**Iteration cap: partially spent.** The six-root implementation consumed the pre-registered narrowing (guard evidence was decisive, not a prompt tweak), so the landed scope is the narrowed four-root list with no further revision; ADR-0007's object flip is recorded as-is.

**Baseline status:** new committed ingestion baselines = the 2026-09-08T13-06-27 run; retrieval group untouched (resolver_eval writes no cpt report).

**Comparability: NON-COMPARABLE for earlier ingestion FP counts and openlobby/flask/django match tallies (pre-#135 resolver evidence surfaces).** The resolver's tool results and prompt root list changed, so resolved-edge comparisons across the boundary are only valid per-class (entry-point subjects: before/after; everything else: variance classes). New committed ingestion baselines = the 2026-09-08T13-06-27 run.

## Curation mode


To inspect raw detection output when adding cases:

```bash
# from app/
PYTHONHASHSEED=0 uv run --extra dev python -m tests.services.cpt.test_cpt_detect_eval
```

Prints actual violations per case; curate `expected_violations` from that output, then verify each expectation against the ADR semantics (expectations must record correct behavior, not whatever the system currently does).
