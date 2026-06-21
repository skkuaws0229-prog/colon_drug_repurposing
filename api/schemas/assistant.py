from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AssistantAskRequest(BaseModel):
    question: str
    drug_key: Optional[str] = None
    mode: str = "graph_context"


class AssistantAskResponse(BaseModel):
    disease: str
    intent: str
    answer: str
    evidence: List[Dict[str, Any]]
    warnings: List[str]
    context_counts: Dict[str, int]

