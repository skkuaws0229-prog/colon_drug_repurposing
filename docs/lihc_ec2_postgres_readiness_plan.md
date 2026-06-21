# LIHC EC2 PostgreSQL Readiness Plan (No-Write)

- disease: `LIHC`
- selected_loader_script: `scripts/load/run_disease_execute_pipeline.py`
- LIHC approved row count: `8`
- ready_for_ec2_readiness_check: `true`
- execute_flags_run: `false`
- db_writes_occurred: `false`

## Files To Copy

- outputs/config_validation/lihc_approved_candidates.csv
- outputs/config_validation/lihc_approved_candidates.json
- outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json
- outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json
- scripts/load/run_disease_execute_pipeline.py
- scripts/load/execute_disease_postgres_from_real_inspection_plan.py
- scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py
- outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json

## SCP Commands

```bash
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_approved_candidates.csv ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_approved_candidates.csv
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_approved_candidates.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_approved_candidates.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_paad_postgres_loader_compatibility_report.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_paad_approved_candidates_manifest_summary.json
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/load/run_disease_execute_pipeline.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/load/run_disease_execute_pipeline.py
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/load/execute_disease_postgres_from_real_inspection_plan.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/load/execute_disease_postgres_from_real_inspection_plan.py
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py
scp -i "<KEY_PATH_TO_PEM>" C:/work/drug-project/outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json
```

## EC2 Python/.venv Check

```bash
cd /home/ec2-user/drug-project
source .venv/bin/activate
python --version
which python
```

## EC2 Syntax Check

```bash
python -m py_compile scripts/load/run_disease_execute_pipeline.py scripts/load/execute_disease_postgres_from_real_inspection_plan.py scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py
```

## PostgreSQL Env Loading

```bash
set -a; source backend/.env; set +a
export PGHOST="${PGHOST:-${POSTGRES_HOST:-${DB_HOST:-}}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-${DB_PORT:-5432}}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-${POSTGRES_DATABASE:-${DB_NAME:-${DATABASE_NAME:-}}}}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-${DB_USER:-}}}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}}"
```

## LIHC Baseline Read-Only Count

```bash
python scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py --output-json outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json --output-md docs/brca_standard_7_cancer_deep_load_baseline.md
python - <<'PY'\nimport json\nfrom pathlib import Path\np=Path('outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json')\nobj=json.loads(p.read_text(encoding='utf-8'))\nfor d in obj.get('disease_load_status_table', []):\n    if d.get('disease')=='LIHC':\n        print('LIHC baseline candidate=', d.get('postgres_candidate_count'))\n        print('LIHC baseline final=', d.get('postgres_final_candidate_count'))\n        print('LIHC baseline admet=', d.get('postgres_admet_count'))\n        print('LIHC baseline model_metric=', d.get('postgres_model_metric_count'))\n        print('LIHC baseline external_validation=', d.get('postgres_external_validation_count'))\nPY
```

## LIHC Idempotency / Rollback (No-Write)

```bash
python scripts/load/run_disease_execute_pipeline.py --project-root /home/ec2-user/drug-project --disease LIHC --plan-json outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json --approved-candidates-path outputs/config_validation/lihc_approved_candidates.csv --idempotency-check-only
python scripts/load/run_disease_execute_pipeline.py --project-root /home/ec2-user/drug-project --disease LIHC --plan-json outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json --approved-candidates-path outputs/config_validation/lihc_approved_candidates.csv --postgres-rollback-test --limit-approved-candidates 1
python scripts/load/run_disease_execute_pipeline.py --project-root /home/ec2-user/drug-project --disease LIHC --plan-json outputs/config_validation/lihc_postgres_load_plan_from_real_inspection.json --approved-candidates-path outputs/config_validation/lihc_approved_candidates.csv --postgres-rollback-test
```

## Post-Rollback Count Comparison

```bash
python - <<'PY'\nimport json\nfrom pathlib import Path\nbase=Path('outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json')\nrb=Path('outputs/config_validation/lihc_postgres_rollback_test_report.json')\nif not base.exists() or not rb.exists():\n    print('missing baseline or rollback report')\n    raise SystemExit(1)\nobj=json.loads(base.read_text(encoding='utf-8'))\nr=json.loads(rb.read_text(encoding='utf-8'))\nprint('rollback_status=', r.get('postgres_execute_status'))\nprint('db_persisted=', r.get('db_persisted'))\nfor d in obj.get('disease_load_status_table', []):\n    if d.get('disease')=='LIHC':\n        print('baseline candidate=', d.get('postgres_candidate_count'))\n        print('baseline final=', d.get('postgres_final_candidate_count'))\nPY
# rerun baseline to compare post-rollback counts remain unchanged
python scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py --output-json outputs/config_validation/brca_standard_7_cancer_deep_load_baseline_after_rollback.json --output-md docs/brca_standard_7_cancer_deep_load_baseline_after_rollback.md
```

## Warning

- `--execute-postgres` is not allowed yet.
- `--execute-neo4j` is not allowed.
- `--execute-all` is not allowed.
- Do not rerun PAAD execute in this workflow.
