#!/usr/bin/env python
"""Build Superset-ready dashboard marts from curated S3 analysis profiles.

This script is designed for protocol_guide_v3.1_20260414 style metadata inputs:
- curated_inventory_summary.csv
- curated_schema_profile.csv
- curated_analysis_summary.json

Key behaviors:
- Excludes `curated_date/glue/` prefix from all marts.
- Never mutates source data.
- Builds summary marts for Superset (no wide matrix upload).
- Continues execution even when an input cannot be read; errors are carried in notes/error fields.
- Supports local paths and `s3://` paths for both input and output.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:
    import fsspec  # type: ignore
except Exception:  # pragma: no cover
    fsspec = None


ROLE_MAP: Dict[str, str] = {
    "gdsc": "label_source",
    "tcga": "reference_cohort_fit_source",
    "metabric": "external_validation_cohort",
    "chembl": "drug_structure_smiles_source",
    "drugbank": "drug_synonym_target_source",
    "depmap": "cell_line_dependency_source",
    "lincs": "perturbation_signature_source",
    "admet": "safety_druglikeness_gate",
    "opentargets": "gene_disease_evidence",
    "string": "ppi_network_evidence",
    "msigdb": "pathway_geneset_source",
    "unknown": "needs_review",
}

PROTOCOL_STAGE_MAP: Dict[str, str] = {
    "gdsc": "step3_label_training",
    "tcga": "step3_fit_imputation_variance_feature_selection",
    "metabric": "step6_external_validation",
    "chembl": "step1_smiles_fingerprint_matching",
    "drugbank": "step1_drug_synonym_target_matching",
    "depmap": "step3_dependency_features",
    "lincs": "step3_signature_reversal_evidence",
    "admet": "step7_toxicity_gate",
    "opentargets": "step8_gene_disease_evidence",
    "string": "step8_ppi_network_evidence",
    "msigdb": "step3_pathway_features",
    "unknown": "manual_review",
}

REQUIRED_FOR_MAP: Dict[str, str] = {
    "gdsc": "ln_ic50_label_training",
    "tcga": "fit_imputation_variance_feature_selection",
    "metabric": "external_validation_transform_only",
    "chembl": "smiles_fingerprint_drug_matching",
    "drugbank": "drug_synonym_target_matching",
    "depmap": "dependency_features",
    "lincs": "signature_reversal_evidence",
    "admet": "toxicity_gate",
    "opentargets": "disease_gene_evidence",
    "string": "ppi_network",
    "msigdb": "pathway_features",
}

MATCHING_ROLE_MAP: Dict[str, str] = {
    "chembl": "canonical_smiles_primary",
    "drugbank": "synonym_target_bridge",
    "gdsc": "drug_label_join_anchor",
}

EVIDENCE_TYPE_MAP: Dict[str, str] = {
    "opentargets": "gene_disease",
    "string": "ppi",
    "msigdb": "pathway",
    "drugbank": "drug_target",
    "chembl": "drug_target",
    "lincs": "signature",
    "admet": "safety",
}

EVIDENCE_ROLE_MAP: Dict[str, str] = {
    "opentargets": "disease_gene_evidence",
    "string": "ppi_network_evidence",
    "msigdb": "pathway_geneset_evidence",
    "drugbank": "drug_target_evidence",
    "chembl": "drug_structure_target_evidence",
    "lincs": "perturbation_signature_evidence",
    "admet": "safety_gate_evidence",
}

HIGH_RISK_PATTERNS: Sequence[str] = (
    "ic50",
    "ln_ic50",
    "auc",
    "rmse",
    "z_score",
    "zscore",
    "response",
    "sensitivity",
    "label",
)
MEDIUM_RISK_PATTERNS: Sequence[str] = (
    "target",
    "putative_target",
    "target_id",
    "target_name",
    "target_type",
)


@dataclass
class ReadResult:
    payload: Any
    error: Optional[str]


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return False
        return value != 0
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y", "ok", "readable", "success"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return float(value)
    except Exception:
        return default


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out.columns = [_clean_name(c) for c in out.columns]
    return out


def _s3_open(path: str, mode: str):
    if fsspec is None:
        raise RuntimeError("fsspec is required for s3:// path support.")
    return fsspec.open(path, mode).open()


def _read_csv_any(path: str) -> ReadResult:
    try:
        if path.startswith("s3://"):
            with _s3_open(path, "rb") as fp:
                return ReadResult(pd.read_csv(fp), None)
        return ReadResult(pd.read_csv(path), None)
    except Exception as exc:  # pragma: no cover - runtime IO handling
        return ReadResult(pd.DataFrame(), f"failed_to_read_csv: {path}: {exc}")


def _read_json_any(path: str) -> ReadResult:
    try:
        if path.startswith("s3://"):
            with _s3_open(path, "r") as fp:
                return ReadResult(json.load(fp), None)
        with open(path, "r", encoding="utf-8") as fp:
            return ReadResult(json.load(fp), None)
    except Exception as exc:  # pragma: no cover - runtime IO handling
        return ReadResult({}, f"failed_to_read_json: {path}: {exc}")


def _write_parquet_any(df: pd.DataFrame, path: str) -> Optional[str]:
    try:
        if path.startswith("s3://"):
            with _s3_open(path, "wb") as fp:
                df.to_parquet(fp, index=False)
        else:
            out_path = Path(path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out_path, index=False)
        return None
    except Exception as exc:  # pragma: no cover - runtime IO handling
        return f"failed_to_write_parquet: {path}: {exc}"


def _extract_first(
    row: pd.Series,
    candidates: Sequence[str],
    default: Any = None,
) -> Any:
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return row[c]
    return default


def _parse_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            obj = json.loads(text)
            if isinstance(obj, list):
                return [str(v).strip() for v in obj if str(v).strip()]
        except Exception:
            pass
    split_items = re.split(r"[|;,]", text)
    if len(split_items) == 1 and " " in text and "," not in text and "|" not in text and ";" not in text:
        split_items = text.split()
    return [item.strip() for item in split_items if item.strip()]


def _json_list_text(values: Sequence[str]) -> str:
    unique = []
    seen = set()
    for v in values:
        lv = str(v).strip()
        if not lv:
            continue
        if lv not in seen:
            seen.add(lv)
            unique.append(lv)
    return json.dumps(unique, ensure_ascii=True)


def _contains_any(text: str, patterns: Sequence[str]) -> bool:
    t = str(text).lower()
    return any(p in t for p in patterns)


def _col_match(columns: Sequence[str], patterns: Sequence[str]) -> List[str]:
    matches: List[str] = []
    for col in columns:
        lcol = col.lower()
        if any(p in lcol for p in patterns):
            matches.append(col)
    return matches


def _extract_dataset_from_uri(uri: str) -> str:
    if not uri:
        return "unknown"
    u = uri.replace("\\", "/")
    parts = [p for p in u.split("/") if p]
    if not parts:
        return "unknown"
    if "curated_date" in parts:
        idx = parts.index("curated_date")
        if idx + 1 < len(parts):
            candidate = _clean_name(parts[idx + 1])
            return candidate or "unknown"
    if len(parts) >= 2:
        return _clean_name(parts[-2]) or "unknown"
    return "unknown"


def _is_glue_path(path: str) -> bool:
    if not path:
        return False
    normalized = path.replace("\\", "/").lower()
    return "curated_date/glue/" in normalized or "/glue/" in normalized


def _filter_glue(df: pd.DataFrame, path_cols: Sequence[str]) -> Tuple[pd.DataFrame, int]:
    if df.empty:
        return df.copy(), 0
    mask = pd.Series([False] * len(df))
    for col in path_cols:
        if col in df.columns:
            mask = mask | df[col].fillna("").astype(str).map(_is_glue_path)
    removed = int(mask.sum())
    return df.loc[~mask].copy(), removed


def _normalize_inventory(inventory_df: pd.DataFrame, s3_prefix: Optional[str]) -> Tuple[pd.DataFrame, int]:
    df = _normalize_columns(inventory_df)
    if df.empty:
        return pd.DataFrame(columns=["dataset_name", "file_extension", "file_count", "total_size_mb", "status"]), 0
    if s3_prefix:
        prefix = s3_prefix.lower()
        path_col = None
        for cand in ("s3_uri", "s3_path", "path", "file_path", "uri"):
            if cand in df.columns:
                path_col = cand
                break
        if path_col:
            df = df[df[path_col].fillna("").astype(str).str.lower().str.startswith(prefix)].copy()

    df, removed = _filter_glue(df, ["s3_uri", "s3_path", "path", "file_path", "uri"])
    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        path_value = str(_extract_first(row, ("s3_uri", "s3_path", "path", "file_path", "uri"), "") or "")
        dataset_name = str(_extract_first(row, ("dataset_name", "dataset", "source_dataset"), "") or "").strip().lower()
        if not dataset_name:
            dataset_name = _extract_dataset_from_uri(path_value)
        dataset_name = _clean_name(dataset_name) or "unknown"

        file_name = str(_extract_first(row, ("file_name", "name", "object_key"), "") or "")
        ext_value = str(_extract_first(row, ("file_extension", "extension", "ext"), "") or "").strip().lower()
        if not ext_value:
            target = file_name or path_value
            if "." in target:
                ext_value = target.rsplit(".", 1)[-1].lower()
            else:
                ext_value = "unknown"

        file_count = _as_float(_extract_first(row, ("file_count", "count", "n_files"), 1.0), 1.0)
        if file_count <= 0:
            file_count = 1.0
        size_mb = _as_float(
            _extract_first(row, ("total_size_mb", "size_mb", "file_size_mb"), None),
            default=-1.0,
        )
        if size_mb < 0:
            size_bytes = _as_float(_extract_first(row, ("total_size_bytes", "file_size_bytes", "size_bytes"), 0.0))
            size_mb = size_bytes / (1024.0 * 1024.0) if size_bytes else 0.0

        status = str(_extract_first(row, ("status", "read_status"), "") or "").strip().lower()
        if not status:
            status = "ready"
        rows.append(
            {
                "dataset_name": dataset_name,
                "file_extension": ext_value,
                "file_count": int(round(file_count)),
                "total_size_mb": round(size_mb, 4),
                "status": status,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["dataset_name", "file_extension", "file_count", "total_size_mb", "status"]), removed

    out = pd.DataFrame(rows)
    out = (
        out.groupby(["dataset_name", "file_extension"], dropna=False, as_index=False)
        .agg(file_count=("file_count", "sum"), total_size_mb=("total_size_mb", "sum"))
    )
    out["status"] = out["file_count"].apply(lambda v: "ready" if v > 0 else "missing")
    return out, removed


def _normalize_schema(schema_df: pd.DataFrame, s3_prefix: Optional[str]) -> Tuple[pd.DataFrame, int]:
    df = _normalize_columns(schema_df)
    if df.empty:
        return pd.DataFrame(), 0
    if s3_prefix:
        prefix = s3_prefix.lower()
        path_col = None
        for cand in ("s3_uri", "s3_path", "path", "file_path", "uri"):
            if cand in df.columns:
                path_col = cand
                break
        if path_col:
            df = df[df[path_col].fillna("").astype(str).str.lower().str.startswith(prefix)].copy()

    df, removed = _filter_glue(df, ["s3_uri", "s3_path", "path", "file_path", "uri"])
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        s3_uri = str(_extract_first(row, ("s3_uri", "s3_path", "path", "file_path", "uri"), "") or "")
        file_name = str(_extract_first(row, ("file_name", "name", "object_key"), "") or "")
        if not file_name and s3_uri:
            file_name = s3_uri.replace("\\", "/").rstrip("/").split("/")[-1]
        dataset_name = str(_extract_first(row, ("dataset_name", "dataset", "source_dataset"), "") or "").strip().lower()
        if not dataset_name:
            dataset_name = _extract_dataset_from_uri(s3_uri or file_name)
        dataset_name = _clean_name(dataset_name) or "unknown"

        n_columns = _as_float(_extract_first(row, ("n_columns", "column_count", "num_columns"), 0), 0)
        if n_columns < 0:
            n_columns = 0
        readable = _as_bool(_extract_first(row, ("readable", "is_readable", "can_read"), False))
        error = str(_extract_first(row, ("error", "read_error"), "") or "").strip()

        candidate_columns = (
            "columns",
            "column_names",
            "schema_columns",
            "sample_columns",
            "column_list",
        )
        col_list: List[str] = []
        for c in candidate_columns:
            if c in row and pd.notna(row[c]):
                col_list = _parse_list(row[c])
                if col_list:
                    break
        if not n_columns and col_list:
            n_columns = float(len(col_list))

        records.append(
            {
                "dataset_name": dataset_name,
                "file_name": file_name or "",
                "s3_uri": s3_uri or "",
                "readable": readable,
                "n_columns": int(round(n_columns)),
                "columns": [str(c).strip() for c in col_list if str(c).strip()],
                "error": error,
                "raw": row.to_dict(),
            }
        )
    return pd.DataFrame(records), removed


def _schema_flag(row: pd.Series, key: str, derived: bool) -> bool:
    raw = row.get("raw")
    if isinstance(raw, dict):
        nk = _clean_name(key)
        if nk in raw and pd.notna(raw[nk]):
            return _as_bool(raw[nk])
    return derived


def _notes_with_error(base: str, extra_error: Optional[str]) -> str:
    notes = base.strip()
    if extra_error:
        if notes:
            notes = f"{notes}; input_error={extra_error}"
        else:
            notes = f"input_error={extra_error}"
    return notes


def build_mart_curated_inventory(inventory_norm: pd.DataFrame, inventory_error: Optional[str], removed_glue: int) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    if inventory_norm.empty:
        for ds, role in ROLE_MAP.items():
            rows.append(
                {
                    "dataset_name": ds,
                    "file_extension": "unknown",
                    "file_count": 0,
                    "total_size_mb": 0.0,
                    "role": role,
                    "protocol_stage": PROTOCOL_STAGE_MAP.get(ds, "manual_review"),
                    "status": "missing",
                    "notes": _notes_with_error("inventory_input_missing", inventory_error),
                }
            )
        return pd.DataFrame(rows)

    for _, row in inventory_norm.iterrows():
        dataset_name = str(row["dataset_name"]).strip().lower() or "unknown"
        role = ROLE_MAP.get(dataset_name, "needs_review")
        protocol_stage = PROTOCOL_STAGE_MAP.get(dataset_name, "manual_review")
        notes = ""
        if removed_glue:
            notes = f"excluded_glue_prefix_files={removed_glue}"
        notes = _notes_with_error(notes, inventory_error)
        rows.append(
            {
                "dataset_name": dataset_name,
                "file_extension": str(row["file_extension"]),
                "file_count": int(_as_float(row["file_count"], 0)),
                "total_size_mb": round(_as_float(row["total_size_mb"], 0.0), 4),
                "role": role,
                "protocol_stage": protocol_stage,
                "status": str(row.get("status", "ready")),
                "notes": notes,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["dataset_name", "file_extension"]).reset_index(drop=True)


def build_mart_dataset_readiness(mart_curated_inventory: pd.DataFrame, inventory_error: Optional[str]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    grouped = pd.DataFrame()
    if not mart_curated_inventory.empty:
        grouped = (
            mart_curated_inventory.groupby("dataset_name", as_index=False)
            .agg(file_count=("file_count", "sum"), total_size_mb=("total_size_mb", "sum"))
        )
    grouped_lookup = {str(r["dataset_name"]): r for _, r in grouped.iterrows()} if not grouped.empty else {}

    for dataset, required_for in REQUIRED_FOR_MAP.items():
        record = grouped_lookup.get(dataset)
        file_count = int(_as_float(record["file_count"], 0)) if record is not None else 0
        total_size_mb = round(_as_float(record["total_size_mb"], 0.0), 4) if record is not None else 0.0
        exists_flag = file_count > 0
        readiness_status = "ready" if exists_flag else "missing"
        notes = f"role={ROLE_MAP.get(dataset, 'needs_review')}"
        notes = _notes_with_error(notes, inventory_error)
        rows.append(
            {
                "required_dataset": dataset,
                "required_for": required_for,
                "exists_flag": exists_flag,
                "file_count": file_count,
                "total_size_mb": total_size_mb,
                "readiness_status": readiness_status,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def build_mart_schema_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    target_cols = [
        "dataset_name",
        "file_name",
        "s3_uri",
        "readable",
        "n_columns",
        "has_label_like_columns",
        "has_drug_columns",
        "has_gene_columns",
        "has_cell_line_columns",
        "has_clinical_columns",
        "label_like_columns",
        "drug_columns",
        "gene_columns",
        "cell_line_columns",
        "clinical_columns",
        "error",
    ]
    if schema_norm.empty:
        return pd.DataFrame(
            [
                {
                    "dataset_name": "unknown",
                    "file_name": "__schema_profile_input_missing__",
                    "s3_uri": "",
                    "readable": False,
                    "n_columns": 0,
                    "has_label_like_columns": False,
                    "has_drug_columns": False,
                    "has_gene_columns": False,
                    "has_cell_line_columns": False,
                    "has_clinical_columns": False,
                    "label_like_columns": "[]",
                    "drug_columns": "[]",
                    "gene_columns": "[]",
                    "cell_line_columns": "[]",
                    "clinical_columns": "[]",
                    "error": _notes_with_error("", schema_error),
                }
            ],
            columns=target_cols,
        )

    rows: List[Dict[str, Any]] = []
    for _, row in schema_norm.iterrows():
        cols = [str(c) for c in row.get("columns", [])]
        label_cols = _col_match(cols, HIGH_RISK_PATTERNS)
        drug_cols = _col_match(cols, ("drug", "smiles", "chembl", "drugbank", "pubchem", "compound", "pert"))
        gene_cols = _col_match(cols, ("gene", "symbol", "ensembl", "entrez"))
        cell_cols = _col_match(cols, ("cell", "depmap", "cosmic"))
        clinical_cols = _col_match(cols, ("os_", "rfs", "dfs", "survival", "stage", "subtype", "patient", "sample"))

        rows.append(
            {
                "dataset_name": str(row.get("dataset_name", "unknown")),
                "file_name": str(row.get("file_name", "")),
                "s3_uri": str(row.get("s3_uri", "")),
                "readable": _as_bool(row.get("readable", False)),
                "n_columns": int(_as_float(row.get("n_columns", 0), 0)),
                "has_label_like_columns": _schema_flag(row, "has_label_like_columns", bool(label_cols)),
                "has_drug_columns": _schema_flag(row, "has_drug_columns", bool(drug_cols)),
                "has_gene_columns": _schema_flag(row, "has_gene_columns", bool(gene_cols)),
                "has_cell_line_columns": _schema_flag(row, "has_cell_line_columns", bool(cell_cols)),
                "has_clinical_columns": _schema_flag(row, "has_clinical_columns", bool(clinical_cols)),
                "label_like_columns": _json_list_text(label_cols),
                "drug_columns": _json_list_text(drug_cols),
                "gene_columns": _json_list_text(gene_cols),
                "cell_line_columns": _json_list_text(cell_cols),
                "clinical_columns": _json_list_text(clinical_cols),
                "error": _notes_with_error(str(row.get("error", "")).strip(), schema_error),
            }
        )
    return pd.DataFrame(rows, columns=target_cols)


def _schema_subset(schema_norm: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    if schema_norm.empty:
        return pd.DataFrame()
    return schema_norm[schema_norm["dataset_name"].astype(str).str.lower() == dataset_name].copy()


def build_mart_gdsc_label_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "file_name",
        "has_ln_ic50",
        "has_ic50",
        "has_auc",
        "has_rmse",
        "has_z_score",
        "has_drug_column",
        "has_cell_line_column",
        "label_readiness_status",
        "leakage_warning",
        "notes",
    ]
    gdsc_df = _schema_subset(schema_norm, "gdsc")
    if gdsc_df.empty:
        return pd.DataFrame(
            [
                {
                    "file_name": "__gdsc_not_found__",
                    "has_ln_ic50": False,
                    "has_ic50": False,
                    "has_auc": False,
                    "has_rmse": False,
                    "has_z_score": False,
                    "has_drug_column": False,
                    "has_cell_line_column": False,
                    "label_readiness_status": "missing",
                    "leakage_warning": "none",
                    "notes": _notes_with_error("gdsc_dataset_missing", schema_error),
                }
            ],
            columns=cols,
        )

    rows: List[Dict[str, Any]] = []
    for _, row in gdsc_df.iterrows():
        names = [str(c).lower() for c in row.get("columns", [])]
        has_ln_ic50 = any("ln_ic50" in c for c in names)
        has_ic50 = any("ic50" in c for c in names)
        has_auc = any("auc" in c for c in names)
        has_rmse = any("rmse" in c for c in names)
        has_z_score = any("z_score" in c or "zscore" in c for c in names)
        has_drug_column = any(p in c for c in names for p in ("drug", "compound", "pert_id"))
        has_cell_line_column = any(p in c for c in names for p in ("cell", "cosmic", "depmap"))
        label_metrics = has_ln_ic50 or has_ic50 or has_auc or has_rmse or has_z_score
        if has_ln_ic50 and has_drug_column and has_cell_line_column:
            readiness = "ready"
        elif label_metrics and (has_drug_column or has_cell_line_column):
            readiness = "partial"
        else:
            readiness = "not_ready"
        leakage_warning = "label_columns_detected_exclude_from_features" if label_metrics else "none"
        notes = _notes_with_error(str(row.get("error", "")).strip(), schema_error)
        rows.append(
            {
                "file_name": str(row.get("file_name", "")),
                "has_ln_ic50": has_ln_ic50,
                "has_ic50": has_ic50,
                "has_auc": has_auc,
                "has_rmse": has_rmse,
                "has_z_score": has_z_score,
                "has_drug_column": has_drug_column,
                "has_cell_line_column": has_cell_line_column,
                "label_readiness_status": readiness,
                "leakage_warning": leakage_warning,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_mart_drug_source_coverage(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "dataset_name",
        "file_name",
        "has_smiles",
        "has_chembl_id",
        "has_drugbank_id",
        "has_pubchem_id",
        "has_drug_name",
        "has_synonym",
        "has_target",
        "source_grade",
        "matching_role",
        "notes",
    ]
    target_ds = {"chembl", "drugbank", "gdsc"}
    if schema_norm.empty:
        return pd.DataFrame(
            [
                {
                    "dataset_name": "unknown",
                    "file_name": "__drug_source_input_missing__",
                    "has_smiles": False,
                    "has_chembl_id": False,
                    "has_drugbank_id": False,
                    "has_pubchem_id": False,
                    "has_drug_name": False,
                    "has_synonym": False,
                    "has_target": False,
                    "source_grade": "D",
                    "matching_role": "manual_review",
                    "notes": _notes_with_error("", schema_error),
                }
            ],
            columns=cols,
        )
    rows: List[Dict[str, Any]] = []
    for _, row in schema_norm.iterrows():
        ds = str(row.get("dataset_name", "")).lower()
        if ds not in target_ds:
            continue
        c = [str(v).lower() for v in row.get("columns", [])]
        has_smiles = any("smiles" in x for x in c)
        has_chembl_id = any("chembl" in x and "id" in x for x in c)
        has_drugbank_id = any("drugbank" in x and "id" in x for x in c)
        has_pubchem_id = any("pubchem" in x or re.search(r"\bcid\b", x) for x in c)
        has_drug_name = any("drug" in x and "id" not in x for x in c) or any("compound_name" in x for x in c)
        has_synonym = any("synonym" in x or "alias" in x for x in c)
        has_target = any("target" in x for x in c)

        if ds == "chembl" and has_smiles:
            source_grade = "A"
        elif ds == "drugbank" and has_drugbank_id and has_smiles:
            source_grade = "B"
        elif ds == "drugbank" and (has_synonym or has_target):
            source_grade = "C"
        elif has_pubchem_id:
            source_grade = "D"
        else:
            source_grade = "D"

        rows.append(
            {
                "dataset_name": ds,
                "file_name": str(row.get("file_name", "")),
                "has_smiles": has_smiles,
                "has_chembl_id": has_chembl_id,
                "has_drugbank_id": has_drugbank_id,
                "has_pubchem_id": has_pubchem_id,
                "has_drug_name": has_drug_name,
                "has_synonym": has_synonym,
                "has_target": has_target,
                "source_grade": source_grade,
                "matching_role": MATCHING_ROLE_MAP.get(ds, "manual_review"),
                "notes": _notes_with_error(str(row.get("error", "")).strip(), schema_error),
            }
        )
    if not rows:
        rows.append(
            {
                "dataset_name": "unknown",
                "file_name": "__drug_source_not_found__",
                "has_smiles": False,
                "has_chembl_id": False,
                "has_drugbank_id": False,
                "has_pubchem_id": False,
                "has_drug_name": False,
                "has_synonym": False,
                "has_target": False,
                "source_grade": "D",
                "matching_role": "manual_review",
                "notes": _notes_with_error("chembl/drugbank/gdsc_missing", schema_error),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_mart_depmap_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "file_name",
        "has_depmap_id",
        "has_cosmic_id",
        "has_cell_line",
        "has_gene_dependency_matrix",
        "n_columns",
        "likely_matrix",
        "role",
        "notes",
    ]
    depmap_df = _schema_subset(schema_norm, "depmap")
    if depmap_df.empty:
        return pd.DataFrame(
            [
                {
                    "file_name": "__depmap_not_found__",
                    "has_depmap_id": False,
                    "has_cosmic_id": False,
                    "has_cell_line": False,
                    "has_gene_dependency_matrix": False,
                    "n_columns": 0,
                    "likely_matrix": False,
                    "role": "cell_line_dependency_source",
                    "notes": _notes_with_error("depmap_dataset_missing", schema_error),
                }
            ],
            columns=cols,
        )
    rows: List[Dict[str, Any]] = []
    for _, row in depmap_df.iterrows():
        c = [str(v).lower() for v in row.get("columns", [])]
        n_columns = int(_as_float(row.get("n_columns", 0), 0))
        likely_matrix = n_columns > 1000
        has_depmap_id = any("depmap_id" in x for x in c)
        has_cosmic_id = any("cosmic" in x for x in c)
        has_cell_line = any("cell_line" in x or x == "cell" or "cellname" in x for x in c)
        has_gene_dependency_matrix = likely_matrix or any(
            p in x for x in c for p in ("gene_effect", "dependency", "crispr")
        )
        rows.append(
            {
                "file_name": str(row.get("file_name", "")),
                "has_depmap_id": has_depmap_id,
                "has_cosmic_id": has_cosmic_id,
                "has_cell_line": has_cell_line,
                "has_gene_dependency_matrix": has_gene_dependency_matrix,
                "n_columns": n_columns,
                "likely_matrix": likely_matrix,
                "role": "cell_line_dependency_source",
                "notes": _notes_with_error(str(row.get("error", "")).strip(), schema_error),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_mart_lincs_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "file_name",
        "has_cell_id",
        "has_pert_id",
        "has_gene_id",
        "has_gene_symbol",
        "has_signature_metric",
        "likely_mcf7_related",
        "role",
        "notes",
    ]
    lincs_df = _schema_subset(schema_norm, "lincs")
    if lincs_df.empty:
        return pd.DataFrame(
            [
                {
                    "file_name": "__lincs_not_found__",
                    "has_cell_id": False,
                    "has_pert_id": False,
                    "has_gene_id": False,
                    "has_gene_symbol": False,
                    "has_signature_metric": False,
                    "likely_mcf7_related": False,
                    "role": "perturbation_signature_source",
                    "notes": _notes_with_error("lincs_dataset_missing", schema_error),
                }
            ],
            columns=cols,
        )
    rows: List[Dict[str, Any]] = []
    for _, row in lincs_df.iterrows():
        c = [str(v).lower() for v in row.get("columns", [])]
        file_name = str(row.get("file_name", ""))
        has_cell_id = any("cell_id" in x or x == "cell" or "cell_line" in x for x in c)
        has_pert_id = any("pert_id" in x or "perturb" in x for x in c)
        has_gene_id = any("gene_id" in x or "entrez" in x for x in c)
        has_gene_symbol = any("gene_symbol" in x or x == "symbol" for x in c)
        has_signature_metric = any(
            p in x for x in c for p in ("zscore", "z_score", "score", "logfc", "tau", "t_stat")
        )
        likely_mcf7_related = "mcf7" in file_name.lower() or any("mcf7" in x for x in c)
        rows.append(
            {
                "file_name": file_name,
                "has_cell_id": has_cell_id,
                "has_pert_id": has_pert_id,
                "has_gene_id": has_gene_id,
                "has_gene_symbol": has_gene_symbol,
                "has_signature_metric": has_signature_metric,
                "likely_mcf7_related": likely_mcf7_related,
                "role": "perturbation_signature_source",
                "notes": _notes_with_error(str(row.get("error", "")).strip(), schema_error),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_mart_metabric_validation_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "file_name",
        "has_expression",
        "has_patient_id",
        "has_sample_id",
        "has_os_months",
        "has_os_status",
        "has_rfs_months",
        "has_rfs_status",
        "has_tumor_stage",
        "has_subtype_or_threegene",
        "validation_role",
        "readiness_status",
        "notes",
    ]
    metabric_df = _schema_subset(schema_norm, "metabric")
    if metabric_df.empty:
        return pd.DataFrame(
            [
                {
                    "file_name": "__metabric_not_found__",
                    "has_expression": False,
                    "has_patient_id": False,
                    "has_sample_id": False,
                    "has_os_months": False,
                    "has_os_status": False,
                    "has_rfs_months": False,
                    "has_rfs_status": False,
                    "has_tumor_stage": False,
                    "has_subtype_or_threegene": False,
                    "validation_role": "external_patient_cohort_validation",
                    "readiness_status": "missing",
                    "notes": _notes_with_error("metabric_dataset_missing", schema_error),
                }
            ],
            columns=cols,
        )
    rows: List[Dict[str, Any]] = []
    for _, row in metabric_df.iterrows():
        c = [str(v).lower() for v in row.get("columns", [])]
        n_columns = int(_as_float(row.get("n_columns", 0), 0))
        file_name = str(row.get("file_name", ""))
        has_expression = n_columns > 1000 or any("expression" in x for x in c)
        has_patient_id = any("patient" in x for x in c)
        has_sample_id = any("sample" in x for x in c)
        has_os_months = any(p in x for x in c for p in ("os_month", "overall_survival_month", "os_time"))
        has_os_status = any(p in x for x in c for p in ("os_status", "overall_survival_status", "os_event"))
        has_rfs_months = any(p in x for x in c for p in ("rfs_month", "dfs_month", "relapse_free_survival_month"))
        has_rfs_status = any(p in x for x in c for p in ("rfs_status", "dfs_status", "relapse_event"))
        has_tumor_stage = any("stage" in x for x in c)
        has_subtype_or_threegene = any(
            p in x for x in c for p in ("subtype", "pam50", "threegene", "er_status", "pr_status", "her2")
        )
        if has_expression and ((has_os_months and has_os_status) or (has_rfs_months and has_rfs_status)):
            readiness = "ready_for_external_validation"
        elif has_expression:
            readiness = "partial_survival_missing"
        else:
            readiness = "not_ready"
        caution = (
            "metabric_is_external_validation_only_not_direct_ln_ic50_label"
            "; validation_scope=biological_plausibility/survival_association/graph_ranking_consistency"
        )
        notes = _notes_with_error(caution, schema_error)
        if str(row.get("error", "")).strip():
            notes = f"{notes}; file_error={str(row.get('error')).strip()}"
        rows.append(
            {
                "file_name": file_name,
                "has_expression": has_expression,
                "has_patient_id": has_patient_id,
                "has_sample_id": has_sample_id,
                "has_os_months": has_os_months,
                "has_os_status": has_os_status,
                "has_rfs_months": has_rfs_months,
                "has_rfs_status": has_rfs_status,
                "has_tumor_stage": has_tumor_stage,
                "has_subtype_or_threegene": has_subtype_or_threegene,
                "validation_role": "external_patient_cohort_validation",
                "readiness_status": readiness,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows, columns=cols)


def _risk_for_column(col_name: str) -> Tuple[str, str, str]:
    c = col_name.lower()
    if any(p in c for p in HIGH_RISK_PATTERNS):
        reason = f"high_risk_label_pattern_matched:{col_name}"
        return "high", "label_leakage", reason
    if any(p in c for p in MEDIUM_RISK_PATTERNS):
        reason = f"target_information_can_leak_or_bias_features:{col_name}"
        return "medium", "target_related", reason
    return "low", "none", "no_risk_pattern_matched"


def build_mart_leakage_audit(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "dataset_name",
        "file_name",
        "column_name",
        "risk_level",
        "risk_type",
        "reason",
        "recommended_action",
    ]
    if schema_norm.empty:
        return pd.DataFrame(
            [
                {
                    "dataset_name": "unknown",
                    "file_name": "__schema_profile_missing__",
                    "column_name": "",
                    "risk_level": "low",
                    "risk_type": "none",
                    "reason": _notes_with_error("schema_input_missing", schema_error),
                    "recommended_action": "manual_review",
                }
            ],
            columns=cols,
        )
    evidence_ds = {"opentargets", "string", "msigdb", "drugbank", "chembl", "lincs", "admet"}
    rows: List[Dict[str, Any]] = []
    for _, row in schema_norm.iterrows():
        ds = str(row.get("dataset_name", "unknown"))
        file_name = str(row.get("file_name", ""))
        column_list = [str(v) for v in row.get("columns", [])]
        risky_found = False
        for col in column_list:
            risk_level, risk_type, reason = _risk_for_column(col)
            if risk_level == "low":
                continue
            risky_found = True
            if risk_level == "high":
                if any(k in col.lower() for k in ("ic50", "auc", "rmse", "z_score", "zscore", "response", "sensitivity")):
                    action = "keep_as_label_only"
                else:
                    action = "exclude_from_features"
            else:
                action = "keep_as_evidence_only" if ds in evidence_ds else "manual_review"
            rows.append(
                {
                    "dataset_name": ds,
                    "file_name": file_name,
                    "column_name": col,
                    "risk_level": risk_level,
                    "risk_type": risk_type,
                    "reason": reason,
                    "recommended_action": action,
                }
            )
        if not risky_found:
            rows.append(
                {
                    "dataset_name": ds,
                    "file_name": file_name,
                    "column_name": "",
                    "risk_level": "low",
                    "risk_type": "none",
                    "reason": _notes_with_error("no_risky_columns_detected", schema_error),
                    "recommended_action": "manual_review",
                }
            )
    return pd.DataFrame(rows, columns=cols)


def build_mart_evidence_source_profile(schema_norm: pd.DataFrame, schema_error: Optional[str]) -> pd.DataFrame:
    cols = [
        "dataset_name",
        "file_name",
        "evidence_type",
        "has_gene",
        "has_disease",
        "has_target",
        "has_pathway",
        "has_score",
        "evidence_role",
        "notes",
    ]
    target_ds = set(EVIDENCE_TYPE_MAP.keys())
    if schema_norm.empty:
        return pd.DataFrame(
            [
                {
                    "dataset_name": "unknown",
                    "file_name": "__evidence_input_missing__",
                    "evidence_type": "unknown",
                    "has_gene": False,
                    "has_disease": False,
                    "has_target": False,
                    "has_pathway": False,
                    "has_score": False,
                    "evidence_role": "manual_review",
                    "notes": _notes_with_error("", schema_error),
                }
            ],
            columns=cols,
        )

    rows: List[Dict[str, Any]] = []
    for _, row in schema_norm.iterrows():
        ds = str(row.get("dataset_name", "")).lower()
        if ds not in target_ds:
            continue
        c = [str(v).lower() for v in row.get("columns", [])]
        rows.append(
            {
                "dataset_name": ds,
                "file_name": str(row.get("file_name", "")),
                "evidence_type": EVIDENCE_TYPE_MAP.get(ds, "unknown"),
                "has_gene": any(p in x for x in c for p in ("gene", "symbol", "ensembl", "entrez")),
                "has_disease": any(p in x for x in c for p in ("disease", "efo", "mondo", "mesh")),
                "has_target": any("target" in x for x in c),
                "has_pathway": any(p in x for x in c for p in ("pathway", "geneset", "reactome", "kegg", "hallmark")),
                "has_score": any(p in x for x in c for p in ("score", "pvalue", "qvalue", "confidence", "odds")),
                "evidence_role": EVIDENCE_ROLE_MAP.get(ds, "manual_review"),
                "notes": _notes_with_error(str(row.get("error", "")).strip(), schema_error),
            }
        )

    if not rows:
        rows.append(
            {
                "dataset_name": "unknown",
                "file_name": "__evidence_sources_missing__",
                "evidence_type": "unknown",
                "has_gene": False,
                "has_disease": False,
                "has_target": False,
                "has_pathway": False,
                "has_score": False,
                "evidence_role": "manual_review",
                "notes": _notes_with_error("evidence_datasets_missing", schema_error),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_mart_dashboard_kpis(
    analysis_summary: Dict[str, Any],
    mart_curated_inventory: pd.DataFrame,
    mart_dataset_readiness: pd.DataFrame,
    mart_gdsc_label_profile: pd.DataFrame,
    mart_metabric_validation_profile: pd.DataFrame,
    mart_drug_source_coverage: pd.DataFrame,
    mart_leakage_audit: pd.DataFrame,
    analysis_error: Optional[str],
) -> pd.DataFrame:
    cols = ["metric_group", "metric_name", "metric_value", "status", "notes"]
    file_extensions = analysis_summary.get("file_extensions", {}) if isinstance(analysis_summary, dict) else {}
    if not isinstance(file_extensions, dict):
        file_extensions = {}
    detected_datasets = analysis_summary.get("detected_datasets", None)
    if detected_datasets is None and isinstance(analysis_summary, dict):
        detected_datasets = analysis_summary.get("detected datasets", [])
    if detected_datasets is None:
        detected_datasets = []
    if not isinstance(detected_datasets, list):
        detected_datasets = []

    if mart_curated_inventory.empty:
        inventory_total_files = 0
        inventory_total_size_mb = 0.0
        parquet_count = 0
    else:
        inventory_total_files = int(_as_float(mart_curated_inventory["file_count"].sum(), 0))
        inventory_total_size_mb = round(_as_float(mart_curated_inventory["total_size_mb"].sum(), 0.0), 4)
        parquet_count = int(
            _as_float(
                mart_curated_inventory[mart_curated_inventory["file_extension"].str.lower() == "parquet"]["file_count"].sum(),
                0,
            )
        )

    total_files = int(_as_float(analysis_summary.get("total_files"), inventory_total_files))
    total_size_mb = round(_as_float(analysis_summary.get("total_size_mb"), inventory_total_size_mb), 4)
    parquet_files = int(_as_float(file_extensions.get("parquet", parquet_count), parquet_count))
    readable_profiled_files = int(_as_float(analysis_summary.get("readable_profiled_files"), 0))
    detected_dataset_count = int(_as_float(analysis_summary.get("detected_dataset_count"), len(detected_datasets)))

    readiness_lookup = {}
    if not mart_dataset_readiness.empty:
        readiness_lookup = {
            str(r["required_dataset"]): bool(r["exists_flag"]) for _, r in mart_dataset_readiness.iterrows()
        }

    evidence_required = {"opentargets", "string", "msigdb", "drugbank", "chembl", "lincs", "admet"}
    evidence_sources_exist = int(all(readiness_lookup.get(ds, False) for ds in evidence_required))
    unknown_dataset_count = int(
        _as_float(mart_curated_inventory[mart_curated_inventory["dataset_name"] == "unknown"]["file_count"].sum(), 0)
    )
    leakage_high_risk_columns_count = int(
        len(mart_leakage_audit[mart_leakage_audit["risk_level"] == "high"]) if not mart_leakage_audit.empty else 0
    )
    metabric_survival_ready = int(
        (
            mart_metabric_validation_profile["readiness_status"]
            == "ready_for_external_validation"
        ).any()
        if not mart_metabric_validation_profile.empty
        else 0
    )
    gdsc_label_ready = int(
        (mart_gdsc_label_profile["label_readiness_status"] == "ready").any()
        if not mart_gdsc_label_profile.empty
        else 0
    )

    chembl_ready = False
    drugbank_ready = False
    gdsc_ready = False
    if not mart_drug_source_coverage.empty:
        chembl_rows = mart_drug_source_coverage[mart_drug_source_coverage["dataset_name"] == "chembl"]
        drugbank_rows = mart_drug_source_coverage[mart_drug_source_coverage["dataset_name"] == "drugbank"]
        gdsc_rows = mart_drug_source_coverage[mart_drug_source_coverage["dataset_name"] == "gdsc"]
        chembl_ready = bool((chembl_rows["has_smiles"] == True).any()) if not chembl_rows.empty else False
        drugbank_ready = bool(
            ((drugbank_rows["has_drugbank_id"] == True) | (drugbank_rows["has_synonym"] == True)).any()
        ) if not drugbank_rows.empty else False
        gdsc_ready = bool((gdsc_rows["has_drug_name"] == True).any()) if not gdsc_rows.empty else False
    drug_matching_sources_ready = int(chembl_ready and drugbank_ready and gdsc_ready)

    kpi_rows = [
        ("inventory", "total_files", total_files, "ok" if total_files > 0 else "warning", ""),
        ("inventory", "total_size_mb", total_size_mb, "ok" if total_size_mb > 0 else "warning", ""),
        ("inventory", "parquet_files", parquet_files, "ok" if parquet_files > 0 else "warning", ""),
        (
            "inventory",
            "readable_profiled_files",
            readable_profiled_files,
            "ok" if readable_profiled_files > 0 else "warning",
            "",
        ),
        (
            "inventory",
            "detected_dataset_count",
            detected_dataset_count,
            "ok" if detected_dataset_count > 0 else "warning",
            "",
        ),
        ("readiness", "gdsc_exists", int(readiness_lookup.get("gdsc", False)), "ready" if readiness_lookup.get("gdsc", False) else "missing", ""),
        ("readiness", "tcga_exists", int(readiness_lookup.get("tcga", False)), "ready" if readiness_lookup.get("tcga", False) else "missing", ""),
        ("readiness", "metabric_exists", int(readiness_lookup.get("metabric", False)), "ready" if readiness_lookup.get("metabric", False) else "missing", ""),
        ("readiness", "chembl_exists", int(readiness_lookup.get("chembl", False)), "ready" if readiness_lookup.get("chembl", False) else "missing", ""),
        ("readiness", "drugbank_exists", int(readiness_lookup.get("drugbank", False)), "ready" if readiness_lookup.get("drugbank", False) else "missing", ""),
        ("readiness", "depmap_exists", int(readiness_lookup.get("depmap", False)), "ready" if readiness_lookup.get("depmap", False) else "missing", ""),
        ("readiness", "lincs_exists", int(readiness_lookup.get("lincs", False)), "ready" if readiness_lookup.get("lincs", False) else "missing", ""),
        ("readiness", "admet_exists", int(readiness_lookup.get("admet", False)), "ready" if readiness_lookup.get("admet", False) else "missing", ""),
        ("readiness", "evidence_sources_exist", evidence_sources_exist, "ready" if evidence_sources_exist else "partial", ""),
        ("quality", "unknown_dataset_count", unknown_dataset_count, "ok" if unknown_dataset_count == 0 else "warning", ""),
        (
            "quality",
            "leakage_high_risk_columns_count",
            leakage_high_risk_columns_count,
            "warning" if leakage_high_risk_columns_count > 0 else "ok",
            "",
        ),
        ("quality", "metabric_survival_ready", metabric_survival_ready, "ready" if metabric_survival_ready else "partial", ""),
        ("quality", "gdsc_label_ready", gdsc_label_ready, "ready" if gdsc_label_ready else "partial", ""),
        (
            "quality",
            "drug_matching_sources_ready",
            drug_matching_sources_ready,
            "ready" if drug_matching_sources_ready else "partial",
            "",
        ),
    ]
    out_rows = []
    for group, name, value, status, notes in kpi_rows:
        out_rows.append(
            {
                "metric_group": group,
                "metric_name": name,
                "metric_value": value,
                "status": status,
                "notes": _notes_with_error(notes, analysis_error),
            }
        )
    return pd.DataFrame(out_rows, columns=cols)


def _output_path(base_dir: str, file_name: str) -> str:
    if base_dir.startswith("s3://"):
        return f"{base_dir.rstrip('/')}/{file_name}"
    return str(Path(base_dir) / file_name)


def build_all_marts(
    inventory_summary_path: str,
    schema_profile_path: str,
    analysis_summary_path: str,
    output_dir: str,
    s3_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    inventory_read = _read_csv_any(inventory_summary_path)
    schema_read = _read_csv_any(schema_profile_path)
    analysis_read = _read_json_any(analysis_summary_path)

    inventory_norm, inventory_glue_removed = _normalize_inventory(
        inventory_read.payload if isinstance(inventory_read.payload, pd.DataFrame) else pd.DataFrame(),
        s3_prefix,
    )
    schema_norm, schema_glue_removed = _normalize_schema(
        schema_read.payload if isinstance(schema_read.payload, pd.DataFrame) else pd.DataFrame(),
        s3_prefix,
    )
    analysis_summary = analysis_read.payload if isinstance(analysis_read.payload, dict) else {}

    mart_curated_inventory = build_mart_curated_inventory(inventory_norm, inventory_read.error, inventory_glue_removed)
    mart_dataset_readiness = build_mart_dataset_readiness(mart_curated_inventory, inventory_read.error)
    mart_schema_profile = build_mart_schema_profile(schema_norm, schema_read.error)
    mart_gdsc_label_profile = build_mart_gdsc_label_profile(schema_norm, schema_read.error)
    mart_drug_source_coverage = build_mart_drug_source_coverage(schema_norm, schema_read.error)
    mart_depmap_profile = build_mart_depmap_profile(schema_norm, schema_read.error)
    mart_lincs_profile = build_mart_lincs_profile(schema_norm, schema_read.error)
    mart_metabric_validation_profile = build_mart_metabric_validation_profile(schema_norm, schema_read.error)
    mart_leakage_audit = build_mart_leakage_audit(schema_norm, schema_read.error)
    mart_evidence_source_profile = build_mart_evidence_source_profile(schema_norm, schema_read.error)
    mart_dashboard_kpis = build_mart_dashboard_kpis(
        analysis_summary,
        mart_curated_inventory,
        mart_dataset_readiness,
        mart_gdsc_label_profile,
        mart_metabric_validation_profile,
        mart_drug_source_coverage,
        mart_leakage_audit,
        analysis_read.error,
    )

    mart_map: Dict[str, pd.DataFrame] = {
        "mart_curated_inventory.parquet": mart_curated_inventory,
        "mart_dataset_readiness.parquet": mart_dataset_readiness,
        "mart_schema_profile.parquet": mart_schema_profile,
        "mart_gdsc_label_profile.parquet": mart_gdsc_label_profile,
        "mart_drug_source_coverage.parquet": mart_drug_source_coverage,
        "mart_depmap_profile.parquet": mart_depmap_profile,
        "mart_lincs_profile.parquet": mart_lincs_profile,
        "mart_metabric_validation_profile.parquet": mart_metabric_validation_profile,
        "mart_leakage_audit.parquet": mart_leakage_audit,
        "mart_evidence_source_profile.parquet": mart_evidence_source_profile,
        "mart_dashboard_kpis.parquet": mart_dashboard_kpis,
    }

    write_errors: List[str] = []
    write_results: List[Dict[str, Any]] = []
    for file_name, df in mart_map.items():
        out_path = _output_path(output_dir, file_name)
        err = _write_parquet_any(df, out_path)
        write_results.append({"file": out_path, "rows": len(df), "error": err})
        if err:
            write_errors.append(err)

    return {
        "read_errors": {
            "inventory_summary": inventory_read.error,
            "schema_profile": schema_read.error,
            "analysis_summary": analysis_read.error,
        },
        "glue_rows_excluded": {
            "inventory_summary": inventory_glue_removed,
            "schema_profile": schema_glue_removed,
        },
        "writes": write_results,
        "write_errors": write_errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Superset dashboard marts from curated analysis summaries.")
    parser.add_argument("--inventory-summary", required=True, help="Path to curated_inventory_summary.csv (local or s3://)")
    parser.add_argument("--schema-profile", required=True, help="Path to curated_schema_profile.csv (local or s3://)")
    parser.add_argument("--analysis-summary", required=True, help="Path to curated_analysis_summary.json (local or s3://)")
    parser.add_argument("--output-dir", required=True, help="Output directory for mart parquet files (local or s3://)")
    parser.add_argument("--s3-prefix", required=False, default=None, help="Optional prefix filter for source paths (ex: s3://bucket/curated_date/)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_all_marts(
        inventory_summary_path=args.inventory_summary,
        schema_profile_path=args.schema_profile,
        analysis_summary_path=args.analysis_summary,
        output_dir=args.output_dir,
        s3_prefix=args.s3_prefix,
    )
    print("Build completed: Superset marts")
    for key, value in result["read_errors"].items():
        if value:
            print(f"[read_error] {key}: {value}")
    print(
        "Glue rows excluded:",
        f"inventory={result['glue_rows_excluded']['inventory_summary']},",
        f"schema={result['glue_rows_excluded']['schema_profile']}",
    )
    for row in result["writes"]:
        status = "ok" if not row["error"] else "error"
        print(f"[{status}] {row['file']} rows={row['rows']}")
        if row["error"]:
            print(f"  -> {row['error']}")


if __name__ == "__main__":
    main()
