# Longitudinal replay census — the pinned five (issue #179)

Answers [#179](https://github.com/Ravicha2/Shepherd/issues/179): do python-tuf,
flowkit, experimenter, structurizr-python and home-assistant carry enough
ADR-bearing, rename-bearing history to support a **sampled every-N replay** — and
what does a run over each cost. Feeds [#182](https://github.com/Ravicha2/Shepherd/issues/182)
(the affordable sampling rate and cadence) and the per-repo role decision; the
DV menu it serves is [#180](https://github.com/Ravicha2/Shepherd/issues/180).

**Sources.** History: the full local clones under `~/UNSW/research/dataset-Shepherd/`
(`repos/repos.yaml`), queried with status-aware `git log` (`-M --diff-filter=R`
for renames, `--diff-filter=A/M` for ADR arrivals and amendments). Cost: the
recorded benchmark cell cost blocks per [#153](https://github.com/Ravicha2/Shepherd/issues/153) —
`benchmark/reports/2026-09-16T23-56-00/` (four repos, k=1) and
`benchmark/reports/2026-09-17T23-44-54/` (home-assistant, full graph), summarised
in `docs/eval.md` (#160/#165 rows). Pin SHAs are census §5 of
`benchmark/gold/census.md`.

All five clones are at their census §5 pins as of this census.

**Settled scope (2026-10-01).** The replay set is **flowkit, experimenter,
home-assistant**; home-assistant is also the deep case study (sampled denser and
read closely). structurizr-python and python-tuf are **out** of the set — see §4
for why, and the note that python-tuf is nearly free to add back.

---

## 1. History and ADR dynamics

| repo | commits | span | ADR files @HEAD | ADRs arrive | arrival span | ADR window¹ | commits in window | ADRs amended after arrival |
|---|---:|---|---:|---|---|---:|---:|---:|
| python-tuf | 6,708 | 2013-01 → 2026-07 | 10 (+index, template) | each once | 2020-10-26 → 2021-11-24 | 2020-10 → 2026-07 | 2,821 | **0 of 10** |
| flowkit | 13,942 | 2018-10 → 2026-05 | 12 (+README) | 6 in one commit, rest spread | 2019-05-15 → 2022-12-16 | 2019-05 → 2026-05 | 10,303 | **2 of 12** (editorial) |
| experimenter | 8,606 | 2016-10 → 2026-08 | 16 (+template, 2 png) | 8 in one commit, rest spread | 2023-03-15 → 2024-12-12 | 2023-03 → 2026-08 | 5,102 | **1 of 16** (editorial) |
| structurizr-python | 502 | 2020-04 → 2023-01 | 9 | 8 in one commit, 9th +2 mo² | 2020-04-05 | 2020-04 → 2023-01 (dead) | 502 | **0 of 9** |
| home-assistant (core) | 116,224 | 2013-09 → 2026-09 | 0 (none in core) | — | — | 2019-05 → 2026-09 | 96,975 | — |
| home-assistant-architecture³ | 67 | 2018-02 → 2026-07 | 22 | spread | 2019-05-15 → 2024-11-20 | 2019-05 → 2026-07 | 58 commits touch `adr/` | **14 of 22** (40 mod commits) |

¹ ADR window = first ADR arrival → repo end. Violations can only be measured where
a rule exists, so this, not the full history, is the replayable span.
² Structurizr's ADRs land on the repo's first commit (2020-04-05); ADR-0009 arrives
2020-06-09; the directory later moves `docs/adr/` → `docs/development/adr/`
(2020-11-27).
³ HA's ADRs live in the **separate** `home-assistant-architecture` repo; HA core has
no ADR paths at any point in its history (checked). A replay of HA samples core
commits and looks up the ADR set as of each sample's date from the arch repo — a
67-commit lookup table, cheap to build.

### Does the "decisions pivot" premise hold?

The ticket's premise is that a study of evolving decisions needs ADRs that
**change** over history. Across all five repos the honest answer is: **ADRs
arrive once and then sit still.** Every ADR file in every repo was added by a
single commit; the only post-arrival edits are:

| repo | amended ADR | commit | substantive? |
|---|---|---|---|
| flowkit | 0001 (pipenv), 0012 (claims→roles) | link fix; drafting edits within 3 days of creation | **no** — editorial |
| experimenter | 0012 (exposure events) | doc-link fix to a reorganised docs site | **no** — editorial |
| home-assistant | 0004 (webscraping) | `7c50d87` 2021-02-10, "Amend ADR004 to allow extracting forms during the auth phase" | **yes** — a new Exceptions carve-out changes the rule |
| home-assistant | 0019 (GPIO) | spelling/date fix; 2026-04-02 context edit removing Supervised references | **no** — editorial |
| home-assistant | 0002 → 0020 (min Python) | 0020 explicitly supersedes 0002 (2023-05-29) | supersession, but **neither side encodes** as a constraint (interpreter floors; census §7) |

So the whole corpus contains **exactly one substantive amendment to a
constraint-bearing ADR**: HA ADR-0004's 2021 auth-phase exception (the ADR that
yields the `homeassistant.components.*` prohibits-dependency constraint). The one
explicit supersession (HA 0002→0020) is genuine pivoting but lands on a rule the
four-predicate grammar cannot encode, so it produces no measurable violation
change.

**Consequence for the study:** the "decisions pivot" measurement (#180's
supporting number, "how often ADRs are amended or superseded") has almost no
data anywhere, and what exists is one event. It should stay a *background*
number — reported, not leaned on — which is what #180 already decided. The main
DV pair (re-introduction rate, fix duration) does not need pivots to work.

---

## 2. Rename / move pressure

Rename events = `git log -M --diff-filter=R` entries; "in window" restricts to the
ADR window of §1. `.py` counts only Python module renames (what an FQN identity
must survive) — the same measure #181's identity work needs.

| repo | window commits | rename events in window (all files) | `.py` rename events in window | events per 100 commits | `.py` per 100 commits |
|---|---:|---:|---:|---:|---:|
| python-tuf | 2,821 | 71 | 39 | 2.5 | 1.4 |
| flowkit | 10,303 | 285 | 52 | 2.8 | 0.5 |
| experimenter | 5,102 | 535 | 21 | 10.5 | 0.4 |
| structurizr-python | 502 | 73 | 41 | 14.5 | 8.2 |
| home-assistant | 96,975 | 6,686 | 488 | 6.9 | 0.5 |

Every repo carries rename events — enough instances for #181's identity rules to
be exercised and measured, nowhere near enough to dominate the event stream.
Python-module renames specifically are rare (0.4–1.4 per 100 commits) everywhere
except structurizr (8.2, from an early package restructure), which is archived.
Home-assistant has the largest **absolute** count (6,686 events, 488 `.py`) simply
by history size, at a moderate per-commit rate.

**Consequence:** rename handling is a real but thin slice of the replay
everywhere; the panel of four non-HA repos plus HA gives 641 `.py` rename events
in-window in total, a workable population for #181's measurement.

---

## 3. Run cost at the pins

Measured at each pin, single machine, from the recorded cell cost blocks
(`PYTHONHASHSEED=0`; HA on the full graph after
[#165](https://github.com/Ravicha2/Shepherd/issues/165)). `detect` is the
**median per-case** detect seconds in the cell — the steady-state cost of one
`detect()` on that repo's graph; the pin-baseline case (includes seed build) is
excluded as an outlier (HA's max is 204.3 s, all others’ maxima are also the
first case).

| repo | graph nodes / edges | py files @HEAD | parse s | resolve s (ADR sessions) | s per ADR | detect median s/case |
|---|---:|---:|---:|---:|---:|---:|
| python-tuf | 321 / 746 | 49 | 0.9 | 81 (10) | 8.1 | 0.3 |
| flowkit | 2,895 / 7,507 | 577 | 3.8 | 128 (12) | 10.7 | 1.3 |
| experimenter | 3,283 / 10,694 | 713 | 7.1 | 180 (16) | 11.3 | 3.2 |
| structurizr-python | 568 / 1,339 | 128 | 1.2 | 63 (9) | 7.0 | 0.2 |
| home-assistant | 88,508 / 343,058 | 18,607 | 145.0 | 512 (22) | 23.3 | 30.4 |

**Per-sample cost (steady state) = parse + detect** (full rebuild per sample;
see the incremental lever below):

| repo | per-sample s | ≈ |
|---|---:|---:|
| python-tuf | 1.2 | — |
| flowkit | 5.1 | — |
| experimenter | 10.3 | — |
| structurizr-python | 1.4 | — |
| home-assistant | 175 | 2.9 min |

**Resolve is amortised, not per-sample.** The ADR set only changes at arrivals
and amendments, so a replay re-resolves only those (per date, per §1). Totals:
≤ one full resolve for each non-HA repo (81–180 s over the whole replay), and
for HA ≤ 58 arch-repo change events × ~23 s ≈ **≤ 22 min worst case** (realistically
less — only the changed ADRs re-resolve). Resolve never dominates; parse and
detect do.

### Candidate N values

`N` = every-Nth commit; `samples = window commits / N`. Wall-clock = samples ×
per-sample cost (resolve excluded, per above).

| repo | candidate N | samples | calendar gap⁴ | replay wall-clock |
|---|---:|---:|---:|---:|
| flowkit | 100 / 50 / 25 | 103 / 206 / 412 | 6–25 d | 8.8 / 18 / 35 min |
| experimenter | 100 / 50 / 25 | 51 / 102 / 204 | 6–25 d | 8.8 / 18 / 35 min |
| home-assistant | 2000 / 1000 / 500 | 48 / 97 / 194 | 14–55 d | 2.3 / 4.7 / 9.4 h |

⁴ calendar gap = ADR-window span ÷ samples — the input #182 needs to choose
commit-count vs calendar cadence. Every feasible N lands at a ≥6-day gap.

**Ruled out as infeasible.** HA at N≤250 (388 samples ≈ 18.9 h at 175 s/sample;
N=100 ≈ 47 h) is outside a single-run budget. Nothing in the feasible space gives
sub-weekly samples in the long-history repos.

**Set totals** (flowkit + experimenter ≈ 32 min–1.2 h depending on N; HA is the
rest): HA N=2000 → **≈ 4.3 h**; N=1000 → **≈ 6.7 h**; N=500 → **≈ 11.4 h**. One
run each.

**Incremental lever (unpriced).** Per-sample parse is a full ADG rebuild at the
pinned cost; the clone's own size varies over history (early samples cheaper than
the upper-bound pin cost used here). If [#112](https://github.com/Ravicha2/Shepherd/issues/112)'s
file-level incremental rebuild is what #182 selects, HA's per-sample parse drops
from 145 s toward changed-file-proportional and the HA replay approaches
detect-only (~30 s/sample → N=1000 ≈ 48 min). The census cannot price that path
without implementing #112; it is flagged, not assumed.

---

## 4. Settled set and roles

**The replay set is flowkit, experimenter, home-assistant.** Home-assistant is
both a panel member and the deep case study. The other two pinned repos are out.

| repo | ADR-bearing | rename-bearing | pivot-bearing | cost | role |
|---|---|---|---|---|---|
| flowkit | yes — 12 ADRs, 10,303-commit window (6 constraints / 12 units) | light (52 `.py`) | none (2 editorial edits) | cheap (5.1 s) | **in set** |
| experimenter | yes — 16 ADRs, 5,102-commit window (4 constraints / 18 units — richest non-HA surface) | moderate (21 `.py`) | none (1 editorial) | moderate (10.3 s) | **in set** |
| home-assistant | yes — 22 ADRs, 96,975-commit window, largest violation surface (`homeassistant.components.*` = 79,875 subject matches) | heavy (488 `.py`) | **the only repo with any: ADR-0004 substantive amendment; 0002→0020 supersession** | 175 s (100×) | **in set + deep case study** |
| python-tuf (out) | 10 ADRs, 2,821-commit window (4 constraints / 6 units) | light (39) | none | 1.2 s | not in set |
| structurizr-python (out) | 9 ADRs in one commit, 502-commit window, dead since 2023-01 | light (41) | none | 1.4 s | not in set |

**Why these three.** They cover the study's needs without overlap. flowkit is the
long steady one (12 ADRs over 10,303 commits, cheap, clean multi-package layout
so violations have a place to live). experimenter is the richest rule surface of
the non-HA repos (16 ADRs, 18 units) with the most structural churn behind it, so
it exercises the rename/identity side (#181). home-assistant is the only repo
that says anything about decisions changing (ADR-0004's amendment), the only one
with a live violation at the pin, and by far the largest surface — so it is the
natural repo to write about in depth.

**home-assistant is in the set *and* the deep case study.** Map
[#106](https://github.com/Ravicha2/Shepherd/issues/106) made it a run-once
report-only generalization run; the census re-examined that (as the map requires)
and lands on joining instead, because it is the only repo with decision-pivot data
and the largest violation surface. "Deeper" means it is sampled denser than the
other two and its events are read closely — at N=500 (≈9.4 h) HA's story stands
on its own; at N=1000 (≈4.7 h) it illustrates while flowkit and experimenter
carry the pooled number. Cost is bounded to a single overnight run either way.

**Why the other two are out.** structurizr-python has no ADR dynamics and a thin,
finished window (nine ADRs stamped in one commit; dead since 2023-01) — nothing
to replay. python-tuf is nearly free (282 samples in 5.6 min) and was left out for
a tighter three-repo panel; it is the one repo whose constrained code was
wholesale rewritten (the 2022 legacy drop), so it is the obvious add-back if the
first run shows the panel producing too few events. Adding it back costs minutes,
not hours.

---

## 5. Assumptions and caveats

- **Pin cost is an upper bound.** Repos grow; samples before the pin parse
  smaller trees. The candidate-N wall-clocks above are worst-case.
- **`detect` per-sample uses the cell's median per-case seconds** (which include
  the per-case graph prep the arms harness does), not the standalone empty-diff
  `detect()` (HA 4.0 s, #165). Conservative.
- **Resolve amortisation assumes ADR-set-as-of-commit resolution of only the
  changed ADRs** — #182's design choice, not settled. If a replay re-resolves the
  whole ADR set at every sample, add ~one full resolve per sample (HA +512 s →
  ~2× the HA cost). Flagged for #182.
- **HA's split ADR repo.** ADR lookups for HA come from
  `home-assistant-architecture` (67 commits); the ≤22 min worst-case re-resolve
  figure assumes the arch repo's 58 change events are each a small partial resolve.
- **Runtimes are single-threaded wall-clock on this machine**, taken from frozen
  reports — they are planning estimates, not benchmarked throughput.
- The census measures **history supply**, not measurement quality: it does not
  re-derive gold constraints, and it does not model how many violations a repo
  actually exhibits per sample (that is the replay's own output).

---

## Appendix: commands used

```sh
# history span, commits in ADR window (per repo, R = clone path)
git -C $R rev-list --count HEAD
git -C $R rev-list --count HEAD --since=<first-ADR-date>

# ADR arrivals (per ADR file, with dates) and amendments
git -C $R log --diff-filter=A --format='%h %cI' --name-only -- <adr_dir>
git -C $R log --diff-filter=M --format='%h %cI' --name-only -- <adr_dir>

# rename pressure, window-split, .py split
git -C $R log -M --diff-filter=R --name-only --format='C|%cI' | awk '
  /^C\|/ {d=substr($0,3,10); next} NF {ev++; if (d>=SINCE) w++; if ($0 ~ /\.py$/) py++; if ($0 ~ /\.py$/ && d>=SINCE) wpy++}
  END {printf "%d %d %d %d\n", ev, w, py, wpy}'

# run cost: read the recorded cost block per repo
python3 -c "import json;d=json.load(open('<cell>.json'));print(d['cost'])"
```
