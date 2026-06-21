# LUAD PostgreSQL Real Inspection Load Report

- execute_performed: `true`
- PostgreSQL execute status: `POSTGRES_LOADED`
- Neo4j execute: `not run`
- approved_artifact_count: `10`
- attempted_artifact_count: `10`
- loaded_artifact_count: `8`
- skipped_artifact_count: `2`
- failed_artifact_count: `0`
- no_admet_blocked_count: `0`
- already_loaded_artifact_count: `2`

## LUAD Table Counts

- drug_candidate_tier: 60
- final_candidate_result: 224

## Failed Artifacts

- (none)

## Skipped Artifacts

- (none)

## Skipped Already Loaded Artifacts

- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_top15.csv | final_candidate_result | already_loaded_for_disease_and_source_s3_uri | existing_rows=15
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_package/lung_step6_top30_tiered_candidates.csv | drug_candidate_tier | already_loaded_for_disease_and_source_s3_uri | existing_rows=30
