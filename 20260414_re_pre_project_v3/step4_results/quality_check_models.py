#!/usr/bin/env python3
"""
15개 모델 품질 점검 스크립트
1. 결측치 점검
2. 이상치 점검
3. 과적합 점검
"""
import os
import json
import numpy as np
from scipy.stats import spearmanr
import glob

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("15개 모델 품질 점검")
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

    # Load OOF and Holdout predictions
    oof_file = json_file.replace(".json", "_oof.npy")
    holdout_file = json_file.replace(".json", "_holdout.npy")

    if not os.path.exists(oof_file) or not os.path.exists(holdout_file):
        print(f"⚠️  Model {model_id} ({model_name}): 예측 파일 없음")
        continue

    oof_pred = np.load(oof_file)
    holdout_pred = np.load(holdout_file)

    models.append({
        "id": model_id,
        "name": model_name,
        "oof_pred": oof_pred,
        "holdout_pred": holdout_pred,
        "json_data": data
    })

print(f"\n✓ {len(models)}개 모델 로드 완료\n")

# ============================================================================
# 1. 결측치 점검
# ============================================================================
print("="*80)
print("1. 결측치 점검")
print("="*80)

nan_issues = []
for m in models:
    oof_nans = np.isnan(m["oof_pred"]).sum()
    holdout_nans = np.isnan(m["holdout_pred"]).sum()

    if oof_nans > 0 or holdout_nans > 0:
        nan_issues.append({
            "model": m["name"],
            "oof_nans": oof_nans,
            "holdout_nans": holdout_nans
        })
        print(f"❌ {m['name']}: OOF NaN={oof_nans}, Holdout NaN={holdout_nans}")
    else:
        print(f"✓ {m['name']}: NaN 없음")

if not nan_issues:
    print("\n✓ 모든 모델 NaN 없음!")
else:
    print(f"\n⚠️  {len(nan_issues)}개 모델에서 NaN 발견")
    # GAT 특별 점검
    gat_model = next((m for m in models if "GAT" in m["name"]), None)
    if gat_model:
        print(f"\n=== GAT NaN 원인 분석 ===")
        holdout_pred = gat_model["holdout_pred"]
        print(f"Holdout 예측값 shape: {holdout_pred.shape}")
        print(f"NaN 개수: {np.isnan(holdout_pred).sum()}")
        print(f"Inf 개수: {np.isinf(holdout_pred).sum()}")
        print(f"유효값 개수: {(~np.isnan(holdout_pred)).sum()}")
        if np.isnan(holdout_pred).sum() > 0:
            print(f"→ Holdout Spearman NaN 원인: 예측값에 NaN 포함")

# ============================================================================
# 2. 이상치 점검
# ============================================================================
print("\n" + "="*80)
print("2. 이상치 점검")
print("="*80)

print("\n모델별 P95 Absolute Error (상위 5% 최악 오차):")
print("-" * 80)
print(f"{'모델명':<30} {'OOF P95 Error':>15} {'Holdout P95 Error':>20}")
print("-" * 80)

for m in models:
    # OOF와 Holdout의 실제 ground truth를 각각의 shape에 맞춰 사용
    oof_len = len(m["oof_pred"])
    holdout_len = len(m["holdout_pred"])

    # y_cv와 y_holdout는 이미 위에서 계산된 것 사용
    # shape 검증
    if oof_len != len(y_cv):
        print(f"⚠️  {m['name']}: OOF shape 불일치 ({oof_len} vs {len(y_cv)})")
        continue
    if holdout_len != len(y_holdout):
        print(f"⚠️  {m['name']}: Holdout shape 불일치 ({holdout_len} vs {len(y_holdout)})")
        continue

    oof_errors = np.abs(m["oof_pred"] - y_cv)
    holdout_errors = np.abs(m["holdout_pred"] - y_holdout)

    # NaN 제거
    oof_errors = oof_errors[~np.isnan(oof_errors)]
    holdout_errors = holdout_errors[~np.isnan(holdout_errors)]

    oof_p95 = np.percentile(oof_errors, 95) if len(oof_errors) > 0 else np.nan
    holdout_p95 = np.percentile(holdout_errors, 95) if len(holdout_errors) > 0 else np.nan

    print(f"{m['name']:<30} {oof_p95:>15.4f} {holdout_p95:>20.4f}")

# Fold별 Spearman std (JSON에 fold별 결과가 있다면)
print("\n\nFold별 성능 편차 (fold_std):")
print("-" * 80)
print(f"{'모델명':<30} {'Fold Std':>15} {'판정':>10}")
print("-" * 80)

for m in models:
    fold_std = m["json_data"].get("oof_performance", {}).get("fold_std", None)
    if fold_std is None:
        fold_std = m["json_data"].get("fold_std", None)

    if fold_std is not None:
        verdict = "안정" if fold_std < 0.02 else "주의" if fold_std < 0.05 else "불안정"
        print(f"{m['name']:<30} {fold_std:>15.4f} {verdict:>10}")
    else:
        print(f"{m['name']:<30} {'N/A':>15} {'N/A':>10}")

# ============================================================================
# 3. 과적합 점검
# ============================================================================
print("\n" + "="*80)
print("3. 과적합 점검")
print("="*80)

print("\n모델별 Train vs OOF 성능:")
print("-" * 100)
print(f"{'모델명':<30} {'Train Sp':>12} {'OOF Sp':>12} {'Gap':>12} {'Ratio':>12} {'판정':>10}")
print("-" * 100)

for m in models:
    # Train Spearman
    train_sp = m["json_data"].get("oof_performance", {}).get("train_spearman", None)
    if train_sp is None:
        train_sp = m["json_data"].get("train_spearman", None)

    # OOF Spearman
    oof_sp = m["json_data"].get("oof_spearman") or m["json_data"].get("oof_performance", {}).get("oof_spearman", None)

    if train_sp is not None and oof_sp is not None:
        gap = train_sp - oof_sp
        ratio = oof_sp / train_sp if train_sp > 0 else 0

        # 판정 기준
        if gap < 0.05:
            verdict = "정상"
        elif gap < 0.10:
            verdict = "경미"
        elif gap < 0.15:
            verdict = "과적합"
        else:
            verdict = "심각"

        print(f"{m['name']:<30} {train_sp:>12.4f} {oof_sp:>12.4f} {gap:>12.4f} {ratio:>12.4f} {verdict:>10}")
    else:
        print(f"{m['name']:<30} {'N/A':>12} {oof_sp if oof_sp else 'N/A':>12} {'N/A':>12} {'N/A':>12} {'N/A':>10}")

print("\n" + "="*80)
print("점검 완료!")
print("="*80)
