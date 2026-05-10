# GitHub Automation Setup

## Runner Types
- GitHub-hosted runners run in GitHub-managed cloud VMs and cannot access services running on your personal/local machine.
- Self-hosted runners run on your own Windows machine and can access local services like `localhost` PostgreSQL/Neo4j.

## Why Two Workflows
- `disease-preflight.yml` is safe for GitHub-hosted runners and only does syntax/config preflight checks.
- `stad-finish-self-hosted.yml` is for real STAD finish execution against local DB/Neo4j and must run on a Windows self-hosted runner.

## Localhost Limitation
- GitHub-hosted runners cannot reach your local `localhost` PostgreSQL/Neo4j.
- Real DB finish pipeline steps requiring local DB connectivity must use the self-hosted workflow.

## Required GitHub Secrets
Configure these repository secrets before using the self-hosted STAD workflow:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

## How To Run Preflight
1. Open **Actions** in GitHub.
2. Select **Disease Pipeline Preflight**.
3. Click **Run workflow**.
4. Choose disease input (`STAD`, `LUAD`, `LIHC`, `PAAD`, `HNSC`, `COAD`, `BRCA`).

## How To Run STAD Self-Hosted Finish
1. Confirm a Windows self-hosted runner is online.
2. Open **Actions** and select **STAD Finish Pipeline Self Hosted**.
3. Click **Run workflow**.
4. Set `confirm` input exactly to `RUN_STAD_FINISH`.

## Safety Warnings
- Never commit secrets or `.env` files.
- Never commit `data_cache`, `outputs`, `raw`, `curated`, `glue`, `reference`, or `shared_inputs`.
- Keep DB/Neo4j execution gated by the finisher script checks.
