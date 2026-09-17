# Commit set for the two-arm run

Decided on #162 (comment 5722635401). This file is the list the run reads. The gold files stay the source of truth for case content; this is the enumeration and the rules.

Pinned population: 5 repos / 60 cases / 63 expected-violation units, asserted by `test_benchmark_gold_shape` (`app/tests/services/adg/test_benchmark_arms_eval.py:523`).

## Tier A: the 60 gold cases (headline, pooled)

Each row becomes a snapshot the arms run against. Injected cases are applied in a scratch clone and committed so they have a real SHA. Historical cases get a detached checkout at their own pin. Everything else runs at its repo's pin.

Pin per repo: python-tuf `6889cfbffbb9`, flowkit `24d88247d579`, experimenter `d61a2b8efcb7`, structurizr-python `31f1dcadb3ff`, home-assistant `e4b01b65d306` (code) with its ADRs from the separate ADR repo at `0c4f7dbf21c9`.

| repo | case_id | type | source | expected units |
|---|---|---|---|---:|
| experimenter | exp-bench-hist-pre-schema-client | historical | `a2de3aebd37b` | 1 |
| experimenter | exp-bench-graphene-backslide | injected | `d61a2b8efcb7` | 1 |
| experimenter | exp-bench-jetstream-db-snapshot | injected | `d61a2b8efcb7` | 3 |
| experimenter | exp-bench-manual-schema-validation | injected | `d61a2b8efcb7` | 2 |
| experimenter | exp-bench-gcs-bypass | injected | `d61a2b8efcb7` | 2 |
| experimenter | exp-bench-jetstream-cluster | injected | `d61a2b8efcb7` | 8 |
| experimenter | exp-bench-hist-late-pre-schema-client | historical | `9857c48a351c` | 1 |
| experimenter | exp-bench-probe-jetstream-sanctioned | compliant_probe | `d61a2b8efcb7` | 0 |
| experimenter | exp-bench-probe-nimbus-ui-no-graphene | compliant_probe | `d61a2b8efcb7` | 0 |
| experimenter | exp-bench-probe-schemas-pydantic | compliant_probe | `d61a2b8efcb7` | 0 |
| experimenter | exp-bench-probe-db-write-no-prohibition | compliant_probe | `d61a2b8efcb7` | 0 |
| flowkit | flowkit-client-direct-flowmachine | injected | `24d88247d579` | 1 |
| flowkit | flowkit-flowapi-direct-flowmachine | injected | `24d88247d579` | 4 |
| flowkit | flowkit-flowapi-endpoint-without-jwt | injected | `24d88247d579` | 2 |
| flowkit | flowkit-flowmachine-core-without-redis | injected | `24d88247d579` | 1 |
| flowkit | flowkit-transitive-flowapi-via-flowclient | injected | `24d88247d579` | 4 |
| flowkit | flowkit-probe-client-httpx-only | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-probe-endpoint-sanctioned | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-probe-core-redis-proper | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-probe-features-no-redis | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-probe-flowapi-utils-assignment | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-probe-decoy-local-name | compliant_probe | `24d88247d579` | 0 |
| flowkit | flowkit-decoy-module-var | known_limitation | `24d88247d579` | 0 |
| flowkit | flowkit-probe-flowetl-out-of-scope | compliant_probe | `24d88247d579` | 0 |
| home-assistant | ha-bench-pin-baseline | historical | `e4b01b65d306` | 1 |
| home-assistant | ha-bench-webscrape-selenium-module | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-webscrape-selenium-setup-local | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-webscrape-selenium-in-existing | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-gpio-new-integration | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-gpio-deep-import | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-probe-http-client | compliant_probe | `e4b01b65d306` | 1 |
| home-assistant | ha-bench-probe-serial-exempt | compliant_probe | `e4b01b65d306` | 1 |
| home-assistant | ha-bench-probe-edit-remote-gpio | compliant_probe | `e4b01b65d306` | 1 |
| home-assistant | ha-bench-gpio-transitive-import | injected | `e4b01b65d306` | 3 |
| home-assistant | ha-bench-webscrape-selenium-alias | injected | `e4b01b65d306` | 2 |
| home-assistant | ha-bench-gpio-removal | injected | `e4b01b65d306` | 0 |
| home-assistant | ha-bench-gpio-wildcard-limitation | known_limitation | `e4b01b65d306` | 1 |
| home-assistant | ha-bench-gpio-dynamic-import-limitation | known_limitation | `e4b01b65d306` | 1 |
| python-tuf | tuf-bench-legacy-json-store | injected | `6889cfbffbb9` | 3 |
| python-tuf | tuf-bench-legacy-repo-client | injected | `6889cfbffbb9` | 1 |
| python-tuf | tuf-bench-hist-pre-repository-compliant | historical | `eb67b09cf834` | 0 |
| python-tuf | tuf-bench-probe-repository-metadata-import | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-probe-repository-dotted-import | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-probe-sanctioned-serializer | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-probe-payload-out-of-scope | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-repository-class-import | injected | `6889cfbffbb9` | 1 |
| python-tuf | tuf-bench-repository-facade-import | injected | `6889cfbffbb9` | 1 |
| python-tuf | tuf-bench-probe-repository-sibling-import | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-serialization-deleted | known_limitation | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-probe-metadata-seeded | compliant_probe | `6889cfbffbb9` | 0 |
| python-tuf | tuf-bench-probe-repository-json-satisfied | compliant_probe | `6889cfbffbb9` | 0 |
| structurizr-python | struct-bench-api-legacy-json-response | injected | `31f1dcadb3ff` | 3 |
| structurizr-python | struct-bench-api-legacy-json-client-class | injected | `31f1dcadb3ff` | 1 |
| structurizr-python | struct-bench-probe-api-settings-seeded | compliant_probe | `31f1dcadb3ff` | 0 |
| structurizr-python | struct-bench-probe-api-pydantic-module | compliant_probe | `31f1dcadb3ff` | 0 |
| structurizr-python | struct-bench-example-deep-import | injected | `31f1dcadb3ff` | 1 |
| structurizr-python | struct-bench-probe-example-toplevel | compliant_probe | `31f1dcadb3ff` | 0 |
| structurizr-python | struct-bench-example-plain-deep-import | injected | `31f1dcadb3ff` | 1 |
| structurizr-python | struct-bench-probe-tests-deep-import | compliant_probe | `31f1dcadb3ff` | 0 |
| structurizr-python | struct-bench-hist-2021-compliant | historical | `ab5adc94c188` | 0 |

Two accounting notes carried from the census:

- home-assistant's three `compliant_probe` rows are not zero-gold rows. Each carries the one genuine violation that stands at the pin, so 9 of HA's 21 units are that same standing violation repeated per case. The #164 scorer must not count it 9 times as independent coverage.
- The 4 `known_limitation` rows are scored as limitation rows, not as units.

## Tier B: real commits (reported separately, never pooled with Tier A)

### Clean merged commits, to check nothing fires

Expected answer is zero findings in both arms, so no ground truth authoring is needed. Any finding is a false positive.

| repo | commit | status |
|---|---|---|
| python-tuf | `0ac86c67` | pilot cell, already annotated at `../../research-exp-setup/annotations/python-tuf/0ac86c67.yml`; baseline reported 3 (0 confirmed) and CPT reported 1 (dismissed) |
| each of the five | to be selected | rule: a merged commit on the repo's default branch, at or near the pin era, with a parent available, carrying no ADR-era change |

### Real commits that do violate

Found by the census, each with a real diff and a real violation:

| repo | commit | what it is |
|---|---|---|
| home-assistant | `e4b01b65` | live ADR-0019 violation at the pin, `remote_rpi_gpio` importing `gpiozero` |
| experimenter | `a2de3aeb` | schema-availability era violation |
| experimenter | `9857c48a` | last pre-adoption commit, parent of the fix `b6d9aebc` |
| eq-questionnaire-runner | `f4803f94^` | real ADR-0004 violations. Outside the five benchmark repos, so optional and never in the pooled denominator |

Real commits are a side tier because a clean merged commit is the normal case, so there is almost nothing to find there. That is exactly why they cannot carry the headline numbers.

## Excluded, with reasons

| commit | reason |
|---|---|
| home-assistant `6e172854` | predates ADR-0019, so gpiozero use there is not a violation |
| python-tuf `499f1c85^` | the engine cannot fire (uniform seeding masks the requires) |
| python-tuf `22b27264` | the engine cannot fire |
| the 4 `known_limitation` cases | the engine cannot fire; limitation rows, not scoring units |

## Run settings

- Reviewer: `deepseek-v4.1-flash`, passed explicitly with `--model` on every run and recorded in each `metrics.json`. Different model family from the resolver (`google/gemini-3.1-flash-lite`), on purpose.
- Runs per arm per commit: 1. `pi` exposes no temperature flag and no seed, so the stance is provider defaults with run-to-run variation uncontrolled. A noise floor means repeats on one repo, the #149 way, not repeats everywhere.
- Constraints: the CPT arm fires on the gold-seeded graphs built by #167, not on constraints re-extracted per run.
- Same reviewer model in both arms, recorded per record.
