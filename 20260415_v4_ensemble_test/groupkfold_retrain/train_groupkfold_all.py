#!/usr/bin/env python3
"""
GroupKFold 재학습 (올바른 방식)

v3처럼 GroupKFold로 모델을 재학습하여 unseen drug 일반화 측정

재학습 대상:
1. CatBoost-Full
2. CatBoost-Drug
3. Bilinear v2
4. Drug+Bilinear 앙상블

vs v3 baseline: CatBoost GroupKFold = 0.491
"""
import sys
from pathlib import Path

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
sys.path.append(str(base_dir / "20260415_v4_ensemble_test/new_models/bilinear"))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold
from catboost import CatBoostRegressor
import json
from datetime import datetime
import gc

from bilinear_model_v2 import BilinearInteractionNetV2
from sklearn.preprocessing import StandardScaler

print("=" * 100)
print("GroupKFold 재학습 (올바른 방식)")
print("=" * 100)

# 경로 설정
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_dir = base_dir / "20260415_v4_ensemble_test/groupkfold_retrain"

# Device
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"\nDevice: {device}")

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# Features + Drug IDs
features_df = pd.read_parquet(base_dir / "20260414_re_pre_project_v3/features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
drug_ids = features_df['canonical_drug_id'].values

# y_train
y = np.load(step4_dir / "y_train.npy")

print(f"✓ Features: {X.shape}")
print(f"✓ Labels: {y.shape}")
print(f"✓ Unique drugs: {len(np.unique(drug_ids))}")

# Drug/Gene indices
drug_indices = np.load(crossattn_dir / "drug_feature_indices.npy")
gene_indices = np.load(crossattn_dir / "gene_feature_indices.npy")

print(f"✓ Drug features: {len(drug_indices)}")
print(f"✓ Gene features: {len(gene_indices)}")

# ============================================================================
# 2. CatBoost-Full GroupKFold
# ============================================================================
print("\n" + "=" * 100)
print("[2] CatBoost-Full GroupKFold 재학습")
print("=" * 100)

gkf = GroupKFold(n_splits=5)
catboost_full_oof = np.zeros(len(y))
catboost_full_fold_sps = []

for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids), 1):
    print(f"\nFold {fold_idx}/5:")

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    train_drugs = set(drug_ids[train_idx])
    val_drugs = set(drug_ids[val_idx])
    overlap = train_drugs & val_drugs

    print(f"  Train: {len(train_idx)} samples, {len(train_drugs)} drugs")
    print(f"  Val:   {len(val_idx)} samples, {len(val_drugs)} drugs")
    print(f"  Overlap: {len(overlap)} (should be 0!)")

    if len(overlap) > 0:
        raise ValueError(f"Fold {fold_idx}: Train/Val drug overlap detected!")

    # CatBoost 학습
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function='RMSE',
        random_seed=42,
        verbose=False
    )
    model.fit(X_train, y_train)

    # Val 예측
    val_pred = model.predict(X_val)
    catboost_full_oof[val_idx] = val_pred

    val_sp = spearmanr(y_val, val_pred)[0]
    catboost_full_fold_sps.append(val_sp)

    print(f"  Val Spearman: {val_sp:.4f}")

catboost_full_mean_sp = np.mean(catboost_full_fold_sps)
catboost_full_std_sp = np.std(catboost_full_fold_sps)
catboost_full_rmse = np.sqrt(np.mean((y - catboost_full_oof) ** 2))

print(f"\nCatBoost-Full GroupKFold 결과:")
print(f"  Mean Spearman: {catboost_full_mean_sp:.4f} ± {catboost_full_std_sp:.4f}")
print(f"  RMSE: {catboost_full_rmse:.4f}")
print(f"  vs v3 (0.491): {catboost_full_mean_sp - 0.491:+.4f}")

# 저장
np.save(output_dir / "catboost_full_groupkfold_oof.npy", catboost_full_oof)

# ============================================================================
# 3. CatBoost-Drug GroupKFold
# ============================================================================
print("\n" + "=" * 100)
print("[3] CatBoost-Drug GroupKFold 재학습")
print("=" * 100)

catboost_drug_oof = np.zeros(len(y))
catboost_drug_fold_sps = []

for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids), 1):
    print(f"\nFold {fold_idx}/5:")

    X_train_drug = X[train_idx][:, drug_indices]
    X_val_drug = X[val_idx][:, drug_indices]
    y_train, y_val = y[train_idx], y[val_idx]

    print(f"  Train: {X_train_drug.shape}")
    print(f"  Val:   {X_val_drug.shape}")

    # CatBoost 학습
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function='RMSE',
        random_seed=42,
        verbose=False
    )
    model.fit(X_train_drug, y_train)

    # Val 예측
    val_pred = model.predict(X_val_drug)
    catboost_drug_oof[val_idx] = val_pred

    val_sp = spearmanr(y_val, val_pred)[0]
    catboost_drug_fold_sps.append(val_sp)

    print(f"  Val Spearman: {val_sp:.4f}")

catboost_drug_mean_sp = np.mean(catboost_drug_fold_sps)
catboost_drug_std_sp = np.std(catboost_drug_fold_sps)
catboost_drug_rmse = np.sqrt(np.mean((y - catboost_drug_oof) ** 2))

print(f"\nCatBoost-Drug GroupKFold 결과:")
print(f"  Mean Spearman: {catboost_drug_mean_sp:.4f} ± {catboost_drug_std_sp:.4f}")
print(f"  RMSE: {catboost_drug_rmse:.4f}")
print(f"  vs CatBoost-Full: {catboost_drug_mean_sp - catboost_full_mean_sp:+.4f}")

# 저장
np.save(output_dir / "catboost_drug_groupkfold_oof.npy", catboost_drug_oof)

# ============================================================================
# 4. Bilinear v2 GroupKFold
# ============================================================================
print("\n" + "=" * 100)
print("[4] Bilinear v2 GroupKFold 재학습")
print("=" * 100)

bilinear_oof = np.zeros(len(y))
bilinear_fold_sps = []

epochs = 200
lr = 1e-4
batch_size = 64
max_grad_norm = 1.0

for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids), 1):
    print(f"\nFold {fold_idx}/5:")

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    # StandardScaler 적용 (Drug/Gene 각각)
    scaler_drug = StandardScaler()
    scaler_gene = StandardScaler()

    X_train_drug = scaler_drug.fit_transform(X_train[:, drug_indices])
    X_train_gene = scaler_gene.fit_transform(X_train[:, gene_indices])

    X_val_drug = scaler_drug.transform(X_val[:, drug_indices])
    X_val_gene = scaler_gene.transform(X_val[:, gene_indices])

    X_train_scaled = np.zeros_like(X_train)
    X_train_scaled[:, drug_indices] = X_train_drug
    X_train_scaled[:, gene_indices] = X_train_gene

    X_val_scaled = np.zeros_like(X_val)
    X_val_scaled[:, drug_indices] = X_val_drug
    X_val_scaled[:, gene_indices] = X_val_gene

    print(f"  Train: {X_train_scaled.shape}")
    print(f"  Val:   {X_val_scaled.shape}")

    # Bilinear 모델 생성
    model = BilinearInteractionNetV2(
        drug_dim=len(drug_indices),
        gene_dim=len(gene_indices),
        hidden_dim=256,
        emb_dim=128,
        dropout=0.3
    ).to(device)

    X_train_tensor = torch.FloatTensor(X_train_scaled).to(device)
    y_train_tensor = torch.FloatTensor(y_train).to(device)
    X_val_tensor = torch.FloatTensor(X_val_scaled).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # 학습
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train_tensor, drug_indices, gene_indices)
        loss = criterion(outputs, y_train_tensor)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            print(f"    Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

    # Val 예측
    model.eval()
    with torch.no_grad():
        val_pred = model(X_val_tensor, drug_indices, gene_indices).cpu().numpy()

    bilinear_oof[val_idx] = val_pred

    val_sp = spearmanr(y_val, val_pred)[0]
    bilinear_fold_sps.append(val_sp)

    print(f"  Val Spearman: {val_sp:.4f}")

    # Memory cleanup
    del model, X_train_tensor, y_train_tensor, X_val_tensor
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

bilinear_mean_sp = np.mean(bilinear_fold_sps)
bilinear_std_sp = np.std(bilinear_fold_sps)
bilinear_rmse = np.sqrt(np.mean((y - bilinear_oof) ** 2))

print(f"\nBilinear v2 GroupKFold 결과:")
print(f"  Mean Spearman: {bilinear_mean_sp:.4f} ± {bilinear_std_sp:.4f}")
print(f"  RMSE: {bilinear_rmse:.4f}")
print(f"  vs CatBoost-Drug: {bilinear_mean_sp - catboost_drug_mean_sp:+.4f}")

# 저장
np.save(output_dir / "bilinear_v2_groupkfold_oof.npy", bilinear_oof)

# ============================================================================
# 5. Drug+Bilinear 앙상블
# ============================================================================
print("\n" + "=" * 100)
print("[5] Drug+Bilinear 앙상블 (GroupKFold OOF)")
print("=" * 100)

# Weighted ensemble
drug_sp = catboost_drug_mean_sp
bilinear_sp = bilinear_mean_sp

w_drug = max(drug_sp, 0)
w_bilinear = max(bilinear_sp, 0)
total = w_drug + w_bilinear

w_drug /= total
w_bilinear /= total

drug_bilinear_oof = w_drug * catboost_drug_oof + w_bilinear * bilinear_oof

drug_bilinear_sp = spearmanr(y, drug_bilinear_oof)[0]
drug_bilinear_rmse = np.sqrt(np.mean((y - drug_bilinear_oof) ** 2))

print(f"Weighted Ensemble:")
print(f"  Drug weight: {w_drug:.4f}")
print(f"  Bilinear weight: {w_bilinear:.4f}")
print(f"  Ensemble Spearman: {drug_bilinear_sp:.4f}")
print(f"  RMSE: {drug_bilinear_rmse:.4f}")
print(f"  vs CatBoost-Drug: {drug_bilinear_sp - catboost_drug_mean_sp:+.4f}")
print(f"  vs CatBoost-Full: {drug_bilinear_sp - catboost_full_mean_sp:+.4f}")

# 저장
np.save(output_dir / "drug_bilinear_groupkfold_oof.npy", drug_bilinear_oof)

# ============================================================================
# 6. 결과 요약
# ============================================================================
print("\n" + "=" * 100)
print("[6] GroupKFold 재학습 결과 요약")
print("=" * 100)

v3_baseline = 0.491

print("\n| Model | GroupKFold Sp | RMSE | vs v3 (0.491) | 판정 |")
print("|-------|---------------|------|---------------|------|")

results_summary = [
    ("CatBoost-Full", catboost_full_mean_sp, catboost_full_std_sp, catboost_full_rmse),
    ("CatBoost-Drug", catboost_drug_mean_sp, catboost_drug_std_sp, catboost_drug_rmse),
    ("Bilinear-v2", bilinear_mean_sp, bilinear_std_sp, bilinear_rmse),
    ("Drug+Bilinear", drug_bilinear_sp, 0.0, drug_bilinear_rmse)
]

best_sp = -1
best_name = ""

for name, mean_sp, std_sp, rmse in results_summary:
    diff = mean_sp - v3_baseline
    marker = ""
    if diff > 0:
        marker = " ✅"
    elif diff < -0.05:
        marker = " ❌"

    if mean_sp > best_sp:
        best_sp = mean_sp
        best_name = name

    if std_sp > 0:
        print(f"| {name:<16} | {mean_sp:.4f} ± {std_sp:.4f} | {rmse:.4f} | {diff:+.4f} | {marker} |")
    else:
        print(f"| {name:<16} | {mean_sp:.4f} | {rmse:.4f} | {diff:+.4f} | {marker} |")

print(f"\n🏆 Best: {best_name} = {best_sp:.4f}")

# ============================================================================
# 7. 핵심 질문 답변
# ============================================================================
print("\n" + "=" * 100)
print("[7] 핵심 질문 답변")
print("=" * 100)

print(f"\n❓ Bilinear의 Drug/Gene 분리 학습이 unseen drug에서 유리한가?")
print(f"   Bilinear: {bilinear_mean_sp:.4f}")
print(f"   CatBoost-Drug: {catboost_drug_mean_sp:.4f}")
if bilinear_mean_sp > catboost_drug_mean_sp:
    print(f"   ✅ YES! Bilinear이 {bilinear_mean_sp - catboost_drug_mean_sp:+.4f} 더 좋음")
    print(f"   → Drug/Gene 분리가 unseen drug 일반화에 효과적!")
else:
    print(f"   ❌ NO. Bilinear이 {bilinear_mean_sp - catboost_drug_mean_sp:+.4f} 더 낮음")

print(f"\n❓ Drug+Bilinear 앙상블이 GroupKFold에서도 개선되는가?")
print(f"   Drug+Bilinear: {drug_bilinear_sp:.4f}")
print(f"   CatBoost-Drug: {catboost_drug_mean_sp:.4f}")
if drug_bilinear_sp > catboost_drug_mean_sp:
    print(f"   ✅ YES! 앙상블이 {drug_bilinear_sp - catboost_drug_mean_sp:+.4f} 개선")
else:
    print(f"   ❌ NO. 앙상블이 {drug_bilinear_sp - catboost_drug_mean_sp:+.4f} 악화")

# ============================================================================
# 8. JSON 저장
# ============================================================================
print("\n" + "=" * 100)
print("[8] 결과 저장")
print("=" * 100)

results = {
    "method": "GroupKFold retrain (correct)",
    "n_splits": 5,
    "n_samples": len(y),
    "unique_drugs": len(np.unique(drug_ids)),
    "v3_baseline": v3_baseline,
    "models": {
        "CatBoost-Full": {
            "mean_spearman": float(catboost_full_mean_sp),
            "std_spearman": float(catboost_full_std_sp),
            "rmse": float(catboost_full_rmse),
            "fold_spearman": [float(x) for x in catboost_full_fold_sps],
            "vs_v3": float(catboost_full_mean_sp - v3_baseline)
        },
        "CatBoost-Drug": {
            "mean_spearman": float(catboost_drug_mean_sp),
            "std_spearman": float(catboost_drug_std_sp),
            "rmse": float(catboost_drug_rmse),
            "fold_spearman": [float(x) for x in catboost_drug_fold_sps],
            "vs_v3": float(catboost_drug_mean_sp - v3_baseline)
        },
        "Bilinear-v2": {
            "mean_spearman": float(bilinear_mean_sp),
            "std_spearman": float(bilinear_std_sp),
            "rmse": float(bilinear_rmse),
            "fold_spearman": [float(x) for x in bilinear_fold_sps],
            "vs_v3": float(bilinear_mean_sp - v3_baseline)
        },
        "Drug+Bilinear": {
            "spearman": float(drug_bilinear_sp),
            "rmse": float(drug_bilinear_rmse),
            "weights": {"drug": float(w_drug), "bilinear": float(w_bilinear)},
            "vs_v3": float(drug_bilinear_sp - v3_baseline)
        }
    },
    "key_findings": {
        "best_model": best_name,
        "best_spearman": float(best_sp),
        "bilinear_better_than_drug": bilinear_mean_sp > catboost_drug_mean_sp,
        "ensemble_improves": drug_bilinear_sp > catboost_drug_mean_sp
    }
}

results_path = output_dir / "groupkfold_retrain_results.json"
with open(results_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ JSON: {results_path}")

# CSV
summary_df = pd.DataFrame([
    {
        'Model': name,
        'GroupKFold_Spearman': res['mean_spearman'] if 'mean_spearman' in res else res['spearman'],
        'Std': res['std_spearman'] if 'std_spearman' in res else 0.0,
        'RMSE': res['rmse'],
        'vs_v3': res['vs_v3']
    }
    for name, res in results['models'].items()
])

csv_path = output_dir / "groupkfold_retrain_comparison.csv"
summary_df.to_csv(csv_path, index=False)
print(f"✓ CSV: {csv_path}")

print("\n" + "=" * 100)
print("GroupKFold 재학습 완료!")
print("=" * 100)
