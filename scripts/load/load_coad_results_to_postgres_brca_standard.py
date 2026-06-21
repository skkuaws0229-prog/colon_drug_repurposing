#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert


DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

DEFAULT_LOCAL_DIR = r"C:\work\drug-project\data_cache\final_data\COAD"
DEFAULT_DISEASE = "COAD"

OUTPUT_DIR = Path("outputs/config_validation")
DOC_PATH = Path("docs/coad_brca_standard_postgres_load_plan.md")
ROLE_MAPPING_CSV = OUTPUT_DIR / "coad_brca_standard_role_mapping.csv"
MISSING_ROLES_CSV = OUTPUT_DIR / "coad_brca_standard_missing_roles.csv"
EXCLUDED_FILES_CSV = OUTPUT_DIR / "coad_brca_standard_excluded_files.csv"
DRY_RUN_REPORT_CSV = OUTPUT_DIR / "coad_brca_standard_dry_run_report.csv"


@dataclass(frozen=True)
class RoleSpec:
    role: str
    brca_relative_path: str
    table_name: str
    parser: str
    required_ext: tuple[str, ...]


ROLE_SPECS: list[RoleSpec] = [
    RoleSpec("top30_unique_candidates", "brca_directive_top30_unique_candidates.csv", "drug_candidate_result", "drug_candidate_result", (".csv", ".tsv", ".txt")),
    RoleSpec("top30_tiered_candidates", "brca_directive_top30_tiered_candidates.csv", "drug_candidate_tier", "drug_candidate_tier", (".csv", ".tsv", ".txt")),
    RoleSpec("model_performance_summary", "brca_model_performance_summary.csv", "model_metric", "model_metric", (".csv", ".tsv", ".txt")),
    RoleSpec("model_performance_detailed", "brca_model_performance_detailed.csv", "model_metric_detailed", "model_metric_detailed", (".csv", ".tsv", ".txt")),
    RoleSpec("ensemble_validation_summary", "brca_directive_ensemble_validation_summary.csv", "ensemble_metric", "ensemble_metric", (".csv", ".tsv", ".txt")),
    RoleSpec("ensemble_source_manifest", "brca_directive_ensemble_source_manifest.csv", "ensemble_source_manifest", "ensemble_source_manifest", (".csv", ".tsv", ".txt", ".json")),
    RoleSpec("copied_source_manifest", "copied_source_manifest.csv", "source_artifact", "source_artifact", (".csv", ".tsv", ".txt", ".json")),
    RoleSpec("reproducibility_manifest", "BRCA_reproducibility_manifest_20260428.json", "run_manifest", "run_manifest", (".json",)),
    RoleSpec("external_validation_top30", "step6_metabric_validation/brca_top30_metabric_scored.csv", "external_validation_result", "external_validation_result", (".csv", ".tsv", ".txt")),
    RoleSpec("external_validation_top15", "step6_metabric_validation/brca_top15_metabric_validated.csv", "external_validation_result", "external_validation_result", (".csv", ".tsv", ".txt")),
    RoleSpec("external_validation_method_a", "step6_metabric_validation/brca_metabric_method_a.csv", "metabric_method_score", "metabric_method_score", (".csv", ".tsv", ".txt")),
    RoleSpec("external_validation_method_b", "step6_metabric_validation/brca_metabric_method_b.csv", "metabric_method_score", "metabric_method_score", (".csv", ".tsv", ".txt")),
    RoleSpec("admet_top30_detailed", "step7_admet_22assay/brca_admet_22assay_top30_detailed.csv", "admet_result", "admet_result", (".csv", ".tsv", ".txt")),
    RoleSpec("final15_after_admet", "step7_admet_22assay/brca_final15_after_admet.csv", "final_candidate_result", "final_candidate_result", (".csv", ".tsv", ".txt")),
    RoleSpec("admet_matches", "step7_admet_22assay/brca_admet_22assay_matches.json", "admet_assay_match", "admet_assay_match", (".json",)),
    RoleSpec("admet_summary", "step7_admet_22assay/brca_admet_22assay_summary.json", "admet_summary", "admet_summary", (".json",)),
]


EXCLUDE_PATTERNS: list[tuple[str, str]] = [
    ("\\curated_data\\", "excluded:curated_data"),
    ("\\external_validation_raw_inputs\\", "excluded:external_validation_raw_inputs"),
    ("family.soft", "excluded:geo_family_soft"),
    ("family.xml", "excluded:geo_family_xml"),
    ("series_matrix", "excluded:geo_series_matrix"),
    ("gpl", "excluded:geo_gpl_or_annotation"),
    ("annotation", "excluded:geo_gpl_or_annotation"),
    ("data_mutations", "excluded:cbioportal_raw"),
    ("data_mrna", "excluded:cbioportal_raw"),
    ("data_cna", "excluded:cbioportal_raw"),
    ("data_log2_cna", "excluded:cbioportal_raw"),
    ("phosphoprotein", "excluded:cptac_raw"),
    ("protein raw", "excluded:cptac_raw"),
    ("cosmic_mutantcensus", "excluded:cosmic_raw"),
    ("clinicaltrials", "excluded:clinicaltrials_raw"),
    ("api snapshot", "excluded:clinicaltrials_raw"),
    ("page json", "excluded:clinicaltrials_raw"),
]


ALIASES: dict[str, list[str]] = {
    "drug_id": ["drug_id", "canonical_drug_id", "drugbank_id", "compound_id", "pert_id", "pubchem_cid", "canonical_drugid"],
    "drug_name": ["drug_name", "compound_name", "pert_iname", "name", "drug_name_norm", "drug"],
    "rank": ["rank", "final_rank", "top_rank", "metabric_rank", "method_rank"],
    "score": ["score", "validation_score", "metabric_score", "ensemble_score", "pred_ic50_mean", "admet_score", "metric_value", "value"],
    "tier": ["tier", "tier_label", "priority_tier"],
    "metric": ["metric", "metric_name", "cv5_spearman", "groupcv_spearman", "scaffoldcv_spearman", "val_spearman_mean"],
    "model": ["model", "model_name", "estimator", "algorithm"],
    "split": ["split", "fold", "dataset", "data_split"],
    "source_name": ["source_name", "artifact_name", "name", "dataset"],
    "source_uri": ["source_uri", "artifact_uri", "uri", "path", "source_s3_uri"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="COAD local dry-run/execute loader using BRCA-loaded role standard only")
    parser.add_argument("--disease", default=DEFAULT_DISEASE)
    parser.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR)
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--limit-rows", type=int, default=None, help="optional cap per matched file for debug")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_name(text_value: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z]+", "_", str(text_value).strip().lower())
    out = re.sub(r"_+", "_", out).strip("_")
    return out or "column"


def normalize_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for col in columns:
        base = norm_name(col)
        idx = seen.get(base, 0)
        seen[base] = idx + 1
        out.append(base if idx == 0 else f"{base}_{idx+1}")
    return out


def tokenize(path_text: str) -> set[str]:
    return {x for x in re.split(r"[^a-z0-9]+", path_text.lower()) if x}


def match_role_score(role: str, relative_path: str) -> int:
    p = relative_path.replace("\\", "/").lower()
    t = tokenize(p)

    def has_all(*words: str) -> bool:
        return all(w in t for w in words)

    if role == "top30_unique_candidates":
        return 100 if (has_all("top30", "unique") and "candidate" in t) else 0
    if role == "top30_tiered_candidates":
        return 100 if (has_all("top30", "tiered") or has_all("top30", "tier1", "tier2", "tier3", "tier4")) else 0
    if role == "model_performance_summary":
        if has_all("model", "performance", "summary"):
            return 100
        if has_all("overfit", "table") and "step4" in t:
            return 90
        return 0
    if role == "model_performance_detailed":
        return 100 if has_all("model", "metrics", "full", "table") else 0
    if role == "ensemble_validation_summary":
        return 100 if has_all("ensemble", "validation", "summary") else 0
    if role == "ensemble_source_manifest":
        if has_all("ensemble", "source", "manifest"):
            return 100
        if has_all("external", "validation", "asset", "manifest"):
            return 95
        return 0
    if role == "copied_source_manifest":
        return 100 if has_all("copied", "source", "manifest") else 0
    if role == "reproducibility_manifest":
        return 100 if has_all("reproducibility", "manifest") else 0
    if role == "external_validation_top30":
        return 100 if ("external" in t and "validation" in t and "top30" in t and "ensemble" in t) else 0
    if role == "external_validation_top15":
        return 100 if ("external" in t and "validation" in t and "top15" in t) else 0
    if role == "external_validation_method_a":
        return 100 if ("external" in t and "validation" in t and ("method_a" in p or has_all("method", "a"))) else 0
    if role == "external_validation_method_b":
        return 100 if ("external" in t and "validation" in t and ("method_b" in p or has_all("method", "b"))) else 0
    if role == "admet_top30_detailed":
        return 100 if ("admet" in t and "top30" in t and ("detailed" in t or "scored" in t)) else 0
    if role == "final15_after_admet":
        if "final15" in t and "admet" in t:
            return 100
        if "top15" in t and "admet" in t:
            return 95
        return 0
    if role == "admet_matches":
        return 100 if ("admet" in t and "matches" in t) else 0
    if role == "admet_summary":
        return 100 if ("admet" in t and "summary" in t) else 0
    return 0


def should_exclude(path_obj: Path, local_root: Path) -> tuple[bool, str]:
    rel = str(path_obj.relative_to(local_root)).replace("/", "\\")
    rel_lower = rel.lower()
    rel_space_norm = re.sub(r"\s+", " ", rel_lower)
    for needle, reason in EXCLUDE_PATTERNS:
        n = needle.lower()
        if n.startswith("\\") and n.endswith("\\"):
            if n in rel_lower:
                return True, reason
            continue
        if n in rel_lower or n in rel_space_norm:
            return True, reason
    return False, ""


def read_tabular(path_obj: Path, limit_rows: int | None = None) -> pd.DataFrame:
    lower = path_obj.name.lower()
    sep = "\t" if lower.endswith(".tsv") else None
    if lower.endswith(".txt"):
        if sep is None:
            df = pd.read_csv(path_obj, sep=None, engine="python", low_memory=False, nrows=limit_rows)
        else:
            df = pd.read_csv(path_obj, sep=sep, low_memory=False, nrows=limit_rows)
    else:
        if sep is None:
            df = pd.read_csv(path_obj, low_memory=False, nrows=limit_rows)
        else:
            df = pd.read_csv(path_obj, sep=sep, low_memory=False, nrows=limit_rows)
    out = df.copy()
    out.columns = normalize_columns([str(c) for c in out.columns])
    return out


def read_json(path_obj: Path) -> Any:
    raw = path_obj.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "cp949"):
        try:
            return json.loads(raw.decode(encoding))
        except Exception:
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))


def get_env(name: str) -> str:
    return os.getenv(name, DEFAULT_POSTGRES[name])


def build_database_url() -> str:
    return (
        f"postgresql+psycopg2://{get_env('POSTGRES_USER')}:{get_env('POSTGRES_PASSWORD')}"
        f"@{get_env('POSTGRES_HOST')}:{get_env('POSTGRES_PORT')}/{get_env('POSTGRES_DB')}"
    )


def find_first_key(record: dict[str, Any], alias_key: str, default: Any = None) -> Any:
    keys = ALIASES.get(alias_key, [])
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
        if isinstance(value, str) and value.strip() == "":
            continue
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
    except Exception:
        return None


def to_int(value: Any, default: int = -1) -> int:
    num = to_float(value)
    if num is None:
        return default
    return int(num)


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
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [to_jsonable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return str(value)


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {norm_name(str(k)): to_jsonable(v) for k, v in record.items()}


def infer_source_run_id(local_file: Path, local_root: Path) -> str:
    rel = str(local_file.relative_to(local_root)).replace("\\", "/")
    first_part = rel.split("/", 1)[0] if "/" in rel else rel
    if re.match(r"^\d{8}_[a-z0-9_]+$", first_part.lower()):
        return first_part
    match = re.search(r"(\d{8}_[a-z0-9_]+)", rel.lower())
    if match:
        return match.group(1)
    return "UNKNOWN_RUN_ID"


def required_groups_for_role(role: str) -> list[list[str]]:
    if role in {"top30_unique_candidates", "top30_tiered_candidates", "final15_after_admet", "admet_top30_detailed", "external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b"}:
        return [ALIASES["drug_name"], ALIASES["rank"]]
    if role == "model_performance_summary":
        return [ALIASES["model"], ALIASES["metric"]]
    if role == "model_performance_detailed":
        return [ALIASES["model"], ALIASES["split"], ALIASES["metric"]]
    if role in {"ensemble_source_manifest", "copied_source_manifest"}:
        return [ALIASES["source_name"]]
    if role in {"reproducibility_manifest", "admet_summary", "admet_matches"}:
        return []
    return []


def has_alias_column(columns: set[str], aliases: list[str]) -> bool:
    for alias in aliases:
        if norm_name(alias) in columns:
            return True
    return False


def validate_schema(role: str, tabular_df: pd.DataFrame | None, json_payload: Any) -> tuple[bool, str, list[str]]:
    warnings: list[str] = []
    if role in {"reproducibility_manifest", "admet_summary", "admet_matches"}:
        if json_payload is None:
            return False, "expected_json_missing", warnings
        return True, "json_payload_present", warnings

    if tabular_df is None:
        if role in {"ensemble_source_manifest", "copied_source_manifest"} and isinstance(json_payload, dict):
            return True, "manifest_json_present", warnings
        return False, "tabular_payload_missing", warnings

    columns = {norm_name(c) for c in tabular_df.columns}
    missing_groups: list[str] = []
    for aliases in required_groups_for_role(role):
        if not has_alias_column(columns, aliases):
            missing_groups.append("|".join(sorted({norm_name(a) for a in aliases})))

    if missing_groups:
        return False, f"missing_required_groups:{';'.join(missing_groups)}", warnings

    if role in {"model_performance_summary", "model_performance_detailed"}:
        numeric_cols = 0
        for col in tabular_df.columns:
            series = pd.to_numeric(tabular_df[col], errors="coerce")
            if series.notna().any():
                numeric_cols += 1
        if numeric_cols == 0:
            return False, "no_numeric_metric_like_columns", warnings

    return True, "schema_ok", warnings


def assess_quality(role: str, tabular_df: pd.DataFrame | None) -> dict[str, Any]:
    if tabular_df is None:
        return {
            "row_count": None,
            "null_risk": "n/a",
            "duplicate_risk": "n/a",
            "rank_numeric_check": "n/a",
            "score_numeric_check": "n/a",
        }

    row_count = int(tabular_df.shape[0])
    cols = list(tabular_df.columns)
    cols_norm = [norm_name(c) for c in cols]
    null_rates = tabular_df.isna().mean().fillna(0.0)
    high_null_cols = [str(cols[i]) for i, r in enumerate(null_rates.tolist()) if float(r) >= 0.5]
    null_risk = "high" if len(high_null_cols) > 0 else ("medium" if bool((null_rates > 0.2).any()) else "low")

    dup_keys: list[str] = []
    if role in {"top30_unique_candidates", "top30_tiered_candidates", "final15_after_admet", "admet_top30_detailed", "external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b"}:
        for key in ["drug_id", "drug_name", "rank"]:
            aliases = [norm_name(a) for a in ALIASES[key]]
            found = next((c for c in cols_norm if c in aliases), None)
            if found:
                dup_keys.append(found)
        if role == "top30_tiered_candidates":
            tier_found = next((c for c in cols_norm if c in [norm_name(x) for x in ALIASES["tier"]]), None)
            if tier_found:
                dup_keys.append(tier_found)
    elif role in {"model_performance_summary", "model_performance_detailed"}:
        for key in ["model", "metric"]:
            aliases = [norm_name(a) for a in ALIASES[key]]
            found = next((c for c in cols_norm if c in aliases), None)
            if found:
                dup_keys.append(found)
        if role == "model_performance_detailed":
            split_found = next((c for c in cols_norm if c in [norm_name(x) for x in ALIASES["split"]]), None)
            if split_found:
                dup_keys.append(split_found)

    duplicate_risk = "unknown"
    if dup_keys:
        dup_count = int(tabular_df.duplicated(subset=dup_keys, keep=False).sum())
        duplicate_risk = "high" if dup_count > 0 else "low"
    else:
        duplicate_risk = "unknown"

    def numeric_check_for_alias(alias_name: str) -> str:
        alias_cols = [norm_name(a) for a in ALIASES[alias_name]]
        target_col = next((col for col in cols_norm if col in alias_cols), None)
        if target_col is None:
            return "column_missing"
        idx = cols_norm.index(target_col)
        s = tabular_df.iloc[:, idx]
        non_null = int(s.notna().sum())
        if non_null == 0:
            return "non_null_zero"
        numeric_non_null = int(pd.to_numeric(s, errors="coerce").notna().sum())
        if numeric_non_null == non_null:
            return "pass_numeric"
        return "partial_non_numeric"

    rank_check = numeric_check_for_alias("rank") if role in {"top30_unique_candidates", "top30_tiered_candidates", "final15_after_admet", "admet_top30_detailed", "external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b"} else "n/a"
    score_check = numeric_check_for_alias("score") if role in {"top30_unique_candidates", "top30_tiered_candidates", "admet_top30_detailed", "external_validation_top30", "external_validation_top15", "external_validation_method_a", "external_validation_method_b", "model_performance_summary", "model_performance_detailed"} else "n/a"

    return {
        "row_count": row_count,
        "null_risk": null_risk,
        "duplicate_risk": duplicate_risk,
        "rank_numeric_check": rank_check,
        "score_numeric_check": score_check,
        "high_null_columns": high_null_cols,
    }


def common_meta(
    disease: str,
    source_run_id: str,
    source_file: Path,
    source_role: str,
    source_disease_cache: str,
    loaded_at: str,
) -> dict[str, Any]:
    return {
        "disease": disease,
        "run_id": source_run_id,
        "source_s3_uri": str(source_file),
        "source_disease_cache": source_disease_cache,
        "source_file": str(source_file),
        "source_role": source_role,
        "source_run_id": source_run_id,
        "loaded_at": loaded_at,
    }


def as_tabular_manifest_rows(json_payload: Any) -> list[dict[str, Any]]:
    if isinstance(json_payload, list):
        return [x for x in json_payload if isinstance(x, dict)]
    if isinstance(json_payload, dict):
        copied = json_payload.get("copied_existing_result_files")
        if isinstance(copied, list):
            rows: list[dict[str, Any]] = []
            for item in copied:
                rows.append(
                    {
                        "artifact_name": str(item),
                        "source_name": str(item),
                        "artifact_uri": str(item),
                        "source_uri": str(item),
                        "artifact_type": "manifest_entry",
                        "weight": None,
                    }
                )
            return rows
        return [json_payload]
    return []


def parse_rows_for_insert(
    role_spec: RoleSpec,
    disease: str,
    source_run_id: str,
    source_file: Path,
    source_disease_cache: str,
    tabular_df: pd.DataFrame | None,
    json_payload: Any,
    loaded_at: str,
) -> list[dict[str, Any]]:
    role = role_spec.role
    parser = role_spec.parser
    rows: list[dict[str, Any]] = []
    meta = common_meta(disease, source_run_id, source_file, role, source_disease_cache, loaded_at)

    if parser == "run_manifest":
        raw_bytes = source_file.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        rows.append(
            {
                **meta,
                "manifest_name": source_file.name,
                "manifest_sha256": sha256,
                "manifest_json": to_jsonable(json_payload),
                "payload": {"meta": meta, "manifest": to_jsonable(json_payload)},
            }
        )
        return rows

    if parser == "admet_summary":
        if isinstance(json_payload, dict):
            for key, value in json_payload.items():
                rows.append(
                    {
                        **meta,
                        "summary_key": norm_name(str(key)),
                        "summary_value": json.dumps(to_jsonable(value), ensure_ascii=False),
                        "payload": {"meta": meta, str(key): to_jsonable(value)},
                    }
                )
        elif isinstance(json_payload, list):
            for idx, value in enumerate(json_payload, start=1):
                rows.append(
                    {
                        **meta,
                        "summary_key": f"item_{idx}",
                        "summary_value": json.dumps(to_jsonable(value), ensure_ascii=False),
                        "payload": {"meta": meta, "value": to_jsonable(value)},
                    }
                )
        else:
            rows.append(
                {
                    **meta,
                    "summary_key": "value",
                    "summary_value": json.dumps(to_jsonable(json_payload), ensure_ascii=False),
                    "payload": {"meta": meta, "value": to_jsonable(json_payload)},
                }
            )
        return rows

    if parser == "admet_assay_match":
        if isinstance(json_payload, dict):
            for top_key, rec in json_payload.items():
                if not isinstance(rec, dict):
                    continue
                drug_id = str(rec.get("drug_id", "") or "")
                drug_name = str(rec.get("drug_name", top_key) or top_key)
                assays = rec.get("assays")
                if not isinstance(assays, dict):
                    continue
                for assay_name, assay_payload in assays.items():
                    payload_rec = assay_payload if isinstance(assay_payload, dict) else {"value": assay_payload}
                    payload_norm = normalize_record(payload_rec)
                    rows.append(
                        {
                            **meta,
                            "drug_id": drug_id,
                            "drug_name": drug_name,
                            "assay_name": str(assay_name),
                            "match_value": str(payload_norm.get("value") or payload_norm.get("match_value") or ""),
                            "match_score": to_float(payload_norm.get("similarity") or payload_norm.get("match_score") or payload_norm.get("score")),
                            "payload": {"meta": meta, **payload_norm},
                        }
                    )
        return rows

    if tabular_df is None:
        if parser in {"ensemble_source_manifest", "source_artifact"}:
            manifest_rows = as_tabular_manifest_rows(json_payload)
            tabular_df = pd.DataFrame(manifest_rows)
            tabular_df.columns = normalize_columns([str(c) for c in tabular_df.columns])
        else:
            return rows

    for raw in tabular_df.to_dict(orient="records"):
        record = normalize_record(raw)
        base = {
            **meta,
            "drug_id": str(find_first_key(record, "drug_id", "") or ""),
            "drug_name": str(find_first_key(record, "drug_name", "") or ""),
            "rank": to_int(find_first_key(record, "rank", -1), default=-1),
            "score": to_float(find_first_key(record, "score")),
            "payload": {"meta": meta, **record},
        }

        if parser == "drug_candidate_result":
            rows.append(base)
            continue
        if parser == "drug_candidate_tier":
            rows.append({**base, "tier": str(find_first_key(record, "tier", "") or "")})
            continue
        if parser == "final_candidate_result":
            rows.append({**base, "final_verdict": str(record.get("final_verdict") or record.get("admet_verdict") or record.get("verdict") or record.get("status") or "")})
            continue
        if parser == "admet_result":
            rows.append(
                {
                    **base,
                    "admet_verdict": str(record.get("admet_verdict") or record.get("verdict") or record.get("pass_fail") or record.get("status") or ""),
                    "hard_fail": to_bool(record.get("hard_fail") or record.get("hard_fail_flag") or record.get("is_hard_fail")),
                }
            )
            continue
        if parser == "external_validation_result":
            validation_source = "top30" if role == "external_validation_top30" else ("top15" if role == "external_validation_top15" else "")
            rows.append(
                {
                    **base,
                    "validation_source": validation_source,
                    "validation_score": to_float(record.get("validation_score") or record.get("metabric_score") or record.get("score") or record.get("pred_ic50_mean")),
                }
            )
            continue
        if parser == "metabric_method_score":
            method = "method_a" if role == "external_validation_method_a" else "method_b"
            rows.append({**base, "method": method})
            continue
        if parser in {"model_metric", "model_metric_detailed"}:
            model = str(find_first_key(record, "model", "") or "")
            split = str(find_first_key(record, "split", "") or "")
            metric_name = record.get("metric") or record.get("metric_name")
            metric_value = record.get("metric_value") or record.get("value") or record.get("score")
            if metric_name is not None and to_float(metric_value) is not None:
                metric_rows = [(str(metric_name), to_float(metric_value))]
            else:
                metric_rows = []
                skip = {"model", "model_name", "estimator", "algorithm", "split", "fold", "dataset", "data_split"}
                for key, value in record.items():
                    if key in skip:
                        continue
                    as_num = to_float(value)
                    if as_num is None:
                        continue
                    metric_rows.append((str(key), as_num))
            for metric, metric_num in metric_rows:
                row_metric = {
                    **meta,
                    "model": model,
                    "metric": metric,
                    "metric_value": metric_num,
                    "payload": {"meta": meta, **record},
                }
                if parser == "model_metric_detailed":
                    row_metric["split"] = split
                rows.append(row_metric)
            continue
        if parser == "ensemble_metric":
            metric_name = record.get("metric") or record.get("metric_name") or record.get("phase") or "ensemble_metric"
            metric_value = to_float(record.get("metric_value") or record.get("value") or record.get("score"))
            if metric_value is None:
                for k, v in record.items():
                    n = to_float(v)
                    if n is not None:
                        metric_name = str(k)
                        metric_value = n
                        break
            rows.append({**meta, "metric": str(metric_name), "metric_value": metric_value, "payload": {"meta": meta, **record}})
            continue
        if parser == "ensemble_source_manifest":
            rows.append(
                {
                    **meta,
                    "model": str(find_first_key(record, "model", "") or ""),
                    "source_name": str(find_first_key(record, "source_name", "") or ""),
                    "source_uri": str(find_first_key(record, "source_uri", "") or ""),
                    "weight": to_float(record.get("weight") or record.get("ensemble_weight") or record.get("contribution")),
                    "payload": {"meta": meta, **record},
                }
            )
            continue
        if parser == "source_artifact":
            rows.append(
                {
                    **meta,
                    "artifact_name": str(record.get("artifact_name") or record.get("source_name") or record.get("name") or source_file.name),
                    "artifact_type": str(record.get("artifact_type") or record.get("source_type") or record.get("type") or ""),
                    "artifact_uri": str(record.get("artifact_uri") or record.get("source_uri") or record.get("uri") or str(source_file)),
                    "artifact_hash": str(record.get("artifact_hash") or record.get("sha256") or record.get("md5") or ""),
                    "payload": {"meta": meta, **record},
                }
            )
            continue

    return rows


def filter_rows_for_table(table: Table, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cols = {c.name for c in table.columns}
    filtered: list[dict[str, Any]] = []
    for row in rows:
        out = {k: v for k, v in row.items() if k in cols}
        if "payload" in cols:
            existing = out.get("payload")
            payload = existing if isinstance(existing, dict) else {}
            payload.setdefault("source_disease_cache", row.get("source_disease_cache"))
            payload.setdefault("source_file", row.get("source_file"))
            payload.setdefault("source_role", row.get("source_role"))
            payload.setdefault("source_run_id", row.get("source_run_id"))
            payload.setdefault("loaded_at", row.get("loaded_at"))
            out["payload"] = payload
        if "source_s3_uri" in cols:
            out["source_s3_uri"] = row.get("source_file")
        if "run_id" in cols:
            out["run_id"] = row.get("source_run_id") or row.get("run_id")
        filtered.append(out)
    return filtered


def delete_for_source(conn: Any, table_name: str, disease: str, run_id: str, source_file: str) -> int:
    result = conn.execute(
        text(
            f"""
            DELETE FROM {table_name}
            WHERE disease = :disease
              AND run_id = :run_id
              AND source_s3_uri = :source_s3_uri
            """
        ),
        {"disease": disease, "run_id": run_id, "source_s3_uri": source_file},
    )
    return int(result.rowcount or 0)


def insert_rows(conn: Any, table: Table, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn.execute(pg_insert(table).values(rows))
    return len(rows)


def write_csv(path_obj: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out_row = {k: row.get(k) for k in fieldnames}
            writer.writerow(out_row)


def write_markdown_plan(
    path_obj: Path,
    disease: str,
    local_dir: Path,
    role_rows: list[dict[str, Any]],
    matched_roles: list[str],
    missing_roles: list[str],
    excluded_count: int,
    dry_run_status: str,
    execute_mode: bool,
) -> None:
    lines: list[str] = []
    lines.append("# COAD BRCA-Standard PostgreSQL Load Plan")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- disease: `{disease}`")
    lines.append(f"- source cache root: `{local_dir}`")
    lines.append("- standard: BRCA-loaded file-role standard only")
    lines.append("- mode default: dry-run")
    lines.append("- COAD biology guardrails retained:")
    lines.append("  - driver_genes: APC, TP53, KRAS, BRAF, PIK3CA, MSI")
    lines.append("  - molecular_subtype: CMS1, CMS2, CMS3, CMS4")
    lines.append("  - MSI remains under driver_genes (no biomarker creation)")
    lines.append("")
    lines.append("## Role Mapping")
    lines.append("| role | brca_artifact | target_table | matched | validation | file |")
    lines.append("|---|---|---|---|---|---|")
    for row in role_rows:
        lines.append(
            f"| {row['source_role']} | `{row['brca_artifact']}` | `{row['target_table']}` | {row['match_status']} | {row['validation_status']} | `{row.get('matched_file','')}` |"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- matched_roles_count: {len(matched_roles)}")
    lines.append(f"- missing_roles_count: {len(missing_roles)}")
    lines.append(f"- excluded_files_count: {excluded_count}")
    lines.append(f"- dry_run_status: {dry_run_status}")
    lines.append(f"- execute_mode: {str(execute_mode).lower()}")
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.dry_run and not args.execute:
        args.dry_run = True

    disease = str(args.disease).strip().upper()
    if disease != "COAD":
        raise ValueError(f"Only COAD is allowed in this bounded loader. requested={disease}")

    project_root = Path(__file__).resolve().parents[2]
    local_dir = Path(os.path.abspath(str(args.local_dir)))
    if not local_dir.exists() or not local_dir.is_dir():
        raise FileNotFoundError(f"local-dir not found or not a directory: {local_dir}")

    all_files = sorted([p for p in local_dir.rglob("*") if p.is_file()])

    excluded_rows: list[dict[str, Any]] = []
    candidate_files: list[Path] = []
    for path_obj in all_files:
        excluded, reason = should_exclude(path_obj, local_dir)
        if excluded:
            excluded_rows.append(
                {
                    "disease": disease,
                    "source_disease_cache": str(local_dir),
                    "relative_path": str(path_obj.relative_to(local_dir)).replace("/", "\\"),
                    "absolute_path": str(path_obj),
                    "exclude_reason": reason,
                }
            )
            continue
        candidate_files.append(path_obj)

    matched: dict[str, Path] = {}
    match_details: dict[str, dict[str, Any]] = {}
    used_files: set[str] = set()

    for spec in ROLE_SPECS:
        scored: list[tuple[int, Path]] = []
        for file_path in candidate_files:
            ext = file_path.suffix.lower()
            if ext not in spec.required_ext:
                continue
            rel = str(file_path.relative_to(local_dir)).replace("/", "\\")
            score = match_role_score(spec.role, rel)
            if score <= 0:
                continue
            scored.append((score, file_path))
        scored.sort(key=lambda x: (-x[0], str(x[1]).lower()))
        chosen: Path | None = None
        chosen_score = 0
        for score, file_path in scored:
            if str(file_path) in used_files:
                continue
            chosen = file_path
            chosen_score = score
            break
        if chosen is not None:
            matched[spec.role] = chosen
            used_files.add(str(chosen))
            match_details[spec.role] = {"score": chosen_score, "candidate_count": len(scored)}
        else:
            match_details[spec.role] = {"score": 0, "candidate_count": len(scored)}

    role_mapping_rows: list[dict[str, Any]] = []
    missing_role_rows: list[dict[str, Any]] = []
    dry_run_rows: list[dict[str, Any]] = []
    execute_batches: list[dict[str, Any]] = []

    loaded_at = now_iso()
    matched_roles: list[str] = []
    missing_roles: list[str] = []

    for spec in ROLE_SPECS:
        role = spec.role
        matched_file = matched.get(role)
        match_status = "matched" if matched_file is not None else "missing"
        if matched_file is None:
            missing_roles.append(role)
            missing_role_rows.append(
                {
                    "disease": disease,
                    "source_role": role,
                    "brca_artifact": spec.brca_relative_path,
                    "target_table": spec.table_name,
                    "missing_reason": "no_coad_counterpart_found_by_brca_pattern",
                }
            )
            role_mapping_rows.append(
                {
                    "disease": disease,
                    "source_role": role,
                    "brca_artifact": spec.brca_relative_path,
                    "target_table": spec.table_name,
                    "parser": spec.parser,
                    "match_status": match_status,
                    "matched_file": "",
                    "match_score": 0,
                    "candidate_count": match_details[role]["candidate_count"],
                    "validation_status": "not_applicable_missing",
                    "row_count": "",
                }
            )
            continue

        matched_roles.append(role)
        tabular_df: pd.DataFrame | None = None
        json_payload: Any = None
        read_error = ""
        try:
            if matched_file.suffix.lower() == ".json":
                json_payload = read_json(matched_file)
            else:
                tabular_df = read_tabular(matched_file, limit_rows=args.limit_rows)
        except Exception as exc:  # noqa: BLE001
            read_error = str(exc)

        validation_status = "failed_read" if read_error else "validated"
        validation_reason = f"read_error:{read_error}" if read_error else ""
        warnings: list[str] = []
        if not read_error:
            schema_ok, schema_reason, warn_list = validate_schema(role, tabular_df, json_payload)
            warnings.extend(warn_list)
            validation_status = "passed" if schema_ok else "failed_schema"
            validation_reason = schema_reason

        quality = assess_quality(role, tabular_df)
        row_count = quality["row_count"]
        columns = [] if tabular_df is None else list(tabular_df.columns)

        if validation_status == "passed":
            source_run_id = infer_source_run_id(matched_file, local_dir)
            parsed_rows = parse_rows_for_insert(
                role_spec=spec,
                disease=disease,
                source_run_id=source_run_id,
                source_file=matched_file,
                source_disease_cache=str(local_dir),
                tabular_df=tabular_df,
                json_payload=json_payload,
                loaded_at=loaded_at,
            )
            execute_batches.append(
                {
                    "spec": spec,
                    "source_run_id": source_run_id,
                    "source_file": matched_file,
                    "rows": parsed_rows,
                }
            )

        role_mapping_rows.append(
            {
                "disease": disease,
                "source_role": role,
                "brca_artifact": spec.brca_relative_path,
                "target_table": spec.table_name,
                "parser": spec.parser,
                "match_status": match_status,
                "matched_file": str(matched_file),
                "match_score": match_details[role]["score"],
                "candidate_count": match_details[role]["candidate_count"],
                "validation_status": validation_status,
                "row_count": row_count if row_count is not None else "",
            }
        )

        dry_run_rows.append(
            {
                "disease": disease,
                "source_disease_cache": str(local_dir),
                "source_role": role,
                "target_table": spec.table_name,
                "parser": spec.parser,
                "source_file": str(matched_file),
                "source_run_id": infer_source_run_id(matched_file, local_dir),
                "file_extension": matched_file.suffix.lower(),
                "schema_header": json.dumps(columns, ensure_ascii=False),
                "row_count": row_count,
                "null_risk": quality["null_risk"],
                "duplicate_risk": quality["duplicate_risk"],
                "rank_numeric_check": quality["rank_numeric_check"],
                "score_numeric_check": quality["score_numeric_check"],
                "validation_status": validation_status,
                "validation_reason": validation_reason,
                "warnings": json.dumps(warnings, ensure_ascii=False),
                "high_null_columns": json.dumps(quality.get("high_null_columns", []), ensure_ascii=False),
                "created_or_loaded_at": loaded_at,
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        ROLE_MAPPING_CSV,
        role_mapping_rows,
        [
            "disease",
            "source_role",
            "brca_artifact",
            "target_table",
            "parser",
            "match_status",
            "matched_file",
            "match_score",
            "candidate_count",
            "validation_status",
            "row_count",
        ],
    )
    write_csv(
        MISSING_ROLES_CSV,
        missing_role_rows,
        ["disease", "source_role", "brca_artifact", "target_table", "missing_reason"],
    )
    write_csv(
        EXCLUDED_FILES_CSV,
        excluded_rows,
        ["disease", "source_disease_cache", "relative_path", "absolute_path", "exclude_reason"],
    )
    write_csv(
        DRY_RUN_REPORT_CSV,
        dry_run_rows,
        [
            "disease",
            "source_disease_cache",
            "source_role",
            "target_table",
            "parser",
            "source_file",
            "source_run_id",
            "file_extension",
            "schema_header",
            "row_count",
            "null_risk",
            "duplicate_risk",
            "rank_numeric_check",
            "score_numeric_check",
            "validation_status",
            "validation_reason",
            "warnings",
            "high_null_columns",
            "created_or_loaded_at",
        ],
    )

    dry_run_pass = True
    if missing_roles:
        dry_run_pass = False
    if any(x["validation_status"] != "passed" for x in dry_run_rows):
        dry_run_pass = False

    write_markdown_plan(
        DOC_PATH,
        disease=disease,
        local_dir=local_dir,
        role_rows=role_mapping_rows,
        matched_roles=matched_roles,
        missing_roles=missing_roles,
        excluded_count=len(excluded_rows),
        dry_run_status="PASS" if dry_run_pass else "FAIL",
        execute_mode=bool(args.execute),
    )

    inserted_total = 0
    if args.execute:
        valid_batches = [b for b in execute_batches if b["rows"]]
        if valid_batches:
            engine = create_engine(build_database_url(), future=True)
            inspector = inspect(engine)
            needed = sorted({b["spec"].table_name for b in valid_batches})
            missing_tables = [name for name in needed if not inspector.has_table(name)]
            if missing_tables:
                raise RuntimeError(f"Missing required target table(s): {', '.join(missing_tables)}")
            metadata = MetaData()
            table_map: dict[str, Table] = {name: Table(name, metadata, autoload_with=engine) for name in needed}
            with engine.begin() as conn:
                for batch in valid_batches:
                    table_name = batch["spec"].table_name
                    table = table_map[table_name]
                    filtered_rows = filter_rows_for_table(table, batch["rows"])
                    delete_for_source(
                        conn=conn,
                        table_name=table_name,
                        disease=disease,
                        run_id=batch["source_run_id"],
                        source_file=str(batch["source_file"]),
                    )
                    inserted_total += insert_rows(conn, table, filtered_rows)

    print(f"BRCA roles used: {len(ROLE_SPECS)}")
    print(f"COAD matched roles: {', '.join(matched_roles) if matched_roles else '(none)'}")
    print(f"COAD missing roles: {', '.join(missing_roles) if missing_roles else '(none)'}")
    print(f"excluded file count: {len(excluded_rows)}")
    print(f"dry-run pass/fail: {'PASS' if dry_run_pass else 'FAIL'}")
    print(f"execute mode true/false: {str(bool(args.execute))}")
    if args.execute:
        print(f"execute inserted rows: {inserted_total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
