# COAD Local Full Profile Readiness Report

- generated_at: 2026-05-05T20:10:37.492336+00:00
- disease: COAD
- local_dir: `C:\work\drug-project\data_cache\final_data\COAD`
- files_scanned: 186

## Required Role Matrix

| role_slot | status | best_candidate_file | reason | issue_type |
|---|---|---|---|---|
| candidate_tiered | missing | `` | no_file_for_required_role | true_missing |
| final_after_admet | missing | `` | no_file_for_required_role | true_missing |
| model_performance_summary | hold | `C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv` | missing_groups:metric/metric_name;metric_value/value/score/spearman/pearson/rmse/mae/r2 | alias_gap_or_schema_mismatch |
| admet_detailed_or_admet_summary | missing | `` | no_file_for_required_role | true_missing |
| reproducibility_or_copied_manifest | missing | `` | no_file_for_required_role | true_missing |

## Final Decision

- COAD is blocked for PostgreSQL dry-run.
- blocked_roles: candidate_tiered, final_after_admet, model_performance_summary, admet_detailed_or_admet_summary, reproducibility_or_copied_manifest

## Notes
- Read-only local profiling only.
- No PostgreSQL writes.
- No Neo4j writes.
