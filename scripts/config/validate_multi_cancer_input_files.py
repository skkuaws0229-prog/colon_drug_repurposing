#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

import boto3
import yaml


SCORING_WEIGHTS = {
    "file_exists": 25,
    "role_clear_from_filename": 20,
    "yaml_key_matches_file_role": 20,
    "schema_compatible_with_loader": 25,
    "load_risk_low": 10,
}

EXPECTED_ROLES = [
    "candidate_unique",
    "candidate_tiered",
    "final_after_admet",
    "model_performance_summary",
    "model_performance_detailed",
    "ensemble_validation_summary",
    "ensemble_source_manifest",
    "external_validation_scored",
    "external_validation_validated",
    "external_validation_method_a",
    "external_validation_method_b",
    "admet_detailed",
    "admet_summary",
    "admet_matches",
    "copied_source_manifest",
    "reproducibility_manifest",
]

STANDARD_KEY_MAP = {
    "candidate_unique": "candidate_unique",
    "candidate_tiered": "candidate_tiered",
    "final_after_admet": "final_after_admet",
    "model_performance_summary": "model_performance_summary",
    "model_performance_detailed": "model_performance_detailed",
    "ensemble_validation_summary": "ensemble_validation_summary",
    "ensemble_source_manifest": "ensemble_source_manifest",
    "external_validation_scored": "external_validation_scored",
    "external_validation_validated": "external_validation_validated",
    "external_validation_method_a": "external_validation_method_a",
    "external_validation_method_b": "external_validation_method_b",
    "admet_detailed": "admet_detailed",
    "admet_summary": "admet_summary",
    "admet_matches": "admet_matches",
    "copied_source_manifest": "copied_source_manifest",
    "reproducibility_manifest": "reproducibility_manifest",
    "external_validation_top30": "external_validation_scored",
    "external_validation_top15": "external_validation_validated",
    "admet_top30": "admet_detailed",
}

PILOT_REQUIRED_GROUPS = [
    ["candidate_tiered"],
    ["final_after_admet"],
    ["model_performance_summary"],
    ["admet_detailed", "admet_summary"],
    ["reproducibility_manifest", "copied_source_manifest"],
]

ROLE_COLUMN_GROUPS: dict[str, list[list[str]]] = {
    "candidate_tiered": [
        ["drug_name", "drug", "compound_name", "compound", "chembl_id", "drug_id"],
        ["rank", "final_rank", "candidate_rank"],
        ["tier", "candidate_tier"],
        ["score", "final_score", "ensemble_score", "model_score"],
    ],
    "final_after_admet": [
        ["drug_name", "drug", "compound_name", "compound", "chembl_id", "drug_id"],
        ["rank", "final_rank"],
        ["final_score", "score", "ensemble_score"],
        ["admet_score", "admet_risk", "pass_fail", "admet_pass"],
    ],
    "model_performance_summary": [
        ["model", "model_name", "model_family"],
        ["metric", "metric_name"],
        ["metric_value", "value", "score"],
        ["split", "phase", "fold", "cv_type"],
    ],
    "model_performance_detailed": [
        ["model", "model_name", "model_family"],
        ["metric", "metric_name"],
        ["metric_value", "value", "score"],
        ["fold", "split", "phase", "config"],
    ],
}

ADMET_DETAIL_TOKENS = [
    "herg",
    "dili",
    "ames",
    "cyp",
    "lipinski",
    "tpsa",
    "logp",
]

MANIFEST_COLS = ["source", "source_file", "s3_uri", "file_name", "run_id", "created_at", "disease"]
SUMMARY_HINT_TOKENS = ["summary", "count", "counts", "risk", "match", "matches", "pass", "fail"]

ROLE_RULES: list[tuple[str, list[list[str]]]] = [
    (
        "candidate_tiered",
        [
            ["top30", "tiered", "candidate"],
            ["top30", "tiered"],
            ["top30", "tier1234"],
            ["top30", "tier1", "tier2", "tier3", "tier4"],
        ],
    ),
    ("candidate_unique", [["unique", "candidate"]]),
    (
        "final_after_admet",
        [
            ["final15"],
            ["final", "after", "admet"],
            ["top15", "admet", "pass"],
            ["top15", "admet", "filtered"],
            ["top15", "admet", "with", "vt"],
            ["top15", "admet", "with", "admet"],
            ["top15", "drugs", "with", "admet"],
        ],
    ),
    (
        "model_performance_summary",
        [
            ["model", "performance", "summary"],
            ["metrics", "summary"],
            ["metrics", "checklist"],
            ["overfit", "table"],
        ],
    ),
    ("model_performance_detailed", [["model", "performance", "detailed"]]),
    ("ensemble_validation_summary", [["ensemble", "validation", "summary"]]),
    ("ensemble_source_manifest", [["ensemble", "source", "manifest"]]),
    ("external_validation_scored", [["metabric", "scored"], ["external", "validation", "scored"]]),
    ("external_validation_validated", [["validated"]]),
    ("external_validation_method_a", [["method", "a"], ["method_a"]]),
    ("external_validation_method_b", [["method", "b"], ["method_b"]]),
    ("admet_detailed", [["admet", "detailed"]]),
    ("admet_summary", [["admet", "summary"]]),
    ("admet_matches", [["admet", "matches"]]),
    (
        "copied_source_manifest",
        [
            ["copied_source_manifest"],
            ["copied", "source", "manifest"],
            ["source", "manifest"],
        ],
    ),
    (
        "reproducibility_manifest",
        [
            ["reproducibility_manifest"],
            ["repro", "manifest"],
            ["reproducibility", "manifest"],
            ["reproduction", "manifest"],
            ["s3", "upload", "manifest"],
        ],
    ),
]

DEFAULT_DISEASE_PREFIXES: dict[str, list[str]] = {
    "COAD": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/COLON/",
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/",
    ],
    "LUNG": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/",
    ],
    "LIHC": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LIVER/",
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/",
    ],
    "PAAD": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PAAD/",
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/",
    ],
    "HNSC": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/",
    ],
    "STAD": [
        "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/",
    ],
}

DISEASE_CONFIG_FILES = {
    "COAD": "colon.yaml",
    "LIHC": "liver.yaml",
    "LUNG": "lung.yaml",
    "PAAD": "pdac.yaml",
    "HNSC": "hnsc.yaml",
    "STAD": "stad.yaml",
}


@dataclass
class SchemaResult:
    score: int
    status: str
    reason: str
    matched_columns: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").strip()


def normalize_prefix(prefix: str) -> str:
    p = normalize_path(prefix)
    if p.startswith("s3:/") and not p.startswith("s3://"):
        p = p.replace("s3:/", "s3://", 1)
    if not p.endswith("/"):
        p += "/"
    return p


def parse_s3_uri(uri: str) -> tuple[str, str]:
    n = normalize_prefix(uri)
    body = n[len("s3://") :]
    bucket, key_prefix = body.split("/", 1)
    return bucket, key_prefix


def get_extension(key: str) -> str:
    lower = key.lower()
    if lower.endswith(".csv.gz"):
        return ".csv.gz"
    if lower.endswith(".jsonl"):
        return ".jsonl"
    return Path(lower).suffix


def is_obvious_exclusion(key: str, size_bytes: int) -> tuple[bool, str]:
    lower = key.lower()
    base = lower.rsplit("/", 1)[-1]
    if key.endswith("/") or (size_bytes == 0 and "." not in base):
        return True, "directory_or_folder_marker"
    if "/logs/" in lower or "/log/" in lower or base.endswith(".log"):
        return True, "log_file"
    if "/tmp/" in lower or "/temp/" in lower or base.endswith(".tmp"):
        return True, "temp_file"
    if "/debug/" in lower or "_debug" in base or "debug_" in base:
        return True, "debug_file"
    if "/intermediate/" in lower or "intermediate" in base:
        return True, "intermediate_file"
    if base.startswith(".") or base.endswith(".swp"):
        return True, "hidden_or_editor_artifact"
    return False, ""


def tokenize_filename(file_name: str) -> set[str]:
    tokens = [t for t in re.split(r"[^a-z0-9]+", file_name.lower()) if t]
    return set(tokens)


def infer_role(file_name: str) -> tuple[str | None, list[str], bool]:
    tokens = tokenize_filename(file_name)
    matched_roles: list[str] = []
    for role, conditions in ROLE_RULES:
        for cond in conditions:
            if all(token in tokens for token in cond):
                matched_roles.append(role)
                break
    unique = sorted(set(matched_roles))
    if not unique:
        return None, [], False
    if len(unique) == 1:
        return unique[0], unique, True
    if "external_validation_method_a" in unique:
        return "external_validation_method_a", unique, False
    if "external_validation_method_b" in unique:
        return "external_validation_method_b", unique, False
    if "external_validation_validated" in unique and len(unique) > 1:
        candidates = [r for r in unique if r != "external_validation_validated"]
        if len(candidates) == 1:
            return candidates[0], unique, False
    return unique[0], unique, False


def list_objects_for_prefix(s3: Any, prefix: str) -> list[dict[str, Any]]:
    bucket, key_prefix = parse_s3_uri(prefix)
    paginator = s3.get_paginator("list_objects_v2")
    out: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for item in page.get("Contents", []):
            out.append(
                {
                    "bucket": bucket,
                    "key": str(item.get("Key", "")),
                    "size_bytes": int(item.get("Size", 0) or 0),
                    "last_modified": item.get("LastModified").isoformat() if item.get("LastModified") else None,
                    "prefix": prefix,
                }
            )
    return out


def load_non_brca_yaml_index(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    cfg_dir = root / "configs" / "diseases"
    for disease, file_name in DISEASE_CONFIG_FILES.items():
        path = cfg_dir / file_name
        if not path.exists():
            out[disease] = {"path": str(path), "input_files": {}}
            continue
        with path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        input_files = cfg.get("input_files", {}) if isinstance(cfg, dict) else {}
        if not isinstance(input_files, dict):
            input_files = {}
        out[disease] = {"path": str(path), "input_files": input_files}
    return out


def build_yaml_lookup(input_files: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    lookup: dict[str, list[dict[str, str]]] = defaultdict(list)
    for key, raw_value in input_files.items():
        if not isinstance(raw_value, str) or raw_value.strip() == "" or raw_value == "TODO_UNCONFIRMED":
            continue
        path_value = normalize_path(raw_value).lstrip("/")
        base_name = path_value.rsplit("/", 1)[-1]
        lookup[base_name.lower()].append(
            {
                "yaml_key": key,
                "yaml_standard_role": STANDARD_KEY_MAP.get(key, key),
                "yaml_value": raw_value,
                "normalized_value": path_value.lower(),
            }
        )
    return lookup


def pick_yaml_match(
    rel_key: str,
    file_name: str,
    lookup: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    candidates = lookup.get(file_name.lower(), [])
    if not candidates:
        return None
    rel_norm = normalize_path(rel_key).lower()
    best = None
    best_score = -1
    for cand in candidates:
        val = cand["normalized_value"]
        score = 0
        if rel_norm.endswith(val):
            score += 100
        else:
            overlap = 0
            rel_parts = rel_norm.split("/")
            val_parts = val.split("/")
            while overlap < min(len(rel_parts), len(val_parts)):
                if rel_parts[-1 - overlap] != val_parts[-1 - overlap]:
                    break
                overlap += 1
            score += overlap
        if score > best_score:
            best_score = score
            best = cand
    return best


def decode_text(blob: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
        try:
            return blob.decode(enc)
        except Exception:  # noqa: BLE001
            continue
    return blob.decode("utf-8", errors="ignore")


def sniff_csv_columns_and_rows(text: str, max_rows: int) -> tuple[list[str], list[dict[str, Any]], str]:
    lines = text.splitlines()
    if not lines:
        return [], [], "empty_payload"
    first = lines[0]
    delimiter = "\t" if first.count("\t") > first.count(",") else ","
    reader = csv.reader(StringIO("\n".join(lines[: max_rows + 1])), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return [], [], "no_rows"
    headers = [str(x).strip() for x in rows[0]]
    out_rows: list[dict[str, Any]] = []
    for row in rows[1 : max_rows + 1]:
        out_rows.append({headers[i] if i < len(headers) else f"col_{i}": row[i] for i in range(min(len(headers), len(row)))})
    return headers, out_rows, ""


def read_csv_sample(s3: Any, bucket: str, key: str, max_bytes: int, max_rows: int) -> tuple[list[str], list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    try:
        resp = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}")
        blob = resp["Body"].read()
        text = decode_text(blob)
        cols, rows, note = sniff_csv_columns_and_rows(text, max_rows=max_rows)
        if note:
            warnings.append(note)
        return cols, rows, warnings, errors
    except Exception as exc:  # noqa: BLE001
        errors.append(f"csv_sample_failed: {exc}")
        return [], [], warnings, errors


def read_gzip_csv_sample(
    s3: Any,
    bucket: str,
    key: str,
    size_bytes: int,
    max_full_bytes: int,
    max_rows: int,
) -> tuple[list[str], list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    try:
        if size_bytes > max_full_bytes:
            warnings.append(f"gzip_too_large_for_safe_full_read>{max_full_bytes}")
            return [], [], warnings, errors
        resp = s3.get_object(Bucket=bucket, Key=key)
        blob = resp["Body"].read()
        text = decode_text(gzip.decompress(blob))
        cols, rows, note = sniff_csv_columns_and_rows(text, max_rows=max_rows)
        if note:
            warnings.append(note)
        return cols, rows, warnings, errors
    except Exception as exc:  # noqa: BLE001
        errors.append(f"csv_gz_sample_failed: {exc}")
        return [], [], warnings, errors


def extract_keys_from_json_obj(obj: Any, max_rows: int) -> tuple[list[str], list[dict[str, Any]]]:
    if isinstance(obj, dict):
        return sorted([str(k) for k in obj.keys()]), [obj]
    if isinstance(obj, list):
        dict_rows = [x for x in obj if isinstance(x, dict)][:max_rows]
        keys = sorted({str(k) for row in dict_rows for k in row.keys()})
        return keys, dict_rows
    return [], []


def read_json_sample(s3: Any, bucket: str, key: str, max_bytes: int, max_rows: int) -> tuple[list[str], list[dict[str, Any]], list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    lower = key.lower()
    try:
        if lower.endswith(".jsonl"):
            resp = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}")
            text = decode_text(resp["Body"].read())
            rows: list[dict[str, Any]] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(item, dict):
                    rows.append(item)
                if len(rows) >= max_rows:
                    break
            keys = sorted({str(k) for row in rows for k in row.keys()})
            return keys, rows, warnings, errors

        resp = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}")
        text = decode_text(resp["Body"].read())
        try:
            parsed = json.loads(text)
        except Exception:
            warnings.append("json_partial_parse_failed")
            return [], [], warnings, errors
        keys, rows = extract_keys_from_json_obj(parsed, max_rows=max_rows)
        return keys, rows, warnings, errors
    except Exception as exc:  # noqa: BLE001
        errors.append(f"json_sample_failed: {exc}")
        return [], [], warnings, errors


def check_column_groups(columns: list[str], groups: list[list[str]]) -> tuple[bool, list[str], list[str]]:
    norm_map = {normalize_text(c).replace(" ", "_"): c for c in columns}
    norm_keys = set(norm_map.keys())
    matched: list[str] = []
    missing_groups: list[str] = []
    for group in groups:
        group_norm = [normalize_text(x).replace(" ", "_") for x in group]
        found = None
        for alt in group_norm:
            if alt in norm_keys:
                found = norm_map[alt]
                break
        if found:
            matched.append(found)
        else:
            missing_groups.append("/".join(group))
    return len(missing_groups) == 0, matched, missing_groups


def manifest_schema_ok(columns: list[str], sample_rows: list[dict[str, Any]], file_name: str) -> tuple[bool, list[str]]:
    norm_cols = {normalize_text(c).replace(" ", "_") for c in columns}
    for c in MANIFEST_COLS:
        if normalize_text(c).replace(" ", "_") in norm_cols:
            return True, [c]
    if sample_rows:
        row_keys = {normalize_text(k).replace(" ", "_") for k in sample_rows[0].keys()}
        for c in MANIFEST_COLS:
            if normalize_text(c).replace(" ", "_") in row_keys:
                return True, [c]
    if "manifest" in file_name.lower():
        return True, ["filename_manifest_hint"]
    return False, []


def admet_summary_schema_ok(columns: list[str], sample_rows: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    space = " ".join([normalize_text(c) for c in columns])
    if any(tok in space for tok in SUMMARY_HINT_TOKENS):
        return True, ["column_summary_hints"]
    if sample_rows:
        row_text = normalize_text(json.dumps(sample_rows[0], ensure_ascii=False))
        if any(tok in row_text for tok in SUMMARY_HINT_TOKENS):
            return True, ["row_summary_hints"]
    return False, []


def admet_detailed_schema_ok(columns: list[str]) -> tuple[bool, list[str]]:
    groups = [["drug_name", "drug", "compound_name", "compound", "chembl_id", "drug_id"]]
    ok1, matched1, _ = check_column_groups(columns, groups)
    norm_space = " ".join(normalize_text(c) for c in columns)
    matched_tokens = [tok for tok in ADMET_DETAIL_TOKENS if tok in norm_space]
    if ok1 and matched_tokens:
        return True, matched1 + matched_tokens
    return False, matched1 + matched_tokens


def schema_compatibility(
    role: str | None,
    ext: str,
    columns: list[str],
    sample_rows: list[dict[str, Any]],
    parse_errors: list[str],
    file_name: str,
) -> SchemaResult:
    if role is None:
        return SchemaResult(score=0, status="unknown", reason="role_not_inferred", matched_columns=[])
    if parse_errors and ext in {".csv", ".csv.gz", ".json", ".jsonl"}:
        return SchemaResult(score=5, status="failed", reason="parse_failed_for_inspection", matched_columns=[])

    if role in ROLE_COLUMN_GROUPS:
        ok, matched, missing = check_column_groups(columns, ROLE_COLUMN_GROUPS[role])
        if ok:
            return SchemaResult(score=25, status="pass", reason="required_columns_present", matched_columns=matched)
        if columns:
            return SchemaResult(score=10, status="partial", reason=f"missing_groups:{';'.join(missing)}", matched_columns=matched)
        return SchemaResult(score=8, status="unknown", reason="no_columns_detected", matched_columns=matched)

    if role == "admet_detailed":
        ok, matched = admet_detailed_schema_ok(columns)
        if ok:
            return SchemaResult(score=25, status="pass", reason="drug_and_admet_signals_present", matched_columns=matched)
        if matched:
            return SchemaResult(score=12, status="partial", reason="partial_admet_signals_only", matched_columns=matched)
        return SchemaResult(score=8, status="unknown", reason="no_admet_signals_detected", matched_columns=[])

    if role == "admet_summary":
        ok, matched = admet_summary_schema_ok(columns, sample_rows)
        if ok:
            return SchemaResult(score=25, status="pass", reason="summary_signals_present", matched_columns=matched)
        return SchemaResult(score=10, status="partial", reason="summary_signals_unclear", matched_columns=[])

    if role in {"ensemble_source_manifest", "copied_source_manifest", "reproducibility_manifest"}:
        ok, matched = manifest_schema_ok(columns, sample_rows, file_name=file_name)
        if ok:
            return SchemaResult(score=23, status="pass", reason="manifest_signals_present", matched_columns=matched)
        return SchemaResult(score=10, status="partial", reason="manifest_columns_not_found", matched_columns=[])

    if role == "admet_matches":
        norm_space = " ".join(normalize_text(c) for c in columns)
        if "match" in norm_space or "matched" in norm_space or "match" in normalize_text(file_name):
            return SchemaResult(score=22, status="pass", reason="match_signal_present", matched_columns=columns[:3])
        return SchemaResult(score=10, status="partial", reason="match_signal_unclear", matched_columns=[])

    if role in {"external_validation_scored", "external_validation_validated", "external_validation_method_a", "external_validation_method_b"}:
        if columns:
            return SchemaResult(score=18, status="partial", reason="external_schema_not_strictly_defined", matched_columns=columns[:5])
        return SchemaResult(score=8, status="unknown", reason="no_columns_detected", matched_columns=[])

    if role == "candidate_unique":
        if columns:
            return SchemaResult(score=16, status="partial", reason="candidate_unique_not_strictly_defined", matched_columns=columns[:4])
        return SchemaResult(score=8, status="unknown", reason="no_columns_detected", matched_columns=[])

    return SchemaResult(score=8, status="unknown", reason="no_specific_rule_for_role", matched_columns=[])


def risk_score(ext: str, size_bytes: int, parse_errors: list[str], key: str) -> tuple[int, str]:
    lower = key.lower()
    if parse_errors:
        return 2, "parse_error_present"
    if any(tok in lower for tok in ["matrix", "counts", "expression", "feature_table"]):
        return 0, "likely_large_matrix_or_raw_signal"
    if ext in {".csv", ".csv.gz", ".json", ".jsonl", ".md"} and size_bytes <= 512 * 1024 * 1024:
        return 10, "low_risk"
    if ext in {".parquet", ".xlsx"}:
        return 4, "moderate_risk_binary_format"
    return 3, "unknown_format_risk"


def decision_for_file(
    inferred_role: str | None,
    schema_status: str,
    total_score: int,
    exclusion_reason: str | None,
    yaml_standard_role: str | None,
    key: str,
) -> tuple[str, str]:
    lower = key.lower()
    if exclusion_reason:
        return "exclude", exclusion_reason
    if inferred_role is None and yaml_standard_role is None:
        if any(tok in lower for tok in ["matrix", "counts", "expression", "raw", "intermediate"]):
            return "exclude", "irrelevant_or_raw_feature_artifact"
        return "hold", "role_unclear"
    if schema_status == "failed":
        return "hold", "schema_parse_failed"
    if total_score >= 80 and schema_status in {"pass", "partial"}:
        return "include", "high_confidence_mapping"
    if schema_status == "pass" and total_score >= 70:
        return "include", "schema_ok_with_medium_confidence"
    return "hold", "needs_manual_review"


def inspect_file_sample(
    s3: Any,
    bucket: str,
    key: str,
    ext: str,
    size_bytes: int,
    max_csv_bytes: int,
    max_json_bytes: int,
    max_gzip_full_bytes: int,
    max_rows: int,
) -> tuple[list[str], list[dict[str, Any]], list[str], list[str]]:
    if ext == ".csv":
        return read_csv_sample(s3, bucket, key, max_bytes=max_csv_bytes, max_rows=max_rows)
    if ext == ".csv.gz":
        return read_gzip_csv_sample(
            s3,
            bucket,
            key,
            size_bytes=size_bytes,
            max_full_bytes=max_gzip_full_bytes,
            max_rows=max_rows,
        )
    if ext in {".json", ".jsonl"}:
        return read_json_sample(s3, bucket, key, max_bytes=max_json_bytes, max_rows=max_rows)
    return [], [], ["sampling_not_supported_for_extension"], []


def validate_disease(
    disease: str,
    prefixes: list[str],
    s3: Any,
    yaml_input_files: dict[str, str],
    max_csv_bytes: int,
    max_json_bytes: int,
    max_gzip_full_bytes: int,
    max_rows: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_objects: list[dict[str, Any]] = []
    prefix_errors: list[str] = []
    for prefix in prefixes:
        try:
            objs = list_objects_for_prefix(s3, prefix=prefix)
            raw_objects.extend(objs)
        except Exception as exc:  # noqa: BLE001
            prefix_errors.append(f"list_failed:{prefix}:{exc}")

    unique_by_key: dict[str, dict[str, Any]] = {}
    for item in raw_objects:
        key = item["key"]
        if key not in unique_by_key:
            unique_by_key[key] = item

    yaml_lookup = build_yaml_lookup(yaml_input_files)
    rows: list[dict[str, Any]] = []
    by_role_best: dict[str, int] = defaultdict(int)
    include_roles: set[str] = set()
    hold_roles: set[str] = set()
    excluded_count = 0
    include_count = 0
    hold_count = 0

    for key in sorted(unique_by_key.keys()):
        item = unique_by_key[key]
        bucket = item["bucket"]
        size_bytes = int(item["size_bytes"])
        prefix_used = item["prefix"]
        rel_key = key
        _, key_prefix = parse_s3_uri(prefix_used)
        if rel_key.startswith(key_prefix):
            rel_key = rel_key[len(key_prefix) :].lstrip("/")

        file_name = key.rsplit("/", 1)[-1]
        ext = get_extension(file_name)
        excluded, exclusion_reason = is_obvious_exclusion(key, size_bytes)

        inferred_role, matched_roles, role_clear = infer_role(file_name=file_name)
        yaml_match = pick_yaml_match(rel_key=rel_key, file_name=file_name, lookup=yaml_lookup)
        yaml_key = yaml_match["yaml_key"] if yaml_match else None
        yaml_standard_role = yaml_match["yaml_standard_role"] if yaml_match else None

        sampled_columns: list[str] = []
        sample_rows: list[dict[str, Any]] = []
        sample_warnings: list[str] = []
        sample_errors: list[str] = []
        if not excluded:
            sampled_columns, sample_rows, sample_warnings, sample_errors = inspect_file_sample(
                s3=s3,
                bucket=bucket,
                key=key,
                ext=ext,
                size_bytes=size_bytes,
                max_csv_bytes=max_csv_bytes,
                max_json_bytes=max_json_bytes,
                max_gzip_full_bytes=max_gzip_full_bytes,
                max_rows=max_rows,
            )

        schema = schema_compatibility(
            role=inferred_role or yaml_standard_role,
            ext=ext,
            columns=sampled_columns,
            sample_rows=sample_rows,
            parse_errors=sample_errors,
            file_name=file_name,
        )

        score_file_exists = SCORING_WEIGHTS["file_exists"]
        score_role_clear = SCORING_WEIGHTS["role_clear_from_filename"] if role_clear else (12 if inferred_role else 0)
        if inferred_role and yaml_standard_role and inferred_role == yaml_standard_role:
            score_yaml = SCORING_WEIGHTS["yaml_key_matches_file_role"]
        elif inferred_role and yaml_standard_role and inferred_role != yaml_standard_role:
            score_yaml = 0
        elif yaml_standard_role and not inferred_role:
            score_yaml = 10
        else:
            score_yaml = 0
        score_schema = schema.score
        score_risk, risk_reason = risk_score(ext=ext, size_bytes=size_bytes, parse_errors=sample_errors, key=key)
        total = score_file_exists + score_role_clear + score_yaml + score_schema + score_risk

        decision, decision_reason = decision_for_file(
            inferred_role=inferred_role,
            schema_status=schema.status,
            total_score=total,
            exclusion_reason=exclusion_reason if excluded else None,
            yaml_standard_role=yaml_standard_role,
            key=key,
        )

        chosen_role = inferred_role or yaml_standard_role
        if chosen_role:
            by_role_best[chosen_role] = max(by_role_best[chosen_role], total)
            if decision == "include":
                include_roles.add(chosen_role)
            elif decision == "hold":
                hold_roles.add(chosen_role)

        if decision == "exclude":
            excluded_count += 1
        elif decision == "include":
            include_count += 1
        else:
            hold_count += 1

        row = {
            "disease": disease,
            "bucket": bucket,
            "s3_key": key,
            "s3_uri": f"s3://{bucket}/{key}",
            "prefix_used": prefix_used,
            "relative_key": rel_key,
            "file_name": file_name,
            "extension": ext,
            "size_bytes": size_bytes,
            "last_modified": item["last_modified"],
            "excluded_by_filter": excluded,
            "exclusion_reason": exclusion_reason if excluded else "",
            "inferred_role": inferred_role or "",
            "matched_roles": matched_roles,
            "role_clear_from_filename": role_clear,
            "yaml_key_match": yaml_key or "",
            "yaml_standard_role": yaml_standard_role or "",
            "sampled_columns": sampled_columns,
            "sample_row_count": len(sample_rows),
            "sample_rows_preview": sample_rows[:3],
            "sample_warnings": sample_warnings,
            "sample_errors": sample_errors,
            "schema_status": schema.status,
            "schema_reason": schema.reason,
            "schema_matched_columns": schema.matched_columns,
            "score_file_exists": score_file_exists,
            "score_role_clear_from_filename": score_role_clear,
            "score_yaml_key_matches_file_role": score_yaml,
            "score_schema_compatible_with_loader": score_schema,
            "score_load_risk_low": score_risk,
            "risk_reason": risk_reason,
            "total_confidence_score": total,
            "decision": decision,
            "decision_reason": decision_reason,
        }
        rows.append(row)

    role_scores = list(by_role_best.values())
    avg_score = round(sum(role_scores) / len(role_scores), 2) if role_scores else 0.0

    pilot_presence: dict[str, str] = {}
    required_ok = True
    for group in PILOT_REQUIRED_GROUPS:
        include_hit = any(role in include_roles for role in group)
        hold_hit = any(role in hold_roles for role in group)
        label = "present" if include_hit else ("uncertain" if hold_hit else "missing")
        pilot_presence[" or ".join(group)] = label
        if label != "present":
            required_ok = False

    if avg_score >= 80 and required_ok:
        disease_confidence = "high"
    elif avg_score < 60 or all(v == "missing" for v in pilot_presence.values()):
        disease_confidence = "low"
    else:
        disease_confidence = "medium"

    summary = {
        "disease": disease,
        "prefixes_checked": prefixes,
        "listed_object_count": len(unique_by_key),
        "included_file_count": include_count,
        "held_file_count": hold_count,
        "excluded_file_count": excluded_count,
        "average_confidence_score": avg_score,
        "disease_confidence": disease_confidence,
        "required_pilot_presence": pilot_presence,
        "role_best_scores": dict(sorted(by_role_best.items())),
        "prefix_errors": prefix_errors,
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            flat = {col: row.get(col, "") for col in columns}
            for key, value in list(flat.items()):
                if isinstance(value, (dict, list)):
                    flat[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow(flat)


def write_markdown(path: Path, disease_summaries: list[dict[str, Any]], file_rows: list[dict[str, Any]]) -> None:
    promotable: list[str] = []
    hold_reasons: dict[str, int] = defaultdict(int)
    exclude_reasons: dict[str, int] = defaultdict(int)

    for summary in disease_summaries:
        if summary["disease_confidence"] == "medium":
            pilot = summary.get("required_pilot_presence", {})
            uncertain_or_missing = [k for k, v in pilot.items() if v != "present"]
            if len(uncertain_or_missing) <= 2 and summary.get("average_confidence_score", 0) >= 70:
                promotable.append(summary["disease"])

    for row in file_rows:
        if row["decision"] == "hold":
            hold_reasons[row["decision_reason"]] += 1
        if row["decision"] == "exclude":
            exclude_reasons[row["decision_reason"]] += 1

    lines: list[str] = []
    lines.append("# Multi-Cancer Input File Validation Report")
    lines.append("")
    lines.append(f"- generated_at: {now_iso()}")
    lines.append("- scope: non-BRCA disease input file mapping validation")
    lines.append("- safety: metadata + small header/sample only; no PostgreSQL/Neo4j writes")
    lines.append("")
    lines.append("## Disease-level summary")
    lines.append("")
    lines.append("| disease | listed_objects | include | hold | exclude | avg_confidence | disease_confidence |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for s in disease_summaries:
        lines.append(
            f"| {s['disease']} | {s['listed_object_count']} | {s['included_file_count']} | "
            f"{s['held_file_count']} | {s['excluded_file_count']} | {s['average_confidence_score']} | {s['disease_confidence']} |"
        )

    lines.append("")
    lines.append("## File-level decision table")
    lines.append("")
    lines.append("| disease | file_name | inferred_role | yaml_key | score | decision | reason |")
    lines.append("|---|---|---|---|---:|---|---|")
    for row in sorted(file_rows, key=lambda x: (x["disease"], -x["total_confidence_score"], x["file_name"]))[:250]:
        lines.append(
            f"| {row['disease']} | {row['file_name']} | {row['inferred_role'] or '-'} | "
            f"{row['yaml_key_match'] or '-'} | {row['total_confidence_score']} | {row['decision']} | {row['decision_reason']} |"
        )

    lines.append("")
    lines.append("## Why COAD/COLON remains pilot candidate")
    lines.append(
        "COAD/COLON remains the pilot because its candidate_tiered/final_after_admet/model_performance_summary "
        "patterns are the most consistently discoverable from filenames and schema hints under a single disease family."
    )

    lines.append("")
    lines.append("## Diseases promotable from medium to high")
    if promotable:
        for disease in sorted(promotable):
            lines.append(f"- {disease}: promote after resolving remaining held required pilot role(s).")
    else:
        lines.append("- None yet: required pilot role coverage or confidence threshold is still incomplete.")

    lines.append("")
    lines.append("## Held files and reasons")
    if hold_reasons:
        for reason, count in sorted(hold_reasons.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {reason}: {count} file(s)")
    else:
        lines.append("- No held files.")

    lines.append("")
    lines.append("## Excluded files and reasons")
    if exclude_reasons:
        for reason, count in sorted(exclude_reasons.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {reason}: {count} file(s)")
    else:
        lines.append("- No excluded files.")

    lines.append("")
    lines.append("## Next action per disease")
    for s in disease_summaries:
        disease = s["disease"]
        missing = [k for k, v in s["required_pilot_presence"].items() if v != "present"]
        if s["disease_confidence"] == "high":
            lines.append(f"- {disease}: ready to map YAML `input_files` using included files only.")
        elif s["disease_confidence"] == "medium":
            lines.append(f"- {disease}: resolve held required roles ({', '.join(missing)}) and re-run validation.")
        else:
            lines.append(f"- {disease}: first identify candidate_tiered/final_after_admet/model summary candidates from additional release-like subfolders.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate non-BRCA disease YAML input_files against S3 metadata/samples using boto3.")
    parser.add_argument("--max-csv-bytes", type=int, default=512 * 1024, help="Max bytes for CSV range sampling.")
    parser.add_argument("--max-json-bytes", type=int, default=768 * 1024, help="Max bytes for JSON range sampling.")
    parser.add_argument("--max-gzip-full-bytes", type=int, default=8 * 1024 * 1024, help="Max full object size for .csv.gz full read.")
    parser.add_argument("--max-rows", type=int, default=20, help="Max sample rows for structured previews.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    out_dir = root / "outputs" / "config_validation"
    docs_path = root / "docs" / "multi_cancer_input_file_validation_report.md"
    out_csv = out_dir / "multi_cancer_input_file_validation_report.csv"
    out_json = out_dir / "multi_cancer_input_file_validation_report.json"
    out_summary_csv = out_dir / "multi_cancer_disease_confidence_summary.csv"

    yaml_index = load_non_brca_yaml_index(root)
    s3 = boto3.client("s3")

    all_rows: list[dict[str, Any]] = []
    disease_summaries: list[dict[str, Any]] = []

    for disease in ["COAD", "LUNG", "LIHC", "PAAD", "HNSC", "STAD"]:
        yaml_info = yaml_index.get(disease, {})
        yaml_input_files = yaml_info.get("input_files", {}) if isinstance(yaml_info, dict) else {}
        cfg_prefix = ""
        cfg_path = yaml_info.get("path", "")
        if cfg_path and Path(cfg_path).exists():
            with Path(cfg_path).open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                cfg_prefix = str(cfg.get("s3_parent_prefix", "")).strip()

        prefixes = list(DEFAULT_DISEASE_PREFIXES[disease])
        if cfg_prefix:
            norm_cfg = normalize_prefix(cfg_prefix)
            if norm_cfg not in prefixes:
                prefixes.append(norm_cfg)

        rows, summary = validate_disease(
            disease=disease,
            prefixes=prefixes,
            s3=s3,
            yaml_input_files=yaml_input_files,
            max_csv_bytes=args.max_csv_bytes,
            max_json_bytes=args.max_json_bytes,
            max_gzip_full_bytes=args.max_gzip_full_bytes,
            max_rows=args.max_rows,
        )
        all_rows.extend(rows)
        disease_summaries.append(summary)
        print(
            f"[validated] {disease} listed={summary['listed_object_count']} include={summary['included_file_count']} "
            f"hold={summary['held_file_count']} exclude={summary['excluded_file_count']} confidence={summary['disease_confidence']}"
        )

    all_rows_sorted = sorted(all_rows, key=lambda x: (x["disease"], x["s3_key"]))
    csv_columns = [
        "disease",
        "s3_uri",
        "prefix_used",
        "relative_key",
        "file_name",
        "extension",
        "size_bytes",
        "last_modified",
        "excluded_by_filter",
        "exclusion_reason",
        "inferred_role",
        "matched_roles",
        "role_clear_from_filename",
        "yaml_key_match",
        "yaml_standard_role",
        "sampled_columns",
        "sample_row_count",
        "sample_rows_preview",
        "sample_warnings",
        "sample_errors",
        "schema_status",
        "schema_reason",
        "schema_matched_columns",
        "score_file_exists",
        "score_role_clear_from_filename",
        "score_yaml_key_matches_file_role",
        "score_schema_compatible_with_loader",
        "score_load_risk_low",
        "risk_reason",
        "total_confidence_score",
        "decision",
        "decision_reason",
    ]
    write_csv(out_csv, all_rows_sorted, csv_columns)

    report = {
        "generated_at": now_iso(),
        "script": "scripts/config/validate_multi_cancer_input_files.py",
        "scope": ["COAD", "LUNG", "LIHC", "PAAD", "HNSC", "STAD"],
        "safety": {
            "db_writes": False,
            "neo4j_writes": False,
            "s3fs_used": False,
            "sampling_only": True,
        },
        "scoring_weights": SCORING_WEIGHTS,
        "expected_roles": EXPECTED_ROLES,
        "disease_summaries": disease_summaries,
        "file_rows": all_rows_sorted,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_rows = []
    for s in disease_summaries:
        row = dict(s)
        row["required_pilot_presence"] = json.dumps(s.get("required_pilot_presence", {}), ensure_ascii=False)
        row["role_best_scores"] = json.dumps(s.get("role_best_scores", {}), ensure_ascii=False)
        row["prefix_errors"] = json.dumps(s.get("prefix_errors", []), ensure_ascii=False)
        row["prefixes_checked"] = json.dumps(s.get("prefixes_checked", []), ensure_ascii=False)
        summary_rows.append(row)
    summary_columns = [
        "disease",
        "listed_object_count",
        "included_file_count",
        "held_file_count",
        "excluded_file_count",
        "average_confidence_score",
        "disease_confidence",
        "required_pilot_presence",
        "role_best_scores",
        "prefixes_checked",
        "prefix_errors",
    ]
    write_csv(out_summary_csv, summary_rows, summary_columns)
    write_markdown(docs_path, disease_summaries=disease_summaries, file_rows=all_rows_sorted)

    print(f"[ok] {out_csv}")
    print(f"[ok] {out_json}")
    print(f"[ok] {out_summary_csv}")
    print(f"[ok] {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
