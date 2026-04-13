#!/usr/bin/env python3
"""
Step 3 Unseen Drug 앙상블 계산
균등 가중 + Spearman 가중 두 가지 방식
"""
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import ndcg_score

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 3 Unseen Drug 앙상블 계산")
print("="*80)

# Load y_test (unseen drug labels)
features_df = pd.read_parquet("../features_slim.parquet")
y_all = np.load("y_train.npy")
drug_ids = features_df['canonical_drug_id'].values

# Recreate unseen drug split (same seed as Step 3)
np.random.seed(42)
unique_drugs = np.unique(drug_ids)
n_unseen = int(len(unique_drugs) * 0.25)
unseen_drugs = np.random.choice(unique_drugs, size=n_unseen, replace=False)
unseen_mask = np.isin(drug_ids, unseen_drugs)
y_test = y_all[unseen_mask]

print(f"Test samples (unseen drugs): {len(y_test)}\n")

# Model IDs and their Unseen Drug Spearman scores
models = {
    1: {'name': 'LightGBM', 'sp': 0.3243},
    2: {'name': 'DART', 'sp': 0.3469},
    4: {'name': 'CatBoost', 'sp': 0.4813},
    10: {'name': 'FlatMLP', 'sp': 0.3666},
    12: {'name': 'FT-Transformer', 'sp': 0.3852},
    13: {'name': 'CrossAttention', 'sp': 0.3695}
}

# Random 5CV baseline
baseline_values = {
    1: 0.8493,
    2: 0.8415,
    4: 0.8624,
    10: 0.8278,
    12: 0.8057,
    13: 0.8238
}

# Load predictions
predictions = {}
for model_id in models.keys():
    pred_file = f"step3_unseen_drug_{model_id:02d}_predictions.npy"
    predictions[model_id] = np.load(pred_file)
    print(f"Loaded: {pred_file} - shape {predictions[model_id].shape}")

def calculate_metrics(y_true, y_pred):
    """회귀 지표"""
    valid_mask = ~np.isnan(y_pred)
    y_true_valid = y_true[valid_mask]
    y_pred_valid = y_pred[valid_mask]

    if len(y_true_valid) == 0:
        return {m: np.nan for m in ['spearman', 'rmse', 'mae', 'median_ae', 'p95_error', 'kendall', 'pearson', 'r2']}

    errors = np.abs(y_true_valid - y_pred_valid)

    return {
        'spearman': spearmanr(y_true_valid, y_pred_valid)[0],
        'rmse': np.sqrt(mean_squared_error(y_true_valid, y_pred_valid)),
        'mae': mean_absolute_error(y_true_valid, y_pred_valid),
        'median_ae': median_absolute_error(y_true_valid, y_pred_valid),
        'p95_error': np.percentile(errors, 95),
        'kendall': kendalltau(y_true_valid, y_pred_valid)[0],
        'pearson': pearsonr(y_true_valid, y_pred_valid)[0],
        'r2': r2_score(y_true_valid, y_pred_valid)
    }

def calculate_ranking_metrics(y_true, y_pred, k=30):
    """Top-k ranking 지표"""
    valid_mask = ~np.isnan(y_pred)
    y_true_valid = y_true[valid_mask]
    y_pred_valid = y_pred[valid_mask]

    if len(y_true_valid) < k:
        return {'precision_at_30': np.nan, 'recall_at_30': np.nan, 'ndcg_at_30': np.nan, 'ef_at_30': np.nan}

    # Top-k predicted indices (most sensitive = lowest viability)
    top_k_idx = np.argsort(y_pred_valid)[:k]

    # Define "sensitive" as below median
    threshold = np.median(y_true_valid)
    is_sensitive = y_true_valid < threshold

    # Precision@k
    precision_at_k = np.mean(is_sensitive[top_k_idx])

    # Recall@k
    total_sensitive = np.sum(is_sensitive)
    recall_at_k = np.sum(is_sensitive[top_k_idx]) / total_sensitive if total_sensitive > 0 else 0.0

    # NDCG@k
    relevance = -y_true_valid
    relevance_normalized = relevance - relevance.min()
    true_relevance = relevance_normalized.reshape(1, -1)
    pred_relevance = relevance_normalized[np.argsort(y_pred_valid)].reshape(1, -1)
    ndcg_k = ndcg_score(true_relevance[:, :k], pred_relevance[:, :k])

    # Enrichment Factor@k
    baseline_rate = total_sensitive / len(y_true_valid)
    ef_k = precision_at_k / baseline_rate if baseline_rate > 0 else 0.0

    return {
        'precision_at_30': precision_at_k,
        'recall_at_30': recall_at_k,
        'ndcg_at_30': ndcg_k,
        'ef_at_30': ef_k
    }

# === 1. 균등 가중 앙상블 ===
print("\n" + "="*80)
print("1. 균등 가중 앙상블 (Equal Weight)")
print("="*80)

equal_weight_pred = np.zeros_like(y_test)
for model_id in models.keys():
    equal_weight_pred += predictions[model_id] / 6.0

equal_reg_metrics = calculate_metrics(y_test, equal_weight_pred)
equal_rank_metrics = calculate_ranking_metrics(y_test, equal_weight_pred, k=30)

print(f"\n  Regression:")
print(f"    Spearman: {equal_reg_metrics['spearman']:.4f}")
print(f"    RMSE: {equal_reg_metrics['rmse']:.4f}")
print(f"    MAE: {equal_reg_metrics['mae']:.4f}")
print(f"  Ranking:")
print(f"    Precision@30: {equal_rank_metrics['precision_at_30']:.4f}")
print(f"    Recall@30: {equal_rank_metrics['recall_at_30']:.4f}")
print(f"    NDCG@30: {equal_rank_metrics['ndcg_at_30']:.4f}")
print(f"    EF@30: {equal_rank_metrics['ef_at_30']:.4f}")

# Baseline
equal_baseline = np.mean(list(baseline_values.values()))
equal_drop = equal_baseline - equal_reg_metrics['spearman']

equal_results = {
    'model': 'Ensemble_EqualWeight',
    'model_id': 'E1',
    'stage': 'step3_unseen_drug',
    'ensemble_type': 'equal_weight',
    'weights': {str(k): 1/6 for k in models.keys()},
    'data_split': {
        'total_drugs': int(len(unique_drugs)),
        'unseen_drugs': int(n_unseen),
        'test_samples': int(len(y_test))
    },
    'regression_metrics': equal_reg_metrics,
    'ranking_metrics': equal_rank_metrics,
    'random_5cv_spearman': equal_baseline,
    'drop_from_random': equal_drop
}

# === 2. Spearman 가중 앙상블 ===
print("\n" + "="*80)
print("2. Spearman 가중 앙상블 (Spearman-Weighted)")
print("="*80)

# Calculate weights based on Unseen Drug Spearman
spearman_scores = np.array([models[mid]['sp'] for mid in models.keys()])
spearman_weights = spearman_scores / spearman_scores.sum()

print("\n  가중치:")
for i, model_id in enumerate(models.keys()):
    print(f"    {models[model_id]['name']:20s} (Model {model_id:02d}): {spearman_weights[i]:.4f}")

spearman_weight_pred = np.zeros_like(y_test)
for i, model_id in enumerate(models.keys()):
    spearman_weight_pred += predictions[model_id] * spearman_weights[i]

spearman_reg_metrics = calculate_metrics(y_test, spearman_weight_pred)
spearman_rank_metrics = calculate_ranking_metrics(y_test, spearman_weight_pred, k=30)

print(f"\n  Regression:")
print(f"    Spearman: {spearman_reg_metrics['spearman']:.4f}")
print(f"    RMSE: {spearman_reg_metrics['rmse']:.4f}")
print(f"    MAE: {spearman_reg_metrics['mae']:.4f}")
print(f"  Ranking:")
print(f"    Precision@30: {spearman_rank_metrics['precision_at_30']:.4f}")
print(f"    Recall@30: {spearman_rank_metrics['recall_at_30']:.4f}")
print(f"    NDCG@30: {spearman_rank_metrics['ndcg_at_30']:.4f}")
print(f"    EF@30: {spearman_rank_metrics['ef_at_30']:.4f}")

# Baseline
weighted_baseline = sum(baseline_values[mid] * spearman_weights[i] for i, mid in enumerate(models.keys()))
weighted_drop = weighted_baseline - spearman_reg_metrics['spearman']

spearman_results = {
    'model': 'Ensemble_SpearmanWeighted',
    'model_id': 'E2',
    'stage': 'step3_unseen_drug',
    'ensemble_type': 'spearman_weighted',
    'weights': {str(k): float(spearman_weights[i]) for i, k in enumerate(models.keys())},
    'data_split': {
        'total_drugs': int(len(unique_drugs)),
        'unseen_drugs': int(n_unseen),
        'test_samples': int(len(y_test))
    },
    'regression_metrics': spearman_reg_metrics,
    'ranking_metrics': spearman_rank_metrics,
    'random_5cv_spearman': weighted_baseline,
    'drop_from_random': weighted_drop
}

# Save results
with open('step3_unseen_drug_ensemble_equal_results.json', 'w') as f:
    json.dump(equal_results, f, indent=2)
print(f"\n✓ 저장: step3_unseen_drug_ensemble_equal_results.json")

with open('step3_unseen_drug_ensemble_weighted_results.json', 'w') as f:
    json.dump(spearman_results, f, indent=2)
print(f"✓ 저장: step3_unseen_drug_ensemble_weighted_results.json")

# Save predictions
np.save('step3_unseen_drug_ensemble_equal_predictions.npy', equal_weight_pred)
np.save('step3_unseen_drug_ensemble_weighted_predictions.npy', spearman_weight_pred)

print("\n" + "="*80)
print("Step 3 앙상블 계산 완료!")
print("="*80)
print(f"\n비교:")
print(f"  균등 가중:      Sp {equal_reg_metrics['spearman']:.4f}, RMSE {equal_reg_metrics['rmse']:.4f}, P@30 {equal_rank_metrics['precision_at_30']:.4f}")
print(f"  Spearman 가중:  Sp {spearman_reg_metrics['spearman']:.4f}, RMSE {spearman_reg_metrics['rmse']:.4f}, P@30 {spearman_rank_metrics['precision_at_30']:.4f}")
