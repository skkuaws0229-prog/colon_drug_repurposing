#!/usr/bin/env python3
"""
Model 12/15: FT-Transformer (GPU-1)
Protocol v3.0 - Simplified Transformer-based MLP
"""
import os
os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

import json
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import KFold
from scipy.stats import spearmanr

print("="*80)
print("Model 12/15: FT-Transformer (GPU-1, 간소화 Transformer MLP)")
print("="*80)

# Device setup
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")

# Load data
X_train = np.load("X_train.npy").astype(np.float32)
y_train = np.load("y_train.npy").astype(np.float32)

# Simple Transformer-based MLP (Feature Tokenizer concept)
class FTTransformerMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        # Feature tokenization (linear projection)
        self.token_embed = nn.Linear(input_dim, 256)

        # Transformer encoder layer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=256,
            nhead=8,
            dim_feedforward=512,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)

        # Output projection
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1)
        )

    def forward(self, x):
        # Token embedding
        x = self.token_embed(x).unsqueeze(1)  # (batch, 1, 256)
        # Transformer
        x = self.transformer(x)
        x = x.squeeze(1)  # (batch, 256)
        # Output
        return self.fc(x).squeeze()

# Train/holdout split
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

# 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_cv))

for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_cv), 1):
    fold_start = time.time()

    X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
    y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

    # DataLoaders
    train_dataset = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)

    # Model
    model = FTTransformerMLP(X_tr.shape[1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    criterion = nn.MSELoss()

    # Training
    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(100):
        model.train()
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

        # Validation
        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                val_losses.append(criterion(outputs, batch_y).item())

        val_loss = np.mean(val_losses)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
            if patience_counter >= 10:
                break

    # Load best model and predict
    model.load_state_dict(best_model_state)
    model.eval()
    with torch.no_grad():
        val_preds = []
        for batch_X, _ in val_loader:
            batch_X = batch_X.to(device)
            val_preds.append(model(batch_X).cpu().numpy())
        y_val_pred = np.concatenate(val_preds)

    oof_predictions[val_idx] = y_val_pred

    fold_sp = spearmanr(y_val, y_val_pred)[0]
    fold_rmse = np.sqrt(np.mean((y_val - y_val_pred) ** 2))
    fold_time = time.time() - fold_start

    print(f"Fold {fold_idx}/5: Sp={fold_sp:.4f}, RMSE={fold_rmse:.4f}, Time={fold_time:.1f}s")

# OOF metrics
oof_sp = spearmanr(y_cv, oof_predictions)[0]
oof_rmse = np.sqrt(np.mean((y_cv - oof_predictions) ** 2))
print(f"OOF: Sp={oof_sp:.4f}, RMSE={oof_rmse:.4f}")

# Holdout evaluation
train_dataset = TensorDataset(torch.from_numpy(X_cv), torch.from_numpy(y_cv))
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)

final_model = FTTransformerMLP(X_cv.shape[1]).to(device)
optimizer = torch.optim.Adam(final_model.parameters(), lr=0.001, weight_decay=1e-5)
criterion = nn.MSELoss()

for epoch in range(100):
    final_model.train()
    for batch_X, batch_y in train_loader:
        batch_X, batch_y = batch_X.to(device), batch_y.to(device)
        optimizer.zero_grad()
        outputs = final_model(batch_X)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

final_model.eval()
with torch.no_grad():
    X_holdout_t = torch.from_numpy(X_holdout).to(device)
    holdout_pred = final_model(X_holdout_t).cpu().numpy()

holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
holdout_rmse = np.sqrt(np.mean((y_holdout - holdout_pred) ** 2))
print(f"Holdout: Sp={holdout_sp:.4f}, RMSE={holdout_rmse:.4f}")

# Ensemble criteria
ensemble_pass = bool(oof_sp >= 0.713 and oof_rmse <= 1.385)
print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")

# Save results
results = {
    "model": "FT-Transformer (SimpleMLP)",
    "device": str(device),
    "oof_spearman": float(oof_sp),
    "oof_rmse": float(oof_rmse),
    "holdout_spearman": float(holdout_sp),
    "holdout_rmse": float(holdout_rmse),
    "ensemble_pass": ensemble_pass
}

with open("model_12_fttransformer.json", "w") as f:
    json.dump(results, f, indent=2)

np.save("model_12_fttransformer_oof.npy", oof_predictions)
np.save("model_12_fttransformer_holdout.npy", holdout_pred)

print("✓ FT-Transformer (SimpleMLP) 완료")
