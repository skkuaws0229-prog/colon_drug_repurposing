#!/usr/bin/env python3
"""
Model 4/15: CatBoost (CPU)
Protocol v3.0 - Default hyperparameters
"""
import os
os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

import json
import time
import numpy as np
from catboost import CatBoostRegressor
from sklearn.model_selection import KFold
from scipy.stats import spearmanr

print("="*80)
print("Model 4/15: CatBoost (CPU)")
print("="*80)

# Load data
X_train = np.load("X_train.npy")
y_train = np.load("y_train.npy")

# Train/holdout split (80/20)
n_samples = len(y_train)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

X_cv = X_train[train_idx]
y_cv = y_train[train_idx]
X_holdout = X_train[holdout_idx]
y_holdout = y_train[holdout_idx]

# 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_cv))

for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
    fold_start = time.time()

    X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
    y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

    # CatBoost with default hyperparameters
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.03,
        depth=6,
        verbose=False,
        random_state=42 + fold_idx
    )

    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), early_stopping_rounds=50)

    y_val_pred = model.predict(X_val)
    oof_predictions[val_idx] = y_val_pred

    fold_sp = spearmanr(y_val, y_val_pred)[0]
    fold_rmse = np.sqrt(np.mean((y_val - y_val_pred) ** 2))
    fold_time = time.time() - fold_start

    print(f"Fold {fold_idx}/5: Sp={fold_sp:.4f}, RMSE={fold_rmse:.4f}, Time={fold_time:.1f}s")

# OOF metrics
oof_sp = spearmanr(y_cv, oof_predictions)[0]
oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
print(f"OOF: Sp={oof_sp:.4f}, RMSE={oof_rmse:.4f}")

# Holdout evaluation
final_model = CatBoostRegressor(
    iterations=1000,
    learning_rate=0.03,
    depth=6,
    verbose=False,
    random_state=42
)
final_model.fit(X_cv, y_cv)
holdout_pred = final_model.predict(X_holdout)

holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))
print(f"Holdout: Sp={holdout_sp:.4f}, RMSE={holdout_rmse:.4f}")

# Ensemble criteria
ensemble_pass = bool(oof_sp >= 0.713 and oof_rmse <= 1.385)
print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")

# Save results
results = {
    "model": "CatBoost",
    "oof_spearman": float(oof_sp),
    "oof_rmse": float(oof_rmse),
    "holdout_spearman": float(holdout_sp),
    "holdout_rmse": float(holdout_rmse),
    "ensemble_pass": ensemble_pass
}

with open("model_04_catboost.json", "w") as f:
    json.dump(results, f, indent=2)

np.save("model_04_catboost_oof.npy", oof_predictions)
np.save("model_04_catboost_holdout.npy", holdout_pred)

print("✓ CatBoost 완료")
