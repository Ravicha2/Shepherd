# Evaluation

Two eval groups, both run against gold data in `tests/ground_truth/` (from `app/`):

## Repo provenance

- **Real (defensible gold):** openlobby, python-tuf — actual repositories with their actual ADR sets. Only these count toward gold-set scale and gated thresholds.
- **Synthetic (smoke fixtures):** flask, django — locally authored fixtures (`repos/flask`, `repos/django`) with hand-written ADRs and built-in violation commits (`base: compliant` → `violation`). They give deterministic pipeline smoke signal and deterministic detection cases, but are excluded from every gated denominator and must not be reported as gold-set results.

```bash
# Ingestion eval: ADR -> constraint extraction quality (real LLM, needs OPENROUTER_API_KEY)
uv run --extra dev pytest -m resolver_eval -s

# Retrieval eval: CPT detection against gold constraints + mock diffs (no LLM, no Neo4j)
uv run --extra dev pytest -m cpt_eval -s
```

## Ingestion group (`resolver_eval`)

Harness: `app/tests/services/adg/test_unified_resolver_eval.py`

Scores the unified resolver against `tests/ground_truth/<repo>_ground_truth.json` (human-curated expected constraints per ADR) for all four repos: openlobby, python-tuf (real gold), flask, django (synthetic smoke, see provenance above).

- Gold coverage is complete: every ADR in every eval repo has an entry, including process/style ADRs with zero constraints (notes explain why). Zero-constraint entries exist so that anything the resolver extracts from them is counted as a false positive instead of being silently unmeasured.
- Scoring: each expected constraint is matched against resolved edges by predicate, with subject/object FQN patterns scored exact / partial (ancestor-descendant tolerance) / miss. Accuracy = (exact + 0.5*partial) / total; false positives = resolved edges matched to no expectation.
- Reports: `tests/ground_truth/<repo>_eval_report.json`.

## Retrieval group (`cpt_eval`)

Harness: `app/tests/services/cpt/test_cpt_detect_eval.py`

Scores CPT detect against `tests/ground_truth/cpt_detect_ground_truth.json`: per-repo deterministic mock diffs (append code to real files) with expected violations.

- Constraints come from the ingestion ground truth (gold constraints), so extraction variance never leaks into retrieval scores. No LLM, no Neo4j.
- Each case's `expected_violations` record the correct outcome per the ADRs, not current system behavior:
  - Function/method subjects inherit their enclosing module's module-level edges (#115), so module-import-only dependencies count at module scope. Known remaining misses are recorded in `grading_note` with their cause, e.g. the two flask middleware expectations (auth.py's module-level `require_auth` import satisfies the function-scope requires even though the decorator is not applied, so the endpoints stay unauthenticated per ADR-002).
  - Over-triggers (requires firing on over-broad subjects, e.g. ADR-0002's `openlobby.core.*` -> elasticsearch) are deliberately listed in `grading_note` as false positives rather than expected.
- Scoring matches on (adr_id, predicate, subject, object); matched_fqn is scored exact / partial with the same ancestor tolerance, since module-level dedup can shift which namespace level a violation is reported at.
- Aggregate report: `tests/ground_truth/cpt_detect_eval_report.json`.

## Reference baselines

2026-08-30 (pre-#115): retrieval group flask 8/8 exact, 1 false positive; django 1 exact, 2 miss, 0 false positives; python-tuf 0 expected, 1 false positive; openlobby 1 exact, 4 false positives. The django misses (function-level subjects cannot see module-level imports) and the tuf/openlobby B2 over-triggers motivated #115.

2026-08-31 (post-#115, function scopes see enclosing module's module-level edges): flask 6 exact, 2 miss, 1 false positive (the two misses are the auth.py middleware tradeoff, recorded in grading notes); django 4/4 exact, 0 false positives (settings-assignment gained the same baseline prohibits as the other django cases); python-tuf 0 expected, 0 false positives; openlobby 1 exact, 3 false positives (django satisfied via module import; elasticsearch/django.db over-triggers remain, over-broad subjects).

2026-08-31 (post-#116, chained-call root resolution B3): flask 6 exact, 2 miss, 1 false positive (unchanged); django 4/4 exact, 3 false positives — all one firing repeated across cases: ADR-002 prohibits project.* -> users.models.* at project.urls, because the imported view functions gained correct CALLS edges to users.models.User (User.objects.all/filter now resolve to their root), completing a transitive path the pre-#116 graph could not express. ADR-002 governs direct imports (urls.py imports views only), so this is a documented over-trigger in the same class as the openlobby wildcard-subject FPs, recorded in the gold grading notes rather than treated as a #116 regression; python-tuf 0 expected, 0 false positives; openlobby 1 exact, 3 false positives (unchanged).

Note: flask and django rows are synthetic-fixture results (smoke signal, not gold). On real repos alone the retrieval gold holds only 1 expected violation (openlobby) — real-repo retrieval gold needs authoring before any threshold is meaningful. Both groups are report-only: accuracy is printed and written, never gated. Thresholds can be added later by gating on the aggregate tallies in the report JSONs.

## Curation mode

To inspect raw detection output when adding cases:

```bash
# from app/
uv run --extra dev python -m tests.services.cpt.test_cpt_detect_eval
```

Prints actual violations per case; curate `expected_violations` from that output, then verify each expectation against the ADR semantics (expectations must record correct behavior, not whatever the system currently does).