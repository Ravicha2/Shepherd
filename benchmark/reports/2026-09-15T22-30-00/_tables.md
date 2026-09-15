# benchmark/reports/2026-09-15T22-30-00

## python-tuf
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 3 | 0 | 1 | 2 | 2 | 0 | 1 | 2 | 6 | 0 | 0 | 41 | 0 | 0 |
| node_on 2 | 3 | 0 | 1 | 3 | 2 | 0 | 1 | 3 | 6 | 0 | 0 | 28 | 6 | 0 |
| node_on 3 | 3 | 0 | 1 | 3 | 2 | 0 | 1 | 3 | 6 | 0 | 0 | 28 | 6 | 0 |
| node_off 1 | 3 | 0 | 1 | 2 | 0 | 0 | 3 | 2 | 6 | 0 | 0 | 12 | 0 | 0 |
| node_off 2 | 3 | 0 | 1 | 2 | 0 | 0 | 3 | 2 | 6 | 0 | 0 | 12 | 0 | 0 |
| node_off 3 | 3 | 0 | 1 | 2 | 0 | 0 | 3 | 2 | 6 | 0 | 0 | 12 | 0 | 0 |

noise floor (node_on run-to-run, 3 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 3.00 | 3.00 | +0.00 | +0/+0/+0 |  |
| ing_partial | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| ing_miss | 0 | 1.00 | 1.00 | +0.00 | +0/+0/+0 |  |
| ing_fp | 1 | 2.67 | 2.00 | +0.67 | +0/+1/+1 |  |
| cls_A_matched | 0 | 2.00 | 0.00 | +2.00 | +1/+1/+1 | EFFECT |
| cls_A_fp | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| cls_BC_matched | 0 | 1.00 | 3.00 | -2.00 | -1/-1/-1 | EFFECT |
| cls_BC_fp | 1 | 2.67 | 2.00 | +0.67 | +0/+1/+1 |  |
| det_exact | 0 | 6.00 | 6.00 | +0.00 | +0/+0/+0 |  |
| det_partial | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_miss | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| fires_structural | 13 | 32.33 | 12.00 | +20.33 | +1/+1/+1 | EFFECT |
| fires_merge_mech | 6 | 4.00 | 0.00 | +4.00 | +0/+1/+1 |  |
| fires_arm_candidates | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |

decision: KEEP (gold-matching load moved beyond floor)

## flowkit
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 4 | 2 | 49 | 0 | 20 | 4 | 29 | 0 | 0 | 12 | 13 | 37 | 0 |
| node_on 2 | 0 | 4 | 2 | 46 | 0 | 17 | 4 | 29 | 0 | 0 | 12 | 13 | 35 | 0 |
| node_on 3 | 0 | 4 | 2 | 46 | 0 | 17 | 4 | 29 | 0 | 0 | 12 | 13 | 35 | 0 |
| node_off 1 | 0 | 3 | 3 | 27 | 0 | 7 | 3 | 20 | 0 | 0 | 12 | 13 | 29 | 0 |
| node_off 2 | 0 | 3 | 3 | 28 | 0 | 7 | 3 | 21 | 0 | 0 | 12 | 13 | 29 | 0 |
| node_off 3 | 0 | 3 | 3 | 27 | 0 | 7 | 3 | 20 | 0 | 0 | 12 | 13 | 29 | 0 |

noise floor (node_on run-to-run, 3 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| ing_partial | 0 | 4.00 | 3.00 | +1.00 | +1/+1/+1 | EFFECT |
| ing_miss | 0 | 2.00 | 3.00 | -1.00 | -1/-1/-1 | EFFECT |
| ing_fp | 3 | 47.00 | 27.33 | +19.67 | +1/+1/+1 | EFFECT |
| cls_A_matched | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| cls_A_fp | 3 | 18.00 | 7.00 | +11.00 | +1/+1/+1 | EFFECT |
| cls_BC_matched | 0 | 4.00 | 3.00 | +1.00 | +1/+1/+1 | EFFECT |
| cls_BC_fp | 0 | 29.00 | 20.33 | +8.67 | +1/+1/+1 | EFFECT |
| det_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_partial | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_miss | 0 | 12.00 | 12.00 | +0.00 | +0/+0/+0 |  |
| fires_structural | 0 | 13.00 | 13.00 | +0.00 | +0/+0/+0 |  |
| fires_merge_mech | 2 | 35.67 | 29.00 | +6.67 | +1/+1/+1 | EFFECT |
| fires_arm_candidates | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |

decision: KEEP (gold-matching load moved beyond floor)

## experimenter
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 1 | 3 | 13 | 0 | 0 | 1 | 13 | 0 | 0 | 18 | 13 | 177 | 1 |
| node_on 2 | 0 | 1 | 3 | 14 | 0 | 0 | 1 | 14 | 0 | 0 | 18 | 13 | 183 | 1 |
| node_on 3 | 0 | 1 | 3 | 14 | 0 | 0 | 1 | 14 | 0 | 0 | 18 | 22 | 205 | 1 |
| node_off 1 | 0 | 1 | 3 | 11 | 0 | 0 | 1 | 11 | 0 | 0 | 18 | 4176 | 107 | 3 |
| node_off 2 | 0 | 2 | 2 | 12 | 0 | 0 | 2 | 12 | 0 | 0 | 18 | 4169 | 89 | 4 |
| node_off 3 | 0 | 1 | 3 | 14 | 0 | 0 | 1 | 14 | 0 | 0 | 18 | 25 | 105 | 1 |

noise floor (node_on run-to-run, 3 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| ing_partial | 0 | 1.00 | 1.33 | -0.33 | +0/-1/+0 |  |
| ing_miss | 0 | 3.00 | 2.67 | +0.33 | +0/+1/+0 |  |
| ing_fp | 1 | 13.67 | 12.33 | +1.33 | +1/+1/+0 | EFFECT |
| cls_A_matched | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| cls_A_fp | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| cls_BC_matched | 0 | 1.00 | 1.33 | -0.33 | +0/-1/+0 |  |
| cls_BC_fp | 1 | 13.67 | 12.33 | +1.33 | +1/+1/+0 | EFFECT |
| det_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_partial | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_miss | 0 | 18.00 | 18.00 | +0.00 | +0/+0/+0 |  |
| fires_structural | 9 | 16.00 | 2790.00 | -2774.00 | -1/-1/-1 | EFFECT |
| fires_merge_mech | 28 | 188.33 | 100.33 | +88.00 | +1/+1/+1 | EFFECT |
| fires_arm_candidates | 0 | 1.00 | 2.67 | -1.67 | -1/-1/+0 | EFFECT |

decision: KEEP (gold-matching load moved beyond floor)

## structurizr-python
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 1 | 1 | 7 | 0 | 2 | 1 | 5 | 0 | 0 | 6 | 0 | 10 | 0 |
| node_on 2 | 0 | 1 | 1 | 7 | 0 | 2 | 1 | 5 | 0 | 0 | 6 | 0 | 10 | 0 |
| node_on 3 | 0 | 1 | 1 | 7 | 0 | 2 | 1 | 5 | 0 | 0 | 6 | 0 | 10 | 0 |
| node_off 1 | 0 | 1 | 1 | 8 | 0 | 0 | 1 | 8 | 0 | 0 | 6 | 0 | 10 | 0 |
| node_off 2 | 0 | 1 | 1 | 8 | 0 | 0 | 1 | 8 | 0 | 0 | 6 | 0 | 10 | 0 |
| node_off 3 | 0 | 1 | 1 | 8 | 0 | 0 | 1 | 8 | 0 | 0 | 6 | 0 | 10 | 0 |

noise floor (node_on run-to-run, 3 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| ing_partial | 0 | 1.00 | 1.00 | +0.00 | +0/+0/+0 |  |
| ing_miss | 0 | 1.00 | 1.00 | +0.00 | +0/+0/+0 |  |
| ing_fp | 0 | 7.00 | 8.00 | -1.00 | -1/-1/-1 | EFFECT |
| cls_A_matched | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| cls_A_fp | 0 | 2.00 | 0.00 | +2.00 | +1/+1/+1 | EFFECT |
| cls_BC_matched | 0 | 1.00 | 1.00 | +0.00 | +0/+0/+0 |  |
| cls_BC_fp | 0 | 5.00 | 8.00 | -3.00 | -1/-1/-1 | EFFECT |
| det_exact | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_partial | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| det_miss | 0 | 6.00 | 6.00 | +0.00 | +0/+0/+0 |  |
| fires_structural | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |
| fires_merge_mech | 0 | 10.00 | 10.00 | +0.00 | +0/+0/+0 |  |
| fires_arm_candidates | 0 | 0.00 | 0.00 | +0.00 | +0/+0/+0 |  |

decision: KEEP (gold-matching load moved beyond floor)

