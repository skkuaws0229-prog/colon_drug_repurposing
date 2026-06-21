from __future__ import annotations

import os
from typing import Any


def _is_select_only(sql: str) -> bool:
    q = (sql or "").strip().lower()
    return q.startswith("select") and all(tok not in q for tok in ["insert ", "update ", "delete ", "drop ", "alter "])


def query_postgres_readonly(disease: str, question: str) -> dict[str, Any]:
    dsn_ready = bool(os.getenv("PGHOST") and os.getenv("PGDATABASE") and os.getenv("PGUSER") and os.getenv("PGPASSWORD"))
    if not dsn_ready:
        return {
            "status": "postgres_unavailable",
            "evidence": [{"type": "postgres_unavailable", "disease": disease, "reason": "env_missing"}],
            "limitations": ["PostgreSQL connection env is not configured for optional read-only query."],
        }

    # Skeleton only: no execution in this stage.
    safe_query_example = "SELECT disease_code, COUNT(*) FROM image_modal_asset WHERE disease_code = %s GROUP BY disease_code"
    if not _is_select_only(safe_query_example):
        return {
            "status": "postgres_unavailable",
            "evidence": [{"type": "postgres_unavailable", "disease": disease, "reason": "query_blocked_non_select"}],
            "limitations": ["Only SELECT is allowed by postgres_tool guardrail."],
        }

    return {
        "status": "postgres_unavailable",
        "evidence": [{"type": "postgres_unavailable", "disease": disease, "reason": "skeleton_no_execution"}],
        "limitations": ["postgres_tool is skeleton-only in this stage; no DB queries executed."],
    }

