# #160: home-assistant cell, and the full-graph vs pruned convention

One cell: `home_assistant_node_on_run1` (node_on, k=1), first HA cell in the
benchmark denominator. Traces (local, #140 convention, gitignored):
`logs/benchmark-arms-160/home_assistant_node_on_run1/resolver_traces.jsonl`.

Run shape (full graph, as the other four repos):

```
cd app
BENCH_REPO=home-assistant BENCH_RUN=1 \
  BENCH_REPORT_DIR=../benchmark/reports/2026-09-17T23-44-54 \
  RESOLVER_TRACE_DIR=../logs/benchmark-arms-160/home_assistant_node_on_run1 \
  PYTHONHASHSEED=0 uv run --extra dev python -m tests.services.adg.test_benchmark_arms_eval
```

## Convention: FULL GRAPH (default)

The pruned staged tree (only the modules each case touches: `remote_rpi_gpio`,
`scrape`, `rest`, `alpha_vantage`, `acomax`, copied from the pin clone) is the
**fallback, not the default**, for two reasons, one measured and one structural.

**Measured: full graph is affordable now.** The census §7 hazard was cost, and
#165 removed it. One HA full-graph `detect()` on an empty diff is 4.0 s
(3.9-4.3 s across runs, `eval.md` #165 row: 79,875 wildcard subject matches
collapse to 0 (ADR-0004) / 7 (ADR-0019) reverse-pass candidates). This cell's
whole detection leg on the full graph, 14 cases over 88,508 nodes, is
**606.1 s** (`cost.detect_seconds`), first case 204.3 s (seed build + pin
baseline) and the rest 27.2-37.3 s each. The pre-#165 projection was ~48.6 min
per `detect()` and ~13 h per cell, which is why HA sat out #149-#158.

**Structural: the pruned tree cannot prove the negative the pin-baseline case
asks for.** `ha-bench-pin-baseline` is a baseline-is-non-zero design: its
expectation is "exactly the 1 standing `remote_rpi_gpio` violation, no other
module fires". A tree holding only five modules can only show the paths inside
those five; the full graph is what shows no other transitive subject fires. The
HA gold's own verification note leaves that confirmation "to the deferred
report-only run"; this cell is that run, for the detection half.

The pruned fallback also breaks cross-repo comparability (four repos measured at
full graph, HA at a 5-module subtree), so it stays a fallback: use it only to
re-check the direct/2-hop case paths when the full graph cannot be run at all,
and say so in the report that quotes it.

## Cell numbers

| quantity | value |
|---|---|
| `cost.parse_seconds` | 145.0 (84,851 parsed nodes / 343,058 edges) |
| `cost.resolve_seconds` | 511.6 (22 ADR sessions, 904,058 prompt / 3,524 completion tokens) |
| `cost.detect_seconds` | 606.1 (14 cases, per-case in the cell JSON) |
| ingestion (gold constraints) | 1 exact / 0 partial / 1 miss, FP 5 |
| detection (violation units) | **17 exact / 0 partial / 4 miss** (21 units) |
| fires | structural 29, merge-mechanism 42, arm-candidates 0 |
| class split | B/C only: 1 matched + 5 FP edges |

The 4 detection misses are one cause, upstream of detection: this run resolved
ADR-0004 to `homeassistant.components.* prohibits_dependency bs4` where gold
holds `selenium`, so the four selenium cases have no edge to fire on. That is
the arm the census deliberately left un-encoded (the Exceptions section
sanctions the generic HTML-parsing integration and `scrape` **is** it:
`scrape/coordinator.py:7` imports `bs4` at module level), i.e. the resolver
picked the FP-prone arm of ADR-0004. ADR-0019 (`gpiozero`) resolved exactly and
all 14 gpiozero/probe/baseline units score exact. Recorded, not patched: the
edge choice is resolver behaviour, and gold does not move to accommodate it.

The HA triage rows do their job: `benchmark/score_scope_triage.py
logs/benchmark-arms-160` now scores HA (`runtime->runtime 2, tooling->tooling 6,
none->runtime 5, none->tooling 1`, `tooling`-recall 6/6) instead of skipping the
repo; the 7 `excluded_tooling_edges` (ADR-0002/0005/0009/0020) are the #159
scope filter's HA bite.
