#!/usr/bin/env python3
"""
CatBoost Feature Subset 상관 분석

3개 모델 간 상관 행렬:
- CatBoost-Full vs CatBoost-Gene
- CatBoost-Full vs CatBoost-Drug
- CatBoost-Gene vs CatBoost-Drug
"""
import numpy as np
from scipy.stats import pearsonr, spearmanr
from pathlib import Path
import json

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
subset_dir = base_dir / "20260415_v4_ensemble_test/catboost_subset"
output_dir = subset_dir / "correlation"

print("=" * 100)
print("CatBoost Feature Subset 상관 분석")
print("=" * 100)

# ============================================================================
# OOF 예측 로드
# ============================================================================
print("\n[1] OOF 예측 로드")
print("-" * 100)

catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
catboost_gene_oof = np.load(subset_dir / "catboost_gene/catboost_gene_oof.npy")
catboost_drug_oof = np.load(subset_dir / "catboost_drug/catboost_drug_oof.npy")

print(f"CatBoost-Full OOF shape: {catboost_full_oof.shape}")
print(f"CatBoost-Gene OOF shape: {catboost_gene_oof.shape}")
print(f"CatBoost-Drug OOF shape: {catboost_drug_oof.shape}")

models = {
    'CatBoost-Full': catboost_full_oof,
    'CatBoost-Gene': catboost_gene_oof,
    'CatBoost-Drug': catboost_drug_oof
}

# ============================================================================
# 상관 행렬 계산
# ============================================================================
print("\n[2] 상관 행렬")
print("-" * 100)

pearson_matrix = {}
spearman_matrix = {}

for name1, pred1 in models.items():
    pearson_matrix[name1] = {}
    spearman_matrix[name1] = {}
    for name2, pred2 in models.items():
        if name1 == name2:
            pearson_matrix[name1][name2] = 1.0
            spearman_matrix[name1][name2] = 1.0
        else:
            p_corr = pearsonr(pred1, pred2)[0]
            s_corr = spearmanr(pred1, pred2)[0]
            pearson_matrix[name1][name2] = float(p_corr)
            spearman_matrix[name1][name2] = float(s_corr)

print("\nPearson 상관:")
print(f"{'':20s} {'Full':>15s} {'Gene':>15s} {'Drug':>15s}")
print("-" * 70)
for name1 in models.keys():
    values = [pearson_matrix[name1][name2] for name2 in models.keys()]
    name_short = name1.replace("CatBoost-", "")
    print(f"{name_short:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

print("\nSpearman 상관:")
print(f"{'':20s} {'Full':>15s} {'Gene':>15s} {'Drug':>15s}")
print("-" * 70)
for name1 in models.keys():
    values = [spearman_matrix[name1][name2] for name2 in models.keys()]
    name_short = name1.replace("CatBoost-", "")
    print(f"{name_short:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

# ============================================================================
# Top-K Overlap (Jaccard)
# ============================================================================
print("\n[3] Top-30 Overlap (Jaccard)")
print("-" * 100)

def jaccard_topk(pred1, pred2, k):
    """Top-k Jaccard similarity"""
    top_k1 = set(np.argsort(pred1)[:k])
    top_k2 = set(np.argsort(pred2)[:k])
    intersection = len(top_k1 & top_k2)
    union = len(top_k1 | top_k2)
    jaccard = intersection / union
    return jaccard, intersection

top30_matrix = {}
for name1 in models.keys():
    top30_matrix[name1] = {}
    for name2 in models.keys():
        if name1 == name2:
            top30_matrix[name1][name2] = 1.0
        else:
            jaccard, overlap = jaccard_topk(models[name1], models[name2], 30)
            top30_matrix[name1][name2] = float(jaccard)

print(f"{'':20s} {'Full':>15s} {'Gene':>15s} {'Drug':>15s}")
print("-" * 70)
for name1 in models.keys():
    values = [top30_matrix[name1][name2] for name2 in models.keys()]
    name_short = name1.replace("CatBoost-", "")
    print(f"{name_short:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

# 쌍별 상세
print("\n쌍별 Top-30 Overlap:")
model_names = list(models.keys())
for i in range(len(model_names)):
    for j in range(i+1, len(model_names)):
        name1, name2 = model_names[i], model_names[j]
        jaccard = top30_matrix[name1][name2]
        overlap_count = int(jaccard * 30)  # Approximate
        print(f"  {name1:20s} vs {name2:20s}: {jaccard:.4f} (~{overlap_count}/30)")

# ============================================================================
# Diversity 판정
# ============================================================================
print("\n[4] Diversity 판정")
print("-" * 100)

# Off-diagonal 평균
pearson_off_diag = []
spearman_off_diag = []

for i, name1 in enumerate(model_names):
    for j, name2 in enumerate(model_names):
        if i < j:
            pearson_off_diag.append(pearson_matrix[name1][name2])
            spearman_off_diag.append(spearman_matrix[name1][name2])

avg_pearson = np.mean(pearson_off_diag)
avg_spearman = np.mean(spearman_off_diag)
avg_top30 = np.mean([top30_matrix[model_names[i]][model_names[j]]
                      for i in range(len(model_names))
                      for j in range(i+1, len(model_names))])

print(f"평균 Pearson 상관:  {avg_pearson:.4f}")
print(f"평균 Spearman 상관: {avg_spearman:.4f}")
print(f"평균 Top-30 Jaccard: {avg_top30:.4f}")

if avg_spearman < 0.90:
    diversity_verdict = "✅ 우수 (< 0.90)"
elif avg_spearman < 0.95:
    diversity_verdict = "⚠️  보통 (0.90 ~ 0.95)"
else:
    diversity_verdict = "❌ 부족 (≥ 0.95)"

print(f"\nDiversity 판정: {diversity_verdict}")

# ============================================================================
# 저장
# ============================================================================
print("\n[5] 결과 저장")
print("-" * 100)

output_dir.mkdir(parents=True, exist_ok=True)

results = {
    "models": list(models.keys()),
    "sample_count": len(catboost_full_oof),
    "pearson_matrix": pearson_matrix,
    "spearman_matrix": spearman_matrix,
    "top30_overlap_matrix": top30_matrix,
    "averages": {
        "pearson": float(avg_pearson),
        "spearman": float(avg_spearman),
        "top30_jaccard": float(avg_top30)
    },
    "diversity_verdict": diversity_verdict
}

# 3model correlation matrix (필수!)
output_json = output_dir / "3model_correlation_matrix.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ JSON: {output_json}")

# Top-30 overlap details
top30_details = {}
for i, name1 in enumerate(model_names):
    for j, name2 in enumerate(model_names):
        if i < j:
            jaccard, overlap = jaccard_topk(models[name1], models[name2], 30)
            top30_details[f"{name1}_vs_{name2}"] = {
                "jaccard": float(jaccard),
                "overlap_count": int(overlap),
                "total": 30
            }

top30_json = output_dir / "top30_overlap.json"
with open(top30_json, "w") as f:
    json.dump(top30_details, f, indent=2)

print(f"✓ Top-30: {top30_json}")

print("\n" + "=" * 100)
print("Phase 2/3 완료: 상관 분석 완료")
print("=" * 100)
