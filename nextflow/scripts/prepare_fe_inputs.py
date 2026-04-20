from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build bridge input tables for Nextflow FE (sample_features, drug_features, labels)."
    )
    p.add_argument(
        "--label-uri",
        default="s3://drug-discovery-joe-raw-data-team4/results/gdsc/21_ic50.parquet",
        help="GDSC IC50 parquet URI.",
    )
    p.add_argument(
        "--drug-uri",
        default="s3://drug-discovery-joe-raw-data-team4/results/features_glue/feature/model_input/elasticnet/elasticnet_drug_dataset.parquet",
        help="Drug-level feature table URI with canonical_smiles (recommended: elasticnet_drug_dataset).",
    )
    p.add_argument(
        "--sample-uri",
        default="s3://drug-discovery-joe-raw-data-team4/results/depmap/57_crispr.parquet",
        help="Sample-level source parquet URI (DepMap CRISPR).",
    )
    p.add_argument(
        "--output-prefix",
        required=True,
        help="Output directory/prefix (local path or s3://...). Example: s3://.../results/features_nextflow_team4/input/20260330_v1",
    )
    p.add_argument("--run-id", required=True)
    p.add_argument(
        "--binary-quantile",
        type=float,
        default=0.3,
        help="If binary_label is absent, generate with ic50 <= quantile as 1.",
    )
    p.add_argument(
        "--cohort-yaml",
        default="",
        help="Optional YAML file that defines cohort filters.",
    )
    p.add_argument(
        "--cohort-name",
        default="",
        help="Optional cohort key in cohort-yaml (e.g., colon, rectal).",
    )
    return p.parse_args()


def _read_parquet(uri: str) -> pd.DataFrame:
    return pd.read_parquet(uri)


def _safe_mkdir(output_prefix: str) -> None:
    if output_prefix.startswith("s3://"):
        return
    Path(output_prefix).mkdir(parents=True, exist_ok=True)


def _write_json(obj: dict[str, Any], path: str) -> None:
    content = json.dumps(obj, ensure_ascii=False, indent=2)
    if path.startswith("s3://"):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        subprocess.run(["aws", "s3", "cp", tmp_path, path], check=True)
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _join_path(prefix: str, name: str) -> str:
    return prefix.rstrip("/") + "/" + name


def _clean_opt_str(value: str | None) -> str:
    return str(value or "").strip()


def _value_match_mask(series: pd.Series, values: list[str], match: str) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    vals = [str(v).strip().lower() for v in values if str(v).strip()]
    if not vals:
        raise ValueError("filter rule 'values' must contain at least one non-empty string.")

    if match == "exact":
        return s.isin(vals)
    if match == "contains":
        pattern = "|".join(re.escape(v) for v in vals)
        return s.str.contains(pattern, na=False, regex=True)
    raise ValueError(f"unsupported match type '{match}' (allowed: exact, contains)")


def _load_cohort_spec(yaml_path: str, cohort_name: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "cohort filtering requires PyYAML. Install with `pip install pyyaml` "
            "or run without --cohort-yaml/--cohort-name."
        ) from e

    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cohorts = cfg.get("cohorts")
    if not isinstance(cohorts, dict):
        raise ValueError("cohort yaml must contain top-level 'cohorts' mapping.")
    if cohort_name not in cohorts:
        raise ValueError(f"cohort '{cohort_name}' not found in {yaml_path}. available={sorted(cohorts.keys())}")

    spec = cohorts[cohort_name] or {}
    mode = str(spec.get("mode", "any")).strip().lower()
    if mode not in {"any", "all"}:
        raise ValueError(f"cohort '{cohort_name}' has invalid mode '{mode}'. allowed: any, all")

    rules = spec.get("rules")
    if not isinstance(rules, list) or len(rules) == 0:
        raise ValueError(f"cohort '{cohort_name}' must define non-empty 'rules'.")

    return {"name": cohort_name, "mode": mode, "rules": rules}


def filter_label_by_cohort(
    label_df: pd.DataFrame,
    cohort_yaml: str,
    cohort_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    yaml_path = _clean_opt_str(cohort_yaml)
    name = _clean_opt_str(cohort_name)

    if not yaml_path and not name:
        return label_df, {"enabled": False}
    if bool(yaml_path) != bool(name):
        raise ValueError("cohort filtering requires both --cohort-yaml and --cohort-name together.")

    spec = _load_cohort_spec(yaml_path, name)
    mode = spec["mode"]
    row_mask = pd.Series(True if mode == "all" else False, index=label_df.index)
    rule_reports: list[dict[str, Any]] = []

    for idx, rule in enumerate(spec["rules"], start=1):
        if not isinstance(rule, dict):
            raise ValueError(f"cohort rule #{idx} must be a mapping object.")

        columns = rule.get("columns")
        if columns is None and "column" in rule:
            columns = [rule["column"]]
        if not isinstance(columns, list) or len(columns) == 0:
            raise ValueError(f"cohort rule #{idx} must define 'columns' list (or 'column').")

        candidate_cols = [str(c).strip() for c in columns if str(c).strip()]
        existing_cols = [c for c in candidate_cols if c in label_df.columns]
        if not existing_cols:
            raise ValueError(
                f"cohort rule #{idx} columns not found. requested={candidate_cols}; "
                f"available={list(label_df.columns)}"
            )

        values = rule.get("values")
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError(f"cohort rule #{idx} must define non-empty 'values' list.")

        match = str(rule.get("match", "exact")).strip().lower()
        negate = bool(rule.get("negate", False))

        rule_mask = pd.Series(False, index=label_df.index)
        for col in existing_cols:
            col_mask = _value_match_mask(label_df[col], values, match)
            rule_mask = rule_mask | col_mask

        if negate:
            rule_mask = ~rule_mask

        if mode == "all":
            row_mask = row_mask & rule_mask
        else:
            row_mask = row_mask | rule_mask

        rule_reports.append(
            {
                "rule_index": idx,
                "columns_used": existing_cols,
                "match": match,
                "negate": negate,
                "matched_rows": int(rule_mask.sum()),
            }
        )

    filtered = label_df.loc[row_mask].copy()
    if filtered.empty:
        raise ValueError(
            f"cohort filtering produced 0 rows for cohort='{name}'. "
            "Please adjust YAML rules/columns."
        )

    qc = {
        "enabled": True,
        "cohort_yaml": yaml_path,
        "cohort_name": name,
        "mode": mode,
        "rows_before": int(label_df.shape[0]),
        "rows_after": int(filtered.shape[0]),
        "retention_rate": float(filtered.shape[0] / max(label_df.shape[0], 1)),
        "rule_reports": rule_reports,
    }
    return filtered, qc


def build_labels(label_df: pd.DataFrame, q: float) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    required = ["cell_line_name", "DRUG_ID", "ln_IC50"]
    missing = [c for c in required if c not in label_df.columns]
    if missing:
        raise ValueError(f"label source missing required columns: {missing}")

    mapping_table = label_df[["cell_line_name", "DRUG_ID"]].copy()
    mapping_table = mapping_table.rename(
        columns={"cell_line_name": "sample_id_raw", "DRUG_ID": "canonical_drug_id_raw"}
    )
    mapping_table["sample_id"] = mapping_table["sample_id_raw"].astype(str).str.strip()
    mapping_table["canonical_drug_id"] = mapping_table["canonical_drug_id_raw"].astype(str).str.strip()
    mapping_table["mapping_rule"] = "sample_id=cell_line_name;canonical_drug_id=DRUG_ID"

    labels = label_df.copy()
    labels = labels.rename(
        columns={
            "cell_line_name": "sample_id",
            "DRUG_ID": "canonical_drug_id",
            "ln_IC50": "ic50",
            "label": "binary_label",
        }
    )
    labels["sample_id"] = labels["sample_id"].astype(str).str.strip()
    labels["canonical_drug_id"] = labels["canonical_drug_id"].astype(str).str.strip()
    labels["ic50"] = pd.to_numeric(labels["ic50"], errors="coerce")

    has_binary = "binary_label" in labels.columns
    if not has_binary:
        labels["binary_label"] = pd.NA

    # Duplicate (sample,drug) pairs are aggregated to median to get deterministic labels.
    pair_before = int(labels.shape[0])
    labels = (
        labels.groupby(["sample_id", "canonical_drug_id"], as_index=False)
        .agg({"ic50": "median", "binary_label": "max"})
        .reset_index(drop=True)
    )
    pair_after = int(labels.shape[0])

    if not has_binary:
        thr = float(labels["ic50"].quantile(q))
        labels["binary_label"] = (labels["ic50"] <= thr).astype(int)
    else:
        labels["binary_label"] = labels["binary_label"].fillna((labels["ic50"] <= labels["ic50"].quantile(q)).astype(int))
        labels["binary_label"] = labels["binary_label"].astype(int)

    qc = {
        "labels_pair_rows_before_groupby": pair_before,
        "labels_pair_rows_after_groupby": pair_after,
        "labels_unique_samples": int(labels["sample_id"].nunique()),
        "labels_unique_drugs": int(labels["canonical_drug_id"].nunique()),
        "labels_ic50_missing_rows": int(labels["ic50"].isna().sum()),
    }
    return labels, mapping_table, qc


def _norm_name(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "", regex=True)
        .str.strip()
    )


def _normalize_smiles_col(s: pd.Series) -> pd.Series:
    out = s.astype(str).str.strip()
    out = out.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "none": pd.NA,
            "None": pd.NA,
            "<NA>": pd.NA,
        }
    )
    return out


def _coerce_drug_id(series: pd.Series) -> pd.Series:
    num = pd.to_numeric(series, errors="coerce")
    out = pd.Series(pd.NA, index=series.index, dtype="object")

    has_num = num.notna()
    if has_num.any():
        out.loc[has_num] = num.loc[has_num].astype(np.int64).astype(str)

    no_num = ~has_num
    if no_num.any():
        out.loc[no_num] = series.loc[no_num].astype(str).str.strip()

    out = out.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return out


def _first_non_null(s: pd.Series) -> Any:
    non_null = s.dropna()
    if len(non_null) > 0:
        return non_null.iloc[0]
    return pd.NA


def _collapse_lookup(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    if key_col not in df.columns:
        raise ValueError(f"key column '{key_col}' not found")
    if "smiles" not in df.columns or "canonical_smiles_raw" not in df.columns:
        raise ValueError("lookup df must include smiles and canonical_smiles_raw")

    tmp = df.copy()
    tmp["_has_smiles"] = (~tmp["smiles"].isna()).astype(int)
    tmp = tmp.sort_values([key_col, "_has_smiles"], ascending=[True, False])
    out = (
        tmp.groupby(key_col, as_index=False)
        .agg(
            smiles=("smiles", _first_non_null),
            canonical_smiles_raw=("canonical_smiles_raw", _first_non_null),
        )
        .reset_index(drop=True)
    )
    return out


def filter_sample_by_labels(sample_df: pd.DataFrame, label_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if "cell_line_name" not in sample_df.columns:
        raise ValueError("sample source missing required column: cell_line_name")
    if "cell_line_name" not in label_df.columns:
        raise ValueError("label source missing required column: cell_line_name")

    before_rows = int(sample_df.shape[0])
    before_unique = int(sample_df["cell_line_name"].astype(str).str.strip().nunique())

    keep = set(label_df["cell_line_name"].astype(str).str.strip().tolist())
    filtered = sample_df[sample_df["cell_line_name"].astype(str).str.strip().isin(keep)].copy()

    after_rows = int(filtered.shape[0])
    after_unique = int(filtered["cell_line_name"].astype(str).str.strip().nunique())

    qc = {
        "enabled": True,
        "rule": "sample.cell_line_name in filtered_label.cell_line_name",
        "rows_before": before_rows,
        "rows_after": after_rows,
        "unique_cell_lines_before": before_unique,
        "unique_cell_lines_after": after_unique,
        "retention_rate_rows": float(after_rows / max(before_rows, 1)),
    }
    return filtered, qc


def build_sample_features(sample_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["cell_line_name", "gene_name", "dependency"]
    missing = [c for c in required if c not in sample_df.columns]
    if missing:
        raise ValueError(f"sample source missing required columns: {missing}")

    wide = sample_df.pivot_table(
        index="cell_line_name",
        columns="gene_name",
        values="dependency",
        aggfunc="mean",
    )
    wide.columns = [f"crispr__{str(c)}" for c in wide.columns]
    wide = wide.reset_index().rename(columns={"cell_line_name": "sample_id"})
    wide["sample_id"] = wide["sample_id"].astype(str).str.strip()
    wide = wide.fillna(wide.median(numeric_only=True))

    qc = {
        "sample_features_rows": int(wide.shape[0]),
        "sample_features_cols": int(wide.shape[1]),
    }
    return wide, qc


def build_drug_features(drug_df: pd.DataFrame, label_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["canonical_smiles"]
    missing = [c for c in required if c not in drug_df.columns]
    if missing:
        raise ValueError(f"drug source missing required columns: {missing}")

    if "DRUG_ID" not in label_df.columns or "drug_name" not in label_df.columns:
        raise ValueError("label source must include DRUG_ID and drug_name for drug mapping.")

    label_drug = label_df[["DRUG_ID", "drug_name"]].dropna(subset=["DRUG_ID"]).copy()
    label_drug["canonical_drug_id"] = _coerce_drug_id(label_drug["DRUG_ID"])
    label_drug["drug_name_norm"] = _norm_name(label_drug["drug_name"])
    label_drug = label_drug.drop_duplicates(subset=["canonical_drug_id", "drug_name_norm"])

    src = drug_df.copy()
    src["canonical_smiles_raw"] = src["canonical_smiles"]
    src["smiles"] = _normalize_smiles_col(src["canonical_smiles"])

    if "drug_name_norm" in src.columns:
        src["drug_name_norm"] = _norm_name(src["drug_name_norm"])
    elif "drug_name" in src.columns:
        src["drug_name_norm"] = _norm_name(src["drug_name"])
    elif "DRUG_NAME" in src.columns:
        src["drug_name_norm"] = _norm_name(src["DRUG_NAME"])
    else:
        src["drug_name_norm"] = pd.NA

    id_col = ""
    for cand in ["DRUG_ID", "drug_id", "canonical_drug_id", "canonical_drug_id_raw"]:
        if cand in src.columns:
            id_col = cand
            break
    if id_col:
        src["canonical_drug_id"] = _coerce_drug_id(src[id_col])
    else:
        src["canonical_drug_id"] = pd.NA

    id_lookup = pd.DataFrame(columns=["canonical_drug_id", "smiles", "canonical_smiles_raw"])
    if id_col:
        id_lookup = _collapse_lookup(
            src[["canonical_drug_id", "smiles", "canonical_smiles_raw"]].dropna(subset=["canonical_drug_id"]),
            key_col="canonical_drug_id",
        )
        id_lookup = id_lookup.rename(
            columns={
                "smiles": "id_smiles",
                "canonical_smiles_raw": "id_canonical_smiles_raw",
            }
        )

    name_lookup = pd.DataFrame(columns=["drug_name_norm", "smiles", "canonical_smiles_raw"])
    if "drug_name_norm" in src.columns:
        name_lookup = _collapse_lookup(
            src[["drug_name_norm", "smiles", "canonical_smiles_raw"]].dropna(subset=["drug_name_norm"]),
            key_col="drug_name_norm",
        )
        name_lookup = name_lookup.rename(
            columns={
                "smiles": "nm_smiles",
                "canonical_smiles_raw": "nm_canonical_smiles_raw",
            }
        )

    merged = label_drug.copy()
    if not id_lookup.empty:
        merged = merged.merge(id_lookup, on="canonical_drug_id", how="left")
    else:
        merged["id_smiles"] = pd.NA
        merged["id_canonical_smiles_raw"] = pd.NA

    if not name_lookup.empty:
        merged = merged.merge(name_lookup, on="drug_name_norm", how="left")
    else:
        merged["nm_smiles"] = pd.NA
        merged["nm_canonical_smiles_raw"] = pd.NA

    merged["smiles"] = merged["id_smiles"].combine_first(merged["nm_smiles"])
    merged["canonical_smiles_raw"] = merged["id_canonical_smiles_raw"].combine_first(merged["nm_canonical_smiles_raw"])
    merged["smiles_source"] = np.where(
        merged["id_smiles"].notna(),
        "drug_id",
        np.where(merged["nm_smiles"].notna(), "drug_name_norm", "unmatched"),
    )

    grouped = (
        merged.groupby("canonical_drug_id", as_index=False)
        .agg(
            smiles=("smiles", _first_non_null),
            canonical_smiles_raw=("canonical_smiles_raw", _first_non_null),
            drug_name_norm=("drug_name_norm", "first"),
            smiles_source=("smiles_source", _first_non_null),
        )
        .reset_index(drop=True)
    )
    grouped["has_smiles"] = (~grouped["smiles"].isna()).astype(int)

    matched_by_id_count = int((grouped["smiles_source"] == "drug_id").sum())
    backfilled_by_name_count = int((grouped["smiles_source"] == "drug_name_norm").sum())
    unresolved_after_backfill = int((grouped["smiles_source"] == "unmatched").sum())

    qc = {
        "drug_features_rows": int(grouped.shape[0]),
        "drug_features_cols": int(grouped.shape[1]),
        "missing_smiles_rows": int(grouped["smiles"].isna().sum()),
        "missing_smiles_rate": float(grouped["smiles"].isna().mean()),
        "smiles_matched_by_drug_id": matched_by_id_count,
        "smiles_backfilled_by_name": backfilled_by_name_count,
        "smiles_unresolved_after_backfill": unresolved_after_backfill,
        "smiles_backfill_policy": "drug_id exact first, then normalized drug_name fallback",
    }
    return grouped, qc


def main() -> None:
    args = parse_args()
    _safe_mkdir(args.output_prefix)

    label_src = _read_parquet(args.label_uri)
    sample_src = _read_parquet(args.sample_uri)
    drug_src = _read_parquet(args.drug_uri)

    filtered_label_src, cohort_qc = filter_label_by_cohort(
        label_df=label_src,
        cohort_yaml=args.cohort_yaml,
        cohort_name=args.cohort_name,
    )

    labels, mapping_table, labels_qc = build_labels(filtered_label_src, args.binary_quantile)
    filtered_sample_src, sample_filter_qc = filter_sample_by_labels(sample_src, filtered_label_src)
    sample_features, sample_qc = build_sample_features(filtered_sample_src)
    drug_features, drug_qc = build_drug_features(drug_src, filtered_label_src)

    labels_key = labels[["sample_id", "canonical_drug_id"]].drop_duplicates()
    sample_key = sample_features[["sample_id"]].drop_duplicates()
    drug_key = drug_features[["canonical_drug_id"]].drop_duplicates()

    label_with_sample = labels_key.merge(sample_key, on="sample_id", how="left", indicator=True)
    label_with_drug = labels_key.merge(drug_key, on="canonical_drug_id", how="left", indicator=True)

    unmatched_samples = int((label_with_sample["_merge"] == "left_only").sum())
    unmatched_drugs = int((label_with_drug["_merge"] == "left_only").sum())
    join_rate_samples = float(1.0 - unmatched_samples / max(len(labels_key), 1))
    join_rate_drugs = float(1.0 - unmatched_drugs / max(len(labels_key), 1))

    out_sample = _join_path(args.output_prefix, "sample_features.parquet")
    out_drug = _join_path(args.output_prefix, "drug_features.parquet")
    out_labels = _join_path(args.output_prefix, "labels.parquet")
    out_mapping = _join_path(args.output_prefix, "mapping_table.parquet")
    out_qc = _join_path(args.output_prefix, "join_qc_report.json")
    out_manifest = _join_path(args.output_prefix, "bridge_manifest.json")

    sample_features.to_parquet(out_sample, index=False)
    drug_features.to_parquet(out_drug, index=False)
    labels.to_parquet(out_labels, index=False)
    mapping_table.to_parquet(out_mapping, index=False)

    qc_report = {
        "run_id": args.run_id,
        "input_uris": {
            "label_uri": args.label_uri,
            "sample_uri": args.sample_uri,
            "drug_uri": args.drug_uri,
        },
        "cohort_filter": cohort_qc,
        "sample_filter": sample_filter_qc,
        "label_to_feature_join_qc": {
            "label_pair_rows": int(labels_key.shape[0]),
            "unmatched_samples": unmatched_samples,
            "unmatched_drugs": unmatched_drugs,
            "join_rate_samples": join_rate_samples,
            "join_rate_drugs": join_rate_drugs,
        },
        "labels_qc": labels_qc,
        "sample_qc": sample_qc,
        "drug_qc": drug_qc,
    }
    _write_json(qc_report, out_qc)

    manifest = {
        "run_id": args.run_id,
        "purpose": "bridge preprocessing for Nextflow FE input contract",
        "output_files": {
            "sample_features": out_sample,
            "drug_features": out_drug,
            "labels": out_labels,
            "mapping_table": out_mapping,
            "join_qc_report": out_qc,
        },
        "notes": {
            "labels_mapping": "cell_line_name->sample_id, DRUG_ID->canonical_drug_id, ln_IC50->ic50",
            "smiles_policy": "smiles is included; has_smiles indicates availability for downstream ADMET/descriptor steps",
            "cohort_filtering": "optional; set --cohort-yaml + --cohort-name to split cohorts",
        },
    }
    _write_json(manifest, out_manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
