import numpy as np
import json
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

print("="*80)
print("Model 10/15: FlatMLP (GPU-1)")
print("="*80)

device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {device}")

class FlatMLP(nn.Module):
    def __init__(self, input_dim, hidden_dims=[512, 256, 128]):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.net = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.net(x).squeeze()

X = np.load("X_train.npy")
y = np.load("y_train.npy")
X_train, X_holdout, y_train, y_holdout = train_test_split(X, y, test_size=0.2, random_state=42)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
oof_predictions = np.zeros(len(y_train))

for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_train), 1):
    X_tr, X_val = X_train[train_idx], X_train[val_idx]
    y_tr, y_val = y_train[train_idx], y_train[val_idx]
    
    train_dataset = TensorDataset(torch.FloatTensor(X_tr), torch.FloatTensor(y_tr))
    val_dataset = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
    
    model = FlatMLP(X_train.shape[1]).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    t0 = time.time()
    for epoch in range(50):
        model.train()
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            loss = criterion(model(X_batch), y_batch)
            loss.backward()
            optimizer.step()
    
    model.eval()
    with torch.no_grad():
        preds = []
        for X_batch, _ in val_loader:
            preds.append(model(X_batch.to(device)).cpu().numpy())
        y_val_pred = np.concatenate(preds)
    
    oof_predictions[val_idx] = y_val_pred
    val_sp, _ = spearmanr(y_val, y_val_pred)
    val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
    print(f"Fold {fold_idx}/5: Sp={val_sp:.4f}, RMSE={val_rmse:.4f}, Time={time.time()-t0:.1f}s")

oof_sp, _ = spearmanr(y_train, oof_predictions)
oof_rmse = np.sqrt(mean_squared_error(y_train, oof_predictions))

model_final = FlatMLP(X_train.shape[1]).to(device)
optimizer_final = optim.Adam(model_final.parameters(), lr=0.001)
holdout_dataset = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
holdout_loader = DataLoader(holdout_dataset, batch_size=256, shuffle=True)

for epoch in range(50):
    model_final.train()
    for X_batch, y_batch in holdout_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer_final.zero_grad()
        loss = criterion(model_final(X_batch), y_batch)
        loss.backward()
        optimizer_final.step()

model_final.eval()
with torch.no_grad():
    y_holdout_pred = model_final(torch.FloatTensor(X_holdout).to(device)).cpu().numpy()

holdout_sp, _ = spearmanr(y_holdout, y_holdout_pred)
holdout_rmse = np.sqrt(mean_squared_error(y_holdout, y_holdout_pred))

ensemble_pass = (oof_sp >= 0.713) and (oof_rmse <= 1.385)
print(f"OOF: Sp={oof_sp:.4f}, RMSE={oof_rmse:.4f}")
print(f"Holdout: Sp={holdout_sp:.4f}, RMSE={holdout_rmse:.4f}")
print(f"Ensemble: {'✓ PASS' if ensemble_pass else '✗ FAIL'}")

with open("model_10_flatmlp.json", "w") as f:
    json.dump({"model": "FlatMLP", "device": device, "oof_spearman": float(oof_sp), "oof_rmse": float(oof_rmse),
               "holdout_spearman": float(holdout_sp), "holdout_rmse": float(holdout_rmse),
               "ensemble_pass": bool(ensemble_pass)}, f, indent=2)
print("✓ FlatMLP 완료")
