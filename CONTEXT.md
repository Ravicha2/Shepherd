# Domain Context

Terms resolved during design sessions. Keep implementation detail out; keep
what a domain expert needs to read the eval history and ADRs.

## Glossary

### File-entry-point FQN
A top-level ADG root segment derived from scaffolding rather than architecture:
single-file entry scripts (`manage`, `noxfile`, `setup`, `conftest`) and
documentation/example trees (`docs`, `examples`). They are ADG root segments
(the root-package list advertises them) but are never valid constraint
subjects — policy and tooling constraints belong to the root package. Named as
a distinct FP class by #128, split into two mechanisms (search-lift vs
list_dependents-surface) by the #131 ablation. See eval.md 2026-09-06 rows.

### Root package
The architectural package root of a repo (`openlobby`, `tamr_client`, `tuf`).
The sanctioned subject for whole-codebase policy/tooling constraints. Not
distinguishable from file-entry-point FQNs at the ADG level (FQNKind has no
PACKAGE kind), which is why grounding is a prompt rule rather than a
deterministic filter.

### Noise floor / effect bar
Run-to-run variance at identical code (#130): match tallies stable, FP within
±2 per repo. A change only counts as an effect if it moves match tallies or
pushes FP past the floor. The floor is the gate; forecast numbers recorded
beside it (anchors) are not gates.

### Anchor
A directional forecast recorded with an eval row ("entry-point FPs should drop
to low single digits"). Distinct from the gate: an anchor may miss while the
change still clears the floor and the ticket still closes honestly.
