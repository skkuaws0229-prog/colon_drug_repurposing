#!/usr/bin/env python3
"""
SAINT 포함 확장 앙상블 평가

추가 조합:
1. CatBoost-Drug + SAINT
2. CatBoost-Full + CatBoost-Drug + SAINT
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, ndcg_score
from pathlib import Path
import json
from datetime import datetime

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
subset_dir = base_dir / "20260415_v4_ensemble_test/catboost_subset"
saint_dir = base_dir / "20260415_v4_ensemble_test/new_models/saint"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 100)
print("SAINT 포함 확장 앙상블 평가")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# OOF
catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
catboost_drug_oof = np.load(subset_dir / "catboost_drug/catboost_drug_oof.npy")
saint_oof = np.load(saint_dir / "saint_oof.npy")

# Holdout
catboost_full_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")
catboost_drug_holdout = np.load(subset_dir / "catboost_drug/catboost_drug_holdout.npy")
saint_holdout = np.load(saint_dir / "saint_holdout.npy")

# Ground truth
y_train_full = np.load(step4_dir / "y_train.npy")
n_samples = len(y_train_full)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

y_cv = y_train_full[train_idx]
y_holdout = y_train_full[holdout_idx]

print(f"CatBoost-Full OOF: {catboost_full_oof.shape}")
print(f"CatBoost-Drug OOF: {catboost_drug_oof.shape}")
print(f"SAINT OOF: {saint_oof.shape}")
print(f"y_cv: {y_cv.shape}, y_holdout: {y_holdout.shape}")

# ============================================================================
# 메트릭 함수
# ============================================================================
def precision_at_k(y_true, y_pred, k=30):
    """Precision@K"""
    top_k_true = set(np.argsort(y_true)[:k])
    top_k_pred = set(np.argsort(y_pred)[:k])
    return len(top_k_true & top_k_pred) / k

def ndcg_at_k(y_true, y_pred, k=30):
    """NDCG@K"""
    top_k_idx = np.argsort(y_pred)[:k]
    relevance = np.max(y_true) - y_true
    y_true_topk = relevance[top_k_idx].reshape(1, -1)
    y_pred_topk = (np.max(y_pred) - y_pred)[top_k_idx].reshape(1, -1)
    ndcg = ndcg_score(y_true_topk, y_pred_topk)
    return ndcg

def evaluate_predictions(y_true, y_pred, name="Model"):
    """예측 평가"""
    spearman = spearmanr(y_true, y_pred)[0]
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    p30 = precision_at_k(y_true, y_pred, k=30)
    ndcg30 = ndcg_at_k(y_true, y_pred, k=30)
    return {
        "name": name,
        "spearman": float(spearman),
        "rmse": float(rmse),
        "p@30": float(p30),
        "ndcg@30": float(ndcg30)
    }

def get_top30_drugs(y_pred, name="Model"):
    """Top-30 약물 목록"""
    top30_idx = np.argsort(y_pred)[:30]
    drugs = []
    for rank, idx in enumerate(top30_idx, 1):
        drugs.append({
            "rank": rank,
            "sample_idx": int(idx),
            "predicted_ic50": float(y_pred[idx])
        })
    return drugs

# ============================================================================
# OOF Spearman (for weighted ensemble)
# ============================================================================
full_oof_sp = spearmanr(y_cv, catboost_full_oof)[0]
drug_oof_sp = spearmanr(y_cv, catboost_drug_oof)[0]
saint_oof_sp = spearmanr(y_cv, saint_oof)[0]

print(f"\nOOF Spearman: Full={full_oof_sp:.4f}, Drug={drug_oof_sp:.4f}, SAINT={saint_oof_sp:.4f}")

# ============================================================================
# 앙상블 조합
# ============================================================================
print("\n[2] 앙상블 조합 평가")
print("-" * 100)

results = []

# Baseline
print("\n[Baseline] CatBoost-Full")
full_oof_metrics = evaluate_predictions(y_cv, catboost_full_oof, "Full_OOF")
full_holdout_metrics = evaluate_predictions(y_holdout, catboost_full_holdout, "Full_Holdout")
print(f"  OOF Spearman: {full_oof_metrics['spearman']:.4f}, Holdout Spearman: {full_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full (baseline)",
    "weighting": "N/A",
    "weights": {"Full": 1.0},
    "oof_metrics": full_oof_metrics,
    "holdout_metrics": full_holdout_metrics,
    "top30_holdout": get_top30_drugs(catboost_full_holdout)
})

# 1. CatBoost-Drug + SAINT (Weighted)
print("\n1. CatBoost-Drug + SAINT (Weighted)")
w_drug = max(drug_oof_sp, 0)
w_saint = max(saint_oof_sp, 0)
total = w_drug + w_saint
w_drug /= total
w_saint /= total

print(f"  가중치: Drug={w_drug:.4f}, SAINT={w_saint:.4f}")

ensemble_ds_w_oof = w_drug * catboost_drug_oof + w_saint * saint_oof
ensemble_ds_w_holdout = w_drug * catboost_drug_holdout + w_saint * saint_holdout

ds_w_oof_metrics = evaluate_predictions(y_cv, ensemble_ds_w_oof, "Drug+SAINT_Weighted_OOF")
ds_w_holdout_metrics = evaluate_predictions(y_holdout, ensemble_ds_w_holdout, "Drug+SAINT_Weighted_Holdout")

print(f"  OOF Spearman: {ds_w_oof_metrics['spearman']:.4f}, Holdout Spearman: {ds_w_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Drug+SAINT",
    "weighting": "Weighted",
    "weights": {"Drug": float(w_drug), "SAINT": float(w_saint)},
    "oof_metrics": ds_w_oof_metrics,
    "holdout_metrics": ds_w_holdout_metrics,
    "top30_holdout": get_top30_drugs(ensemble_ds_w_holdout)
})

# 2. CatBoost-Drug + SAINT (Equal)
print("\n2. CatBoost-Drug + SAINT (Equal)")
ensemble_ds_e_oof = 0.5 * catboost_drug_oof + 0.5 * saint_oof
ensemble_ds_e_holdout = 0.5 * catboost_drug_holdout + 0.5 * saint_holdout

ds_e_oof_metrics = evaluate_predictions(y_cv, ensemble_ds_e_oof, "Drug+SAINT_Equal_OOF")
ds_e_holdout_metrics = evaluate_predictions(y_holdout, ensemble_ds_e_holdout, "Drug+SAINT_Equal_Holdout")

print(f"  OOF Spearman: {ds_e_oof_metrics['spearman']:.4f}, Holdout Spearman: {ds_e_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Drug+SAINT",
    "weighting": "Equal",
    "weights": {"Drug": 0.5, "SAINT": 0.5},
    "oof_metrics": ds_e_oof_metrics,
    "holdout_metrics": ds_e_holdout_metrics,
    "top30_holdout": get_top30_drugs(ensemble_ds_e_holdout)
})

# 3. CatBoost-Full + CatBoost-Drug + SAINT (Weighted)
print("\n3. CatBoost-Full + CatBoost-Drug + SAINT (Weighted)")
w_full = max(full_oof_sp, 0)
w_drug2 = max(drug_oof_sp, 0)
w_saint2 = max(saint_oof_sp, 0)
total2 = w_full + w_drug2 + w_saint2
w_full /= total2
w_drug2 /= total2
w_saint2 /= total2

print(f"  가중치: Full={w_full:.4f}, Drug={w_drug2:.4f}, SAINT={w_saint2:.4f}")

ensemble_fds_w_oof = w_full * catboost_full_oof + w_drug2 * catboost_drug_oof + w_saint2 * saint_oof
ensemble_fds_w_holdout = w_full * catboost_full_holdout + w_drug2 * catboost_drug_holdout + w_saint2 * saint_holdout

fds_w_oof_metrics = evaluate_predictions(y_cv, ensemble_fds_w_oof, "Full+Drug+SAINT_Weighted_OOF")
fds_w_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fds_w_holdout, "Full+Drug+SAINT_Weighted_Holdout")

print(f"  OOF Spearman: {fds_w_oof_metrics['spearman']:.4f}, Holdout Spearman: {fds_w_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Drug+SAINT",
    "weighting": "Weighted",
    "weights": {"Full": float(w_full), "Drug": float(w_drug2), "SAINT": float(w_saint2)},
    "oof_metrics": fds_w_oof_metrics,
    "holdout_metrics": fds_w_holdout_metrics,
    "top30_holdout": get_top30_drugs(ensemble_fds_w_holdout)
})

# 4. CatBoost-Full + CatBoost-Drug + SAINT (Equal)
print("\n4. CatBoost-Full + CatBoost-Drug + SAINT (Equal)")
ensemble_fds_e_oof = (catboost_full_oof + catboost_drug_oof + saint_oof) / 3
ensemble_fds_e_holdout = (catboost_full_holdout + catboost_drug_holdout + saint_holdout) / 3

fds_e_oof_metrics = evaluate_predictions(y_cv, ensemble_fds_e_oof, "Full+Drug+SAINT_Equal_OOF")
fds_e_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fds_e_holdout, "Full+Drug+SAINT_Equal_Holdout")

print(f"  OOF Spearman: {fds_e_oof_metrics['spearman']:.4f}, Holdout Spearman: {fds_e_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Drug+SAINT",
    "weighting": "Equal",
    "weights": {"Full": 1/3, "Drug": 1/3, "SAINT": 1/3},
    "oof_metrics": fds_e_oof_metrics,
    "holdout_metrics": fds_e_holdout_metrics,
    "top30_holdout": get_top30_drugs(ensemble_fds_e_holdout)
})

# ============================================================================
# 비교 표
# ============================================================================
print("\n" + "=" * 100)
print("성능 비교표")
print("=" * 100)

print(f"\n{'Combination':30s} {'Weighting':15s} {'Holdout Sp':>12s} {'RMSE':>12s} {'P@30':>12s} {'NDCG@30':>12s}")
print("-" * 90)
for r in results:
    print(f"{r['combination']:30s} {r['weighting']:15s} "
          f"{r['holdout_metrics']['spearman']:>12.4f} {r['holdout_metrics']['rmse']:>12.4f} "
          f"{r['holdout_metrics']['p@30']:>12.4f} {r['holdout_metrics']['ndcg@30']:>12.4f}")

# Best performer
best_holdout = max(results, key=lambda x: x['holdout_metrics']['spearman'])
baseline = results[0]['holdout_metrics']['spearman']
best_value = best_holdout['holdout_metrics']['spearman']
improvement = best_value - baseline

print(f"\n🏆 Best: {best_holdout['combination']} ({best_holdout['weighting']}) = {best_value:.4f}")
if best_value > baseline:
    print(f"✅ 개선: +{improvement:.4f} ({improvement/baseline*100:.2f}%)")
else:
    print(f"❌ 악화: {improvement:.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[3] 저장")
print("-" * 100)

output_json = output_dir / "ensemble_saint_extended_results.json"
with open(output_json, "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "baseline": {"model": "CatBoost-Full", "holdout_spearman": float(baseline)},
        "results": results,
        "best": {
            "combination": best_holdout['combination'],
            "weighting": best_holdout['weighting'],
            "holdout_spearman": float(best_value),
            "improvement": float(improvement)
        }
    }, f, indent=2)

print(f"✓ JSON: {output_json}")

# Top-30 CSV
for r in results:
    comb_name = r['combination'].replace("+", "_").replace(" ", "_").replace("(", "").replace(")", "")
    weight_name = r['weighting'].replace("/", "_")

    top30_df = pd.DataFrame(r['top30_holdout'])
    top30_path = output_dir / f"top30_saint_{comb_name.lower()}_{weight_name.lower()}.csv"
    top30_df.to_csv(top30_path, index=False)
    print(f"✓ Top-30: {top30_path}")

print("\n" + "=" * 100)
print("SAINT 포함 앙상블 평가 완료!")
print("=" * 100)
