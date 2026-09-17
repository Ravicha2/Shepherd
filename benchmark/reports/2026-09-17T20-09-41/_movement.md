# FP / quality movement vs `2026-09-16T23-56-00`

| repo | run | ing e/p/m | FP | zero-gold FP | has-gold FP | excl. tooling | class A/B-C matched,FP | detection violation e/p/m |
|---|---|---|---|---|---|---|---|---|
| python-tuf | base r1 | 3/0/1 | 4 | 3 | 1 | 0 | A 0,0 B/C 3,4 | 6/0/0 (pattern 6/0/0, overlap 1064, stale 0) |
| python-tuf | **new r1** | 3/0/1 | 1 | 1 | 0 | 0 | A 0,0 B/C 3,1 | 6/0/0 (pattern 6/0/0, overlap 1064, stale 0) |
| python-tuf | **new r2** | 3/0/1 | 4 | 4 | 0 | 0 | A 0,0 B/C 3,4 | 6/0/0 (pattern 6/0/0, overlap 1064, stale 0) |
| flowkit | base r1 | 0/4/2 | 45 | 43 | 2 | 0 | A 0,20 B/C 4,25 | 9/0/3 (pattern 0/0/12, overlap 1721, stale 0) |
| flowkit | **new r1** | 0/3/3 | 14 | 12 | 2 | 32 | A 0,0 B/C 3,14 | 6/0/6 (pattern 0/0/12, overlap 1379, stale 0) |
| flowkit | **new r2** | 0/4/2 | 15 | 12 | 3 | 40 | A 0,0 B/C 4,15 | 9/0/3 (pattern 0/0/12, overlap 1721, stale 0) |
| experimenter | base r1 | 0/0/4 | 10 | 8 | 2 | 1 | A 0,0 B/C 0,10 | 0/0/18 (pattern 0/0/18, overlap 0, stale 0) |
| experimenter | **new r1** | 0/2/2 | 14 | 12 | 2 | 1 | A 0,0 B/C 2,14 | 1/0/17 (pattern 0/0/18, overlap 733, stale 0) |
| experimenter | **new r2** | 0/1/3 | 13 | 12 | 1 | 0 | A 0,0 B/C 1,13 | 1/0/17 (pattern 0/0/18, overlap 733, stale 0) |
| structurizr-python | base r1 | 0/1/1 | 7 | 7 | 0 | 6 | A 0,4 B/C 1,3 | 4/0/2 (pattern 0/0/6, overlap 60, stale 0) |
| structurizr-python | **new r1** | 0/1/1 | 0 | 0 | 0 | 13 | A 0,0 B/C 1,0 | 4/0/2 (pattern 0/0/6, overlap 60, stale 0) |
| structurizr-python | **new r2** | 0/1/1 | 0 | 0 | 0 | 13 | A 0,0 B/C 1,0 | 4/0/2 (pattern 0/0/6, overlap 60, stale 0) |

## detection fires per (adr, predicate, object), baseline -> new


**python-tuf**

| adr | predicate | object | base fires | new fires |
|---|---|---|---|---|
| ADR-2020-11-30 | prohibits_dependency | securesystemslib | 0 | 98 |
| ADR-0008 | prohibits_implementation | tuf.api._payload.Signed | 0 | 12 |
| ADR-0008 | requires_implementation | tuf.api._payload.Signed | 1 | 0 |

**flowkit**

| adr | predicate | object | base fires | new fires |
|---|---|---|---|---|
| ADR-0010 | prohibits_dependency | airflow | 117 | 0 |
| ADR-0012 | prohibits_implementation | flowauth.backend.flowauth.models.Scope | 65 | 0 |
| ADR-0008 | requires_dependency | papermill | 3 | 6 |
| ADR-0008 | requires_dependency | scrapbook | 3 | 6 |
| ADR-0009 | requires_dependency | nbconvert | 3 | 6 |
| ADR-0010 | requires_dependency | prefect | 1 | 6 |
| ADR-0007 | requires_dependency | mapboxgl | 0 | 6 |
| ADR-0009 | requires_dependency | asciidoctor | 0 | 6 |
| ADR-0005 | requires_dependency | zmq | 1 | 4 |
| ADR-0003 | requires_dependency | flowmachine.* | 4 | 0 |
| ADR-0003 | requires_dependency | flowapi.* | 0 | 3 |
| ADR-0005 | requires_dependency | redis | 1 | 2 |
| ADR-0006 | requires_dependency | quart_jwt_extended | 1 | 2 |
| ADR-0003 | requires_dependency | flowapi.flowapi.* | 0 | 3 |
| ADR-0011 | requires_implementation | flowmachine.flowmachine.features.location.redacted_labelled_spatial_aggregate.RedactedLabelledSpatialAggregate | 0 | 2 |

**experimenter**

| adr | predicate | object | base fires | new fires |
|---|---|---|---|---|
| ADR-0010 | requires_dependency | pydantic | 29 | 58 |
| ADR-0004 | requires_dependency | celery | 22 | 44 |
| ADR-0002 | requires_dependency | react | 0 | 44 |
| ADR-0002 | requires_dependency | react-bootstrap | 0 | 44 |
| ADR-0003 | requires_dependency | experimenter.experimenter.jetstream.* | 27 | 0 |
| ADR-0011 | prohibits_implementation | experimenter.experimenter.glean.* | 9 | 18 |
| ADR-0008 | requires_dependency | graphene_django | 22 | 0 |
| ADR-0002 | requires_dependency | graphene_django | 22 | 0 |
| ADR-0003 | requires_dependency | rest_framework | 0 | 22 |
| ADR-0003 | requires_dependency | experimenter.experimenter.experiments.api.* | 0 | 21 |
| ADR-0008 | requires_dependency | graphene | 21 | 0 |
| ADR-0013 | requires_dependency | experimenter.experimenter.metrics.* | 20 | 0 |
| ADR-0003 | requires_dependency | google | 0 | 14 |
| ADR-0008 | prohibits_dependency | graphene | 0 | 4 |
| ADR-0008 | prohibits_dependency | graphene_django | 0 | 4 |

**structurizr-python**

| adr | predicate | object | base fires | new fires |
|---|---|---|---|---|
| ADR-0004 | requires_dependency | versioneer | 6 | 0 |
