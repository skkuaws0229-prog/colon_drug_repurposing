#!/usr/bin/env python3
"""
Model 15/15: GAT (Graph Attention Network, Drug-Split)
Protocol v3.0 - Simplified GAT with drug-based splitting
"""
import os
os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import KFold
from scipy.stats import spearmanr

print("="*80)
print("Model 15/15: GAT (Graph Attention Network, Drug-Split)")
print("="*80)

# Device setup
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")

# Load data
X_train = np.load("X_train.npy").astype(np.float32)
y_train = np.load("y_train.npy").astype(np.float32)

# Load features to get drug identifiers
features_slim = pd.read_parquet("../features_slim.parquet")
drug_ids = features_slim['canonical_drug_id'].values

# Simplified GAT-inspired MLP (attention-based aggregation)
class GATMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        # Multi-head attention layers
        self.attn1 = nn.MultiheadAttention(
            embed_dim=512,
            num_heads=8,
            dropout=0.2,
            batch_first=True
        )
        self.attn2 = nn.MultiheadAttention(
            embed_dim=256,
            num_heads=4,
            dropout=0.2,
            batch_first=True
        )

        # Feature projection
        self.proj = nn.Linear(input_dim, 512)

        # Attention processing layers
        self.layer1 = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2)
        )

        # Output layer
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 1)
        )

    def forward(self, x):
        # Project to embedding space
        x = self.proj(x).unsqueeze(1)  # (batch, 1, 512)

        # Multi-head attention (self-attention)
        attn_out1, _ = self.attn1(x, x, x)
        attn_out1 = attn_out1.squeeze(1)  # (batch, 512)

        # Layer 1
        x = self.layer1(attn_out1).unsqueeze(1)  # (batch, 1, 256)

        # Second attention layer
        attn_out2, _ = self.attn2(x, x, x)
        attn_out2 = attn_out2.squeeze(1)  # (batch, 256)

        # Output
        return self.fc(attn_out2).squeeze()

# Train/holdout split (80/20) - DRUG-BASED
unique_drugs = np.unique(drug_ids)
n_train_drugs = int(len(unique_drugs) * 0.8)
np.random.seed(42)
np.random.shuffle(unique_drugs)

train_drugs = set(unique_drugs[:n_train_drugs])
holdout_drugs = set(unique_drugs[n_train_drugs:])

train_mask = np.array([drug in train_drugs for drug in drug_ids])
holdout_mask = ~train_mask

train_idx = np.where(train_mask)[0]
holdout_idx = np.where(holdout_mask)[0]

X_cv = X_train[train_idx]
y_cv = y_train[train_idx]
drug_ids_cv = drug_ids[train_idx]
X_holdout = X_train[holdout_idx]
y_holdout = y_train[holdout_idx]

print(f"Drug-split: {len(train_drugs)} train drugs, {len(holdout_drugs)} holdout drugs")
print(f"Samples: {len(train_idx)} train, {len(holdout_idx)} holdout")

# 5-fold CV with drug-based splitting
unique_cv_drugs = np.unique(drug_ids_cv)
kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_cv))

for fold_idx, (drug_tr_idx, drug_val_idx) in enumerate(kf.split(unique_cv_drugs), 1):
    fold_start = time.time()

    # Get drugs for this fold
    drugs_tr = set(unique_cv_drugs[drug_tr_idx])
    drugs_val = set(unique_cv_drugs[drug_val_idx])

    # Map to sample indices
    fold_tr_mask = np.array([drug in drugs_tr for drug in drug_ids_cv])
    fold_val_mask = np.array([drug in drugs_val for drug in drug_ids_cv])

    tr_idx = np.where(fold_tr_mask)[0]
    val_idx = np.where(fold_val_mask)[0]

    X_tr, X_val = X_cv[tr_idx], X_cv[val_idx]
    y_tr, y_val = y_cv[tr_idx], y_cv[val_idx]

    # DataLoaders
    train_dataset = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)

    # Model
    model = GATMLP(X_tr.shape[1]).to(device)
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

final_model = GATMLP(X_cv.shape[1]).to(device)
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
    "model": "GAT (Drug-Split)",
    "device": str(device),
    "split_type": "drug-based",
    "oof_spearman": float(oof_sp),
    "oof_rmse": float(oof_rmse),
    "holdout_spearman": float(holdout_sp),
    "holdout_rmse": float(holdout_rmse),
    "ensemble_pass": ensemble_pass
}

with open("model_15_gat.json", "w") as f:
    json.dump(results, f, indent=2)

np.save("model_15_gat_oof.npy", oof_predictions)
np.save("model_15_gat_holdout.npy", holdout_pred)

print("✓ GAT (Drug-Split) 완료")
