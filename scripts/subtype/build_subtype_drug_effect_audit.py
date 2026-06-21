#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
import yaml


CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
MAX_JSON_PREVIEW_BYTES = 2 * 1024 * 1024
MAX_PARQUET_BYTES = 80 * 1024 * 1024
MAX_TABLE_ROWS_MD = 200

INCLUDE_TOKENS = [
    "final",
    "top15",
    "top30",
    "candidate",
    "tier",
    "admet",
    "metabric",
    "validation",
    "training",
    "feature",
    "ml_training",
    "pair",
    "subtype",
    "cell",
]

EXCLUDE_TOKENS = [
    "image",
    "images",
    "figure",
    "figures",
    "plot",
    "plots",
    "png",
    "jpg",
    "jpeg",
    "html",
    "tmp",
    "temp",
    "debug",
    "log",
    "glue",
    "raw",
    "intermediate",
    "cache",
]

AUDIT_FIELD_ORDER = [
    "disease",
    "drug_name",
    "drug_id",
    "chembl_id",
    "smiles",
    "cell_line_id",
    "cell_line_name",
    "sample_id",
    "subtype",
    "molecular_subtype",
    "pam50",
    "predicted_score",
    "prediction",
    "ln_ic50",
    "y_ln_ic50",
    "ic50",
    "pred_ic50",
    "predicted_ic50",
    "predicted_ln_ic50",
    "auc",
    "rank",
    "final_score",
    "ensemble_score",
    "admet_score",
    "target_gene",
    "target_name",
]

FIELD_ALIASES: dict[str, list[str]] = {
    "disease": ["disease", "cancer", "disease_code", "cancer_type"],
    "drug_name": ["drug_name", "drug", "compound_name", "name", "drug_name_norm"],
    "drug_id": ["drug_id", "canonical_drug_id", "compound_id", "pubchem_id", "cid"],
    "chembl_id": ["chembl_id", "drug_chembl_id"],
    "smiles": ["smiles", "canonical_smiles"],
    "cell_line_id": ["cell_line_id", "cell_id", "depmap_id", "cosmic_id"],
    "cell_line_name": ["cell_line_name", "cell_line", "cell", "cell_name"],
    "sample_id": ["sample_id", "sample", "patient_id", "tumor_id"],
    "subtype": ["subtype", "cancer_subtype"],
    "molecular_subtype": ["molecular_subtype", "molecule_subtype"],
    "pam50": ["pam50", "pam50_subtype"],
    "predicted_score": ["predicted_score", "prediction_score", "pred_score", "score_pred"],
    "prediction": ["prediction", "pred", "predicted_response", "pred_response"],
    "ln_ic50": ["ln_ic50", "log_ic50", "pred_ln_ic50"],
    "y_ln_ic50": ["y_ln_ic50"],
    "ic50": ["ic50", "mean_ic50"],
    "pred_ic50": ["pred_ic50"],
    "predicted_ic50": ["predicted_ic50"],
    "predicted_ln_ic50": ["predicted_ln_ic50"],
    "auc": ["auc", "auroc", "a_u_c"],
    "rank": ["rank", "final_rank", "step7_final_rank"],
    "final_score": ["final_score", "score"],
    "ensemble_score": ["ensemble_score"],
    "admet_score": ["admet_score", "safety_score"],
    "target_gene": ["target_gene", "gene_target", "target_symbol"],
    "target_name": ["target_name", "target", "target_pathway"],
}

RESPONSE_PRIORITY = [
    "ln_ic50",
    "y_ln_ic50",
    "ic50",
    "pred_ic50",
    "predicted_ic50",
    "predicted_ln_ic50",
    "predicted_score",
    "prediction",
    "auc",
    "final_score",
    "ensemble_score",
    "admet_score",
]
SUBTYPE_PRIORITY = ["subtype", "molecular_subtype", "pam50"]
DRUG_PRIORITY = ["drug_id", "chembl_id", "drug_name", "smiles"]
JOIN_ID_PRIORITY = ["cell_line_id", "cell_line_name", "sample_id"]
LOWER_BETTER_FIELDS = {"ln_ic50", "y_ln_ic50", "ic50", "pred_ic50", "predicted_ic50", "predicted_ln_ic50"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", safe_str(name).lower()).strip("_")


def norm_val(v: Any) -> str:
    return safe_str(v).strip().lower()


def to_builtin(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, bool)):
        return v
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if hasattr(v, "item"):
        try:
            return to_builtin(v.item())
        except Exception:
            return safe_str(v)
    return safe_str(v)


def str2bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    t = safe_str(v).lower()
    if t in {"1", "true", "t", "yes", "y"}:
        return True
    if t in {"0", "false", "f", "no", "n", ""}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {v}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BRCA subtype-specific drug effect audit v2 (read-only).")
    p.add_argument("--disease", required=True)
    p.add_argument("--s3-prefix", required=True)
    p.add_argument("--limit-rows", type=int, default=100)
    p.add_argument("--execute", type=str2bool, default=False)
    return p.parse_args()


def has_project_markers(path: Path) -> bool:
    return (path / "scripts").is_dir() and (path / "docs").is_dir() and (path / "outputs").is_dir()


def resolve_project_root() -> Path:
    if CANONICAL_PROJECT_ROOT.exists() and has_project_markers(CANONICAL_PROJECT_ROOT):
        return CANONICAL_PROJECT_ROOT

    cwd = Path.cwd().resolve()
    script_path = Path(__file__).resolve()

    if has_project_markers(cwd):
        return cwd

    for p in [script_path.parent, *script_path.parents]:
        if has_project_markers(p):
            if "onedrive" in str(p).lower() and CANONICAL_PROJECT_ROOT.exists() and has_project_markers(CANONICAL_PROJECT_ROOT):
                return CANONICAL_PROJECT_ROOT.resolve()
            return p

    if CANONICAL_PROJECT_ROOT.exists() and has_project_markers(CANONICAL_PROJECT_ROOT):
        return CANONICAL_PROJECT_ROOT.resolve()
    return cwd


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    m = re.match(r"^s3://([^/]+)/?(.*)$", safe_str(s3_uri))
    if not m:
        raise ValueError(f"invalid_s3_uri:{s3_uri}")
    bucket = m.group(1)
    prefix = m.group(2)
    return bucket, prefix


def list_s3_objects(s3: Any, bucket: str, prefix: str) -> list[dict[str, Any]]:
    paginator = s3.get_paginator("list_objects_v2")
    out: list[dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = safe_str(obj.get("Key"))
            if not key or key.endswith("/"):
                continue
            out.append({"key": key, "size_bytes": int(obj.get("Size", 0) or 0)})
    return out


def token_match(text: str, token: str) -> bool:
    return re.search(rf"(^|[^a-z0-9]){re.escape(token.lower())}([^a-z0-9]|$)", text.lower()) is not None


def choose_delimiter(header_line: str) -> str:
    candidates = [",", "\t", ";", "|"]
    counts = {d: header_line.count(d) for d in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def detect_extension(key: str) -> str:
    lower = key.lower()
    if lower.endswith(".csv") or lower.endswith(".tsv") or lower.endswith(".txt"):
        return "csv"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".parquet"):
        return "parquet"
    return "unsupported"


def inspect_csv(s3: Any, bucket: str, key: str, limit_rows: int) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"]
    lines: list[str] = []
    for raw in body.iter_lines():
        if raw is None:
            continue
        lines.append(raw.decode("utf-8", errors="replace"))
        if len(lines) >= limit_rows + 1:
            break
    if not lines:
        return [], [], ["empty_or_unreadable_csv"]
    delim = choose_delimiter(lines[0])
    text = "\n".join(lines) + "\n"
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    cols = [safe_str(c) for c in (reader.fieldnames or []) if safe_str(c)]
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append({safe_str(k): to_builtin(v) for k, v in row.items()})
        if len(rows) >= limit_rows:
            break
    if not cols:
        warnings.append("missing_csv_header")
    return cols, rows, warnings


def extract_json_records(payload: Any, limit_rows: int) -> tuple[list[dict[str, Any]], list[str]]:
    if isinstance(payload, list):
        records = [x for x in payload if isinstance(x, dict)]
        if records:
            return records[:limit_rows], []
        wrapped = [{"value": to_builtin(x)} for x in payload[:limit_rows]]
        return wrapped, ["json_list_not_dict"]
    if isinstance(payload, dict):
        for k in ["rows", "data", "records", "results", "items"]:
            value = payload.get(k)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return [x for x in value[:limit_rows] if isinstance(x, dict)], []
        return [payload], []
    return [], ["json_top_level_not_list_or_dict"]


def inspect_json(s3: Any, bucket: str, key: str, limit_rows: int) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    head = s3.head_object(Bucket=bucket, Key=key)
    size = int(head.get("ContentLength", 0) or 0)
    raw: bytes
    if size <= MAX_JSON_PREVIEW_BYTES:
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    else:
        raw = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{MAX_JSON_PREVIEW_BYTES - 1}")["Body"].read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        if size > MAX_JSON_PREVIEW_BYTES:
            warnings.append("json_parse_failed_in_preview_range")
            return [], [], warnings
        warnings.append("json_parse_failed")
        return [], [], warnings
    rows, row_warnings = extract_json_records(payload, limit_rows)
    warnings.extend(row_warnings)
    cols: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for col in row.keys():
            if col not in seen:
                seen.add(col)
                cols.append(col)
    return cols, rows, warnings


def inspect_parquet(s3: Any, bucket: str, key: str, limit_rows: int) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    head = s3.head_object(Bucket=bucket, Key=key)
    size = int(head.get("ContentLength", 0) or 0)
    if size > MAX_PARQUET_BYTES:
        return [], [], ["parquet_too_large_for_readonly_sample"]
    raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    try:
        df = pd.read_parquet(io.BytesIO(raw))
    except Exception:
        return [], [], ["parquet_parse_failed"]
    sample = df.head(limit_rows)
    cols = [safe_str(c) for c in sample.columns]
    rows = [{safe_str(k): to_builtin(v) for k, v in row.items()} for row in sample.to_dict(orient="records")]
    return cols, rows, []


def detect_field_candidates(raw_columns: list[str]) -> dict[str, list[str]]:
    normalized = {raw: norm_col(raw) for raw in raw_columns}
    out: dict[str, list[str]] = {}
    for field in AUDIT_FIELD_ORDER:
        aliases = FIELD_ALIASES.get(field, [])
        matched: list[str] = []
        for raw, ncol in normalized.items():
            for alias in aliases:
                na = norm_col(alias)
                if ncol == na or na in ncol:
                    matched.append(raw)
                    break
        out[field] = matched
    return out


def choose_preferred_column(field_candidates: dict[str, list[str]], priority: list[str]) -> tuple[str | None, str | None]:
    for field in priority:
        vals = field_candidates.get(field, [])
        if vals:
            return vals[0], field
    return None, None


def get_first_present(row: dict[str, Any], columns: list[str]) -> tuple[str | None, Any]:
    for col in columns:
        if col in row:
            v = row.get(col)
            if safe_str(v) != "":
                return col, v
    return None, None


def as_numeric(v: Any) -> float | None:
    try:
        if v is None:
            return None
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def infer_response_direction(field_key: str | None, col_name: str | None) -> tuple[str, str]:
    fk = safe_str(field_key).lower()
    col = norm_col(safe_str(col_name))
    if fk in LOWER_BETTER_FIELDS:
        return "LOWER_IS_BETTER", "KNOWN_DIRECTION"
    if any(x in col for x in ["ln_ic50", "y_ln_ic50", "predicted_ln_ic50", "predicted_ic50", "pred_ic50"]):
        return "LOWER_IS_BETTER", "KNOWN_DIRECTION"
    if any(x in col for x in ["sensitivity", "sensitive"]):
        return "HIGHER_IS_BETTER", "KNOWN_DIRECTION"
    return "UNKNOWN", "UNKNOWN_DIRECTION"


def aggregate_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "mean_response": None,
            "median_response": None,
            "min_response": None,
            "max_response": None,
            "std_response": None,
        }
    s = pd.Series(values, dtype="float64")
    return {
        "mean_response": float(s.mean()),
        "median_response": float(s.median()),
        "min_response": float(s.min()),
        "max_response": float(s.max()),
        "std_response": float(s.std(ddof=1)) if len(values) > 1 else 0.0,
    }


def load_config_subtypes(project_root: Path, disease: str) -> list[str]:
    cfg = project_root / "configs" / "diseases" / f"{disease.lower()}.yaml"
    if not cfg.exists():
        return []
    try:
        payload = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    bio = payload.get("biology", {}) if isinstance(payload, dict) else {}
    subtypes = bio.get("molecular_subtypes", []) if isinstance(bio, dict) else []
    if isinstance(subtypes, list):
        return [safe_str(x) for x in subtypes if safe_str(x)]
    return []


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    if not rows:
        return ["| (none) |", "|---|"]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        vals = [safe_str(row.get(c, "")) for c in columns]
        vals = [v.replace("\n", " ").replace("|", "\\|") for v in vals]
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def infer_role(
    rel_path_lower: str,
    basename_lower: str,
    has_drug: bool,
    has_response_col: bool,
    has_join_id: bool,
    has_subtype_col: bool,
    has_cell_name_col: bool,
) -> tuple[str, str]:
    if has_drug and has_join_id and has_response_col:
        if has_subtype_col:
            return "pair_response_files", "drug_join_response_with_subtype"
        return "pair_response_files", "drug_join_response"

    if has_join_id and has_subtype_col:
        return "subtype_metadata_files", "join_key_with_subtype"

    if has_join_id and has_cell_name_col and not has_response_col:
        return "cell_line_metadata_files", "join_key_with_cell_name"

    candidate_name_hit = any(token_match(basename_lower, t) or token_match(rel_path_lower, t) for t in ["top15", "top30", "final", "tier", "admet", "metabric", "candidate", "validation"])
    if candidate_name_hit and has_drug:
        return "candidate_result_files", "candidate_like_name_and_drug_column"

    return "unsupported_or_irrelevant_files", "insufficient_columns_for_target_roles"


def main() -> int:
    args = parse_args()
    disease = safe_str(args.disease).upper()
    if disease != "BRCA":
        raise SystemExit("This v2 audit currently supports --disease BRCA only.")

    limit_rows = max(1, int(args.limit_rows))
    bucket, prefix = parse_s3_uri(args.s3_prefix)
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"

    project_root = resolve_project_root()
    script_path = Path(__file__).resolve()

    out_json = project_root / "outputs" / "config_validation" / "brca_subtype_drug_effect_audit.json"
    out_md = project_root / "docs" / "brca_subtype_drug_effect_audit.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")
    objects = list_s3_objects(s3, bucket, prefix)

    excluded_reason_counter: Counter[str] = Counter()
    included_files: list[dict[str, Any]] = []
    excluded_files_preview: list[dict[str, Any]] = []

    for obj in objects:
        key = obj["key"]
        rel_path = key[len(prefix) :] if key.startswith(prefix) else key
        rel_lower = rel_path.lower()
        basename_lower = Path(rel_path).name.lower()

        include_hits = [t for t in INCLUDE_TOKENS if token_match(basename_lower, t) or token_match(rel_lower, t)]
        if not include_hits:
            excluded_reason_counter["no_include_token_on_basename_or_relative_path"] += 1
            continue

        exclude_hits = [t for t in EXCLUDE_TOKENS if t.lower() in rel_lower]
        if exclude_hits:
            reason = f"exclude_token:{exclude_hits[0]}"
            excluded_reason_counter[reason] += 1
            if len(excluded_files_preview) < 200:
                excluded_files_preview.append({"s3_uri": f"s3://{bucket}/{key}", "reason": reason})
            continue

        included_files.append(
            {
                "key": key,
                "relative_path": rel_path,
                "basename": Path(rel_path).name,
                "size_bytes": obj["size_bytes"],
                "include_hits": include_hits,
            }
        )

    file_audits: list[dict[str, Any]] = []
    candidate_result_files: list[dict[str, Any]] = []
    pair_response_files: list[dict[str, Any]] = []
    subtype_metadata_files: list[dict[str, Any]] = []
    cell_line_metadata_files: list[dict[str, Any]] = []
    unsupported_or_irrelevant_files: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    important_files_columns: list[dict[str, Any]] = []

    rows_inspected = 0
    rows_with_subtype = 0
    rows_with_drug_identifier = 0
    rows_with_response_score = 0
    rows_same_row_ready = 0

    status_counts: Counter[str] = Counter()
    missing_subtype_rows: list[dict[str, Any]] = []
    missing_response_rows: list[dict[str, Any]] = []

    aggregation_bucket: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "values": [],
            "cell_values": set(),
            "n_rows": 0,
            "drug_identifier": "",
            "subtype": "",
            "response_column_used": "",
            "subtype_column_used": "",
        }
    )
    best_direction_seen: dict[tuple[str, str], tuple[str, str]] = {}
    discovered_subtype_values: set[str] = set()

    response_file_samples: dict[str, dict[str, Any]] = {}
    subtype_meta_samples: dict[str, dict[str, Any]] = {}

    for file_obj in included_files:
        key = file_obj["key"]
        s3_uri = f"s3://{bucket}/{key}"
        ext = detect_extension(key)
        if ext == "unsupported":
            unsupported_or_irrelevant_files.append({"s3_uri": s3_uri, "reason": "unsupported_extension"})
            continue

        columns: list[str] = []
        sample_rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            if ext == "csv":
                columns, sample_rows, warnings = inspect_csv(s3, bucket, key, limit_rows)
            elif ext == "json":
                columns, sample_rows, warnings = inspect_json(s3, bucket, key, limit_rows)
            elif ext == "parquet":
                columns, sample_rows, warnings = inspect_parquet(s3, bucket, key, limit_rows)
        except Exception as exc:
            warnings = [f"inspect_failed:{exc}"]

        field_candidates = detect_field_candidates(columns)
        subtype_col, subtype_field_key = choose_preferred_column(field_candidates, SUBTYPE_PRIORITY)
        response_col, response_field_key = choose_preferred_column(field_candidates, RESPONSE_PRIORITY)
        direction, direction_status = infer_response_direction(response_field_key, response_col)

        drug_cols: list[str] = []
        for f in DRUG_PRIORITY:
            drug_cols.extend(field_candidates.get(f, []))
        drug_cols = [x for i, x in enumerate(drug_cols) if x and x not in drug_cols[:i]]

        join_id_cols: list[str] = []
        for f in JOIN_ID_PRIORITY:
            join_id_cols.extend(field_candidates.get(f, []))
        join_id_cols = [x for i, x in enumerate(join_id_cols) if x and x not in join_id_cols[:i]]
        has_join_id = len(join_id_cols) > 0
        has_cell_name_col = len(field_candidates.get("cell_line_name", [])) > 0
        has_drug = len(drug_cols) > 0
        has_response_col = response_col is not None
        has_subtype_col = subtype_col is not None

        response_numeric_count = 0
        join_values_by_col: dict[str, set[str]] = defaultdict(set)
        join_value_counts_by_col: dict[str, Counter[str]] = defaultdict(Counter)
        subtype_values_by_col: dict[str, set[str]] = defaultdict(set)

        file_status_counter: Counter[str] = Counter()
        for idx, row in enumerate(sample_rows):
            rows_inspected += 1
            drug_col_used, drug_val = get_first_present(row, drug_cols)
            subtype_val = row.get(subtype_col) if subtype_col else None
            response_val = row.get(response_col) if response_col else None
            response_num = as_numeric(response_val)
            has_subtype = safe_str(subtype_val) != ""
            has_drug_val = safe_str(drug_val) != ""
            has_response_val = response_num is not None

            if has_subtype:
                rows_with_subtype += 1
                discovered_subtype_values.add(safe_str(subtype_val))
            if has_drug_val:
                rows_with_drug_identifier += 1
            if has_response_val:
                rows_with_response_score += 1
                response_numeric_count += 1

            for jc in join_id_cols:
                jv = norm_val(row.get(jc))
                if jv:
                    join_values_by_col[jc].add(jv)
                    join_value_counts_by_col[jc][jv] += 1
            if subtype_col:
                sv = norm_val(row.get(subtype_col))
                if sv:
                    subtype_values_by_col[subtype_col].add(sv)

            if has_subtype and has_drug_val and has_response_val:
                status = "SAME_ROW_SUBTYPE_EFFECT_READY"
                rows_same_row_ready += 1
                group_key = (
                    safe_str(drug_val),
                    safe_str(subtype_val),
                    safe_str(response_col),
                    safe_str(subtype_col),
                )
                bucket_row = aggregation_bucket[group_key]
                bucket_row["n_rows"] += 1
                bucket_row["values"].append(response_num)
                bucket_row["drug_identifier"] = safe_str(drug_val)
                bucket_row["subtype"] = safe_str(subtype_val)
                bucket_row["response_column_used"] = safe_str(response_col)
                bucket_row["subtype_column_used"] = safe_str(subtype_col)
                if join_id_cols:
                    _, pair_val = get_first_present(row, join_id_cols)
                    if safe_str(pair_val):
                        bucket_row["cell_values"].add(safe_str(pair_val))
                best_direction_seen[(safe_str(drug_val), safe_str(response_col))] = (direction, direction_status)
            elif not has_subtype:
                status = "MISSING_SUBTYPE_METADATA"
                if len(missing_subtype_rows) < MAX_TABLE_ROWS_MD:
                    missing_subtype_rows.append(
                        {
                            "s3_uri": s3_uri,
                            "row_index": idx,
                            "drug_identifier": safe_str(drug_val),
                            "response_value": safe_str(response_val),
                        }
                    )
            elif not has_response_val:
                status = "MISSING_RESPONSE_SCORE"
                if len(missing_response_rows) < MAX_TABLE_ROWS_MD:
                    missing_response_rows.append(
                        {
                            "s3_uri": s3_uri,
                            "row_index": idx,
                            "drug_identifier": safe_str(drug_val),
                            "subtype": safe_str(subtype_val),
                        }
                    )
            else:
                status = "MISSING_DRUG_IDENTIFIER"

            status_counts[status] += 1
            file_status_counter[status] += 1

        role, role_reason = infer_role(
            file_obj["relative_path"].lower(),
            file_obj["basename"].lower(),
            has_drug=has_drug,
            has_response_col=has_response_col and response_numeric_count > 0,
            has_join_id=has_join_id,
            has_subtype_col=has_subtype_col,
            has_cell_name_col=has_cell_name_col,
        )

        role_item = {
            "s3_uri": s3_uri,
            "extension": ext,
            "rows_inspected": len(sample_rows),
            "reason": role_reason,
        }
        if role == "candidate_result_files":
            candidate_result_files.append(role_item)
        elif role == "pair_response_files":
            pair_response_files.append(role_item)
        elif role == "subtype_metadata_files":
            subtype_metadata_files.append(role_item)
        elif role == "cell_line_metadata_files":
            cell_line_metadata_files.append(role_item)
        else:
            unsupported_or_irrelevant_files.append(role_item)

        if role == "pair_response_files":
            response_file_samples[s3_uri] = {
                "s3_uri": s3_uri,
                "join_id_columns": join_id_cols,
                "join_values_by_col": {k: sorted(v)[:500] for k, v in join_values_by_col.items()},
                "join_value_counts_by_col": {k: dict(v) for k, v in join_value_counts_by_col.items()},
                "response_column": response_col,
                "response_field_key": response_field_key,
                "direction": direction,
                "direction_status": direction_status,
                "response_numeric_count": response_numeric_count,
                "rows_inspected": len(sample_rows),
            }
            if direction_status == "UNKNOWN_DIRECTION":
                status_counts["UNKNOWN_RESPONSE_DIRECTION"] += response_numeric_count
                blockers.append({"s3_uri": s3_uri, "blocker": "UNKNOWN_RESPONSE_DIRECTION", "response_column": response_col})

        if role == "subtype_metadata_files":
            subtype_meta_samples[s3_uri] = {
                "s3_uri": s3_uri,
                "join_id_columns": join_id_cols,
                "join_values_by_col": {k: sorted(v)[:500] for k, v in join_values_by_col.items()},
                "subtype_column": subtype_col,
                "subtype_field_key": subtype_field_key,
                "subtype_value_count": len(next(iter(subtype_values_by_col.values()), set())),
                "rows_inspected": len(sample_rows),
            }

        if columns:
            important_files_columns.append(
                {
                    "s3_uri": s3_uri,
                    "extension": ext,
                    "rows_inspected": len(sample_rows),
                    "detected_columns": columns,
                }
            )

        file_audits.append(
            {
                "s3_uri": s3_uri,
                "extension": ext,
                "size_bytes": file_obj["size_bytes"],
                "relative_path_under_prefix": file_obj["relative_path"],
                "basename": file_obj["basename"],
                "rows_inspected": len(sample_rows),
                "include_hits": file_obj["include_hits"],
                "warnings": warnings,
                "role": role,
                "role_reason": role_reason,
                "detected_columns": columns,
                "field_candidates": field_candidates,
                "chosen_columns": {
                    "subtype_column": subtype_col,
                    "subtype_field_key": subtype_field_key,
                    "response_column": response_col,
                    "response_field_key": response_field_key,
                    "drug_identifier_columns": drug_cols,
                    "join_id_columns": join_id_cols,
                },
                "direction_assumption": {"direction": direction, "direction_status": direction_status},
                "row_status_counts": dict(file_status_counter),
            }
        )

    join_readiness_pairs: list[dict[str, Any]] = []
    join_ready_rows_estimate = 0
    response_files_with_no_join_overlap = 0

    for r_uri, r_meta in response_file_samples.items():
        best_overlap = 0
        best_record: dict[str, Any] | None = None
        for s_uri, s_meta in subtype_meta_samples.items():
            for r_join_col in r_meta.get("join_id_columns", []):
                r_set = set(r_meta.get("join_values_by_col", {}).get(r_join_col, []))
                if not r_set:
                    continue
                for s_join_col in s_meta.get("join_id_columns", []):
                    s_set = set(s_meta.get("join_values_by_col", {}).get(s_join_col, []))
                    if not s_set:
                        continue
                    overlap_vals = sorted(r_set.intersection(s_set))
                    overlap_count = len(overlap_vals)
                    if overlap_count <= 0:
                        continue
                    r_counter = Counter(r_meta.get("join_value_counts_by_col", {}).get(r_join_col, {}))
                    overlap_row_count = int(sum(r_counter.get(v, 0) for v in overlap_vals))
                    record = {
                        "response_file": r_uri,
                        "subtype_metadata_file": s_uri,
                        "response_join_column": r_join_col,
                        "subtype_join_column": s_join_col,
                        "overlap_distinct_values": overlap_count,
                        "overlap_response_rows_estimate": overlap_row_count,
                        "overlap_values_preview": overlap_vals[:20],
                    }
                    join_readiness_pairs.append(record)
                    if overlap_row_count > best_overlap:
                        best_overlap = overlap_row_count
                        best_record = record
        if best_record:
            join_ready_rows_estimate += best_overlap
            status_counts["JOIN_READY_SUBTYPE_EFFECT"] += best_overlap
        else:
            response_files_with_no_join_overlap += 1
            if subtype_meta_samples:
                status_counts["MISSING_JOIN_KEY"] += int(r_meta.get("rows_inspected", 0))

    if not response_file_samples:
        status_counts["MISSING_RESPONSE_TABLE"] = 1

    if response_file_samples and not subtype_meta_samples:
        total_response_rows = int(sum(m.get("rows_inspected", 0) for m in response_file_samples.values()))
        status_counts["MISSING_SUBTYPE_METADATA"] += total_response_rows

    drug_subtype_summary: list[dict[str, Any]] = []
    for (_, _, _, _), item in aggregation_bucket.items():
        stats = aggregate_stats(item["values"])
        drug_subtype_summary.append(
            {
                "drug_identifier": item["drug_identifier"],
                "subtype": item["subtype"],
                "n_rows": item["n_rows"],
                "n_cell_lines": len(item["cell_values"]) if item["cell_values"] else None,
                "mean_response": stats["mean_response"],
                "median_response": stats["median_response"],
                "min_response": stats["min_response"],
                "max_response": stats["max_response"],
                "std_response": stats["std_response"],
                "response_column_used": item["response_column_used"],
                "subtype_column_used": item["subtype_column_used"],
            }
        )

    best_subtype_per_drug: list[dict[str, Any]] = []
    by_drug_col: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in drug_subtype_summary:
        by_drug_col[(safe_str(row["drug_identifier"]), safe_str(row["response_column_used"]))].append(row)
    for (drug_id, response_col), rows in by_drug_col.items():
        direction, direction_status = best_direction_seen.get((drug_id, response_col), ("UNKNOWN", "UNKNOWN_DIRECTION"))
        if direction_status == "UNKNOWN_DIRECTION":
            best_subtype_per_drug.append(
                {
                    "drug_identifier": drug_id,
                    "response_column_used": response_col,
                    "best_subtype": None,
                    "best_mean_response": None,
                    "direction_assumption": direction,
                    "direction_status": direction_status,
                }
            )
            continue
        ranked = [r for r in rows if r.get("mean_response") is not None]
        if not ranked:
            continue
        best = min(ranked, key=lambda x: float(x["mean_response"])) if direction == "LOWER_IS_BETTER" else max(ranked, key=lambda x: float(x["mean_response"]))
        best_subtype_per_drug.append(
            {
                "drug_identifier": drug_id,
                "response_column_used": response_col,
                "best_subtype": best.get("subtype"),
                "best_mean_response": best.get("mean_response"),
                "direction_assumption": direction,
                "direction_status": direction_status,
            }
        )

    if rows_same_row_ready > 0:
        final_ui_readiness_status = "READY_FOR_SUBTYPE_VIEWER_SAME_ROW"
    elif join_ready_rows_estimate > 0:
        final_ui_readiness_status = "READY_FOR_SUBTYPE_VIEWER_JOIN_REQUIRED"
    elif not response_file_samples:
        final_ui_readiness_status = "BLOCKED_NO_RESPONSE_TABLE"
    elif not subtype_meta_samples:
        final_ui_readiness_status = "PARTIAL_READY_NEEDS_SUBTYPE_METADATA"
    elif response_files_with_no_join_overlap > 0:
        final_ui_readiness_status = "BLOCKED_NO_JOIN_KEY"
    else:
        final_ui_readiness_status = "BLOCKED_NO_USABLE_SUBTYPE_EFFECT_DATA"

    config_subtypes = load_config_subtypes(project_root, disease)
    config_set = {safe_str(x) for x in config_subtypes if safe_str(x)}
    discovered_set = {safe_str(x) for x in discovered_subtype_values if safe_str(x)}
    subtype_reference = {
        "config_subtype_labels": sorted(config_set),
        "discovered_subtype_labels": sorted(discovered_set),
        "missing_from_discovered_vs_config": sorted(config_set - discovered_set),
        "discovered_not_in_config": sorted(discovered_set - config_set),
    }

    path_diagnostics = {
        "cwd": str(Path.cwd()),
        "resolved_project_root": str(project_root),
        "script_path": str(Path(__file__)),
        "json_output_path": str(out_json),
        "markdown_output_path": str(out_md),
    }

    audit_json = {
        "generated_at": now_iso(),
        "audit_version": "v2_strict_join_readiness",
        "disease": disease,
        "s3_prefix": safe_str(args.s3_prefix),
        "execute": bool(args.execute),
        "read_only_enforced": True,
        "notes": [
            "No PostgreSQL writes.",
            "No Neo4j writes.",
            "No docking execution.",
            "No value imputation or fabricated rows.",
        ],
        "path_diagnostics": path_diagnostics,
        "total_files_scanned": len(objects),
        "included_files_count": len(included_files),
        "excluded_files_count": int(sum(excluded_reason_counter.values())),
        "excluded_files_count_by_reason": dict(excluded_reason_counter),
        "included_files": [f"s3://{bucket}/{x['key']}" for x in included_files],
        "excluded_files_preview": excluded_files_preview,
        "file_audits": file_audits,
        "candidate_result_files": candidate_result_files,
        "pair_response_files": pair_response_files,
        "subtype_metadata_files": subtype_metadata_files,
        "cell_line_metadata_files": cell_line_metadata_files,
        "unsupported_or_irrelevant_files": unsupported_or_irrelevant_files,
        "rows_inspected": rows_inspected,
        "rows_with_subtype": rows_with_subtype,
        "rows_with_drug_identifier": rows_with_drug_identifier,
        "rows_with_response_score": rows_with_response_score,
        "rows_subtype_effect_ready": rows_same_row_ready,
        "status_counts": dict(status_counts),
        "join_readiness_summary": {
            "response_files_detected": len(response_file_samples),
            "subtype_metadata_files_detected": len(subtype_meta_samples),
            "join_ready_pairs_count": len(join_readiness_pairs),
            "join_ready_rows_estimate": join_ready_rows_estimate,
            "response_files_with_no_join_overlap": response_files_with_no_join_overlap,
            "join_pairs": join_readiness_pairs[:1000],
        },
        "drug_by_subtype_summary": drug_subtype_summary,
        "best_subtype_per_drug": best_subtype_per_drug,
        "missing_subtype_rows": missing_subtype_rows,
        "missing_response_rows": missing_response_rows,
        "detected_columns_per_important_file": important_files_columns,
        "subtype_label_reference": subtype_reference,
        "blockers_or_missing_required_columns": blockers,
        "final_ui_readiness_status": final_ui_readiness_status,
    }

    out_json.write_text(json.dumps(audit_json, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines: list[str] = []
    md_lines.append("# BRCA Subtype-specific Drug Effect Audit (v2 strict)")
    md_lines.append("")
    md_lines.append(f"- generated_at: `{audit_json['generated_at']}`")
    md_lines.append(f"- disease: `{disease}`")
    md_lines.append(f"- s3_prefix: `{safe_str(args.s3_prefix)}`")
    md_lines.append(f"- execute_flag_received: `{bool(args.execute)}`")
    md_lines.append("- docking_execution: `not run`")
    md_lines.append("- postgres_writes: `not run`")
    md_lines.append("- neo4j_writes: `not run`")
    md_lines.append("")
    md_lines.append("## Path diagnostics")
    md_lines.append("")
    md_lines.append(f"- cwd: `{path_diagnostics['cwd']}`")
    md_lines.append(f"- resolved_project_root: `{path_diagnostics['resolved_project_root']}`")
    md_lines.append(f"- script_path: `{path_diagnostics['script_path']}`")
    md_lines.append(f"- json_output_path: `{path_diagnostics['json_output_path']}`")
    md_lines.append(f"- markdown_output_path: `{path_diagnostics['markdown_output_path']}`")
    md_lines.append("")
    md_lines.append("## File Scan Summary")
    md_lines.append("")
    md_lines.append(f"- total files scanned: `{len(objects)}`")
    md_lines.append(f"- included files: `{len(included_files)}`")
    md_lines.append(f"- excluded files: `{int(sum(excluded_reason_counter.values()))}`")
    md_lines.append("")
    md_lines.append("### Excluded files count by reason")
    md_lines.append("")
    for k, v in sorted(excluded_reason_counter.items(), key=lambda x: x[0]):
        md_lines.append(f"- {k}: {v}")
    if not excluded_reason_counter:
        md_lines.append("- none")
    md_lines.append("")
    md_lines.append("## File role split")
    md_lines.append("")
    md_lines.append(f"- candidate_result_files: `{len(candidate_result_files)}`")
    md_lines.append(f"- pair_response_files: `{len(pair_response_files)}`")
    md_lines.append(f"- subtype_metadata_files: `{len(subtype_metadata_files)}`")
    md_lines.append(f"- cell_line_metadata_files: `{len(cell_line_metadata_files)}`")
    md_lines.append(f"- unsupported_or_irrelevant_files: `{len(unsupported_or_irrelevant_files)}`")
    md_lines.append("")
    md_lines.append("## Candidate result files")
    md_lines.append("")
    md_lines.extend(md_table(candidate_result_files[:MAX_TABLE_ROWS_MD], ["s3_uri", "extension", "rows_inspected", "reason"]))
    md_lines.append("")
    md_lines.append("## Pair response files")
    md_lines.append("")
    md_lines.extend(md_table(pair_response_files[:MAX_TABLE_ROWS_MD], ["s3_uri", "extension", "rows_inspected", "reason"]))
    md_lines.append("")
    md_lines.append("## Subtype metadata files")
    md_lines.append("")
    md_lines.extend(md_table(subtype_metadata_files[:MAX_TABLE_ROWS_MD], ["s3_uri", "extension", "rows_inspected", "reason"]))
    md_lines.append("")
    md_lines.append("## Join-readiness summary")
    md_lines.append("")
    md_lines.append(f"- response_files_detected: `{len(response_file_samples)}`")
    md_lines.append(f"- subtype_metadata_files_detected: `{len(subtype_meta_samples)}`")
    md_lines.append(f"- join_ready_pairs_count: `{len(join_readiness_pairs)}`")
    md_lines.append(f"- join_ready_rows_estimate: `{join_ready_rows_estimate}`")
    md_lines.append(f"- response_files_with_no_join_overlap: `{response_files_with_no_join_overlap}`")
    md_lines.append("")
    md_lines.extend(
        md_table(
            join_readiness_pairs[:MAX_TABLE_ROWS_MD],
            [
                "response_file",
                "subtype_metadata_file",
                "response_join_column",
                "subtype_join_column",
                "overlap_distinct_values",
                "overlap_response_rows_estimate",
            ],
        )
    )
    md_lines.append("")
    md_lines.append("## Row-level readiness")
    md_lines.append("")
    md_lines.append(f"- rows inspected: `{rows_inspected}`")
    md_lines.append(f"- rows with subtype: `{rows_with_subtype}`")
    md_lines.append(f"- rows with drug identifier: `{rows_with_drug_identifier}`")
    md_lines.append(f"- rows with response score: `{rows_with_response_score}`")
    md_lines.append(f"- rows_subtype_effect_ready (same row): `{rows_same_row_ready}`")
    md_lines.append("")
    md_lines.append("### Status counts")
    md_lines.append("")
    for k, v in sorted(status_counts.items()):
        md_lines.append(f"- {k}: {v}")
    if rows_same_row_ready == 0:
        md_lines.append("- explanation: same-row subtype effect data was not found in sampled rows; join-ready paths are listed above.")
    md_lines.append("")
    md_lines.append("## Drug-by-subtype summary table")
    md_lines.append("")
    md_lines.extend(
        md_table(
            drug_subtype_summary[:MAX_TABLE_ROWS_MD],
            [
                "drug_identifier",
                "subtype",
                "n_rows",
                "n_cell_lines",
                "mean_response",
                "median_response",
                "min_response",
                "max_response",
                "std_response",
                "response_column_used",
                "subtype_column_used",
            ],
        )
    )
    md_lines.append("")
    md_lines.append("## Best subtype per drug table")
    md_lines.append("")
    md_lines.extend(
        md_table(
            best_subtype_per_drug[:MAX_TABLE_ROWS_MD],
            [
                "drug_identifier",
                "response_column_used",
                "best_subtype",
                "best_mean_response",
                "direction_assumption",
                "direction_status",
            ],
        )
    )
    md_lines.append("")
    md_lines.append("## Missing subtype table")
    md_lines.append("")
    md_lines.extend(md_table(missing_subtype_rows[:MAX_TABLE_ROWS_MD], ["s3_uri", "row_index", "drug_identifier", "response_value"]))
    md_lines.append("")
    md_lines.append("## Missing response table")
    md_lines.append("")
    md_lines.extend(md_table(missing_response_rows[:MAX_TABLE_ROWS_MD], ["s3_uri", "row_index", "drug_identifier", "subtype"]))
    md_lines.append("")
    md_lines.append("## Subtype label reference (config vs discovered)")
    md_lines.append("")
    md_lines.append(f"- config_subtype_labels: `{', '.join(subtype_reference['config_subtype_labels']) if subtype_reference['config_subtype_labels'] else '(none)'}`")
    md_lines.append(f"- discovered_subtype_labels: `{', '.join(subtype_reference['discovered_subtype_labels']) if subtype_reference['discovered_subtype_labels'] else '(none)'}`")
    md_lines.append(f"- missing_from_discovered_vs_config: `{', '.join(subtype_reference['missing_from_discovered_vs_config']) if subtype_reference['missing_from_discovered_vs_config'] else '(none)'}`")
    md_lines.append(f"- discovered_not_in_config: `{', '.join(subtype_reference['discovered_not_in_config']) if subtype_reference['discovered_not_in_config'] else '(none)'}`")
    md_lines.append("")
    md_lines.append("## Final UI readiness")
    md_lines.append("")
    md_lines.append(f"- final_ui_readiness_status: `{final_ui_readiness_status}`")
    md_lines.append("- recommended_next_action: prioritize subtype effect viewer before docking viewer; keep docking gated while blocked statuses remain.")

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"total_files_scanned={len(objects)}")
    print(f"included_files={len(included_files)}")
    print(f"candidate_result_files={len(candidate_result_files)}")
    print(f"pair_response_files={len(pair_response_files)}")
    print(f"subtype_metadata_files={len(subtype_metadata_files)}")
    print(f"rows_inspected={rows_inspected}")
    print(f"rows_subtype_effect_ready={rows_same_row_ready}")
    print(f"final_ui_readiness_status={final_ui_readiness_status}")
    print(f"json_output={out_json}")
    print(f"markdown_output={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
