# COAD Empty Plan Diagnostic

- generated_at: `2026-05-10T18:21:59.8518706Z`
- canonical_project_root: `C:\work\drug-project`
- coad_config_path: `C:\work\drug-project\configs\diseases\coad.yaml`
- coad_s3_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`
- postgres_plan_status: `PASS_WITH_WARNINGS`
- approved_artifact_count: `0`
- plan_rows_count: `0`

## Why Plan Is Empty
- Real-file inspection approved count is 0.
- Plan builder includes only `APPROVED_FOR_POSTGRES_LOAD` rows.
- Expected COAD artifacts are currently excluded or downgraded to `NEEDS_REVIEW` / `NOT_COMPACT_RESULT`.

## Stage Counts
- reconcile load_candidates: `5`
- reconcile needs_review: `66`
- inspection approved_for_postgres_load_count: `0`
- inspection needs_review_count: `9`
- inspection not_compact_result_count: `33`

## Expected Artifact Diagnostics

| filename | inventory | candidate_discovery | inspection | included_in_plan |
|---|---|---|---|---|
| 20260428_colon_v2_step4_model_metrics_full_table.csv | DO_NOT_LOAD_EXCLUDED / raw_curated_glue_excluded_current_stage | MISSING | MISSING | False |
| 20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv | NEEDS_REVIEW / compact_result_role_uncertain | NEEDS_REVIEW / compact_result_keywords_present_but_role_uncertain | NEEDS_REVIEW / model_metric_columns_detected | False |
| 20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv | NEEDS_REVIEW / compact_result_role_uncertain | NEEDS_REVIEW / compact_result_keywords_present_but_role_uncertain | NEEDS_REVIEW / model_metric_columns_detected | False |
| 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv | NEEDS_REVIEW / compact_result_role_uncertain | NEEDS_REVIEW / compact_result_keywords_present_but_role_uncertain | NOT_COMPACT_RESULT / no_confident_table_mapping | False |
| 20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json | NEEDS_REVIEW / compact_result_role_uncertain | NEEDS_REVIEW / compact_result_keywords_present_but_role_uncertain | NOT_COMPACT_RESULT / no_confident_table_mapping | False |
| 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | LOAD_CANDIDATE / compact_result_role_confident | LOAD_CANDIDATE / role_pattern_confident_from_brca_coad_mapping | NEEDS_REVIEW / admet_and_drug_columns_detected | False |
| 20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json | LOAD_CANDIDATE / compact_result_role_confident | LOAD_CANDIDATE / role_pattern_confident_from_brca_coad_mapping | NOT_COMPACT_RESULT / no_confident_table_mapping | False |

## Per-File Root Cause Notes
- 20260428_colon_v2_step4_model_metrics_full_table.csv
  - Excluded at reconciliation stage by path/token guardrail.
  - Substring token matching with exclude_folders can over-exclude names containing token-like text (e.g., full_table with token full).
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv
  - Real-file inspection marked NEEDS_REVIEW, so plan builder excludes it.
  - Model metric-like schema is MEDIUM confidence and not auto-approved.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv
  - Real-file inspection marked NEEDS_REVIEW, so plan builder excludes it.
  - Model metric-like schema is MEDIUM confidence and not auto-approved.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv
  - Real-file inspection could not map file to a confident table/role.
  - Column aliases do not match strict key rules used by propose_target.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json
  - Real-file inspection could not map file to a confident table/role.
  - Column aliases do not match strict key rules used by propose_target.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv
  - Real-file inspection marked NEEDS_REVIEW, so plan builder excludes it.
  - ADMET+drug heuristic routes to NEEDS_REVIEW, not APPROVED.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
- 20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json
  - Real-file inspection could not map file to a confident table/role.
  - Column aliases do not match strict key rules used by propose_target.
  - Plan builder includes only decision=APPROVED_FOR_POSTGRES_LOAD; this file was not approved.
