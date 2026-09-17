# #158 triage accuracy (per-edge verdicts vs the human labels)

## Confusion matrix (rows = ADR label, columns = resolver verdict)

| expected \ observed | runtime | tooling | none |
|---|---|---|---|
| runtime | 13 | 0 | 0 |
| tooling | 17 | 55 | 0 |
| none | 11 | 0 | 0 |

Edges scored: 96  (label mix {'none': 18, 'tooling': 18, 'runtime': 11})

## The two named metrics

- `none`-precision: 0/0 = n/a
- `tooling`-recall: 55/72 = 0.764

## Recall-safety (has-gold runtime edges, enumerated per repo)

A `none`-drop or a tooling demotion is scope-induced and final. A zero-emitted ADR
is only a candidate: the scorer does not read the prior baseline, so an extraction
miss that already existed there is reported here too. Diff against the baseline dir
before calling it a loss.

- **FAILURE** python-tuf ADR-0006: no edge emitted at all
- **FAILURE** structurizr-python ADR-0008: no edge emitted at all

## experimenter ADR-0008 passing-mention trap

- verdicts: ['runtime', 'runtime'], dropped: 0, runtime edge survived: **True**

## Per-repo confusion

- experimenter: {'none->runtime': 4, 'runtime->runtime': 4, 'tooling->runtime': 8}
- flowkit: {'none->runtime': 3, 'runtime->runtime': 7, 'tooling->runtime': 9, 'tooling->tooling': 40}
- python-tuf: {'none->runtime': 4, 'runtime->runtime': 1, 'tooling->tooling': 2}
- structurizr-python: {'runtime->runtime': 1, 'tooling->tooling': 13}
