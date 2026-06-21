# BRCA PostgreSQL Load Validation Report

- generated_at: `2026-05-10T19:59:22.869895+00:00`
- postgres_validation_status: `PASS`
- validation_mode: `POST_EXECUTE`
- execute_performed: `true`
- postgres_execute_status: `POSTGRES_LOADED`
- loaded_artifact_count: `7`
- skipped_artifact_count: `1`
- already_loaded_artifact_count: `1`
- failed_artifact_count: `0`

## Row Counts By Table
- final_candidate_result: 135
- drug_candidate_result: 30
- drug_candidate_tier: 150
- admet_result: 30
- external_validation_result: 45
- model_metric: 215
- model_metric_detailed: 602
- ensemble_metric: 9
- source_artifact: 1
- load_audit: 0
- run_manifest: 1

## Guardrail Checks
- excluded_artifact_load_violations: 0
- no_admet_violations: 0
- non_disease_rows_by_table: {'final_candidate_result': 45, 'drug_candidate_result': 331, 'drug_candidate_tier': 300, 'admet_result': 32, 'external_validation_result': 92, 'model_metric': 45, 'model_metric_detailed': 43, 'ensemble_metric': 1, 'source_artifact': 2, 'load_audit': 0, 'run_manifest': 0}
- missing_source_s3_uri_rows_by_table: {'final_candidate_result': 0, 'drug_candidate_result': 0, 'drug_candidate_tier': 0, 'admet_result': 0, 'external_validation_result': 0, 'model_metric': 0, 'model_metric_detailed': 0, 'ensemble_metric': 0, 'source_artifact': 0, 'load_audit': 0, 'run_manifest': 0}
- no_admet_violations_by_table: {'final_candidate_result': 0, 'admet_result': 0, 'run_manifest': 0}

## Errors
- (none)

## Warnings
- (none)
