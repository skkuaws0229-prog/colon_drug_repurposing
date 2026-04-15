"""
멀티모달 Step 2: Chemprop MPNN 학습

학습 설정:
- seed=42
- 5-fold CV with OOF predictions
- 20% holdout
- Gene features as extra features
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr
import json
import time
import subprocess
import tempfile
import os

print("=" * 100)
print("Chemprop MPNN 학습")
print("=" * 100)

# 경로 설정
step2_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260415_multimodal_pipeline/step2_mpnn")
input_path = step2_dir / "chemprop_input.csv"

# [1] 데이터 로드
print("\n[1] 데이터 로드")
print("-" * 100)
df = pd.read_csv(input_path)
print(f"✓ Shape: {df.shape}")
print(f"✓ Columns: {len(df.columns)} (smiles + target + {len(df.columns)-2} gene features)")

# [2] Holdout split (80/20, seed=42)
print("\n[2] Holdout Split (80/20)")
print("-" * 100)
np.random.seed(42)
n_samples = len(df)
indices = np.arange(n_samples)
np.random.shuffle(indices)

n_train = int(0.8 * n_samples)
train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

df_train = df.iloc[train_idx].reset_index(drop=True)
df_holdout = df.iloc[holdout_idx].reset_index(drop=True)

print(f"  - Train: {len(df_train)} samples")
print(f"  - Holdout: {len(df_holdout)} samples")

# Train/Holdout 파일 저장
train_path = step2_dir / "train.csv"
holdout_path = step2_dir / "holdout.csv"
df_train.to_csv(train_path, index=False)
df_holdout.to_csv(holdout_path, index=False)
print(f"  - Train saved: {train_path}")
print(f"  - Holdout saved: {holdout_path}")

# [3] 5-Fold CV with OOF
print("\n[3] 5-Fold Cross-Validation")
print("-" * 100)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(df_train))
oof_targets = df_train['target'].values
fold_metrics = []

for fold_idx, (train_fold_idx, val_fold_idx) in enumerate(kf.split(df_train), 1):
    print(f"\n--- Fold {fold_idx}/5 ---")

    # Fold 데이터 분할
    df_train_fold = df_train.iloc[train_fold_idx].reset_index(drop=True)
    df_val_fold = df_train.iloc[val_fold_idx].reset_index(drop=True)

    print(f"  Train: {len(df_train_fold)}, Val: {len(df_val_fold)}")

    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_train:
        df_train_fold.to_csv(f_train.name, index=False)
        train_fold_path = f_train.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f_val:
        df_val_fold.to_csv(f_val.name, index=False)
        val_fold_path = f_val.name

    # Chemprop 모델 저장 경로
    model_dir = step2_dir / f"model_fold{fold_idx}"
    model_dir.mkdir(exist_ok=True)

    # Chemprop 학습 명령어
    # --features_only: gene features만 사용 (SMILES는 MPNN으로 인코딩)
    # --num_workers 0: macOS에서 multiprocessing 이슈 방지
    cmd = [
        "chemprop_train",
        "--data_path", train_fold_path,
        "--dataset_type", "regression",
        "--save_dir", str(model_dir),
        "--epochs", "30",
        "--batch_size", "50",
        "--hidden_size", "300",
        "--depth", "3",
        "--dropout", "0.1",
        "--seed", "42",
        "--quiet"
    ]

    print(f"  Training...")
    start_time = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30분 timeout
        if result.returncode != 0:
            print(f"  ⚠️  Training failed:")
            print(f"  STDOUT: {result.stdout}")
            print(f"  STDERR: {result.stderr}")
            os.unlink(train_fold_path)
            os.unlink(val_fold_path)
            continue
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Training timeout (30 min)")
        os.unlink(train_fold_path)
        os.unlink(val_fold_path)
        continue

    training_time = time.time() - start_time
    print(f"  Training time: {training_time:.1f}s")

    # Prediction
    pred_path = step2_dir / f"pred_fold{fold_idx}.csv"
    cmd_predict = [
        "chemprop_predict",
        "--test_path", val_fold_path,
        "--checkpoint_dir", str(model_dir),
        "--preds_path", str(pred_path)
    ]

    print(f"  Predicting...")
    result = subprocess.run(cmd_predict, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠️  Prediction failed:")
        print(f"  STDERR: {result.stderr}")
        os.unlink(train_fold_path)
        os.unlink(val_fold_path)
        continue

    # OOF 예측 로드
    df_pred = pd.read_csv(pred_path)
    val_preds = df_pred.iloc[:, -1].values  # 마지막 컬럼이 예측값

    # OOF 저장
    oof_preds[val_fold_idx] = val_preds

    # Fold 평가
    val_targets = df_val_fold['target'].values
    fold_sp = spearmanr(val_targets, val_preds)[0]
    fold_rmse = np.sqrt(mean_squared_error(val_targets, val_preds))

    print(f"  Val Spearman: {fold_sp:.4f}")
    print(f"  Val RMSE: {fold_rmse:.4f}")

    fold_metrics.append({
        'fold': fold_idx,
        'spearman': float(fold_sp),
        'rmse': float(fold_rmse),
        'training_time': training_time
    })

    # 임시 파일 삭제
    os.unlink(train_fold_path)
    os.unlink(val_fold_path)

# OOF 평가
print(f"\n--- OOF 전체 평가 ---")
oof_sp = spearmanr(oof_targets, oof_preds)[0]
oof_rmse = np.sqrt(mean_squared_error(oof_targets, oof_preds))
print(f"  OOF Spearman: {oof_sp:.4f}")
print(f"  OOF RMSE: {oof_rmse:.4f}")

# OOF 저장
oof_save_path = step2_dir / "mpnn_oof.npy"
np.save(oof_save_path, oof_preds)
print(f"  ✓ OOF saved: {oof_save_path}")

# [4] Final model on full train + Holdout prediction
print("\n[4] Final Model Training (Full Train)")
print("-" * 100)

final_model_dir = step2_dir / "model_final"
final_model_dir.mkdir(exist_ok=True)

cmd_final = [
    "chemprop_train",
    "--data_path", str(train_path),
    "--dataset_type", "regression",
    "--save_dir", str(final_model_dir),
    "--epochs", "30",
    "--batch_size", "50",
    "--hidden_size", "300",
    "--depth", "3",
    "--dropout", "0.1",
    "--seed", "42",
    "--quiet"
]

print(f"  Training final model...")
start_time = time.time()
result = subprocess.run(cmd_final, capture_output=True, text=True, timeout=1800)

if result.returncode != 0:
    print(f"  ⚠️  Final training failed:")
    print(f"  STDERR: {result.stderr}")
else:
    final_training_time = time.time() - start_time
    print(f"  Training time: {final_training_time:.1f}s")

    # Holdout prediction
    holdout_pred_path = step2_dir / "pred_holdout.csv"
    cmd_predict_holdout = [
        "chemprop_predict",
        "--test_path", str(holdout_path),
        "--checkpoint_dir", str(final_model_dir),
        "--preds_path", str(holdout_pred_path)
    ]

    print(f"  Predicting on holdout...")
    result = subprocess.run(cmd_predict_holdout, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠️  Holdout prediction failed:")
        print(f"  STDERR: {result.stderr}")
    else:
        # Holdout 평가
        df_holdout_pred = pd.read_csv(holdout_pred_path)
        holdout_preds = df_holdout_pred.iloc[:, -1].values
        holdout_targets = df_holdout['target'].values

        holdout_sp = spearmanr(holdout_targets, holdout_preds)[0]
        holdout_rmse = np.sqrt(mean_squared_error(holdout_targets, holdout_preds))

        print(f"  Holdout Spearman: {holdout_sp:.4f}")
        print(f"  Holdout RMSE: {holdout_rmse:.4f}")

        # Holdout 저장
        holdout_save_path = step2_dir / "mpnn_holdout.npy"
        np.save(holdout_save_path, holdout_preds)
        print(f"  ✓ Holdout saved: {holdout_save_path}")

# [5] 학습 로그 저장
print("\n[5] 학습 로그 저장")
print("-" * 100)

log = {
    'experiment': {
        'date': time.strftime('%Y-%m-%d'),
        'model': 'Chemprop MPNN',
        'n_samples_total': n_samples,
        'n_train': len(df_train),
        'n_holdout': len(df_holdout),
        'n_gene_features': len(df.columns) - 2,
        'seed': 42
    },
    'cv': {
        'n_folds': 5,
        'fold_metrics': fold_metrics,
        'oof_spearman': float(oof_sp),
        'oof_rmse': float(oof_rmse),
        'mean_fold_spearman': np.mean([f['spearman'] for f in fold_metrics]),
        'std_fold_spearman': np.std([f['spearman'] for f in fold_metrics])
    },
    'holdout': {
        'spearman': float(holdout_sp) if 'holdout_sp' in locals() else None,
        'rmse': float(holdout_rmse) if 'holdout_rmse' in locals() else None
    },
    'hyperparameters': {
        'epochs': 30,
        'batch_size': 50,
        'hidden_size': 300,
        'depth': 3,
        'dropout': 0.1
    }
}

log_path = step2_dir / "mpnn_train_log.json"
with open(log_path, 'w') as f:
    json.dump(log, f, indent=2)
print(f"✓ Log saved: {log_path}")

print("\n" + "=" * 100)
print("✅ Chemprop MPNN 학습 완료!")
print("=" * 100)
print(f"  - OOF Spearman: {oof_sp:.4f}")
print(f"  - Holdout Spearman: {holdout_sp:.4f}" if 'holdout_sp' in locals() else "  - Holdout: Failed")
print(f"  - OOF saved: {oof_save_path}")
print(f"  - Holdout saved: {holdout_save_path}" if 'holdout_save_path' in locals() else "")
