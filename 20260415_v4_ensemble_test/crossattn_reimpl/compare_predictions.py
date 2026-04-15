#!/usr/bin/env python3
"""
FlatMLP vs Real CrossAttention 예측값 비교
"""
import numpy as np
from scipy.stats import pearsonr, spearmanr
from pathlib import Path
import json

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"

print("=" * 80)
print("FlatMLP vs Real CrossAttention 예측값 비교")
print("=" * 80)

# OOF predictions 로드
flatmlp_oof = np.load(step4_dir / "model_10_oof.npy")
new_crossattn_oof = np.load(output_dir / "real_crossattention_oof.npy")

print(f"\nFlatMLP OOF shape:        {flatmlp_oof.shape}")
print(f"New CrossAttention shape: {new_crossattn_oof.shape}")

# 길이 맞추기 (CV split이 다를 수 있음)
min_len = min(len(flatmlp_oof), len(new_crossattn_oof))
flatmlp_oof = flatmlp_oof[:min_len]
new_crossattn_oof = new_crossattn_oof[:min_len]

print(f"비교 샘플 수: {min_len}")

# ============================================================================
# 예측값 상관 계산
# ============================================================================
print("\n[1] 예측값 상관")
print("-" * 80)

pearson_corr, pearson_pval = pearsonr(flatmlp_oof, new_crossattn_oof)
spearman_corr, spearman_pval = spearmanr(flatmlp_oof, new_crossattn_oof)

print(f"Pearson correlation:  {pearson_corr:.6f} (p-value: {pearson_pval:.2e})")
print(f"Spearman correlation: {spearman_corr:.6f} (p-value: {spearman_pval:.2e})")

# 기존 비교
print(f"\n기존 (FlatMLP vs 가짜 CrossAttention): 0.9848")
print(f"새로운 (FlatMLP vs 진짜 CrossAttention): {spearman_corr:.4f}")
print(f"개선: {0.9848 - spearman_corr:.4f} (낮을수록 좋음)")

# ============================================================================
# 차이 분석
# ============================================================================
print("\n[2] 예측값 차이 분석")
print("-" * 80)

abs_diff = np.abs(flatmlp_oof - new_crossattn_oof)
max_diff = np.max(abs_diff)
mean_diff = np.mean(abs_diff)
median_diff = np.median(abs_diff)

print(f"Max absolute diff:    {max_diff:.6f}")
print(f"Mean absolute diff:   {mean_diff:.6f}")
print(f"Median absolute diff: {median_diff:.6f}")

# 기존 비교
print(f"\n기존 Mean abs diff: 0.2777")
print(f"새로운 Mean abs diff: {mean_diff:.4f}")
print(f"개선: {mean_diff - 0.2777:.4f} (높을수록 다름)")

# ============================================================================
# Top-K Overlap
# ============================================================================
print("\n[3] Top-K Overlap (Jaccard)")
print("-" * 80)

# Top-30
top30_flatmlp = set(np.argsort(flatmlp_oof)[:30])
top30_new = set(np.argsort(new_crossattn_oof)[:30])
jaccard_30 = len(top30_flatmlp & top30_new) / len(top30_flatmlp | top30_new)
overlap_30 = len(top30_flatmlp & top30_new)

print(f"Top-30 Jaccard: {jaccard_30:.4f} ({overlap_30}/30 일치)")

# Top-50
top50_flatmlp = set(np.argsort(flatmlp_oof)[:50])
top50_new = set(np.argsort(new_crossattn_oof)[:50])
jaccard_50 = len(top50_flatmlp & top50_new) / len(top50_flatmlp | top50_new)
overlap_50 = len(top50_flatmlp & top50_new)

print(f"Top-50 Jaccard: {jaccard_50:.4f} ({overlap_50}/50 일치)")

# 기존 비교
print(f"\n기존 Top-30 Jaccard: 0.3953 (17/30)")
print(f"새로운 Top-30 Jaccard: {jaccard_30:.4f} ({overlap_30}/30)")
print(f"변화: {jaccard_30 - 0.3953:.4f} (낮을수록 다양함)")

# ============================================================================
# 목표 달성 여부
# ============================================================================
print("\n[4] 목표 달성 여부")
print("=" * 80)

goals = {
    "Spearman < 0.95": spearman_corr < 0.95,
    "Top-30 Jaccard < 0.6": jaccard_30 < 0.6,
    "Spearman 개선 (0.9848 대비)": spearman_corr < 0.9848,
    "Mean diff 증가 (0.2777 대비)": mean_diff > 0.2777
}

for goal, achieved in goals.items():
    status = "✅ 달성" if achieved else "❌ 미달성"
    print(f"{goal:40s}: {status}")

all_achieved = all(goals.values())
verdict = "✅ 모든 목표 달성!" if all_achieved else "⚠️  일부 목표 미달성"

print(f"\n최종 판정: {verdict}")

# ============================================================================
# 저장
# ============================================================================
results = {
    "comparison": "FlatMLP vs Real CrossAttention",
    "samples": int(min_len),
    "correlations": {
        "pearson": float(pearson_corr),
        "spearman": float(spearman_corr),
        "old_spearman": 0.9848,
        "improvement": float(0.9848 - spearman_corr)
    },
    "differences": {
        "max_abs_diff": float(max_diff),
        "mean_abs_diff": float(mean_diff),
        "median_abs_diff": float(median_diff),
        "old_mean_abs_diff": 0.2777,
        "improvement": float(mean_diff - 0.2777)
    },
    "overlap": {
        "top30_jaccard": float(jaccard_30),
        "top30_overlap": int(overlap_30),
        "top50_jaccard": float(jaccard_50),
        "top50_overlap": int(overlap_50),
        "old_top30_jaccard": 0.3953,
        "improvement": float(jaccard_30 - 0.3953)
    },
    "goals": {k: bool(v) for k, v in goals.items()},
    "verdict": verdict
}

output_json = output_dir / "flatmlp_vs_new_crossattn_comparison.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n결과 저장: {output_json}")
print("\n비교 완료!")
