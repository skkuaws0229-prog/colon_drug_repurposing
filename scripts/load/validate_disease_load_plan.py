#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import yaml
from botocore.exceptions import ClientError
from sqlalchemy import create_engine, inspect


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate disease load plan before generic PG loading")
    parser.add_argument("--disease", required=True)
    parser.add_argument("--config-dir", default="configs/diseases")
    parser.add_argument("--check-db", action="store_true")
    parser.add_argument("--check-s3", action="store_true")
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


def s3_exists(s3_client: Any, uri: str) -> tuple[bool, str]:
    bucket, key = parse_s3_uri(uri)
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True, ""
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False, "not_found"
        return False, f"s3_error:{code}"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


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


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    config_dir = (root / args.config_dir).resolve() if not Path(args.config_dir).is_absolute() else Path(args.config_dir).resolve()

    disease_input, config_path = resolve_config_file(args.disease, config_dir)
    cfg = load_yaml(config_path)
    disease_code = str(cfg.get("disease", disease_input)).upper()
    run_id = str(cfg.get("run_id", ""))
    status = str(cfg.get("status", ""))
    release_prefix = str(cfg.get("s3_release_prefix", "")).strip()
    input_files = cfg.get("input_files", {})
    if not isinstance(input_files, dict):
        raise ValueError("input_files must be a mapping in config.")

    warnings: list[str] = []
    errors: list[str] = []

    if not release_prefix or release_prefix == "TODO_UNCONFIRMED":
        warnings.append("s3_release_prefix is TODO_UNCONFIRMED")

    mapped_files: list[dict[str, Any]] = []
    todo_count = 0
    for role, table_name in ROLE_TABLE_MAP.items():
        rel = str(input_files.get(role, "TODO_UNCONFIRMED")).strip()
        if rel == "TODO_UNCONFIRMED" or not rel:
            todo_count += 1
            mapped_files.append(
                {
                    "role": role,
                    "target_table": table_name,
                    "relative_path": rel or "TODO_UNCONFIRMED",
                    "s3_uri": None,
                    "s3_exists": None,
                    "s3_error": None,
                }
            )
            continue
        s3_uri = resolve_s3_file_uri(cfg, rel)
        mapped_files.append(
            {
                "role": role,
                "target_table": table_name,
                "relative_path": rel,
                "s3_uri": s3_uri,
                "s3_exists": None,
                "s3_error": None,
            }
        )

    if todo_count == len(ROLE_TABLE_MAP):
        errors.append("All mapped input_files are TODO_UNCONFIRMED.")

    if args.check_s3:
        s3_client = boto3.client("s3")
        for item in mapped_files:
            s3_uri = item.get("s3_uri")
            if not s3_uri:
                continue
            exists, err = s3_exists(s3_client, s3_uri)
            item["s3_exists"] = exists
            item["s3_error"] = err or None
            if not exists:
                warnings.append(f"missing S3 object: {s3_uri}")

    db_tables_checked: list[dict[str, Any]] = []
    if args.check_db:
        try:
            engine = create_engine(build_database_url(), future=True)
            inspector = inspect(engine)
            for table_name in sorted(set(ROLE_TABLE_MAP.values())):
                exists = inspector.has_table(table_name)
                db_tables_checked.append({"table_name": table_name, "exists": exists})
                if not exists:
                    errors.append(f"missing PostgreSQL table: {table_name}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"database check failed: {exc}")

    report = {
        "generated_at": now_iso(),
        "disease_requested": disease_input,
        "disease": disease_code,
        "run_id": run_id,
        "status": status,
        "config_path": str(config_path),
        "s3_parent_prefix": cfg.get("s3_parent_prefix"),
        "s3_release_prefix": release_prefix,
        "check_s3": args.check_s3,
        "check_db": args.check_db,
        "mapped_files": mapped_files,
        "db_tables_checked": db_tables_checked,
        "warnings": warnings,
        "errors": errors,
    }

    out_dir = root / "outputs" / "config_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{disease_code.lower()}_load_plan.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"disease={disease_code} run_id={run_id} status={status}")
    print(f"release_prefix={release_prefix}")
    print(f"mapped_files={len(mapped_files)} todo={todo_count}")
    if args.check_s3:
        missing = sum(1 for x in mapped_files if x.get("s3_exists") is False)
        print(f"s3_checked=yes missing={missing}")
    if args.check_db:
        missing_tables = [x["table_name"] for x in db_tables_checked if not x["exists"]]
        print(f"db_checked=yes missing_tables={len(missing_tables)}")
    if warnings:
        print("warnings:")
        for w in warnings[:10]:
            print(f"- {w}")
    if errors:
        print("errors:")
        for e in errors:
            print(f"- {e}")
        print(f"[error] load-plan validation failed. report={out_path}")
        return 1
    print(f"[ok] load-plan validation passed. report={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

