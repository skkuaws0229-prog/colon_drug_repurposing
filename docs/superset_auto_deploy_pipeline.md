# Superset Automatic Deploy Pipeline

This guide provides a repeatable deploy pipeline for local Windows + Docker Desktop and GitHub Actions (self-hosted runner).

## What was added
- Local/runner deploy script: `scripts/deploy_superset_pipeline.ps1`
- Existing recovery helper reused: `scripts/run_superset_with_docker_recovery.ps1`
- GitHub Actions workflow: `.github/workflows/deploy-superset-stack.yml`

## Local one-command deploy
```powershell
cd C:\work\drug-project
.\scripts\deploy_superset_pipeline.ps1 `
  -ProjectDir "<repo-root>\superset" `
  -ComposeFile "docker-compose-image-tag.yml"
```

## What the pipeline does
1. `docker compose up -d`
2. If compose fails, run Docker recovery and retry
3. Validate service status via `docker compose ps`
4. Validate PostgreSQL via `pg_isready`
5. Validate Superset via `http://127.0.0.1:8088/health`

## GitHub Actions deploy
Workflow file:
- `.github/workflows/deploy-superset-stack.yml`

Trigger:
1. GitHub repo -> **Actions**
2. Open **Deploy Superset Stack**
3. Click **Run workflow**
4. (Optional) override:
   - `project_dir`
   - `compose_file`

Notes:
- This workflow uses `runs-on: [self-hosted, windows]`.
- Docker Desktop and the Superset project directory must exist on the runner.
- On failure, compose logs are uploaded as an artifact (`superset-deploy-debug`).

## Quick health checks
```powershell
docker compose -f <repo-root>\superset\docker-compose-image-tag.yml ps
docker exec superset_db pg_isready -U superset -d superset
```


