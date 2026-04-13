#!/usr/bin/env python3
"""
Step 4: Scaffold Split (CPU 모델)
Murcko scaffold 기반 화학 구조 분할
"""
import os
import json
import numpy as np
import pandas as pd
import pickle
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb
import catboost as cb

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 4: Scaffold Split (CPU)")
print("="*80)

# Load data
features_df = pd.read_parquet("../features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
y = np.load("y_train.npy")

# Random 5CV baseline values
BASELINE_SPEARMAN = {
    1: 0.8493,   # LightGBM
    2: 0.8415,   # DART
    4: 0.8624    # CatBoost
}

# Extract SMILES and generate Murcko scaffolds
print("\nGenerating Murcko scaffolds...")
smiles_col = 'drug__canonical_smiles_raw' if 'drug__canonical_smiles_raw' in features_df.columns else 'drug__smiles'
smiles_list = features_df[smiles_col].values

scaffolds = []
for smi in smiles_list:
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            scaffold = MurckoScaffold.GetScaffoldForMol(mol)
            scaffold_smiles = Chem.MolToSmiles(scaffold)
            scaffolds.append(scaffold_smiles)
        else:
            scaffolds.append('INVALID')
    except:
        scaffolds.append('INVALID')

scaffolds = np.array(scaffolds)
unique_scaffolds = np.unique(scaffolds[scaffolds != 'INVALID'])

print(f"Total samples: {len(X)}")
print(f"Unique scaffolds: {len(unique_scaffolds)}")
print(f"Invalid SMILES: {np.sum(scaffolds == 'INVALID')}")

# Scaffold split (80% train scaffolds, 20% test scaffolds)
np.random.seed(42)
n_test_scaffolds = int(len(unique_scaffolds) * 0.2)
test_scaffolds = np.random.choice(unique_scaffolds, size=n_test_scaffolds, replace=False)
test_mask = np.isin(scaffolds, test_scaffolds)

X_train, X_test = X[~test_mask], X[test_mask]
y_train, y_test = y[~test_mask], y[test_mask]

print(f"\nData Split:")
print(f"  Test scaffolds: {len(test_scaffolds)} ({len(test_scaffolds)/len(unique_scaffolds)*100:.1f}%)")
print(f"  Train samples: {len(X_train)}")
print(f"  Test samples (unseen scaffolds): {len(X_test)}\n")

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

def train_scaffold_cpu(model_name, model_id, model_params):
    print(f"\n{'='*80}")
    print(f"Step 4 Scaffold Split: {model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    # Train model
    if 'LightGBM' in model_name:
        if 'DART' in model_name:
            model = lgb.LGBMRegressor(**model_params, boosting_type='dart', verbose=-1)
        else:
            model = lgb.LGBMRegressor(**model_params, verbose=-1)
    elif 'CatBoost' in model_name:
        model = cb.CatBoostRegressor(**model_params, verbose=0)

    print("  Training on seen scaffolds...")
    model.fit(X_train, y_train)

    # Predict on unseen scaffolds
    print("  Predicting on unseen scaffolds...")
    y_pred = model.predict(X_test)

    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred)

    print(f"\n  Spearman: {metrics['spearman']:.4f}")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    print(f"  MAE: {metrics['mae']:.4f}")

    # Baseline comparison
    baseline_sp = BASELINE_SPEARMAN.get(model_id, np.nan)
    drop_from_random = baseline_sp - metrics['spearman'] if not np.isnan(baseline_sp) else np.nan

    results = {
        'model': model_name,
        'model_id': model_id,
        'stage': 'step4_scaffold_split',
        'data_split': {
            'total_scaffolds': int(len(unique_scaffolds)),
            'test_scaffolds': int(len(test_scaffolds)),
            'train_samples': int(len(X_train)),
            'test_samples': int(len(X_test))
        },
        'metrics': metrics,
        'random_5cv_spearman': baseline_sp,
        'drop_from_random': drop_from_random
    }

    # Save
    results_file = f"step4_scaffold_{model_id:02d}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    model_file = f"step4_scaffold_{model_id:02d}_model.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)

    np.save(f"step4_scaffold_{model_id:02d}_predictions.npy", y_pred)

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
    train_scaffold_cpu(model_name, model_id, params)

print("\n" + "="*80)
print("CPU 모델 완료!")
print("="*80)
