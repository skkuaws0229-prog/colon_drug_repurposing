# BRCA Neo4j Knowledge Graph Guide

## Purpose
This workflow builds a Neo4j Knowledge Graph (KG) for BRCA from curated PostgreSQL result tables.
It is designed for graph exploration, downstream querying, and future AI/agent integration.

## Why PostgreSQL Is the Source of Truth
- PostgreSQL already stores validated BRCA run outputs.
- Loading KG from PostgreSQL guarantees consistency with audited tabular results.
- This avoids direct raw S3 coupling and prevents accidental cross-disease ingestion.

## Scope
- disease: `BRCA`
- run_id: `BRCA_RELEASE_V1`
- Source: PostgreSQL tables only
- Not in scope:
  - direct S3 scans
  - CRC/COLON/LUNG/LUAD/STAD
  - FastAPI build
  - Agentic AI build

## Node Labels
- `Disease`
- `Run`
- `Drug`
- `CandidateResult`
- `FinalCandidate`
- `ADMETResult`
- `ValidationResult`
- `Gene`
- `Pathway`
- `Model`
- `Metric`
- `SourceArtifact`

## Relationship Types
- `(:Drug)-[:CANDIDATE_FOR]->(:Disease)`
- `(:Drug)-[:HAS_RANKING]->(:CandidateResult)`
- `(:Drug)-[:SELECTED_AS_FINAL]->(:FinalCandidate)`
- `(:Drug)-[:HAS_ADMET]->(:ADMETResult)`
- `(:Drug)-[:VALIDATED_BY]->(:ValidationResult)`
- `(:Drug)-[:TARGETS]->(:Gene)`
- `(:Gene)-[:ASSOCIATED_WITH]->(:Disease)`
- `(:Gene)-[:INVOLVED_IN]->(:Pathway)`
- `(:Model)-[:HAS_METRIC]->(:Metric)`
- `(:Run)-[:PRODUCED]->(:CandidateResult)`
- `(:Run)-[:USED_SOURCE]->(:SourceArtifact)`

## Environment Variables
PostgreSQL:
- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5432`
- `POSTGRES_DB=Drug`
- `POSTGRES_USER=Drug`
- `POSTGRES_PASSWORD=1234`

Neo4j:
- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=1234`
- `NEO4J_DATABASE=neo4j`

## Scripts
- Loader:
  - `scripts/kg/load_brca_kg_to_neo4j.py`
- Validator:
  - `scripts/kg/check_brca_kg.py`
- PowerShell runner:
  - `scripts/kg/run_brca_kg_load.ps1`

## Run BRCA KG Load in One Command
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\kg\run_brca_kg_load.ps1
```

## Outputs
- KG load report:
  - `outputs/kg_validation/brca_kg_load_report.json`
- KG validation report:
  - `outputs/kg_validation/brca_kg_validation_report.json`

## Rerun Safety
- Loader uses `MERGE` for all key nodes and relationships.
- Constraints are created with `IF NOT EXISTS`.
- Reruns should be idempotent and avoid duplicate graph entities.

## Troubleshooting
- Neo4j not running:
  - Ensure Neo4j service/container is up and healthy.
- Wrong password:
  - Verify `NEO4J_USER`/`NEO4J_PASSWORD`.
- Bolt port `7687` closed:
  - Check local firewall, Neo4j config, and bind/listen address.
- No PostgreSQL data loaded:
  - Confirm BRCA PostgreSQL load completed first (`disease=BRCA`, `run_id=BRCA_RELEASE_V1`).
- Missing target gene/pathway:
  - Some rows may not include target/pathway fields; loader skips missing values gracefully.
- Duplicate nodes:
  - Ensure constraints exist and loader is not manually bypassing `MERGE`.
- Rerun safety with MERGE:
  - Keep current loader logic and constraints; avoid changing `MERGE` keys without schema review.
