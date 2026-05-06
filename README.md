# BRCA Evidence Graph Pipeline for Drug Repurposing

A reproducible biomedical data engineering pipeline that ingests BRCA drug repurposing outputs from S3 into PostgreSQL, validates structured results, builds a Neo4j Knowledge Graph, and exposes FastAPI endpoints for future Agentic AI explanations.

## Architecture
S3 result artifacts  
-> PostgreSQL Drug DB  
-> Neo4j Knowledge Graph  
-> FastAPI Query Layer  
-> Future Vector DB / Agentic AI / UI

## Current Verified Status
- PostgreSQL load/validation: implemented
- Neo4j KG load/validation: implemented
- FastAPI query layer: implemented
- Multi-cancer expansion: planned/config preparation
- Vector DB/RAG: planned
- Agentic AI: planned
- UI dashboard: planned

## Verified BRCA KG Counts
### Nodes
- Disease: 1
- Run: 1
- Drug: 30
- CandidateResult: 30
- FinalCandidate: 15
- ADMETResult: 30
- ValidationResult: 45
- Gene: 36
- Pathway: 15
- Model: 43
- Metric: 817
- SourceArtifact: 1

### Relationships
- CANDIDATE_FOR: 30
- HAS_RANKING: 30
- SELECTED_AS_FINAL: 15
- HAS_ADMET: 30
- VALIDATED_BY: 45
- TARGETS: 39
- ASSOCIATED_WITH: 36
- INVOLVED_IN: 38
- HAS_METRIC: 817
- PRODUCED: 30
- USED_SOURCE: 1

## Quickstart (Teammates)
```powershell
cd <repo-root>
pip install -r requirements.txt
```

Set env vars:

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
```

Run stages:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage postgres
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage kg
powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage api -StartApiServer
```

## Recruiter-Friendly Technical Highlights
- S3-based artifact ingestion
- PostgreSQL normalized evidence layer
- idempotent loading and validation
- model metric normalization using phase/family/source_model_dir
- Neo4j Knowledge Graph construction
- FastAPI evidence API
- teammate-friendly PowerShell automation
- ready for multi-cancer expansion

## Repository Scope
- PostgreSQL BRCA loader and validator
- Neo4j BRCA KG loader and validator
- FastAPI BRCA query layer
- team automation runner (`scripts/run_team_brca_pipeline.ps1`)
- release/readiness documentation in `docs/`

## Optional Dependency Note
RDKit is intentionally not pinned in `requirements.txt` yet. If molecular structure image generation is added later, install RDKit separately via Conda.

## Team Automation Docs
See `docs/team_automation_pipeline.md` for stage-by-stage operations, env setup, and troubleshooting.

