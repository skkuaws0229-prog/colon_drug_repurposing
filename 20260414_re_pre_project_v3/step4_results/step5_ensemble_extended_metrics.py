"""
Step 5 앙상블 확장 메트릭 분석
- Diversity (모델 간 예측 상관)
- Ranking metrics (Precision@30, NDCG@30, MAP, EF@30)
- 개별 모델 대비 앙상블 성능 향상
"""

import numpy as np
import json
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score
import pandas as pd

print("=" * 80)
print("Step 5 앙상블 확장 메트릭 분석")
print("=" * 80)

# 데이터 로드
y_train = np.load('y_train.npy')

models_A = ['04', '02', '10']
models_B = ['04', '02', '10', '13']
model_names = {'04': 'CatBoost', '02': 'DART', '10': 'FlatMLP', '13': 'CrossAttention'}

seeds = [42, 123, 456, 789, 2026]

# 1. Diversity 분석 (모델 간 예측 상관)
print("\n" + "=" * 80)
print("1. 모델 간 Diversity 분석")
print("=" * 80)

# 각 시드에서 모델 간 상관 계산
print("\n[앙상블 A - 모델 간 Spearman 상관]")
diversity_A = []

for seed in seeds:
    preds = []
    for mid in models_A:
        pred = np.load(f'step5_seed{seed}_{mid}_oof.npy')
        preds.append(pred)

    # 상관 행렬 계산
    corr_matrix = np.corrcoef(preds)
    # 대각선 제외한 평균 상관
    mask = np.ones_like(corr_matrix, dtype=bool)
    np.fill_diagonal(mask, False)
    avg_corr = corr_matrix[mask].mean()
    diversity_A.append(avg_corr)

    print(f"Seed {seed}:")
    for i, mid1 in enumerate(models_A):
        for j, mid2 in enumerate(models_A):
            if i < j:
                print(f"  {model_names[mid1]} - {model_names[mid2]}: {corr_matrix[i,j]:.4f}")
    print(f"  평균 상관: {avg_corr:.4f}")

diversity_A_mean = np.mean(diversity_A)
print(f"\n앙상블 A 평균 diversity: {diversity_A_mean:.4f} (낮을수록 다양성 높음)")

print("\n[앙상블 B - 모델 간 Spearman 상관]")
diversity_B = []

for seed in seeds:
    preds = []
    for mid in models_B:
        pred = np.load(f'step5_seed{seed}_{mid}_oof.npy')
        preds.append(pred)

    corr_matrix = np.corrcoef(preds)
    mask = np.ones_like(corr_matrix, dtype=bool)
    np.fill_diagonal(mask, False)
    avg_corr = corr_matrix[mask].mean()
    diversity_B.append(avg_corr)

    print(f"Seed {seed}:")
    for i, mid1 in enumerate(models_B):
        for j, mid2 in enumerate(models_B):
            if i < j:
                print(f"  {model_names[mid1]} - {model_names[mid2]}: {corr_matrix[i,j]:.4f}")
    print(f"  평균 상관: {avg_corr:.4f}")

diversity_B_mean = np.mean(diversity_B)
print(f"\n앙상블 B 평균 diversity: {diversity_B_mean:.4f} (낮을수록 다양성 높음)")

# 2. Ranking Metrics 계산
print("\n" + "=" * 80)
print("2. Ranking Metrics (Top 30 기준)")
print("=" * 80)

def calculate_ranking_metrics(y_true, y_pred, k=30):
    """Ranking 메트릭 계산"""
    # Top k 인덱스
    top_k_pred = np.argsort(y_pred)[::-1][:k]
    top_k_true = np.argsort(y_true)[::-1][:k]

    # Precision@k
    precision = len(set(top_k_pred) & set(top_k_true)) / k

    # Recall@k
    total_relevant = len(top_k_true)
    recall = len(set(top_k_pred) & set(top_k_true)) / total_relevant if total_relevant > 0 else 0

    # NDCG@k
    # y_true를 relevance score로 사용
    y_true_sorted = y_true[top_k_pred]
    ideal_sorted = np.sort(y_true)[::-1][:k]

    dcg = np.sum((2**y_true_sorted - 1) / np.log2(np.arange(2, k + 2)))
    idcg = np.sum((2**ideal_sorted - 1) / np.log2(np.arange(2, k + 2)))
    ndcg = dcg / idcg if idcg > 0 else 0

    # Enrichment Factor @k
    # Random selection 대비 얼마나 더 좋은 약물을 선택했는지
    ef = (len(set(top_k_pred) & set(top_k_true)) / k) / (total_relevant / len(y_true))

    # MAP (Mean Average Precision)
    ap_sum = 0
    hits = 0
    for i, idx in enumerate(top_k_pred):
        if idx in top_k_true:
            hits += 1
            ap_sum += hits / (i + 1)
    map_score = ap_sum / total_relevant if total_relevant > 0 else 0

    return {
        'precision': precision,
        'recall': recall,
        'ndcg': ndcg,
        'ef': ef,
        'map': map_score
    }

# 앙상블 A 평균 예측값 로드
ens_A_eq = np.load('ensemble_A_equal_oof.npy')
ens_A_wt = np.load('ensemble_A_weighted_oof.npy')
ens_B_eq = np.load('ensemble_B_equal_oof.npy')
ens_B_wt = np.load('ensemble_B_weighted_oof.npy')

ranking_A_eq = calculate_ranking_metrics(y_train, ens_A_eq)
ranking_A_wt = calculate_ranking_metrics(y_train, ens_A_wt)
ranking_B_eq = calculate_ranking_metrics(y_train, ens_B_eq)
ranking_B_wt = calculate_ranking_metrics(y_train, ens_B_wt)

print("\n[앙상블 A - Equal Weight]")
for metric, value in ranking_A_eq.items():
    print(f"  {metric.upper()}: {value:.4f}")

print("\n[앙상블 A - Weighted]")
for metric, value in ranking_A_wt.items():
    print(f"  {metric.upper()}: {value:.4f}")

print("\n[앙상블 B - Equal Weight]")
for metric, value in ranking_B_eq.items():
    print(f"  {metric.upper()}: {value:.4f}")

print("\n[앙상블 B - Weighted]")
for metric, value in ranking_B_wt.items():
    print(f"  {metric.upper()}: {value:.4f}")

# 3. 개별 모델 대비 앙상블 성능 향상
print("\n" + "=" * 80)
print("3. 개별 모델 대비 앙상블 성능 향상")
print("=" * 80)

# 각 모델의 OOF Spearman (Step 5 결과에서)
individual_scores = {}
for mid in models_B:
    with open(f'step5_multiseed_{mid}_results.json', 'r') as f:
        result = json.load(f)
    individual_scores[mid] = result['cross_seed_stats']['oof_spearman_mean']

best_individual = max(individual_scores.values())
best_model = [k for k, v in individual_scores.items() if v == best_individual][0]

# 앙상블 OOF Spearman
with open('step5_ensemble_comprehensive_results.json', 'r') as f:
    ens_results = json.load(f)

ens_A_eq_sp = ens_results['ensemble_A']['equal_weight']['oof_spearman_mean']
ens_A_wt_sp = ens_results['ensemble_A']['weighted']['oof_spearman_mean']
ens_B_eq_sp = ens_results['ensemble_B']['equal_weight']['oof_spearman_mean']
ens_B_wt_sp = ens_results['ensemble_B']['weighted']['oof_spearman_mean']

print(f"\n개별 모델 최고 성능: {model_names[best_model]} (OOF Sp = {best_individual:.4f})")
print(f"\n앙상블 A Equal:    {ens_A_eq_sp:.4f} (Δ = {ens_A_eq_sp - best_individual:+.4f})")
print(f"앙상블 A Weighted: {ens_A_wt_sp:.4f} (Δ = {ens_A_wt_sp - best_individual:+.4f})")
print(f"앙상블 B Equal:    {ens_B_eq_sp:.4f} (Δ = {ens_B_eq_sp - best_individual:+.4f})")
print(f"앙상블 B Weighted: {ens_B_wt_sp:.4f} (Δ = {ens_B_wt_sp - best_individual:+.4f})")

improvement_A_eq = ens_A_eq_sp > best_individual
improvement_A_wt = ens_A_wt_sp > best_individual
improvement_B_eq = ens_B_eq_sp > best_individual
improvement_B_wt = ens_B_wt_sp > best_individual

print(f"\n앙상블이 개별 최고 모델보다 우수:")
print(f"  A Equal:    {'✓' if improvement_A_eq else '✗'}")
print(f"  A Weighted: {'✓' if improvement_A_wt else '✗'}")
print(f"  B Equal:    {'✓' if improvement_B_eq else '✗'}")
print(f"  B Weighted: {'✓' if improvement_B_wt else '✗'}")

# 4. 가중치 쏠림 분석
print("\n" + "=" * 80)
print("4. 가중치 쏠림 분석")
print("=" * 80)

weights_A = ens_results['ensemble_A']['weights_normalized']
weights_B = ens_results['ensemble_B']['weights_normalized']

# Entropy 계산 (균일 분포에서 얼마나 멀어졌는지)
def calculate_entropy(weights):
    weights_array = np.array(list(weights.values()))
    entropy = -np.sum(weights_array * np.log(weights_array + 1e-10))
    max_entropy = np.log(len(weights))
    normalized_entropy = entropy / max_entropy
    return normalized_entropy

entropy_A = calculate_entropy(weights_A)
entropy_B = calculate_entropy(weights_B)

print(f"\n앙상블 A 가중치 분포:")
for mid, weight in weights_A.items():
    print(f"  {model_names[mid]}: {weight:.4f}")
print(f"  Entropy: {entropy_A:.4f} (1.0 = 완전 균일)")

print(f"\n앙상블 B 가중치 분포:")
for mid, weight in weights_B.items():
    print(f"  {model_names[mid]}: {weight:.4f}")
print(f"  Entropy: {entropy_B:.4f} (1.0 = 완전 균일)")

# 결과 저장
extended_results = {
    "diversity": {
        "ensemble_A": {
            "mean_correlation": float(diversity_A_mean),
            "seed_correlations": [float(x) for x in diversity_A]
        },
        "ensemble_B": {
            "mean_correlation": float(diversity_B_mean),
            "seed_correlations": [float(x) for x in diversity_B]
        }
    },
    "ranking_metrics": {
        "ensemble_A_equal": {k: float(v) for k, v in ranking_A_eq.items()},
        "ensemble_A_weighted": {k: float(v) for k, v in ranking_A_wt.items()},
        "ensemble_B_equal": {k: float(v) for k, v in ranking_B_eq.items()},
        "ensemble_B_weighted": {k: float(v) for k, v in ranking_B_wt.items()}
    },
    "improvement_over_best": {
        "best_individual_model": model_names[best_model],
        "best_individual_score": float(best_individual),
        "ensemble_A_equal": {
            "score": float(ens_A_eq_sp),
            "delta": float(ens_A_eq_sp - best_individual),
            "improved": improvement_A_eq
        },
        "ensemble_A_weighted": {
            "score": float(ens_A_wt_sp),
            "delta": float(ens_A_wt_sp - best_individual),
            "improved": improvement_A_wt
        },
        "ensemble_B_equal": {
            "score": float(ens_B_eq_sp),
            "delta": float(ens_B_eq_sp - best_individual),
            "improved": improvement_B_eq
        },
        "ensemble_B_weighted": {
            "score": float(ens_B_wt_sp),
            "delta": float(ens_B_wt_sp - best_individual),
            "improved": improvement_B_wt
        }
    },
    "weight_distribution": {
        "ensemble_A": {
            "weights": weights_A,
            "entropy": float(entropy_A)
        },
        "ensemble_B": {
            "weights": weights_B,
            "entropy": float(entropy_B)
        }
    }
}

with open('step5_ensemble_extended_metrics.json', 'w') as f:
    json.dump(extended_results, f, indent=2)

print("\n" + "=" * 80)
print("확장 메트릭 저장 완료: step5_ensemble_extended_metrics.json")
print("=" * 80)
