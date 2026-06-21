# Multi-Cancer BRAC Standard Final Status

- generated_at: `2026-05-10T20:57:55.590923+00:00`
- neo4j_connectivity_status: `FAIL`
- neo4j_connectivity_reason: `connectivity_error:{code: Neo.ClientError.Security.Unauthorized} {message: The client is unauthorized due to authentication failure.}`

## Disease Status
### BRCA
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `POSTGRES_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `BLOCKED`

### COAD
- dry_run_validation: `PASS_WITH_WARNINGS`
- safe_for_postgres_execute: `true`
- postgres_status: `COMPLETED_FROM_EXISTING_VALIDATED_REPORT`
- postgres_execute: `NOT_RERUN_ALREADY_COMPLETED`
- neo4j_status: `USE_EXISTING_REPORT_OR_BLOCKED_BY_CURRENT_NEO4J_AUTH`
- restart_generic_detector_warning: `selected_plan_rows=0`
- restart_generic_detector_warning_explanation: `generic BRCA-standard restart detector did not recognize completed legacy COAD artifacts, but prior COAD disease-specific pipeline is already completed.`
- postgres_execute_status: `NOT_RERUN_ALREADY_COMPLETED`
- postgres_validation_status: `COMPLETED_FROM_EXISTING_VALIDATED_REPORT`
- neo4j_write_plan_status: `FAIL`
- neo4j_validation_status: `BLOCKED`
- postgres_completed_row_counts:
  - admet_result: `32`
  - coad_load_audit: `35`
  - drug_candidate_result: `331`
  - drug_candidate_tier: `30`
  - ensemble_metric: `1`
  - external_validation_result: `80`
  - final_candidate_result: `15`
  - model_metric: `45`
  - model_metric_detailed: `43`
  - source_artifact: `2`

### LUAD
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `POSTGRES_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `BLOCKED`

### LIHC
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `SKIPPED_ALREADY_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `BLOCKED`

### STAD
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `SKIPPED_ALREADY_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `PASS`

### PAAD
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `POSTGRES_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `BLOCKED`

### HNSC
- dry_run_validation: `PASS`
- safe_for_postgres_execute: `true`
- postgres_execute_status: `POSTGRES_LOADED`
- postgres_validation_status: `PASS`
- neo4j_write_plan_status: `PASS_WITH_WARNINGS`
- neo4j_validation_status: `BLOCKED`

