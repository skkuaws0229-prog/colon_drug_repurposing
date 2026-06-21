from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

try:
    from services.literature_rag_service import LiteratureRAGService
except ModuleNotFoundError:
    from backend.services.literature_rag_service import LiteratureRAGService


router = APIRouter(prefix="/api/rag", tags=["literature-rag"])


class LiteratureRAGRequest(BaseModel):
    disease: str = Field(..., min_length=1)
    drug_name: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class LiteratureSearchResult(BaseModel):
    score: float
    title: str
    pmid: str
    doi: str
    year: str
    journal: str
    snippet: str
    source: str
    url: str


class LiteratureRAGResponse(BaseModel):
    no_evidence: bool
    query: str
    results: list[LiteratureSearchResult]


class LiteratureAskResponse(BaseModel):
    no_evidence: bool
    answer: str
    evidence_summary: str
    retrieved_documents: list[LiteratureSearchResult]


@router.post("/literature/search", response_model=LiteratureRAGResponse)
def query_literature(payload: LiteratureRAGRequest) -> LiteratureRAGResponse:
    service = LiteratureRAGService()
    result = service.search(
        disease=payload.disease.strip().upper(),
        drug_name=payload.drug_name.strip(),
        question=payload.question.strip(),
        top_k=payload.top_k,
    )

    if result.error:
        if "not found" in result.error.lower():
            raise HTTPException(status_code=503, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    docs = [LiteratureSearchResult(**doc) for doc in result.results]
    return LiteratureRAGResponse(
        no_evidence=result.no_evidence,
        query=result.query,
        results=docs,
    )


@router.post("/literature/ask", response_model=LiteratureAskResponse)
def ask_literature(payload: LiteratureRAGRequest) -> LiteratureAskResponse:
    service = LiteratureRAGService()
    result = service.ask(
        disease=payload.disease.strip().upper(),
        drug_name=payload.drug_name.strip(),
        question=payload.question.strip(),
        top_k=payload.top_k,
    )

    if result.error:
        if "not found" in result.error.lower():
            raise HTTPException(status_code=503, detail=result.error)
        raise HTTPException(status_code=500, detail=result.error)

    docs = [LiteratureSearchResult(**doc) for doc in result.retrieved_documents]
    return LiteratureAskResponse(
        no_evidence=result.no_evidence,
        answer=result.answer,
        evidence_summary=result.evidence_summary,
        retrieved_documents=docs,
    )
