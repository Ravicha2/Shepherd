# 21. Route Inventory as a Derived View over the ADG

Date: 2026-10-19

## Status

Accepted

## Context

The security pivot experiment (issue #220) needs a deterministic enumeration of a repo's HTTP request
surface — route → handler → module — for three consumers: A3's render-matched context block (the
anchor), the route-coverage DV's denominator, and the structural join from BAC-BENCH's affected
routes to handler modules. The ADG today has modules, imports, classes and functions; the request
surface is a new concept.

Three placements were considered in the 2026-10-19 design grilling:

1. **Persisted ADG nodes** — route nodes + handler edges in Neo4j, queryable via `node_search`,
   participating in CPT detection.
2. **Derived view** — a deterministic module that computes the inventory from the parsed repo and
   the ADG's module/import graph on demand; nothing persisted, no schema change.
3. **Experiment-local script** in `research-exp-setup` — rejected outright: claim 3 says the agent
   is "anchored by the decision graph"; an anchor computed by a script beside the graph would make
   that claim dishonest, and the module mapping would drift from the ADG.

Between 1 and 2: persisting route nodes couples the security experiment to a Neo4j schema migration
and to ADR 013's update strategy before the pivot decision (#219 open questions 1–2) has been made
— a large cost paid for a direction that may not survive. The derived view delivers all three
consumers without touching the graph store; its record schema is the contract if promotion to
persisted nodes is ever wanted.

## Decision

Build the route inventory in `services/adg/` as a derived view:

- One record per route: methods, raw path, canonical path, handler FQN, module, registration kind,
  evidence (file + line).
- Canonical paths strip converter types and parameter names (`<int:user_id>` and `{id}` are both
  one param segment); gold joins are structural — literal segments + param positions — never string
  equality.
- No guard extraction. Decorator stacks, permission classes and middleware are excluded by design:
  guards are the reading agent's work, and claim 3's mechanism stays honest only if the inventory
  stops at the surface.
- Recomputed per pinned SHA; deterministic and byte-identical on reruns.
- No Neo4j schema change; ADR 013's full-rebuild update strategy is untouched.

## Consequences

- The experiment starts without a graph-store migration; the COMP9992 pivot decision is not blocked
  on schema work.
- If the security direction becomes the thesis, promoting routes to persisted nodes is a small
  follow-up; the record schema above is the migration contract.
- `node_search` cannot query routes until that promotion — a product need for graph-native route
  queries is the promotion trigger.
- The inventory does not participate in CPT detection; `requires_dependency` still fires on module
  imports only — correct for A1's claim, which is about the presence-check form.
- Recompute-per-SHA is O(repo size) per case; acceptable at 18 cases.

## Risks

- **Framework coverage is the schedule risk.** Flask/FastAPI decorator enumeration is cheap;
  Django URLconf traversal and DRF router registration are the hard cases (10 of the 18 Python
  benchmark cases). Phase 1 gates buildability and reports gaps rather than working around them —
  per the issue, "if it is not cheap, that is a stop-and-report, not a workaround."
- A derived view can silently diverge from the ADG's module graph if the join keys are not shared.
  Mitigated by computing handler→module from the same FQN machinery the graph uses.