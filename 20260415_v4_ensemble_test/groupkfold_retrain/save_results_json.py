"""
GroupKFold 재학습 결과를 JSON으로 저장 (numpy bool_ 이슈 수정)
"""
import json
from pathlib import Path

# 실행 결과에서 추출한 값들
output_dir = Path(__file__).parent

v3_baseline = 0.491

# CatBoost-Full 결과
catboost_full_folds = [0.5778, 0.4804, 0.4157, 0.5672, 0.5535]
catboost_full_mean_sp = 0.5189
catboost_full_std_sp = 0.0619
catboost_full_rmse = 2.2787

# CatBoost-Drug 결과
catboost_drug_folds = [0.5711, 0.5041, 0.4137, 0.5799, 0.5364]
catboost_drug_mean_sp = 0.5210
catboost_drug_std_sp = 0.0600
catboost_drug_rmse = 2.2646

# Bilinear v2 결과
bilinear_folds = [0.5331, 0.4821, 0.2003, 0.3226, 0.4988]
bilinear_mean_sp = 0.4074
bilinear_std_sp = 0.1264
bilinear_rmse = 2.8968

# Drug+Bilinear 앙상블 결과
w_drug = 0.5612
w_bilinear = 0.4388
drug_bilinear_sp = 0.5145
drug_bilinear_rmse = 2.3412

# Best model
best_name = "CatBoost-Drug"
best_sp = catboost_drug_mean_sp

results = {
    "experiment": {
        "date": "2026-04-15",
        "method": "GroupKFold by canonical_drug_id, 5-fold retrain",
        "v3_baseline": v3_baseline,
        "total_samples": 6366,
        "unique_drugs": 243
    },
    "models": {
        "CatBoost-Full": {
            "mean_spearman": float(catboost_full_mean_sp),
            "std_spearman": float(catboost_full_std_sp),
            "rmse": float(catboost_full_rmse),
            "vs_v3": float(catboost_full_mean_sp - v3_baseline),
            "fold_spearmans": [float(x) for x in catboost_full_folds]
        },
        "CatBoost-Drug": {
            "mean_spearman": float(catboost_drug_mean_sp),
            "std_spearman": float(catboost_drug_std_sp),
            "rmse": float(catboost_drug_rmse),
            "vs_v3": float(catboost_drug_mean_sp - v3_baseline),
            "fold_spearmans": [float(x) for x in catboost_drug_folds]
        },
        "Bilinear-v2": {
            "mean_spearman": float(bilinear_mean_sp),
            "std_spearman": float(bilinear_std_sp),
            "rmse": float(bilinear_rmse),
            "vs_v3": float(bilinear_mean_sp - v3_baseline),
            "fold_spearmans": [float(x) for x in bilinear_folds]
        },
        "Drug+Bilinear": {
            "spearman": float(drug_bilinear_sp),
            "rmse": float(drug_bilinear_rmse),
            "weights": {"drug": float(w_drug), "bilinear": float(w_bilinear)},
            "vs_v3": float(drug_bilinear_sp - v3_baseline)
        }
    },
    "key_findings": {
        "best_model": best_name,
        "best_spearman": float(best_sp),
        "bilinear_better_than_drug": bool(bilinear_mean_sp > catboost_drug_mean_sp),  # False
        "ensemble_improves": bool(drug_bilinear_sp > catboost_drug_mean_sp)  # False
    },
    "conclusions": {
        "bilinear_vs_drug_diff": float(bilinear_mean_sp - catboost_drug_mean_sp),
        "ensemble_vs_drug_diff": float(drug_bilinear_sp - catboost_drug_mean_sp),
        "bilinear_hurts_unseen_drugs": True,
        "ensemble_does_not_improve_groupkfold": True,
        "recommended_model": "CatBoost-Drug"
    }
}

# JSON 저장
results_path = output_dir / "groupkfold_retrain_results.json"
with open(results_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ Results saved to: {results_path}")
print(f"\nKey findings:")
print(f"  - Best model: {best_name} ({best_sp:.4f})")
print(f"  - Bilinear better than Drug: {results['key_findings']['bilinear_better_than_drug']}")
print(f"  - Ensemble improves: {results['key_findings']['ensemble_improves']}")
print(f"  - Bilinear vs Drug: {bilinear_mean_sp - catboost_drug_mean_sp:.4f}")
print(f"  - Ensemble vs Drug: {drug_bilinear_sp - catboost_drug_mean_sp:.4f}")
