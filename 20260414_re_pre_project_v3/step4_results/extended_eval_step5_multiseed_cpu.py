#!/usr/bin/env python3
"""
Step 5: Multi-seed Stability (CPU 모델)
5개 시드로 Random 5CV 반복 (42, 123, 456, 789, 2026)
"""
import os
import json
import numpy as np
import pandas as pd
import pickle
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error
import lightgbm as lgb
import catboost as cb

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 5: Multi-seed Stability (CPU)")
print("="*80)

# Load data
X = np.load("X_train.npy")
y = np.load("y_train.npy")

# Seeds to test
SEEDS = [42, 123, 456, 789, 2026]

# Model configurations
models_config = [
    ("LightGBM", 1, {
        'n_estimators': 1000, 'learning_rate': 0.05, 'max_depth': 7,
        'num_leaves': 31, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 0.1, 'random_state': 42, 'verbose': -1
    }),
    ("LightGBM-DART", 2, {
        'n_estimators': 1000, 'learning_rate': 0.05, 'max_depth': 7,
        'num_leaves': 31, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 0.1, 'random_state': 42, 'boosting_type': 'dart', 'verbose': -1
    }),
    ("CatBoost", 4, {
        'iterations': 1000, 'learning_rate': 0.05, 'depth': 6,
        'l2_leaf_reg': 3, 'random_seed': 42, 'verbose': 0
    })
]

def train_seed(model_name, model_id, base_params, seed):
    """Train model with specific seed"""
    print(f"\n  Seed {seed}:")

    # Update random seed
    params = base_params.copy()
    if 'random_state' in params:
        params['random_state'] = seed
    if 'random_seed' in params:
        params['random_seed'] = seed

    # 5-fold CV
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    fold_scores = []
    oof_predictions = np.zeros(len(y))
    train_predictions = np.zeros(len(y))

    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # Train model
        if 'LightGBM' in model_name:
            model = lgb.LGBMRegressor(**params)
        elif 'CatBoost' in model_name:
            model = cb.CatBoostRegressor(**params)

        model.fit(X_train, y_train)

        # Predictions
        val_pred = model.predict(X_val)
        oof_predictions[val_idx] = val_pred

        # Train predictions for this fold
        train_pred = model.predict(X_train)
        train_predictions[train_idx] = train_pred

        # Fold score
        fold_sp = spearmanr(y_val, val_pred)[0]
        fold_scores.append(fold_sp)

    # Calculate metrics
    oof_sp = spearmanr(y, oof_predictions)[0]
    oof_rmse = np.sqrt(mean_squared_error(y, oof_predictions))
    oof_mae = mean_absolute_error(y, oof_predictions)

    # Train Spearman
    train_sp = spearmanr(y, train_predictions)[0]
    gap = train_sp - oof_sp

    print(f"    Train Sp: {train_sp:.4f}, OOF Sp: {oof_sp:.4f}, Gap: {gap:.4f}")
    print(f"    RMSE: {oof_rmse:.4f}, MAE: {oof_mae:.4f}")

    # Get Top-30 drug indices (lowest predicted viability)
    top30_indices = np.argsort(oof_predictions)[:30]

    return {
        'seed': seed,
        'train_spearman': train_sp,
        'oof_spearman': oof_sp,
        'oof_rmse': oof_rmse,
        'oof_mae': oof_mae,
        'gap': gap,
        'fold_scores': fold_scores,
        'fold_mean': np.mean(fold_scores),
        'fold_std': np.std(fold_scores),
        'top30_indices': top30_indices.tolist(),
        'oof_predictions': oof_predictions
    }

# Train all models
print("\n" + "="*80)
print("CPU 모델 실행 중...")
print("="*80)

all_results = {}

for model_name, model_id, params in models_config:
    print(f"\n{'='*80}")
    print(f"Model {model_id:02d}: {model_name}")
    print(f"{'='*80}")

    seed_results = []
    all_top30_sets = []

    for seed in SEEDS:
        result = train_seed(model_name, model_id, params, seed)
        seed_results.append(result)
        all_top30_sets.append(set(result['top30_indices']))

        # Save seed-specific predictions
        np.save(f"step5_seed{seed}_{model_id:02d}_oof.npy", result['oof_predictions'])

    # Calculate cross-seed statistics
    oof_sps = [r['oof_spearman'] for r in seed_results]
    train_sps = [r['train_spearman'] for r in seed_results]
    gaps = [r['gap'] for r in seed_results]
    rmses = [r['oof_rmse'] for r in seed_results]

    # Top-30 overlap (intersection across all seeds)
    top30_intersection = set.intersection(*all_top30_sets)
    top30_union = set.union(*all_top30_sets)

    # Jaccard similarity (average pairwise)
    jaccard_scores = []
    for i in range(len(all_top30_sets)):
        for j in range(i+1, len(all_top30_sets)):
            intersection = len(all_top30_sets[i] & all_top30_sets[j])
            union = len(all_top30_sets[i] | all_top30_sets[j])
            jaccard = intersection / union if union > 0 else 0.0
            jaccard_scores.append(jaccard)

    avg_jaccard = np.mean(jaccard_scores) if jaccard_scores else 0.0

    # Fold std average
    avg_fold_std = np.mean([r['fold_std'] for r in seed_results])

    summary = {
        'model_id': model_id,
        'model_name': model_name,
        'stage': 'step5_multiseed',
        'seeds': SEEDS,
        'seed_results': seed_results,
        'cross_seed_stats': {
            'train_spearman_mean': np.mean(train_sps),
            'train_spearman_std': np.std(train_sps),
            'oof_spearman_mean': np.mean(oof_sps),
            'oof_spearman_std': np.std(oof_sps),
            'gap_mean': np.mean(gaps),
            'gap_std': np.std(gaps),
            'rmse_mean': np.mean(rmses),
            'rmse_std': np.std(rmses),
            'top30_overlap_count': len(top30_intersection),
            'top30_total_unique': len(top30_union),
            'top30_jaccard_similarity': avg_jaccard,
            'avg_fold_std': avg_fold_std
        }
    }

    # Save results
    with open(f"step5_multiseed_{model_id:02d}_results.json", 'w') as f:
        # Remove oof_predictions from seed_results for JSON (too large)
        summary_save = summary.copy()
        summary_save['seed_results'] = [
            {k: v for k, v in r.items() if k != 'oof_predictions'}
            for r in seed_results
        ]
        json.dump(summary_save, f, indent=2)

    all_results[model_id] = summary

    print(f"\n  종합 통계 (5 seeds):")
    print(f"    OOF Sp: {summary['cross_seed_stats']['oof_spearman_mean']:.4f} ± {summary['cross_seed_stats']['oof_spearman_std']:.4f}")
    print(f"    Gap:    {summary['cross_seed_stats']['gap_mean']:.4f} ± {summary['cross_seed_stats']['gap_std']:.4f}")
    print(f"    Top-30 Overlap: {len(top30_intersection)}/30 ({len(top30_intersection)/30*100:.1f}%)")
    print(f"    Jaccard Similarity: {avg_jaccard:.4f}")
    print(f"    ✓ 저장: step5_multiseed_{model_id:02d}_results.json")

print("\n" + "="*80)
print("CPU 모델 완료!")
print("="*80)
