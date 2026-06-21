# COAD PostgreSQL Upsert Fix Plan (No-Write)

- mode: NO_WRITE_PATCH_PLAN
- db_writes_occurred: false
- execute_flags_run: false
- coad_msi_location: driver_genes
- biology_snapshot_consistent_with_config: True

## Baseline
- duplicate_risk_level(before): HIGH
- recommendation(before): HOLD_FOR_UPSERT_FIX
- root_cause: timestamp-derived run_id could change every execute run

## Patch Strategy
1. Add --run-id CLI option for explicit stable run_id.
2. If execute-postgres is requested and --run-id is absent, derive stable run_id from approved candidates manifest SHA256.
3. Block timestamp-style run_id in execute mode.
4. Add --idempotency-check-only no-write preflight to report planned run_id and read-only reuse check.

## Stable run_id format
- COAD_EXECUTE_MANIFEST_SHA256_<16HEX>

## Table Behavior Documentation
- model_metric: INSERT/UPSERT (UNIQUE-key dependent)
- model_metric_detailed: INSERT/UPSERT (UNIQUE-key dependent)
- drug_candidate_result: INSERT/UPSERT (UNIQUE-key dependent)
- drug_candidate_tier: INSERT/UPSERT (UNIQUE-key dependent)
- final_candidate_result: INSERT/UPSERT (UNIQUE-key dependent)
- external_validation_result: INSERT/UPSERT (UNIQUE-key dependent)
- admet_result: INSERT/UPSERT (UNIQUE-key dependent)
- ensemble_metric: INSERT/UPSERT (UNIQUE-key dependent)
- source_artifact: INSERT/UPSERT (UNIQUE-key dependent)
- coad_load_audit: explicit UPSERT by (disease, run_id, source_s3_uri, table_name, status)

## Inputs
- approved manifest rows: 31
- source artifacts: see JSON plan file
