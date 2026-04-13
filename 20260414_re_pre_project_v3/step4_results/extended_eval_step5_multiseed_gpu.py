#!/usr/bin/env python3
"""
Step 5: Multi-seed Stability (GPU 모델)
5개 시드로 Random 5CV 반복 + GraphSAGE 포함
"""
import os
import json
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 5: Multi-seed Stability (GPU)")
print("="*80)

# Load data
X = np.load("X_train.npy").astype(np.float32)
y = np.load("y_train.npy").astype(np.float32)

device = 'mps' if torch.backends.mps.is_available() else 'cpu'
print(f"Device: {device}\n")

# Seeds
SEEDS = [42, 123, 456, 789, 2026]

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

def train_seed(model_name, model_id, model_class, seed):
    """Train model with specific seed"""
    print(f"\n  Seed {seed}:")

    # Set seeds
    torch.manual_seed(seed)
    np.random.seed(seed)

    # 5-fold CV
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    fold_scores = []
    oof_predictions = np.zeros(len(y))
    train_predictions = np.zeros(len(y))

    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # Initialize model
        model = model_class(X.shape[1]).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(device)
        y_train_t = torch.FloatTensor(y_train).to(device)
        X_val_t = torch.FloatTensor(X_val).to(device)

        # Train
        model.train()
        for epoch in range(100):
            optimizer.zero_grad()
            outputs = model(X_train_t)
            loss = criterion(outputs, y_train_t)
            loss.backward()
            optimizer.step()

        # Evaluate
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val_t).cpu().numpy()
            train_pred = model(X_train_t).cpu().numpy()

        oof_predictions[val_idx] = val_pred
        train_predictions[train_idx] = train_pred

        # Fold score
        fold_sp = spearmanr(y_val, val_pred)[0]
        fold_scores.append(fold_sp)

    # Calculate metrics
    oof_sp = spearmanr(y, oof_predictions)[0]
    oof_rmse = np.sqrt(mean_squared_error(y, oof_predictions))
    oof_mae = mean_absolute_error(y, oof_predictions)

    # Train Spearman
    train_sp = spearmanr(y, train_predictions)[0]
    gap = train_sp - oof_sp

    print(f"    Train Sp: {train_sp:.4f}, OOF Sp: {oof_sp:.4f}, Gap: {gap:.4f}")
    print(f"    RMSE: {oof_rmse:.4f}, MAE: {oof_mae:.4f}")

    # Top-30
    top30_indices = np.argsort(oof_predictions)[:30]

    return {
        'seed': seed,
        'train_spearman': train_sp,
        'oof_spearman': oof_sp,
        'oof_rmse': oof_rmse,
        'oof_mae': oof_mae,
        'gap': gap,
        'fold_scores': fold_scores,
        'fold_mean': np.mean(fold_scores),
        'fold_std': np.std(fold_scores),
        'top30_indices': top30_indices.tolist(),
        'oof_predictions': oof_predictions
    }

# Model configurations
models_config = [
    ("FlatMLP", 10, FlatMLP),
    ("CrossAttention", 13, CrossAttentionMLP),
    ("FT-Transformer", 12, FTTransformerMLP),
    ("GraphSAGE", 14, GraphSAGEMLP)
]

print("="*80)
print("GPU 모델 실행 중...")
print("="*80)

all_results = {}

for model_name, model_id, model_class in models_config:
    print(f"\n{'='*80}")
    print(f"Model {model_id:02d}: {model_name}")
    print(f"{'='*80}")

    seed_results = []
    all_top30_sets = []

    for seed in SEEDS:
        result = train_seed(model_name, model_id, model_class, seed)
        seed_results.append(result)
        all_top30_sets.append(set(result['top30_indices']))

        # Save
        np.save(f"step5_seed{seed}_{model_id:02d}_oof.npy", result['oof_predictions'])

    # Cross-seed statistics
    oof_sps = [r['oof_spearman'] for r in seed_results]
    train_sps = [r['train_spearman'] for r in seed_results]
    gaps = [r['gap'] for r in seed_results]
    rmses = [r['oof_rmse'] for r in seed_results]

    # Top-30 overlap
    top30_intersection = set.intersection(*all_top30_sets)
    top30_union = set.union(*all_top30_sets)

    # Jaccard similarity
    jaccard_scores = []
    for i in range(len(all_top30_sets)):
        for j in range(i+1, len(all_top30_sets)):
            intersection = len(all_top30_sets[i] & all_top30_sets[j])
            union = len(all_top30_sets[i] | all_top30_sets[j])
            jaccard = intersection / union if union > 0 else 0.0
            jaccard_scores.append(jaccard)

    avg_jaccard = np.mean(jaccard_scores) if jaccard_scores else 0.0
    avg_fold_std = np.mean([r['fold_std'] for r in seed_results])

    summary = {
        'model_id': model_id,
        'model_name': model_name,
        'stage': 'step5_multiseed',
        'seeds': SEEDS,
        'seed_results': seed_results,
        'cross_seed_stats': {
            'train_spearman_mean': np.mean(train_sps),
            'train_spearman_std': np.std(train_sps),
            'oof_spearman_mean': np.mean(oof_sps),
            'oof_spearman_std': np.std(oof_sps),
            'gap_mean': np.mean(gaps),
            'gap_std': np.std(gaps),
            'rmse_mean': np.mean(rmses),
            'rmse_std': np.std(rmses),
            'top30_overlap_count': len(top30_intersection),
            'top30_total_unique': len(top30_union),
            'top30_jaccard_similarity': avg_jaccard,
            'avg_fold_std': avg_fold_std
        }
    }

    # Save
    with open(f"step5_multiseed_{model_id:02d}_results.json", 'w') as f:
        summary_save = summary.copy()
        summary_save['seed_results'] = [
            {k: v for k, v in r.items() if k != 'oof_predictions'}
            for r in seed_results
        ]
        json.dump(summary_save, f, indent=2)

    all_results[model_id] = summary

    print(f"\n  종합 통계 (5 seeds):")
    print(f"    OOF Sp: {summary['cross_seed_stats']['oof_spearman_mean']:.4f} ± {summary['cross_seed_stats']['oof_spearman_std']:.4f}")
    print(f"    Gap:    {summary['cross_seed_stats']['gap_mean']:.4f} ± {summary['cross_seed_stats']['gap_std']:.4f}")
    print(f"    Top-30 Overlap: {len(top30_intersection)}/30")
    print(f"    Jaccard: {avg_jaccard:.4f}")
    print(f"    ✓ 저장: step5_multiseed_{model_id:02d}_results.json")

print("\n" + "="*80)
print("GPU 모델 완료!")
print("="*80)
