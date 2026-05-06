#!/usr/bin/env python
"""Quick BRCA table-count checker with non-zero exit on empty key tables."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from sqlalchemy import create_engine, text


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("brca_table_counts")

DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

DISEASE = "BRCA"
RUN_ID = "BRCA_RELEASE_V1"

TABLES = [
    "brca_load_audit",
    "run_manifest",
    "source_artifact",
    "drug_candidate_result",
    "drug_candidate_tier",
    "final_candidate_result",
    "admet_result",
    "admet_assay_match",
    "admet_summary",
    "external_validation_result",
    "metabric_method_score",
    "model_metric",
    "model_metric_detailed",
    "ensemble_metric",
    "ensemble_source_manifest",
]

KEY_TABLES = [
    "drug_candidate_result",
    "drug_candidate_tier",
    "final_candidate_result",
    "admet_result",
    "external_validation_result",
    "model_metric",
    "model_metric_detailed",
    "ensemble_metric",
]


def get_env(name: str) -> str:
    return os.getenv(name, DEFAULT_POSTGRES[name])


def build_database_url() -> str:
    host = get_env("POSTGRES_HOST")
    port = get_env("POSTGRES_PORT")
    db = get_env("POSTGRES_DB")
    user = get_env("POSTGRES_USER")
    password = get_env("POSTGRES_PASSWORD")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def scalar_int(conn: Any, sql: str, params: Dict[str, Any]) -> int:
    row = conn.execute(text(sql), params).mappings().one()
    return int(row["n"])


def main() -> int:
    engine = create_engine(build_database_url(), future=True)
    counts: Dict[str, int] = {}

    with engine.connect() as conn:
        print("[info] BRCA table counts")
        for table in TABLES:
            n = scalar_int(
                conn,
                f"""
                SELECT COUNT(*) AS n
                FROM {table}
                WHERE disease = :disease
                  AND run_id = :run_id
                """,
                {"disease": DISEASE, "run_id": RUN_ID},
            )
            counts[table] = n
            print(f"- {table}: {n}")

    empty_key_tables: List[str] = [table for table in KEY_TABLES if counts.get(table, 0) == 0]
    if empty_key_tables:
        LOGGER.error("Empty key result tables: %s", ", ".join(empty_key_tables))
        return 2

    LOGGER.info("All key BRCA result tables are non-empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
