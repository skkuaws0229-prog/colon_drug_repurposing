"""
현재 Drug + Bilinear v2 앙상블의 Diversity 측정

목적:
1. Drug vs Bilinear v2 상관 측정 (Pearson/Spearman)
2. Top-30 Jaccard similarity 측정
3. 현재 앙상블 성능 측정
"""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from pathlib import Path
import json

# Paths
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
drug_dir = base_dir / "20260415_v4_ensemble_test/catboost_subset/catboost_drug"
bilinear_dir = base_dir / "20260415_v4_ensemble_test/new_models/bilinear"
v3_dir = base_dir / "20260414_re_pre_project_v3"

# Load predictions
print("=" * 80)
print("현재 Drug + Bilinear v2 Diversity 측정")
print("=" * 80)

# CatBoost-Drug
drug_oof = np.load(drug_dir / "catboost_drug_oof.npy")
drug_holdout = np.load(drug_dir / "catboost_drug_holdout.npy")

# Bilinear v2
bilinear_oof = np.load(bilinear_dir / "bilinear_v2_oof.npy")
bilinear_holdout = np.load(bilinear_dir / "bilinear_v2_holdout.npy")

print(f"\n[1] 데이터 확인")
print(f"-" * 80)
print(f"Drug OOF shape: {drug_oof.shape}")
print(f"Drug Holdout shape: {drug_holdout.shape}")
print(f"Bilinear v2 OOF shape: {bilinear_oof.shape}")
print(f"Bilinear v2 Holdout shape: {bilinear_holdout.shape}")

# OOF Correlation
print(f"\n[2] OOF Diversity")
print(f"-" * 80)
oof_pearson = pearsonr(drug_oof, bilinear_oof)[0]
oof_spearman = spearmanr(drug_oof, bilinear_oof)[0]
print(f"Pearson correlation:  {oof_pearson:.4f}")
print(f"Spearman correlation: {oof_spearman:.4f}")

# Holdout Correlation
print(f"\n[3] Holdout Diversity")
print(f"-" * 80)
holdout_pearson = pearsonr(drug_holdout, bilinear_holdout)[0]
holdout_spearman = spearmanr(drug_holdout, bilinear_holdout)[0]
print(f"Pearson correlation:  {holdout_pearson:.4f}")
print(f"Spearman correlation: {holdout_spearman:.4f}")

# Top-30 Jaccard
print(f"\n[4] Top-30 Overlap (Jaccard)")
print(f"-" * 80)

def top_k_jaccard(pred1, pred2, k=30):
    """Top-K Jaccard similarity"""
    top1 = set(np.argsort(pred1)[::-1][:k])
    top2 = set(np.argsort(pred2)[::-1][:k])
    intersection = len(top1 & top2)
    union = len(top1 | top2)
    jaccard = intersection / union if union > 0 else 0
    return jaccard, intersection

oof_jaccard, oof_overlap = top_k_jaccard(drug_oof, bilinear_oof, k=30)
holdout_jaccard, holdout_overlap = top_k_jaccard(drug_holdout, bilinear_holdout, k=30)

print(f"OOF Top-30 Jaccard:      {oof_jaccard:.4f} ({oof_overlap}/30 overlap)")
print(f"Holdout Top-30 Jaccard:  {holdout_jaccard:.4f} ({holdout_overlap}/30 overlap)")

# Ensemble performance (weighted)
print(f"\n[5] 현재 앙상블 성능 (Weighted 51%/49%)")
print(f"-" * 80)

# Load targets
y_all = np.load(v3_dir / "step4_results/y_train.npy")  # Actually contains all data

# OOF와 Holdout 크기로 분할 (5092 + 1274 = 6366)
# 일반적으로 train:test = 80:20 split
y_train = y_all[:5092]  # First 5092 for train (OOF)
y_holdout = y_all[5092:5092+1274]  # Next 1274 for holdout

# Weighted ensemble (51% Drug, 49% Bilinear)
w_drug = 0.51
w_bilinear = 0.49

ensemble_oof = w_drug * drug_oof + w_bilinear * bilinear_oof
ensemble_holdout = w_drug * drug_holdout + w_bilinear * bilinear_holdout

# Metrics
oof_sp = spearmanr(y_train, ensemble_oof)[0]
holdout_sp = spearmanr(y_holdout, ensemble_holdout)[0]
oof_rmse = np.sqrt(np.mean((y_train - ensemble_oof) ** 2))
holdout_rmse = np.sqrt(np.mean((y_holdout - ensemble_holdout) ** 2))

print(f"OOF Spearman:      {oof_sp:.4f}")
print(f"OOF RMSE:          {oof_rmse:.4f}")
print(f"Holdout Spearman:  {holdout_sp:.4f}")
print(f"Holdout RMSE:      {holdout_rmse:.4f}")

# Top-30 P@30, NDCG@30
def precision_at_k(y_true, y_pred, k=30):
    """Precision@K"""
    top_k_idx = np.argsort(y_pred)[::-1][:k]
    top_k_true = y_true[top_k_idx]
    # Consider top 30 in y_true as positives
    threshold = np.sort(y_true)[::-1][min(k-1, len(y_true)-1)]
    return np.sum(top_k_true >= threshold) / k

def ndcg_at_k(y_true, y_pred, k=30):
    """NDCG@K"""
    top_k_idx = np.argsort(y_pred)[::-1][:k]
    top_k_true = y_true[top_k_idx]

    # DCG
    dcg = np.sum(top_k_true / np.log2(np.arange(2, k + 2)))

    # IDCG
    ideal_idx = np.argsort(y_true)[::-1][:k]
    ideal_true = y_true[ideal_idx]
    idcg = np.sum(ideal_true / np.log2(np.arange(2, k + 2)))

    return dcg / idcg if idcg > 0 else 0

holdout_p30 = precision_at_k(y_holdout, ensemble_holdout, k=30)
holdout_ndcg30 = ndcg_at_k(y_holdout, ensemble_holdout, k=30)

print(f"Holdout P@30:      {holdout_p30:.4f}")
print(f"Holdout NDCG@30:   {holdout_ndcg30:.4f}")

# Save results
results = {
    "timestamp": pd.Timestamp.now().isoformat(),
    "ensemble": "Drug (51%) + Bilinear v2 (49%)",
    "diversity": {
        "oof_pearson": float(oof_pearson),
        "oof_spearman": float(oof_spearman),
        "holdout_pearson": float(holdout_pearson),
        "holdout_spearman": float(holdout_spearman),
        "oof_top30_jaccard": float(oof_jaccard),
        "oof_top30_overlap": int(oof_overlap),
        "holdout_top30_jaccard": float(holdout_jaccard),
        "holdout_top30_overlap": int(holdout_overlap)
    },
    "performance": {
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "holdout_p30": float(holdout_p30),
        "holdout_ndcg30": float(holdout_ndcg30)
    },
    "individual_models": {
        "drug": {
            "oof_spearman": 0.8645,
            "holdout_spearman": 0.8710
        },
        "bilinear_v2": {
            "oof_spearman": 0.8298,
            "holdout_spearman": 0.8522
        }
    }
}

output_path = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260415_v4_ensemble_test/tuning/current_diversity.json")
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ 결과 저장: {output_path}")
print("=" * 80)
