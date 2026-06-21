#!/usr/bin/env python3
"""
Step 6 (CRC): External validation with TCGA cohort + optional GSE39582 metadata summary.
Input : Top 30 drugs from Step 5 ensemble
Output: Top 15 validated drugs for Step 7
"""
import warnings
warnings.filterwarnings("ignore")

import gzip
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
DRUG_ANN = f"{S3_BASE}/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"

ENSEMBLE_DIR = Path(__file__).parent / "ensemble_results"
TOP30_PATH = ENSEMBLE_DIR / "top30_drugs.csv"
ENSEMBLE_JSON = ENSEMBLE_DIR / "ensemble_results.json"
OUTPUT_DIR = Path(__file__).parent / "crc_external_results"
OUTPUT_DIR.mkdir(exist_ok=True)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "runs" / "20260420_crc_split_v2" / "external_validation_raw"
TCGA_EXPR_PATH = DEFAULT_RAW / "tcga_coadread_data_mrna_seq_v2_rsem.txt"
TCGA_CLIN_PAT_PATH = DEFAULT_RAW / "tcga_coadread_data_clinical_patient.txt"
TCGA_CLIN_SMP_PATH = DEFAULT_RAW / "tcga_coadread_data_clinical_sample.txt"
GSE39582_MATRIX_GZ = DEFAULT_RAW / "GSE39582_series_matrix.txt.gz"
# Cohort knobs (overridden by orchestrator).
TCGA_ONCOTREE_CODE = "COAD"   # e.g., COAD or READ
TCGA_FALLBACK_SITE = "Colon"  # e.g., Colon or Rectum/Rectal
TCGA_LABEL = "COAD"           # display label
INCLUDE_GSE39582 = True

KNOWN_CRC_DRUGS = {
    "Fluorouracil", "Capecitabine", "Irinotecan", "SN-38", "Oxaliplatin",
    "Cetuximab", "Panitumumab", "Bevacizumab", "Regorafenib",
    "Trifluridine", "Topotecan", "Camptothecin",
}

CRC_PATHWAYS = {
    "ERK MAPK signaling", "PI3K/MTOR signaling", "Cell cycle",
    "Apoptosis regulation", "DNA replication", "Genome integrity",
    "WNT signaling", "RTK signaling",
}


def _read_cbio(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, sep="\t", comment="#", low_memory=False)


def load_data():
    print("Loading Step5 outputs + external cohorts...")
    t0 = time.time()
    top30 = pd.read_csv(TOP30_PATH)
    drug_ann = pd.read_parquet(DRUG_ANN)
    with open(ENSEMBLE_JSON, encoding="utf-8") as f:
        ens_results = json.load(f)

    expr = pd.read_csv(TCGA_EXPR_PATH, sep="\t", low_memory=False)
    clin_pat = _read_cbio(TCGA_CLIN_PAT_PATH)
    clin_smp = _read_cbio(TCGA_CLIN_SMP_PATH)

    # Cohort filter (COAD / READ)
    if "ONCOTREE_CODE" in clin_smp.columns:
        smp_cohort = clin_smp[
            clin_smp["ONCOTREE_CODE"].astype(str).str.upper() == str(TCGA_ONCOTREE_CODE).upper()
        ].copy()
    else:
        smp_cohort = clin_smp[
            clin_smp["CANCER_TYPE_DETAILED"].astype(str).str.contains(
                str(TCGA_FALLBACK_SITE), case=False, na=False
            )
        ].copy()

    # Hard guard: CRC split step6 must use the requested cohort only.
    if smp_cohort.empty:
        raise ValueError(
            f"No samples found for TCGA cohort filter: {TCGA_ONCOTREE_CODE} / fallback={TCGA_FALLBACK_SITE}"
        )
    if "ONCOTREE_CODE" in smp_cohort.columns:
        codes = set(smp_cohort["ONCOTREE_CODE"].astype(str).str.upper().unique().tolist())
        expected = str(TCGA_ONCOTREE_CODE).upper()
        if expected not in codes:
            raise ValueError(f"Cohort mismatch: expected {expected}, got {sorted(codes)}")

    sample_cols = [c for c in smp_cohort["SAMPLE_ID"].astype(str).tolist() if c in expr.columns]
    if not sample_cols:
        raise ValueError(f"No expression columns matched selected TCGA cohort: {TCGA_ONCOTREE_CODE}")
    expr = expr[["Hugo_Symbol"] + sample_cols].copy()
    sample_to_patient = {
        str(s): str(p) for s, p in zip(smp_cohort["SAMPLE_ID"], smp_cohort["PATIENT_ID"])
        if pd.notna(s) and pd.notna(p)
    }
    patient_ids = set(sample_to_patient.values())
    clin_pat = clin_pat[clin_pat["PATIENT_ID"].astype(str).isin(patient_ids)].copy()
    clin_pat["PATIENT_ID"] = clin_pat["PATIENT_ID"].astype(str)
    clin_pat["os_months"] = pd.to_numeric(clin_pat.get("OS_MONTHS"), errors="coerce")
    clin_pat["os_event"] = clin_pat.get("OS_STATUS", "").astype(str).str.contains("DECEASED|1:", case=False, na=False).astype(int)
    clin_pat = clin_pat.dropna(subset=["os_months"])

    print(f"  Top30 drugs: {len(top30)}")
    print(f"  TCGA-{TCGA_LABEL} expression: {expr.shape[0]} genes x {len(sample_cols)} samples")
    print(f"  TCGA-{TCGA_LABEL} clinical: {len(clin_pat)} patients")
    print(f"  Loaded in {time.time()-t0:.1f}s")
    return top30, drug_ann, ens_results, expr, clin_pat, sample_cols, sample_to_patient


def method_a_tcga_expression(expr, sample_cols, top30, drug_ann):
    print("\n" + "=" * 60)
    print(f"  Method A (TCGA-{TCGA_LABEL}): Target Expression Validation")
    print("=" * 60)

    genes = expr["Hugo_Symbol"].astype(str).str.upper().fillna("")
    expr_num = expr[sample_cols].apply(pd.to_numeric, errors="coerce")
    global_median = np.nanmedian(expr_num.to_numpy(dtype=float))

    rows = []
    for _, r in top30.iterrows():
        drug_id = int(r["drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]
        if ann.empty:
            rows.append({
                "drug_id": drug_id, "drug_name": f"Drug_{drug_id}",
                "target": "N/A", "pathway": "N/A", "target_expressed": False,
                "pct_patients_expressing": 0.0, "expr_rank_pct": 0.0,
                "crc_pathway_relevant": False,
            })
            continue

        ann = ann.iloc[0]
        drug_name = str(ann.get("DRUG_NAME", f"Drug_{drug_id}"))
        target = str(ann.get("PUTATIVE_TARGET_NORMALIZED", "N/A"))
        pathway = str(ann.get("PATHWAY_NAME_NORMALIZED", "N/A"))
        target_genes = [t.strip().upper() for t in target.split(",") if t.strip()]

        mask = genes.isin(target_genes)
        if mask.any():
            target_expr = expr_num.loc[mask]
            mean_target = np.nanmean(target_expr.to_numpy(dtype=float))
            pct_expr = np.nanmean(target_expr.to_numpy(dtype=float) > global_median)
            gene_means = np.nanmean(expr_num.to_numpy(dtype=float), axis=1)
            expr_rank_pct = float(np.nanmean(gene_means < mean_target) * 100.0)
            target_expressed = bool(pct_expr > 0.30)
        else:
            pct_expr = 0.0
            expr_rank_pct = 50.0
            target_expressed = True

        rows.append({
            "drug_id": drug_id,
            "drug_name": drug_name,
            "target": target,
            "pathway": pathway,
            "target_expressed": target_expressed,
            "pct_patients_expressing": float(pct_expr),
            "expr_rank_pct": float(expr_rank_pct),
            "crc_pathway_relevant": pathway in CRC_PATHWAYS,
        })

    df = pd.DataFrame(rows)
    print(f"  Summary: expressed={int(df['target_expressed'].sum())}/{len(df)}, "
          f"CRC-pathway={int(df['crc_pathway_relevant'].sum())}/{len(df)}")
    return df


def method_b_tcga_survival(expr, sample_cols, sample_to_patient, clin_pat, top30, drug_ann):
    print("\n" + "=" * 60)
    print(f"  Method B (TCGA-{TCGA_LABEL}): Survival Stratification")
    print("=" * 60)

    genes = expr["Hugo_Symbol"].astype(str).str.upper().fillna("")
    expr_num = expr[sample_cols].apply(pd.to_numeric, errors="coerce")

    rows = []
    for _, r in top30.iterrows():
        drug_id = int(r["drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]
        if ann.empty:
            rows.append({
                "drug_id": drug_id, "drug_name": f"Drug_{drug_id}",
                "survival_significant": False, "log_rank_p": 1.0,
                "median_os_high": 0.0, "median_os_low": 0.0,
                "hr_direction": "unknown",
            })
            continue

        ann = ann.iloc[0]
        drug_name = str(ann.get("DRUG_NAME", f"Drug_{drug_id}"))
        target = str(ann.get("PUTATIVE_TARGET_NORMALIZED", "N/A"))
        target_genes = [t.strip().upper() for t in target.split(",") if t.strip()]
        mask = genes.isin(target_genes)

        if not mask.any():
            rows.append({
                "drug_id": drug_id, "drug_name": drug_name,
                "survival_significant": False, "log_rank_p": 1.0,
                "median_os_high": 0.0, "median_os_low": 0.0,
                "hr_direction": "pathway-level",
            })
            continue

        target_by_sample = expr_num.loc[mask].mean(axis=0)
        patient_vals = {}
        for s, v in target_by_sample.items():
            pid = sample_to_patient.get(str(s))
            if pid is None or pd.isna(v):
                continue
            patient_vals.setdefault(pid, []).append(float(v))

        patient_expr = pd.Series({k: float(np.nanmean(v)) for k, v in patient_vals.items()}, name="target_expr")
        merged = clin_pat[["PATIENT_ID", "os_months", "os_event"]].merge(
            patient_expr.rename_axis("PATIENT_ID").reset_index(),
            on="PATIENT_ID", how="inner"
        ).dropna(subset=["os_months", "target_expr"])

        if len(merged) < 30:
            rows.append({
                "drug_id": drug_id, "drug_name": drug_name,
                "survival_significant": False, "log_rank_p": 1.0,
                "median_os_high": 0.0, "median_os_low": 0.0,
                "hr_direction": "insufficient",
            })
            continue

        med = float(np.nanmedian(merged["target_expr"]))
        high = merged[merged["target_expr"] >= med]["os_months"].to_numpy(dtype=float)
        low = merged[merged["target_expr"] < med]["os_months"].to_numpy(dtype=float)
        if len(high) > 10 and len(low) > 10:
            _, p = mannwhitneyu(high, low, alternative="two-sided")
            mh, ml = float(np.median(high)), float(np.median(low))
            sig = bool(p < 0.05)
            direction = "protective" if mh > ml else "risk"
        else:
            p, mh, ml, sig, direction = 1.0, 0.0, 0.0, False, "insufficient"

        rows.append({
            "drug_id": drug_id,
            "drug_name": drug_name,
            "survival_significant": sig,
            "log_rank_p": float(p),
            "median_os_high": float(mh),
            "median_os_low": float(ml),
            "hr_direction": direction,
        })

    df = pd.DataFrame(rows)
    print(f"  Summary: significant={int(df['survival_significant'].sum())}/{len(df)}")
    return df


def method_c_precision(top30, drug_ann):
    print("\n" + "=" * 60)
    print("  Method C: Known CRC Drug Precision (P@K)")
    print("=" * 60)
    names = []
    for _, r in top30.iterrows():
        drug_id = int(r["drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]
        name = str(ann.iloc[0]["DRUG_NAME"]) if not ann.empty else f"Drug_{drug_id}"
        names.append(name)

    p_at_k = {}
    for k in [5, 10, 15, 20, 30]:
        hit = sum(1 for x in names[:k] if x in KNOWN_CRC_DRUGS)
        p_at_k[f"P@{k}"] = {"precision": hit / k, "hits": hit, "total": k}
        print(f"  P@{k}: {hit}/{k} = {hit/k:.2%}")
    return p_at_k


def summarize_gse39582():
    print("\n" + "=" * 60)
    print("  Method D: GSE39582 Metadata Summary")
    print("=" * 60)
    out = {
        "dataset": "GSE39582",
        "file": str(GSE39582_MATRIX_GZ),
        "n_samples_from_title": 0,
        "n_geo_accessions": 0,
        "characteristics_rows": 0,
        "survival_keyword_hits": 0,
        "detected_characteristic_keys": [],
    }
    if not INCLUDE_GSE39582:
        print("  GSE39582 summary disabled for this cohort.")
        out["disabled"] = True
        return out

    if not GSE39582_MATRIX_GZ.exists():
        print("  GSE39582 file missing; summary skipped.")
        return out

    key_set = set()
    with gzip.open(GSE39582_MATRIX_GZ, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("!series_matrix_table_begin"):
                break
            if line.startswith("!Sample_title"):
                out["n_samples_from_title"] = max(0, len(line.rstrip("\n").split("\t")) - 1)
            elif line.startswith("!Sample_geo_accession"):
                out["n_geo_accessions"] = max(0, len(line.rstrip("\n").split("\t")) - 1)
            elif line.startswith("!Sample_characteristics_ch1"):
                out["characteristics_rows"] += 1
                vals = line.rstrip("\n").split("\t")[1:]
                for v in vals:
                    vv = v.strip().strip('"')
                    m = re.match(r"^\s*([^:]{1,80})\s*:\s*(.+)\s*$", vv)
                    if m:
                        key_set.add(m.group(1).strip().lower())
                    if re.search(r"survival|relapse|recurrence|death|status|event", vv, flags=re.I):
                        out["survival_keyword_hits"] += 1

    out["detected_characteristic_keys"] = sorted(key_set)[:25]
    print(f"  Samples: {out['n_samples_from_title']} (titles), {out['n_geo_accessions']} (GSM)")
    print(f"  Characteristic rows: {out['characteristics_rows']}, "
          f"survival-like hits: {out['survival_keyword_hits']}")
    return out


def select_top15(top30, df_a, df_b, drug_ann):
    s = top30[["drug_id", "mean_pred_ic50", "mean_true_ic50", "sensitivity_rate", "n_samples"]].copy()
    a = df_a.set_index("drug_id")
    b = df_b.set_index("drug_id")

    s["drug_name"] = s["drug_id"].map(lambda x: a.loc[x, "drug_name"] if x in a.index else f"Drug_{x}")
    s["target"] = s["drug_id"].map(lambda x: a.loc[x, "target"] if x in a.index else "N/A")
    s["pathway"] = s["drug_id"].map(lambda x: a.loc[x, "pathway"] if x in a.index else "N/A")
    s["target_expressed"] = s["drug_id"].map(lambda x: bool(a.loc[x, "target_expressed"]) if x in a.index else False).astype(int)
    s["crc_pathway"] = s["drug_id"].map(lambda x: bool(a.loc[x, "crc_pathway_relevant"]) if x in a.index else False).astype(int)
    s["survival_sig"] = s["drug_id"].map(lambda x: bool(b.loc[x, "survival_significant"]) if x in b.index else False).astype(int)
    s["known_crc"] = s["drug_name"].isin(KNOWN_CRC_DRUGS).astype(int)

    s["validation_score"] = (
        s["target_expressed"] * 2.0
        + s["crc_pathway"] * 1.5
        + s["survival_sig"] * 2.5
        + s["known_crc"] * 2.0
        + (s["sensitivity_rate"] >= 0.9).astype(float) * 1.5
        - s["mean_pred_ic50"].rank(ascending=True) * 0.05
    )
    top15 = s.nlargest(15, "validation_score").sort_values("mean_pred_ic50", ascending=True).copy()
    top15["final_rank"] = np.arange(1, len(top15) + 1)
    return top15, s


def save_results(df_a, df_b, p_at_k, gse_summary, top15, all_scores, ens_results):
    out_json = OUTPUT_DIR / "step6_crc_external_results.json"
    desc = f"CRC External Validation (TCGA-{TCGA_LABEL})"
    if INCLUDE_GSE39582:
        desc += " + GSE39582"
    summary = {
        "step": 6,
        "description": desc,
        "method_a_tcga_expression": {
            "n_targets_expressed": int(df_a["target_expressed"].sum()),
            "n_crc_pathway": int(df_a["crc_pathway_relevant"].sum()),
            "n_total": int(len(df_a)),
            "details": df_a.to_dict(orient="records"),
        },
        "method_b_tcga_survival": {
            "n_significant": int(df_b["survival_significant"].sum()),
            "n_total": int(len(df_b)),
            "details": df_b.to_dict(orient="records"),
        },
        "method_c_known_crc_precision": p_at_k,
        "method_d_gse39582_metadata": gse_summary,
        "ensemble_metrics": ens_results.get("ensemble_metrics", {}),
        "top15_validated": top15[[
            "final_rank", "drug_id", "drug_name", "target", "pathway",
            "mean_pred_ic50", "mean_true_ic50", "sensitivity_rate",
            "target_expressed", "survival_sig", "known_crc", "validation_score"
        ]].to_dict(orient="records"),
        "all_30_scores": all_scores[[
            "drug_id", "drug_name", "target", "pathway",
            "mean_pred_ic50", "sensitivity_rate",
            "target_expressed", "survival_sig", "known_crc", "validation_score"
        ]].to_dict(orient="records"),
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    top15.to_csv(OUTPUT_DIR / "top15_validated.csv", index=False)
    print(f"\n  Results saved: {out_json}")
    print(f"  Top15 CSV saved: {OUTPUT_DIR / 'top15_validated.csv'}")
    return summary


def upload_to_s3():
    # Overridden by orchestrator when needed.
    return None


def main():
    t0 = time.time()
    print("\n" + "=" * 60)
    title = f"  Step 6: CRC External Validation (TCGA-{TCGA_LABEL})"
    if INCLUDE_GSE39582:
        title += " + GSE39582"
    print(title)
    print("=" * 60)

    top30, drug_ann, ens_results, expr, clin_pat, sample_cols, sample_to_patient = load_data()
    df_a = method_a_tcga_expression(expr, sample_cols, top30, drug_ann)
    df_b = method_b_tcga_survival(expr, sample_cols, sample_to_patient, clin_pat, top30, drug_ann)
    p_at_k = method_c_precision(top30, drug_ann)
    gse_summary = summarize_gse39582()
    top15, all_scores = select_top15(top30, df_a, df_b, drug_ann)
    summary = save_results(df_a, df_b, p_at_k, gse_summary, top15, all_scores, ens_results)
    upload_to_s3()

    print("\n" + "=" * 60)
    print(f"  Step 6 COMPLETE ({(time.time()-t0)/60:.1f} min)")
    print("=" * 60)
    return summary


if __name__ == "__main__":
    main()
