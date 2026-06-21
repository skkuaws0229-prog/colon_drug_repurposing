from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class DiseaseListResponse(BaseModel):
    diseases: List[str]


class DiseaseSummaryResponse(BaseModel):
    disease: str
    postgres_table_counts: Dict[str, int]
    neo4j_node_counts: Dict[str, int]
    neo4j_relationship_counts: Dict[str, int]
    status: str
    warnings: List[str]

