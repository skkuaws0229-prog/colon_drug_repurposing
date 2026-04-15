#!/usr/bin/env python3
"""
CatBoost vs FT-Transformer vs TabNet 상관 측정
"""
import numpy as np
from scipy.stats import pearsonr, spearmanr
from pathlib import Path
import json

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 80)
print("CatBoost vs FT-Transformer vs TabNet 상관 측정")
print("=" * 80)

# OOF predictions 로드
catboost_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
ftt_oof = np.load(step4_dir / "model_12_fttransformer_oof.npy")
tabnet_oof = np.load(step4_dir / "model_11_oof.npy")

print(f"\nCatBoost OOF shape:      {catboost_oof.shape}")
print(f"FT-Transformer OOF shape: {ftt_oof.shape}")
print(f"TabNet OOF shape:         {tabnet_oof.shape}")

# 길이 맞추기
min_len = min(len(catboost_oof), len(ftt_oof), len(tabnet_oof))
catboost_oof = catboost_oof[:min_len]
ftt_oof = ftt_oof[:min_len]
tabnet_oof = tabnet_oof[:min_len]

print(f"비교 샘플 수: {min_len}")

models = {
    'CatBoost': catboost_oof,
    'FT-Transformer': ftt_oof,
    'TabNet': tabnet_oof
}

# ============================================================================
# 1. Pearson/Spearman 상관 행렬
# ============================================================================
print("\n[1] 상관 행렬")
print("-" * 80)

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
print(f"{'':20s} {'CatBoost':>15s} {'FT-Transformer':>15s} {'TabNet':>15s}")
for name1 in models.keys():
    values = [pearson_matrix[name1][name2] for name2 in models.keys()]
    print(f"{name1:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

print("\nSpearman 상관:")
print(f"{'':20s} {'CatBoost':>15s} {'FT-Transformer':>15s} {'TabNet':>15s}")
for name1 in models.keys():
    values = [spearman_matrix[name1][name2] for name2 in models.keys()]
    print(f"{name1:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

# 평균 상관 (off-diagonal)
pearson_off_diag = []
spearman_off_diag = []

for i, (name1, pred1) in enumerate(models.items()):
    for j, (name2, pred2) in enumerate(models.items()):
        if i < j:
            pearson_off_diag.append(pearson_matrix[name1][name2])
            spearman_off_diag.append(spearman_matrix[name1][name2])

avg_pearson = np.mean(pearson_off_diag)
avg_spearman = np.mean(spearman_off_diag)

print(f"\n평균 Pearson 상관:  {avg_pearson:.4f}")
print(f"평균 Spearman 상관: {avg_spearman:.4f}")

# ============================================================================
# 2. Top-30 Overlap
# ============================================================================
print("\n[2] Top-30 Overlap (Jaccard)")
print("-" * 80)

top30_sets = {}
for name, pred in models.items():
    top30_sets[name] = set(np.argsort(pred)[:30])

overlap_matrix = {}
for name1 in models.keys():
    overlap_matrix[name1] = {}
    for name2 in models.keys():
        if name1 == name2:
            overlap_matrix[name1][name2] = 1.0
        else:
            set1 = top30_sets[name1]
            set2 = top30_sets[name2]
            jaccard = len(set1 & set2) / len(set1 | set2)
            overlap_matrix[name1][name2] = float(jaccard)

print(f"{'':20s} {'CatBoost':>15s} {'FT-Transformer':>15s} {'TabNet':>15s}")
for name1 in models.keys():
    values = [overlap_matrix[name1][name2] for name2 in models.keys()]
    print(f"{name1:20s} {values[0]:>15.4f} {values[1]:>15.4f} {values[2]:>15.4f}")

# 쌍별 상세
print("\n쌍별 Top-30 Overlap:")
for i, name1 in enumerate(models.keys()):
    for j, name2 in enumerate(models.keys()):
        if i < j:
            jaccard = overlap_matrix[name1][name2]
            overlap_count = len(top30_sets[name1] & top30_sets[name2])
            print(f"  {name1:20s} vs {name2:20s}: {jaccard:.4f} ({overlap_count}/30)")

avg_top30_overlap = np.mean([overlap_matrix[n1][n2]
                              for i, n1 in enumerate(models.keys())
                              for j, n2 in enumerate(models.keys()) if i < j])

print(f"\n평균 Top-30 Jaccard: {avg_top30_overlap:.4f}")

# ============================================================================
# 3. Diversity 판정
# ============================================================================
print("\n[3] Diversity 판정")
print("-" * 80)

print(f"평균 Pearson 상관:  {avg_pearson:.4f}")
print(f"평균 Spearman 상관: {avg_spearman:.4f}")
print(f"평균 Top-30 Jaccard: {avg_top30_overlap:.4f}")

if avg_pearson < 0.90:
    diversity_verdict = "✅ 우수 (< 0.90)"
elif avg_pearson < 0.95:
    diversity_verdict = "⚠️  보통 (0.90 ~ 0.95)"
else:
    diversity_verdict = "❌ 부족 (≥ 0.95)"

print(f"\nDiversity 판정: {diversity_verdict}")

# 기존 조합과 비교
print("\n기존 조합 (CatBoost+FlatMLP+CrossAttention) 대비:")
print(f"  기존 평균 상관: 0.9680")
print(f"  새 조합 평균:   {avg_pearson:.4f}")
print(f"  차이:          {avg_pearson - 0.9680:+.4f}")

if avg_pearson < 0.9680:
    print(f"  → ✅ Diversity 개선!")
else:
    print(f"  → ❌ Diversity 악화")

# ============================================================================
# 저장
# ============================================================================
print("\n[4] 결과 저장")
print("-" * 80)

results = {
    "models": list(models.keys()),
    "sample_count": int(min_len),
    "pearson_matrix": pearson_matrix,
    "spearman_matrix": spearman_matrix,
    "top30_overlap_matrix": overlap_matrix,
    "averages": {
        "pearson": float(avg_pearson),
        "spearman": float(avg_spearman),
        "top30_jaccard": float(avg_top30_overlap)
    },
    "diversity_verdict": diversity_verdict,
    "comparison_to_previous": {
        "previous_avg_corr": 0.9680,
        "new_avg_corr": float(avg_pearson),
        "difference": float(avg_pearson - 0.9680),
        "improved": bool(avg_pearson < 0.9680)
    }
}

output_json = output_dir / "catboost_ftt_tabnet_correlation.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ JSON: {output_json}")

# Summary
summary_path = output_dir / "catboost_ftt_tabnet_summary.txt"
with open(summary_path, "w") as f:
    f.write("=" * 80 + "\n")
    f.write("CatBoost vs FT-Transformer vs TabNet 상관 측정\n")
    f.write("=" * 80 + "\n\n")

    f.write("평균 상관:\n")
    f.write(f"  Pearson:  {avg_pearson:.4f}\n")
    f.write(f"  Spearman: {avg_spearman:.4f}\n")
    f.write(f"  Top-30 Jaccard: {avg_top30_overlap:.4f}\n\n")

    f.write(f"Diversity 판정: {diversity_verdict}\n\n")

    f.write("기존 조합 대비:\n")
    f.write(f"  기존 (CatBoost+FlatMLP+CrossAttention): 0.9680\n")
    f.write(f"  새 조합 (CatBoost+FTT+TabNet):          {avg_pearson:.4f}\n")
    f.write(f"  차이: {avg_pearson - 0.9680:+.4f}\n")

print(f"✓ Summary: {summary_path}")

print("\n측정 완료!")
