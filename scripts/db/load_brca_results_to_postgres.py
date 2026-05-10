#!/usr/bin/env python
"""Load BRCA result files from S3 into existing PostgreSQL tables.

Scope:
- PostgreSQL loading and validation metadata only.
- Uses one fixed BRCA S3 prefix and an explicit 16-file manifest.
- Idempotent per-file loading with DELETE + INSERT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import boto3
import pandas as pd
import s3fs
from botocore.exceptions import ClientError
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("brca_loader")

DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

DEFAULT_DISEASE = "BRCA"
DEFAULT_RUN_ID = "BRCA_RELEASE_V1"
DEFAULT_S3_PREFIX = (
    "s3://say2-4team/20260408_new_pre_project_biso/"
    "202604_Final_data/BRCA/20260428_new_BRCA_data/"
)
REPORT_PATH = Path("outputs/db_validation/brca_postgres_load_report.json")


@dataclass(frozen=True)
class FileSpec:
    relative_path: str
    table_name: str
    parser: str
    required: bool = True
    extra: Optional[Dict[str, Any]] = None


FILE_SPECS: List[FileSpec] = [
    FileSpec("brca_directive_top30_unique_candidates.csv", "drug_candidate_result", "drug_candidate_result"),
    FileSpec("brca_directive_top30_tiered_candidates.csv", "drug_candidate_tier", "drug_candidate_tier"),
    FileSpec("brca_model_performance_summary.csv", "model_metric", "model_metric"),
    FileSpec("brca_model_performance_detailed.csv", "model_metric_detailed", "model_metric_detailed"),
    FileSpec("brca_directive_ensemble_validation_summary.csv", "ensemble_metric", "ensemble_metric"),
    FileSpec("brca_directive_ensemble_source_manifest.csv", "ensemble_source_manifest", "ensemble_source_manifest"),
    FileSpec("copied_source_manifest.csv", "source_artifact", "source_artifact"),
    FileSpec("BRCA_reproducibility_manifest_20260428.json", "run_manifest", "run_manifest"),
    FileSpec(
        "step6_metabric_validation/brca_top30_metabric_scored.csv",
        "external_validation_result",
        "external_validation_result",
        extra={"validation_source": "metabric_scored"},
    ),
    FileSpec(
        "step6_metabric_validation/brca_top15_metabric_validated.csv",
        "external_validation_result",
        "external_validation_result",
        extra={"validation_source": "metabric_validated"},
    ),
    FileSpec(
        "step6_metabric_validation/brca_metabric_method_a.csv",
        "metabric_method_score",
        "metabric_method_score",
        extra={"method": "method_a"},
    ),
    FileSpec(
        "step6_metabric_validation/brca_metabric_method_b.csv",
        "metabric_method_score",
        "metabric_method_score",
        extra={"method": "method_b"},
    ),
    FileSpec("step7_admet_22assay/brca_admet_22assay_top30_detailed.csv", "admet_result", "admet_result"),
    FileSpec("step7_admet_22assay/brca_final15_after_admet.csv", "final_candidate_result", "final_candidate_result"),
    FileSpec("step7_admet_22assay/brca_admet_22assay_matches.json", "admet_assay_match", "admet_assay_match"),
    FileSpec("step7_admet_22assay/brca_admet_22assay_summary.json", "admet_summary", "admet_summary"),
]

REQUIRED_TABLES = [
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

UNIQUE_KEY_COLUMNS: Dict[str, List[str]] = {
    "run_manifest": ["disease", "run_id", "source_s3_uri", "manifest_name"],
    "source_artifact": ["disease", "run_id", "source_s3_uri", "artifact_name", "artifact_uri"],
    "drug_candidate_result": ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank"],
    "drug_candidate_tier": ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank", "tier"],
    "final_candidate_result": ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank"],
    "admet_result": ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank"],
    "admet_assay_match": ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "assay_name"],
    "admet_summary": ["disease", "run_id", "source_s3_uri", "summary_key"],
    "external_validation_result": ["disease", "run_id", "source_s3_uri", "validation_source", "drug_id", "drug_name", "rank"],
    "metabric_method_score": ["disease", "run_id", "source_s3_uri", "method", "drug_id", "drug_name", "rank"],
    "model_metric": [
        "disease",
        "run_id",
        "source_s3_uri",
        "phase",
        "family",
        "model",
        "metric",
        "source_model_dir",
    ],
    "model_metric_detailed": [
        "disease",
        "run_id",
        "source_s3_uri",
        "phase",
        "family",
        "model",
        "split",
        "metric",
        "source_model_dir",
    ],
    "ensemble_metric": ["disease", "run_id", "source_s3_uri", "metric"],
    "ensemble_source_manifest": ["disease", "run_id", "source_s3_uri", "model", "source_name", "source_uri"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load BRCA files from S3 into PostgreSQL")
    parser.add_argument("--disease", default=DEFAULT_DISEASE)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--s3-base-prefix", default=DEFAULT_S3_PREFIX)
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    return parser.parse_args()


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


def normalize_column_name(name: str) -> str:
    text_value = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    text_value = re.sub(r"_+", "_", text_value).strip("_")
    return text_value or "column"


def normalize_columns(columns: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Dict[str, int] = {}
    for col in columns:
        base = normalize_column_name(col)
        idx = seen.get(base, 0)
        seen[base] = idx + 1
        out.append(base if idx == 0 else f"{base}_{idx + 1}")
    return out


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = normalize_columns(out.columns)
    return out


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return str(value)


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k): to_jsonable(v) for k, v in record.items()}


def as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any, default: int = -1) -> int:
    val = as_float(value)
    if val is None:
        return default
    return int(val)


def as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "t", "yes", "y", "pass", "passed"}:
        return True
    if text_value in {"0", "false", "f", "no", "n", "fail", "failed"}:
        return False
    return None


def first_value(record: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key not in record:
            continue
        value = record[key]
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        return value
    return default


def common_row(disease: str, run_id: str, source_s3_uri: str) -> Dict[str, Any]:
    return {"disease": disease, "run_id": run_id, "source_s3_uri": source_s3_uri}


def build_metric_name(base_metric: str, record: Dict[str, Any]) -> str:
    context_parts: List[str] = []
    for key in ["phase", "family", "subgroup", "setting"]:
        value = record.get(key)
        if value is None:
            continue
        text_value = str(value).strip()
        if not text_value:
            continue
        context_parts.append(f"{key}={text_value}")
    if not context_parts:
        return base_metric
    return f"{base_metric}|{'|'.join(context_parts)}"


def deduplicate_rows(table_name: str, rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    key_columns = UNIQUE_KEY_COLUMNS.get(table_name)
    if not rows or not key_columns:
        return rows, 0

    dedup: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(col) for col in key_columns)
        dedup[key] = row
    deduped_rows = list(dedup.values())
    return deduped_rows, len(rows) - len(deduped_rows)


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {uri}")
    path = uri[len("s3://") :]
    bucket, key = path.split("/", 1)
    return bucket, key


def s3_exists(s3_client: Any, uri: str) -> bool:
    bucket, key = parse_s3_uri(uri)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def read_csv_from_s3(uri: str) -> pd.DataFrame:
    return normalize_dataframe(pd.read_csv(uri, storage_options={"anon": False}))


def read_json_from_s3(fs: s3fs.S3FileSystem, uri: str) -> Any:
    with fs.open(uri, "rb") as handle:
        return json.load(handle)


def read_bytes_from_s3(s3_client: Any, uri: str) -> bytes:
    bucket, key = parse_s3_uri(uri)
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def parse_drug_candidate_result(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "drug_id": str(
                    first_value(
                        record,
                        ["drug_id", "canonical_drug_id", "drugbank_id", "compound_id", "pert_id", "pubchem_cid"],
                        "",
                    )
                    or ""
                ),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "final_rank", "top_rank"], -1), default=-1),
                "score": as_float(
                    first_value(
                        record,
                        [
                            "score",
                            "drug_level_score",
                            "mean_prediction_score",
                            "ensemble_score",
                            "final_score",
                            "weighted_score",
                            "probability",
                        ],
                    )
                ),
                "payload": record,
            }
        )
    return rows


def parse_drug_candidate_tier(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "drug_id": str(
                    first_value(
                        record,
                        ["drug_id", "canonical_drug_id", "drugbank_id", "compound_id", "pert_id", "pubchem_cid"],
                        "",
                    )
                    or ""
                ),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "final_rank", "top_rank"], -1), default=-1),
                "tier": str(first_value(record, ["tier", "tier_label", "priority_tier"], "") or ""),
                "score": as_float(
                    first_value(
                        record,
                        [
                            "score",
                            "drug_level_score",
                            "mean_prediction_score",
                            "ensemble_score",
                            "final_score",
                            "weighted_score",
                            "probability",
                        ],
                    )
                ),
                "payload": record,
            }
        )
    return rows


def parse_final_candidate_result(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "drug_id": str(first_value(record, ["drug_id", "drugbank_id", "compound_id", "pert_id"], "") or ""),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "final_rank"], -1), default=-1),
                "final_verdict": str(first_value(record, ["final_verdict", "admet_verdict", "verdict", "status"], "") or ""),
                "payload": record,
            }
        )
    return rows


def parse_admet_result(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "drug_id": str(first_value(record, ["drug_id", "drugbank_id", "compound_id", "pert_id"], "") or ""),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "final_rank"], -1), default=-1),
                "admet_verdict": str(first_value(record, ["admet_verdict", "verdict", "pass_fail", "status"], "") or ""),
                "hard_fail": as_bool(first_value(record, ["hard_fail", "hard_fail_flag", "is_hard_fail"])),
                "score": as_float(first_value(record, ["score", "admet_score", "total_score", "weighted_score"])),
                "payload": record,
            }
        )
    return rows


def infer_metric_rows(
    df: pd.DataFrame,
    disease: str,
    run_id: str,
    source_s3_uri: str,
    detailed: bool,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        model = str(first_value(record, ["model", "model_name", "estimator", "algorithm"], "") or "")
        split = str(first_value(record, ["split", "fold", "dataset", "data_split", "set"], "") or "")
        metric_name = first_value(record, ["metric", "metric_name"])
        metric_value = first_value(record, ["metric_value", "value", "score"])
        phase = str(first_value(record, ["phase", "stage", "config", "track"], "") or "")
        family = str(first_value(record, ["family", "model_family", "type"], "") or "")
        source_model_dir = str(
            first_value(record, ["source_model_dir", "model_dir", "source_dir", "artifact_dir"], "") or ""
        )

        if metric_name is not None:
            rows.append(
                {
                    **common_row(disease, run_id, source_s3_uri),
                    "phase": phase,
                    "family": family,
                    "model": model,
                    "split": split,
                    "metric": build_metric_name(str(metric_name), record),
                    "metric_value": as_float(metric_value),
                    "source_model_dir": source_model_dir,
                    "payload": record,
                }
            )
            continue

        skip_cols = {
            "model",
            "model_name",
            "estimator",
            "algorithm",
            "split",
            "fold",
            "dataset",
            "data_split",
            "set",
            "disease",
            "run_id",
            "source_s3_uri",
        }
        for key, value in record.items():
            if key in skip_cols:
                continue
            numeric = as_float(value)
            if numeric is None:
                continue
            rows.append(
                {
                    **common_row(disease, run_id, source_s3_uri),
                    "phase": phase,
                    "family": family,
                    "model": model,
                    "split": split,
                    "metric": build_metric_name(key, record),
                    "metric_value": numeric,
                    "source_model_dir": source_model_dir,
                    "payload": record,
                }
            )

    if not detailed:
        for row in rows:
            row.pop("split", None)
    return rows


def parse_ensemble_metric(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in infer_metric_rows(df, disease, run_id, source_s3_uri, detailed=False):
        metric_name = build_metric_name(f"{row.get('model', '')}:{row['metric']}".strip(":"), row.get("payload", {}))
        out.append(
            {
                "disease": row["disease"],
                "run_id": row["run_id"],
                "source_s3_uri": row["source_s3_uri"],
                "metric": metric_name,
                "metric_value": row["metric_value"],
                "payload": row["payload"],
            }
        )
    return out


def parse_ensemble_source_manifest(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "model": str(first_value(record, ["model", "model_name", "estimator"], "") or ""),
                "source_name": str(first_value(record, ["source_name", "artifact_name", "dataset", "name"], "") or ""),
                "source_uri": str(first_value(record, ["source_uri", "source_s3_uri", "s3_uri", "uri", "path"], "") or ""),
                "weight": as_float(first_value(record, ["weight", "ensemble_weight", "contribution"])),
                "payload": record,
            }
        )
    return rows


def parse_source_artifact(df: pd.DataFrame, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "artifact_name": str(first_value(record, ["artifact_name", "source_name", "file_name", "dataset", "name"], "") or ""),
                "artifact_type": str(first_value(record, ["artifact_type", "source_type", "type"], "") or ""),
                "artifact_uri": str(first_value(record, ["artifact_uri", "source_s3_uri", "s3_uri", "uri", "path", "file_path"], "") or ""),
                "artifact_hash": str(first_value(record, ["artifact_hash", "sha256", "md5", "checksum"], "") or ""),
                "payload": record,
            }
        )
    return rows


def parse_external_validation_result(
    df: pd.DataFrame,
    disease: str,
    run_id: str,
    source_s3_uri: str,
    validation_source: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "validation_source": validation_source,
                "drug_id": str(first_value(record, ["drug_id", "drugbank_id", "compound_id", "pert_id"], "") or ""),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "final_rank", "metabric_rank"], -1), default=-1),
                "validation_score": as_float(first_value(record, ["validation_score", "metabric_score", "score", "corr", "correlation"])),
                "payload": record,
            }
        )
    return rows


def parse_metabric_method_score(
    df: pd.DataFrame,
    disease: str,
    run_id: str,
    source_s3_uri: str,
    method: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in df.to_dict(orient="records"):
        record = normalize_record(raw)
        rows.append(
            {
                **common_row(disease, run_id, source_s3_uri),
                "method": method,
                "drug_id": str(first_value(record, ["drug_id", "drugbank_id", "compound_id", "pert_id"], "") or ""),
                "drug_name": str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], "") or ""),
                "rank": as_int(first_value(record, ["rank", "method_rank", "final_rank"], -1), default=-1),
                "score": as_float(first_value(record, ["score", "method_score", "metabric_score", "corr", "correlation"])),
                "payload": record,
            }
        )
    return rows


def parse_run_manifest(raw_json: Any, raw_bytes: bytes, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    return [
        {
            **common_row(disease, run_id, source_s3_uri),
            "manifest_name": Path(source_s3_uri).name,
            "manifest_sha256": sha256,
            "manifest_json": to_jsonable(raw_json),
        }
    ]


def _extract_assay_rows(data: Any, parent_drug_id: str = "", parent_drug_name: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    if isinstance(data, list):
        for item in data:
            rows.extend(_extract_assay_rows(item, parent_drug_id, parent_drug_name))
        return rows

    if not isinstance(data, dict):
        return rows

    normalized = {normalize_column_name(k): v for k, v in data.items()}
    drug_id = str(first_value(normalized, ["drug_id", "drugbank_id", "compound_id", "pert_id"], parent_drug_id) or "")
    drug_name = str(first_value(normalized, ["drug_name", "compound_name", "pert_iname", "name"], parent_drug_name) or "")

    assay_name = first_value(normalized, ["assay_name", "assay", "endpoint", "test_name"])
    if assay_name is not None:
        rows.append(
            {
                "drug_id": drug_id,
                "drug_name": drug_name,
                "assay_name": str(assay_name),
                "match_value": str(first_value(normalized, ["match_value", "value", "status", "result"], "") or ""),
                "match_score": as_float(first_value(normalized, ["match_score", "score", "probability", "confidence"])),
                "payload": to_jsonable(data),
            }
        )
        return rows

    nested_found = False
    for nested_key in ["matches", "assays", "results", "items", "data"]:
        nested = normalized.get(nested_key)
        if isinstance(nested, (list, dict)):
            rows.extend(_extract_assay_rows(nested, drug_id, drug_name))
            nested_found = True

    if not nested_found:
        for key, nested in data.items():
            if isinstance(nested, (list, dict)):
                rows.extend(_extract_assay_rows(nested, drug_id or normalize_column_name(key), drug_name))

    return rows


def parse_admet_assay_match(raw_json: Any, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    # Primary expected structure:
    # {
    #   "<drug_name>": {
    #     "drug_id": ...,
    #     "drug_name": ...,
    #     "assays": {
    #       "<assay_name>": {"value": ..., "similarity": ..., ...}
    #     }
    #   }
    # }
    if isinstance(raw_json, dict):
        for top_key, rec in raw_json.items():
            if not isinstance(rec, dict):
                continue
            record = normalize_record(rec)
            drug_id = str(first_value(record, ["drug_id", "drugbank_id", "compound_id", "pert_id"], "") or "")
            drug_name = str(first_value(record, ["drug_name", "compound_name", "pert_iname", "name"], top_key) or top_key)
            assays = rec.get("assays")
            if not isinstance(assays, dict):
                continue
            for assay_name, assay_payload in assays.items():
                assay_record = normalize_record(assay_payload) if isinstance(assay_payload, dict) else {"value": to_jsonable(assay_payload)}
                out.append(
                    {
                        **common_row(disease, run_id, source_s3_uri),
                        "drug_id": drug_id,
                        "drug_name": drug_name,
                        "assay_name": str(assay_name),
                        "match_value": str(first_value(assay_record, ["value", "match_value", "status", "result"], "") or ""),
                        "match_score": as_float(first_value(assay_record, ["similarity", "match_score", "score", "confidence"])),
                        "payload": assay_record,
                    }
                )

    # Fallback for any alternate nested format
    if not out:
        for row in _extract_assay_rows(raw_json):
            out.append(
                {
                    **common_row(disease, run_id, source_s3_uri),
                    "drug_id": row["drug_id"],
                    "drug_name": row["drug_name"],
                    "assay_name": row["assay_name"],
                    "match_value": row["match_value"],
                    "match_score": row["match_score"],
                    "payload": row["payload"],
                }
            )

    return out


def parse_admet_summary(raw_json: Any, disease: str, run_id: str, source_s3_uri: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if isinstance(raw_json, dict):
        for key, value in raw_json.items():
            rows.append(
                {
                    **common_row(disease, run_id, source_s3_uri),
                    "summary_key": normalize_column_name(str(key)),
                    "summary_value": json.dumps(to_jsonable(value), ensure_ascii=False),
                    "payload": {str(key): to_jsonable(value)},
                }
            )
        return rows

    if isinstance(raw_json, list):
        for idx, value in enumerate(raw_json, start=1):
            rows.append(
                {
                    **common_row(disease, run_id, source_s3_uri),
                    "summary_key": f"item_{idx}",
                    "summary_value": json.dumps(to_jsonable(value), ensure_ascii=False),
                    "payload": to_jsonable(value),
                }
            )
        return rows

    rows.append(
        {
            **common_row(disease, run_id, source_s3_uri),
            "summary_key": "value",
            "summary_value": json.dumps(to_jsonable(raw_json), ensure_ascii=False),
            "payload": {"value": to_jsonable(raw_json)},
        }
    )
    return rows


def parse_rows(spec: FileSpec, source_uri: str, fs: s3fs.S3FileSystem, s3_client: Any, disease: str, run_id: str) -> List[Dict[str, Any]]:
    extra = spec.extra or {}

    if spec.parser == "run_manifest":
        raw_json = read_json_from_s3(fs, source_uri)
        raw_bytes = read_bytes_from_s3(s3_client, source_uri)
        return parse_run_manifest(raw_json, raw_bytes, disease, run_id, source_uri)
    if spec.parser == "admet_assay_match":
        return parse_admet_assay_match(read_json_from_s3(fs, source_uri), disease, run_id, source_uri)
    if spec.parser == "admet_summary":
        return parse_admet_summary(read_json_from_s3(fs, source_uri), disease, run_id, source_uri)

    df = read_csv_from_s3(source_uri)
    if spec.parser == "drug_candidate_result":
        return parse_drug_candidate_result(df, disease, run_id, source_uri)
    if spec.parser == "drug_candidate_tier":
        return parse_drug_candidate_tier(df, disease, run_id, source_uri)
    if spec.parser == "final_candidate_result":
        return parse_final_candidate_result(df, disease, run_id, source_uri)
    if spec.parser == "admet_result":
        return parse_admet_result(df, disease, run_id, source_uri)
    if spec.parser == "external_validation_result":
        return parse_external_validation_result(df, disease, run_id, source_uri, extra.get("validation_source", ""))
    if spec.parser == "metabric_method_score":
        return parse_metabric_method_score(df, disease, run_id, source_uri, extra.get("method", ""))
    if spec.parser == "model_metric":
        metric_rows = infer_metric_rows(df, disease, run_id, source_uri, detailed=False)
        return [
            {
                "disease": row["disease"],
                "run_id": row["run_id"],
                "source_s3_uri": row["source_s3_uri"],
                "phase": row.get("phase", "") or "",
                "family": row.get("family", "") or "",
                "model": row["model"],
                "metric": row["metric"],
                "metric_value": row["metric_value"],
                "source_model_dir": row.get("source_model_dir", "") or "",
                "payload": row["payload"],
            }
            for row in metric_rows
        ]
    if spec.parser == "model_metric_detailed":
        metric_rows = infer_metric_rows(df, disease, run_id, source_uri, detailed=True)
        return [
            {
                "disease": row["disease"],
                "run_id": row["run_id"],
                "source_s3_uri": row["source_s3_uri"],
                "phase": row.get("phase", "") or "",
                "family": row.get("family", "") or "",
                "model": row["model"],
                "split": row.get("split", "") or "",
                "metric": row["metric"],
                "metric_value": row["metric_value"],
                "source_model_dir": row.get("source_model_dir", "") or "",
                "payload": row["payload"],
            }
            for row in metric_rows
        ]
    if spec.parser == "ensemble_metric":
        return parse_ensemble_metric(df, disease, run_id, source_uri)
    if spec.parser == "ensemble_source_manifest":
        return parse_ensemble_source_manifest(df, disease, run_id, source_uri)
    if spec.parser == "source_artifact":
        return parse_source_artifact(df, disease, run_id, source_uri)

    raise ValueError(f"Unsupported parser: {spec.parser}")


def ensure_required_tables(engine: Any) -> None:
    inspector = inspect(engine)
    missing = [table for table in REQUIRED_TABLES if not inspector.has_table(table)]
    if missing:
        raise RuntimeError(
            "Missing required BRCA tables in database. "
            f"Run scripts/db/001_create_brca_tables.sql first. Missing: {', '.join(missing)}"
        )


def delete_for_source(conn: Any, table_name: str, disease: str, run_id: str, source_s3_uri: str) -> int:
    result = conn.execute(
        text(
            f"""
            DELETE FROM {table_name}
            WHERE disease = :disease
              AND run_id = :run_id
              AND source_s3_uri = :source_s3_uri
            """
        ),
        {"disease": disease, "run_id": run_id, "source_s3_uri": source_s3_uri},
    )
    return int(result.rowcount or 0)


def insert_rows(conn: Any, table: Table, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.execute(pg_insert(table).values(rows))
    return len(rows)


def count_for_source(conn: Any, table_name: str, disease: str, run_id: str, source_s3_uri: str) -> int:
    row = conn.execute(
        text(
            f"""
            SELECT COUNT(*) AS n
            FROM {table_name}
            WHERE disease = :disease
              AND run_id = :run_id
              AND source_s3_uri = :source_s3_uri
            """
        ),
        {"disease": disease, "run_id": run_id, "source_s3_uri": source_s3_uri},
    ).mappings().one()
    return int(row["n"])


def write_audit_row(
    conn: Any,
    audit_table: Table,
    disease: str,
    run_id: str,
    source_s3_uri: str,
    table_name: str,
    file_name: str,
    status: str,
    row_count: int,
    message: str,
) -> None:
    conn.execute(
        text(
            """
            DELETE FROM brca_load_audit
            WHERE disease = :disease
              AND run_id = :run_id
              AND source_s3_uri = :source_s3_uri
              AND table_name = :table_name
            """
        ),
        {
            "disease": disease,
            "run_id": run_id,
            "source_s3_uri": source_s3_uri,
            "table_name": table_name,
        },
    )
    insert_rows(
        conn,
        audit_table,
        [
            {
                "disease": disease,
                "run_id": run_id,
                "source_s3_uri": source_s3_uri,
                "table_name": table_name,
                "file_name": file_name,
                "status": status,
                "row_count": row_count,
                "message": message,
            }
        ],
    )


def validate_s3_prefix(prefix: str) -> str:
    normalized = prefix.strip()
    if not normalized.startswith("s3://"):
        raise ValueError(f"s3-base-prefix must start with s3://, got: {prefix}")
    return normalized.rstrip("/") + "/"


def save_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Saved load report: %s", path)


def main() -> int:
    args = parse_args()
    s3_prefix = validate_s3_prefix(args.s3_base_prefix)
    report_path = Path(args.report_path)

    LOGGER.info("PostgreSQL target: %s", connection_target())
    LOGGER.info("Load strategy per file/table: DELETE + INSERT (idempotent by disease/run_id/source_s3_uri)")
    LOGGER.info("S3 BRCA source prefix: %s", s3_prefix)

    engine = create_engine(build_database_url(), future=True)
    s3_client = boto3.client("s3")
    fs = s3fs.S3FileSystem(anon=False)

    try:
        ensure_required_tables(engine)
    except Exception as exc:
        LOGGER.error("Table validation failed: %s", exc)
        return 1

    metadata = MetaData()
    tables = {table: Table(table, metadata, autoload_with=engine) for table in REQUIRED_TABLES}

    summary_entries: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []

    with engine.begin() as conn:
        for spec in FILE_SPECS:
            source_uri = f"{s3_prefix}{spec.relative_path}"
            file_name = Path(spec.relative_path).name
            entry: Dict[str, Any] = {
                "table_name": spec.table_name,
                "source_file": spec.relative_path,
                "source_s3_uri": source_uri,
                "strategy": "delete_insert",
                "rows_deleted": 0,
                "rows_inserted": 0,
                "rows_after_load_for_source": 0,
                "warnings": [],
                "failure": None,
            }

            try:
                if not s3_exists(s3_client, source_uri):
                    message = f"Missing S3 file: {source_uri}"
                    if spec.required:
                        errors.append(message)
                        entry["failure"] = message
                        status = "error"
                        LOGGER.error(message)
                    else:
                        warnings.append(message)
                        entry["warnings"].append(message)
                        status = "warning"
                        LOGGER.warning(message)
                    write_audit_row(
                        conn,
                        tables["brca_load_audit"],
                        args.disease,
                        args.run_id,
                        source_uri,
                        spec.table_name,
                        file_name,
                        status,
                        0,
                        message,
                    )
                    summary_entries.append(entry)
                    continue

                rows = parse_rows(spec, source_uri, fs, s3_client, args.disease, args.run_id)
                deduped_rows, duplicates_removed = deduplicate_rows(spec.table_name, rows)
                if duplicates_removed > 0:
                    dedup_message = (
                        f"Removed {duplicates_removed} duplicate rows by unique key before insert "
                        f"for table={spec.table_name}"
                    )
                    warnings.append(dedup_message)
                    entry["warnings"].append(dedup_message)
                    LOGGER.warning(dedup_message)

                with conn.begin_nested():
                    deleted = delete_for_source(conn, spec.table_name, args.disease, args.run_id, source_uri)
                    inserted = insert_rows(conn, tables[spec.table_name], deduped_rows)
                    final_count = count_for_source(conn, spec.table_name, args.disease, args.run_id, source_uri)

                entry["rows_deleted"] = deleted
                entry["rows_inserted"] = inserted
                entry["rows_after_load_for_source"] = final_count
                LOGGER.info(
                    "[%s] %s <- %s | deleted=%s inserted=%s current=%s",
                    "OK",
                    spec.table_name,
                    spec.relative_path,
                    deleted,
                    inserted,
                    final_count,
                )
                write_audit_row(
                    conn,
                    tables["brca_load_audit"],
                    args.disease,
                    args.run_id,
                    source_uri,
                    spec.table_name,
                    file_name,
                    "success",
                    inserted,
                    f"DELETE+INSERT completed. deleted={deleted}, inserted={inserted}, current={final_count}",
                )
            except Exception as exc:
                message = f"Failed to load {source_uri} into {spec.table_name}: {exc}"
                if spec.required:
                    errors.append(message)
                else:
                    warnings.append(message)
                    entry["warnings"].append(message)
                entry["failure"] = message
                LOGGER.error(message)
                write_audit_row(
                    conn,
                    tables["brca_load_audit"],
                    args.disease,
                    args.run_id,
                    source_uri,
                    spec.table_name,
                    file_name,
                    "error",
                    0,
                    message,
                )
            summary_entries.append(entry)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disease": args.disease,
        "run_id": args.run_id,
        "postgres_target": connection_target(),
        "s3_base_prefix": s3_prefix,
        "status": "success" if not errors else "failed",
        "summary": summary_entries,
        "warnings": warnings,
        "failures": errors,
    }
    save_report(report_path, report)

    print("\nLoad summary:")
    for item in summary_entries:
        print(
            f"- table={item['table_name']} file={item['source_file']} "
            f"inserted={item['rows_inserted']} deleted={item['rows_deleted']} "
            f"warnings={len(item['warnings'])} failure={'yes' if item['failure'] else 'no'}"
        )

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nFailures:")
        for failure in errors:
            print(f"- {failure}")
        return 2

    print("\n[ok] BRCA PostgreSQL load completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
