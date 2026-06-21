# COAD EC2 PostgreSQL Execute Readiness Plan (No-Write)

- execution_mode: EC2_READINESS_ONLY
- real_postgres_execute_performed: false
- real_neo4j_execute_performed: false
- db_writes_occurred: false
- execute_flags_run: false
- human confirmation required before any future write: true
- COAD MSI location: driver_genes

## Local Status Snapshot
- approved candidates row count: 31
- local ready_for_real_execute: False
- local blockers:
- no executable Python available in current environment
- PostgreSQL process env not loaded

## Files To Transfer
- local: C:\work\drug-project\outputs\config_validation\coad_s3_auto_pipeline_20260524T185540Z\coad_approved_candidates.csv
  ec2: /home/ec2-user/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.csv
- local: C:\work\drug-project\outputs\config_validation\coad_s3_auto_pipeline_20260524T185540Z\coad_approved_candidates.json
  ec2: /home/ec2-user/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.json
- local: C:\work\drug-project\outputs\config_validation\coad_s3_pre_execute_approval_report.json
  ec2: /home/ec2-user/drug-project/outputs/config_validation/coad_s3_pre_execute_approval_report.json
- local: C:\work\drug-project\outputs\config_validation\coad_postgres_execute_readiness_gate_v2.json
  ec2: /home/ec2-user/drug-project/outputs/config_validation/coad_postgres_execute_readiness_gate_v2.json
- local: C:\work\drug-project\docs\coad_postgres_execute_readiness_gate_v2.md
  ec2: /home/ec2-user/drug-project/outputs/config_validation/coad_postgres_execute_readiness_gate_v2.md

## SCP Commands
- mkdir -p /home/ec2-user/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z
- scp -i <PEM_PATH> C:/work/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.csv ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.csv
- scp -i <PEM_PATH> C:/work/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.json
- scp -i <PEM_PATH> C:/work/drug-project/outputs/config_validation/coad_s3_pre_execute_approval_report.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/coad_s3_pre_execute_approval_report.json
- scp -i <PEM_PATH> C:/work/drug-project/outputs/config_validation/coad_postgres_execute_readiness_gate_v2.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/coad_postgres_execute_readiness_gate_v2.json
- scp -i <PEM_PATH> C:/work/drug-project/docs/coad_postgres_execute_readiness_gate_v2.md ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/coad_postgres_execute_readiness_gate_v2.md

## EC2 Read-only Verification Commands
### Presence checks
- cd /home/ec2-user/drug-project
- ls -l outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.csv
- ls -l outputs/config_validation/coad_s3_auto_pipeline_20260524T185540Z/coad_approved_candidates.json
- ls -l outputs/config_validation/coad_s3_pre_execute_approval_report.json
- ls -l outputs/config_validation/coad_postgres_execute_readiness_gate_v2.json
- ls -l outputs/config_validation/coad_postgres_execute_readiness_gate_v2.md

### Python/.venv checks
- python3 --version || true
- python --version || true
- py --version || true
- /home/ec2-user/drug-project/.venv/bin/python --version || true
- command -v python3 || true
- command -v python || true

### PostgreSQL env checks (masked)
- for k in PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD; do if [ -n "${!k}" ]; then echo "$k=***set***"; else echo "$k=***unset***"; fi; done
- [ -f /home/ec2-user/drug-project/.env.local ] && echo '.env.local exists' || echo '.env.local missing'
- [ -f /home/ec2-user/drug-project/.env.runtime ] && echo '.env.runtime exists' || echo '.env.runtime missing'
- [ -f /home/ec2-user/drug-project/backend/.env ] && echo 'backend/.env exists' || echo 'backend/.env missing'

### PostgreSQL SELECT 1 (only if env loaded)
- if [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGDATABASE" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then psql -t -A -c 'select 1;' ; else echo 'SKIP: PG env not fully loaded'; fi
- if [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGDATABASE" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then psql -t -A -c 'select current_database(), current_user;' ; else echo 'SKIP: PG env not fully loaded'; fi

### Target table existence checks (read-only)
- if [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGDATABASE" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then psql -t -A -c "select table_name from information_schema.tables where table_schema='public' and table_name in ('drug_candidate_result','admet_result','external_validation_result','final_candidate_result','model_metric','model_metric_detailed','load_audit','source_artifact','drug_candidate_tier','ensemble_metric') order by table_name;" ; else echo 'SKIP: PG env not fully loaded'; fi

### Duplicate-risk audit checks (read-only)
- if [ -n "$PGHOST" ] && [ -n "$PGPORT" ] && [ -n "$PGDATABASE" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then psql -t -A -c "select 'manual_sql_required_for_duplicate_risk';" ; else echo 'SKIP: PG env not fully loaded'; fi

### Explicit no-execute guardrail
- # Do NOT run run_coad_execute_pipeline.py with --execute-postgres
- # Do NOT run any command containing --execute-postgres/--execute-neo4j/--execute-all
