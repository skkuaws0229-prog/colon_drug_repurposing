#!/usr/bin/env python3
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from scipy.stats import spearmanr, kendalltau, pearsonr
import lightgbm as lgb
import time
import warnings
warnings.filterwarnings("ignore")

print("=" * 80)
print("Model 2/15: LightGBM DART (CPU)")
print("=" * 80)
print()

output_dir = Path("step4_results")
X = np.load("X_train.npy")
y = np.load("y_train.npy")

N_FOLDS = 5
SEED = 42
HOLDOUT_RATIO = 0.2
BENCH_SP = 0.713
BENCH_RMSE = 1.385

X_train, X_holdout, y_train, y_holdout = train_test_split(
    X, y, test_size=HOLDOUT_RATIO, random_state=SEED
)

print(f"Data: X_train={X_train.shape}, X_holdout={X_holdout.shape}")
print()

kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
oof_predictions = np.zeros(len(y_train))
fold_results = []

print("[5-Fold CV]")
for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_train), 1):
    X_tr, X_val = X_train[train_idx], X_train[val_idx]
    y_tr, y_val = y_train[train_idx], y_train[val_idx]
    
    model = lgb.LGBMRegressor(
        boosting_type="dart",
        random_state=SEED,
        verbosity=-1,
        force_col_wise=True
    )
    
    t0 = time.time()
    model.fit(X_tr, y_tr)
    train_time = time.time() - t0
    
    y_tr_pred = model.predict(X_tr)
    y_val_pred = model.predict(X_val)
    oof_predictions[val_idx] = y_val_pred
    
    val_sp, _ = spearmanr(y_val, y_val_pred)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
    tr_sp, _ = spearmanr(y_tr, y_tr_pred)
    
    print(f"Fold {fold_idx}/5: Val Sp={val_sp:.4f}, RMSE={val_rmse:.4f}, Time={train_time:.1f}s")
    
    fold_results.append({
        "fold": fold_idx,
        "val_spearman": float(val_sp),
        "val_rmse": float(val_rmse)
    })

oof_sp, _ = spearmanr(y_train, oof_predictions)
oof_rmse = np.sqrt(mean_squared_error(y_train, oof_predictions))

print()
print(f"OOF Spearman: {oof_sp:.4f}")
print(f"OOF RMSE:     {oof_rmse:.4f}")

# Holdout
model_final = lgb.LGBMRegressor(
    boosting_type="dart",
    random_state=SEED,
    verbosity=-1,
    force_col_wise=True
)
model_final.fit(X_train, y_train)
y_holdout_pred = model_final.predict(X_holdout)

holdout_sp, _ = spearmanr(y_holdout, y_holdout_pred)
holdout_rmse = np.sqrt(mean_squared_error(y_holdout, y_holdout_pred))

print(f"Holdout Sp:   {holdout_sp:.4f}")
print(f"Holdout RMSE: {holdout_rmse:.4f}")
print()

sp_pass = oof_sp >= BENCH_SP
rmse_pass = oof_rmse <= BENCH_RMSE
ensemble_pass = sp_pass and rmse_pass

print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")
print()

results = {
    "model": "LightGBM-DART",
    "oof_spearman": float(oof_sp),
    "oof_rmse": float(oof_rmse),
    "holdout_spearman": float(holdout_sp),
    "holdout_rmse": float(holdout_rmse),
    "ensemble_pass": ensemble_pass
}

with open("model_02_lightgbm_dart.json", "w") as f:
    json.dump(results, f, indent=2)

print("✓ LightGBM DART 완료")
