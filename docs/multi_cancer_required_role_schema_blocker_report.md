# Multi-Cancer Required Role & Schema Blocker Report

- generated_at: 2026-05-05T19:36:30.311581+00:00
- scope: post-filename-heuristic update, read-only blocker analysis
- safety: no PostgreSQL writes, no Neo4j writes, no YAML edits, no validator edits in this task

## 1. Disease-level current status

| disease | current confidence | current score | previous score | promoted/demoted/unchanged | main remaining blocker |
|---|---|---:|---:|---|---|
| COAD | medium | 75.44 | 65.44 | unchanged | column_alias_gap |
| LUNG | medium | 73.89 | 63.89 | unchanged | column_alias_gap |
| LIHC | medium | 72.86 | 68.57 | unchanged | missing_required_role |
| PAAD | medium | 76.50 | 73.17 | unchanged | missing_required_role |
| HNSC | medium | 67.88 | 56.62 | promoted | missing_required_role |
| STAD | medium | 77.50 | 77.50 | unchanged | missing_required_role |

## 2. Required role matrix

| disease | required role | status | best candidate file | score | reason not included | missing required columns | issue type |
|---|---|---|---|---:|---|---|---|
| COAD | admet_detailed_or_admet_summary | include | 20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json | 100 | - | - | resolved_include |
| COAD | candidate_tiered | include | 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv | 85 | - | tier/candidate_tier;score/final_score/ensemble_score/model_score | resolved_include |
| COAD | final_after_admet | hold | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | 55 | needs_manual_review | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | alias_gap |
| COAD | model_performance_summary | include | 20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv | 85 | - | metric/metric_name;metric_value/value/score | resolved_include |
| COAD | reproducibility_manifest_or_copied_source_manifest | include | S3_REPRODUCTION_MANIFEST.md | 98 | - | - | resolved_include |
| HNSC | admet_detailed_or_admet_summary | include | hnsc_admet_candidate_gate.csv | 70 | - | - | resolved_include |
| HNSC | candidate_tiered | include | top30_tier1234_fixed_hnsc.csv | 85 | - | score/final_score/ensemble_score/model_score | resolved_include |
| HNSC | final_after_admet | include | hnsc_admet_filtered_top15.csv | 85 | - | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | resolved_include |
| HNSC | model_performance_summary | include | metrics_summary.json | 85 | - | model/model_name/model_family;metric/metric_name;metric_value/value/score;split/phase/fold/cv_type | resolved_include |
| HNSC | reproducibility_manifest_or_copied_source_manifest | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| LIHC | admet_detailed_or_admet_summary | include | stad_admet_summary.json | 80 | - | - | resolved_include |
| LIHC | candidate_tiered | include | lihc_v2_top30_dedup_tiered.csv | 85 | - | tier/candidate_tier;score/final_score/ensemble_score/model_score | resolved_include |
| LIHC | final_after_admet | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| LIHC | model_performance_summary | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| LIHC | reproducibility_manifest_or_copied_source_manifest | include | REPRO_MANIFEST.json | 98 | - | - | resolved_include |
| LUNG | admet_detailed_or_admet_summary | include | lung_admet_summary.json | 100 | - | - | resolved_include |
| LUNG | candidate_tiered | include | lung_step6_top30_tiered_candidates.csv | 85 | - | rank/final_rank/candidate_rank;score/final_score/ensemble_score/model_score | resolved_include |
| LUNG | final_after_admet | hold | lung_all_admet_pass.csv | 55 | needs_manual_review | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | alias_gap |
| LUNG | model_performance_summary | include | lung_32_metrics_checklist.csv | 85 | - | model/model_name/model_family;metric_value/value/score;split/phase/fold/cv_type | resolved_include |
| LUNG | reproducibility_manifest_or_copied_source_manifest | include | lung_s3_upload_manifest_20260429.md | 98 | - | - | resolved_include |
| PAAD | admet_detailed_or_admet_summary | include | admet_summary_independent.json | 100 | - | - | resolved_include |
| PAAD | candidate_tiered | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| PAAD | final_after_admet | include | step7_top15_pdac_admet_with_vt.csv | 85 | - | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | resolved_include |
| PAAD | model_performance_summary | hold | dl_metrics_summary.csv | 65 | needs_manual_review | metric/metric_name;metric_value/value/score;split/phase/fold/cv_type | schema_mismatch |
| PAAD | reproducibility_manifest_or_copied_source_manifest | include | paad_raw_source_manifest_20260421.json | 78 | - | - | resolved_include |
| STAD | admet_detailed_or_admet_summary | include | stad_admet_summary.json | 100 | - | - | resolved_include |
| STAD | candidate_tiered | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| STAD | final_after_admet | hold | stad_drugs_with_admet.csv | 55 | needs_manual_review | final_score/score/ensemble_score;admet_score/admet_risk/pass_fail/admet_pass | alias_gap |
| STAD | model_performance_summary | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |
| STAD | reproducibility_manifest_or_copied_source_manifest | missing | - | 0 | no_file_mapped_to_required_role | - | true_missing |

## 3. Schema alias candidates (manual confirmation required)

| disease | file | role slot | observed column/pattern | proposed target | why |
|---|---|---|---|---|---|
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | final_after_admet | prediction_or_selection_score | final_score | final selection score proxy likely |
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | final_after_admet | admet_status_like | admet_pass | ADMET decision semantic likely |
| LUNG | lung_all_admet_pass.csv | final_after_admet | prediction_or_selection_score | final_score | final selection score proxy likely |
| LUNG | lung_all_admet_pass.csv | final_after_admet | admet_status_like | admet_pass | ADMET decision semantic likely |
| STAD | stad_drugs_with_admet.csv | final_after_admet | prediction_or_selection_score | final_score | final selection score proxy likely |
| STAD | stad_drugs_with_admet.csv | final_after_admet | admet_status_like | admet_pass | ADMET decision semantic likely |

## 4. Files that must remain hold (manual review)

Top manual-review priorities are required-role-related holds first.

| disease | file | inferred role | expected role | score | review reason |
|---|---|---|---|---:|---|
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | - | final_after_admet | 55 | admet_final_distinction_unclear |
| HNSC | HNSC_top30_tier1234_fixed_20260428.md | candidate_tiered | - | 63 | likely_intermediate |
| LIHC | prepare_lihc_v2_top30_dedup_tiered.py | candidate_tiered | - | 56 | likely_intermediate |
| LUNG | lung_step6_top30_tiered_candidates.json | candidate_tiered | - | 65 | required_columns_absent |
| LUNG | lung_all_admet_pass.csv | - | final_after_admet | 55 | admet_final_distinction_unclear |
| PAAD | admet_detailed_candidates.csv | admet_detailed | - | 67 | score_meaning_unclear |
| PAAD | admet_preprocessing_summary_20260406.md | admet_summary | - | 65 | likely_intermediate |
| PAAD | dl_metrics_summary.csv | model_performance_summary | - | 65 | required_columns_absent |
| PAAD | ml_metrics_summary.csv | model_performance_summary | - | 65 | required_columns_absent |
| STAD | stad_drugs_with_admet.csv | - | final_after_admet | 55 | admet_final_distinction_unclear |
| COAD | 20260428_colon_v2_step6_external_validation_asset_manifest.json | - | ensemble_source_manifest | 68 | score_meaning_unclear |
| COAD | colon_top30_drugs_ensemble.csv | - | external_validation_scored | 63 | score_meaning_unclear |
| COAD | 20260428_colon_v2_step4_model_metrics_full_table.csv | - | model_performance_detailed | 55 | required_columns_absent |
| COAD | 20260428_colon_v2_colon_clinical_trials_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_comprehensive_drug_scores.csv | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_comprehensive_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_cosmic_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_cptac_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_geo_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_prism_validation_results.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_top30_drugs_ensemble.csv | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_colon_top50_drugs_ensemble.csv | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_pipeline_report_step6_step7.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_reproduction_protocol.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step4_2abc_15models_metrics_preview.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_execution_gate_decision.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_execution_gate_decision.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_external_validation_clinicaltrials_api_snapshot.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_external_validation_gap_report.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_external_validation_path_mapping.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_external_validation_surrogate_compound_matching_protocol.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_prism_compound_name_lookup_report.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_readiness_gate_report.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step6_readiness_gate_report.md | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step7_crc_clinical_tier_seed.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json | - | - | 35 | role_ambiguous |
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_no_admet_tier_sort_only.csv | - | - | 35 | role_ambiguous |
| COAD | GPL570_probe_to_gene.json | - | - | 35 | role_ambiguous |
| COAD | README.md | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_all_studies.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_001.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_002.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_003.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_004.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_005.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_006.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_007.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_008.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_009.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_010.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_011.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_012.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_013.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_014.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_015.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_016.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_017.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_018.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_019.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_020.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_021.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_022.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_023.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_024.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_025.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_026.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_027.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_028.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_029.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_030.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_031.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_032.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_033.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_034.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_035.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_036.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_037.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_038.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_039.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_040.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_041.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_042.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_043.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_044.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_045.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_046.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_047.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_048.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_049.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_050.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_051.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_052.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_053.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_054.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_055.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_056.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_057.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_058.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_059.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_060.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_061.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_062.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_063.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_064.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_065.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_066.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_067.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_068.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_069.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_070.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_071.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_072.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_073.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_074.json | - | - | 35 | role_ambiguous |
| COAD | clinicaltrials_colorectal_cancer_page_075.json | - | - | 35 | role_ambiguous |

## 5. Revalidation priority

| rank | disease | likelihood signal | missing required roles | held required roles | alias-gap slots |
|---:|---|---:|---:|---:|---:|
| 1 | COAD | 74.44 | 0 | 1 | 1 |
| 2 | LUNG | 72.89 | 0 | 1 | 1 |
| 3 | PAAD | 60.50 | 1 | 1 | 0 |
| 4 | HNSC | 55.88 | 1 | 0 | 0 |
| 5 | LIHC | 48.86 | 2 | 0 | 0 |
| 6 | STAD | 40.50 | 3 | 1 | 1 |

## 6. Final decision

- No disease is ready for PostgreSQL dry-run yet.
- Reason: no disease has reached high confidence and required-role blockers (missing/hold with schema issues) remain.
- Non-BRCA DB loading remains blocked.
