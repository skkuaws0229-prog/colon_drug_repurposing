#!/usr/bin/env python3
"""
Train Spearman 보완 + 이상치 샘플 식별
"""
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
import glob

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Train Spearman 보완 + 이상치 샘플 식별")
print("="*80)

# Load data
X_train = np.load("X_train.npy")
y_train = np.load("y_train.npy")
features_df = pd.read_parquet("../features_slim.parquet")

print(f"데이터 로드 완료:")
print(f"  X_train: {X_train.shape}")
print(f"  y_train: {y_train.shape}")
print(f"  features_df: {features_df.shape}\n")

# Split data (same as training)
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

# Get metadata for analysis
features_df_reindexed = features_df.iloc[holdout_idx].reset_index(drop=True)

# ============================================================================
# 1. Train Spearman 계산 (앙상블 통과 모델만)
# ============================================================================
print("="*80)
print("1. Train Spearman 보완 (앙상블 통과 모델)")
print("="*80)

# Load ensemble-pass models
ensemble_models = []
for i in range(1, 16):
    json_files = glob.glob(f"model_{i:02d}_*.json")
    if not json_files:
        continue

    json_file = json_files[0]
    with open(json_file) as f:
        data = json.load(f)

    if not data.get("ensemble_pass", False):
        continue

    model_name = data.get("model", "Unknown")
    oof_file = json_file.replace(".json", "_oof.npy")

    if not os.path.exists(oof_file):
        continue

    oof_pred = np.load(oof_file)

    ensemble_models.append({
        "id": i,
        "name": model_name,
        "oof_pred": oof_pred,
        "json_data": data
    })

print(f"분석 대상: {len(ensemble_models)}개 앙상블 통과 모델\n")

# Calculate Train Spearman using 5-fold CV approach
print("Train Spearman 계산 (5-Fold CV train set 사용):")
print("-" * 100)
print(f"{'모델명':<30} {'Train Sp':>12} {'OOF Sp':>12} {'Gap':>10} {'Ratio':>10} {'판정':>12}")
print("-" * 100)

from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from catboost import CatBoostRegressor

train_results = []

for m in ensemble_models:
    model_name = m["name"]
    oof_sp = m["json_data"].get("oof_spearman", None)

    # Quick retrain to get train predictions
    # Use 5-fold CV to calculate train spearman
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    train_predictions = np.zeros(len(y_cv))

    print(f"\n{model_name}: ", end="", flush=True)

    fold_train_sps = []
    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
        X_tr, y_tr = X_cv[tr_idx], y_cv[tr_idx]

        # Quick model training based on model type
        if "CatBoost" in model_name:
            model = CatBoostRegressor(iterations=100, verbose=0, random_state=42)
        elif "RandomForest" in model_name or "RSF" in model_name:
            model = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42, verbose=0)
        elif "ExtraTrees" in model_name:
            model = ExtraTreesRegressor(n_estimators=100, n_jobs=-1, random_state=42, verbose=0)
        elif "Stacking" in model_name:
            # Skip stacking (너무 오래 걸림)
            print("Stacking 스킵 (시간 소요)")
            train_predictions = None
            break
        else:
            # Skip other models
            print(f"{model_name} 스킵 (모델 타입 미지원)")
            train_predictions = None
            break

        model.fit(X_tr, y_tr)
        train_pred = model.predict(X_tr)

        # Calculate train spearman for this fold
        fold_train_sp = spearmanr(y_tr, train_pred)[0]
        fold_train_sps.append(fold_train_sp)

        print(f"F{fold_idx}:{fold_train_sp:.3f} ", end="", flush=True)

    if train_predictions is not None and len(fold_train_sps) > 0:
        train_sp = np.mean(fold_train_sps)

        if oof_sp is not None:
            gap = train_sp - oof_sp
            ratio = oof_sp / train_sp if train_sp > 0 else 0

            # 판정
            if gap < 0.05:
                verdict = "NORMAL"
            elif gap < 0.10:
                verdict = "WARNING"
            elif gap < 0.15:
                verdict = "OVERFITTING"
            else:
                verdict = "SEVERE"

            train_results.append({
                "name": model_name,
                "train_sp": train_sp,
                "oof_sp": oof_sp,
                "gap": gap,
                "ratio": ratio,
                "verdict": verdict
            })

            print(f"\n{model_name:<30} {train_sp:>12.4f} {oof_sp:>12.4f} {gap:>10.4f} {ratio:>10.4f} {verdict:>12}")

print("\n" + "="*80)

# ============================================================================
# 2. 극단적 오차 샘플 식별
# ============================================================================
print("\n" + "="*80)
print("2. 극단적 오차 샘플 식별 (Top 10)")
print("="*80)

# Calculate errors for all ensemble models
all_errors = []
valid_models = []

for m in ensemble_models:
    holdout_file = f"model_{m['id']:02d}_*.json".replace(".json", "_holdout.npy")
    holdout_files = glob.glob(holdout_file.replace("_*.json", "_*_holdout.npy"))

    if not holdout_files:
        continue

    holdout_pred = np.load(holdout_files[0])

    if len(holdout_pred) != len(y_holdout):
        continue

    errors = np.abs(holdout_pred - y_holdout)
    all_errors.append(errors)
    valid_models.append(m["name"])

if all_errors:
    all_errors_array = np.array(all_errors)
    mean_errors = np.nanmean(all_errors_array, axis=0)
    worst_indices = np.argsort(mean_errors)[-10:][::-1]

    print(f"\n극단적 오차 샘플 (Holdout Top 10):")
    print("-" * 120)
    print(f"{'순위':<6} {'Idx':<8} {'sample_id':<25} {'drug_id':<20} {'실제 IC50':>12} {'평균 오차':>12}")
    print("-" * 120)

    for rank, idx in enumerate(worst_indices, 1):
        true_val = y_holdout[idx]
        avg_error = mean_errors[idx]

        # Get metadata from features_df
        if idx < len(features_df_reindexed):
            row = features_df_reindexed.iloc[idx]
            sample_id = row.get('sample_id', 'N/A')
            drug_id = row.get('canonical_drug_id', 'N/A')
        else:
            sample_id = 'N/A'
            drug_id = 'N/A'

        print(f"{rank:<6} {idx:<8} {str(sample_id):<25} {str(drug_id):<20} {true_val:>12.4f} {avg_error:>12.4f}")

    # Check if these drugs/samples appear elsewhere
    print("\n\n이상치 샘플 분석 (상위 3개):")
    print("-" * 120)

    for rank, idx in enumerate(worst_indices[:3], 1):
        if idx >= len(features_df_reindexed):
            continue

        row = features_df_reindexed.iloc[idx]
        sample_id = row.get('sample_id', 'N/A')
        drug_id = row.get('canonical_drug_id', 'N/A')

        print(f"\n[{rank}] Idx={idx}, sample_id={sample_id}, drug_id={drug_id}")

        # Check if this drug appears elsewhere
        drug_mask = features_df['canonical_drug_id'] == drug_id
        drug_count = drug_mask.sum()

        # Check if this sample appears elsewhere
        sample_mask = features_df['sample_id'] == sample_id
        sample_count = sample_mask.sum()

        print(f"  - 이 약물(drug_id={drug_id})의 총 등장 횟수: {drug_count}회")
        print(f"  - 이 샘플(sample_id={sample_id})의 총 등장 횟수: {sample_count}회")

        # Check labels for this drug/sample in full dataset
        # (labels are in y_train with same order as features)
        if drug_count > 1:
            drug_indices = features_df.index[drug_mask].tolist()
            drug_labels = y_train[drug_indices]
            print(f"  - 이 약물의 다른 IC50 값들: mean={drug_labels.mean():.4f}, std={drug_labels.std():.4f}, range=[{drug_labels.min():.4f}, {drug_labels.max():.4f}]")

        if sample_count > 1:
            sample_indices = features_df.index[sample_mask].tolist()
            sample_labels = y_train[sample_indices]
            print(f"  - 이 샘플의 다른 IC50 값들: mean={sample_labels.mean():.4f}, std={sample_labels.std():.4f}, range=[{sample_labels.min():.4f}, {sample_labels.max():.4f}]")

print("\n" + "="*80)
print("분석 완료!")
print("="*80)
