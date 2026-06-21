from __future__ import annotations

from fastapi import APIRouter

from api.db.neo4j import check_neo4j_health
from api.db.postgres import check_postgres_health


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def backend_health() -> dict[str, str]:
    return {"status": "ok", "service": "drug-project-api"}


@router.get("/db/health")
def db_health() -> dict[str, object]:
    postgres: dict[str, object]
    neo4j: dict[str, object]
    warnings: list[str] = []

    try:
        postgres = check_postgres_health()
    except Exception as exc:
        postgres = {"status": "error", "message": "PostgreSQL unavailable", "detail": exc.__class__.__name__}
        warnings.append("PostgreSQL unavailable")

    try:
        neo4j = check_neo4j_health()
    except Exception as exc:
        neo4j = {"status": "error", "message": "Neo4j unavailable", "detail": exc.__class__.__name__}
        warnings.append("Neo4j unavailable")

    status = "ok"
    if postgres.get("status") != "ok" or neo4j.get("status") != "ok":
        status = "degraded"

    return {
        "status": status,
        "backend": "ok",
        "postgres": postgres,
        "neo4j": neo4j,
        "warnings": warnings,
    }

