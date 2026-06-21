# COAD PostgreSQL Rollback Test Plan

- execution_mode: POSTGRES_ROLLBACK_TEST_PLAN
- db_persisted: false
- db_writes_committed: false
- writes_to_neo4j: false

## CLI
- required: --postgres-rollback-test
- optional: --limit-approved-candidates N
- optional: --run-id <stable_id>

## Guardrails
- requires approved candidates CSV
- cannot combine with --execute-neo4j
- cannot combine with --execute-all
- transaction policy: ALWAYS ROLLBACK, NEVER COMMIT

## run_id policy
- execute/rollback path uses stable run_id resolver
- explicit --run-id accepted
- fallback: manifest SHA256-derived run_id
- timestamp-only run_id blocked in execute mode

## Behavior
- uses the same PostgreSQL write path as execute-postgres
- opens transaction
- attempts planned row writes
- collects would_insert/would_update/would_skip/would_fail when available
- always rollback
- reports db_persisted=false

## Table Behavior (ON CONFLICT)
- model_metric: dynamic UNIQUE-key upsert path
- model_metric_detailed: dynamic UNIQUE-key upsert path
- drug_candidate_result: dynamic UNIQUE-key upsert path
- drug_candidate_tier: dynamic UNIQUE-key upsert path
- final_candidate_result: dynamic UNIQUE-key upsert path
- external_validation_result: dynamic UNIQUE-key upsert path
- admet_result: dynamic UNIQUE-key upsert path
- ensemble_metric: dynamic UNIQUE-key upsert path
- source_artifact: dynamic UNIQUE-key upsert path
- coad_load_audit: explicit ON CONFLICT (disease, run_id, source_s3_uri, table_name, status)
