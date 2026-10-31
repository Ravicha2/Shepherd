# Issue #259 — A6 full 18-case gate: write-up and verdict

*2026-10-30. Issue #268; closes #259; target #252; gate #249; amendment #266;
RFC #240. Every number below reads from artifacts in the `research-exp-setup`
repo (`main`, merge `fc81a82`): the dated #267 record
`security/records/a6_gate_267/`, the frozen #259 record
`security/records/a6_gate/`, the frozen lowering sessions under
`security/runs/`, and the A2 adjudication sheets under
`security/records/adjudication/`. No case was rerun for this note.*

## Verdict

The #249 gate under the #266 paired-handler `clears` amendment is **FAIL**,
with `clears` 5/6 on class (ii). From `security/records/a6_gate_267/summary.json`:

| check | result |
|---|---|
| lowering_provenance | PASS |
| zero_candidate | PASS |
| fires (class ii, 6/6) | PASS |
| **clears (class ii, 6/6)** | **FAIL — 5/6** |
| subset | PASS |
| replacement | PASS |
| orphans | PASS |
| collateral (12 reported) | PASS |
| frozen comparability | PASS (all 18, detect outputs byte-identical) |

`fires` passes 6/6. `clears` fails on tandoor alone; the other five class-(ii)
cases clear, including both load-bearing wins for the #252 target (pretix,
weblate). The frozen #259 run failed the same gate 3/6 on `clears`; the
amendment moved pretix and weblate to clear without touching any detect
output.

## Tandoor: visible but conservatively rejected

#253's closing note called this case a dead end. The #267 record supports a
more precise statement: the fix is visible to the extractor and rejected on
purpose.

The fixing diff (`recipes` `0b363fb6..84fa837c5`, `cookbook/views/api.py`,
`RecipeViewSet.batch_update`) adds the ownership filter on the same chain
#253 built the chain-unit for:

```python
recipes = Recipe.objects.filter(
    id__in=serializer.validated_data['recipes'], space=self.request.space
).filter(Q(private=False) | (Q(private=True) & (Q(created_by=self.request.user) | Q(shared=self.request.user))))
```

The `created_by` and `shared` disjuncts name the requester. `Q(private=False)`
does not, and it can grant on its own, so the #258 soundness stance rejects
the whole `or`: "an `or` authorizes only when every disjunct does, since any
one disjunct can grant on its own"
(`app/services/adg/object_scope.py:865`). Weakening that rule would
let a requester-less disjunct authorize every requester; that route is
deliberately not taken.

The gate holds the case red through arm 4 of the amendment. `batch_update`
has no route object parameter (#253's closing note), so no violation names it
at either SHA, and the case-level fire is carried by 23 sibling handlers in
`cookbook/views/api.py`. A sibling-only fire is not a clear, so tandoor fails
`clears` with its fire unattributed.

Tandoor is not load-bearing for #252. A2 held it reader-side, and 14/18
requires pretix and weblate. Its `fires` check passes; only `clears` fails.

## The 14 cases, attributed (#252 duty)

Each of the 14 mapped to a memory-side change or an A2-held hit, from the
frozen lowering sessions, the per-case records, and the A2 adjudication
sheets.

| case | class | role | fires at vulnerable (#267) | attribution |
|---|---|---|---|---|
| pretix-ghsa-pmjj-h5jm-vxh4 | ii | required win | yes | lowered row `src.pretix.api.views.* requires_object_scope src.pretix.api.auth.*` (#248 corpus); the advisory routes name `OrganizerExportersViewSet.download` / `EventExportersViewSet.download`, which the ViewSets do not define, and the #254 INHERITS lookup resolves the defining node `ExportersMixin.download`, loading the `CachedFile` unguarded; at the fixing SHA the handler binds `cf.allowed_for_session` and no longer fires |
| weblate-ghsa-3pmh-24wp-xpf4 | ii | required win | yes | #248's row (`weblate.trans.views.*`) matched no handler on the advisory surface, so #255 re-lowered weblate at the same SHA with the anchored row `weblate.api.views.* requires_object_scope weblate.auth.*`; it binds `UserViewSet.notifications` / `notifications_details`, which fire at the vulnerable SHA and clear at the fixing SHA |
| askbot-devel-ghsa-r2jv-fwfr-4j8c | ii | A2-held | yes | A2-held hit (`records/adjudication/a2-free/…`); 5 avatar handlers fire |
| langflow-ghsa-8c4j-f57c-35cf | ii | A2-held | yes | A2-held hit; `flows.read_flow` / `update_flow` / `delete_flow` fire |
| open-webui-ghsa-26g9-27vm-x3q8 | ii | A2-held | yes | A2-held hit; 7 `routers/files` handlers fire |
| tandoor-ghsa-v8x3-w674-55p5 | ii | A2-held | yes | A2-held hit; fire sibling-carried, `clears` red (section above) |
| aegra-aegra-ghsa-m98r-6667-4wq7 | i | A2-held | yes | A2-held hit |
| khoj-ghsa-6whj-7qmg-86qj | i | A2-held | no | A2-held hit; 3 candidate files, no violation |
| langflow-ghsa-rf6x-r45m-xv3w | i | A2-held | yes | A2-held hit |
| plane-ghsa-qw87-v5w3-6vxx | i | A2-held | no | A2-held hit; 11 candidate files, no violation |
| wagtail-ghsa-4qvv-g3vr-m348 | i | A2-held | yes | A2-held hit |
| wger-ghsa-g8gc-6c4h-jg86 | i | A2-held | yes | A2-held hit |
| mlflow-ghsa-46r5-x6jq-v8g6 | iii | A2-held | no | A2-held hit; 0 candidate files, no row binds a handler |
| wger-ghsa-42cr-w2gr-m54q | iii | A2-held | yes | A2-held hit |

The two required wins trace to memory-side changes only: a frozen lowered row
plus the #254 INHERITS resolution for pretix, and the #255 re-anchored row for
weblate. No reader-side change enters either.

## No-slack collateral note (#252 duty)

14/18 means holding A2's twelve and winning pretix and weblate. A single fire
regression on a held case drops the total below target unless one of the four
class-(i) cases A2 missed (indico, langflow-7grx, weblate-mpf5, weblate-wppc)
flips reader-side.

Against the #267 record there is no regression: every held case reports the
same vulnerable fire as the frozen #259 run. Per case, fire at vulnerable,
#259 → #267:

| held case | class | fire, #259 → #267 |
|---|---|---|
| aegra-aegra-ghsa-m98r-6667-4wq7 | i | yes → yes |
| khoj-ghsa-6whj-7qmg-86qj | i | no → no |
| langflow-ghsa-rf6x-r45m-xv3w | i | yes → yes |
| plane-ghsa-qw87-v5w3-6vxx | i | no → no |
| wagtail-ghsa-4qvv-g3vr-m348 | i | yes → yes |
| wger-ghsa-g8gc-6c4h-jg86 | i | yes → yes |
| askbot-devel-ghsa-r2jv-fwfr-4j8c | ii | yes → yes |
| langflow-ghsa-8c4j-f57c-35cf | ii | yes → yes |
| open-webui-ghsa-26g9-27vm-x3q8 | ii | yes → yes |
| tandoor-ghsa-v8x3-w674-55p5 | ii | yes → yes |
| mlflow-ghsa-46r5-x6jq-v8g6 | iii | no → no |
| wger-ghsa-42cr-w2gr-m54q | iii | yes → yes |

Three held cases are detect-silent at the vulnerable SHA: khoj, plane and
mlflow. They were silent in #259 as well, so this is not a regression, but the
reader arm must hold them without detect-side support.

## Recall arithmetic, per class

Which of the 14 the detect side supports, read from
`records/a6_gate_267/summary.json` (`vulnerable.fire` per case) against A2's
held set:

| class | of the 14 | detect-supported | not supported |
|---|---:|---|---|
| (i) | 6 | 4: aegra, langflow-rf6x, wagtail-4qvv, wger-g8gc | khoj, plane |
| (ii) | 6 | 6: askbot, langflow-8c4j, open-webui, tandoor, pretix, weblate-3pmh | none |
| (iii) | 2 | 1: wger-42cr | mlflow |
| total | 14 | 11 | 3 |

The detect side supports 11 of the 14. The 14/18 itself is reader-side recall
and stays with the reader arm (Stage 1), as recorded in the frozen #259
comment; this note does not claim it.

## Verdict applied

#249 registered "fires 6/6, clears 6/6" on class (ii). Observed under the
amendment: fires 6/6 PASS, clears 5/6 FAIL, tandoor alone. The gate verdict is
FAIL and is recorded as such in `records/a6_gate_267/summary.json`. The #252
target's two load-bearing wins have fire and clear evidence. #259 closes on
this note and the #267 record.