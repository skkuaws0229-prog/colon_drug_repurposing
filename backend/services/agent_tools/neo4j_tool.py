from __future__ import annotations

import os


def _is_match_return_only(cypher: str) -> bool:
    q = (cypher or "").strip().lower()
    if not q.startswith("match"):
        return False
    if " return " not in f" {q} ":
        return False
    blocked = [" create ", " merge ", " delete ", " set ", " remove ", " drop "]
    return not any(tok in f" {q} " for tok in blocked)


def query_neo4j_readonly(disease: str, question: str) -> dict:
    env_ready = bool(os.getenv("NEO4J_URI") and os.getenv("NEO4J_USER") and os.getenv("NEO4J_PASSWORD"))
    if not env_ready:
        return {
            "status": "neo4j_unavailable",
            "evidence": [{"type": "neo4j_unavailable", "disease": disease, "reason": "env_missing"}],
            "limitations": ["Neo4j env is not configured for optional read-only query."],
        }

    safe_query_example = "MATCH (d:Disease {code:$disease}) RETURN d.code AS code"
    if not _is_match_return_only(safe_query_example):
        return {
            "status": "neo4j_unavailable",
            "evidence": [{"type": "neo4j_unavailable", "disease": disease, "reason": "query_blocked_non_readonly"}],
            "limitations": ["Only MATCH/RETURN is allowed by neo4j_tool guardrail."],
        }

    return {
        "status": "neo4j_unavailable",
        "evidence": [{"type": "neo4j_unavailable", "disease": disease, "reason": "skeleton_no_execution"}],
        "limitations": ["neo4j_tool is skeleton-only in this stage; no graph queries executed."],
    }

