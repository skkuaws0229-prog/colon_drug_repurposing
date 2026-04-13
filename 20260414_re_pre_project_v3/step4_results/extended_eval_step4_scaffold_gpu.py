#!/usr/bin/env python3
"""
Step 4: Scaffold Split (GPU 모델)
Murcko scaffold 기반 + GraphSAGE 포함 (총 4개)
"""
import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, mean_squared_error, r2_score

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 4: Scaffold Split (GPU)")
print("="*80)

# Load data
features_df = pd.read_parquet("../features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
y = np.load("y_train.npy")

device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"Device: {device}\n")

# Random 5CV baseline values
BASELINE_SPEARMAN = {
    10: 0.8278,  # FlatMLP
    12: 0.8057,  # FT-Transformer
    13: 0.8238,  # CrossAttention
    14: 0.4326   # GraphSAGE (OOF from drug-split)
}

# Generate Murcko scaffolds
print("Generating Murcko scaffolds...")
smiles_col = 'drug__canonical_smiles_raw' if 'drug__canonical_smiles_raw' in features_df.columns else 'drug__smiles'
smiles_list = features_df[smiles_col].values

scaffolds = []
for smi in smiles_list:
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            scaffold = MurckoScaffold.GetScaffoldForMol(mol)
            scaffold_smiles = Chem.MolToSmiles(scaffold)
            scaffolds.append(scaffold_smiles)
        else:
            scaffolds.append('INVALID')
    except:
        scaffolds.append('INVALID')

scaffolds = np.array(scaffolds)
unique_scaffolds = np.unique(scaffolds[scaffolds != 'INVALID'])

print(f"Total samples: {len(X)}")
print(f"Unique scaffolds: {len(unique_scaffolds)}")

# Scaffold split (80% train, 20% test) - SAME seed as CPU
np.random.seed(42)
n_test_scaffolds = int(len(unique_scaffolds) * 0.2)
test_scaffolds = np.random.choice(unique_scaffolds, size=n_test_scaffolds, replace=False)
test_mask = np.isin(scaffolds, test_scaffolds)

X_train, X_test = X[~test_mask], X[test_mask]
y_train, y_test = y[~test_mask], y[test_mask]

print(f"\nData Split:")
print(f"  Test scaffolds: {len(test_scaffolds)} ({len(test_scaffolds)/len(unique_scaffolds)*100:.1f}%)")
print(f"  Train samples: {len(X_train)}")
print(f"  Test samples: {len(X_test)}\n")

# Model architectures
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

class GraphSAGEMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.agg1 = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        self.agg2 = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        self.combine = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        self.fc = nn.Linear(128, 1)

    def forward(self, x):
        x = self.agg1(x)
        x = self.agg2(x)
        x = self.combine(x)
        return self.fc(x).squeeze()

def calculate_metrics(y_true, y_pred):
    """회귀 지표"""
    valid_mask = ~np.isnan(y_pred)
    y_true_valid = y_true[valid_mask]
    y_pred_valid = y_pred[valid_mask]

    if len(y_true_valid) == 0:
        return {m: np.nan for m in ['spearman', 'rmse', 'mae', 'median_ae', 'p95_error', 'kendall', 'pearson', 'r2']}

    errors = np.abs(y_true_valid - y_pred_valid)

    return {
        'spearman': spearmanr(y_true_valid, y_pred_valid)[0],
        'rmse': np.sqrt(mean_squared_error(y_true_valid, y_pred_valid)),
        'mae': mean_absolute_error(y_true_valid, y_pred_valid),
        'median_ae': median_absolute_error(y_true_valid, y_pred_valid),
        'p95_error': np.percentile(errors, 95),
        'kendall': kendalltau(y_true_valid, y_pred_valid)[0],
        'pearson': pearsonr(y_true_valid, y_pred_valid)[0],
        'r2': r2_score(y_true_valid, y_pred_valid)
    }

def train_scaffold_gpu(model_name, model_id, model_class):
    print(f"\n{'='*80}")
    print(f"Step 4 Scaffold Split: {model_name} (Model {model_id:02d})")
    print(f"{'='*80}")

    model = model_class(X.shape[1]).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    X_train_tensor = torch.FloatTensor(X_train).to(device)
    y_train_tensor = torch.FloatTensor(y_train).to(device)
    X_test_tensor = torch.FloatTensor(X_test).to(device)

    print("  Training on seen scaffolds...")
    model.train()
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X_train_tensor)
        loss = criterion(outputs, y_train_tensor)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 25 == 0:
            print(f"    Epoch {epoch+1}/100, Loss: {loss.item():.4f}")

    print("  Predicting on unseen scaffolds...")
    model.eval()
    with torch.no_grad():
        y_pred = model(X_test_tensor).cpu().numpy()

    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred)

    print(f"\n  Spearman: {metrics['spearman']:.4f}")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    print(f"  MAE: {metrics['mae']:.4f}")

    # Baseline comparison
    baseline_sp = BASELINE_SPEARMAN.get(model_id, np.nan)
    drop_from_random = baseline_sp - metrics['spearman'] if not np.isnan(baseline_sp) else np.nan

    results = {
        'model': model_name,
        'model_id': model_id,
        'stage': 'step4_scaffold_split',
        'data_split': {
            'total_scaffolds': int(len(unique_scaffolds)),
            'test_scaffolds': int(len(test_scaffolds)),
            'train_samples': int(len(X_train)),
            'test_samples': int(len(X_test))
        },
        'metrics': metrics,
        'random_5cv_spearman': baseline_sp,
        'drop_from_random': drop_from_random
    }

    # Save
    results_file = f"step4_scaffold_{model_id:02d}_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    model_file = f"step4_scaffold_{model_id:02d}_model.pt"
    torch.save(model.state_dict(), model_file)

    np.save(f"step4_scaffold_{model_id:02d}_predictions.npy", y_pred)

    print(f"  ✓ Saved: {results_file}")
    return results

# Execute
print("="*80)
print("GPU 모델 실행 중...")
print("="*80)

result_flatmlp = train_scaffold_gpu("FlatMLP", 10, FlatMLP)
result_crossattn = train_scaffold_gpu("CrossAttention", 13, CrossAttentionMLP)
result_fttrans = train_scaffold_gpu("FT-Transformer", 12, FTTransformerMLP)
result_graphsage = train_scaffold_gpu("GraphSAGE", 14, GraphSAGEMLP)

print("\n" + "="*80)
print("GPU 모델 완료!")
print("="*80)
