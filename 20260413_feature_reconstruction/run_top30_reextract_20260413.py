#!/usr/bin/env python3
"""
Top 30 Drug Re-extraction (v2 기준)
═══════════════════════════════════════════════════════════════
Data: v2 OOF predictions (oof_predictions.parquet)
Ensemble: Spearman 비례 weight (St=0.38 / Cb=0.31 / RF=0.21 / XG=0.10)
Selection: 앙상블 pred score 기준 상위 30개 (sample별 평균 → drug 기준 정렬)
Output: results/top30_reextract_20260413.csv
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
OOF_PATH = PROJECT_ROOT / "results" / "ml_mechanism_v2_results_20260413" / "oof_predictions.parquet"
DRUG_ANN_S3 = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"

OUTPUT_DIR = PROJECT_ROOT / "results" / "top30_reextract_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Spearman 비례 가중치 (v2 기준 Stacking_Ridge=0.5182, CatBoost=0.5140, RF=0.5064, XGBoost=0.4908)
ENSEMBLE_WEIGHTS = {
    "pred_Stacking_Ridge": 0.38,
    "pred_CatBoost": 0.31,
    "pred_RandomForest": 0.21,
    "pred_XGBoost": 0.10,
}

TOP_K = 30
# IC50 sensitivity threshold: ln(IC50) < ln(1.0) ≈ 0 → sensitive
SENSITIVITY_THRESHOLD = 0.0


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Top 30 Drug Re-extraction (v2 OOF 기반)")
    print("=" * 70)

    # ── 1. OOF predictions 로드 ──
    print("\n  Loading OOF predictions...")
    oof = pd.read_parquet(OOF_PATH)
    print(f"    Shape: {oof.shape}")
    print(f"    Columns: {list(oof.columns)}")
    print(f"    Drugs: {oof['canonical_drug_id'].nunique()}, Samples: {oof['sample_id'].nunique()}")

    pred_cols = [c for c in oof.columns if c.startswith("pred_")]
    print(f"    Prediction columns: {pred_cols}")

    # 가중치 검증
    w_sum = sum(ENSEMBLE_WEIGHTS.values())
    print(f"\n  Ensemble weights (sum={w_sum:.2f}):")
    for col, w in ENSEMBLE_WEIGHTS.items():
        model = col.replace("pred_", "")
        sp = oof[col].values
        sp_corr = np.corrcoef(sp, oof["y_true"].values)[0, 1]
        print(f"    {model:<20s}: w={w:.2f}  (Pearson with y_true: {sp_corr:.4f})")

    # ── 2. 앙상블 예측값 계산 ──
    print("\n  Computing ensemble predictions...")
    oof["pred_ensemble"] = sum(
        oof[col] * w for col, w in ENSEMBLE_WEIGHTS.items()
    )

    # 전체 OOF Spearman 확인
    from scipy.stats import spearmanr
    sp_ens, _ = spearmanr(oof["y_true"], oof["pred_ensemble"])
    print(f"    Ensemble OOF Spearman: {sp_ens:.4f}")

    # ── 3. Drug별 평균 예측값 ──
    print("\n  Aggregating per-drug predictions...")
    drug_stats = oof.groupby("canonical_drug_id").agg(
        mean_pred_ic50=("pred_ensemble", "mean"),
        std_pred_ic50=("pred_ensemble", "std"),
        mean_true_ic50=("y_true", "mean"),
        std_true_ic50=("y_true", "std"),
        n_samples=("sample_id", "count"),
    ).reset_index()

    # Sensitivity rate: pred < threshold 인 비율
    sens = oof.groupby("canonical_drug_id").apply(
        lambda g: (g["pred_ensemble"] < SENSITIVITY_THRESHOLD).mean()
    ).reset_index(name="sensitivity_rate")
    drug_stats = drug_stats.merge(sens, on="canonical_drug_id")

    # True sensitivity rate
    true_sens = oof.groupby("canonical_drug_id").apply(
        lambda g: (g["y_true"] < SENSITIVITY_THRESHOLD).mean()
    ).reset_index(name="true_sensitivity_rate")
    drug_stats = drug_stats.merge(true_sens, on="canonical_drug_id")

    print(f"    Total drugs: {len(drug_stats)}")
    print(f"    Pred IC50 range: [{drug_stats['mean_pred_ic50'].min():.3f}, "
          f"{drug_stats['mean_pred_ic50'].max():.3f}]")

    # ── 4. Drug annotation 병합 ──
    print("\n  Loading drug annotations...")
    drug_ann = pd.read_parquet(DRUG_ANN_S3)
    drug_ann = drug_ann.rename(columns={"DRUG_ID": "canonical_drug_id"})
    drug_ann["canonical_drug_id"] = drug_ann["canonical_drug_id"].astype(str)
    drug_stats["canonical_drug_id"] = drug_stats["canonical_drug_id"].astype(str)

    drug_stats = drug_stats.merge(
        drug_ann[["canonical_drug_id", "DRUG_NAME", "PUTATIVE_TARGET_NORMALIZED",
                  "PATHWAY_NAME_NORMALIZED"]],
        on="canonical_drug_id", how="left",
    )
    drug_stats = drug_stats.rename(columns={
        "DRUG_NAME": "drug_name",
        "PUTATIVE_TARGET_NORMALIZED": "target",
        "PATHWAY_NAME_NORMALIZED": "pathway",
    })

    # ── 5. Top 30 선정 (낮은 IC50 = 더 효과적) ──
    drug_stats = drug_stats.sort_values("mean_pred_ic50", ascending=True)
    drug_stats["rank"] = range(1, len(drug_stats) + 1)

    top30 = drug_stats.head(TOP_K).copy()

    # ── 6. 결과 출력 ──
    print(f"\n{'='*90}")
    print(f"  TOP {TOP_K} DRUGS (v2 앙상블 기준, 낮은 IC50 = 효과적)")
    print(f"{'='*90}")
    print(f"  {'Rank':>4}  {'Drug':<25} {'Pred IC50':>10} {'True IC50':>10} "
          f"{'Sens%':>6} {'Target':<25} {'Pathway':<20}")
    print(f"  {'-'*106}")

    for _, r in top30.iterrows():
        target = str(r.get("target", "N/A"))[:23]
        pathway = str(r.get("pathway", "N/A"))[:18]
        print(f"  {int(r['rank']):>4}  {str(r.get('drug_name', 'N/A')):<25} "
              f"{r['mean_pred_ic50']:>10.4f} {r['mean_true_ic50']:>10.4f} "
              f"{r['sensitivity_rate']:>5.0%} {target:<25} {pathway:<20}")

    print(f"  {'-'*106}")

    # ── 7. 통계 요약 ──
    print(f"\n  Top {TOP_K} 통계:")
    print(f"    Pred IC50 mean: {top30['mean_pred_ic50'].mean():.4f} "
          f"(전체: {drug_stats['mean_pred_ic50'].mean():.4f})")
    print(f"    True IC50 mean: {top30['mean_true_ic50'].mean():.4f} "
          f"(전체: {drug_stats['mean_true_ic50'].mean():.4f})")
    print(f"    Sensitivity rate (pred): {top30['sensitivity_rate'].mean():.1%} "
          f"(전체: {drug_stats['sensitivity_rate'].mean():.1%})")
    print(f"    Sensitivity rate (true): {top30['true_sensitivity_rate'].mean():.1%} "
          f"(전체: {drug_stats['true_sensitivity_rate'].mean():.1%})")

    # Known BRCA drugs check
    known_brca = {
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
    known_hits = [n for n in top30["drug_name"].values if n in known_brca]
    print(f"\n    Known BRCA drugs in Top {TOP_K}: {len(known_hits)}/{TOP_K}")
    for name in known_hits:
        rank = int(top30[top30["drug_name"] == name]["rank"].values[0])
        print(f"      #{rank}: {name}")

    # ── 8. 저장 ──
    # CSV
    save_cols = ["rank", "canonical_drug_id", "drug_name", "target", "pathway",
                 "mean_pred_ic50", "std_pred_ic50", "mean_true_ic50",
                 "sensitivity_rate", "true_sensitivity_rate", "n_samples"]
    csv_path = OUTPUT_DIR / "top30_reextract.csv"
    top30[save_cols].to_csv(csv_path, index=False)
    print(f"\n  Saved: {csv_path}")

    # JSON (전체 295 drug ranking)
    json_path = OUTPUT_DIR / "all_drug_ranking.json"
    all_ranking = drug_stats[save_cols].to_dict(orient="records")

    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        return obj

    with open(json_path, "w") as f:
        json.dump({
            "description": "v2 ensemble-based drug ranking (all 295 drugs)",
            "ensemble_weights": {k.replace("pred_", ""): v for k, v in ENSEMBLE_WEIGHTS.items()},
            "ensemble_oof_spearman": float(sp_ens),
            "top30_drugs": top30[save_cols].to_dict(orient="records"),
            "total_drugs": len(drug_stats),
        }, f, indent=2, default=convert)
    print(f"  Saved: {json_path}")

    dt = time.time() - t0
    print(f"\n  Completed in {dt:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
