# BRCA FastAPI Backend

## Purpose
Stage 3 query layer for BRCA evidence retrieval.
This API serves BRCA run data from PostgreSQL plus BRCA KG context from Neo4j for downstream consumers.

## Architecture
- Source of truth (structured): PostgreSQL (`Drug` DB)
- Graph context: Neo4j (`neo4j` DB)
- API framework: FastAPI
- Scope fixed:
  - `disease = BRCA`
  - `run_id = BRCA_RELEASE_V1`
- Out of scope:
  - Agentic AI build
  - UI build
  - Other diseases

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

## Run Command
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\api\run_brca_api.ps1
```

## Endpoint List
- `GET /api/health`
- `GET /api/brca/candidates`
- `GET /api/brca/candidates/{drug_id}`
- `GET /api/brca/candidates/{drug_id}/admet`
- `GET /api/brca/candidates/{drug_id}/validation`
- `GET /api/brca/candidates/{drug_id}/kg`
- `GET /api/brca/agent-context/{drug_id}`

## Example Responses
`GET /api/health`
```json
{
  "status": "ok",
  "disease": "BRCA",
  "run_id": "BRCA_RELEASE_V1",
  "postgres_ok": true,
  "neo4j_ok": true
}
```

`GET /api/brca/candidates`
```json
[
  {
    "rank": 1,
    "drug_id": "DBxxxx",
    "drug_name": "ExampleDrug",
    "canonical_smiles": "CCO...",
    "drug_level_score": 0.9123,
    "confidence_grade": "A",
    "final15": true,
    "admet_verdict": "Approved",
    "validation_score": 0.77
  }
]
```

`GET /api/brca/candidates/{drug_id}/kg`
```json
{
  "drug_id": "DBxxxx",
  "drug_name": "ExampleDrug",
  "disease_relationships": [
    {
      "disease": "BRCA",
      "run_id": "BRCA_RELEASE_V1",
      "rank": 1,
      "score": 0.9123,
      "confidence_grade": "A"
    }
  ],
  "genes": ["EGFR", "PIK3CA"],
  "pathways": ["PI3K-AKT signaling pathway"],
  "admet_relationship_summary": [],
  "validation_relationship_summary": []
}
```

## API Smoke Check
```powershell
python .\scripts\api\check_brca_api.py
```

## Troubleshooting
- API does not start:
  - Verify `uvicorn`, `fastapi`, `sqlalchemy`, `psycopg2`, `neo4j` are installed in current Python environment.
- `503 PostgreSQL unavailable`:
  - Check PostgreSQL service and connection values (`localhost:5432`, DB `Drug`).
- `503 Neo4j unavailable`:
  - Check Neo4j is running and Bolt is open on `7687`.
- `404 drug_id not found`:
  - Confirm the `drug_id` exists in `drug_candidate_result` for `BRCA_RELEASE_V1`.
- Empty genes/pathways in KG response:
  - Verify BRCA Neo4j KG load script has been run successfully.
