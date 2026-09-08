# 18. Eval Gate: Frozen-Baseline Ratchet

Date: 2026-09-08

## Status

Accepted (decided on issue #119, comments 5580984652 + 5581072650; supersedes #119's body plan of threshold-setting from a fresh k-run baseline and #110's measure-then-ratchet sequencing)

## Context

#119 asks for actual gates (retrieval gate on CI, ingestion gate on releases). Both eval groups are report-only today. The natural plan was: implement the gate, run a fresh k-run baseline, set ratchet constants a margin below the observed worst run.

Two constraints changed the plan:

1. **The gold set has evolved at least three times** (#117 authoring, #125 narrowing, #136 scope reclassification). Re-running evals now risks re-opening drift, and re-fitting thresholds (or the gold) to the same set risks overfitting: the resolver's remaining misses/FPs are mostly documented limitations, so an aspiring threshold tuned on this set would encode the fit, not generalization.
2. **The 60% exact-of-matched sub-floor** (#107) would be red from day one: the committed baseline measures exact 5 / partial 7 matched = 41.7% blended-heavy. Adopting it as a gate constant now would either block releases indefinitely or tempt gold-side iteration, both worse than deferring it.

The HITL decision: freeze all eval runs (both groups, including deterministic cpt_eval), set the ratchet directly from the committed baselines, and route the generalization question to benchmark curation (#111 route, Su et al. repos) rather than further eval iteration.

## Decisions

### 1. The gate asserts, it does not execute

The gate never runs eval harnesses. It reads the committed baseline reports and asserts the ratchet constants:

- Ingestion: top-level `tests/ground_truth/<repo>_eval_report.json` (real repos: openlobby, python_tuf, tamr_client), aggregate blended (exact + 0.5*partial)/total >= 0.5667 (= (5 + 0.5*7)/15), FP <= 15 (the post-exclusion `false_positives` field, per #136).
- Retrieval: top-level `tests/ground_truth/cpt_detect_eval_report.json`, real-repo keys only, exact + 0.5*partial >= 12.0 (of 14 expected), FP <= 1.

flask/django synthetic rows are excluded from every gate denominator (smoke signal only, per the eval.md provenance section).

### 2. Ratchet semantics under the freeze

The floor moves only by deliberate re-baseline: re-run both groups at PYTHONHASHSEED=0 (ingestion k=2), diff against committed baselines, re-commit reports and constants together, record the row in eval.md (Change / Numbers / Impact / Comparability). A code change claimed eval-neutral that would move tallies therefore fails the gate until the baseline is consciously re-committed: no silent drift, and the freeze makes re-baselining expensive enough to stay rare.

### 3. The 60% sub-floor is not a gate constant

It stays the decided aspiration on #107's books. Measured exact/matched is 41.7%; adopting 60% now would be red from day one, and closing the gap by iterating this gold set is exactly the overfitting risk the freeze exists to avoid. Revisit only with generalization evidence from the benchmark curation, on the expanded denominator.

### 4. k is a caller policy, not gate code

Eval-side ingestion gate: k=2 worst-run (this issue's body) when LLM runs resume. Benchmark release side: k=3 (per #106/#118). The gate mechanism reads whichever run directories it is pointed at.

### 5. Denominators frozen

15 ingestion constraints / 14 retrieval expected violations over 25 real-repo cases (comment 5580984652: the 25-target on both legs is dropped as redundant, retrieval expectations being deduped from ingestion constraints). No curation sprint; wide-CI disclosure stands as the paper limitation.

## Consequences

- CI carries a cheap, deterministic assertion over checked-in JSON; no LLM cost, no Neo4j, no run variance.
- The gate is red only if the committed reports and constants disagree, i.e. someone moved one without the other.
- Thresholds are baseline-frozen, not aspirational; they understate what the system may be capable of and overstate nothing. The honest generalization test is the benchmark set, not this gold set.
- When the freeze lifts: benchmark curation first, then re-baseline, then (only if justified on the expanded denominator) re-tune thresholds including the sub-floor.

## Related

- #119 (gating mechanism; this ADR resolves its threshold and k questions)
- #110 (ratchet mechanics, worst-run gate shape)
- #107 (25-target superseded; sub-floor aspiration retained)
- eval.md (baseline rows and comparability rules; this ADR's constants are the committed 2026-09-08T13-06-27 run)
- #111 (benchmark curation, the next generalization evidence source)