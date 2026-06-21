from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy.exc import SQLAlchemyError

from api.db import postgres_target_label
from api.schemas.disease import DiseaseListResponse, DiseaseSummaryResponse
from api.services.neo4j_graph_service import get_graph_summary
from api.services.postgres_service import get_disease_summary_postgres_status, list_diseases, normalize_disease


router = APIRouter()


def postgres_unavailable_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "source": "postgres",
            "message": "PostgreSQL unavailable",
            "detail": f"{exc.__class__.__name__} at {postgres_target_label()}",
            "data": [],
        },
    )


def neo4j_unavailable_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "source": "neo4j",
            "message": "Neo4j unavailable",
            "detail": exc.__class__.__name__,
            "nodes": [],
            "links": [],
        },
    )


@router.get("/diseases", response_model=DiseaseListResponse)
def get_diseases() -> DiseaseListResponse:
    return DiseaseListResponse(diseases=list_diseases())


@router.get("/diseases/{disease}/summary", response_model=DiseaseSummaryResponse)
def get_disease_summary(disease: str) -> DiseaseSummaryResponse:
    try:
        normalized = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    warnings = []
    try:
        pg_summary = get_disease_summary_postgres_status(normalized)
    except SQLAlchemyError as exc:
        return postgres_unavailable_response(exc)

    try:
        graph_summary = get_graph_summary(normalized)
    except (ServiceUnavailable, Neo4jError) as exc:
        return neo4j_unavailable_response(exc)

    warnings.extend(pg_summary.get("warnings", []))
    warnings.extend(graph_summary.get("known_warnings", []))

    statuses = {pg_summary.get("status"), graph_summary.get("graph_status")}
    if "FAIL" in statuses:
        status = "FAIL"
    elif "PASS_WITH_WARNINGS" in statuses or warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    return DiseaseSummaryResponse(
        disease=normalized,
        postgres_table_counts=pg_summary.get("postgres_table_counts", {}),
        neo4j_node_counts=graph_summary.get("node_counts", {}),
        neo4j_relationship_counts=graph_summary.get("relationship_counts", {}),
        status=status,
        warnings=warnings,
    )
