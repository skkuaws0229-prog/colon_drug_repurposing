from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Split raw input tables by cohort definition before FE preprocessing. "
            "Outputs cohort-scoped label/sample/drug/LINCS/target tables."
        )
    )
    p.add_argument("--label-uri", required=True)
    p.add_argument("--sample-uri", required=True)
    p.add_argument("--drug-uri", required=True)
    p.add_argument("--lincs-drug-signature-uri", required=True)
    p.add_argument("--drug-target-uri", required=True)
    p.add_argument("--cohort-yaml", default="")
    p.add_argument("--cohort-name", default="")
    p.add_argument(
        "--sample-match-mode",
        choices=["exact", "alnum_norm"],
        default="exact",
        help=(
            "How to match sample cell line IDs against cohort label cell lines. "
            "'exact' keeps strict string match; "
            "'alnum_norm' removes non-alphanumeric chars and uppercases before matching."
        ),
    )
    p.add_argument("--out-dir", required=True)
    p.add_argument("--run-id", required=True)
    return p.parse_args()


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
            "cohort splitting requires PyYAML. Install with `pip install pyyaml`."
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


def _norm_cell(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()


def _alnum_norm_text(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", str(v).upper())


def _alnum_norm_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().map(_alnum_norm_text)


def _norm_did(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\.0+$", "", regex=True)


def _find_col(df: pd.DataFrame, candidates: list[str], table_name: str) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"{table_name} missing id column. expected one of: {candidates}")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_parquet(args.label_uri)
    sample_df = pd.read_parquet(args.sample_uri)
    drug_df = pd.read_parquet(args.drug_uri)
    lincs_df = pd.read_parquet(args.lincs_drug_signature_uri)
    target_df = pd.read_parquet(args.drug_target_uri)

    filtered_label, cohort_qc = filter_label_by_cohort(label_df, args.cohort_yaml, args.cohort_name)

    required_label_cols = ["cell_line_name", "DRUG_ID"]
    missing = [c for c in required_label_cols if c not in filtered_label.columns]
    if missing:
        raise ValueError(f"label input missing required columns for split: {missing}")

    keep_cells = set(_norm_cell(filtered_label["cell_line_name"]).tolist())
    keep_drugs = set(_norm_did(filtered_label["DRUG_ID"]).tolist())

    sample_id_col = _find_col(sample_df, ["cell_line_name", "sample_id"], "sample")
    drug_id_col = _find_col(drug_df, ["DRUG_ID", "canonical_drug_id"], "drug")
    lincs_id_col = _find_col(lincs_df, ["canonical_drug_id", "DRUG_ID"], "lincs_drug_signature")
    target_id_col = _find_col(target_df, ["canonical_drug_id", "DRUG_ID"], "drug_target")

    sample_before = int(sample_df.shape[0])
    drug_before = int(drug_df.shape[0])
    lincs_before = int(lincs_df.shape[0])
    target_before = int(target_df.shape[0])

    sample_cells_series = _norm_cell(sample_df[sample_id_col])
    if args.sample_match_mode == "exact":
        sample_mask = sample_cells_series.isin(keep_cells)
        sample_match_qc = {
            "mode": "exact",
            "cohort_cells_input": int(len(keep_cells)),
            "cohort_cells_matched_exact": int(len(set(sample_cells_series[sample_mask].tolist()))),
            "cohort_cells_matched_final": int(len(set(sample_cells_series[sample_mask].tolist()))),
            "recovered_by_normalization_count": 0,
            "recovered_by_normalization_preview": [],
        }
    else:
        keep_norm = set(_alnum_norm_text(v) for v in keep_cells if _alnum_norm_text(v))
        sample_norm_series = _alnum_norm_series(sample_cells_series)
        sample_mask = sample_norm_series.isin(keep_norm)

        sample_exact_set = set(sample_cells_series.tolist())
        sample_norm_set = set(sample_norm_series.tolist())
        matched_exact_cells = set(v for v in keep_cells if v in sample_exact_set)
        matched_norm_cells = set(v for v in keep_cells if _alnum_norm_text(v) in sample_norm_set)
        recovered = sorted(list(matched_norm_cells - matched_exact_cells))
        sample_match_qc = {
            "mode": "alnum_norm",
            "cohort_cells_input": int(len(keep_cells)),
            "cohort_cells_matched_exact": int(len(matched_exact_cells)),
            "cohort_cells_matched_final": int(len(matched_norm_cells)),
            "recovered_by_normalization_count": int(len(recovered)),
            "recovered_by_normalization_preview": recovered[:50],
        }

    sample_df = sample_df[sample_mask].copy()
    drug_df = drug_df[_norm_did(drug_df[drug_id_col]).isin(keep_drugs)].copy()
    lincs_df = lincs_df[_norm_did(lincs_df[lincs_id_col]).isin(keep_drugs)].copy()
    target_df = target_df[_norm_did(target_df[target_id_col]).isin(keep_drugs)].copy()

    sample_after = int(sample_df.shape[0])
    drug_after = int(drug_df.shape[0])
    lincs_after = int(lincs_df.shape[0])
    target_after = int(target_df.shape[0])

    out_label = out_dir / "label.parquet"
    out_sample = out_dir / "sample.parquet"
    out_drug = out_dir / "drug.parquet"
    out_lincs = out_dir / "lincs_drug_signature.parquet"
    out_target = out_dir / "drug_target.parquet"
    out_manifest = out_dir / "split_manifest.json"

    filtered_label.to_parquet(out_label, index=False)
    sample_df.to_parquet(out_sample, index=False)
    drug_df.to_parquet(out_drug, index=False)
    lincs_df.to_parquet(out_lincs, index=False)
    target_df.to_parquet(out_target, index=False)

    manifest = {
        "run_id": args.run_id,
        "cohort_name": args.cohort_name,
        "cohort_filter": cohort_qc,
        "id_columns": {
            "sample_id_col": sample_id_col,
            "drug_id_col": drug_id_col,
            "lincs_id_col": lincs_id_col,
            "target_id_col": target_id_col,
        },
        "sample_match_qc": sample_match_qc,
        "row_counts": {
            "label_before": int(label_df.shape[0]),
            "label_after": int(filtered_label.shape[0]),
            "sample_before": sample_before,
            "sample_after": sample_after,
            "drug_before": drug_before,
            "drug_after": drug_after,
            "lincs_before": lincs_before,
            "lincs_after": lincs_after,
            "target_before": target_before,
            "target_after": target_after,
        },
        "outputs": {
            "label": str(out_label),
            "sample": str(out_sample),
            "drug": str(out_drug),
            "lincs_drug_signature": str(out_lincs),
            "drug_target": str(out_target),
        },
    }
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
