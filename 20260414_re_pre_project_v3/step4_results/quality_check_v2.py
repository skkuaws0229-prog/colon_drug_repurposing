#!/usr/bin/env python3
"""
15개 모델 품질 점검 v2
1. 결측치 점검 (15개 전체)
2. 이상치 점검 (앙상블 통과 12개)
3. 과적합 점검 (15개 전체)
"""
import os
import json
import numpy as np
from scipy.stats import spearmanr
import glob

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("15개 모델 품질 점검 v2")
print("="*80)

# Load ground truth
y_train = np.load("y_train.npy")
n_samples = len(y_train)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

y_cv = y_train[train_idx]
y_holdout = y_train[holdout_idx]

print(f"Ground truth shape: y_train={y_train.shape}, y_cv={y_cv.shape}, y_holdout={y_holdout.shape}\n")

# Collect all models
models = []
for i in range(1, 16):
    json_files = glob.glob(f"model_{i:02d}_*.json")
    if not json_files:
        continue

    json_file = json_files[0]
    model_id = i

    # Load JSON
    with open(json_file) as f:
        data = json.load(f)

    model_name = data.get("model", "Unknown")

    # Try to load OOF and Holdout predictions
    oof_file = json_file.replace(".json", "_oof.npy")
    holdout_file = json_file.replace(".json", "_holdout.npy")

    oof_pred = None
    holdout_pred = None
    has_predictions = False

    if os.path.exists(oof_file):
        oof_pred = np.load(oof_file)
        has_predictions = True
    if os.path.exists(holdout_file):
        holdout_pred = np.load(holdout_file)
        has_predictions = True

    models.append({
        "id": model_id,
        "name": model_name,
        "oof_pred": oof_pred,
        "holdout_pred": holdout_pred,
        "has_predictions": has_predictions,
        "json_data": data
    })

print(f"✓ {len(models)}개 모델 로드 완료")
print(f"  - 예측 파일(.npy) 있음: {sum(1 for m in models if m['has_predictions'])}개")
print(f"  - 예측 파일(.npy) 없음: {sum(1 for m in models if not m['has_predictions'])}개\n")

# ============================================================================
# 1. 결측치 점검 (15개 전체)
# ============================================================================
print("="*80)
print("1. 결측치 점검 (15개 모델 전체)")
print("="*80)

nan_count = 0
for m in models:
    if not m["has_predictions"]:
        print(f"⚠️  {m['name']}: 예측 파일 없음 (JSON 결과만 존재)")
        continue

    oof_nans = np.isnan(m["oof_pred"]).sum() if m["oof_pred"] is not None else "N/A"
    holdout_nans = np.isnan(m["holdout_pred"]).sum() if m["holdout_pred"] is not None else "N/A"

    if (isinstance(oof_nans, int) and oof_nans > 0) or (isinstance(holdout_nans, int) and holdout_nans > 0):
        nan_count += 1
        print(f"❌ {m['name']}: OOF NaN={oof_nans}, Holdout NaN={holdout_nans}")

        # GAT 특별 분석
        if "GAT" in m["name"]:
            print(f"   → GAT NaN 원인 분석:")
            if m["holdout_pred"] is not None:
                holdout_pred = m["holdout_pred"]
                print(f"      Holdout shape: {holdout_pred.shape}")
                print(f"      NaN 개수: {np.isnan(holdout_pred).sum()}")
                print(f"      Inf 개수: {np.isinf(holdout_pred).sum()}")
                print(f"      유효값 개수: {(~np.isnan(holdout_pred) & ~np.isinf(holdout_pred)).sum()}")
                # Check for constant predictions
                valid_preds = holdout_pred[~np.isnan(holdout_pred) & ~np.isinf(holdout_pred)]
                if len(valid_preds) > 0:
                    print(f"      유효 예측값 범위: [{valid_preds.min():.4f}, {valid_preds.max():.4f}]")
                    print(f"      유효 예측값 std: {valid_preds.std():.4f}")
                    if valid_preds.std() < 0.01:
                        print(f"      → Holdout Spearman NaN 원인: 예측값 분산 거의 없음 (상수 예측)")
                    else:
                        print(f"      → Holdout Spearman NaN 원인: 예측값에 NaN 포함")
    else:
        print(f"✓ {m['name']}: NaN 없음 (OOF={oof_nans}, Holdout={holdout_nans})")

print(f"\n총 {len(models)}개 중 NaN 발견: {nan_count}개\n")

# ============================================================================
# 2. 이상치 점검 (앙상블 통과 12개)
# ============================================================================
print("="*80)
print("2. 이상치 점검 (앙상블 통과 모델만)")
print("="*80)

# Filter ensemble-pass models with predictions
ensemble_models = [m for m in models if m["json_data"].get("ensemble_pass", False) and m["has_predictions"]]

print(f"\n분석 대상: {len(ensemble_models)}개 모델\n")

print("모델별 Error 통계 (P95, MedianAE):")
print("-" * 90)
print(f"{'모델명':<30} {'OOF P95':>12} {'OOF MedianAE':>15} {'Holdout P95':>12} {'Holdout MedianAE':>15}")
print("-" * 90)

for m in ensemble_models:
    if m["oof_pred"] is None or m["holdout_pred"] is None:
        continue

    # Shape validation
    if len(m["oof_pred"]) != len(y_cv) or len(m["holdout_pred"]) != len(y_holdout):
        print(f"⚠️  {m['name']}: Shape 불일치, 건너뜀")
        continue

    oof_errors = np.abs(m["oof_pred"] - y_cv)
    holdout_errors = np.abs(m["holdout_pred"] - y_holdout)

    # Remove NaN
    oof_errors_valid = oof_errors[~np.isnan(oof_errors)]
    holdout_errors_valid = holdout_errors[~np.isnan(holdout_errors)]

    oof_p95 = np.percentile(oof_errors_valid, 95) if len(oof_errors_valid) > 0 else np.nan
    oof_medianae = np.median(oof_errors_valid) if len(oof_errors_valid) > 0 else np.nan
    holdout_p95 = np.percentile(holdout_errors_valid, 95) if len(holdout_errors_valid) > 0 else np.nan
    holdout_medianae = np.median(holdout_errors_valid) if len(holdout_errors_valid) > 0 else np.nan

    print(f"{m['name']:<30} {oof_p95:>12.4f} {oof_medianae:>15.4f} {holdout_p95:>12.4f} {holdout_medianae:>15.4f}")

# 극단적 오차 샘플 식별 (Top 10 worst errors)
print("\n\n극단적 오차 발생 샘플 (Holdout Top 10):")
print("-" * 90)

# Aggregate errors across all models
all_errors = []
for m in ensemble_models:
    if m["holdout_pred"] is None or len(m["holdout_pred"]) != len(y_holdout):
        continue
    errors = np.abs(m["holdout_pred"] - y_holdout)
    all_errors.append(errors)

if all_errors:
    all_errors_array = np.array(all_errors)  # shape: (n_models, n_holdout)
    mean_errors = np.nanmean(all_errors_array, axis=0)  # Average error across models
    worst_indices = np.argsort(mean_errors)[-10:][::-1]  # Top 10 worst

    print(f"{'Idx':<6} {'실제값':>10} {'평균 오차':>12} {'발생 모델수':>15}")
    print("-" * 90)
    for idx in worst_indices:
        true_val = y_holdout[idx]
        avg_error = mean_errors[idx]
        n_models = (~np.isnan(all_errors_array[:, idx])).sum()
        print(f"{idx:<6} {true_val:>10.4f} {avg_error:>12.4f} {n_models:>15}")

# ============================================================================
# 3. 과적합 점검 (15개 전체)
# ============================================================================
print("\n" + "="*80)
print("3. 과적합 점검 (15개 모델 전체)")
print("="*80)

print("\n모델별 Train vs OOF 성능:")
print("-" * 110)
print(f"{'모델명':<30} {'Train Sp':>12} {'OOF Sp':>12} {'Gap':>10} {'Ratio':>10} {'Fold Std':>12} {'판정':>12}")
print("-" * 110)

for m in models:
    # Extract metrics from JSON
    train_sp = m["json_data"].get("oof_performance", {}).get("train_spearman", None)
    if train_sp is None:
        train_sp = m["json_data"].get("train_spearman", None)

    oof_sp = m["json_data"].get("oof_spearman")
    if oof_sp is None:
        oof_sp = m["json_data"].get("oof_performance", {}).get("oof_spearman", None)

    fold_std = m["json_data"].get("oof_performance", {}).get("fold_std", None)
    if fold_std is None:
        fold_std = m["json_data"].get("fold_std", None)

    if train_sp is not None and oof_sp is not None:
        gap = train_sp - oof_sp
        ratio = oof_sp / train_sp if train_sp > 0 else 0

        # 판정 기준
        if gap < 0.05:
            verdict = "NORMAL"
        elif gap < 0.10:
            verdict = "WARNING"
        elif gap < 0.15:
            verdict = "OVERFITTING"
        else:
            verdict = "SEVERE"

        fold_std_str = f"{fold_std:.4f}" if fold_std is not None else "N/A"

        print(f"{m['name']:<30} {train_sp:>12.4f} {oof_sp:>12.4f} {gap:>10.4f} {ratio:>10.4f} {fold_std_str:>12} {verdict:>12}")
    else:
        # Try to show at least OOF Sp
        oof_sp_str = f"{oof_sp:.4f}" if oof_sp is not None else "N/A"
        fold_std_str = f"{fold_std:.4f}" if fold_std is not None else "N/A"
        print(f"{m['name']:<30} {'N/A':>12} {oof_sp_str:>12} {'N/A':>10} {'N/A':>10} {fold_std_str:>12} {'N/A':>12}")

print("\n" + "="*80)
print("점검 완료!")
print("="*80)
