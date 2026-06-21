# COAD PostgreSQL Execute Readiness Gate (No-Write)

- execution_mode: SIMULATION_ONLY
- command_preview_only: true
- real_postgres_execute_performed: false
- real_neo4j_execute_performed: false
- db_writes_occurred: false

## Approval
- approved_for_postgres_execute: True
- approved_for_neo4j_execute: False
- coad_msi_location: driver_genes

## Checks
- approved_candidates_csv_exists: True
- approved_candidates_row_count: 31
- correct_local_dir_exists: True
- onedrive_path_absent_from_command_preview: True
- run_coad_execute_pipeline_script_exists: True
- executable_python_available: False
- selected_executable_python: none
- postgres_process_env_ready: False
- read_only_postgresql_connection_can_be_tested: False
- target_table_existence_can_be_tested: False
- duplicate_risk_audit_can_be_tested: False

PostgreSQL process env (masked):
- PGHOST: set=False, masked=
- PGPORT: set=False, masked=
- PGDATABASE: set=False, masked=
- PGUSER: set=False, masked=
- PGPASSWORD: set=False, masked=

## Real Execute Gate
- ready_for_real_execute: False

Blockers remaining:
- no executable Python available in current environment
- PostgreSQL process env not loaded
