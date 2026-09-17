# benchmark/reports/2026-09-17T20-09-41

## python-tuf
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 3 | 0 | 1 | 1 | 0 | 0 | 3 | 1 | 6 | 0 | 0 | 6 | 0 | 0 | 1064 | 0 | 96 | 0 | 2 |
| node_on 2 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 4 | 6 | 0 | 0 | 6 | 0 | 0 | 1064 | 0 | 40 | 0 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 0.4 | 61.8 | 3.4 | 0.26 | 222524 | 2076 | 10.0 |

noise floor (node_on run-to-run, 2 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 3.00 | nan | +nan | - |  |
| ing_partial | 0 | 0.00 | nan | +nan | - |  |
| ing_miss | 0 | 1.00 | nan | +nan | - |  |
| ing_fp | 3 | 2.50 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 3.00 | nan | +nan | - |  |
| cls_BC_fp | 3 | 2.50 | nan | +nan | - |  |
| det_exact | 0 | 6.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 6.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 0.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 1064.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 56 | 68.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 0.00 | nan | +nan | - |  |
| fires_arm_candidates | 2 | 1.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## flowkit
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 3 | 3 | 14 | 0 | 0 | 3 | 14 | 6 | 0 | 6 | 0 | 0 | 12 | 1379 | 0 | 0 | 24 | 0 |
| node_on 2 | 0 | 4 | 2 | 15 | 0 | 0 | 4 | 15 | 9 | 0 | 3 | 0 | 0 | 12 | 1721 | 0 | 0 | 28 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 3.4 | 126.2 | 17.8 | 1.37 | 405306 | 7418 | 12.0 |

noise floor (node_on run-to-run, 2 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 1 | 3.50 | nan | +nan | - |  |
| ing_miss | 1 | 2.50 | nan | +nan | - |  |
| ing_fp | 1 | 14.50 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 1 | 3.50 | nan | +nan | - |  |
| cls_BC_fp | 1 | 14.50 | nan | +nan | - |  |
| det_exact | 3 | 7.50 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 3 | 4.50 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 12.00 | nan | +nan | - |  |
| det_diag_overlap | 342 | 1550.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 0.00 | nan | +nan | - |  |
| fires_merge_mech | 4 | 26.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## experimenter
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 2 | 2 | 14 | 0 | 0 | 2 | 14 | 1 | 0 | 17 | 0 | 0 | 18 | 733 | 0 | 13 | 131 | 0 |
| node_on 2 | 0 | 1 | 3 | 13 | 0 | 0 | 1 | 13 | 1 | 0 | 17 | 0 | 0 | 18 | 733 | 0 | 13 | 116 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 5.3 | 183.6 | 73.5 | 6.68 | 658174 | 3972 | 16.0 |

noise floor (node_on run-to-run, 2 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 1 | 1.50 | nan | +nan | - |  |
| ing_miss | 1 | 2.50 | nan | +nan | - |  |
| ing_fp | 1 | 13.50 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 1 | 1.50 | nan | +nan | - |  |
| cls_BC_fp | 1 | 13.50 | nan | +nan | - |  |
| det_exact | 0 | 1.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 17.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 18.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 733.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 13.00 | nan | +nan | - |  |
| fires_merge_mech | 15 | 123.50 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## structurizr-python
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 4 | 0 | 2 | 0 | 0 | 6 | 60 | 0 | 0 | 0 | 0 |
| node_on 2 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 4 | 0 | 2 | 0 | 0 | 6 | 60 | 0 | 0 | 0 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 0.5 | 46.3 | 2.1 | 0.24 | 127794 | 2121 | 9.0 |

noise floor (node_on run-to-run, 2 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 0 | 1.00 | nan | +nan | - |  |
| ing_miss | 0 | 1.00 | nan | +nan | - |  |
| ing_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 1.00 | nan | +nan | - |  |
| cls_BC_fp | 0 | 0.00 | nan | +nan | - |  |
| det_exact | 0 | 4.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 2.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 6.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 60.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 0.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 0.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

