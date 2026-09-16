# benchmark/reports/2026-09-16T23-56-00

## python-tuf
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 4 | 6 | 0 | 0 | 6 | 0 | 0 | 1064 | 0 | 28 | 1 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 0.9 | 81.1 | 7.5 | 0.57 | 237525 | 2177 | 10.0 |

noise floor (node_on run-to-run, 1 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 3.00 | nan | +nan | - |  |
| ing_partial | 0 | 0.00 | nan | +nan | - |  |
| ing_miss | 0 | 1.00 | nan | +nan | - |  |
| ing_fp | 0 | 4.00 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 3.00 | nan | +nan | - |  |
| cls_BC_fp | 0 | 4.00 | nan | +nan | - |  |
| det_exact | 0 | 6.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 6.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 0.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 1064.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 28.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 1.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## flowkit
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 4 | 2 | 45 | 0 | 20 | 4 | 25 | 9 | 0 | 3 | 0 | 0 | 12 | 1721 | 0 | 182 | 17 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 3.8 | 128.3 | 25.8 | 1.98 | 385203 | 6371 | 12.0 |

noise floor (node_on run-to-run, 1 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 0 | 4.00 | nan | +nan | - |  |
| ing_miss | 0 | 2.00 | nan | +nan | - |  |
| ing_fp | 0 | 45.00 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 20.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 4.00 | nan | +nan | - |  |
| cls_BC_fp | 0 | 25.00 | nan | +nan | - |  |
| det_exact | 0 | 9.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 3.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 12.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 1721.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 182.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 17.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## experimenter
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 0 | 4 | 10 | 0 | 0 | 0 | 10 | 0 | 0 | 18 | 0 | 0 | 18 | 0 | 0 | 9 | 163 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 7.1 | 180.1 | 60.5 | 5.50 | 526899 | 3412 | 16.0 |

noise floor (node_on run-to-run, 1 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 0 | 0.00 | nan | +nan | - |  |
| ing_miss | 0 | 4.00 | nan | +nan | - |  |
| ing_fp | 0 | 10.00 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_BC_fp | 0 | 10.00 | nan | +nan | - |  |
| det_exact | 0 | 0.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 18.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 18.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 0.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 9.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 163.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

## structurizr-python
| arm run | ing_exact | ing_partial | ing_miss | ing_fp | cls_A_matched | cls_A_fp | cls_BC_matched | cls_BC_fp | det_exact | det_partial | det_miss | det_pattern_exact | det_pattern_partial | det_pattern_miss | det_diag_overlap | det_stale_gold | fires_structural | fires_merge_mech | fires_arm_candidates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| node_on 1 | 0 | 1 | 1 | 7 | 0 | 4 | 1 | 3 | 4 | 0 | 2 | 0 | 0 | 6 | 60 | 0 | 0 | 6 | 0 |

cost (mean over that arm's runs):
| arm | parse_s | resolve_s | detect_s | case_detect_s | prompt_tok | completion_tok | sessions |
|---|---|---|---|---|---|---|---|
| node_on | 1.2 | 63.0 | 4.5 | 0.51 | 164191 | 2039 | 9.0 |

noise floor (node_on run-to-run, 1 runs) and arm delta:
| metric | floor | mean_on | mean_off | delta | paired signs | effect |
|---|---|---|---|---|---|---|
| ing_exact | 0 | 0.00 | nan | +nan | - |  |
| ing_partial | 0 | 1.00 | nan | +nan | - |  |
| ing_miss | 0 | 1.00 | nan | +nan | - |  |
| ing_fp | 0 | 7.00 | nan | +nan | - |  |
| cls_A_matched | 0 | 0.00 | nan | +nan | - |  |
| cls_A_fp | 0 | 4.00 | nan | +nan | - |  |
| cls_BC_matched | 0 | 1.00 | nan | +nan | - |  |
| cls_BC_fp | 0 | 3.00 | nan | +nan | - |  |
| det_exact | 0 | 4.00 | nan | +nan | - |  |
| det_partial | 0 | 0.00 | nan | +nan | - |  |
| det_miss | 0 | 2.00 | nan | +nan | - |  |
| det_pattern_exact | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_partial | 0 | 0.00 | nan | +nan | - |  |
| det_pattern_miss | 0 | 6.00 | nan | +nan | - |  |
| det_diag_overlap | 0 | 60.00 | nan | +nan | - |  |
| det_stale_gold | 0 | 0.00 | nan | +nan | - |  |
| fires_structural | 0 | 0.00 | nan | +nan | - |  |
| fires_merge_mech | 0 | 6.00 | nan | +nan | - |  |
| fires_arm_candidates | 0 | 0.00 | nan | +nan | - |  |

decision: NO MOVEMENT beyond floor -> prompt/validation work (#146), not tool iteration

