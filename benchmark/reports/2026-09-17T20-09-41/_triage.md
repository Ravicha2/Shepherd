# #158 triage accuracy (per-edge verdicts vs the human labels)

## Confusion matrix (rows = ADR label, columns = resolver verdict)

| expected \ observed | runtime | tooling | none |
|---|---|---|---|
| runtime | 26 | 1 | 0 |
| tooling | 34 | 102 | 0 |
| none | 19 | 0 | 0 |

Edges scored: 182  (label mix {'none': 18, 'tooling': 18, 'runtime': 11})

## The two named metrics

- `none`-precision: 0/0 = n/a
- `tooling`-recall: 102/136 = 0.750

## Recall-safety (has-gold runtime edges, enumerated per repo)

A `none`-drop or a tooling demotion is scope-induced and final. A zero-emitted ADR
is only a candidate: the scorer does not read the prior baseline, so an extraction
miss that already existed there is reported here too. Diff against the baseline dir
before calling it a loss.

- **FAILURE** python-tuf ADR-0006: no edge emitted at all
- **FAILURE** structurizr-python ADR-0008: no edge emitted at all

## experimenter ADR-0008 passing-mention trap

- verdicts: ['runtime', 'runtime', 'runtime', 'runtime'], dropped: 0, runtime edge survived: **True**

## Per-repo confusion

- experimenter: {'none->runtime': 8, 'runtime->runtime': 9, 'runtime->tooling': 1, 'tooling->runtime': 16}
- flowkit: {'none->runtime': 6, 'runtime->runtime': 13, 'tooling->runtime': 18, 'tooling->tooling': 72}
- python-tuf: {'none->runtime': 5, 'runtime->runtime': 2, 'tooling->tooling': 4}
- structurizr-python: {'runtime->runtime': 2, 'tooling->tooling': 26}
