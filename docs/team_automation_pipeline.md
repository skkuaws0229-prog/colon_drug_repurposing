# Team Automation Pipeline (BRCA)

## Purpose
This automation runs the BRCA evidence platform stages:
S3 result artifacts -> PostgreSQL -> Neo4j KG -> FastAPI checks.

## Environment Variables
Set these before running stages:

```powershell
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="Drug"
$env:POSTGRES_USER="Drug"
$env:POSTGRES_PASSWORD="1234"

$env:NEO4J_URI="bolt://127.0.0.1:7687"
$env:NEO4J_USER="neo4j"
$env:NEO4J_PASSWORD="<your-neo4j-password>"
$env:NEO4J_DATABASE="neo4j"

$env:AWS_PROFILE="default"
```

## Stage: postgres
Runs PostgreSQL table/schema prep, BRCA load, and DB validation.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage postgres
```

Expected high-level checks:
- candidate/admet/validation tables populated
- model metrics loaded
- no schema/constraint errors

## Stage: kg
Runs Neo4j BRCA KG ingestion and KG count validation.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage kg
```

Expected high-level checks:
- Disease/Run/Drug/CandidateResult nodes exist
- relationship counts match expected BRCA baseline

## Stage: api
Runs FastAPI query checks and can optionally start the API server.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage api -StartApiServer
```

Common endpoint checks:
- `/api/health`
- `/api/brca/candidates`
- `/api/brca/candidates/{drug_id}`
- `/api/brca/candidates/{drug_id}/kg`

## Secrets Policy
- Never commit real secrets.
- Never hardcode real Neo4j credentials in docs/scripts/config.
- Use environment variables and placeholders such as `<your-neo4j-password>`.
- `.env` is for local use only and must stay untracked.

## Troubleshooting
- PostgreSQL connection fails: verify host/port/user/password and local service status.
- Neo4j auth fails: verify `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.
- API check fails: ensure dependencies are installed and API server is running.
- Port conflicts: free occupied ports or run services on alternate ports.
- Missing AWS access: verify `AWS_PROFILE` and local AWS credential configuration.

## Related Files
- `scripts/run_team_brca_pipeline.ps1`
- `README.md`
- `docs/github_release_checklist.md`

