from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    disease: str
    run_id: str
    postgres_ok: bool
    neo4j_ok: bool


class CandidateSummary(BaseModel):
    rank: Optional[int] = None
    drug_id: str
    drug_name: Optional[str] = None
    canonical_smiles: Optional[str] = None
    drug_level_score: Optional[float] = None
    confidence_grade: Optional[str] = None
    final15: bool = False
    admet_verdict: Optional[str] = None
    validation_score: Optional[float] = None


class CandidateDetail(BaseModel):
    candidate: Dict[str, Any]
    tiers: List[Dict[str, Any]]
    final_candidates: List[Dict[str, Any]]
    source_s3_uris: List[str]


class ADMETDetail(BaseModel):
    drug_id: str
    admet_results: List[Dict[str, Any]]


class ValidationDetail(BaseModel):
    drug_id: str
    validation_results: List[Dict[str, Any]]
    metabric_method_scores: List[Dict[str, Any]]


class KGDetail(BaseModel):
    drug_id: str
    drug_name: Optional[str] = None
    disease: str
    candidate_relationship: Optional[Dict[str, Any]] = None
    genes: List[str]
    pathways: List[str]
    admet: Optional[Dict[str, Any]] = None
    validation: List[Dict[str, Any]]
    warnings: List[str]


class AgentContext(BaseModel):
    drug_id: str
    candidate_ranking: Dict[str, Any]
    tier_rationale: List[Dict[str, Any]]
    final15_status: Dict[str, Any]
    admet_result: List[Dict[str, Any]]
    external_validation_result: List[Dict[str, Any]]
    model_metric_summary: List[Dict[str, Any]]
    neo4j_context: Dict[str, Any]
    source_s3_uri_list: List[str]
    warnings_caveats: List[str]
