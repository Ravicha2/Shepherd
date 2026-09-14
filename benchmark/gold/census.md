# Census — benchmark gold set curation (issue #138)

Analysis-only working document for the ADRLinter benchmark gold set. Per-repo ADR
census, candidate constraints, scoring-unit tallies, natural ADR-ADR conflicts,
commit pins, python-tuf eval-overlap flags, and the eq-runner triage verdict.

**Constraint grammar (only these four predicates, per the CPT engine):**
`prohibits_dependency`, `requires_dependency`, `requires_implementation`,
`prohibits_implementation` — dependency/implementation edges between FQN
patterns only. Code style, process, governance, deployment, docs-tooling
decisions are NOT code-inferable and emit no edges.

**Gold format convention** (from `tests/ground_truth/python_tuf_ground_truth.json`
and `flask_ground_truth.json`): each ADR entry is
`{adr_id, adr_path, constraints: [{subject, predicate, object, justification}], note}`;
zero-constraint ADRs carry an explicit one-line note and empty constraints.
Subjects/objects are FQN patterns with `*` wildcards.

---

## 1. Per-repo census tables

### 1.1 python-tuf @ 6889cfbffbb90a17930fbdedf12ae050be775fe3 (2026-07-14)

ADRs at `docs/adr/` (0000–0010, no 0007 — numbering skips it; `index.md` and
`template.md` are not ADRs). **This repo is also in the frozen eval set; see
§6 for eval-overlap flags.**

| ADR | Title | Code-inferable? | # constraints | pin status | evidence |
|-----|-------|-----------------|--------------:|------------|----------|
| 0000 | Use Markdown Architectural Decision Records | No | 0 | comply (n/a) | — |
| 0001 | Default to Python 3.6 or newer | Yes | 2 | COMPLY | `tuf/` (no `python2.7`/`python3.5` deps; only `sys.version_info >= (3, 11)` guard in `tuf/api/_payload.py:71`) |
| 0002 | Pre-1.0 deprecation strategy | No | 0 | comply (n/a) | — |
| 0003 | Where to develop TUF 1.0.0 | No | 0 | comply (n/a) | — |
| 0004 | Extent of OOP in metadata model | No | 0 | comply (n/a) | — |
| 0005 | Use Google Python style guide | No | 0 | comply (n/a) | — |
| 0006 | Where to implement model serialization | Yes | 1 | COMPLY | `tuf/api/metadata.py:72,158,267,294` (`from tuf.api.serialization import ...`) |
| 0008 | Accept unrecognised fields | No | 0 | comply (n/a) | — |
| 0009 | What is a reference implementation | No | 0 | comply (n/a) | — |
| 0010 | Repository library design | Yes | 1 | COMPLY | `tuf/repository/_repository.py:15` (`from tuf.api.metadata import ...`) |

**Total: 4 constraints, 0 violations at pin (HEAD is compliant).**

#### ADR-0006 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `tuf.api.metadata.*` | requires_dependency | `tuf.api.serialization.*` | "Serialization is implemented independently of the metadata class as described in (3)"; the metadata class keeps only dict-conversion helpers ("Compromise 2"), so wire-format (de)serialization lives in `tuf.api.serialization` and metadata classes depend on it, not the other way around. | COMPLY (eval gold has this constraint; see §6) | `tuf/api/metadata.py:72` (`from tuf.api.serialization import ...`) |

#### ADR-0010 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `tuf.repository.*` | requires_dependency | `tuf.api.metadata.*` | "Metadata API makes modifying metadata far easier than legacy code base"; the decision title itself: "Repository library design built on top of Metadata API" — the repository library depends on the Metadata API. Note (per eval gold): do NOT emit requires_implementation for `tuf.repository._repository.Repository`; "built on top of" is a dependency, and Repository-as-ABC is extendable by choice. | COMPLY | `tuf/repository/_repository.py:15` |

#### ADR-0001 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `tuf.*` | prohibits_dependency | `python2.7` | "Chosen option: 'Support only Python 3.6+' ... Python 2.7 is end-of-life" — no tuf module may depend on Python 2.7 runtime features. | COMPLY | `tuf/` — no EOL-python guards anywhere at pin |
| `tuf.*` | prohibits_dependency | `python3.5` | "Python 3.5 is end-of-life" under the same 'Support only Python 3.6+' decision. | COMPLY | `tuf/` — no EOL-python guards anywhere at pin |

#### Zero-constraint ADR notes (for the gold author)

- **ADR-0000**: Documentation-process ADR (adopt MADR format); governs how decisions are written, not code structure. Emit no edges.
- **ADR-0002**: Release/support-process ADR (best-effort support for pre-1.0 bugs); governance commitment, not a code constraint. Emit no edges.
- **ADR-0003**: Process/location ADR (develop 1.0.0 in a subdirectory); development-process decision, not enforceable. Emit no edges.
- **ADR-0004**: Data-representation choice (custom classes vs dicts inside the metadata model); not a dependency/implementation edge between FQNs, and "may be extended with self-validation" is optional. Emit no edges.
- **ADR-0005**: Code-style ADR (Google style guide); naming/formatting not expressible as FQN edges; linter-config suggestion explicitly optional. Emit no edges.
- **ADR-0008**: Runtime-behavior ADR (preserve unrecognized fields on load); deserialization behavior inside the metadata API, not a dependency/implementation relation. Emit no edges.
- **ADR-0009**: Vision ADR (reference implementation is exemplary); design philosophy with no checkable code-level constraint. Emit no edges.

#### python-tuf alternate commits (benchmark instances can be pinned here)

| SHA | date | reason |
|-----|------|--------|
| `a2794c2f36513375d0d85ce7034f59c2bb10c95e` | 2022-01-26 | "Drop legacy implementation" — at `a2794c2f^`, `tuf/repository_tool.py` + `tuf/repository_lib.py` (~7000 lines, 58 securesystemslib imports, `import json` for wire format) violate ADR-0010's rationale head-on. A pre-drop pin (e.g. parent of `eb67b09c`) yields legacy-vs-ADR-0010 tension; the drop commit itself demonstrates the ADR being enacted. |
| `499f1c858ea315be578087bbb189b46e9504ecfc` | 2021-03-04 | "Adopt serialization sub-package in metadata API" — immediately before ADR-0006 was even written (`164074db`, 2021-03-18); at `499f1c85^` (=`4a22b4a5`), `tuf/api/metadata.py` has no `tuf.api.serialization` dependency (factory comments only) while `tuf/api/serialization/json.py` already exists — a clean instance-disjoint "metadata classes not yet depending on serialization package" snapshot. |
| `5e17617fc5c2b9295fa9731e92e082e0329b3a36` | 2022-11-28 | "Add repository module" — introduces `tuf/repository/__init__.py` + `_repository.py`; the `__init__.py` at this commit (and at the eval pin) imports only `tuf.repository._repository`, making it the discriminating counterpart for ADR-0010's requires (transitive path does not satisfy). New benchmark violation code appended here would be instance-disjoint from the eval pin's cases. |
| `22b2726413f7cde2361bd701ac6b9bc21ee7bfcb` | 2024-02-21 | "Metadata API: move inner classes to internal module" — large refactor of `tuf/api/metadata.py` right before the pin window; a good "refactor under constraint" pin for generating violations against ADR-0006 while `__init__.py`-of-repository remains unconstrained. |

Eval-overlap rule for the annotator: the eval gold's *instances* are diff-injected
cases at the eval pin (`tuf-metadata-handrolled-codec`, `tuf-repository-stdlib-role-files`,
plus zero-expectation probes). Any benchmark instance must be a **different code
location / different diff** — ideally pinned at one of the alternate commits above.

---

### 1.2 flowkit @ 24d88247d57987fe33f6b8915540d7bf09b58033 (2026-05-28)

ADRs at `docs/source/developer/adr/` (0001–0012 + README).

| ADR | Title | Code-inferable? | # constraints | pin status | evidence |
|-----|-------|-----------------|--------------:|------------|----------|
| 0001 | Pipenv for package/dependency management | No | 0 | comply (n/a) | — |
| 0002 | Pytest for testing | No | 0 | comply (n/a) | — |
| 0003 | HTTP API as Single Access Point | Yes | 2 | COMPLY | `flowapi/flowapi/` (no `flowmachine` import: `grep -rln "import flowmachine" flowapi/` → empty); `flowclient/` likewise imports only httpx/pandas (`flowclient/flowclient/client.py:8-10`) |
| 0004 | Quart as HTTP Framework | Yes | 1 | COMPLY | `flowapi/flowapi/main.py` (Quart app), `flowapi/flowapi/jwt_auth_callbacks.py:12` (`from quart import ...`), `flowapi/flowapi/geography.py:5` (`from quart import Blueprint ...`) |
| 0005 | IPC — zeromq and redis | Yes | 2 | COMPLY | `flowapi/flowapi/main.py:14-15` (zmq), `flowmachine/flowmachine/core/query_state.py:17` (`from redis import StrictRedis`), `flowmachine/flowmachine/core/cache.py` (redis) |
| 0006 | JWTs for API Access Control | Yes | 1 | COMPLY | `flowapi/flowapi/main.py:23,135` (`JWTManager(app)`); `@jwt_required` on all query endpoints (`flowapi/flowapi/query_endpoints.py:17,120,220`, `geography.py:12`, `qa_endpoints.py:10,80,193`) |
| 0007 | Mapbox GL for map visualisations | No | 0 | comply (n/a) | — |
| 0008 | Jupyter notebooks for AutoFlow | No | 0 | comply (n/a) | — |
| 0009 | Asciidoctor PDF for notebook→PDF | No | 0 | comply (n/a) | — |
| 0010 | Prefect for AutoFlow workflows | No | 0 | comply (n/a) | — |
| 0011 | Redaction strategy for labelled aggregates | No | 0 | comply (n/a) | — |
| 0012 | Claims→roles/scopes permission rework | No | 0 | comply (n/a) | — |

**Total: 6 constraints, 0 violations at pin (HEAD is compliant).**

#### ADR-0003 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `flowclient.*` | requires_dependency | `flowapi.*` (HTTP only) | "there is a _single_ copy of the library responsible for constructing and running queries, accessed through a language neutral HTTP API" — clients reach the backend only through the HTTP API. NOTE: "through HTTP" is a transport semantics, only weakly expressible; the checkable edge is *no direct backend-library import*. | COMPLY | `flowclient/flowclient/client.py:8` (httpx, no flowmachine import anywhere in `flowclient/`) |
| `flowapi.*` | prohibits_dependency | `flowmachine.*` | Same ADR: the API wraps FlowMachine ("FlowMachine will be wrapped by an HTTP API") — the wrapper layer must not import the wrapped library directly; they communicate over zmq (ADR-0005). | COMPLY | `grep -rln "import flowmachine" flowapi/` → empty |

*Conservatism note:* the `flowapi prohibits flowmachine` edge is defensible from
"FlowMachine will be wrapped by an HTTP API" + ADR-0005's zmq IPC decision; an
annotator wanting a stricter reading may emit only the `flowclient requires flowapi`
edge. The engine checks imports, and flowapi's only flowmachine mention is a
config hostname string (`flowapi/flowapi/config.py:54`), not an import.

#### ADR-0004 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `flowapi.*` | requires_dependency | `quart` | "The FlowKit API will make use of the Quart framework." | COMPLY | `flowapi/flowapi/main.py` (Quart app), `flowapi/flowapi/jwt_auth_callbacks.py:12` (`from quart import current_app, request, Response`), `flowapi/flowapi/geography.py:5` |

#### ADR-0005 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `flowapi.*` | requires_dependency | `zmq` | "API-backend communication will be via zeromq" | COMPLY | `flowapi/flowapi/main.py:14` (`import zmq`) |
| `flowmachine.*` (core/server + core) | requires_dependency | `redis` | "IPC in the backend will be mediated by redis" | COMPLY | `flowmachine/flowmachine/core/query_state.py:17` (`from redis import StrictRedis`), `flowmachine/flowmachine/core/cache.py` |

#### ADR-0006 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `flowapi.*` | requires_dependency | `quart_jwt_extended` (JWT machinery) | "API authentication and access control will use JWTs." | COMPLY | `flowapi/flowapi/main.py:23,135`; `@jwt_required` decorators on every protected endpoint |

#### Zero-constraint ADR notes

- **ADR-0001**: Tooling-choice ADR (pipenv vs pip vs conda); package-manager workflow, not an FQN edge. Emit no edges.
- **ADR-0002**: Testing-framework choice (pytest); a dev-process/tooling decision. Emit no edges.
- **ADR-0007**: Notebook-visualisation library choice for worked examples (Mapbox vs Folium vs GeoViews); affects docs notebooks only, not architecture edges. Emit no edges.
- **ADR-0008**: AutoFlow notebook-execution choice (Jupyter + Papermill); `autoflow/` does not exist at this pin and the decision targets an external tool deployment. Emit no edges.
- **ADR-0009**: Notebook→PDF conversion tooling (nbconvert + Asciidoctor PDF); build tooling, not a code relation. Emit no edges.
- **ADR-0010**: Workflow-engine choice for AutoFlow (Prefect vs Airflow); no `prefect` or `airflow` import anywhere in the Python packages at this pin (flowetl uses Airflow, but ADR-0010 governs AutoFlow, which is absent). Emit no edges.
- **ADR-0011**: Redaction policy (drop aggregation zones with any disaggregation < 15); runtime numeric policy implemented in `flowmachine/flowmachine/features/location/redacted_labelled_spatial_aggregate.py:31` (`redaction_threshold: int = 15`) — a business rule, not a dependency/implementation edge. Emit no edges.
- **ADR-0012**: Permissions-model rework (claims→roles/scopes); auth-domain data-model redesign spanning flowauth DB schema and JWT contents — not FQN-expressible. Emit no edges.

#### flowkit violation-potential note

All six constraints COMPLY at the pin. Violations for the benchmark must be
*injected diffs* (e.g. `flowclient` module importing `flowmachine` directly →
fires both ADR-0003 edges; a `flowapi` module importing `flowmachine` → fires
ADR-0003 prohibition; a new flowapi endpoint without `quart_jwt_extended` → fires
ADR-0006 requires). The repo's multi-package layout (`flowapi`, `flowclient`,
`flowmachine`, `flowauth`, `flowetl`) makes subject scoping clean.

---

### 1.3 mozilla-experimenter @ d61a2b8efcb7fd77a849c9f9dc163130473b7f16 (2026-08-31)

ADRs at `docs/adrs/` (0001–0016 + `template.md`).

| ADR | Title | Code-inferable? | # constraints | pin status | evidence |
|-----|-------|-----------------|--------------:|------------|----------|
| 0001 | Build Nimbus console in Experimenter | No | 0 | comply (n/a) | — |
| 0002 | Nimbus front-end directory tree + React/CRA/Bootstrap/GQL | No | 0 | n/a | — |
| 0003 | Analysis visualization architecture | Yes | 1 | COMPLY | `experimenter/experimenter/jetstream/client.py:59` (`load_data_from_gcs`), `experimenter/pyproject.toml:39` (`google-cloud-storage`) |
| 0004 | Monitoring data import | No | 0 | comply (n/a) | — |
| 0005 | Doc Hub — Docusaurus + GH Pages | No | 0 | comply (n/a) | — |
| 0006 | Doc Hub repo location | No | 0 | comply (n/a) | — |
| 0007 | Doc Hub URL | No | 0 | comply (n/a) | — |
| 0008 | Front-end web development with HTMX | Yes | 2 | COMPLY | `experimenter/experimenter/nimbus_ui/forms.py:1988-1997` (`htmx_attrs`), `experimenter/experimenter/nimbus_ui/static/js/*.js` (htmx); no graphene dep in `experimenter/pyproject.toml` |
| 0009 | Nimbus Web SDK architecture (Rust cargo features) | No | 0 | comply (n/a) | — |
| 0010 | Jetstream/Nimbus shared schema | Yes | 2 | COMPLY | `schemas/mozilla_nimbus_schemas/jetstream/*.py` (`from pydantic import BaseModel`); `experimenter/experimenter/jetstream/client.py:15,23` (`from mozilla_nimbus_schemas.jetstream import ...`, `from pydantic import ValidationError`) |
| 0011 | Nimbus Web Glean application structure | No | 0 | comply (n/a) | — |
| 0012 | Exposure events and coenrolling features | No | 0 | comply (n/a) | — |
| 0013 | Guardrail metric versioning | No | 0 | comply (n/a) | — |
| 0014 | Desktop randomization unit normandy_id→group_id | No | 0 | comply (n/a) | — |
| 0015 | QA-only mode for web apps | No | 0 | comply (n/a) | — |
| 0016 | CI workflow for external Firefox changes | No | 0 | comply (n/a) | — |

**Total: 4 constraints, 0 violations at pin (HEAD is compliant).**

#### ADR-0003 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `experimenter.jetstream.*` | requires_dependency | `google.cloud.storage` (GCS) | "The visualization front end fetches data via a Django REST API, which fetches Jetstream data on demand using GCS dependencies. Data is not stored in the database." (chosen option 2). | COMPLY | `experimenter/experimenter/jetstream/client.py:59` (`load_data_from_gcs`); `google-cloud-storage` in `experimenter/pyproject.toml:39` |
| `experimenter.jetstream.*` | prohibits_dependency | `experimenter.experiments.models` (DB write path) | Same option-2 sentence: "It does not require storing the data to the Django database." — the Jetstream-fetch layer must not persist analysis data via the Django models. | COMPLY | `experimenter/experimenter/jetstream/client.py` imports no `experimenter.experiments` module (only `jetstream.models`, the local Pydantic layer, at lines 25-27) |

*Conservatism note:* the prohibits edge is the more debatable of the two — it
encodes "Data is not stored in the database". A stricter annotator may drop it
and keep only the GCS requires. `jetstream/tasks.py` does use
`experimenter.experiments.models` (sizing/monitoring), so the subject may need
narrowing to the `client.py` fetch path (e.g. subject `experimenter.jetstream.client*`)
if the annotator keeps it.

#### ADR-0008 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `experimenter.nimbus_ui.*` (new HTMX pages) | requires_dependency | `htmx` (django-htmx / hx-* attributes) | "we have decided to choose the option - Designing new pages with HTMX ... All web pages using HTMX!" — new server-rendered pages depend on HTMX. | COMPLY | `experimenter/experimenter/nimbus_ui/forms.py:1988` (`htmx_attrs = {...hx-...}`); `django-htmx` in `experimenter/pyproject.toml` |
| `experimenter.nimbus_ui.*` (new HTMX pages) | prohibits_dependency | `graphene` / GraphQL API layer | "using GraphQL significantly hinders the performance ... The main benefit of choosing option 2 is that it can co-exist with React/GraphQL" + "No API's call needed" — new HTMX pages bypass the GraphQL stack. | COMPLY | no `graphene`/`graphql` dependency remains in `experimenter/pyproject.toml`; `grep -rln graphene experimenter/experimenter/` → empty |

*Conservatism note:* the htmx requires is attribute/template-based; a static
analysis that only sees imports can check the `django_htmx`/htmx module
dependency, not raw `hx-` attributes. The annotator may encode the subject
narrowly (the `nimbus_ui.new` page modules) or accept the known-miss semantics.
The GraphQL prohibition is cleanly checkable (no graphene import anywhere).

#### ADR-0010 candidate constraints

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `experimenter.jetstream.*` (ingest) | requires_dependency | `mozilla_nimbus_schemas.*` (pydantic schemas) | "define the schema using Pydantic, and put this definition in the experimenter repository ... one schema definition shared between Experimenter and Jetstream would allow for validation of outputs from Jetstream while removing the need for Experimenter to make assumptions" | COMPLY | `experimenter/experimenter/jetstream/client.py:15,23` (`from mozilla_nimbus_schemas.jetstream import ...`, `from pydantic import ValidationError`); `schemas/mozilla_nimbus_schemas/jetstream/metadata.py:5` (`from pydantic import BaseModel`) |
| `schemas.mozilla_nimbus_schemas.*` | requires_dependency | `pydantic` | "Option 1: Pydantic ... Create schema definitions using Pydantic" — the shared schema package is defined with pydantic models. | COMPLY | `schemas/mozilla_nimbus_schemas/jetstream/analysis_errors.py:6`, `metadata.py:5` etc. |

#### Zero-constraint ADR notes

- **ADR-0001**: Strategy ADR (build Nimbus inside Experimenter vs new app); portfolio decision, no FQN edge. Emit no edges.
- **ADR-0002**: Front-end directory tree + React/CRA/Bootstrap/GQL stack choice; JS-side layout/tooling, not Python FQN edges. Emit no edges.
- **ADR-0004**: Monitoring-data sourcing (on-demand query vs ETL bucket vs Grafana embed); data-pipeline strategy with cost tradeoffs, no enforceable import/inheritance edge ("would be ideal to implement option (2) immediately ... continuing work on option (4)" — explicitly transitional). Emit no edges.
- **ADR-0005 / 0006 / 0007**: Docs-hub tooling, repo location, and URL; documentation-infrastructure decisions. Emit no edges.
- **ADR-0009**: Rust crate organization (cargo features, one library); outside the Python codebase entirely. Emit no edges.
- **ADR-0011**: Glean app-ID granularity (per product domain); telemetry-identity decision. Emit no edges.
- **ADR-0012**: Exposure-event attribution via feature-JSON `experiment` property; client-side messaging behavior. Emit no edges.
- **ADR-0013**: Metric versioning convention (`_v#` suffixes); data-definition naming policy. Emit no edges.
- **ADR-0014**: Randomization-unit change (normandy_id→group_id); client telemetry semantics. Emit no edges.
- **ADR-0015**: QA-preview workflow for web apps; QA process. Emit no edges.
- **ADR-0016**: CI workflow JIT-testing strategy; CI process. Emit no edges.

#### experimenter violation-potential note

All four constraints COMPLY at the pin. The GraphQL one is attractive for
injected violations precisely because the graphene stack is *gone* — any
`import graphene` anywhere in `experimenter.*` is a blatant ADR-0008/0002
backslide. Good injected-diff shapes: `jetstream/client.py` writing
`NimbusExperiment` rows (ADR-0003 DB-prohibition); a new HTMX view importing
graphene; `schemas/` module defining a schema without pydantic
(ADR-0010 requires pydantic).

Historical pinning option: at `a2de3aeb` (2023-06-09, "add jetstream/analysis
schemas") the `client.py` still parses Jetstream JSON *by hand* (`import json`,
no `mozilla_nimbus_schemas` import) — an ADR-0010 requires-violation snapshot
taken weeks *before* the fix commit `b6d9aebc` (2023-06-23, "validate incoming
jetstream schemas"). That (ADR-0010, requires mozilla_nimbus_schemas) violation
instance is real, historical, and instance-disjoint from anything at HEAD.

---

### 1.4 eq-questionnaire-runner @ da90adfdc4390c0fd1d33dbc896adc38d6ca2022 (2026-08-26)

ADRs at `doc/architecture/decisions/` (0001–0010 + PNGs; `0006-question-flow.png`,
`0009-*.png` are images, not ADRs).

| ADR | Title | Code-inferable? | # constraints | pin status | evidence |
|-----|-------|-----------------|--------------:|------------|----------|
| 0001 | Record architecture decisions | No | 0 | comply (n/a) | — |
| 0002 | Refactor functional tests into surveys/components/features | No | 0 | comply (n/a) | — |
| 0003 | Authoring schema variants (manifests+blocks, YAML) | No | 0 | comply (n/a) | — |
| 0004 | Use kid to identify key pair | Yes (weak) | 0–1 | COMPLY | `app/authentication/authenticator.py:185` (`sdc.crypto.decrypter.decrypt` selects key by kid inside the library); `app/services/supplementary_data.py:8,114` (`sdc.crypto.jwe_helper.JWEHelper.decrypt`) |
| 0005 | Simplify URLs (block ids as root) | No | 0 | comply (n/a) | — |
| 0006 | Named lists first-class construct | No | 0 | comply (n/a) | — |
| 0007 | Relationships | No | 0 | comply (n/a) | — |
| 0008 | Lookups | No | 0 | comply (n/a) | — |
| 0009 | Primary person | No | 0 | comply (n/a) | — |
| 0010 | Cookies | Yes (weak) | 1 | VIOLATE (mild, 2 spots) | `app/routes/session.py:124` (`cookie_session["expires_in"] = ...`), `app/routes/session.py:59-62` (`set_schema_context_in_cookie` writes `theme` from `schema.json`) |

**Total: 1–2 constraints (0 solid), 1–2 mild violations at pin.**

#### ADR-0010 candidate constraint

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `app.*` (session/cookie layer) | prohibits_dependency | `schema.json` session properties (`theme`, `survey_title`, `expires_in`) | "Store `schema_name` or `schema_url` in the cookie and remove schema properties i.e. `theme`, `survey_title` and `expires_in`." | **VIOLATE** | `app/routes/session.py:59-62` still writes `theme` from `schema.json` into the cookie; `app/routes/session.py:124` still writes `expires_in` from `get_session_timeout_in_seconds(g.schema)` (a schema-derived value, contradicting "remove ... `expires_in`") |

*Conservatism note:* this is a *data-content* prohibition ("do not store these
properties in the cookie"), not a dependency/implementation edge between FQNs.
It can be forced into the grammar as a prohibits_dependency on the schema-data
module, but that is a semantic stretch for a static import/call checker — the
annotator would have to encode "writes schema property X into cookie_session"
which the CPT graph does not model. Treated as **0 encodable constraints** for
scoring; noted here because it is the one ADR with genuine HEAD-vs-ADR tension.

#### ADR-0004 candidate constraint (weak)

| subject | predicate | object | justification (ADR sentence) | status | evidence |
|---|---|---|---|---|---|
| `app.*` (crypto call sites) | requires_dependency | `sdc.crypto` (kid-aware keystore) | "We will use the kid value in the header of the JWE and JWT tokens to identify the key that was used" — key selection must go through the kid-aware sdc-crypto keystore rather than local crypto code. | COMPLY | `app/authentication/authenticator.py:10,185` (`from sdc.crypto.decrypter import decrypt`), `app/views/handlers/submission.py:6,58` (`sdc.crypto.encrypter.encrypt`), `app/services/supplementary_data.py:8` (`JWEHelper`) |

*Conservatism note:* the kid-selection itself happens inside `sdc-crypto`; a
static checker sees only "app calls sdc.crypto", which encodes the migration
decision, not the kid header contract. Historical violations existed (see
alternate commits below) but at HEAD this is compliant and the constraint is
low-value. Counted as **0–1 borderline**; not recommended for the gold set.

#### Zero-constraint ADR notes

- **ADR-0001**: Meta-ADR (adopt Nygard-style ADRs). Emit no edges.
- **ADR-0002**: Test-organization ADR (JS spec folder layout); test-structure decision. Emit no edges.
- **ADR-0003**: Build-time schema generation from YAML manifests; authoring-pipeline decision ("No impact on survey runner code"). Emit no edges.
- **ADR-0005**: URL-shape ADR (block ids as root paths); routing design expressed in Flask route *patterns*, not dependency edges. Emit no edges.
- **ADR-0006**: Schema/store data-model ADR (ListCollector block type, list store shape); data representation, no FQN edge. Emit no edges.
- **ADR-0007**: Relationships feature design (URL shape + answer store shape). Emit no edges.
- **ADR-0008**: Lookup answer type + external REST service; schema/UI feature. Emit no edges.
- **ADR-0009**: Primary person store attribute + PrimaryPersonCollector block type; feature design. Emit no edges.

#### eq-runner alternate commits (only viable violation material)

| SHA | date | reason |
|-----|------|--------|
| `f4803f946f9d020fa1e5865b5cc77cfcba2bad2f` | 2017-09-29 | "Changes to survey-runner to use sdc-cryptography library" — at `f4803f94^` (parent), `app/cryptography/token_helper.py` does kid-based key selection locally (`secret_store.get_private_key_by_kid`); a pin *before* the sdc-crypto migration yields real ADR-0004 violations, but the repo layout (app/cryptography, submitter/) differs radically from HEAD. |
| `36f583ce8fd9f50ffcd849e8923cc3e1f16f3ce3` | 2017-07-26 | "Removed default KID" merge — the ADR-0004 crossover-period behavior (default key when no kid) being removed; ultra-fine-grained, header-level, not import-checkable. |
| `871489a17c00d7008fedd8b6b9294d7e459875d5` | 2019-07-30 | "Refactor view logic" (mid URL-structure migration, ADR-0005 era) — historical URL-shape state, but URL shapes are not FQN-expressible. |

None of these give a *modern-code* violation population: at HEAD the crypto is
centralized in `sdc-crypto` calls and everything else is data/UI/routing design.
The only HEAD-vs-ADR tension (ADR-0010 `theme`/`expires_in` cookie remnants) is
not FQN-encodable. **Verdict: swap (see §3).**

---

## 2. Scoring-unit totals

Scoring unit = one constraint. Violation instance = one (repo, ADR, constraint,
code location) where the pin demonstrably violates.

| repo | ADRs scanned | code-inferable ADRs | scoring units (constraints) | violation instances at pin | compliant instances (probes) |
|------|------------:|--------------------:|----------------------------:|---------------------------:|-----------------------------:|
| python-tuf | 10 | 3 | 4 | 0 | 4 (all-comply baseline) |
| flowkit | 12 | 4 | 6 | 0 | 6 |
| experimenter | 16 | 3 | 4 | 0 (+1 historical at `a2de3aeb`) | 4 |
| eq-questionnaire-runner | 10 | 1 (weak) | 0–1 (0 recommended) | 1 mild, non-encodable | 0–1 |
| **Grand total (active 1–4)** | 48 | 11 | **14–15** | **0 at HEAD** (1–2 historical/weak) | **14–15** |

**Against the target (50+ violation instances, ~100 scoring units): SHORT.**

Gap analysis:

- The census yields **~14 scoring units** vs ~100 target — a gap of ~85. Even
  doubling per-ADR constraint extraction (finer-grained subjects, e.g. splitting
  ADR-0005 flowkit into per-package edges) gets maybe +5–8.
- **Violations at pins are zero for all four active repos.** Every active repo's
  HEAD complies with its own ADRs (expected: ADRs describe the adopted design).
  The benchmark population therefore comes from *injected diffs* (per issue #74)
  and/or *historical pins*, not from HEAD violations.
- Scaling levers, in order of value:
  1. **Injected-diff instances**: each scoring unit can host multiple injected
     violation diffs (flask-style). With 14 constraints × 2–3 injected cases
     each, the 50-instance population is reachable: 14 × 3 ≈ 42, plus
     historical pins closes the gap.
  2. **Historical pins** (already identified): python-tuf `499f1c85`/`a2794c2f^`
     (ADR-0006/0010 violations), experimenter `a2de3aeb` (ADR-0010 violation),
     eq-runner `f4803f94^` (ADR-0004 violation) — each is a real,
     instance-disjoint violation snapshot.
  3. **Add repos**: a fifth/sixth repo with dense checkable constraints would
     add 5–15 units each (see §3 for candidate names from the ADR-Study-Dataset).
  4. **home-assistant** (held-out) has 2–3 checkable ADRs (§7) worth ~4–6 units
     if it is ever promoted to gold authoring.

---

## 3. eq-questionnaire-runner triage verdict

> **2026-09-14 UPDATE: SWAP EXECUTED.** Replacement = `Midnighter/structurizr-python`
> (the repos.md designated spare). The two candidates recommended below failed
> re-vetting: `transcom/mymove` is GONE from GitHub (only archived
> `transcom/mymove-docs` remains); `vwt-digital/operational-data-hub` confirmed
> docs-only (~15 KB Python, no code to violate). The structurizr-python census
> and gold live in `structurizr_python_gold.json` /
> `structurizr_python_instances.json`; everything below is the superseded
> eq-runner record.

### structurizr-python census (2026-09-14)

Clone: `dataset-Shepherd/small/structurizr-python`, HEAD pin
`31f1dcadb3ff113d8a77ce132657237ea01c307b` (2025-08-14, 502 commits, ~620 KB,
Apache-2.0, alive). Strict #120-grammar triage of 9 ADRs: **2 encodable
constraints** (honest correction of the ~3-4 pre-walk estimate):

| ADR | verdict |
|-----|---------|
| 0001 record-decisions, 0002 version-control | zero-constraint (meta/process) |
| 0003 python-3-6-only | zero-constraint. NOT encoded: no version explicitly rejected in the Decision (Python 2 is Context rationale only); encoding would re-create the class-A passing-mention failure mode |
| 0004 versioneer, 0005 isort/black/flake8, 0006 tox, 0007 pytest | zero-constraint (tooling) |
| 0008 package-structure | **`examples.*` prohibits_dependency `structurizr.api.*`** (top level exports the full api surface at `src/structurizr/__init__.py`; sanctioned form = `examples/upload_workspace.py:25`; tests/ excluded, the "tests reflect this package structure" sentence = layout mirroring; model/view deep imports out of scope: top level does not re-export them) |
| 0009 pydantic-for-json | **`src.structurizr.api.*` requires_dependency `pydantic`** (api_response.py:21, structurizr_client_settings.py:31). NOT encoded: blanket `src.structurizr.* requires` (over-broad) and a model-layer json prohibition (separation is class-level Model/ModelIO co-located; Decision is a tool choice, not a prohibition) |

**Layout rule (this repo's counterpart of flowkit's doubled pkg/pkg):** module
FQNs carry the src-layout prefix (`src.structurizr.*`) while IMPORTS edge
targets are the literal dotted import (`structurizr.api.structurizr_client`,
`pydantic`). Gold subjects use the FQN shape; objects use the import-target
shape.

**Verification (empirical, mirrors test_cpt_detect_eval run_case):** baseline
at HEAD = zero violations (ADR-0008 orphan: no example deep-imports the api
package). Scoring pass: **5 exact / 0 partial / 0 miss / 0 FP** over 7 cases
(3 injected: api function+class granularity, api class-only, examples
deep-import; 3 compliant probes: #115 seeding, sanctioned pydantic module,
top-level import counterpart; 1 historical compliant: `ab5adc9` 2021-12-01,
satisfied requires on a full api tree). Second historical pin `6af4134`
(2020-04-05, pre-pydantic cookiecutter skeleton): both constraints orphan,
verified zero-violation; era context, not a case pin (no violation instance
reachable: pydantic resolves to no node in that tree).

**Population after this repo: 35 cases / 27 expected-violation scoring units**
(was 28 / 22; #106 target 50+ / ~100, shortfall persists).

HA report-only run DEFERRED (user decision 2026-09-14; scoped per-package run
when resumed; full-graph detect perf is an engine concern, not a #138 blocker).

**Constraint yield at HEAD: 0 encodable scoring units (1 weak/borderline: ADR-0004
requires sdc.crypto; 1 non-encodable: ADR-0010 cookie-property prohibition).**

**Verdict: SWAP.** The prior observation is confirmed — 9 of 10 ADRs are UI/domain
decisions (URL shapes, list data model, relationships, lookups, primary person,
cookie contents, test organization, build manifests). The single crypto ADR
(0004) is satisfied via a third-party library call whose kid semantics live
inside `sdc-crypto`, invisible to import/call-level analysis. eq-runner would
contribute ~0 of the 50+ violation instances — dead weight.

What a replacement needs: Python repo, 3+ ADRs with *dependency/implementation*
decisions, dense checkable constraints. Candidates from the ADR-Study-Dataset
(`adr_all.csv`, `project_stats.csv`):

| candidate | ADRs in dataset | why promising |
|-----------|----------------:|---------------|
| `transcom/mymove` | 67 total, incl. `docs/adr/0010-isolate-test-access-to-database.md`, `0062-run-tests-in-transactions.md`, `0011-test-suites.md` | Django/Python monolith; DB-access isolation and test-transaction ADRs are import-checkable |
| `NERC-CEH/datalab` | 47 total (mostly infra; `0029-dask-for-python-distributed-compute.md`) | Python-heavy data platform; compute-stack ADRs may yield requires_dependency on dask/pandas |
| `vwt-digital/operational-data-hub` | 73 ADRs | Large decision count; verify Python-side density first (many ADRs are infra/Node) |
| `Datatamer/tamr-client` | 10 ADRs, incl. `0008-standardized-imports.md`, `0009-separate-types-and-functions.md`, `0005-composable-functions.md` | **Highest density of FQN-checkable constraints** (types module separation, import standardization) — but NOTE: tamr-client + openlobby are already in the frozen eval set (`cpt_detect_ground_truth.json`); using them in the benchmark would violate instance-disjointness unless only unused ADRs/constraints are taken. Flag to the issue-tracker before picking. |
| `boxwise/boxwise-flask` / `boxtribute` | 4 / 2 | Flask/Django Python apps, smaller ADR counts |

Recommendation: shortlist `transcom/mymove` (Python, Django, many process-adjacent
but some import-checkable ADRs) and re-verify `vwt-digital/operational-data-hub`
ADR language for FQN-expressible decisions; only consider tamr-client if the
curation team explicitly signs off on constraint-level (not instance-level)
disjointness from the eval gold.

---

## 4. Natural ADR-ADR conflicts

Pairs of ADRs within the same repo whose encodable constraints contradict:

| repo | pair | clash |
|------|------|-------|
| python-tuf | ADR-0003 (subdirectory development plan: "flesh out tuf/api/*, implement tuf/repository/*") vs ADR-0010 (minimal repository abstraction, "does not implement all repository actions itself") | Both constrain `tuf.repository.*`'s relationship to the metadata/application code, but neither yields contradicting *predicates* in the four-predicate grammar (one is a plan, the other a dependency direction). Not a constraint clash. |
| flowkit | ADR-0003 (HTTP API single access point: `flowapi prohibits flowmachine`) vs ADR-0005 (zmq API-backend communication) | Not a contradiction: zmq is the sanctioned channel; the prohibition targets direct imports. No clash. |
| experimenter | ADR-0002 (GQL for Nimbus UI) vs ADR-0008 (HTMX for new pages) | **Near-conflict**: ADR-0002 mandates GraphQL/apollo for the Nimbus front-end; ADR-0008 moves new pages to HTMX and deprecates the GraphQL path ("eventually moving to HTMX"). In constraint form: ADR-0002 requires `nimbus_ui.*` → graphql stack; ADR-0008 prohibits `nimbus_ui.*` (new pages) → graphene. These genuinely clash on `experimenter.nimbus_ui.*` → graphene/graphql — a textbook supersession pair (0008 later-in-time supersedes 0002's GraphQL mandate for pages). |

**Count: 1 genuine natural conflict pair** (experimenter ADR-0002 vs ADR-0008),
plus 2 structural near-pairs that do not encode as contradicting constraints.

**Decision rule triggered: fewer than ~10 natural conflicts total ⇒ synthetic
conflict-ADR injection will be needed later (per issue #74).** The experimenter
pair is the only organic supersession pair found across all 58 ADRs scanned; the
benchmark's conflict-detection cases will be synthetic.

---

## 5. Commit pin table

| repo | pin SHA | pin date | status |
|------|---------|----------|--------|
| python-tuf | `6889cfbffbb90a17930fbdedf12ae050be775fe3` | 2026-07-14 | violations found: none at pin (compliant); alternate candidates listed (`a2794c2f^`, `499f1c85^`, `5e17617f`, `22b27264`) |
| flowkit | `24d88247d57987fe33f6b8915540d7bf09b58033` | 2026-05-28 | violations found: none at pin (compliant); injected-diff cases recommended |
| mozilla-experimenter | `d61a2b8efcb7fd77a849c9f9dc163130473b7f16` | 2026-08-31 | violations found: none at pin (compliant); historical violation pin `a2de3aeb` (2023-06-09) identified |
| eq-questionnaire-runner | `da90adfdc4390c0fd1d33dbc896adc38d6ca2022` | 2026-08-26 | violations found: 1 mild non-encodable (ADR-0010 cookie remnants); verdict SWAP |
| home-assistant (held-out, report-only) | `e4b01b65d306cf4ffcd692b9eb7c7d2ce4f794e4` | 2026-09-01 | code repo; ADRs in separate repo `home-assistant-architecture` @ `0c4f7dbf21c9e1279bea23a1eb2f9ab295d0e9e9`; no deep violation scan (report-only) |

---

## 6. python-tuf eval-overlap flags

The frozen eval gold (`tests/ground_truth/python_tuf_ground_truth.json`) contains
exactly 4 constraints; this census re-derives the same 4 (identical
subject/predicate/object, since the ADR text determines them):

| constraint | in eval gold? | overlap risk | disjoint benchmark recommendation |
|-----------|:---:|--------------|-----------------------------------|
| ADR-0006 `tuf.api.metadata.*` requires `tuf.api.serialization.*` | YES (eval) | constraint duplicate (unavoidable — same ADR text) | benchmark must use **different instances**: (a) historical pin `499f1c85^` where `tuf/api/metadata.py` lacks the serialization dependency; (b) injected diff *other than* the eval's `LegacyWireFormatCodec` hand-rolled codec (e.g. a `to_json()` method using stdlib `json` added to `Root`, or a serializer helper inside `_payload.py`) |
| ADR-0010 `tuf.repository.*` requires `tuf.api.metadata.*` | YES (eval) | constraint duplicate | benchmark instances must avoid the eval's `tuf/repository/__init__.py` stdlib-json helpers; candidates: (a) historical pin `5e17617f`/`a2794c2f^` era where `tuf/repository/*` did not exist yet (inverse violation via injected module), (b) injected diff adding a stdlib-json metadata reader to `tuf/repository/_repository.py` *function scope* (different matched_fqn than eval's `__init__.py` helpers) |
| ADR-0001 `tuf.*` prohibits `python2.7` | YES (eval) | constraint duplicate | never fires at any modern pin; benchmark value ≈ 0 — recommend *not* carrying this constraint into the benchmark set, or using it only as a zero-expectation probe |
| ADR-0001 `tuf.*` prohibits `python3.5` | YES (eval) | constraint duplicate | same as above |

Eval *instance* duplication check (against `tests/ground_truth/cpt_detect_ground_truth.json`,
python-tuf cases): the eval's violating instances are
`tuf.api.metadata.LegacyWireFormatCodec` (injected diff in `tuf/api/metadata.py`)
and `tuf.repository.read_role_file_with_stdlib_json` /
`write_role_file_with_stdlib_json` (injected diff in `tuf/repository/__init__.py`),
plus zero-expectation probes in `tuf/api/serialization/*`, `tuf/repository/_repository.py`,
`tuf/ngclient/fetcher.py`, and `tuf/api/serialization/json.py` (dotted-import probe).

**Instance-disjoint benchmark set for python-tuf:**

1. **Historical-pin instance (ADR-0006)**: pin `499f1c858ea315be578087bbb189b46e9504ecfc^`
   (2021-03-04); `tuf/api/metadata.py` has no `tuf.api.serialization` dependency at
   any scope while `tuf/api/serialization/json.py` exists — fires ADR-0006 requires
   at `tuf.api.metadata` (module FQN), a different matched_fqn and a different code
   state than the eval's injected codec.
2. **Historical-pin instance (ADR-0010)**: pin `a2794c2f36513375d0d85ce7034f59c2bb10c95e^`
   (2022-01-26, pre-legacy-drop) — `tuf/repository/` does not exist while legacy
   `tuf/repository_tool.py`/`repository_lib.py` (~7000 lines) implement repository
   functionality *without* the Metadata API; an injected `tuf/repository/` skeleton
   or the legacy modules themselves yield ADR-0010 violations instance-disjoint
   from the eval.
3. **Injected-diff instances at the eval pin (allowed, different locations)**: e.g.
   stdlib-json codec added to `tuf/api/_payload.py` (ADR-0006 fire at
   `tuf.api._payload.<name>`), or a repository-side helper in
   `tuf/repository/_repository.py` that re-parses metadata with `json` (ADR-0010
   fire at a `_repository` FQN — note the eval's `_repository.py` case is a
   *zero-expectation probe*, so a violating diff there is disjoint by construction).
4. **Not recommended**: carrying ADR-0001's EOL-python prohibitions into the
   benchmark — they are eval-gold duplicates with no plausible firing instance at
   any candidate pin.

---

## 7. home-assistant held-out preview (report-only)

Code @ `e4b01b65d306cf4ffcd692b9eb7c7d2ce4f794e4` (2026-09-01); ADRs @
`home-assistant-architecture` `0c4f7dbf21c9e1279bea23a1eb2f9ab295d0e9e9`, `adr/`
(0001–0022). **Classification + candidate constraint counts only — no deep
violation scan.**

| ADR | Title | Code-inferable? | candidate constraints (est.) | note |
|-----|-------|-----------------|-----------------------------:|------|
| 0001 | Record architecture decisions | No | 0 | meta-ADR |
| 0002 | Minimum supported Python version | Yes | 1 | "support the latest two released minor upstream Python versions" — version-check prohibition on EOL minors; **superseded by ADR-0020** (note both) |
| 0003 | Monitor condition and data selectors | No | 0 | config-option UX policy ("We don't merge PRs with data selectors") — process, not FQN edge |
| 0004 | Webscraping | Yes | 1–2 | "no longer accept any new integration that relies on webscraping" — prohibits_dependency `homeassistant.components.*` → `beautifulsoup`/scraping libs; **exception carved for `scrape` integration itself** (present at pin: `homeassistant/components/scrape/manifest.json` requires `beautifulsoup4`) — the exception must be encoded or the constraint will false-positive |
| 0005 | Code formatting (Black) | No | 0 | style/tooling |
| 0006 | Docker images | No | 0 | packaging/deployment |
| 0007 | Config YAML structure for integrations | No | 0 | YAML-config placement rule ("configuration under the integration domain key") — config-file structure, not an import/inheritance edge |
| 0008 | Code owners | No | 0 | governance |
| 0009 | Translations 2.0 | No | 0 | i18n process |
| 0010 | Integration configuration (config entries/flows) | No | 0 | config-UX architecture; the checkable residue (config_flow flags in manifests) is manifest data, not Python FQN edges |
| 0011 | Discovery requires unique ID | Yes (weak) | 1 | "Integrations that are discoverable must provide a unique id (via `async_set_unique_id`)" — requires_dependency `homeassistant.components.*.config_flow.*` → `async_set_unique_id`; borderline (call-based, per-integration, exception-heavy) |
| 0012 | Define supported installation method | No | 0 | support-policy definition |
| 0013 | Home Assistant Container | No | 0 | installation method |
| 0014 | Home Assistant Supervised | No | 0 | installation method |
| 0015 | Home Assistant OS | No | 0 | installation method |
| 0016 | Home Assistant Core | No | 0 | installation method |
| 0017 | Hardware screening OS | No | 0 | hardware policy |
| 0018 | Supported databases | Yes | 1–2 | "Limit DB support to ... MariaDB ≥ 10.3, MySQL ≥ 8.0, PostgreSQL ≥ 12, SQLite" — recorder enforces via version checks (`homeassistant/components/recorder/util.py:79-92`); encodable as requires_dependency on the recorder's dialect/version gate, borderline (runtime version policy, not import topology) |
| 0019 | GPIO | Yes | 1 | "no longer accept integrations that integrate with devices over GPIO" — prohibits_dependency `homeassistant.components.*` → `RPi.GPIO`/`gpiozero`/`pigpio`; **exception for serial-device exposure**; at pin `remote_rpi_gpio` (gpiozero+pigpio) still exists marked `legacy` — a genuine, checkable violation instance |
| 0020 | Minimum supported Python version (supersedes 0002) | Yes | 1 | single-minor policy; supersedes ADR-0002 — only one of the pair should be active (supersession case) |
| 0021 | YAML config deprecation policy | No | 0 | deprecation-period process |
| 0022 | Integration quality scale | No | 0 | grading framework |

**Held-out estimate: 5–7 candidate constraints** (ADR-0002/0020 pair counts once
under supersession; ADR-0004, 0011, 0018, 0019 are the checkable ones), with
ADR-0019 offering a real violation instance at the pin (`remote_rpi_gpio`
integration using gpiozero/pigpio against the prohibition). Good candidate for a
future report-only pipeline run; the ADR-0004/0019 exception clauses make
constraint authoring FP-prone and would need careful negative-space encoding.

---

## Appendix: evidence-search commands used (for the annotator)

```sh
# python-tuf
grep -n "serialization" tuf/api/metadata.py
grep -rn "import json|python2|python_2|sys.version_info" tuf/api/metadata.py tuf/repository/*.py
grep -n "import" tuf/repository/_repository.py tuf/repository/__init__.py

# flowkit
grep -rn "^from quart|from quart import" flowapi/flowapi/
grep -rln "zmq" flowapi/flowapi/ flowmachine/flowmachine/core/server/
grep -rln "redis" flowmachine/flowmachine/core/
grep -rln "import flowmachine" flowapi/ flowclient/        # expect empty
grep -rn "jwt_required|protect" flowapi/flowapi/*.py
grep -rn "redaction_threshold" flowmachine/flowmachine/features/location/redacted_labelled_spatial_aggregate.py

# experimenter
grep -rn "htmx" experimenter/experimenter/nimbus_ui/forms.py
grep -rln "graphene|graphene_django" experimenter/experimenter/   # expect empty
grep -rn "from mozilla_nimbus_schemas|from pydantic" experimenter/experimenter/jetstream/client.py
grep -n "from pydantic" schemas/mozilla_nimbus_schemas/jetstream/*.py
grep -n "load_data_from_gcs" experimenter/experimenter/jetstream/client.py

# eq-runner
grep -rn "sdc.crypto|decrypter|JWEHelper" app/ --include="*.py"
grep -rn "cookie_session\[" app/ --include="*.py"
grep -rn "async_set_unique_id" homeassistant/components/*/config_flow.py   # (home-assistant)
```