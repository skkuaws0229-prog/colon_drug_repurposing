#!/usr/bin/env python3
"""
Bilinear v2 학습 스크립트

개선사항:
- learning rate: 1e-3 → 1e-4
- epochs: 100 → 200
- BatchNorm 추가
- gradient clipping: max_norm=1.0
- Drug/Gene block 각각 StandardScaler 적용
"""
import sys
from pathlib import Path

# 모델 경로 추가
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
sys.path.append(str(base_dir / "20260415_v4_ensemble_test/new_models/bilinear"))

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
import json
from datetime import datetime

from bilinear_model_v2 import BilinearInteractionNetV2

print("=" * 100)
print("Bilinear v2 학습")
print("=" * 100)

# 경로 설정
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_dir = base_dir / "20260415_v4_ensemble_test/new_models/bilinear"

# Device
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"\nDevice: {device}")

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[데이터 로드]")
print("-" * 100)

# Feature indices
drug_indices = np.load(crossattn_dir / "drug_feature_indices.npy")
gene_indices = np.load(crossattn_dir / "gene_feature_indices.npy")

print(f"Drug features: {len(drug_indices)}")
print(f"Gene features: {len(gene_indices)}")

# X_train, y_train
X_train = np.load(step4_dir / "X_train.npy")
y_train = np.load(step4_dir / "y_train.npy")

print(f"X_train shape: {X_train.shape}")
print(f"y_train shape: {y_train.shape}")

# Train/Holdout split (v3와 동일)
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
# StandardScaler 적용 (Drug/Gene 각각)
# ============================================================================
print("\n[StandardScaler 적용]")
print("-" * 100)

# Drug features 스케일링
scaler_drug = StandardScaler()
X_cv_drug = X_cv[:, drug_indices]
X_cv_drug_scaled = scaler_drug.fit_transform(X_cv_drug)
X_holdout_drug_scaled = scaler_drug.transform(X_holdout[:, drug_indices])

# Gene features 스케일링
scaler_gene = StandardScaler()
X_cv_gene = X_cv[:, gene_indices]
X_cv_gene_scaled = scaler_gene.fit_transform(X_cv_gene)
X_holdout_gene_scaled = scaler_gene.transform(X_holdout[:, gene_indices])

# 재결합
X_cv_scaled = np.zeros_like(X_cv)
X_cv_scaled[:, drug_indices] = X_cv_drug_scaled
X_cv_scaled[:, gene_indices] = X_cv_gene_scaled

X_holdout_scaled = np.zeros_like(X_holdout)
X_holdout_scaled[:, drug_indices] = X_holdout_drug_scaled
X_holdout_scaled[:, gene_indices] = X_holdout_gene_scaled

print("✓ StandardScaler 적용 완료")
print(f"  Drug features: mean={np.mean(X_cv_drug_scaled):.4f}, std={np.std(X_cv_drug_scaled):.4f}")
print(f"  Gene features: mean={np.mean(X_cv_gene_scaled):.4f}, std={np.std(X_cv_gene_scaled):.4f}")

# ============================================================================
# 학습
# ============================================================================
print("\n[Bilinear v2 학습]")
print("-" * 100)

# 하이퍼파라미터 (개선)
epochs = 200  # 100 → 200
lr = 1e-4  # 1e-3 → 1e-4
batch_size = 64
max_grad_norm = 1.0  # Gradient clipping

print(f"Hyperparameters:")
print(f"  Epochs: {epochs}")
print(f"  Learning rate: {lr}")
print(f"  Batch size: {batch_size}")
print(f"  Max grad norm: {max_grad_norm}")

# 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_cv))
train_predictions = np.zeros(len(y_cv))
fold_train_sps = []
fold_oof_sps = []

for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv_scaled), 1):
    print(f"\nFold {fold_idx}/5:")

    X_tr, X_val = X_cv_scaled[tr_idx], X_cv_scaled[val_idx]
    y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

    # 모델 생성
    model = BilinearInteractionNetV2(
        drug_dim=len(drug_indices),
        gene_dim=len(gene_indices),
        hidden_dim=256,
        emb_dim=128,
        dropout=0.3
    ).to(device)

    X_tr_tensor = torch.FloatTensor(X_tr).to(device)
    y_tr_tensor = torch.FloatTensor(y_tr).to(device)
    X_val_tensor = torch.FloatTensor(X_val).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # 학습
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_tr_tensor, drug_indices, gene_indices)
        loss = criterion(outputs, y_tr_tensor)
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)

        optimizer.step()

        if (epoch + 1) % 40 == 0:
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

# 전체 메트릭
train_sp = np.mean(fold_train_sps)
oof_sp = spearmanr(y_cv, oof_predictions)[0]
oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
gap = train_sp - oof_sp
fold_std = np.std(fold_oof_sps)

print(f"\n전체 메트릭:")
print(f"  Train Spearman: {train_sp:.4f}")
print(f"  OOF Spearman:   {oof_sp:.4f}")
print(f"  OOF RMSE:       {oof_rmse:.4f}")
print(f"  Gap:            {gap:.4f}")
print(f"  Fold Std:       {fold_std:.4f}")

# Final model (전체 CV 데이터로)
print(f"\nFinal model 학습...")
final_model = BilinearInteractionNetV2(
    drug_dim=len(drug_indices),
    gene_dim=len(gene_indices),
    hidden_dim=256,
    emb_dim=128,
    dropout=0.3
).to(device)

X_cv_tensor = torch.FloatTensor(X_cv_scaled).to(device)
y_cv_tensor = torch.FloatTensor(y_cv).to(device)
X_holdout_tensor = torch.FloatTensor(X_holdout_scaled).to(device)

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

final_model.train()
for epoch in range(epochs):
    optimizer.zero_grad()
    outputs = final_model(X_cv_tensor, drug_indices, gene_indices)
    loss = criterion(outputs, y_cv_tensor)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(final_model.parameters(), max_grad_norm)
    optimizer.step()

final_model.eval()
with torch.no_grad():
    holdout_pred = final_model(X_holdout_tensor, drug_indices, gene_indices).cpu().numpy()

holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))

print(f"  Holdout Spearman: {holdout_sp:.4f}")
print(f"  Holdout RMSE:     {holdout_rmse:.4f}")

# ============================================================================
# 저장
# ============================================================================
print(f"\n결과 저장...")

# 1. Model weight
model_path = output_dir / "bilinear_v2_model.pt"
torch.save(final_model.state_dict(), model_path)
print(f"  ✓ Model: {model_path}")

# 2. OOF predictions
oof_path = output_dir / "bilinear_v2_oof.npy"
np.save(oof_path, oof_predictions)
print(f"  ✓ OOF: {oof_path} (shape: {oof_predictions.shape})")

# 3. Holdout predictions
holdout_path = output_dir / "bilinear_v2_holdout.npy"
np.save(holdout_path, holdout_pred)
print(f"  ✓ Holdout: {holdout_path} (shape: {holdout_pred.shape})")

# 4. Scalers
import pickle
scaler_path = output_dir / "bilinear_v2_scalers.pkl"
with open(scaler_path, "wb") as f:
    pickle.dump({'drug': scaler_drug, 'gene': scaler_gene}, f)
print(f"  ✓ Scalers: {scaler_path}")

# 5. Results
results = {
    "model": "Bilinear-v2",
    "timestamp": datetime.now().isoformat(),
    "device": device,
    "hyperparameters": {
        "epochs": epochs,
        "learning_rate": lr,
        "batch_size": batch_size,
        "max_grad_norm": max_grad_norm
    },
    "improvements": [
        "BatchNorm added",
        "Gradient clipping (max_norm=1.0)",
        "StandardScaler on Drug/Gene blocks",
        "Learning rate reduced (1e-3 → 1e-4)",
        "Epochs doubled (100 → 200)"
    ],
    "metrics": {
        "train_spearman": float(train_sp),
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "gap": float(gap),
        "fold_std": float(fold_std)
    },
    "fold_metrics": {
        "fold_train_sps": [float(x) for x in fold_train_sps],
        "fold_oof_sps": [float(x) for x in fold_oof_sps]
    }
}

results_path = output_dir / "bilinear_v2_results.json"
with open(results_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"  ✓ Results: {results_path}")

print(f"\nBilinear v2 학습 완료!")

# ============================================================================
# OOF Spearman 체크 및 CatBoost-Full 상관 측정
# ============================================================================
print("\n" + "=" * 100)
print("성능 판정")
print("=" * 100)

print(f"\nOOF Spearman: {oof_sp:.4f}")

if oof_sp >= 0.75:
    print(f"✅ 합격 (≥ 0.75)! CatBoost-Full과 상관 측정...")

    # CatBoost-Full OOF 로드
    catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")

    from scipy.stats import pearsonr
    pearson_corr = pearsonr(catboost_full_oof, oof_predictions)[0]
    spearman_corr = spearmanr(catboost_full_oof, oof_predictions)[0]

    print(f"  vs CatBoost-Full:")
    print(f"    Pearson:  {pearson_corr:.4f}")
    print(f"    Spearman: {spearman_corr:.4f}")

    # Top-30 Jaccard
    def jaccard_topk(pred1, pred2, k=30):
        top_k1 = set(np.argsort(pred1)[:k])
        top_k2 = set(np.argsort(pred2)[:k])
        intersection = len(top_k1 & top_k2)
        union = len(top_k1 | top_k2)
        return intersection / union, intersection

    jaccard, overlap = jaccard_topk(catboost_full_oof, oof_predictions, 30)
    print(f"    Top-30 Jaccard: {jaccard:.4f} ({overlap}/30)")

    # 상관 결과 저장
    correlation_results = {
        "bilinear_v2_oof_spearman": float(oof_sp),
        "vs_catboost_full": {
            "pearson": float(pearson_corr),
            "spearman": float(spearman_corr),
            "top30_jaccard": float(jaccard),
            "top30_overlap": int(overlap)
        },
        "ensemble_eligible": True
    }

    corr_path = output_dir / "bilinear_v2_correlation.json"
    with open(corr_path, "w") as f:
        json.dump(correlation_results, f, indent=2)
    print(f"  ✓ Correlation: {corr_path}")

    print("\n✅ Bilinear-v2를 앙상블 조합에 추가할 수 있습니다!")

else:
    print(f"❌ 불합격 (< 0.75). 앙상블 조합에 추가하지 않습니다.")

print("\n" + "=" * 100)
