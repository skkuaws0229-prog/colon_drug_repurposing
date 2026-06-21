from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.core.disease_aliases import list_supported_diseases, normalize_disease
from api.db.neo4j import get_graph_summary_by_disease
from api.db.postgres import (
    get_candidate_summary_by_disease,
    get_candidates_contract_by_disease,
    get_final_candidates_contract_by_disease,
)


router = APIRouter(prefix="/api", tags=["diseases"])


@router.get("/diseases")
def get_diseases() -> dict[str, object]:
    diseases = list_supported_diseases()
    return {"diseases": diseases, "count": len(diseases)}


@router.get("/diseases/{disease}/candidates")
def get_disease_candidates(disease: str, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, object]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return get_candidates_contract_by_disease(canonical, limit=limit)
    except Exception as exc:
        return {
            "disease": canonical,
            "count": 0,
            "items": [],
            "warnings": [f"PostgreSQL unavailable: {exc.__class__.__name__}"],
            "diagnostics": {"source": "postgres", "endpoint": "candidates"},
        }


@router.get("/diseases/{disease}/final-candidates")
def get_disease_final_candidates(
    disease: str, limit: int = Query(default=100, ge=1, le=1000)
) -> dict[str, object]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return get_final_candidates_contract_by_disease(canonical, limit=limit)
    except Exception as exc:
        return {
            "disease": canonical,
            "count": 0,
            "items": [],
            "warnings": [f"PostgreSQL unavailable: {exc.__class__.__name__}"],
            "diagnostics": {"source": "postgres", "endpoint": "final-candidates"},
        }


@router.get("/diseases/{disease}/summary")
def get_disease_summary(disease: str) -> dict[str, object]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    warnings: list[str] = []
    postgres_summary: dict[str, object]
    graph_summary: dict[str, object]

    try:
        postgres_summary = get_candidate_summary_by_disease(canonical)
        warnings.extend([str(w) for w in postgres_summary.get("warnings", [])])
    except Exception as exc:
        postgres_summary = {
            "disease": canonical,
            "table_counts": {},
            "warnings": [f"PostgreSQL unavailable: {exc.__class__.__name__}"],
            "status": "PASS_WITH_WARNINGS",
        }
        warnings.extend(postgres_summary["warnings"])

    try:
        graph_summary = get_graph_summary_by_disease(canonical)
        warnings.extend([str(w) for w in graph_summary.get("warnings", [])])
    except Exception as exc:
        graph_summary = {
            "disease": canonical,
            "node_counts": {},
            "relationship_counts": {},
            "status": "PASS_WITH_WARNINGS",
            "warnings": [f"Neo4j unavailable: {exc.__class__.__name__}"],
        }
        warnings.extend(graph_summary["warnings"])

    if (not postgres_summary.get("table_counts")) and (graph_summary.get("status") == "EMPTY"):
        status = "EMPTY"
    elif warnings or "PASS_WITH_WARNINGS" in {postgres_summary.get("status"), graph_summary.get("status")}:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    return {
        "disease": canonical,
        "postgres": postgres_summary,
        "graph": graph_summary,
        "status": status,
        "warnings": warnings,
    }
