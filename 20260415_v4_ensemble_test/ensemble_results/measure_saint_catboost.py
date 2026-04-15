#!/usr/bin/env python3
"""
SAINT vs CatBoost 상관 측정
"""
import numpy as np
from scipy.stats import pearsonr, spearmanr
from pathlib import Path
import json

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
saint_dir = base_dir / "20260415_v4_ensemble_test/new_models/saint"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 80)
print("SAINT vs CatBoost 상관 측정")
print("=" * 80)

# OOF predictions 로드
catboost_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
saint_oof = np.load(saint_dir / "saint_oof.npy")

print(f"\nCatBoost OOF shape: {catboost_oof.shape}")
print(f"SAINT OOF shape:    {saint_oof.shape}")

# 길이 맞추기
min_len = min(len(catboost_oof), len(saint_oof))
catboost_oof = catboost_oof[:min_len]
saint_oof = saint_oof[:min_len]

print(f"비교 샘플 수: {min_len}")

# ============================================================================
# 1. Pearson/Spearman 상관
# ============================================================================
print("\n[1] 상관 계수")
print("-" * 80)

pearson_corr, pearson_pval = pearsonr(catboost_oof, saint_oof)
spearman_corr, spearman_pval = spearmanr(catboost_oof, saint_oof)

print(f"Pearson correlation:  {pearson_corr:.4f} (p-value: {pearson_pval:.2e})")
print(f"Spearman correlation: {spearman_corr:.4f} (p-value: {spearman_pval:.2e})")

# ============================================================================
# 2. Top-K Overlap (Jaccard)
# ============================================================================
print("\n[2] Top-K Overlap (Jaccard)")
print("-" * 80)

def jaccard_topk(pred1, pred2, k):
    """Top-k Jaccard similarity"""
    top_k1 = set(np.argsort(pred1)[:k])
    top_k2 = set(np.argsort(pred2)[:k])
    intersection = len(top_k1 & top_k2)
    union = len(top_k1 | top_k2)
    jaccard = intersection / union
    return jaccard, intersection

top30_jaccard, top30_overlap = jaccard_topk(catboost_oof, saint_oof, 30)
top50_jaccard, top50_overlap = jaccard_topk(catboost_oof, saint_oof, 50)

print(f"Top-30 Jaccard: {top30_jaccard:.4f} ({top30_overlap}/30 overlap)")
print(f"Top-50 Jaccard: {top50_jaccard:.4f} ({top50_overlap}/50 overlap)")

# ============================================================================
# 3. Diversity 판정
# ============================================================================
print("\n[3] Diversity 판정")
print("-" * 80)

print(f"Pearson correlation:  {pearson_corr:.4f}")
print(f"Spearman correlation: {spearman_corr:.4f}")
print(f"Top-30 Jaccard:       {top30_jaccard:.4f}")

if spearman_corr < 0.90:
    diversity_verdict = "✅ 우수 (< 0.90)"
elif spearman_corr < 0.95:
    diversity_verdict = "⚠️  보통 (0.90 ~ 0.95)"
else:
    diversity_verdict = "❌ 부족 (≥ 0.95)"

print(f"\nDiversity 판정: {diversity_verdict}")

# 기존 조합과 비교
print("\n기존 조합 (CatBoost+FlatMLP+CrossAttention) 대비:")
print(f"  기존 평균 상관: 0.9680")
print(f"  새 조합 (CatBoost+SAINT):   {spearman_corr:.4f}")
print(f"  차이:          {spearman_corr - 0.9680:+.4f}")

if spearman_corr < 0.9680:
    print(f"  → ✅ Diversity 개선!")
else:
    print(f"  → ❌ Diversity 악화")

# ============================================================================
# 저장
# ============================================================================
print("\n[4] 결과 저장")
print("-" * 80)

results = {
    "models": ["CatBoost", "SAINT"],
    "sample_count": int(min_len),
    "correlations": {
        "pearson": float(pearson_corr),
        "pearson_pvalue": float(pearson_pval),
        "spearman": float(spearman_corr),
        "spearman_pvalue": float(spearman_pval)
    },
    "top_k_overlap": {
        "top30_jaccard": float(top30_jaccard),
        "top30_overlap": int(top30_overlap),
        "top50_jaccard": float(top50_jaccard),
        "top50_overlap": int(top50_overlap)
    },
    "diversity_verdict": diversity_verdict,
    "comparison_to_previous": {
        "previous_avg_corr": 0.9680,
        "new_corr": float(spearman_corr),
        "difference": float(spearman_corr - 0.9680),
        "improved": bool(spearman_corr < 0.9680)
    }
}

output_json = output_dir / "saint_catboost_correlation.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ JSON: {output_json}")

# Summary
summary_path = output_dir / "saint_catboost_summary.txt"
with open(summary_path, "w") as f:
    f.write("=" * 80 + "\n")
    f.write("SAINT vs CatBoost 상관 측정\n")
    f.write("=" * 80 + "\n\n")

    f.write("상관 계수:\n")
    f.write(f"  Pearson:  {pearson_corr:.4f}\n")
    f.write(f"  Spearman: {spearman_corr:.4f}\n\n")

    f.write("Top-K Overlap:\n")
    f.write(f"  Top-30 Jaccard: {top30_jaccard:.4f} ({top30_overlap}/30)\n")
    f.write(f"  Top-50 Jaccard: {top50_jaccard:.4f} ({top50_overlap}/50)\n\n")

    f.write(f"Diversity 판정: {diversity_verdict}\n\n")

    f.write("기존 조합 대비:\n")
    f.write(f"  기존 (CatBoost+FlatMLP+CrossAttention): 0.9680\n")
    f.write(f"  새 조합 (CatBoost+SAINT):               {spearman_corr:.4f}\n")
    f.write(f"  차이: {spearman_corr - 0.9680:+.4f}\n")

print(f"✓ Summary: {summary_path}")

print("\n측정 완료!")
