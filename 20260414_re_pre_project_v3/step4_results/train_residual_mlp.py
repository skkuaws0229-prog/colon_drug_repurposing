#!/usr/bin/env python3
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import time
import warnings
warnings.filterwarnings("ignore")

print("=" * 80)
print("Model 9/15: ResidualMLP (GPU/MPS)")
print("=" * 80)
print()

# MPS 사용 가능 확인
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {device}")
print()

class ResidualBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(dim, dim)
        )
    
    def forward(self, x):
        return x + self.fc(x)

class ResidualMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256, n_blocks=3):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.blocks = nn.ModuleList([ResidualBlock(hidden_dim) for _ in range(n_blocks)])
        self.output = nn.Linear(hidden_dim, 1)
    
    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        return self.output(x).squeeze()

def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        y_pred = model(X_batch)
        loss = criterion(y_pred, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

def predict(model, loader, device):
    model.eval()
    preds = []
    with torch.no_grad():
        for X_batch, _ in loader:
            X_batch = X_batch.to(device)
            y_pred = model(X_batch)
            preds.append(y_pred.cpu().numpy())
    return np.concatenate(preds)

output_dir = Path("step4_results")
X = np.load("X_train.npy")
y = np.load("y_train.npy")

N_FOLDS = 5
SEED = 42
HOLDOUT_RATIO = 0.2
BENCH_SP = 0.713
BENCH_RMSE = 1.385
EPOCHS = 50
BATCH_SIZE = 256

X_train, X_holdout, y_train, y_holdout = train_test_split(
    X, y, test_size=HOLDOUT_RATIO, random_state=SEED
)

print(f"Data: X_train={X_train.shape}, X_holdout={X_holdout.shape}")
print()

kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
oof_predictions = np.zeros(len(y_train))

print("[5-Fold CV]")
for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_train), 1):
    X_tr, X_val = X_train[train_idx], X_train[val_idx]
    y_tr, y_val = y_train[train_idx], y_train[val_idx]
    
    # Dataset
    train_dataset = TensorDataset(
        torch.FloatTensor(X_tr),
        torch.FloatTensor(y_tr)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_val)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Model
    model = ResidualMLP(X_train.shape[1]).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    t0 = time.time()
    for epoch in range(EPOCHS):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
    train_time = time.time() - t0
    
    # Predict
    y_val_pred = predict(model, val_loader, device)
    oof_predictions[val_idx] = y_val_pred
    
    val_sp, _ = spearmanr(y_val, y_val_pred)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
    
    print(f"Fold {fold_idx}/5: Val Sp={val_sp:.4f}, RMSE={val_rmse:.4f}, Time={train_time:.1f}s")

oof_sp, _ = spearmanr(y_train, oof_predictions)
oof_rmse = np.sqrt(mean_squared_error(y_train, oof_predictions))

print()
print(f"OOF Spearman: {oof_sp:.4f}")
print(f"OOF RMSE:     {oof_rmse:.4f}")

# Holdout
holdout_dataset = TensorDataset(
    torch.FloatTensor(X_train),
    torch.FloatTensor(y_train)
)
holdout_loader_train = DataLoader(holdout_dataset, batch_size=BATCH_SIZE, shuffle=True)

holdout_test_dataset = TensorDataset(
    torch.FloatTensor(X_holdout),
    torch.FloatTensor(y_holdout)
)
holdout_loader_test = DataLoader(holdout_test_dataset, batch_size=BATCH_SIZE, shuffle=False)

model_final = ResidualMLP(X_train.shape[1]).to(device)
optimizer_final = optim.Adam(model_final.parameters(), lr=0.001)

for epoch in range(EPOCHS):
    train_epoch(model_final, holdout_loader_train, criterion, optimizer_final, device)

y_holdout_pred = predict(model_final, holdout_loader_test, device)
holdout_sp, _ = spearmanr(y_holdout, y_holdout_pred)
holdout_rmse = np.sqrt(mean_squared_error(y_holdout, y_holdout_pred))

print(f"Holdout Sp:   {holdout_sp:.4f}")
print(f"Holdout RMSE: {holdout_rmse:.4f}")
print()

sp_pass = oof_sp >= BENCH_SP
rmse_pass = oof_rmse <= BENCH_RMSE
ensemble_pass = sp_pass and rmse_pass

print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")
print()

results = {
    "model": "ResidualMLP",
    "device": device,
    "oof_spearman": float(oof_sp),
    "oof_rmse": float(oof_rmse),
    "holdout_spearman": float(holdout_sp),
    "holdout_rmse": float(holdout_rmse),
    "ensemble_pass": ensemble_pass
}

with open("model_09_residual_mlp.json", "w") as f:
    json.dump(results, f, indent=2)

print("✓ ResidualMLP 완료")
