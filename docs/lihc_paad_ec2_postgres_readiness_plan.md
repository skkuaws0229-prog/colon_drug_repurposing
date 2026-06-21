# LIHC/PAAD EC2 PostgreSQL Readiness Plan (No-Write)

- selected loader script: `scripts/load/run_disease_execute_pipeline.py`
- compatibility recommended_next_action: `BLOCKED_NEEDS_SCRIPT_PATCH`
- db_writes_occurred: `false`
- execute_flags_run: `false`

## Files To Copy To EC2

- outputs/config_validation/lihc_approved_candidates.csv
- outputs/config_validation/lihc_approved_candidates.json
- outputs/config_validation/paad_approved_candidates.csv
- outputs/config_validation/paad_approved_candidates.json
- outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json
- outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json
- scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py
- scripts/load/run_disease_execute_pipeline.py
- scripts/load/execute_disease_postgres_from_real_inspection_plan.py

## SCP Commands

```bash
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_approved_candidates.csv ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_approved_candidates.csv
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_approved_candidates.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_approved_candidates.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/paad_approved_candidates.csv ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/paad_approved_candidates.csv
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/paad_approved_candidates.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/paad_approved_candidates.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/load/run_disease_execute_pipeline.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/load/run_disease_execute_pipeline.py
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/load/execute_disease_postgres_from_real_inspection_plan.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/load/execute_disease_postgres_from_real_inspection_plan.py
```

## EC2 Python / .venv Check

```bash
cd /home/ec2-user/drug-project
source .venv/bin/activate
python --version
which python
```

## PostgreSQL Env Loading (No Secret Echo)

```bash
set -a; source backend/.env; set +a
export PGHOST="${PGHOST:-${POSTGRES_HOST:-${DB_HOST:-}}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-${DB_PORT:-5432}}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-${POSTGRES_DATABASE:-${DB_NAME:-${DATABASE_NAME:-}}}}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-${DB_USER:-}}}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}}"
```

## Read-Only Baseline Count Commands (LIHC/PAAD)

```bash
cd /home/ec2-user/drug-project
source .venv/bin/activate
set -a; source backend/.env; set +a
export PGHOST="${PGHOST:-${POSTGRES_HOST:-${DB_HOST:-}}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-${DB_PORT:-5432}}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-${POSTGRES_DATABASE:-${DB_NAME:-${DATABASE_NAME:-}}}}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-${DB_USER:-}}}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}}"
python --version
python scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py --output-json outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json --output-md docs/brca_standard_7_cancer_deep_load_baseline.md
python - <<'PY'\nimport json\nfrom pathlib import Path\np=Path('outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json')\nobj=json.loads(p.read_text(encoding='utf-8'))\nfor d in obj.get('disease_load_status_table', []):\n    if d.get('disease') in {'LIHC','PAAD'}:\n        print(d['disease'], 'candidate=', d.get('postgres_candidate_count'), 'final=', d.get('postgres_final_candidate_count'), 'admet=', d.get('postgres_admet_count'), 'model_metric=', d.get('postgres_model_metric_count'), 'external_validation=', d.get('postgres_external_validation_count'))\nPY
```

## Idempotency / Rollback Command Support

- LIHC idempotency-check-only: not supported
- PAAD idempotency-check-only: not supported
- LIHC rollback-test: not supported
- PAAD rollback-test: not supported

## Warning

- `--execute-postgres` is not allowed yet.
- `--execute-neo4j` is not allowed.
- `--execute-all` is not allowed.
