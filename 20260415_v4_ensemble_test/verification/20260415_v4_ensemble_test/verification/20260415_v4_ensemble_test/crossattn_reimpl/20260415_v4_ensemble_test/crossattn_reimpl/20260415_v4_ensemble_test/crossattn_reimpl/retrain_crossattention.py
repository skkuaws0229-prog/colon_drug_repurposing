#!/usr/bin/env python3
"""
RealCrossAttentionModel 재학습
기존 v3와 동일한 조건으로 학습하되, 새 모델 사용
"""
import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from pathlib import Path

# 모델 import
from real_crossattention import RealCrossAttentionModel

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
output_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("RealCrossAttentionModel 재학습")
print("=" * 80)

# Device 설정
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"\nDevice: {device}")

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 80)

# Feature indices
drug_indices = np.load(output_dir / "drug_feature_indices.npy")
gene_indices = np.load(output_dir / "gene_feature_indices.npy")

print(f"Drug features: {len(drug_indices)}")
print(f"Gene features: {len(gene_indices)}")

# X_train, y_train from v3
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
X_train = np.load(step4_dir / "X_train.npy")
y_train = np.load(step4_dir / "y_train.npy")

print(f"X_train shape: {X_train.shape}")
print(f"y_train shape: {y_train.shape}")

# Train/Holdout split (동일하게)
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

print(f"CV samples: {len(X_cv)}")
print(f"Holdout samples: {len(X_holdout)}")

# ============================================================================
# 5-Fold CV 학습
# ============================================================================
print("\n[2] 5-Fold Cross-Validation 학습")
print("-" * 80)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_cv))
train_predictions = np.zeros(len(y_cv))
fold_train_sps = []
fold_oof_sps = []

epochs = 100
lr = 0.001
hidden_dim = 256
n_heads = 4
dropout = 0.3

for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
    print(f"\nFold {fold_idx}/5:")

    X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
    y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

    # 모델 생성
    model = RealCrossAttentionModel(
        drug_dim=len(drug_indices),
        gene_dim=len(gene_indices),
        hidden_dim=hidden_dim,
        n_heads=n_heads,
        dropout=dropout
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Tensor 변환
    X_tr_tensor = torch.FloatTensor(X_tr).to(device)
    y_tr_tensor = torch.FloatTensor(y_tr).to(device)
    X_val_tensor = torch.FloatTensor(X_val).to(device)

    # 학습
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_tr_tensor, drug_indices, gene_indices)
        loss = criterion(outputs, y_tr_tensor)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

    # 평가
    model.eval()
    with torch.no_grad():
        train_pred = model(X_tr_tensor, drug_indices, gene_indices).cpu().numpy()
        val_pred = model(X_val_tensor, drug_indices, gene_indices).cpu().numpy()

    train_predictions[tr_idx] = train_pred
    oof_predictions[val_idx] = val_pred

    train_sp = spearmanr(y_tr, train_pred)[0]
    val_sp = spearmanr(y_val, val_pred)[0]

    fold_train_sps.append(train_sp)
    fold_oof_sps.append(val_sp)

    print(f"  Train Sp: {train_sp:.4f}, OOF Sp: {val_sp:.4f}")

# ============================================================================
# 전체 메트릭
# ============================================================================
print("\n[3] 전체 메트릭")
print("-" * 80)

train_sp = np.mean(fold_train_sps)
oof_sp = spearmanr(y_cv, oof_predictions)[0]
oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
gap = train_sp - oof_sp
ratio = oof_sp / train_sp if train_sp > 0 else 0
fold_std = np.std(fold_oof_sps)

print(f"Train Spearman:     {train_sp:.4f}")
print(f"OOF Spearman:       {oof_sp:.4f}")
print(f"OOF RMSE:           {oof_rmse:.4f}")
print(f"Gap:                {gap:.4f}")
print(f"Train/OOF Ratio:    {ratio:.4f}")
print(f"Fold Std:           {fold_std:.4f}")

# 성능 판정
print("\n성능 판정:")
print("-" * 80)
if oof_sp >= 0.75:
    verdict = "✅ 성공 (OOF Sp ≥ 0.75)"
    status = "success"
elif oof_sp >= 0.70:
    verdict = "⚠️  경고 (0.70 ≤ OOF Sp < 0.75)"
    status = "warning"
else:
    verdict = "❌ 실패 (OOF Sp < 0.70) - Attention 구현 문제 가능성"
    status = "failed"

print(f"{verdict}")
print(f"기존 CrossAttention OOF Sp: 0.824")
print(f"새 모델 OOF Sp:             {oof_sp:.4f}")
print(f"차이:                       {oof_sp - 0.824:.4f}")

# ============================================================================
# Final Model 학습 (전체 CV 데이터)
# ============================================================================
print("\n[4] Final Model 학습")
print("-" * 80)

final_model = RealCrossAttentionModel(
    drug_dim=len(drug_indices),
    gene_dim=len(gene_indices),
    hidden_dim=hidden_dim,
    n_heads=n_heads,
    dropout=dropout
).to(device)

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

X_cv_tensor = torch.FloatTensor(X_cv).to(device)
y_cv_tensor = torch.FloatTensor(y_cv).to(device)
X_holdout_tensor = torch.FloatTensor(X_holdout).to(device)

final_model.train()
for epoch in range(epochs):
    optimizer.zero_grad()
    outputs = final_model(X_cv_tensor, drug_indices, gene_indices)
    loss = criterion(outputs, y_cv_tensor)
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 20 == 0:
        print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

# Holdout 평가
final_model.eval()
with torch.no_grad():
    holdout_pred = final_model(X_holdout_tensor, drug_indices, gene_indices).cpu().numpy()

holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))

print(f"\nHoldout Spearman: {holdout_sp:.4f}")
print(f"Holdout RMSE:     {holdout_rmse:.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[5] 결과 저장")
print("-" * 80)

# 1. Model weights
model_path = output_dir / "real_crossattention_model.pt"
torch.save(final_model.state_dict(), model_path)
print(f"✓ Model: {model_path}")

# 2. OOF predictions
oof_path = output_dir / "real_crossattention_oof.npy"
np.save(oof_path, oof_predictions)
print(f"✓ OOF predictions: {oof_path}")

# 3. Train predictions
train_path = output_dir / "real_crossattention_train.npy"
np.save(train_path, train_predictions)
print(f"✓ Train predictions: {train_path}")

# 4. Holdout predictions
holdout_path = output_dir / "real_crossattention_holdout.npy"
np.save(holdout_path, holdout_pred)
print(f"✓ Holdout predictions: {holdout_path}")

# 5. Metadata JSON
results = {
    "model": "RealCrossAttentionModel",
    "device": device,
    "architecture": {
        "drug_dim": len(drug_indices),
        "gene_dim": len(gene_indices),
        "hidden_dim": hidden_dim,
        "n_heads": n_heads,
        "dropout": dropout,
        "total_parameters": sum(p.numel() for p in final_model.parameters())
    },
    "training": {
        "epochs": epochs,
        "learning_rate": lr,
        "optimizer": "Adam",
        "loss": "MSELoss",
        "cv_folds": 5,
        "random_seed": 42
    },
    "metrics": {
        "train_spearman": float(train_sp),
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "gap": float(gap),
        "ratio": float(ratio),
        "fold_std": float(fold_std)
    },
    "fold_metrics": {
        "fold_train_sps": [float(x) for x in fold_train_sps],
        "fold_oof_sps": [float(x) for x in fold_oof_sps]
    },
    "comparison": {
        "old_crossattention_oof_sp": 0.824,
        "new_crossattention_oof_sp": float(oof_sp),
        "difference": float(oof_sp - 0.824)
    },
    "verdict": {
        "status": status,
        "message": verdict
    }
}

json_path = output_dir / "real_crossattention_results.json"
with open(json_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"✓ Metadata: {json_path}")

print("\n" + "=" * 80)
print("재학습 완료!")
print("=" * 80)
print(f"\n최종 판정: {verdict}")
print(f"\nOOF predictions 경로: {oof_path}")
print(f"다음 단계: FlatMLP와 예측값 비교")
