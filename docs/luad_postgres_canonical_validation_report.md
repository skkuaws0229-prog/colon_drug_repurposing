# LUAD PostgreSQL Canonical Validation Report

- generated_at: `2026-05-10T11:58:10.531683+00:00`
- disease_code: `LUAD`
- canonical_plan_exists: `true`
- canonical_file_count: `2`
- already_loaded_count: `2`
- newly_loaded_count: `0`
- postgres_validation_status: `PASS`
- reason: `canonical_targets_already_loaded_validation_passed`

## Canonical Source Counts

| target_table | source_s3_uri | row_count |
|---|---|---:|
| final_candidate_result | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_top15.csv | 15 |
| drug_candidate_tier | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_package/lung_step6_top30_tiered_candidates.csv | 30 |

## Guardrails

- disease_code_luad_only: `True`
- no_lung_rows: `True`
- no_laud_rows: `True`
- blocked_source_path_rows: `0`
- no_admet_guardrail_violations: `0`
