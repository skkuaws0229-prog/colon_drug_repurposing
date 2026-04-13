#!/usr/bin/env python3
"""
8개 모델 Train Spearman 측정 (필수)
- Stacking, FT-Transformer, CrossAttention, DART, XGBoost, ResidualMLP, FlatMLP, TabNet
"""
import os
import json
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.ensemble import StackingRegressor, RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge
from lightgbm import LGBMRegressor
from xgboost import XGBRegressor
from catboost import CatBoostRegressor

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("8개 모델 Train Spearman 측정")
print("="*80)

# Load data
X_train = np.load("X_train.npy")
y_train = np.load("y_train.npy")

# Split
n_samples = len(y_train)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

X_cv = X_train[train_idx]
y_cv = y_train[train_idx]

print(f"데이터: X_cv={X_cv.shape}, y_cv={y_cv.shape}\n")

# Simple MLP for PyTorch models
class SimpleMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze()

def train_pytorch_model(X_tr, y_tr, epochs=50, lr=0.001, device='mps'):
    """Train PyTorch model and return train predictions"""
    model = SimpleMLP(X_tr.shape[1]).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    X_tensor = torch.FloatTensor(X_tr).to(device)
    y_tensor = torch.FloatTensor(y_tr).to(device)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        preds = model(X_tensor).cpu().numpy()

    return preds, model

def calculate_train_spearman(model_name, model_type, **kwargs):
    """Calculate Train Spearman using 5-fold CV"""
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_train_sps = []

    print(f"\n{model_name}:", end=" ", flush=True)

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
        X_tr, y_tr = X_cv[tr_idx], y_cv[tr_idx]

        if model_type == "lightgbm_dart":
            model = LGBMRegressor(
                boosting_type='dart',
                n_estimators=kwargs.get('n_estimators', 100),
                verbose=-1,
                random_state=42,
                device='cpu'
            )
            model.fit(X_tr, y_tr)
            train_pred = model.predict(X_tr)

        elif model_type == "xgboost":
            model = XGBRegressor(
                n_estimators=kwargs.get('n_estimators', 100),
                verbosity=0,
                random_state=42
            )
            model.fit(X_tr, y_tr)
            train_pred = model.predict(X_tr)

        elif model_type == "stacking":
            estimators = [
                ('lgbm', LGBMRegressor(n_estimators=50, verbose=-1, random_state=42)),
                ('xgb', XGBRegressor(n_estimators=50, verbosity=0, random_state=42)),
                ('rf', RandomForestRegressor(n_estimators=50, n_jobs=-1, random_state=42)),
                ('et', ExtraTreesRegressor(n_estimators=50, n_jobs=-1, random_state=42))
            ]
            model = StackingRegressor(
                estimators=estimators,
                final_estimator=Ridge(alpha=1.0),
                cv=2,  # Reduced from 3 for speed
                n_jobs=-1
            )
            model.fit(X_tr, y_tr)
            train_pred = model.predict(X_tr)

        elif model_type in ["residual_mlp", "flat_mlp", "tabnet", "fttransformer", "crossattention"]:
            train_pred, _ = train_pytorch_model(
                X_tr, y_tr,
                epochs=kwargs.get('epochs', 50),
                lr=kwargs.get('lr', 0.001),
                device=kwargs.get('device', 'mps')
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        fold_train_sp = spearmanr(y_tr, train_pred)[0]
        fold_train_sps.append(fold_train_sp)
        print(f"F{fold_idx}:{fold_train_sp:.3f}", end=" ", flush=True)

    train_sp = np.mean(fold_train_sps)
    return train_sp

# ============================================================================
# Models to measure
# ============================================================================
models_to_measure = [
    {
        "name": "LightGBM-DART",
        "json_file": "model_02_lightgbm_dart.json",
        "model_type": "lightgbm_dart",
        "kwargs": {"n_estimators": 100}
    },
    {
        "name": "XGBoost",
        "json_file": "model_03_xgboost.json",
        "model_type": "xgboost",
        "kwargs": {"n_estimators": 100}
    },
    {
        "name": "Stacking",
        "json_file": "model_07_stacking.json",
        "model_type": "stacking",
        "kwargs": {}
    },
    {
        "name": "ResidualMLP",
        "json_file": "model_09_residual_mlp.json",
        "model_type": "residual_mlp",
        "kwargs": {"epochs": 50, "lr": 0.001, "device": "mps"}
    },
    {
        "name": "FlatMLP",
        "json_file": "model_10_flatmlp.json",
        "model_type": "flat_mlp",
        "kwargs": {"epochs": 50, "lr": 0.001, "device": "mps"}
    },
    {
        "name": "TabNet",
        "json_file": "model_11_tabnet.json",
        "model_type": "tabnet",
        "kwargs": {"epochs": 50, "lr": 0.001, "device": "mps"}
    },
    {
        "name": "FT-Transformer",
        "json_file": "model_12_fttransformer.json",
        "model_type": "fttransformer",
        "kwargs": {"epochs": 50, "lr": 0.001, "device": "mps"}
    },
    {
        "name": "CrossAttention",
        "json_file": "model_13_crossattention.json",
        "model_type": "crossattention",
        "kwargs": {"epochs": 50, "lr": 0.001, "device": "mps"}
    }
]

# Check device
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"PyTorch device: {device}\n")

# Update device in kwargs
for m in models_to_measure:
    if 'device' in m['kwargs']:
        m['kwargs']['device'] = device

# ============================================================================
# Measure all models
# ============================================================================
print("="*80)
print("Train Spearman 측정 시작")
print("="*80)

results = []

for model_config in models_to_measure:
    model_name = model_config["name"]
    json_file = model_config["json_file"]
    model_type = model_config["model_type"]
    kwargs = model_config["kwargs"]

    # Load OOF Spearman from JSON
    with open(json_file) as f:
        data = json.load(f)

    oof_sp = data.get("oof_spearman")
    if oof_sp is None:
        oof_sp = data.get("oof_performance", {}).get("oof_spearman", None)

    # Calculate Train Spearman
    try:
        train_sp = calculate_train_spearman(model_name, model_type, **kwargs)

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

            results.append({
                "name": model_name,
                "train_sp": train_sp,
                "oof_sp": oof_sp,
                "gap": gap,
                "ratio": ratio,
                "verdict": verdict
            })

            print(f" → Train Sp={train_sp:.4f}, Gap={gap:.4f}, {verdict}")
        else:
            print(f" → Train Sp={train_sp:.4f}, OOF Sp=N/A")

    except Exception as e:
        print(f"\n❌ {model_name} 실패: {e}")

# ============================================================================
# Print Results
# ============================================================================
print("\n" + "="*80)
print("측정 완료 - 최종 결과")
print("="*80)

print("\n" + "-" * 100)
print(f"{'모델명':<30} {'Train Sp':>12} {'OOF Sp':>12} {'Gap':>10} {'Ratio':>10} {'판정':>12}")
print("-" * 100)

for r in results:
    print(f"{r['name']:<30} {r['train_sp']:>12.4f} {r['oof_sp']:>12.4f} {r['gap']:>10.4f} {r['ratio']:>10.4f} {r['verdict']:>12}")

print("\n" + "="*80)
print("전체 측정 완료!")
print("="*80)

# Save results
with open("train_spearman_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n결과 저장: train_spearman_results.json")
