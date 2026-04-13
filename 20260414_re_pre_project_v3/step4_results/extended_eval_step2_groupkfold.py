#!/usr/bin/env python3
"""
2단계: GroupKFold (by canonical_drug_id) 평가
대상: CatBoost, LightGBM, DART, FlatMLP, CrossAttention, FT-Transformer (6개)
"""
import os
import json
import numpy as np
import pandas as pd
import pickle
import torch
import torch.nn as nn
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("2단계: GroupKFold (by canonical_drug_id) 평가")
print("="*80)

# Load data
features_df = pd.read_parquet("../features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
y = np.load("y_train.npy")
drug_ids = features_df['canonical_drug_id'].values

print(f"\n데이터 로드:")
print(f"  Features: {X.shape}")
print(f"  Labels: {y.shape}")
print(f"  유니크 약물 수: {len(np.unique(drug_ids))}\n")

# Device for PyTorch
device = 'mps' if torch.backends.mps.is_available() else 'cpu'

# Simple MLP for PyTorch models
class SimpleMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1)
        )
    def forward(self, x):
        return self.net(x).squeeze()

def calculate_metrics(y_true, y_pred):
    """Calculate all metrics"""
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

def train_groupkfold_cpu(model_name, model_id, create_model_fn, model_type='cpu'):
    """Train with GroupKFold for CPU models"""
    print(f"\n{'='*80}")
    print(f"2단계 GroupKFold: {model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    gkf = GroupKFold(n_splits=5)
    fold_metrics = []
    oof_predictions = np.zeros(len(y))

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids), 1):
        print(f"\nFold {fold_idx}/5:")
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = create_model_fn()
        model.fit(X_train, y_train)

        val_pred = model.predict(X_val)
        oof_predictions[val_idx] = val_pred

        metrics = calculate_metrics(y_val, val_pred)
        fold_metrics.append(metrics)

        print(f"  Sp: {metrics['spearman']:.4f}, RMSE: {metrics['rmse']:.4f}, MAE: {metrics['mae']:.4f}")

        # Save fold model
        fold_model_file = f"step2_groupkfold_{model_id:02d}_fold{fold_idx}.pkl"
        with open(fold_model_file, 'wb') as f:
            pickle.dump(model, f)

    # Overall metrics
    overall_metrics = calculate_metrics(y, oof_predictions)

    # Calculate mean and std across folds
    metrics_summary = {}
    for metric_name in fold_metrics[0].keys():
        values = [f[metric_name] for f in fold_metrics]
        metrics_summary[f'{metric_name}_mean'] = np.mean(values)
        metrics_summary[f'{metric_name}_std'] = np.std(values)
        metrics_summary[f'{metric_name}_folds'] = values

    # Load random 5CV result for comparison
    try:
        with open(f"model_{model_id:02d}.json") as f:
            random_cv_data = json.load(f)
        random_sp = random_cv_data.get('oof_spearman', np.nan)
    except:
        random_sp = np.nan

    drop_from_random = random_sp - overall_metrics['spearman'] if not np.isnan(random_sp) else np.nan

    results = {
        'model': model_name,
        'model_id': model_id,
        'stage': 'step2_groupkfold',
        'overall_metrics': overall_metrics,
        'fold_metrics': fold_metrics,
        'metrics_summary': metrics_summary,
        'random_5cv_spearman': random_sp,
        'drop_from_random': drop_from_random
    }

    # Save results
    results_file = f"step2_groupkfold_{model_id:02d}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Save OOF predictions
    np.save(f"step2_groupkfold_{model_id:02d}_oof.npy", oof_predictions)

    print(f"\n전체 GroupKFold 성능:")
    print(f"  Spearman: {overall_metrics['spearman']:.4f} ± {metrics_summary['spearman_std']:.4f}")
    print(f"  Random 5CV 대비 하락: {drop_from_random:.4f}")
    print(f"✓ 저장 완료: {results_file}")

    return results

def train_groupkfold_gpu(model_name, model_id, model_class):
    """Train with GroupKFold for GPU models"""
    print(f"\n{'='*80}")
    print(f"2단계 GroupKFold: {model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    gkf = GroupKFold(n_splits=5)
    fold_metrics = []
    oof_predictions = np.zeros(len(y))

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids), 1):
        print(f"\nFold {fold_idx}/5:")
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = model_class(X.shape[1]).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        X_train_tensor = torch.FloatTensor(X_train).to(device)
        y_train_tensor = torch.FloatTensor(y_train).to(device)
        X_val_tensor = torch.FloatTensor(X_val).to(device)

        # Train
        model.train()
        for epoch in range(100):
            optimizer.zero_grad()
            outputs = model(X_train_tensor)
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()

        # Predict
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val_tensor).cpu().numpy()

        oof_predictions[val_idx] = val_pred

        metrics = calculate_metrics(y_val, val_pred)
        fold_metrics.append(metrics)

        print(f"  Sp: {metrics['spearman']:.4f}, RMSE: {metrics['rmse']:.4f}, MAE: {metrics['mae']:.4f}")

        # Save fold model
        fold_model_file = f"step2_groupkfold_{model_id:02d}_fold{fold_idx}.pt"
        torch.save(model.state_dict(), fold_model_file)

    # Overall metrics
    overall_metrics = calculate_metrics(y, oof_predictions)

    # Calculate mean and std across folds
    metrics_summary = {}
    for metric_name in fold_metrics[0].keys():
        values = [f[metric_name] for f in fold_metrics]
        metrics_summary[f'{metric_name}_mean'] = np.mean(values)
        metrics_summary[f'{metric_name}_std'] = np.std(values)
        metrics_summary[f'{metric_name}_folds'] = values

    # Load random 5CV result
    try:
        with open(f"model_{model_id:02d}.json") as f:
            random_cv_data = json.load(f)
        random_sp = random_cv_data.get('oof_spearman', np.nan)
    except:
        random_sp = np.nan

    drop_from_random = random_sp - overall_metrics['spearman'] if not np.isnan(random_sp) else np.nan

    results = {
        'model': model_name,
        'model_id': model_id,
        'stage': 'step2_groupkfold',
        'overall_metrics': overall_metrics,
        'fold_metrics': fold_metrics,
        'metrics_summary': metrics_summary,
        'random_5cv_spearman': random_sp,
        'drop_from_random': drop_from_random
    }

    # Save results
    results_file = f"step2_groupkfold_{model_id:02d}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Save OOF predictions
    np.save(f"step2_groupkfold_{model_id:02d}_oof.npy", oof_predictions)

    print(f"\n전체 GroupKFold 성능:")
    print(f"  Spearman: {overall_metrics['spearman']:.4f} ± {metrics_summary['spearman_std']:.4f}")
    print(f"  Random 5CV 대비 하락: {drop_from_random:.4f}")
    print(f"✓ 저장 완료: {results_file}")

    return results

# ============================================================================
# Execute CPU models
# ============================================================================
print("\n" + "="*80)
print("CPU 모델 실행 중...")
print("="*80)

# CatBoost
result_catboost = train_groupkfold_cpu(
    "CatBoost", 4,
    lambda: CatBoostRegressor(iterations=100, verbose=0, random_state=42)
)

# LightGBM
result_lgbm = train_groupkfold_cpu(
    "LightGBM", 1,
    lambda: LGBMRegressor(n_estimators=100, verbose=-1, random_state=42)
)

# DART
result_dart = train_groupkfold_cpu(
    "LightGBM-DART", 2,
    lambda: LGBMRegressor(boosting_type='dart', n_estimators=100, verbose=-1, random_state=42)
)

print("\n" + "="*80)
print("CPU 모델 완료!")
print("="*80)
