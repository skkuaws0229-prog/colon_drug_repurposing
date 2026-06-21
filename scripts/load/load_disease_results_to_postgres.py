#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
import s3fs
import yaml
from botocore.exceptions import ClientError
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert


LOGGER = logging.getLogger("generic_disease_loader")

DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

ROLE_TABLE_MAP: dict[str, str] = {
    "candidate_unique": "drug_candidate_result",
    "candidate_tiered": "drug_candidate_tier",
    "model_performance_summary": "model_metric",
    "model_performance_detailed": "model_metric_detailed",
    "ensemble_validation_summary": "ensemble_metric",
    "ensemble_source_manifest": "ensemble_source_manifest",
    "external_validation_top30": "external_validation_result",
    "external_validation_top15": "external_validation_result",
    "external_validation_method_a": "external_validation_result",
    "external_validation_method_b": "external_validation_result",
    "admet_top30": "admet_result",
    "final_after_admet": "final_candidate_result",
    "admet_summary": "admet_summary",
    "copied_source_manifest": "source_artifact",
    "reproducibility_manifest": "run_manifest",
}

EXECUTE_ALLOWED_DISEASES = {"COAD"}

ALIAS_TO_CONFIG = {
    "BRCA": "brca.yaml",
    "COAD": "colon.yaml",
    "COLON": "colon.yaml",
    "HNSC": "hnsc.yaml",
    "LIHC": "liver.yaml",
    "LIVER": "liver.yaml",
    "LUNG": "lung.yaml",
    "PAAD": "pdac.yaml",
    "PDAC": "pdac.yaml",
    "STAD": "stad.yaml",
}

DRUG_ID_KEYS = ["drug_id", "canonical_drug_id", "compound_id", "pubchem_cid", "drugbank_id", "pert_id"]
DRUG_NAME_KEYS = ["drug_name", "canonical_drug_name", "name", "compound_name", "pert_iname", "drug"]
RANK_KEYS = ["rank", "final_rank", "top_rank"]
SCORE_KEYS = ["score", "drug_level_score", "confidence_score", "validation_score"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic config-driven disease loader to PostgreSQL")
    parser.add_argument("--disease", required=True, help="Disease code or alias (e.g., COAD, COLON, BRCA)")
    parser.add_argument("--config-dir", default="configs/diseases")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--limit-rows", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_env(name: str) -> str:
    return os.getenv(name, DEFAULT_POSTGRES[name])


def build_database_url() -> str:
    return (
        f"postgresql+psycopg2://{get_env('POSTGRES_USER')}:{get_env('POSTGRES_PASSWORD')}"
        f"@{get_env('POSTGRES_HOST')}:{get_env('POSTGRES_PORT')}/{get_env('POSTGRES_DB')}"
    )


def normalize_s3_uri(uri: str) -> str:
    s = str(uri).strip().replace("\\", "/")
    if s.startswith("s3:/") and not s.startswith("s3://"):
        s = s.replace("s3:/", "s3://", 1)
    if not s.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {uri}")
    while "///" in s:
        s = s.replace("///", "//")
    return s


def normalize_prefix(uri: str) -> str:
    s = normalize_s3_uri(uri)
    if not s.endswith("/"):
        s += "/"
    return s


def parse_s3_uri(uri: str) -> tuple[str, str]:
    s = normalize_s3_uri(uri)
    bucket_key = s[len("s3://") :]
    bucket, key = bucket_key.split("/", 1)
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


def s3_size(s3_client: Any, uri: str) -> int | None:
    bucket, key = parse_s3_uri(uri)
    try:
        resp = s3_client.head_object(Bucket=bucket, Key=key)
        return int(resp.get("ContentLength", 0))
    except ClientError:
        return None


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def normalize_col(name: str) -> str:
    text_value = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    text_value = re.sub(r"_+", "_", text_value).strip("_")
    return text_value or "column"


def normalize_columns(cols: list[str]) -> list[str]:
    out: list[str] = []
    seen: dict[str, int] = {}
    for col in cols:
        base = normalize_col(col)
        idx = seen.get(base, 0)
        seen[base] = idx + 1
        out.append(base if idx == 0 else f"{base}_{idx + 1}")
    return out


def first_value(record: dict[str, Any], keys: list[str], default: Any = None) -> Any:
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


def to_float(value: Any) -> float | None:
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


def to_int(value: Any, default: int = -1) -> int:
    number = to_float(value)
    if number is None:
        return default
    return int(number)


def to_bool(value: Any) -> bool | None:
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
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return str(value)


def common_meta_row(
    disease: str,
    run_id: str,
    source_s3_uri: str,
    source_file_role: str,
    loaded_at: str,
) -> dict[str, Any]:
    return {
        "disease": disease,
        "run_id": run_id,
        "source_s3_uri": source_s3_uri,
        "source_file_role": source_file_role,
        "loaded_at": loaded_at,
    }


def resolve_config_file(disease_input: str, config_dir: Path) -> tuple[str, Path]:
    disease = str(disease_input).strip().upper()
    if disease not in ALIAS_TO_CONFIG:
        supported = ", ".join(sorted(ALIAS_TO_CONFIG))
        raise ValueError(f"Unsupported disease '{disease_input}'. Supported: {supported}")
    config_path = config_dir / ALIAS_TO_CONFIG[disease]
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    return disease, config_path


def resolve_s3_file_uri(cfg: dict[str, Any], rel_path: str) -> str:
    parent = normalize_prefix(str(cfg.get("s3_parent_prefix", "")))
    release = str(cfg.get("s3_release_prefix", "")).strip()
    rel = str(rel_path).strip().lstrip("/")
    if rel.startswith("s3://"):
        return normalize_s3_uri(rel)
    if release and release != "TODO_UNCONFIRMED":
        release_prefix = normalize_prefix(release)
        if rel.startswith("202") or rel.startswith("step") or rel.startswith("generated/") or rel.startswith("admet/"):
            return normalize_s3_uri(f"{parent}{rel}")
        return normalize_s3_uri(f"{release_prefix}{rel}")
    return normalize_s3_uri(f"{parent}{rel}")


def read_preview_dataframe(
    fs: s3fs.S3FileSystem,
    s3_uri: str,
    sample_rows: int = 20,
    limit_rows: int | None = None,
) -> pd.DataFrame:
    ext = Path(s3_uri.lower()).suffix
    nrows = limit_rows if limit_rows is not None else sample_rows
    nrows = max(1, int(nrows))
    if ext == ".csv":
        df = pd.read_csv(s3_uri, storage_options={"anon": False}, nrows=nrows)
    elif ext == ".tsv":
        df = pd.read_csv(s3_uri, storage_options={"anon": False}, sep="\t", nrows=nrows)
    elif ext == ".json":
        with fs.open(s3_uri, "rb") as handle:
            raw = json.load(handle)
        if isinstance(raw, list):
            df = pd.DataFrame(raw[:nrows])
        elif isinstance(raw, dict):
            df = pd.DataFrame([raw])
        else:
            df = pd.DataFrame([{"value": raw}])
    else:
        raise ValueError(f"Unsupported file extension for preview: {s3_uri}")
    out = df.copy()
    out.columns = normalize_columns([str(c) for c in out.columns])
    return out


def build_plan_entries(
    cfg: dict[str, Any],
    disease_input: str,
) -> tuple[str, str, list[dict[str, Any]], list[str]]:
    disease_code = str(cfg.get("disease", disease_input)).strip().upper()
    run_id = str(cfg.get("run_id", "")).strip()
    input_files = cfg.get("input_files", {})
    if not isinstance(input_files, dict):
        raise ValueError("input_files must be a mapping in disease config.")

    warnings: list[str] = []
    entries: list[dict[str, Any]] = []
    todo_count = 0

    for role, table_name in ROLE_TABLE_MAP.items():
        rel_path = str(input_files.get(role, "TODO_UNCONFIRMED")).strip()
        todo = rel_path == "TODO_UNCONFIRMED" or not rel_path
        if todo:
            todo_count += 1
            warnings.append(f"{role}: TODO_UNCONFIRMED")
            continue
        s3_uri = resolve_s3_file_uri(cfg, rel_path)
        entries.append(
            {
                "source_file_role": role,
                "target_table": table_name,
                "relative_path": rel_path,
                "s3_uri": s3_uri,
            }
        )

    if todo_count == len(ROLE_TABLE_MAP):
        raise ValueError("All mapped input_files are TODO_UNCONFIRMED; nothing actionable to load.")

    return disease_code, run_id, entries, warnings


def ensure_execute_allowed(disease_code: str, cfg: dict[str, Any]) -> None:
    if disease_code not in EXECUTE_ALLOWED_DISEASES:
        raise ValueError(
            f"--execute is restricted to pilot disease(s): {', '.join(sorted(EXECUTE_ALLOWED_DISEASES))}. "
            f"Requested={disease_code}"
        )
    release = str(cfg.get("s3_release_prefix", "")).strip()
    if not release or release == "TODO_UNCONFIRMED":
        raise ValueError("Execution blocked: s3_release_prefix is TODO_UNCONFIRMED.")
    status = str(cfg.get("status", "")).strip().lower()
    if "blocked" in status:
        raise ValueError(f"Execution blocked by status={cfg.get('status')}")


def db_table_columns(metadata_table: Table) -> set[str]:
    return {col.name for col in metadata_table.columns}


def convert_record(record: dict[str, Any]) -> dict[str, Any]:
    return {str(k): to_jsonable(v) for k, v in record.items()}


def parse_rows_for_role(
    role: str,
    df: pd.DataFrame | None,
    raw_json: Any,
    disease: str,
    run_id: str,
    source_s3_uri: str,
    loaded_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if role in {"candidate_unique", "candidate_tiered", "final_after_admet", "external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b", "admet_top30"} and df is None:
        return rows

    if role == "reproducibility_manifest":
        if raw_json is None:
            return rows
        rows.append(
            {
                **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                "manifest_name": Path(source_s3_uri).name,
                "manifest_sha256": None,
                "manifest_json": to_jsonable(raw_json),
                "payload": {"source_file_role": role, "loaded_at": loaded_at},
            }
        )
        return rows

    if role == "admet_summary":
        if isinstance(raw_json, dict):
            for key, value in raw_json.items():
                rows.append(
                    {
                        **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                        "summary_key": normalize_col(str(key)),
                        "summary_value": json.dumps(to_jsonable(value), ensure_ascii=False),
                        "payload": {"source_file_role": role, "loaded_at": loaded_at},
                    }
                )
        elif raw_json is not None:
            rows.append(
                {
                    **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                    "summary_key": "value",
                    "summary_value": json.dumps(to_jsonable(raw_json), ensure_ascii=False),
                    "payload": {"source_file_role": role, "loaded_at": loaded_at},
                }
            )
        return rows

    if role in {"copied_source_manifest", "ensemble_source_manifest"}:
        if df is None:
            return rows
        for raw in df.to_dict(orient="records"):
            record = convert_record(raw)
            rows.append(
                {
                    **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                    "artifact_name": str(first_value(record, ["artifact_name", "name", "source_name"], Path(source_s3_uri).name) or Path(source_s3_uri).name),
                    "artifact_type": str(first_value(record, ["artifact_type", "type"], "manifest") or "manifest"),
                    "artifact_uri": str(first_value(record, ["artifact_uri", "source_uri", "uri"], source_s3_uri) or source_s3_uri),
                    "artifact_hash": str(first_value(record, ["artifact_hash", "sha256"], "") or ""),
                    "model": str(first_value(record, ["model", "model_name"], "") or ""),
                    "source_name": str(first_value(record, ["source_name", "artifact_name", "name"], "") or ""),
                    "source_uri": str(first_value(record, ["source_uri", "artifact_uri", "uri"], "") or ""),
                    "weight": to_float(first_value(record, ["weight"])),
                    "payload": {**record, "source_file_role": role, "loaded_at": loaded_at},
                }
            )
        return rows

    if role in {"model_performance_summary", "model_performance_detailed"}:
        if df is None:
            return rows
        for raw in df.to_dict(orient="records"):
            record = convert_record(raw)
            model = str(first_value(record, ["model", "model_name", "estimator", "algorithm"], "") or "")
            phase = str(first_value(record, ["phase"], "") or "")
            family = str(first_value(record, ["family"], "") or "")
            source_model_dir = str(first_value(record, ["source_model_dir", "model_dir"], "") or "")
            split = str(first_value(record, ["split", "fold", "dataset"], "") or "")

            metric = first_value(record, ["metric", "metric_name"])
            metric_value = first_value(record, ["metric_value", "value", "score", "rmse", "r2", "cv_spearman"])
            if metric is not None and to_float(metric_value) is not None:
                rows.append(
                    {
                        **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                        "phase": phase,
                        "family": family,
                        "model": model,
                        "split": split,
                        "metric": str(metric),
                        "metric_value": to_float(metric_value),
                        "source_model_dir": source_model_dir,
                        "payload": {**record, "source_file_role": role, "loaded_at": loaded_at},
                    }
                )
                continue

            for col_name, col_value in record.items():
                if col_name in {"phase", "family", "model", "model_name", "estimator", "algorithm", "split", "fold", "dataset"}:
                    continue
                numeric = to_float(col_value)
                if numeric is None:
                    continue
                rows.append(
                    {
                        **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
                        "phase": phase,
                        "family": family,
                        "model": model,
                        "split": split,
                        "metric": str(col_name),
                        "metric_value": numeric,
                        "source_model_dir": source_model_dir,
                        "payload": {**record, "source_file_role": role, "loaded_at": loaded_at},
                    }
                )
        return rows

    if df is None:
        return rows

    for raw in df.to_dict(orient="records"):
        record = convert_record(raw)
        base_row = {
            **common_meta_row(disease, run_id, source_s3_uri, role, loaded_at),
            "drug_id": str(first_value(record, DRUG_ID_KEYS, "") or ""),
            "drug_name": str(first_value(record, DRUG_NAME_KEYS, "") or ""),
            "rank": to_int(first_value(record, RANK_KEYS, -1), default=-1),
            "score": to_float(first_value(record, SCORE_KEYS)),
            "payload": {**record, "source_file_role": role, "loaded_at": loaded_at},
        }

        if role == "candidate_unique":
            rows.append(base_row)
        elif role == "candidate_tiered":
            rows.append(
                {
                    **base_row,
                    "tier": str(first_value(record, ["tier", "tier_label", "clinical_tier"], "") or ""),
                }
            )
        elif role == "final_after_admet":
            rows.append(
                {
                    **base_row,
                    "final_verdict": str(first_value(record, ["final_verdict", "admet_verdict", "verdict", "status"], "") or ""),
                }
            )
        elif role == "admet_top30":
            rows.append(
                {
                    **base_row,
                    "admet_verdict": str(first_value(record, ["admet_verdict", "verdict", "admet"], "") or ""),
                    "hard_fail": to_bool(first_value(record, ["hard_fail", "hard_fail_flag"])),
                }
            )
        elif role in {"external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b"}:
            validation_source = role.replace("external_validation_", "")
            rows.append(
                {
                    **base_row,
                    "validation_source": validation_source,
                    "validation_score": to_float(first_value(record, ["validation_score", "score", "metabric_score"])),
                    "method": "method_a" if role.endswith("method_a") else ("method_b" if role.endswith("method_b") else ""),
                }
            )

    return rows


def filter_rows_for_table(rows: list[dict[str, Any]], table_name: str, table_columns: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row.get("payload") or {})
        if "source_file_role" in row:
            payload.setdefault("source_file_role", row["source_file_role"])
        if "loaded_at" in row:
            payload.setdefault("loaded_at", row["loaded_at"])
        filtered = {k: v for k, v in row.items() if k in table_columns}

        if "payload" in table_columns:
            existing_payload = filtered.get("payload")
            if isinstance(existing_payload, dict):
                payload = {**payload, **existing_payload}
            filtered["payload"] = payload

        if table_name == "external_validation_result":
            filtered.pop("method", None)
        if table_name == "model_metric":
            filtered.pop("split", None)
        if table_name == "source_artifact":
            filtered.pop("model", None)
            filtered.pop("source_name", None)
            filtered.pop("source_uri", None)
            filtered.pop("weight", None)
        if table_name == "ensemble_source_manifest":
            filtered.pop("artifact_name", None)
            filtered.pop("artifact_type", None)
            filtered.pop("artifact_uri", None)
            filtered.pop("artifact_hash", None)

        out.append(filtered)
    return out


def is_schema_confident(role: str, preview_df: pd.DataFrame | None, raw_json: Any) -> tuple[bool, str]:
    if role in {"reproducibility_manifest", "admet_summary"}:
        if raw_json is None:
            return False, "json payload could not be read"
        return True, "json payload available"
    if preview_df is None:
        return False, "preview dataframe unavailable"
    cols = {str(c).lower() for c in preview_df.columns}
    if role.startswith("candidate_") or role in {"final_after_admet", "admet_top30"}:
        if cols.intersection(set(DRUG_ID_KEYS + DRUG_NAME_KEYS)):
            return True, "drug identifier/name columns detected"
        return False, "missing drug identifier/name columns"
    if role.startswith("external_validation_"):
        if cols.intersection(set(DRUG_ID_KEYS + DRUG_NAME_KEYS)):
            return True, "external validation looks candidate-compatible"
        return False, "external validation schema not recognized"
    if role.startswith("model_performance_"):
        numeric_cols = 0
        for col in preview_df.columns:
            series = pd.to_numeric(preview_df[col], errors="coerce")
            if series.notna().any():
                numeric_cols += 1
        if numeric_cols > 0:
            return True, "numeric metric-like columns detected"
        return False, "no numeric metric-like columns detected"
    if role in {"copied_source_manifest", "ensemble_source_manifest"}:
        return True, "manifest-like tabular file"
    return True, "default pass-through"


def ensure_tables_exist(engine: Any, plan_entries: list[dict[str, Any]]) -> dict[str, Table]:
    inspector = inspect(engine)
    needed = sorted({entry["target_table"] for entry in plan_entries})
    missing = [name for name in needed if not inspector.has_table(name)]
    if missing:
        raise RuntimeError(f"Missing required target table(s): {', '.join(missing)}")
    metadata = MetaData()
    return {name: Table(name, metadata, autoload_with=engine) for name in needed}


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


def insert_rows(conn: Any, table: Table, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.execute(pg_insert(table).values(rows))
    return len(rows)


def read_json_file(fs: s3fs.S3FileSystem, s3_uri: str) -> Any:
    with fs.open(s3_uri, "rb") as handle:
        return json.load(handle)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO), format="[%(levelname)s] %(message)s")

    if args.execute:
        print("Execute mode is intentionally disabled in this scaffold. Review load plan and dry-run output first.")
        return 2

    script_root = Path(__file__).resolve().parents[2]
    config_dir = (script_root / args.config_dir).resolve() if not Path(args.config_dir).is_absolute() else Path(args.config_dir).resolve()

    disease_input, config_path = resolve_config_file(args.disease, config_dir)
    cfg = load_yaml(config_path)
    disease_code, run_id, plan_entries, plan_warnings = build_plan_entries(cfg, disease_input)
    s3_release_prefix = str(cfg.get("s3_release_prefix", "")).strip()
    status = str(cfg.get("status", "")).strip()

    if not s3_release_prefix or s3_release_prefix == "TODO_UNCONFIRMED":
        raise ValueError("s3_release_prefix is TODO_UNCONFIRMED. Update config before running loader.")
    if "blocked" in status.lower():
        raise ValueError(f"Loader blocked by config status: {status}")

    LOGGER.info("Config file: %s", config_path)
    LOGGER.info("Disease: %s (requested=%s)", disease_code, disease_input)
    LOGGER.info("Run ID: %s", run_id)
    LOGGER.info("S3 release prefix: %s", s3_release_prefix)
    LOGGER.info("Mode: %s", "execute" if args.execute else "dry-run")

    s3_client = boto3.client("s3")
    fs = s3fs.S3FileSystem(anon=False)

    dry_report: list[dict[str, Any]] = []
    execute_batches: list[dict[str, Any]] = []
    loaded_at = now_iso()

    for entry in plan_entries:
        role = entry["source_file_role"]
        s3_uri = entry["s3_uri"]
        target_table = entry["target_table"]
        preview_df: pd.DataFrame | None = None
        raw_json: Any = None
        exists = False
        size_bytes = s3_size(s3_client, s3_uri)
        warning_list: list[str] = []

        try:
            exists = s3_exists(s3_client, s3_uri)
        except Exception as exc:  # noqa: BLE001
            warning_list.append(f"s3 check failed: {exc}")

        if exists:
            try:
                if s3_uri.lower().endswith(".json"):
                    raw_json = read_json_file(fs, s3_uri)
                else:
                    preview_df = read_preview_dataframe(fs, s3_uri, sample_rows=20, limit_rows=args.limit_rows)
            except Exception as exc:  # noqa: BLE001
                warning_list.append(f"preview read failed: {exc}")
        else:
            warning_list.append("mapped file not found in S3")

        confident, confidence_reason = is_schema_confident(role, preview_df, raw_json)
        if role in {"external_validation_method_a", "external_validation_method_b"} and preview_df is not None:
            cols = {str(c).lower() for c in preview_df.columns}
            if "method" in cols or "method_score" in cols:
                target_table = "metabric_method_score"
                entry["target_table"] = target_table
                confidence_reason = f"{confidence_reason}; routed to metabric_method_score"
        expected_rows = None
        if preview_df is not None:
            expected_rows = int(len(preview_df))
        elif isinstance(raw_json, list):
            expected_rows = len(raw_json)
        elif isinstance(raw_json, dict):
            expected_rows = 1

        dry_item = {
            "source_file_role": role,
            "target_table": target_table,
            "s3_uri": s3_uri,
            "exists": exists,
            "size_bytes": size_bytes,
            "columns": list(preview_df.columns) if preview_df is not None else [],
            "sample_rows": preview_df.head(3).to_dict(orient="records") if preview_df is not None else [],
            "expected_rows_preview": expected_rows,
            "schema_confident": confident,
            "schema_reason": confidence_reason,
            "warnings": warning_list,
        }
        dry_report.append(dry_item)

    print("\n[DRY-RUN PLAN]")
    for item in dry_report:
        print(
            f"- role={item['source_file_role']} table={item['target_table']} exists={item['exists']} "
            f"rows_preview={item['expected_rows_preview']} confident={item['schema_confident']}"
        )
        if item["warnings"]:
            for warning in item["warnings"]:
                print(f"  warning: {warning}")

    for warning in plan_warnings:
        LOGGER.warning(warning)

    if args.dry_run:
        print("\n[ok] Dry-run completed. No PostgreSQL writes were performed.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
