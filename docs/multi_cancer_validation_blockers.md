# Multi-Cancer Validation Blockers

- generated_at: 2026-05-05T19:26:24.568270+00:00
- source: outputs/config_validation/multi_cancer_input_file_validation_report.csv
- source: outputs/config_validation/multi_cancer_disease_confidence_summary.csv
- safety: read-only diagnostic (no DB, no Neo4j, no YAML changes)

## A. Disease-level blocker summary

| disease | current_confidence | current_score | required_roles_present | required_roles_missing | include | hold | exclude | main_blocker_type | recommended_next_action |
|---|---|---:|---|---|---:|---:|---:|---|---|
| COAD | medium | 75.44 | candidate_tiered, model_performance_summary, admet_detailed_or_admet_summary, reproducibility_manifest_or_copied_source_manifest | - | 6 | 358 | 30 | filename-role heuristic is improved only | Improve filename token rules for known project naming variants, then rerun validator. |
| HNSC | medium | 67.88 | candidate_tiered, final_after_admet, model_performance_summary, admet_detailed_or_admet_summary | reproducibility_manifest_or_copied_source_manifest | 9 | 223 | 56 | actual required files are missing | Confirm release package contains required roles and locate missing slot(s): reproducibility_manifest_or_copied_source_manifest. |
| LIHC | medium | 72.86 | candidate_tiered, admet_detailed_or_admet_summary, reproducibility_manifest_or_copied_source_manifest | final_after_admet, model_performance_summary | 5 | 292 | 25 | actual required files are missing | Confirm release package contains required roles and locate missing slot(s): final_after_admet, model_performance_summary. |
| LUNG | medium | 73.89 | candidate_tiered, model_performance_summary, admet_detailed_or_admet_summary, reproducibility_manifest_or_copied_source_manifest | - | 4 | 755 | 2540 | filename-role heuristic is improved only | Improve filename token rules for known project naming variants, then rerun validator. |
| PAAD | medium | 76.50 | final_after_admet, admet_detailed_or_admet_summary, reproducibility_manifest_or_copied_source_manifest | candidate_tiered | 5 | 244 | 267 | actual required files are missing | Confirm release package contains required roles and locate missing slot(s): candidate_tiered. |
| STAD | medium | 77.50 | admet_detailed_or_admet_summary | candidate_tiered, model_performance_summary, reproducibility_manifest_or_copied_source_manifest | 1 | 134 | 855 | actual required files are missing | Confirm release package contains required roles and locate missing slot(s): candidate_tiered, model_performance_summary, reproducibility_manifest_or_copied_source_manifest. |

## B. Required pilot role matrix

| disease | required_role_slot | present_include | present_hold | missing | best_file_candidate | best_file_score | reason_not_include |
|---|---|---|---|---|---|---:|---|
| COAD | admet_detailed_or_admet_summary | yes | no | no | 20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json | 100 | - |
| COAD | candidate_tiered | yes | no | no | 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv | 85 | - |
| COAD | final_after_admet | no | yes | no | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | 55 | needs_manual_review |
| COAD | model_performance_summary | yes | no | no | 20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv | 85 | - |
| COAD | reproducibility_manifest_or_copied_source_manifest | yes | no | no | S3_REPRODUCTION_MANIFEST.md | 98 | - |
| HNSC | admet_detailed_or_admet_summary | yes | no | no | hnsc_admet_candidate_gate.csv | 70 | - |
| HNSC | candidate_tiered | yes | no | no | top30_tier1234_fixed_hnsc.csv | 85 | - |
| HNSC | final_after_admet | yes | no | no | hnsc_admet_filtered_top15.csv | 85 | - |
| HNSC | model_performance_summary | yes | no | no | metrics_summary.json | 85 | - |
| HNSC | reproducibility_manifest_or_copied_source_manifest | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| LIHC | admet_detailed_or_admet_summary | yes | no | no | stad_admet_summary.json | 80 | - |
| LIHC | candidate_tiered | yes | no | no | lihc_v2_top30_dedup_tiered.csv | 85 | - |
| LIHC | final_after_admet | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| LIHC | model_performance_summary | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| LIHC | reproducibility_manifest_or_copied_source_manifest | yes | no | no | REPRO_MANIFEST.json | 98 | - |
| LUNG | admet_detailed_or_admet_summary | yes | no | no | lung_admet_summary.json | 100 | - |
| LUNG | candidate_tiered | yes | no | no | lung_step6_top30_tiered_candidates.csv | 85 | - |
| LUNG | final_after_admet | no | yes | no | lung_all_admet_pass.csv | 55 | needs_manual_review |
| LUNG | model_performance_summary | yes | no | no | lung_32_metrics_checklist.csv | 85 | - |
| LUNG | reproducibility_manifest_or_copied_source_manifest | yes | no | no | lung_s3_upload_manifest_20260429.md | 98 | - |
| PAAD | admet_detailed_or_admet_summary | yes | no | no | admet_summary_independent.json | 100 | - |
| PAAD | candidate_tiered | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| PAAD | final_after_admet | yes | no | no | step7_top15_pdac_admet_with_vt.csv | 85 | - |
| PAAD | model_performance_summary | no | yes | no | ml_metrics_summary.csv | 65 | needs_manual_review |
| PAAD | reproducibility_manifest_or_copied_source_manifest | yes | no | no | paad_raw_source_manifest_20260421.json | 78 | - |
| STAD | admet_detailed_or_admet_summary | yes | no | no | stad_admet_summary.json | 100 | - |
| STAD | candidate_tiered | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| STAD | final_after_admet | no | yes | no | stad_drugs_with_admet.csv | 55 | needs_manual_review |
| STAD | model_performance_summary | no | no | yes | - | 0 | no_file_mapped_to_required_role |
| STAD | reproducibility_manifest_or_copied_source_manifest | no | no | yes | - | 0 | no_file_mapped_to_required_role |

## C. Hold reason summary

| disease | inferred_role | expected_role | role_match | schema_checked | missing_required_columns | risk_flags | decision_reason | hold_file_count |
|---|---|---|---|---|---|---|---|---:|
| LUNG | - | - | none | no | - | low_risk | role_unclear | 452 |
| COAD | - | - | none | no | - | low_risk | role_unclear | 244 |
| LUNG | - | - | none | no | - | unknown_format_risk | role_unclear | 237 |
| LIHC | - | - | none | no | - | unknown_format_risk | role_unclear | 182 |
| PAAD | - | - | none | no | - | low_risk | role_unclear | 132 |
| COAD | - | - | none | no | - | unknown_format_risk | role_unclear | 109 |
| HNSC | - | - | none | no | - | low_risk | role_unclear | 99 |
| PAAD | - | - | none | no | - | unknown_format_risk | role_unclear | 94 |
| LIHC | - | - | none | no | - | low_risk | role_unclear | 92 |
| HNSC | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 85 |
| LUNG | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 58 |
| STAD | - | - | none | no | - | low_risk | role_unclear | 54 |
| STAD | - | - | none | no | - | unknown_format_risk | role_unclear | 51 |
| HNSC | - | - | none | no | - | unknown_format_risk | role_unclear | 28 |
| STAD | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 28 |
| PAAD | model_performance_summary | - | inferred_only | yes | metric/metric_name;metric_value/value/score;split/phase/fold/cv_type | low_risk | needs_manual_review | 12 |
| LIHC | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 10 |
| HNSC | - | external_validation_method_a | expected_only | no | - | moderate_risk_binary_format | needs_manual_review | 4 |
| HNSC | - | external_validation_method_b | expected_only | no | - | moderate_risk_binary_format | needs_manual_review | 4 |
| LIHC | - | candidate_unique | expected_only | yes | - | low_risk | needs_manual_review | 3 |
| LIHC | - | external_validation_scored | expected_only | yes | - | low_risk | needs_manual_review | 2 |
| LUNG | - | external_validation_method_a | expected_only | yes | - | low_risk | needs_manual_review | 2 |
| LUNG | - | external_validation_method_b | expected_only | yes | - | low_risk | needs_manual_review | 2 |
| PAAD | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 2 |
| COAD | - | - | none | no | - | moderate_risk_binary_format | role_unclear | 1 |
| COAD | - | ensemble_source_manifest | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| COAD | - | external_validation_scored | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| COAD | - | final_after_admet | expected_only | yes | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | low_risk | needs_manual_review | 1 |
| COAD | - | model_performance_detailed | expected_only | yes | metric/metric_name;metric_value/value/score | low_risk | needs_manual_review | 1 |
| HNSC | - | candidate_unique | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| HNSC | - | external_validation_scored | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| HNSC | candidate_tiered | - | inferred_only | no | - | low_risk | needs_manual_review | 1 |
| LIHC | - | ensemble_source_manifest | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| LIHC | - | model_performance_detailed | expected_only | yes | metric/metric_name;metric_value/value/score | low_risk | needs_manual_review | 1 |
| LIHC | candidate_tiered | - | inferred_only | no | - | unknown_format_risk | needs_manual_review | 1 |
| LUNG | - | candidate_unique | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| LUNG | - | final_after_admet | expected_only | yes | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | low_risk | needs_manual_review | 1 |
| LUNG | - | model_performance_detailed | expected_only | yes | metric/metric_name;metric_value/value/score | low_risk | needs_manual_review | 1 |
| LUNG | candidate_tiered | - | inferred_only | yes | rank/final_rank/candidate_rank;score/final_score/ensemble_score/model_score | low_risk | needs_manual_review | 1 |
| PAAD | - | candidate_unique | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| PAAD | - | external_validation_method_a | expected_only | yes | - | low_risk | needs_manual_review | 1 |
| PAAD | admet_detailed | - | inferred_only | yes | - | low_risk | needs_manual_review | 1 |
| PAAD | admet_summary | - | inferred_only | yes | - | low_risk | needs_manual_review | 1 |
| STAD | - | final_after_admet | expected_only | yes | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | low_risk | needs_manual_review | 1 |

## D. Promotion candidates

| disease | current_score | current_confidence | promotion_candidate_if |
|---|---:|---|---|
| STAD | 77.50 | medium | actual required files are missing |
| PAAD | 76.50 | medium | actual required files are missing |
| COAD | 75.44 | medium | filename-role heuristic is improved only |
| LUNG | 73.89 | medium | filename-role heuristic is improved only |
| LIHC | 72.86 | medium | actual required files are missing |
| HNSC | 67.88 | medium | actual required files are missing |

## E. Explanation
- COAD was initially selected as a pilot candidate, but current validation still shows medium confidence because required pilot role slots are not all in `present_include` state.
- No non-BRCA disease should be loaded yet.
- STAD and PAAD are closest to high based on current score.
- HNSC remains low and needs manual inspection.
- Next step: adjust validator filename-role heuristics and column alias logic only when this report shows the underlying file is otherwise valid.
