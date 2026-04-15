#!/usr/bin/env python3
"""
Phase 1: 3개 모델 전부 학습
Bilinear + SAINT + HGT
"""
import sys
import os
from pathlib import Path

# 모델 경로 추가
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
sys.path.append(str(base_dir / "20260415_v4_ensemble_test/new_models/bilinear"))
sys.path.append(str(base_dir / "20260415_v4_ensemble_test/new_models/saint"))
sys.path.append(str(base_dir / "20260415_v4_ensemble_test/new_models/hgt"))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
import json
from datetime import datetime

# 모델 import
from bilinear_model import BilinearInteractionNet
from saint_model import SAINTModelLite
from hgt_model import SimpleHGTModel, create_drug_gene_bipartite_graph

print("=" * 100)
print("Phase 1: 3개 모델 전부 학습")
print("=" * 100)

# 경로 설정
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_base = base_dir / "20260415_v4_ensemble_test/new_models"

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
# 공통 학습 함수
# ============================================================================
def train_model(model_name, model_class, model_kwargs, use_indices=True, is_graph=False):
    """
    모델 학습 (5-fold CV)

    Args:
        model_name: 모델 이름
        model_class: 모델 클래스
        model_kwargs: 모델 초기화 kwargs
        use_indices: drug/gene indices 사용 여부
        is_graph: HGT (graph 모델) 여부
    """
    print(f"\n{'='*100}")
    print(f"{model_name} 학습 시작")
    print(f"{'='*100}")

    output_dir = output_base / model_name.lower()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 하이퍼파라미터
    epochs = 100
    lr = 0.001
    batch_size = 64 if not is_graph else 1  # Graph는 batch=1

    # 5-fold CV
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros(len(y_cv))
    train_predictions = np.zeros(len(y_cv))
    fold_train_sps = []
    fold_oof_sps = []
    train_logs = []

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
        print(f"\nFold {fold_idx}/5:")

        X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
        y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

        # 모델 생성
        if is_graph:
            # HGT는 특별 처리
            model = model_class(**model_kwargs).to(device)

            # Graph 생성
            print("  Creating graph...")
            train_graph = create_drug_gene_bipartite_graph(X_tr, drug_indices, gene_indices, top_k=20)
            val_graph = create_drug_gene_bipartite_graph(X_val, drug_indices, gene_indices, top_k=20)

            # Graph를 device로
            train_graph = train_graph.to(device)
            val_graph = val_graph.to(device)

            y_tr_tensor = torch.FloatTensor(y_tr[:train_graph['drug'].x.size(0)]).to(device)
            y_val_tensor = torch.FloatTensor(y_val[:val_graph['drug'].x.size(0)]).to(device)

        else:
            model = model_class(**model_kwargs).to(device)

            X_tr_tensor = torch.FloatTensor(X_tr).to(device)
            y_tr_tensor = torch.FloatTensor(y_tr).to(device)
            X_val_tensor = torch.FloatTensor(X_val).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        # 학습
        model.train()
        fold_losses = []

        for epoch in range(epochs):
            if is_graph:
                # HGT
                optimizer.zero_grad()
                outputs = model(train_graph)
                loss = criterion(outputs, y_tr_tensor)
                loss.backward()
                optimizer.step()
                fold_losses.append(float(loss.item()))

            else:
                # Bilinear, SAINT
                optimizer.zero_grad()
                if use_indices:
                    outputs = model(X_tr_tensor, drug_indices, gene_indices)
                else:
                    outputs = model(X_tr_tensor)

                loss = criterion(outputs, y_tr_tensor)
                loss.backward()
                optimizer.step()
                fold_losses.append(float(loss.item()))

            if (epoch + 1) % 20 == 0:
                print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

        # 평가
        model.eval()
        with torch.no_grad():
            if is_graph:
                train_pred = model(train_graph).cpu().numpy()
                val_pred = model(val_graph).cpu().numpy()

                # 크기 맞추기
                train_pred = train_pred[:len(y_tr)]
                val_pred = val_pred[:len(y_val)]

            else:
                if use_indices:
                    train_pred = model(X_tr_tensor, drug_indices, gene_indices).cpu().numpy()
                    val_pred = model(X_val_tensor, drug_indices, gene_indices).cpu().numpy()
                else:
                    train_pred = model(X_tr_tensor).cpu().numpy()
                    val_pred = model(X_val_tensor).cpu().numpy()

        train_predictions[tr_idx] = train_pred
        oof_predictions[val_idx] = val_pred

        train_sp = spearmanr(y_tr, train_pred)[0]
        val_sp = spearmanr(y_val, val_pred)[0]

        fold_train_sps.append(train_sp)
        fold_oof_sps.append(val_sp)

        print(f"  Train Sp: {train_sp:.4f}, OOF Sp: {val_sp:.4f}")

        train_logs.append({
            'fold': fold_idx,
            'losses': fold_losses,
            'train_spearman': float(train_sp),
            'oof_spearman': float(val_sp)
        })

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

    if is_graph:
        final_model = model_class(**model_kwargs).to(device)
        final_graph_cv = create_drug_gene_bipartite_graph(X_cv, drug_indices, gene_indices, top_k=20).to(device)
        final_graph_holdout = create_drug_gene_bipartite_graph(X_holdout, drug_indices, gene_indices, top_k=20).to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

        y_cv_tensor = torch.FloatTensor(y_cv[:final_graph_cv['drug'].x.size(0)]).to(device)

        final_model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = final_model(final_graph_cv)
            loss = criterion(outputs, y_cv_tensor)
            loss.backward()
            optimizer.step()

        final_model.eval()
        with torch.no_grad():
            holdout_pred = final_model(final_graph_holdout).cpu().numpy()[:len(y_holdout)]

        # Graph 저장
        torch.save(final_graph_cv, output_dir / f"{model_name.lower()}_graph_data.pt")

    else:
        final_model = model_class(**model_kwargs).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

        X_cv_tensor = torch.FloatTensor(X_cv).to(device)
        y_cv_tensor = torch.FloatTensor(y_cv).to(device)
        X_holdout_tensor = torch.FloatTensor(X_holdout).to(device)

        final_model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            if use_indices:
                outputs = final_model(X_cv_tensor, drug_indices, gene_indices)
            else:
                outputs = final_model(X_cv_tensor)

            loss = criterion(outputs, y_cv_tensor)
            loss.backward()
            optimizer.step()

        final_model.eval()
        with torch.no_grad():
            if use_indices:
                holdout_pred = final_model(X_holdout_tensor, drug_indices, gene_indices).cpu().numpy()
            else:
                holdout_pred = final_model(X_holdout_tensor).cpu().numpy()

    holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
    holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))

    print(f"  Holdout Spearman: {holdout_sp:.4f}")
    print(f"  Holdout RMSE:     {holdout_rmse:.4f}")

    # ========================================================================
    # 저장
    # ========================================================================
    print(f"\n결과 저장...")

    # 1. Model weight
    model_path = output_dir / f"{model_name.lower()}_model.pt"
    torch.save(final_model.state_dict(), model_path)
    print(f"  ✓ Model: {model_path}")

    # 2. OOF predictions (필수!)
    oof_path = output_dir / f"{model_name.lower()}_oof.npy"
    np.save(oof_path, oof_predictions)
    print(f"  ✓ OOF: {oof_path} (shape: {oof_predictions.shape})")

    # 3. Holdout predictions (필수!)
    holdout_path = output_dir / f"{model_name.lower()}_holdout.npy"
    np.save(holdout_path, holdout_pred)
    print(f"  ✓ Holdout: {holdout_path} (shape: {holdout_pred.shape})")

    # 4. Train log
    log_path = output_dir / f"{model_name.lower()}_train_log.json"
    with open(log_path, "w") as f:
        json.dump(train_logs, f, indent=2)
    print(f"  ✓ Train log: {log_path}")

    # 5. Results (필수!)
    results = {
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "hyperparameters": {
            "epochs": epochs,
            "learning_rate": lr,
            "batch_size": batch_size
        },
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

    results_path = output_dir / f"{model_name.lower()}_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Results: {results_path}")

    print(f"\n{model_name} 학습 완료!")
    return results

# ============================================================================
# 모델별 학습
# ============================================================================

# 1. Bilinear
bilinear_results = train_model(
    model_name="Bilinear",
    model_class=BilinearInteractionNet,
    model_kwargs={
        'drug_dim': len(drug_indices),
        'gene_dim': len(gene_indices),
        'hidden_dim': 256,
        'emb_dim': 128,
        'dropout': 0.3
    },
    use_indices=True,
    is_graph=False
)

# 2. SAINT
saint_results = train_model(
    model_name="SAINT",
    model_class=SAINTModelLite,
    model_kwargs={
        'n_features': X_train.shape[1],
        'embed_dim': 64,
        'n_heads': 4,
        'n_layers': 2,
        'n_tokens': 64,
        'dropout': 0.3
    },
    use_indices=False,
    is_graph=False
)

# 3. HGT
hgt_results = train_model(
    model_name="HGT",
    model_class=SimpleHGTModel,
    model_kwargs={
        'drug_dim': len(drug_indices),
        'gene_dim': len(gene_indices),
        'hidden_dim': 128,
        'n_layers': 2,
        'n_heads': 4,
        'dropout': 0.3
    },
    use_indices=False,
    is_graph=True
)

print("\n" + "=" * 100)
print("Phase 1 완료: 3개 모델 학습 완료!")
print("=" * 100)

# 요약
print("\n최종 요약:")
print(f"{'Model':15s} {'OOF Sp':>10s} {'Holdout Sp':>12s} {'Gap':>8s}")
print("-" * 50)
print(f"{'Bilinear':15s} {bilinear_results['metrics']['oof_spearman']:>10.4f} "
      f"{bilinear_results['metrics']['holdout_spearman']:>12.4f} "
      f"{bilinear_results['metrics']['gap']:>8.4f}")
print(f"{'SAINT':15s} {saint_results['metrics']['oof_spearman']:>10.4f} "
      f"{saint_results['metrics']['holdout_spearman']:>12.4f} "
      f"{saint_results['metrics']['gap']:>8.4f}")
print(f"{'HGT':15s} {hgt_results['metrics']['oof_spearman']:>10.4f} "
      f"{hgt_results['metrics']['holdout_spearman']:>12.4f} "
      f"{hgt_results['metrics']['gap']:>8.4f}")
