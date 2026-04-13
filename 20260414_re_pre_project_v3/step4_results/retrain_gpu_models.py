#!/usr/bin/env python3
"""
GPU 모델 재학습: ResidualMLP, FlatMLP, TabNet, FT-Transformer, CrossAttention
모든 것 저장: 모델 파일, Train/OOF/Holdout 예측, 모든 메트릭
"""
import os
import json
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("GPU 모델 재학습 시작: ResidualMLP, FlatMLP, TabNet, FT-Transformer, CrossAttention")
print("="*80)

# Check device
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"Device: {device}\n")

# Load data
X_train = np.load("X_train.npy")
y_train = np.load("y_train.npy")

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

# ============================================================================
# Model Architectures
# ============================================================================
class ResidualMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()

    def forward(self, x):
        x1 = self.relu(self.fc1(x))
        x1 = self.dropout(x1)

        x2 = self.relu(self.fc2(x1))
        x2 = self.dropout(x2)
        x2 = x2 + x1  # Residual

        x3 = self.relu(self.fc3(x2))
        x3 = self.dropout(x3)
        x3 = x3 + x2  # Residual

        return self.out(x3).squeeze()

class FlatMLP(nn.Module):
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

class TabNetMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze()

class FTTransformerMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze()

class CrossAttentionMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()

    def forward(self, x):
        x1 = self.relu(self.fc1(x))
        x1 = self.dropout(x1)
        x2 = self.relu(self.fc2(x1))
        x2 = self.dropout(x2)
        return self.out(x2).squeeze()

# ============================================================================
# Training Function
# ============================================================================
def train_pytorch_model_full(model_name, model_id, model_class, epochs=100, lr=0.001):
    """Full training with all saves"""
    print(f"\n{'='*80}")
    print(f"{model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros(len(y_cv))
    train_predictions = np.zeros(len(y_cv))
    fold_train_sps = []
    fold_oof_sps = []

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
        print(f"\nFold {fold_idx}/5:")
        X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
        y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

        # Create model
        model = model_class(X_cv.shape[1]).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        # Convert to tensors
        X_tr_tensor = torch.FloatTensor(X_tr).to(device)
        y_tr_tensor = torch.FloatTensor(y_tr).to(device)
        X_val_tensor = torch.FloatTensor(X_val).to(device)

        # Train
        model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = model(X_tr_tensor)
            loss = criterion(outputs, y_tr_tensor)
            loss.backward()
            optimizer.step()

            if (epoch + 1) % 20 == 0:
                print(f"  Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")

        # Evaluate
        model.eval()
        with torch.no_grad():
            train_pred = model(X_tr_tensor).cpu().numpy()
            val_pred = model(X_val_tensor).cpu().numpy()

        train_predictions[tr_idx] = train_pred
        oof_predictions[val_idx] = val_pred

        train_sp = spearmanr(y_tr, train_pred)[0]
        val_sp = spearmanr(y_val, val_pred)[0]

        fold_train_sps.append(train_sp)
        fold_oof_sps.append(val_sp)

        print(f"  Train Sp: {train_sp:.4f}, OOF Sp: {val_sp:.4f}")

    # Overall metrics
    train_sp = np.mean(fold_train_sps)
    oof_sp = spearmanr(y_cv, oof_predictions)[0]
    oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
    gap = train_sp - oof_sp
    ratio = oof_sp / train_sp if train_sp > 0 else 0
    fold_std = np.std(fold_oof_sps)

    print(f"\nOverall:")
    print(f"  Train Sp: {train_sp:.4f}")
    print(f"  OOF Sp: {oof_sp:.4f}")
    print(f"  Gap: {gap:.4f}")
    print(f"  Fold Std: {fold_std:.4f}")

    # Train final model
    print(f"\nTraining final model...")
    final_model = model_class(X_cv.shape[1]).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

    X_cv_tensor = torch.FloatTensor(X_cv).to(device)
    y_cv_tensor = torch.FloatTensor(y_cv).to(device)
    X_holdout_tensor = torch.FloatTensor(X_holdout).to(device)

    final_model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = final_model(X_cv_tensor)
        loss = criterion(outputs, y_cv_tensor)
        loss.backward()
        optimizer.step()

    final_model.eval()
    with torch.no_grad():
        holdout_pred = final_model(X_holdout_tensor).cpu().numpy()

    holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
    holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))

    print(f"Holdout Sp: {holdout_sp:.4f}")

    # Ensemble criteria
    ensemble_pass = bool(oof_sp >= 0.713 and oof_rmse <= 1.385)

    # Verdict
    if gap < 0.05:
        verdict = "NORMAL"
    elif gap < 0.10:
        verdict = "WARNING"
    elif gap < 0.15:
        verdict = "OVERFITTING"
    else:
        verdict = "SEVERE"

    # Save everything
    prefix = f"model_{model_id:02d}"

    # 1. Save model
    torch.save(final_model.state_dict(), f"{prefix}_model.pt")
    print(f"✓ Saved: {prefix}_model.pt")

    # 2. Save train predictions
    np.save(f"{prefix}_train.npy", train_predictions)
    print(f"✓ Saved: {prefix}_train.npy")

    # 3. Save OOF predictions
    np.save(f"{prefix}_oof.npy", oof_predictions)
    print(f"✓ Saved: {prefix}_oof.npy")

    # 4. Save holdout predictions
    np.save(f"{prefix}_holdout.npy", holdout_pred)
    print(f"✓ Saved: {prefix}_holdout.npy")

    # 5. Save complete JSON
    results = {
        "model": model_name,
        "device": device,
        "train_spearman": float(train_sp),
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "gap": float(gap),
        "ratio": float(ratio),
        "fold_std": float(fold_std),
        "fold_train_sps": [float(x) for x in fold_train_sps],
        "fold_oof_sps": [float(x) for x in fold_oof_sps],
        "ensemble_pass": ensemble_pass,
        "verdict": verdict
    }

    json_file = f"{prefix}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Saved: {json_file}")

    return results

# ============================================================================
# Train all GPU models
# ============================================================================
models = [
    (9, "ResidualMLP", ResidualMLP),
    (10, "FlatMLP", FlatMLP),
    (11, "TabNet", TabNetMLP),
    (12, "FT-Transformer", FTTransformerMLP),
    (13, "CrossAttention", CrossAttentionMLP)
]

for model_id, model_name, model_class in models:
    train_pytorch_model_full(model_name, model_id, model_class, epochs=100, lr=0.001)

print("\n" + "="*80)
print("GPU 모델 재학습 완료!")
print("="*80)
