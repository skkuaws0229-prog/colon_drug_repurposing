# COAD PostgreSQL Idempotency / Upsert Safety Audit (No-Write)

- execution_mode: NO_WRITE_CODE_AUDIT
- db_writes_occurred: false
- execute_flags_run: false
- config_validation_status: passed
- coad_msi_location: driver_genes
- biology_snapshot_consistent_with_config: True

## Input Presence
- scripts/load/run_coad_execute_pipeline.py : True
- scripts/load/select_and_load_coad_postgres_neo4j_candidates.py : True
- outputs/config_validation/coad_approved_candidates.csv : False
- outputs/config_validation/coad_approved_candidates.json : False
- outputs/config_validation/coad_ec2_postgres_readonly_readiness_audit.json : False
- docs/coad_ec2_postgres_readonly_readiness_audit.md : False
- outputs/config_validation/coad_s3_pre_execute_approval_report.json : True
- outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.csv : True

## Loader Code Findings
- `run_coad_execute_pipeline.py` performs real PostgreSQL writes inside one transaction and commits/rolls back.
- Row write mode is dynamic: `INSERT ... ON CONFLICT DO UPDATE` only if a complete UNIQUE key is present in row payload; otherwise plain `INSERT`.
- `coad_load_audit` uses explicit upsert by `(disease, run_id, source_s3_uri, table_name, status)`.
- New `run_id` is generated per execute run (`COAD_EXECUTE_<UTC timestamp>`), which breaks replay-idempotency across separate runs.
- `select_and_load_coad_postgres_neo4j_candidates.py` does not execute PostgreSQL writes; it only generates execute plan placeholders.

## Table-by-Table Idempotency Status
- model_metric (from model_metric, approved_rows=1)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, model, metric
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- model_metric_detailed (from model_metric_detailed, approved_rows=1)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, model, split, metric
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- drug_candidate_result (from drug_candidate_result, approved_rows=3)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, drug_id, drug_name, rank
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- drug_candidate_tier (from drug_candidate_tier, approved_rows=1)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, drug_id, drug_name, rank, tier
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- final_candidate_result (from final_candidate_result, approved_rows=1)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, drug_id, drug_name, rank
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- admet_result (from admet_result, approved_rows=3)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, drug_id, drug_name, rank
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- external_validation_result (from external_validation_result, approved_rows=14)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, validation_source, drug_id, drug_name, rank
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- ensemble_metric (from ensemble_metric, approved_rows=1)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, metric
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- source_artifact (from source_artifact, approved_rows=2)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE_IF_UNIQUE_KEY_AVAILABLE_ELSE_INSERT_ONLY
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, artifact_name, artifact_uri
  - same_run_id: LIKELY_UPSERT_UPDATE
  - new_run_id: LIKELY_INSERT_NEW_ROWS
  - duplicate_risk: HIGH
  - status: NOT_SAFE_FOR_IDEMPOTENT_REEXECUTE
- coad_load_audit (from load_audit, approved_rows=4)
  - write_pattern: INSERT_ON_CONFLICT_DO_UPDATE
  - conflict_keys_from_schema: disease, run_id, source_s3_uri, table_name, status
  - same_run_id: UPSERT_UPDATE
  - new_run_id: INSERT_NEW_AUDIT_ROWS_EXPECTED
  - duplicate_risk: MEDIUM
  - status: EXPECTED_APPEND_PER_RUN

## Risk Summary
- duplicate_risk_level: HIGH
- execute_safe: false
- rationale: unique keys include `run_id` in schema; execute path creates a new run_id by default, so reruns can append logically duplicate COAD rows instead of updating prior run rows.

## Required Changes Before Execute
- Add deterministic run_id override for replay (same artifact batch should reuse run_id).
- Or add/choose conflict keys that represent business identity without run_id for COAD replay use-case.
- Add pre-execute duplicate gate: block when existing COAD rows exist and run_id differs unless explicit override flag is set.
- Validate approved manifest schema compatibility before execute (current loader expects decision/target_table_candidate/selected_file/selected_s3_uri/expected_local_path).

## Recommendation
- HOLD_FOR_UPSERT_FIX

## Code References
- scripts/load/run_coad_execute_pipeline.py:65, 597-668, 757-787, 791-817, 1015-1017, 1440
- scripts/load/select_and_load_coad_postgres_neo4j_candidates.py:1333-1352, 1619-1620
- scripts/db/001_create_brca_tables.sql:42-220
- scripts/db/003_create_coad_load_audit.sql:6-18
