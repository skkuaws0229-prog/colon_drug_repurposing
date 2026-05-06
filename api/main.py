from __future__ import annotations

from fastapi import FastAPI

from api.db import SQLAlchemyError, ping as pg_ping
from api.neo4j_client import Neo4jError, ServiceUnavailable, ping as neo4j_ping
from api.routers.brca import DISEASE, RUN_ID, router as brca_router
from api.schemas.brca import HealthResponse


app = FastAPI(title="BRCA Evidence API", version="0.1.0")
app.include_router(brca_router, prefix="/api/brca", tags=["brca"])


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    postgres_ok = False
    neo4j_ok = False

    try:
        postgres_ok = pg_ping()
    except SQLAlchemyError:
        postgres_ok = False

    try:
        neo4j_ok = neo4j_ping()
    except (ServiceUnavailable, Neo4jError):
        neo4j_ok = False

    status = "ok" if postgres_ok and neo4j_ok else "degraded"
    return HealthResponse(
        status=status,
        disease=DISEASE,
        run_id=RUN_ID,
        postgres_ok=postgres_ok,
        neo4j_ok=neo4j_ok,
    )
