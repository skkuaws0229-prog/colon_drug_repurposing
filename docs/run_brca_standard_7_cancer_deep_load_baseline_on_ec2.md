# Run BRCA-Standard 7-Cancer Deep Load Baseline on EC2 (Read-only)

## Scope
- Diseases: `BRCA`, `COAD`, `LUAD`, `LIHC`, `STAD`, `PAAD`, `HNSC`
- Purpose: discover current PostgreSQL/Neo4j loaded state before any real load
- Mode: read-only only (`SELECT`, `MATCH/RETURN`)
- No execute flags, no DB writes

## 1) Copy Script to EC2
Run on local machine:

```powershell
scp -i "<KEY_PATH_TO_PEM>" `
  C:\work\drug-project\scripts\validation\readonly_brca_standard_7_cancer_deep_load_baseline.py `
  ec2-user@<EC2_HOST>:/home/ec2-user/drug-project/scripts/validation/
```

## 2) Prepare EC2 Environment
Run on EC2:

```bash
cd /home/ec2-user/drug-project
source .venv/bin/activate

set -a
source backend/.env
set +a
```

Map `POSTGRES_*` / `DB_*` to `PG*`:

```bash
export PGHOST="${PGHOST:-${POSTGRES_HOST:-${DB_HOST:-}}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-${DB_PORT:-5432}}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-${POSTGRES_DATABASE:-${DB_NAME:-${DATABASE_NAME:-}}}}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-${DB_USER:-}}}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}}"
```

Neo4j env setup:

```bash
export NEO4J_URI="${NEO4J_URI:-}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-${NEO4J_PASSWORD_RUNTIME:-}}"
```

## 3) Run Baseline Script (Read-only)
Without API check:

```bash
python scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py \
  --output-json outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json \
  --output-md docs/brca_standard_7_cancer_deep_load_baseline.md
```

Optional graph API status check:

```bash
python scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py \
  --api-base-url "http://127.0.0.1:8000" \
  --output-json outputs/config_validation/brca_standard_7_cancer_deep_load_baseline.json \
  --output-md docs/brca_standard_7_cancer_deep_load_baseline.md
```

## 4) Safety Guardrails
- Do not pass:
  - `--execute-postgres`
  - `--execute-neo4j`
  - `--execute-all`
- No loader execution in this step
- No PostgreSQL writes
- No Neo4j writes
- No password reset / service restart
