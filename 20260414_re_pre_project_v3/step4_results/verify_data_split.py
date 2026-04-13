#!/usr/bin/env python3
"""
이전 학습과 재학습의 데이터 split 일치 여부 확인
"""
import numpy as np
import os

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("이전 학습 vs 재학습 데이터 split 검증")
print("="*80)

# Load ground truth
y_train = np.load("y_train.npy")

# Recreate split (재학습에서 사용한 방식)
n_samples = len(y_train)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

y_cv_new = y_train[train_idx]
y_holdout_new = y_train[holdout_idx]

print(f"\n재학습 split (seed=42, 80/20):")
print(f"  Total samples: {n_samples}")
print(f"  Train CV: {len(y_cv_new)}")
print(f"  Holdout: {len(y_holdout_new)}")
print(f"  Holdout 샘플 인덱스 (처음 10개): {holdout_idx[:10]}")

# Compare with existing holdout predictions
print("\n" + "="*80)
print("기존 모델 vs 재학습 모델 Holdout 예측값 비교")
print("="*80)

models_to_check = [
    (4, "CatBoost", "model_04_catboost_holdout.npy", "model_04_holdout.npy"),
    (5, "RandomForest", "model_05_randomforest_holdout.npy", "model_05_holdout.npy"),
    (7, "Stacking", "model_07_stacking_holdout.npy", "model_07_holdout.npy"),
]

all_match = True

for model_id, model_name, old_file, new_file in models_to_check:
    print(f"\n{model_name} (Model {model_id:02d}):")

    if not os.path.exists(old_file):
        print(f"  ⚠️  기존 파일 없음: {old_file}")
        continue

    if not os.path.exists(new_file):
        print(f"  ⚠️  재학습 파일 없음: {new_file}")
        continue

    old_pred = np.load(old_file)
    new_pred = np.load(new_file)

    print(f"  기존 holdout shape: {old_pred.shape}")
    print(f"  재학습 holdout shape: {new_pred.shape}")

    if old_pred.shape != new_pred.shape:
        print(f"  ❌ Shape 불일치! 데이터 split이 다름!")
        all_match = False
        continue

    # Check if predictions are for the same samples
    # by comparing correlation with ground truth
    old_corr = np.corrcoef(old_pred, y_holdout_new)[0, 1]
    new_corr = np.corrcoef(new_pred, y_holdout_new)[0, 1]

    print(f"  기존 예측 vs 재학습 ground truth 상관계수: {old_corr:.6f}")
    print(f"  재학습 예측 vs 재학습 ground truth 상관계수: {new_corr:.6f}")

    # Check if predictions are identical (same model, same data)
    pred_diff = np.abs(old_pred - new_pred)
    max_diff = pred_diff.max()
    mean_diff = pred_diff.mean()

    print(f"  예측값 차이: max={max_diff:.6f}, mean={mean_diff:.6f}")

    if max_diff < 1e-5:
        print(f"  ✅ 예측값 동일 (차이 < 1e-5) → 데이터 split 동일!")
    elif old_corr > 0.99 and new_corr > 0.99:
        print(f"  ✅ Ground truth 상관계수 모두 높음 → 데이터 split 동일 (모델만 다름)")
    else:
        print(f"  ❌ 데이터 split이 다르거나 문제 있음!")
        all_match = False

# Check original training scripts for seed
print("\n" + "="*80)
print("원본 학습 스크립트 seed 확인")
print("="*80)

scripts_to_check = [
    "train_ml_models.py",
    "train_dl_models.py",
    "train_stacking.py"
]

for script in scripts_to_check:
    if os.path.exists(f"../{script}"):
        print(f"\n{script}:")
        os.system(f"grep -n 'seed.*=' ../{script} | head -5")
    elif os.path.exists(script):
        print(f"\n{script}:")
        os.system(f"grep -n 'seed.*=' {script} | head -5")

print("\n" + "="*80)
if all_match:
    print("✅ 결론: 데이터 split 일치 - 이전 결과와 비교 가능")
else:
    print("❌ 결론: 데이터 split 불일치 - 이전 결과와 비교 불가능!")
print("="*80)
