# RA v2 Manual PostgreSQL Reload Package

- package_status: READY_FOR_MANUAL_HUMAN_CONFIRMATION
- execution_mode: PREVIEW_ONLY_NOT_EXECUTED
- idempotency_check_only: PASS
- rollback_test: PASS
- db_persisted: false
- image_modal_asset_excluded: true
- approved_for_neo4j_execute: false
- neo4j_blocked_until_postgres_v2_reload_validated: true

## Expected RA v2 Counts
- disease_result_artifact: 2
- disease_candidate_result: 22
- disease_admet_result: 23
- disease_model_metric: 1
- disease_validation_result: 20
- disease_evidence_summary: 9
- disease_embedding_artifact_review: 0
- image_modal_asset: 0

## PostgreSQL Cleanup + Reload Command Preview
- PREVIEW_ONLY_NOT_EXECUTED
- python scripts/non_cancer/load_non_cancer_curated_postgres_neo4j.py --disease RA --s3-prefix s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/ --deep-load --no-image --ra-v2-row-level --execute-postgres --run-id RA_V2_ROW_LEVEL_RELOAD_ONCE_<YYYYMMDD> --plan-json outputs/config_validation/ra_v2_real_reload_plan_ec2.json --plan-md docs/ra_v2_real_reload_plan_ec2.md --postgres-report-json outputs/config_validation/ra_v2_real_reload_postgres_report_ec2.json --postgres-report-md docs/ra_v2_real_reload_postgres_report_ec2.md --validation-json outputs/config_validation/ra_v2_real_reload_validation_ec2.json --validation-md docs/ra_v2_real_reload_validation_ec2.md

## Post-Execute Validation Command Preview
- python scripts/non_cancer/load_non_cancer_curated_postgres_neo4j.py --disease RA --s3-prefix s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/ --deep-load --no-image --ra-v2-row-level --idempotency-check-only --run-id RA_V2_ROW_LEVEL_RELOAD_ONCE_<YYYYMMDD> --plan-json outputs/config_validation/ra_v2_post_execute_idempotency_plan_ec2.json --plan-md docs/ra_v2_post_execute_idempotency_plan_ec2.md --validation-json outputs/config_validation/ra_v2_post_execute_idempotency_validation_ec2.json --validation-md docs/ra_v2_post_execute_idempotency_validation_ec2.md
- psql -c "SELECT COUNT(*) FROM disease_candidate_result WHERE disease_code = $$RA$$;"

## Rollback/Restore Notes
- If execute fails, stop and keep Neo4j blocked.
- Re-run rollback-test mode first (non-persistent) before retrying execute.
- Verify RA-scoped counts against expected targets before any Neo4j consideration.
- Keep image modal excluded (do not use --allow-image-modal).

## Safety
- Real cleanup/reload has NOT been executed.
- Human confirmation is required before any real execution.
