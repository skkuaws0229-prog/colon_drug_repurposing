#!/usr/bin/env python
"""Validate BRCA PostgreSQL load status and save a JSON report."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import create_engine, text


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("brca_validation")

DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

DISEASE = "BRCA"
RUN_ID = "BRCA_RELEASE_V1"
REPORT_PATH = Path("outputs/db_validation/brca_postgres_validation_report.json")
SOURCE_PREFIX = "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/"

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


def get_env(name: str) -> str:
    return os.getenv(name, DEFAULT_POSTGRES[name])


def build_database_url() -> str:
    host = get_env("POSTGRES_HOST")
    port = get_env("POSTGRES_PORT")
    db = get_env("POSTGRES_DB")
    user = get_env("POSTGRES_USER")
    password = get_env("POSTGRES_PASSWORD")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def connection_target() -> str:
    host = get_env("POSTGRES_HOST")
    port = get_env("POSTGRES_PORT")
    db = get_env("POSTGRES_DB")
    user = get_env("POSTGRES_USER")
    return f"host={host} port={port} db={db} user={user}"


def serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def df_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        out.append({str(k): serialize_value(v) for k, v in row.items()})
    return out


def scalar_int(conn: Any, sql: str, params: Dict[str, Any]) -> int:
    row = conn.execute(text(sql), params).mappings().one()
    return int(row["n"])


def print_df(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}")
    if df.empty:
        print("(no rows)")
        return
    print(df.to_string(index=False))


def main() -> int:
    LOGGER.info("PostgreSQL target: %s", connection_target())
    engine = create_engine(build_database_url(), future=True)
    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disease": DISEASE,
        "run_id": RUN_ID,
        "postgres_target": connection_target(),
        "row_counts": {},
        "presence_checks": {},
        "metadata_checks": {},
    }

    try:
        with engine.connect() as conn:
            print("[info] Row counts")
            for table_name in TABLES:
                n = scalar_int(
                    conn,
                    f"""
                    SELECT COUNT(*) AS n
                    FROM {table_name}
                    WHERE disease = :disease
                      AND run_id = :run_id
                    """,
                    {"disease": DISEASE, "run_id": RUN_ID},
                )
                report["row_counts"][table_name] = n
                print(f"- {table_name}: {n}")

            # Presence checks requested by user
            presence_checks = {
                "top30_candidate_results": report["row_counts"]["drug_candidate_result"] >= 30,
                "tiered_candidate_results": report["row_counts"]["drug_candidate_tier"] > 0,
                "final15_after_admet": report["row_counts"]["final_candidate_result"] >= 15,
                "admet_detailed_results": report["row_counts"]["admet_result"] > 0,
                "metabric_validation_results": report["row_counts"]["external_validation_result"] > 0,
                "model_performance_summary": report["row_counts"]["model_metric"] > 0,
                "model_performance_detailed": report["row_counts"]["model_metric_detailed"] > 0,
                "ensemble_validation_summary": report["row_counts"]["ensemble_metric"] > 0,
                "source_manifest": report["row_counts"]["source_artifact"] > 0,
                "reproducibility_manifest": report["row_counts"]["run_manifest"] > 0,
            }
            report["presence_checks"] = presence_checks
            print("\n[info] Presence checks")
            for key, passed in presence_checks.items():
                print(f"- {key}: {'PASS' if passed else 'FAIL'}")

            top30_df = pd.read_sql(
                text(
                    """
                    SELECT drug_id, drug_name, rank, score
                    FROM drug_candidate_result
                    WHERE disease = :disease
                      AND run_id = :run_id
                    ORDER BY rank ASC, drug_name ASC
                    LIMIT 30
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["top30_candidates"] = df_records(top30_df)
            print_df("[info] Top 30 candidate drugs by rank", top30_df)

            final15_df = pd.read_sql(
                text(
                    """
                    SELECT drug_id, drug_name, rank, final_verdict
                    FROM final_candidate_result
                    WHERE disease = :disease
                      AND run_id = :run_id
                    ORDER BY rank ASC, drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["final15_candidates"] = df_records(final15_df)
            print_df("[info] Final15 candidates", final15_df)

            admet_verdict_df = pd.read_sql(
                text(
                    """
                    SELECT COALESCE(admet_verdict, 'NULL') AS admet_verdict, COUNT(*) AS n
                    FROM admet_result
                    WHERE disease = :disease
                      AND run_id = :run_id
                    GROUP BY COALESCE(admet_verdict, 'NULL')
                    ORDER BY n DESC, admet_verdict ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["admet_verdict_distribution"] = df_records(admet_verdict_df)
            print_df("[info] ADMET verdict distribution", admet_verdict_df)

            admet_hard_fail_df = pd.read_sql(
                text(
                    """
                    SELECT
                      CASE
                        WHEN hard_fail IS TRUE THEN 'true'
                        WHEN hard_fail IS FALSE THEN 'false'
                        ELSE 'null'
                      END AS hard_fail,
                      COUNT(*) AS n
                    FROM admet_result
                    WHERE disease = :disease
                      AND run_id = :run_id
                    GROUP BY 1
                    ORDER BY n DESC, hard_fail ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["admet_hard_fail_distribution"] = df_records(admet_hard_fail_df)
            print_df("[info] ADMET hard_fail distribution", admet_hard_fail_df)

            metabric_summary_df = pd.read_sql(
                text(
                    """
                    SELECT
                      validation_source,
                      COUNT(*) AS n,
                      MIN(validation_score) AS min_validation_score,
                      AVG(validation_score) AS avg_validation_score,
                      MAX(validation_score) AS max_validation_score
                    FROM external_validation_result
                    WHERE disease = :disease
                      AND run_id = :run_id
                    GROUP BY validation_source
                    ORDER BY validation_source ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["metabric_validation_score_summary"] = df_records(metabric_summary_df)
            print_df("[info] METABRIC validation_score summary", metabric_summary_df)

            model_summary_df = pd.read_sql(
                text(
                    """
                    SELECT model, metric, metric_value
                    FROM model_metric
                    WHERE disease = :disease
                      AND run_id = :run_id
                    ORDER BY model ASC, metric ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["model_performance_summary"] = df_records(model_summary_df)
            print_df("[info] Model performance summary", model_summary_df)

            ensemble_summary_df = pd.read_sql(
                text(
                    """
                    SELECT metric, metric_value
                    FROM ensemble_metric
                    WHERE disease = :disease
                      AND run_id = :run_id
                    ORDER BY metric ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["ensemble_validation_summary"] = df_records(ensemble_summary_df)
            print_df("[info] Ensemble validation summary", ensemble_summary_df)

            # Missing joins requested by user
            missing_candidates_without_admet_df = pd.read_sql(
                text(
                    """
                    SELECT c.drug_id, c.drug_name, c.rank
                    FROM drug_candidate_result c
                    LEFT JOIN admet_result a
                      ON a.disease = c.disease
                     AND a.run_id = c.run_id
                     AND a.drug_id = c.drug_id
                     AND a.drug_name = c.drug_name
                    WHERE c.disease = :disease
                      AND c.run_id = :run_id
                      AND a.id IS NULL
                    ORDER BY c.rank ASC, c.drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["candidate_drugs_without_admet"] = df_records(missing_candidates_without_admet_df)
            print_df("[info] Missing joins: candidate drugs without ADMET", missing_candidates_without_admet_df)

            missing_candidates_without_metabric_df = pd.read_sql(
                text(
                    """
                    SELECT c.drug_id, c.drug_name, c.rank
                    FROM drug_candidate_result c
                    LEFT JOIN external_validation_result v
                      ON v.disease = c.disease
                     AND v.run_id = c.run_id
                     AND v.drug_id = c.drug_id
                     AND v.drug_name = c.drug_name
                    WHERE c.disease = :disease
                      AND c.run_id = :run_id
                      AND v.id IS NULL
                    ORDER BY c.rank ASC, c.drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["candidate_drugs_without_metabric_validation"] = df_records(missing_candidates_without_metabric_df)
            print_df(
                "[info] Missing joins: candidate drugs without METABRIC validation",
                missing_candidates_without_metabric_df,
            )

            final15_not_in_top30_df = pd.read_sql(
                text(
                    """
                    SELECT f.drug_id, f.drug_name, f.rank
                    FROM final_candidate_result f
                    LEFT JOIN drug_candidate_result c
                      ON c.disease = f.disease
                     AND c.run_id = f.run_id
                     AND c.drug_id = f.drug_id
                     AND c.drug_name = f.drug_name
                    WHERE f.disease = :disease
                      AND f.run_id = :run_id
                      AND c.id IS NULL
                    ORDER BY f.rank ASC, f.drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["final15_drugs_not_in_top30"] = df_records(final15_not_in_top30_df)
            print_df("[info] Missing joins: final15 drugs not found in top30", final15_not_in_top30_df)

            admet_not_in_candidates_df = pd.read_sql(
                text(
                    """
                    SELECT a.drug_id, a.drug_name, a.rank
                    FROM admet_result a
                    LEFT JOIN drug_candidate_result c
                      ON c.disease = a.disease
                     AND c.run_id = a.run_id
                     AND c.drug_id = a.drug_id
                     AND c.drug_name = a.drug_name
                    WHERE a.disease = :disease
                      AND a.run_id = :run_id
                      AND c.id IS NULL
                    ORDER BY a.rank ASC, a.drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["admet_drugs_not_found_in_candidate_list"] = df_records(admet_not_in_candidates_df)
            print_df("[info] Missing joins: ADMET drugs not found in candidate list", admet_not_in_candidates_df)

            validation_not_in_candidates_df = pd.read_sql(
                text(
                    """
                    SELECT v.validation_source, v.drug_id, v.drug_name, v.rank
                    FROM external_validation_result v
                    LEFT JOIN drug_candidate_result c
                      ON c.disease = v.disease
                     AND c.run_id = v.run_id
                     AND c.drug_id = v.drug_id
                     AND c.drug_name = v.drug_name
                    WHERE v.disease = :disease
                      AND v.run_id = :run_id
                      AND c.id IS NULL
                    ORDER BY v.validation_source ASC, v.rank ASC, v.drug_name ASC
                    """
                ),
                conn,
                params={"disease": DISEASE, "run_id": RUN_ID},
            )
            report["validation_drugs_not_found_in_candidate_list"] = df_records(validation_not_in_candidates_df)
            print_df(
                "[info] Missing joins: validation drugs not found in candidate list",
                validation_not_in_candidates_df,
            )

            # Metadata checks requested by user
            metadata_checks: Dict[str, Any] = {}
            for table_name in TABLES:
                null_source_count = scalar_int(
                    conn,
                    f"""
                    SELECT COUNT(*) AS n
                    FROM {table_name}
                    WHERE disease = :disease
                      AND run_id = :run_id
                      AND (source_s3_uri IS NULL OR btrim(source_s3_uri) = '')
                    """,
                    {"disease": DISEASE, "run_id": RUN_ID},
                )
                metadata_checks[table_name] = {
                    "null_or_blank_source_s3_uri_rows": null_source_count,
                    "disease_check": "BRCA",
                    "run_id_check": "BRCA_RELEASE_V1",
                }

            metadata_checks["unexpected_disease_for_run_id"] = scalar_int(
                conn,
                """
                SELECT COUNT(*) AS n
                FROM drug_candidate_result
                WHERE run_id = :run_id
                  AND disease <> :disease
                """,
                {"run_id": RUN_ID, "disease": DISEASE},
            )
            metadata_checks["unexpected_run_id_for_disease"] = scalar_int(
                conn,
                """
                SELECT COUNT(*) AS n
                FROM drug_candidate_result
                WHERE disease = :disease
                  AND run_id <> :run_id
                """,
                {"run_id": RUN_ID, "disease": DISEASE},
            )
            metadata_checks["rows_with_expected_prefix_in_candidates"] = scalar_int(
                conn,
                """
                SELECT COUNT(*) AS n
                FROM drug_candidate_result
                WHERE disease = :disease
                  AND run_id = :run_id
                  AND source_s3_uri LIKE :prefix
                """,
                {"run_id": RUN_ID, "disease": DISEASE, "prefix": f"{SOURCE_PREFIX}%"},
            )
            report["metadata_checks"] = metadata_checks

            print("\n[info] Metadata checks")
            print(f"- expected disease: {DISEASE}")
            print(f"- expected run_id: {RUN_ID}")
            print(f"- candidate rows with source_s3_uri under BRCA prefix: {metadata_checks['rows_with_expected_prefix_in_candidates']}")
            print(f"- unexpected disease for run_id: {metadata_checks['unexpected_disease_for_run_id']}")
            print(f"- unexpected run_id for disease: {metadata_checks['unexpected_run_id_for_disease']}")
            for table_name in TABLES:
                print(
                    f"- {table_name}: null/blank source_s3_uri rows="
                    f"{metadata_checks[table_name]['null_or_blank_source_s3_uri_rows']}"
                )
    except Exception as exc:
        LOGGER.error("Validation failed: %s", exc)
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Validation report saved: %s", REPORT_PATH)

    # Fail if any core presence check fails.
    failed_presence = [name for name, passed in report["presence_checks"].items() if not passed]
    if failed_presence:
        LOGGER.error("Core presence checks failed: %s", ", ".join(failed_presence))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
