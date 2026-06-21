from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    group: str
    properties: Dict[str, Any]


class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]


class GraphSummaryResponse(BaseModel):
    disease: str
    node_counts: Dict[str, int]
    relationship_counts: Dict[str, int]
    graph_status: str
    known_warnings: List[str]


class ForceGraphResponse(BaseModel):
    disease: str
    nodes: List[GraphNode]
    links: List[GraphLink]


class GraphNodeNeighborhoodResponse(BaseModel):
    disease: str
    node_id: str
    center: Optional[GraphNode] = None
    nodes: List[GraphNode]
    links: List[GraphLink]


class DrugGraphContextResponse(BaseModel):
    disease: str
    drug_key: str
    DrugCandidate: List[Dict[str, Any]]
    CandidateScore: List[Dict[str, Any]]
    FinalCandidateEvidence: List[Dict[str, Any]]
    AdmetEvidence: List[Dict[str, Any]]
    ExternalValidationEvidence: List[Dict[str, Any]]
    ModelEvidence: List[Dict[str, Any]]
    EnsembleEvidence: List[Dict[str, Any]]
    SourceArtifact: List[Dict[str, Any]]
    Run: List[Dict[str, Any]]

