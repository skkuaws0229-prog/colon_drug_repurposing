#!/usr/bin/env python3
"""
CPU 모델 재학습: DART, XGBoost, Stacking
모든 것 저장: 모델 파일, Train/OOF/Holdout 예측, 모든 메트릭
"""
import os
import json
import numpy as np
import pickle
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.ensemble import StackingRegressor, RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("CPU 모델 재학습 시작: DART, XGBoost, Stacking")
print("="*80)

# Load data
X_train = np.load("X_train.npy")
y_train = np.load("y_train.npy")

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

def train_model_full(model_name, model_id, create_model_fn, **kwargs):
    """Full training with all saves"""
    print(f"\n{'='*80}")
    print(f"{model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros(len(y_cv))
    train_predictions = np.zeros(len(y_cv))
    fold_train_sps = []
    fold_oof_sps = []

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
        print(f"\nFold {fold_idx}/5:")
        X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
        y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

        model = create_model_fn()
        model.fit(X_tr, y_tr)

        # Train predictions
        train_pred = model.predict(X_tr)
        train_predictions[tr_idx] = train_pred
        train_sp = spearmanr(y_tr, train_pred)[0]

        # OOF predictions
        val_pred = model.predict(X_val)
        oof_predictions[val_idx] = val_pred
        val_sp = spearmanr(y_val, val_pred)[0]

        fold_train_sps.append(train_sp)
        fold_oof_sps.append(val_sp)

        print(f"  Train Sp: {train_sp:.4f}, OOF Sp: {val_sp:.4f}")

    # Overall metrics
    train_sp = np.mean(fold_train_sps)
    oof_sp = spearmanr(y_cv, oof_predictions)[0]
    oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
    gap = train_sp - oof_sp
    ratio = oof_sp / train_sp if train_sp > 0 else 0
    fold_std = np.std(fold_oof_sps)

    print(f"\nOverall:")
    print(f"  Train Sp: {train_sp:.4f}")
    print(f"  OOF Sp: {oof_sp:.4f}")
    print(f"  Gap: {gap:.4f}")
    print(f"  Fold Std: {fold_std:.4f}")

    # Train final model on full CV data
    print(f"\nTraining final model on full CV data...")
    final_model = create_model_fn()
    final_model.fit(X_cv, y_cv)
    holdout_pred = final_model.predict(X_holdout)

    holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
    holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))

    print(f"Holdout Sp: {holdout_sp:.4f}")

    # Ensemble criteria
    ensemble_pass = bool(oof_sp >= 0.713 and oof_rmse <= 1.385)

    # Verdict
    if gap < 0.05:
        verdict = "NORMAL"
    elif gap < 0.10:
        verdict = "WARNING"
    elif gap < 0.15:
        verdict = "OVERFITTING"
    else:
        verdict = "SEVERE"

    # Save everything
    prefix = f"model_{model_id:02d}"

    # 1. Save model
    with open(f"{prefix}_model.pkl", "wb") as f:
        pickle.dump(final_model, f)
    print(f"✓ Saved: {prefix}_model.pkl")

    # 2. Save train predictions
    np.save(f"{prefix}_train.npy", train_predictions)
    print(f"✓ Saved: {prefix}_train.npy")

    # 3. Save OOF predictions
    np.save(f"{prefix}_oof.npy", oof_predictions)
    print(f"✓ Saved: {prefix}_oof.npy")

    # 4. Save holdout predictions
    np.save(f"{prefix}_holdout.npy", holdout_pred)
    print(f"✓ Saved: {prefix}_holdout.npy")

    # 5. Save complete JSON
    results = {
        "model": model_name,
        "train_spearman": float(train_sp),
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "gap": float(gap),
        "ratio": float(ratio),
        "fold_std": float(fold_std),
        "fold_train_sps": [float(x) for x in fold_train_sps],
        "fold_oof_sps": [float(x) for x in fold_oof_sps],
        "ensemble_pass": ensemble_pass,
        "verdict": verdict
    }

    json_file = f"{prefix}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Saved: {json_file}")

    return results

# ============================================================================
# Model 02: LightGBM-DART
# ============================================================================
def create_dart():
    return LGBMRegressor(
        boosting_type='dart',
        n_estimators=100,
        verbose=-1,
        random_state=42,
        device='cpu'
    )

dart_results = train_model_full("LightGBM-DART", 2, create_dart)

# ============================================================================
# Model 03: XGBoost
# ============================================================================
def create_xgboost():
    return XGBRegressor(
        n_estimators=100,
        verbosity=0,
        random_state=42
    )

xgb_results = train_model_full("XGBoost", 3, create_xgboost)

# ============================================================================
# Model 07: Stacking
# ============================================================================
def create_stacking():
    estimators = [
        ('lgbm', LGBMRegressor(n_estimators=100, verbose=-1, random_state=42)),
        ('xgb', XGBRegressor(n_estimators=100, verbosity=0, random_state=42)),
        ('rf', RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)),
        ('et', ExtraTreesRegressor(n_estimators=100, n_jobs=-1, random_state=42))
    ]
    return StackingRegressor(
        estimators=estimators,
        final_estimator=Ridge(alpha=1.0),
        cv=3,
        n_jobs=-1
    )

stack_results = train_model_full("Stacking", 7, create_stacking)

print("\n" + "="*80)
print("CPU 모델 재학습 완료!")
print("="*80)
