# COAD PostgreSQL Execute Simulation-Only Report

- execution_mode: SIMULATION_ONLY
- real_postgres_execute_performed: false
- real_neo4j_execute_performed: false
- db_writes_occurred: false
- approved_for_postgres_execute: true
- approved_for_neo4j_execute: false
- ready_for_postgres_execute: false

## Reason Not Ready
- approved candidates csv missing
- no executable Python available in current environment
- PostgreSQL process env not loaded

## Environment Snapshot
- approved_candidates_csv_exists: false
- selected_executable_python: none
- postgres_env_ready: false
- command_preview_only: true

## Counts Policy
- no inserted/updated/skipped/failed counts because execution was not performed
- no table counts because execution was not performed

## Safety Gates
- REQUIRE_MANUAL_CONFIRMATION_BEFORE_DB_WRITE: true
- ALLOW_CODEX_TO_EXECUTE_DB_WRITE: false
- ALLOW_AUTOMATION_TO_MUTATE_DB: false

## Biology Guardrail
- coad_msi_location: driver_genes
- coad_msi_preserved: true
