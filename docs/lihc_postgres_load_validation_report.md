# LIHC PostgreSQL Load Validation Report

- generated_at: `2026-05-10T20:05:55.721040+00:00`
- postgres_validation_status: `PASS`
- validation_mode: `POST_EXECUTE`
- execute_performed: `true`
- postgres_execute_status: `SKIPPED_ALREADY_LOADED`
- loaded_artifact_count: `0`
- skipped_artifact_count: `5`
- already_loaded_artifact_count: `5`
- failed_artifact_count: `0`

## Row Counts By Table
- final_candidate_result: 0
- drug_candidate_result: 0
- drug_candidate_tier: 225
- admet_result: 0
- external_validation_result: 0
- model_metric: 0
- model_metric_detailed: 0
- ensemble_metric: 0
- source_artifact: 0
- load_audit: 0
- run_manifest: 0

## Guardrail Checks
- excluded_artifact_load_violations: 0
- no_admet_violations: 0
- non_disease_rows_by_table: {'final_candidate_result': 389, 'drug_candidate_result': 361, 'drug_candidate_tier': 255, 'admet_result': 62, 'external_validation_result': 137, 'model_metric': 260, 'model_metric_detailed': 645, 'ensemble_metric': 10, 'source_artifact': 3, 'load_audit': 0, 'run_manifest': 1}
- missing_source_s3_uri_rows_by_table: {'final_candidate_result': 0, 'drug_candidate_result': 0, 'drug_candidate_tier': 0, 'admet_result': 0, 'external_validation_result': 0, 'model_metric': 0, 'model_metric_detailed': 0, 'ensemble_metric': 0, 'source_artifact': 0, 'load_audit': 0, 'run_manifest': 0}
- no_admet_violations_by_table: {'final_candidate_result': 0, 'admet_result': 0, 'run_manifest': 0}

## Errors
- (none)

## Warnings
- (none)
