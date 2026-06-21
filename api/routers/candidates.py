from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.db import postgres_target_label
from api.services.postgres_service import get_candidate_detail, list_candidates, normalize_disease


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


@router.get("/diseases/{disease}/candidates", response_model=List[Dict[str, Any]])
def get_candidates(
    disease: str,
    limit: int = Query(default=50, ge=1, le=1000),
    source: Optional[str] = None,
    final_only: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    try:
        normalized = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return list_candidates(normalized, limit=limit, source=source, final_only=final_only)
    except SQLAlchemyError as exc:
        return postgres_unavailable_response(exc)


@router.get("/diseases/{disease}/candidates/{drug_key}", response_model=Dict[str, Any])
def get_candidate_by_key(disease: str, drug_key: str) -> Dict[str, Any]:
    try:
        normalized = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return get_candidate_detail(normalized, drug_key)
    except SQLAlchemyError as exc:
        return postgres_unavailable_response(exc)
