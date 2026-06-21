#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import yaml


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

INCLUDED_ROLE_TARGETS: dict[str, str] = {
    "candidate_tiered": "drug_candidate_tier",
    "final_after_admet": "final_candidate_result",
    "external_validation_top30": "external_validation_result",
    "admet_top30": "admet_result",
}

EXPLICITLY_EXCLUDED_ROLES = [
    "candidate_unique",
    "model_performance_summary",
    "model_performance_detailed",
    "admet_summary",
    "reproducibility_manifest",
    "ensemble_source_manifest",
]

PAYLOAD_COLUMN_CANDIDATES = ["payload", "payload_json", "raw_payload", "metadata", "extra_json"]
SKIP_INSERT_COLUMNS = {"id", "created_at", "updated_at"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build COAD read-only safe write-plan preview")
    parser.add_argument("--disease", default="COAD")
    parser.add_argument("--config-dir", default="configs/diseases")
    parser.add_argument("--mapping-spec", default="outputs/config_validation/coad_postgres_column_mapping_spec.json")
    parser.add_argument("--schema-report", default="outputs/config_validation/coad_postgres_target_schema_report.json")
    parser.add_argument("--limit-rows", type=int, default=10)
    parser.add_argument("--output", default="outputs/config_validation/coad_safe_write_plan_preview.json")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_project_root(start: Path | None = None) -> Path:
    start_path = (start or Path.cwd()).resolve()
    for candidate in [start_path, *start_path.parents]:
        if (candidate / "configs" / "diseases").exists() and (candidate / "scripts").exists():
            return candidate
    return start_path


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "cp949"):
        try:
            parsed = json.loads(raw.decode(encoding))
            if not isinstance(parsed, dict):
                raise ValueError("JSON root must be a mapping.")
            return parsed
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(f"Failed to parse JSON {path}: {last_error}")


def resolve_config_file(disease_input: str, config_dir: Path) -> tuple[str, Path]:
    disease = str(disease_input).strip().upper()
    if disease not in ALIAS_TO_CONFIG:
        raise ValueError(f"Unsupported disease '{disease_input}'.")
    cfg_path = (config_dir / ALIAS_TO_CONFIG[disease]).resolve()
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    return disease, cfg_path


def normalize_s3_uri(uri: str) -> str:
    text_value = str(uri).strip().replace("\\", "/")
    if text_value.startswith("s3:/") and not text_value.startswith("s3://"):
        text_value = text_value.replace("s3:/", "s3://", 1)
    if not text_value.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {uri}")
    while "///" in text_value:
        text_value = text_value.replace("///", "//")
    return text_value


def normalize_prefix(uri: str) -> str:
    out = normalize_s3_uri(uri)
    if not out.endswith("/"):
        out += "/"
    return out


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


def parse_s3_uri(uri: str) -> tuple[str, str]:
    normalized = normalize_s3_uri(uri)
    bucket_key = normalized[len("s3://") :]
    bucket, key = bucket_key.split("/", 1)
    return bucket, key


def decode_with_fallback(raw_bytes: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return raw_bytes.decode(enc), enc
        except Exception:  # noqa: BLE001
            continue
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8"


def detect_delimiter(csv_text: str) -> str:
    sample = "\n".join(csv_text.splitlines()[:20])
    if not sample.strip():
        return ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return str(dialect.delimiter)
    except Exception:  # noqa: BLE001
        return ","


def read_csv_sample_from_s3(s3_client: Any, s3_uri: str, limit_rows: int) -> tuple[list[dict[str, Any]], str]:
    bucket, key = parse_s3_uri(s3_uri)
    body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
    csv_bytes = body
    if key.lower().endswith(".gz") or s3_uri.lower().endswith(".csv.gz"):
        csv_bytes = gzip.decompress(body)
    csv_text, encoding = decode_with_fallback(csv_bytes)
    delimiter = detect_delimiter(csv_text)
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(reader):
        if idx >= max(1, int(limit_rows)):
            break
        parsed: dict[str, Any] = {}
        for k, v in (row or {}).items():
            key_name = str(k).strip() if k is not None else ""
            parsed[key_name] = None if v is None else str(v)
        rows.append(parsed)
    return rows, encoding


def normalize_col(name: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(name).strip())
    while "__" in base:
        base = base.replace("__", "_")
    return base.strip("_")


def row_lookup(row: dict[str, Any]) -> dict[str, Any]:
    lookup: dict[str, Any] = {}
    for k, v in row.items():
        raw_key = str(k)
        lookup[raw_key] = v
        lookup[raw_key.lower()] = v
        lookup[normalize_col(raw_key)] = v
    return lookup


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return int(float(text_value))
    except Exception:  # noqa: BLE001
        return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return float(text_value)
    except Exception:  # noqa: BLE001
        return None


def to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "t", "yes", "y", "pass", "passed"}:
        return True
    if text_value in {"0", "false", "f", "no", "n", "fail", "failed"}:
        return False
    return None


def first_non_empty(lookup: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = lookup.get(key)
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value == "":
            continue
        return value
    return None


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def schema_table_map(schema_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    table_reports = schema_report.get("table_reports", [])
    out: dict[str, dict[str, Any]] = {}
    if isinstance(table_reports, list):
        for item in table_reports:
            if not isinstance(item, dict):
                continue
            table_name = str(item.get("table_name", "")).strip()
            if table_name:
                out[table_name] = item
    return out


def mapping_by_role(mapping_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mappings = mapping_spec.get("mappings", [])
    out: dict[str, dict[str, Any]] = {}
    if isinstance(mappings, list):
        for item in mappings:
            if not isinstance(item, dict):
                continue
            if not bool(item.get("execute_ready")):
                continue
            role = str(item.get("source_file_role", "")).strip()
            if role:
                out[role] = item
    return out


def infer_validation_source(role: str, source_s3_uri: str, lookup: dict[str, Any]) -> str:
    explicit = first_non_empty(lookup, ["validation_source", "source", "method"])
    if explicit is not None:
        return str(explicit)
    if role.startswith("external_validation_"):
        return role.replace("external_validation_", "")
    name = Path(source_s3_uri).name.lower()
    if "top30" in name:
        return "top30"
    return "external_validation"


def pick_score(role: str, lookup: dict[str, Any]) -> float | None:
    role_priority: dict[str, list[str]] = {
        "candidate_tiered": ["pred_ic50_mean", "score", "ensemble_score"],
        "final_after_admet": ["pred_ic50_mean", "safety_score", "final_score", "ensemble_score", "score"],
        "external_validation_top30": ["validation_score", "ensemble_score", "pred_ic50_mean", "score"],
        "admet_top30": ["safety_score", "score", "pred_ic50_mean"],
    }
    candidates = role_priority.get(role, ["score", "pred_ic50_mean", "ensemble_score"])
    raw_value = first_non_empty(lookup, candidates)
    return to_float(raw_value)


def normalize_unique_constraints(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def choose_unique_constraint_columns(table_schema_row: dict[str, Any]) -> list[str]:
    constraints = normalize_unique_constraints(table_schema_row.get("unique_constraints"))
    if not constraints:
        return []
    first = constraints[0]
    cols = first.get("columns", [])
    if isinstance(cols, list):
        return [str(c) for c in cols]
    return []


def validate_row(
    proposed_row: dict[str, Any],
    unique_constraint_columns: list[str],
    payload_column_name: str | None,
) -> dict[str, Any]:
    missing_unique_values: list[str] = []
    for col in unique_constraint_columns:
        value = proposed_row.get(col)
        if value is None:
            missing_unique_values.append(col)
            continue
        if isinstance(value, str) and value.strip() == "":
            missing_unique_values.append(col)

    payload_serializable = True
    payload_error = None
    if payload_column_name is not None:
        try:
            json.dumps(proposed_row.get(payload_column_name))
        except Exception as exc:  # noqa: BLE001
            payload_serializable = False
            payload_error = str(exc)

    valid = len(missing_unique_values) == 0 and payload_serializable
    notes: list[str] = []
    if missing_unique_values:
        notes.append("Missing values for unique-constraint columns: " + ", ".join(missing_unique_values))
    if not payload_serializable:
        notes.append(f"Payload JSON serialization failed: {payload_error}")

    return {
        "valid": valid,
        "unique_constraint_fields_populated": len(missing_unique_values) == 0,
        "missing_unique_constraint_values": missing_unique_values,
        "payload_json_serializable": payload_serializable,
        "notes": notes,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# COAD Safe Write-Plan Preview")
    lines.append("")
    lines.append("## Executive summary")
    lines.append(f"- generated_at: {report.get('generated_at')}")
    lines.append(f"- disease: {report.get('disease')}")
    lines.append(f"- run_id: {report.get('run_id')}")
    lines.append(f"- execute_mode: {report.get('execute_mode')}")
    lines.append(f"- included_roles: {', '.join(report.get('included_roles') or [])}")
    lines.append("")
    lines.append("## Included roles")
    for role in report.get("included_roles", []):
        lines.append(f"- {role}")
    if not report.get("included_roles"):
        lines.append("- none")

    lines.append("")
    lines.append("## Excluded roles")
    for role in report.get("excluded_roles", []):
        lines.append(f"- {role}")
    if not report.get("excluded_roles"):
        lines.append("- none")

    lines.append("")
    lines.append("## Table-by-table proposed insert preview")
    for plan in report.get("plans", []):
        lines.append("")
        lines.append(f"### {plan.get('source_file_role')} -> {plan.get('target_table')}")
        lines.append(f"- source_s3_uri: `{plan.get('source_s3_uri')}`")
        lines.append(f"- rows_previewed: {len(plan.get('proposed_rows') or [])}")
        lines.append(f"- execute_ready_preview: {plan.get('execute_ready_preview')}")
        lines.append(f"- unique_constraint: {json.dumps(plan.get('unique_constraint') or [])}")
        lines.append(f"- target_columns: {json.dumps(plan.get('target_columns') or [])}")
        lines.append(f"- payload_column_used: {plan.get('payload_column_used')}")
        if plan.get("proposed_rows"):
            lines.append("- sample proposed row:")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(plan.get("proposed_rows")[0], indent=2, ensure_ascii=False))
            lines.append("```")
        else:
            lines.append("- sample proposed row: none")
        blockers = plan.get("blockers") or []
        if blockers:
            lines.append("- blockers:")
            for blocker in blockers:
                lines.append(f"  - {blocker}")
        else:
            lines.append("- blockers: none")

    lines.append("")
    lines.append("## Unique constraint readiness")
    for plan in report.get("plans", []):
        validations = plan.get("row_validation") or []
        all_unique_ready = all(bool(v.get("unique_constraint_fields_populated")) for v in validations) if validations else False
        lines.append(f"- {plan.get('target_table')}: {all_unique_ready}")

    lines.append("")
    lines.append("## Payload strategy")
    lines.append("- All proposed rows include payload with:")
    lines.append("  - source_file_role")
    lines.append("  - loaded_at_preview")
    lines.append("  - original_row")
    lines.append("  - unmapped_columns")
    lines.append("  - mapping_notes")

    lines.append("")
    lines.append("## Blockers")
    any_blockers = False
    for plan in report.get("plans", []):
        blockers = plan.get("blockers") or []
        if not blockers:
            continue
        any_blockers = True
        lines.append(f"- {plan.get('target_table')}: {'; '.join(blockers)}")
    if not any_blockers:
        lines.append("- none")

    lines.append("")
    lines.append("## Next actions")
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")
    if not report.get("next_actions"):
        lines.append("- none")

    lines.append("")
    lines.append("This is a read-only write-plan preview. No PostgreSQL writes were performed.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_root = find_project_root(Path.cwd())
    config_dir = (project_root / args.config_dir).resolve() if not Path(args.config_dir).is_absolute() else Path(args.config_dir).resolve()
    disease_input, config_path = resolve_config_file(args.disease, config_dir)
    cfg = load_yaml(config_path)

    mapping_spec_path = (
        Path(args.mapping_spec).resolve()
        if Path(args.mapping_spec).is_absolute()
        else (project_root / args.mapping_spec).resolve()
    )
    schema_report_path = (
        Path(args.schema_report).resolve()
        if Path(args.schema_report).is_absolute()
        else (project_root / args.schema_report).resolve()
    )
    profile_path = (project_root / "outputs" / "config_validation" / "coad_input_column_profile.json").resolve()
    output_json_path = Path(args.output).resolve() if Path(args.output).is_absolute() else (project_root / args.output).resolve()
    output_md_path = (project_root / "docs" / "coad_safe_write_plan_preview.md").resolve()

    if not mapping_spec_path.exists():
        print(f"[error] mapping spec not found: {mapping_spec_path}")
        return 1
    if not schema_report_path.exists():
        print(f"[error] schema report not found: {schema_report_path}")
        return 1
    if not profile_path.exists():
        print(f"[error] input column profile not found: {profile_path}")
        return 1

    mapping_spec = load_json(mapping_spec_path)
    schema_report = load_json(schema_report_path)
    profile_report = load_json(profile_path)

    disease_code = str(cfg.get("disease", disease_input)).strip().upper()
    run_id = str(cfg.get("run_id", "")).strip()
    input_files = cfg.get("input_files", {})
    if not isinstance(input_files, dict):
        print("[error] input_files must be a mapping in disease config.")
        return 1

    mappings_by_role = mapping_by_role(mapping_spec)
    schema_by_table = schema_table_map(schema_report)
    profile_by_role = {
        str(item.get("role")): item for item in (profile_report.get("profiles") or []) if isinstance(item, dict)
    }

    s3_client = boto3.client("s3")
    loaded_at_preview = now_iso()

    included_roles: list[str] = []
    excluded_roles: list[str] = []
    plans: list[dict[str, Any]] = []
    rows_previewed: dict[str, int] = {}

    for excluded in EXPLICITLY_EXCLUDED_ROLES:
        excluded_roles.append(f"{excluded}: explicitly excluded")

    for role, target_table in INCLUDED_ROLE_TARGETS.items():
        mapping_entry = mappings_by_role.get(role)
        if mapping_entry is None:
            excluded_roles.append(f"{role}: not execute-ready in mapping spec")
            continue

        rel_path = str(input_files.get(role, "TODO_UNCONFIRMED")).strip()
        if rel_path == "" or rel_path == "TODO_UNCONFIRMED":
            excluded_roles.append(f"{role}: TODO_UNCONFIRMED")
            continue

        table_schema_row = schema_by_table.get(target_table)
        blockers: list[str] = []
        if table_schema_row is None:
            blockers.append(f"Target table '{target_table}' not found in schema report")
            actual_columns: list[str] = []
            unique_constraint: list[str] = []
            payload_column_name = None
        else:
            actual_columns = [str(c) for c in (table_schema_row.get("actual_columns") or [])]
            unique_constraint = choose_unique_constraint_columns(table_schema_row)
            payload_column_name = next((c for c in PAYLOAD_COLUMN_CANDIDATES if c in set(actual_columns)), None)
            if payload_column_name is None:
                blockers.append("No payload-like column available in target table")

        source_s3_uri = resolve_s3_file_uri(cfg, rel_path)
        raw_rows: list[dict[str, Any]] = []
        encoding_used = None
        try:
            raw_rows, encoding_used = read_csv_sample_from_s3(s3_client, source_s3_uri, args.limit_rows)
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"S3 read failed: {exc}")

        proposed_rows: list[dict[str, Any]] = []
        row_validation: list[dict[str, Any]] = []

        for idx, source_row in enumerate(raw_rows):
            lookup = row_lookup(source_row)
            drug_id_raw = first_non_empty(lookup, ["canonical_drug_id", "drug_id"])
            drug_name_raw = first_non_empty(lookup, ["drug_name", "drug_name_norm"])
            rank_raw = first_non_empty(lookup, ["rank", "final_rank", "admet_rank", "ensemble_rank", "step7_final_rank", "rank_admet"])
            tier_raw = first_non_empty(lookup, ["tier_20260428_colon_v2", "tier"])
            score_raw = pick_score(role, lookup)
            final_verdict_raw = first_non_empty(lookup, ["final_verdict", "verdict", "admet_verdict"])
            validation_source_raw = infer_validation_source(role, source_s3_uri, lookup)
            validation_score_raw = first_non_empty(lookup, ["validation_score", "score", "ensemble_score", "pred_ic50_mean"])
            admet_verdict_raw = first_non_empty(lookup, ["admet_verdict", "verdict"])
            hard_fail_raw = first_non_empty(lookup, ["hard_fail"])

            mapping_notes: list[str] = []
            if score_raw is None:
                mapping_notes.append("score could not be inferred from preferred score fields")
            if role == "external_validation_top30" and validation_score_raw is None:
                mapping_notes.append("validation_score defaulted to null")

            candidate = {
                "disease": disease_code,
                "run_id": run_id,
                "source_s3_uri": source_s3_uri,
                "drug_id": str(drug_id_raw) if drug_id_raw is not None else None,
                "drug_name": str(drug_name_raw) if drug_name_raw is not None else None,
                "rank": to_int(rank_raw),
                "tier": str(tier_raw) if tier_raw is not None else None,
                "score": score_raw,
                "final_verdict": str(final_verdict_raw) if final_verdict_raw is not None else None,
                "validation_source": str(validation_source_raw) if validation_source_raw is not None else None,
                "validation_score": to_float(validation_score_raw),
                "admet_verdict": str(admet_verdict_raw) if admet_verdict_raw is not None else None,
                "hard_fail": to_bool(hard_fail_raw),
            }

            if role == "admet_top30" and candidate.get("hard_fail") is None:
                candidate["hard_fail"] = False

            mapped_keys_used = {k for k, v in candidate.items() if v is not None}
            unmapped_columns = sorted([col for col in source_row.keys() if normalize_col(col) not in mapped_keys_used and col not in mapped_keys_used])

            payload_obj = {
                "source_file_role": role,
                "loaded_at_preview": loaded_at_preview,
                "encoding_used": encoding_used,
                "original_row": to_jsonable(source_row),
                "unmapped_columns": unmapped_columns,
                "mapping_notes": mapping_notes,
            }

            proposed_row: dict[str, Any] = {}
            allowed_columns = [c for c in actual_columns if c not in SKIP_INSERT_COLUMNS]
            for col in allowed_columns:
                if col in PAYLOAD_COLUMN_CANDIDATES:
                    continue
                if col in candidate:
                    proposed_row[col] = candidate[col]

            if payload_column_name is not None and payload_column_name in allowed_columns:
                proposed_row[payload_column_name] = payload_obj

            validation = validate_row(proposed_row, unique_constraint, payload_column_name)
            validation["row_index"] = idx
            row_validation.append(validation)
            proposed_rows.append(proposed_row)

        if not raw_rows and not blockers:
            blockers.append("No source rows were sampled from S3")

        execute_ready_preview = len(blockers) == 0 and all(bool(v.get("valid")) for v in row_validation) and len(proposed_rows) > 0

        plan = {
            "source_file_role": role,
            "target_table": target_table,
            "source_s3_uri": source_s3_uri,
            "target_columns": actual_columns,
            "unique_constraint": unique_constraint,
            "payload_column_used": payload_column_name,
            "proposed_rows": proposed_rows,
            "row_validation": row_validation,
            "blockers": blockers,
            "execute_ready_preview": execute_ready_preview,
        }
        plans.append(plan)
        rows_previewed[target_table] = len(proposed_rows)
        included_roles.append(role)

    # Include TODO roles and non-included config roles in exclusion list for transparency.
    for role_name, role_path in input_files.items():
        role_name_str = str(role_name)
        role_path_str = str(role_path).strip()
        if role_name_str in INCLUDED_ROLE_TARGETS:
            continue
        if role_name_str in EXPLICITLY_EXCLUDED_ROLES:
            continue
        if role_path_str == "TODO_UNCONFIRMED" or role_path_str == "":
            excluded_roles.append(f"{role_name_str}: TODO_UNCONFIRMED")
        else:
            excluded_roles.append(f"{role_name_str}: not included in safe write-plan scope")

    next_actions: list[str] = []
    for plan in plans:
        if plan["execute_ready_preview"]:
            continue
        for blocker in plan.get("blockers", []):
            next_actions.append(f"{plan['target_table']}: {blocker}")
        for item in plan.get("row_validation", []):
            if not item.get("valid"):
                next_actions.extend([f"{plan['target_table']} row {item.get('row_index')}: {note}" for note in item.get("notes", [])])

    if not next_actions:
        next_actions.append("All proposed rows passed preview validation for included execute-ready roles.")

    report = {
        "disease": disease_code,
        "run_id": run_id,
        "execute_mode": "disabled",
        "generated_at": now_iso(),
        "rows_previewed": rows_previewed,
        "included_roles": included_roles,
        "plans": plans,
        "excluded_roles": sorted(set(excluded_roles)),
        "next_actions": next_actions,
        "note": "This is a read-only write-plan preview. No PostgreSQL writes were performed.",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(output_md_path, report)

    print(f"[ok] JSON report: {output_json_path}")
    print(f"[ok] Markdown report: {output_md_path}")
    print(f"[ok] Included roles: {', '.join(included_roles) if included_roles else 'none'}")
    print("This is a read-only write-plan preview. No PostgreSQL writes were performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
