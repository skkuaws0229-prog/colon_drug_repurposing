#!/usr/bin/env python3
"""
Step 3: Unseen Drug Holdout (CPU 모델)
20-30% 약물을 완전히 제외하고 평가
"""
import os
import json
import numpy as np
import pandas as pd
import pickle
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import ndcg_score
import lightgbm as lgb
import catboost as cb

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 3: Unseen Drug Holdout (CPU)")
print("="*80)

# Load data
features_df = pd.read_parquet("../features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
y = np.load("y_train.npy")
drug_ids = features_df['canonical_drug_id'].values

# Random 5CV baseline values
BASELINE_SPEARMAN = {
    1: 0.8493,   # LightGBM
    2: 0.8415,   # DART
    4: 0.8624    # CatBoost
}

# Unseen drug split (25% drugs as holdout)
np.random.seed(42)
unique_drugs = np.unique(drug_ids)
n_unseen = int(len(unique_drugs) * 0.25)
unseen_drugs = np.random.choice(unique_drugs, size=n_unseen, replace=False)
unseen_mask = np.isin(drug_ids, unseen_drugs)

X_train, X_test = X[~unseen_mask], X[unseen_mask]
y_train, y_test = y[~unseen_mask], y[unseen_mask]

print(f"\nData Split:")
print(f"  Total drugs: {len(unique_drugs)}")
print(f"  Unseen drugs: {len(unseen_drugs)} ({len(unseen_drugs)/len(unique_drugs)*100:.1f}%)")
print(f"  Train samples: {len(X_train)}")
print(f"  Test samples (unseen drugs): {len(X_test)}")

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

    # Define "sensitive" as below median (or you can use a threshold like < 0.5)
    threshold = np.median(y_true_valid)
    is_sensitive = y_true_valid < threshold

    # Precision@k: fraction of top-k that are truly sensitive
    precision_at_k = np.mean(is_sensitive[top_k_idx])

    # Recall@k: fraction of all sensitive found in top-k
    total_sensitive = np.sum(is_sensitive)
    recall_at_k = np.sum(is_sensitive[top_k_idx]) / total_sensitive if total_sensitive > 0 else 0.0

    # NDCG@k: Use negative viability as relevance (lower viability = higher relevance)
    relevance = -y_true_valid  # Invert so lower viability = higher score
    relevance_normalized = relevance - relevance.min()
    true_relevance = relevance_normalized.reshape(1, -1)
    pred_relevance = relevance_normalized[np.argsort(y_pred_valid)].reshape(1, -1)
    ndcg_k = ndcg_score(true_relevance[:, :k], pred_relevance[:, :k])

    # Enrichment Factor@k: (Precision@k) / (baseline rate)
    baseline_rate = total_sensitive / len(y_true_valid)
    ef_k = precision_at_k / baseline_rate if baseline_rate > 0 else 0.0

    return {
        'precision_at_30': precision_at_k,
        'recall_at_30': recall_at_k,
        'ndcg_at_30': ndcg_k,
        'ef_at_30': ef_k
    }

def train_unseen_drug_cpu(model_name, model_id, model_params):
    print(f"\n{'='*80}")
    print(f"Step 3 Unseen Drug: {model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    # Train model
    if 'LightGBM' in model_name:
        if 'DART' in model_name:
            model = lgb.LGBMRegressor(**model_params, boosting_type='dart', verbose=-1)
        else:
            model = lgb.LGBMRegressor(**model_params, verbose=-1)
    elif 'CatBoost' in model_name:
        model = cb.CatBoostRegressor(**model_params, verbose=0)

    print("  Training on seen drugs...")
    model.fit(X_train, y_train)

    # Predict on unseen drugs
    print("  Predicting on unseen drugs...")
    y_pred = model.predict(X_test)

    # Calculate metrics
    regression_metrics = calculate_metrics(y_test, y_pred)
    ranking_metrics = calculate_ranking_metrics(y_test, y_pred, k=30)

    print(f"\n  Regression:")
    print(f"    Spearman: {regression_metrics['spearman']:.4f}")
    print(f"    RMSE: {regression_metrics['rmse']:.4f}")
    print(f"  Ranking:")
    print(f"    Precision@30: {ranking_metrics['precision_at_30']:.4f}")
    print(f"    NDCG@30: {ranking_metrics['ndcg_at_30']:.4f}")

    # Baseline comparison
    baseline_sp = BASELINE_SPEARMAN.get(model_id, np.nan)
    drop_from_random = baseline_sp - regression_metrics['spearman'] if not np.isnan(baseline_sp) else np.nan

    results = {
        'model': model_name,
        'model_id': model_id,
        'stage': 'step3_unseen_drug',
        'data_split': {
            'total_drugs': int(len(unique_drugs)),
            'unseen_drugs': int(len(unseen_drugs)),
            'train_samples': int(len(X_train)),
            'test_samples': int(len(X_test))
        },
        'regression_metrics': regression_metrics,
        'ranking_metrics': ranking_metrics,
        'random_5cv_spearman': baseline_sp,
        'drop_from_random': drop_from_random
    }

    # Save
    results_file = f"step3_unseen_drug_{model_id:02d}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    model_file = f"step3_unseen_drug_{model_id:02d}_model.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)

    np.save(f"step3_unseen_drug_{model_id:02d}_predictions.npy", y_pred)

    print(f"  ✓ Saved: {results_file}")
    return results

# Model configurations
models_config = [
    ("LightGBM", 1, {
        'n_estimators': 1000, 'learning_rate': 0.05, 'max_depth': 7,
        'num_leaves': 31, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 0.1, 'random_state': 42
    }),
    ("LightGBM-DART", 2, {
        'n_estimators': 1000, 'learning_rate': 0.05, 'max_depth': 7,
        'num_leaves': 31, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 0.1, 'random_state': 42
    }),
    ("CatBoost", 4, {
        'iterations': 1000, 'learning_rate': 0.05, 'depth': 6,
        'l2_leaf_reg': 3, 'random_seed': 42
    })
]

print("\n" + "="*80)
print("CPU 모델 실행 중...")
print("="*80)

for model_name, model_id, params in models_config:
    train_unseen_drug_cpu(model_name, model_id, params)

print("\n" + "="*80)
print("CPU 모델 완료!")
print("="*80)
