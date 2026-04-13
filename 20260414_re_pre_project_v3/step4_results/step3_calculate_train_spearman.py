#!/usr/bin/env python3
"""
Step 3 Unseen Drug Train Spearman 계산
과적합 분석
"""
import os
import json
import numpy as np
import pandas as pd
import pickle
import torch
from scipy.stats import spearmanr

os.chdir('/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results')

print("="*80)
print("Step 3 Unseen Drug Train Spearman 계산")
print("="*80)

# Load data and recreate split
features_df = pd.read_parquet("../features_slim.parquet")
X = features_df.select_dtypes(include=[np.number]).values
y = np.load("y_train.npy")
drug_ids = features_df['canonical_drug_id'].values

# Recreate unseen drug split (same seed)
np.random.seed(42)
unique_drugs = np.unique(drug_ids)
n_unseen = int(len(unique_drugs) * 0.25)
unseen_drugs = np.random.choice(unique_drugs, size=n_unseen, replace=False)
unseen_mask = np.isin(drug_ids, unseen_drugs)

X_train, X_test = X[~unseen_mask], X[unseen_mask]
y_train, y_test = y[~unseen_mask], y[unseen_mask]

print(f"Train samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")

device = 'mps' if torch.backends.mps.is_available() else 'cpu'

# Model configurations
models_info = [
    (1, 'LightGBM', 'cpu', 'pkl'),
    (2, 'DART', 'cpu', 'pkl'),
    (4, 'CatBoost', 'cpu', 'pkl'),
    (10, 'FlatMLP', 'gpu', 'pt'),
    (12, 'FT-Transformer', 'gpu', 'pt'),
    (13, 'CrossAttention', 'gpu', 'pt')
]

# GPU model architectures
class FlatMLP(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_dim, 1)
        )
    def forward(self, x):
        return self.net(x).squeeze()

class CrossAttentionMLP(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.fc1 = torch.nn.Linear(input_dim, hidden_dim)
        self.fc2 = torch.nn.Linear(hidden_dim, hidden_dim)
        self.out = torch.nn.Linear(hidden_dim, 1)
        self.dropout = torch.nn.Dropout(0.3)
        self.relu = torch.nn.ReLU()
    def forward(self, x):
        x1 = self.relu(self.fc1(x))
        x1 = self.dropout(x1)
        x2 = self.relu(self.fc2(x1))
        x2 = self.dropout(x2)
        return self.out(x2).squeeze()

class FTTransformerMLP(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_dim, 1)
        )
    def forward(self, x):
        return self.net(x).squeeze()

results = []

for model_id, model_name, model_type, ext in models_info:
    print(f"\n{'='*80}")
    print(f"Model {model_id:02d}: {model_name}")
    print(f"{'='*80}")

    # Load test Spearman from results
    with open(f"step3_unseen_drug_{model_id:02d}_results.json") as f:
        result_data = json.load(f)
    test_sp = result_data['regression_metrics']['spearman']

    # Load model and predict on training data
    model_file = f"step3_unseen_drug_{model_id:02d}_model.{ext}"

    if model_type == 'cpu':
        with open(model_file, 'rb') as f:
            model = pickle.load(f)
        train_pred = model.predict(X_train)

    else:  # GPU models
        if model_id == 10:
            model = FlatMLP(X.shape[1]).to(device)
        elif model_id == 12:
            model = FTTransformerMLP(X.shape[1]).to(device)
        elif model_id == 13:
            model = CrossAttentionMLP(X.shape[1]).to(device)

        model.load_state_dict(torch.load(model_file, map_location=device))
        model.eval()

        with torch.no_grad():
            X_train_tensor = torch.FloatTensor(X_train).to(device)
            train_pred = model(X_train_tensor).cpu().numpy()

    # Calculate Train Spearman
    train_sp = spearmanr(y_train, train_pred)[0]

    # Calculate Gap and Ratio
    gap = train_sp - test_sp
    ratio = test_sp / train_sp if train_sp > 0 else 0.0

    # Determine verdict
    if gap < 0.05:
        verdict = "NORMAL"
    elif gap < 0.10:
        verdict = "WARNING"
    elif gap < 0.15:
        verdict = "OVERFITTING"
    else:
        verdict = "SEVERE"

    print(f"  Train Sp: {train_sp:.4f}")
    print(f"  Test Sp:  {test_sp:.4f}")
    print(f"  Gap:      {gap:.4f}")
    print(f"  Ratio:    {ratio:.4f}")
    print(f"  Verdict:  {verdict}")

    results.append({
        'model_id': model_id,
        'model_name': model_name,
        'train_spearman': train_sp,
        'test_spearman': test_sp,
        'gap': gap,
        'ratio': ratio,
        'verdict': verdict
    })

    # Update the results JSON
    result_data['train_spearman'] = train_sp
    result_data['overfitting_gap'] = gap
    result_data['test_train_ratio'] = ratio
    result_data['overfitting_verdict'] = verdict

    with open(f"step3_unseen_drug_{model_id:02d}_results.json", 'w') as f:
        json.dump(result_data, f, indent=2)

# Save summary
summary = {
    'stage': 'step3_unseen_drug',
    'results': results
}

with open('step3_unseen_drug_train_spearman_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("\n" + "="*80)
print("Step 3 Train Spearman 계산 완료!")
print("="*80)

# Print table
print("\n결과 테이블:")
print(f"{'Model':<20} {'Train Sp':>10} {'Test Sp':>10} {'Gap':>10} {'Ratio':>10} {'Verdict':<15}")
print("-"*80)
for r in results:
    print(f"{r['model_name']:<20} {r['train_spearman']:>10.4f} {r['test_spearman']:>10.4f} "
          f"{r['gap']:>10.4f} {r['ratio']:>10.4f} {r['verdict']:<15}")
