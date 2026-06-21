from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

from api.db import fetch_all, fetch_one
from api.services.disease_aliases import get_disease_db_codes, list_supported_diseases, normalize_disease_code


SUPPORTED_DISEASES = tuple(list_supported_diseases())

SUMMARY_TABLES: Sequence[str] = (
    "run_manifest",
    "source_artifact",
    "drug_candidate_result",
    "drug_candidate_tier",
    "final_candidate_result",
    "admet_result",
    "external_validation_result",
    "metabric_method_score",
    "model_metric",
    "model_metric_detailed",
    "ensemble_metric",
    "ensemble_source_manifest",
)

DETAIL_TABLES: Dict[str, str] = {
    "candidate_rows": "drug_candidate_result",
    "tier_rows": "drug_candidate_tier",
    "final_candidate_evidence": "final_candidate_result",
    "admet_rows": "admet_result",
    "external_validation_rows": "external_validation_result",
    "metabric_method_rows": "metabric_method_score",
    "model_metric_rows": "model_metric",
    "model_metric_detailed_rows": "model_metric_detailed",
    "ensemble_metric_rows": "ensemble_metric",
    "ensemble_source_manifest_rows": "ensemble_source_manifest",
    "source_artifact_rows": "source_artifact",
    "run_manifest_rows": "run_manifest",
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def normalize_disease(disease: str) -> str:
    return normalize_disease_code(disease)


def list_diseases() -> List[str]:
    return list_supported_diseases()


def _safe_ident(identifier: str) -> str:
    if not _IDENT_RE.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return identifier


@lru_cache(maxsize=256)
def get_table_columns(table_name: str) -> List[str]:
    table = _safe_ident(table_name)
    rows = fetch_all(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
        ORDER BY ordinal_position
        """,
        {"table_name": table},
    )
    return [str(row["column_name"]) for row in rows]


def table_exists(table_name: str) -> bool:
    return bool(get_table_columns(table_name))


def _column_exists(table_name: str, column_name: str) -> bool:
    return column_name in set(get_table_columns(table_name))


def _disease_where_clause(column_ref: str, disease: str, param_prefix: str = "disease_code") -> tuple[str, Dict[str, Any]]:
    codes = [c.upper() for c in get_disease_db_codes(disease)]
    params: Dict[str, Any] = {}
    placeholders: List[str] = []
    for idx, code in enumerate(codes):
        key = f"{param_prefix}_{idx}"
        placeholders.append(f":{key}")
        params[key] = code
    clause = f"UPPER({column_ref}) IN ({', '.join(placeholders)})"
    return clause, params


def _count_rows(table_name: str, disease: str) -> Optional[int]:
    if not table_exists(table_name):
        return None
    table = _safe_ident(table_name)
    params: Dict[str, Any] = {}
    where_sql = ""
    if _column_exists(table_name, "disease"):
        clause, p = _disease_where_clause("disease", disease, "disease_count")
        where_sql = f" WHERE {clause}"
        params.update(p)
    row = fetch_one(f"SELECT COUNT(*) AS c FROM {table}{where_sql}", params)
    if not row:
        return 0
    return int(row["c"] or 0)


def get_postgres_table_counts(disease: str) -> Dict[str, int]:
    normalized = normalize_disease(disease)
    counts: Dict[str, int] = {}
    for table_name in SUMMARY_TABLES:
        value = _count_rows(table_name, normalized)
        if value is not None:
            counts[table_name] = value
    return counts


def _build_candidate_match_clause(table_name: str) -> str:
    cols = set(get_table_columns(table_name))
    clauses: List[str] = []
    if "drug_id" in cols:
        clauses.append("t.drug_id = :drug_key")
    if "drug_key" in cols:
        clauses.append("t.drug_key = :drug_key")
    if "drug_name" in cols:
        clauses.append("LOWER(COALESCE(t.drug_name, '')) LIKE LOWER(:drug_key_like)")
    if not clauses:
        return "1 = 0"
    return "(" + " OR ".join(clauses) + ")"


def _build_order_clause(table_name: str) -> str:
    cols = set(get_table_columns(table_name))
    order: List[str] = []
    if "rank" in cols:
        order.append("rank ASC")
    if "drug_name" in cols:
        order.append("drug_name ASC")
    if "created_at" in cols:
        order.append("created_at DESC")
    if "id" in cols:
        order.append("id ASC")
    if not order:
        return ""
    return " ORDER BY " + ", ".join(order)


def _canonicalize_disease_field(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if "disease" in item and item["disease"] is not None:
            try:
                item["disease"] = normalize_disease_code(str(item["disease"]))
            except ValueError:
                pass
        out.append(item)
    return out


def get_disease_summary_postgres_status(disease: str) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    counts = get_postgres_table_counts(normalized)
    warnings: List[str] = []
    if not counts:
        warnings.append("No expected PostgreSQL tables were found in schema public.")
    if counts.get("drug_candidate_result", 0) == 0:
        warnings.append("No candidate rows were found in drug_candidate_result.")
    status = "PASS_WITH_WARNINGS" if warnings else "PASS"
    return {"postgres_table_counts": counts, "status": status, "warnings": warnings}


def list_candidates(
    disease: str,
    limit: int = 50,
    source: Optional[str] = None,
    final_only: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    normalized = normalize_disease(disease)
    table_name = "drug_candidate_result"
    if not table_exists(table_name):
        return []

    limit_value = max(1, min(int(limit), 1000))
    where: List[str] = ["1 = 1"]
    params: Dict[str, Any] = {"limit": limit_value}

    if _column_exists(table_name, "disease"):
        clause, p = _disease_where_clause("c.disease", normalized, "disease_candidates")
        where.append(clause)
        params.update(p)
    if source and _column_exists(table_name, "source_s3_uri"):
        where.append("c.source_s3_uri = :source")
        params["source"] = source

    final_table = "final_candidate_result"
    if final_only and table_exists(final_table):
        candidate_cols = set(get_table_columns(table_name))
        final_cols = set(get_table_columns(final_table))
        if "drug_id" in candidate_cols and "drug_id" in final_cols:
            exists_where = ["f.drug_id = c.drug_id"]
            if "disease" in final_cols:
                f_clause, f_params = _disease_where_clause("f.disease", normalized, "disease_final")
                exists_where.append(f_clause)
                params.update(f_params)
            if "run_id" in candidate_cols and "run_id" in final_cols:
                exists_where.append("f.run_id = c.run_id")
            where.append(
                "EXISTS (SELECT 1 FROM final_candidate_result f WHERE " + " AND ".join(exists_where) + ")"
            )

    query = (
        "SELECT c.* FROM drug_candidate_result c"
        f" WHERE {' AND '.join(where)}"
        f"{_build_order_clause(table_name)}"
        " LIMIT :limit"
    )
    return _canonicalize_disease_field(fetch_all(query, params))


def fetch_candidate_table_rows(
    table_name: str,
    disease: str,
    drug_key: str,
    row_limit: int = 300,
) -> List[Dict[str, Any]]:
    normalized = normalize_disease(disease)
    if not table_exists(table_name):
        return []

    where = ["1 = 1"]
    params: Dict[str, Any] = {
        "drug_key": drug_key,
        "drug_key_like": f"%{drug_key}%",
        "row_limit": max(1, min(row_limit, 3000)),
    }

    if _column_exists(table_name, "disease"):
        clause, p = _disease_where_clause("t.disease", normalized, "disease_detail")
        where.append(clause)
        params.update(p)

    has_drug_id = _column_exists(table_name, "drug_id")
    has_drug_key = _column_exists(table_name, "drug_key")
    has_drug_name = _column_exists(table_name, "drug_name")
    has_drug_match = has_drug_id or has_drug_key or has_drug_name
    if has_drug_match:
        where.append(_build_candidate_match_clause(table_name))

    query = (
        f"SELECT t.* FROM {_safe_ident(table_name)} t"
        f" WHERE {' AND '.join(where)}"
        f"{_build_order_clause(table_name)}"
        " LIMIT :row_limit"
    )
    return _canonicalize_disease_field(fetch_all(query, params))


def get_candidate_detail(disease: str, drug_key: str) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    detail: Dict[str, Any] = {"disease": normalized, "drug_key": drug_key}
    for key, table_name in DETAIL_TABLES.items():
        detail[key] = fetch_candidate_table_rows(table_name, normalized, drug_key)

    detail["model_ensemble_evidence"] = {
        "metabric_method_rows": detail.pop("metabric_method_rows"),
        "model_metric_rows": detail.pop("model_metric_rows"),
        "model_metric_detailed_rows": detail.pop("model_metric_detailed_rows"),
        "ensemble_metric_rows": detail.pop("ensemble_metric_rows"),
        "ensemble_source_manifest_rows": detail.pop("ensemble_source_manifest_rows"),
    }
    return detail
