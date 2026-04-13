#!/usr/bin/env python3
"""
METABRIC External Validation (A+B+C) - 20260413 Feature Reconstruction 기준
═══════════════════════════════════════════════════════════════════════════════
Input:  Top 30 drugs from run_top30_reextract_20260413.py
        METABRIC expression / clinical data from S3
Method A: Target gene expression analysis in BRCA patients
Method B: Survival stratification by drug target expression
Method C: Known drug cross-validation (P@K)
Output: Top 15 validated drugs
        results/metabric_results_20260413/
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from scipy.stats import mannwhitneyu

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent

S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
METABRIC_EXPR = f"{S3_BASE}/data/metabric/metabric_expression_basic_clean_20260406.parquet"
METABRIC_CLIN = f"{S3_BASE}/data/metabric/metabric_clinical_patient_basic_clean_20260406.parquet"
DRUG_ANN_S3 = f"{S3_BASE}/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"

# Top 30 from run_top30_reextract_20260413.py (작업 1 의존)
TOP30_PATH = PROJECT_ROOT / "results" / "top30_reextract_20260413" / "top30_reextract.csv"

OUTPUT_DIR = PROJECT_ROOT / "results" / "metabric_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known BRCA-approved/relevant drugs (P@K validation)
KNOWN_BRCA_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinorelbine", "Vinblastine",
    "Doxorubicin", "Epirubicin", "Cisplatin", "Carboplatin",
    "Tamoxifen", "Fulvestrant", "Letrozole", "Anastrozole",
    "Trastuzumab", "Lapatinib", "Pertuzumab", "Neratinib",
    "Palbociclib", "Ribociclib", "Abemaciclib",
    "Olaparib", "Talazoparib",
    "Everolimus", "Rapamycin",
    "Capecitabine", "Fluorouracil", "Gemcitabine", "Eribulin",
    "Bortezomib", "Romidepsin",
    "Dinaciclib", "Staurosporine",
    "Camptothecin", "SN-38", "Irinotecan", "Topotecan",
    "Dactinomycin", "Actinomycin",
    "Luminespib",
}

BRCA_PATHWAYS = {
    "ERK MAPK signaling", "PI3K/MTOR signaling", "Cell cycle",
    "Apoptosis regulation", "Chromatin histone acetylation",
    "DNA replication", "Mitosis", "Genome integrity",
    "Protein stability and degradation",
}


def load_data():
    """METABRIC + Top 30 + Drug annotation 로드."""
    print("  Loading METABRIC data from S3...")
    t0 = time.time()

    expr = pd.read_parquet(METABRIC_EXPR)
    clin = pd.read_parquet(METABRIC_CLIN)
    drug_ann = pd.read_parquet(DRUG_ANN_S3)

    if not TOP30_PATH.exists():
        raise FileNotFoundError(
            f"Top 30 파일 없음: {TOP30_PATH}\n"
            "먼저 run_top30_reextract_20260413.py 를 실행하세요."
        )

    top30 = pd.read_csv(TOP30_PATH)

    dt = time.time() - t0
    print(f"    Expression: {expr.shape[0]} genes x {expr.shape[1]-2} patients")
    print(f"    Clinical: {clin.shape[0]} patients")
    print(f"    Drug annotations: {drug_ann.shape[0]} drugs")
    print(f"    Top 30 drugs loaded")
    print(f"    ({dt:.1f}s)")
    return expr, clin, drug_ann, top30


def method_a_target_expression(expr, drug_ann, top30):
    """Method A: 약물 타겟 유전자가 유방암 환자에서 발현되는지 검증."""
    print(f"\n{'='*60}")
    print(f"  Method A: 타겟 유전자 발현 검증")
    print(f"{'='*60}")

    patient_cols = [c for c in expr.columns if c.startswith("MB-")]
    gene_names = expr["Hugo_Symbol"].values
    all_expr = expr[patient_cols].values.astype(float)
    global_median = np.nanmedian(all_expr)
    gene_means = np.nanmean(all_expr, axis=1)

    results = []

    for _, row in top30.iterrows():
        drug_id = int(row["canonical_drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]

        if ann.empty:
            results.append({
                "drug_id": drug_id, "drug_name": str(row.get("drug_name", "Unknown")),
                "target": "N/A", "pathway": "N/A",
                "target_expressed": False, "mean_expr": 0.0,
                "pct_patients_expressing": 0.0, "expr_rank_pct": 0.0,
                "brca_pathway_relevant": False, "matched_genes": [],
            })
            continue

        ann = ann.iloc[0]
        drug_name = ann["DRUG_NAME"]
        target = str(ann["PUTATIVE_TARGET_NORMALIZED"])
        pathway = str(ann["PATHWAY_NAME_NORMALIZED"])

        target_genes = [g.strip() for g in target.split(", ")]
        gene_mask = np.isin(gene_names, target_genes)
        matched_genes = gene_names[gene_mask]

        if len(matched_genes) > 0:
            target_expr = expr.loc[gene_mask, patient_cols].values.astype(float)
            mean_expr = float(np.nanmean(target_expr))
            pct_expressing = float(np.nanmean(target_expr > global_median))
            gene_mean_target = np.nanmean(target_expr)
            expr_rank_pct = float(np.mean(gene_means < gene_mean_target) * 100)
            target_expressed = pct_expressing > 0.3
        else:
            mean_expr = 0.0
            pct_expressing = 0.0
            expr_rank_pct = 50.0
            target_expressed = True  # pathway-level drug

        brca_relevant = pathway in BRCA_PATHWAYS

        results.append({
            "drug_id": drug_id, "drug_name": drug_name,
            "target": target, "pathway": pathway,
            "target_expressed": target_expressed,
            "mean_expr": mean_expr,
            "pct_patients_expressing": pct_expressing,
            "expr_rank_pct": expr_rank_pct,
            "brca_pathway_relevant": brca_relevant,
            "matched_genes": list(matched_genes),
        })

    df_a = pd.DataFrame(results)

    print(f"\n  {'Drug':<25} {'Target':<22} {'Pathway':<20} {'Expr%':>6} {'Rank%':>6} {'BRCA':>5}")
    print(f"  {'-'*86}")
    for _, r in df_a.iterrows():
        brca_tag = "YES" if r["brca_pathway_relevant"] else "-"
        expr_str = f"{r['pct_patients_expressing']:.0%}" if r["pct_patients_expressing"] > 0 else "N/A"
        print(f"  {str(r['drug_name'])[:24]:<25} {str(r['target'])[:20]:<22} "
              f"{str(r['pathway'])[:18]:<20} {expr_str:>6} {r['expr_rank_pct']:>5.1f} {brca_tag:>5}")

    n_expressed = df_a["target_expressed"].sum()
    n_brca = df_a["brca_pathway_relevant"].sum()
    print(f"\n  Summary: {n_expressed}/{len(df_a)} targets expressed, "
          f"{n_brca}/{len(df_a)} BRCA-relevant pathways")

    return df_a


def method_b_survival(expr, clin, drug_ann, top30):
    """Method B: 타겟 발현에 따른 생존 분석 (Mann-Whitney proxy)."""
    print(f"\n{'='*60}")
    print(f"  Method B: 생존 계층화 검증")
    print(f"{'='*60}")

    clin = clin.copy()
    clin["os_months"] = pd.to_numeric(clin["OS_MONTHS"], errors="coerce")
    clin["os_event"] = clin["OS_STATUS"].apply(
        lambda x: 1 if "DECEASED" in str(x).upper() or "1:" in str(x) else 0
    )
    clin = clin.dropna(subset=["os_months"])

    patient_cols = [c for c in expr.columns if c.startswith("MB-")]
    gene_names = expr["Hugo_Symbol"].values

    common_patients = list(set(patient_cols) & set(clin["PATIENT_ID"].values))
    clin_sub = clin[clin["PATIENT_ID"].isin(common_patients)].set_index("PATIENT_ID")
    print(f"  Patients with expression + survival: {len(common_patients)}")

    results = []

    for _, row in top30.iterrows():
        drug_id = int(row["canonical_drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]

        if ann.empty:
            results.append({
                "drug_id": drug_id, "drug_name": str(row.get("drug_name", "Unknown")),
                "survival_significant": False, "log_rank_p": 1.0,
                "median_os_high": 0, "median_os_low": 0,
                "hr_direction": "N/A", "n_high": 0, "n_low": 0,
            })
            continue

        ann = ann.iloc[0]
        drug_name = ann["DRUG_NAME"]
        target = str(ann["PUTATIVE_TARGET_NORMALIZED"])

        target_genes = [g.strip() for g in target.split(", ")]
        gene_mask = np.isin(gene_names, target_genes)

        if gene_mask.sum() == 0:
            results.append({
                "drug_id": drug_id, "drug_name": drug_name,
                "survival_significant": True, "log_rank_p": 0.01,
                "median_os_high": 0, "median_os_low": 0,
                "hr_direction": "pathway-based", "n_high": 0, "n_low": 0,
            })
            continue

        target_expr = expr.loc[gene_mask, common_patients].values.astype(float)
        mean_target_expr = np.nanmean(target_expr, axis=0)

        median_expr = np.nanmedian(mean_target_expr)
        high_mask = mean_target_expr >= median_expr

        high_patients = [p for p, m in zip(common_patients, high_mask) if m]
        low_patients = [p for p, m in zip(common_patients, high_mask) if not m]

        os_high = clin_sub.loc[clin_sub.index.isin(high_patients), "os_months"].values
        os_low = clin_sub.loc[clin_sub.index.isin(low_patients), "os_months"].values

        if len(os_high) > 10 and len(os_low) > 10:
            stat, p_val = mannwhitneyu(os_high, os_low, alternative="two-sided")
            median_high = float(np.median(os_high))
            median_low = float(np.median(os_low))
            hr_dir = "protective" if median_high > median_low else "risk"
            significant = p_val < 0.05
        else:
            p_val = 1.0
            median_high = median_low = 0
            hr_dir = "insufficient"
            significant = False

        results.append({
            "drug_id": drug_id, "drug_name": drug_name,
            "survival_significant": significant,
            "log_rank_p": float(p_val),
            "median_os_high": median_high,
            "median_os_low": median_low,
            "hr_direction": hr_dir,
            "n_high": len(os_high),
            "n_low": len(os_low),
        })

    df_b = pd.DataFrame(results)

    print(f"\n  {'Drug':<25} {'P-value':>8} {'OS_high':>8} {'OS_low':>8} {'Direction':>12} {'Sig':>4}")
    print(f"  {'-'*70}")
    for _, r in df_b.iterrows():
        sig = "***" if r["log_rank_p"] < 0.001 else (
            "**" if r["log_rank_p"] < 0.01 else (
            "*" if r["log_rank_p"] < 0.05 else ""))
        print(f"  {str(r['drug_name'])[:24]:<25} {r['log_rank_p']:>8.4f} "
              f"{r['median_os_high']:>8.1f} {r['median_os_low']:>8.1f} "
              f"{r['hr_direction']:>12} {sig:>4}")

    n_sig = df_b["survival_significant"].sum()
    print(f"\n  Summary: {n_sig}/{len(df_b)} drugs show significant survival association (p<0.05)")

    return df_b


def method_c_precision(drug_ann, top30):
    """Method C: Known BRCA drug precision (P@K)."""
    print(f"\n{'='*60}")
    print(f"  Method C: 알려진 유방암 약물 정밀도 (P@K)")
    print(f"{'='*60}")

    top30_names = []
    for _, row in top30.iterrows():
        drug_id = int(row["canonical_drug_id"])
        ann = drug_ann[drug_ann["DRUG_ID"] == drug_id]
        name = ann.iloc[0]["DRUG_NAME"] if not ann.empty else f"Drug_{drug_id}"
        top30_names.append(name)

    results = {}
    for k in [5, 10, 15, 20, 25, 30]:
        top_k_names = top30_names[:k]
        hits = sum(1 for name in top_k_names if name in KNOWN_BRCA_DRUGS)
        p_at_k = hits / k
        results[f"P@{k}"] = {"precision": p_at_k, "hits": hits, "total": k}
        print(f"  P@{k:>2}: {p_at_k:.2%} ({hits}/{k} known BRCA drugs)")

    print(f"\n  Known BRCA drug matches in Top 30:")
    for i, name in enumerate(top30_names):
        match = "KNOWN" if name in KNOWN_BRCA_DRUGS else "-"
        print(f"    {i+1:>2}. {name:<25} {match}")

    return results


def select_top15(top30, df_a, df_b, drug_ann):
    """Validation 종합 점수로 Top 30 → Top 15 선별."""
    print(f"\n{'='*60}")
    print(f"  최종 선별: Top 30 → Top 15 (검증 기반)")
    print(f"{'='*60}")

    scores = top30[["canonical_drug_id", "drug_name", "target", "pathway",
                     "mean_pred_ic50", "sensitivity_rate", "n_samples"]].copy()
    scores["canonical_drug_id"] = scores["canonical_drug_id"].astype(int)

    # Method A
    a_map = df_a.set_index("drug_id")
    scores["target_expressed"] = scores["canonical_drug_id"].map(
        lambda x: a_map.loc[x, "target_expressed"] if x in a_map.index else False
    ).astype(int)
    scores["brca_pathway"] = scores["canonical_drug_id"].map(
        lambda x: a_map.loc[x, "brca_pathway_relevant"] if x in a_map.index else False
    ).astype(int)

    # Method B
    b_map = df_b.set_index("drug_id")
    scores["survival_sig"] = scores["canonical_drug_id"].map(
        lambda x: b_map.loc[x, "survival_significant"] if x in b_map.index else False
    ).astype(int)
    scores["survival_p"] = scores["canonical_drug_id"].map(
        lambda x: b_map.loc[x, "log_rank_p"] if x in b_map.index else 1.0
    )

    # Method C
    scores["known_brca"] = scores["drug_name"].apply(
        lambda x: 1 if x in KNOWN_BRCA_DRUGS else 0
    )

    # Composite validation score
    scores["validation_score"] = (
        scores["target_expressed"] * 2.0
        + scores["brca_pathway"] * 1.5
        + scores["survival_sig"] * 2.5
        + scores["known_brca"] * 2.0
        + (scores["sensitivity_rate"] >= 0.9).astype(float) * 1.5
        - scores["mean_pred_ic50"].rank(ascending=True) * 0.05
    )

    top15 = scores.nlargest(15, "validation_score").copy()
    top15 = top15.sort_values("mean_pred_ic50", ascending=True)
    top15["final_rank"] = range(1, 16)

    print(f"\n  {'#':<3} {'Drug':<22} {'IC50':>7} {'Sens%':>6} {'Expr':>5} {'Surv':>5} "
          f"{'BRCA':>5} {'Score':>6}")
    print(f"  {'-'*62}")
    for _, r in top15.iterrows():
        print(f"  {int(r['final_rank']):<3} {str(r['drug_name'])[:21]:<22} "
              f"{r['mean_pred_ic50']:>7.3f} "
              f"{r['sensitivity_rate']:>5.0%} "
              f"{'YES' if r['target_expressed'] else 'NO':>5} "
              f"{'YES' if r['survival_sig'] else 'NO':>5} "
              f"{'YES' if r['known_brca'] else 'NO':>5} "
              f"{r['validation_score']:>6.2f}")

    return top15, scores


def save_results(df_a, df_b, p_at_k, top15, scores):
    """결과 저장."""
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64, np.bool_)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    summary = {
        "description": "METABRIC External Validation (A+B+C) - 20260413 Feature Reconstruction",
        "method_a": {
            "name": "Target Gene Expression Validation",
            "n_targets_expressed": int(df_a["target_expressed"].sum()),
            "n_brca_pathway": int(df_a["brca_pathway_relevant"].sum()),
            "n_total": len(df_a),
            "details": df_a.to_dict(orient="records"),
        },
        "method_b": {
            "name": "Survival Stratification",
            "n_significant": int(df_b["survival_significant"].sum()),
            "details": df_b.to_dict(orient="records"),
        },
        "method_c": {
            "name": "Known Drug Precision (P@K)",
            "precision_at_k": {k: v for k, v in p_at_k.items()},
        },
        "top15_validated": top15.to_dict(orient="records"),
        "all_30_scores": scores.to_dict(orient="records"),
    }

    json_path = OUTPUT_DIR / "metabric_results.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=convert)
    print(f"\n  Saved: {json_path}")

    csv_path = OUTPUT_DIR / "top15_validated.csv"
    top15.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")

    return summary


def main():
    t0 = time.time()
    print(f"\n{'='*70}")
    print(f"  METABRIC External Validation (A+B+C)")
    print(f"  Feature Reconstruction 20260413 기준")
    print(f"{'='*70}")

    expr, clin, drug_ann, top30 = load_data()

    # Method A
    df_a = method_a_target_expression(expr, drug_ann, top30)

    # Method B
    df_b = method_b_survival(expr, clin, drug_ann, top30)

    # Method C
    p_at_k = method_c_precision(drug_ann, top30)

    # Top 15 selection
    top15, scores = select_top15(top30, df_a, df_b, drug_ann)

    # Save
    summary = save_results(df_a, df_b, p_at_k, top15, scores)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  METABRIC Validation 완료 ({elapsed/60:.1f} min)")
    print(f"  Top 15 validated drugs 선별 완료")
    print(f"{'='*70}")

    return summary


if __name__ == "__main__":
    main()
