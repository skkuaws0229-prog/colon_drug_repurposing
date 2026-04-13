#!/usr/bin/env python3
"""
Step 2 GroupKFold 앙상블 계산
균등 가중 + Spearman 가중 두 가지 방식
"""
import os
import json
import numpy as np
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 2 GroupKFold 앙상블 계산")
print("="*80)

# Load y_true
y = np.load("y_train.npy")

# Model IDs and their GroupKFold Spearman scores
models = {
    1: {'name': 'LightGBM', 'sp': 0.5153},
    2: {'name': 'DART', 'sp': 0.4974},
    4: {'name': 'CatBoost', 'sp': 0.4933},
    10: {'name': 'FlatMLP', 'sp': 0.5125},
    12: {'name': 'FT-Transformer', 'sp': 0.5275},
    13: {'name': 'CrossAttention', 'sp': 0.5142}
}

# Random 5CV baseline for ensemble (weighted average of individual baselines)
baseline_values = {
    1: 0.8493,
    2: 0.8415,
    4: 0.8624,
    10: 0.8278,
    12: 0.8057,
    13: 0.8238
}

# Load OOF predictions
oof_predictions = {}
for model_id in models.keys():
    oof_file = f"step2_groupkfold_{model_id:02d}_oof.npy"
    oof_predictions[model_id] = np.load(oof_file)
    print(f"Loaded: {oof_file} - shape {oof_predictions[model_id].shape}")

def calculate_metrics(y_true, y_pred):
    """전체 회귀 지표"""
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

# === 1. 균등 가중 앙상블 ===
print("\n" + "="*80)
print("1. 균등 가중 앙상블 (Equal Weight)")
print("="*80)

equal_weight_pred = np.zeros_like(y)
for model_id in models.keys():
    equal_weight_pred += oof_predictions[model_id] / 6.0

equal_metrics = calculate_metrics(y, equal_weight_pred)
print(f"\n  Spearman: {equal_metrics['spearman']:.4f}")
print(f"  RMSE: {equal_metrics['rmse']:.4f}")
print(f"  MAE: {equal_metrics['mae']:.4f}")

# Baseline for equal weight ensemble (simple average)
equal_baseline = np.mean(list(baseline_values.values()))
equal_drop = equal_baseline - equal_metrics['spearman']

equal_results = {
    'model': 'Ensemble_EqualWeight',
    'model_id': 'E1',
    'stage': 'step2_groupkfold',
    'ensemble_type': 'equal_weight',
    'weights': {str(k): 1/6 for k in models.keys()},
    'overall_metrics': equal_metrics,
    'random_5cv_spearman': equal_baseline,
    'drop_from_random': equal_drop
}

# === 2. Spearman 가중 앙상블 ===
print("\n" + "="*80)
print("2. Spearman 가중 앙상블 (Spearman-Weighted)")
print("="*80)

# Calculate weights based on GroupKFold Spearman
spearman_scores = np.array([models[mid]['sp'] for mid in models.keys()])
spearman_weights = spearman_scores / spearman_scores.sum()

print("\n  가중치:")
for i, model_id in enumerate(models.keys()):
    print(f"    {models[model_id]['name']:20s} (Model {model_id:02d}): {spearman_weights[i]:.4f}")

spearman_weight_pred = np.zeros_like(y)
for i, model_id in enumerate(models.keys()):
    spearman_weight_pred += oof_predictions[model_id] * spearman_weights[i]

spearman_metrics = calculate_metrics(y, spearman_weight_pred)
print(f"\n  Spearman: {spearman_metrics['spearman']:.4f}")
print(f"  RMSE: {spearman_metrics['rmse']:.4f}")
print(f"  MAE: {spearman_metrics['mae']:.4f}")

# Baseline for weighted ensemble (weighted average of baselines)
weighted_baseline = sum(baseline_values[mid] * spearman_weights[i] for i, mid in enumerate(models.keys()))
weighted_drop = weighted_baseline - spearman_metrics['spearman']

spearman_results = {
    'model': 'Ensemble_SpearmanWeighted',
    'model_id': 'E2',
    'stage': 'step2_groupkfold',
    'ensemble_type': 'spearman_weighted',
    'weights': {str(k): float(spearman_weights[i]) for i, k in enumerate(models.keys())},
    'overall_metrics': spearman_metrics,
    'random_5cv_spearman': weighted_baseline,
    'drop_from_random': weighted_drop
}

# Save results
with open('step2_groupkfold_ensemble_equal_results.json', 'w') as f:
    json.dump(equal_results, f, indent=2)
print(f"\n✓ 저장: step2_groupkfold_ensemble_equal_results.json")

with open('step2_groupkfold_ensemble_weighted_results.json', 'w') as f:
    json.dump(spearman_results, f, indent=2)
print(f"✓ 저장: step2_groupkfold_ensemble_weighted_results.json")

# Save predictions
np.save('step2_groupkfold_ensemble_equal_oof.npy', equal_weight_pred)
np.save('step2_groupkfold_ensemble_weighted_oof.npy', spearman_weight_pred)

print("\n" + "="*80)
print("Step 2 앙상블 계산 완료!")
print("="*80)
print(f"\n비교:")
print(f"  균등 가중:      Sp {equal_metrics['spearman']:.4f}, RMSE {equal_metrics['rmse']:.4f}, Drop {equal_drop:.4f}")
print(f"  Spearman 가중:  Sp {spearman_metrics['spearman']:.4f}, RMSE {spearman_metrics['rmse']:.4f}, Drop {weighted_drop:.4f}")
