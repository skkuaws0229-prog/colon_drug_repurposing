#!/usr/bin/env python3
"""
DL Model Training (5 models) with GroupKFold CV
Data: final_features_20260413.parquet (local, CRISPR→Pathway+Target 대체)
CV: GroupKFold(n_splits=5, groups=canonical_drug_id)
Models: ResidualMLP, FlatMLP, TabNet, FT_Transformer, Cross_Attention
Device: MPS (M4 GPU)
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import spearmanr, pearsonr

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"

SEED = 42
N_FOLDS = 5
BENCH_SP = 0.713
BENCH_RMSE = 1.385
OUTPUT_DIR = PROJECT_ROOT / "results" / "dl_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

torch.manual_seed(SEED)
np.random.seed(SEED)

ID_COLS = ["sample_id", "canonical_drug_id"]
LABEL_PREFIX = "label_"
DRUG_PREFIXES = ["drug_morgan_", "lincs_", "drug_desc_"]
DRUG_EXACT = ["drug__has_smiles", "drug_has_valid_smiles"]

# Device
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")
print(f"Using device: {DEVICE}")


def load_data():
    """Load final_features parquet. Order: [sample_cols | drug_cols] for CrossAttention."""
    print("Loading data from local parquet...")
    t0 = time.time()

    df = pd.read_parquet(DATA_PATH)

    label_cols = [c for c in df.columns if c.startswith(LABEL_PREFIX)]
    feat_cols = [c for c in df.columns if c not in ID_COLS + label_cols]

    # Identify drug vs sample columns
    drug_cols = []
    for c in feat_cols:
        if any(c.startswith(p) for p in DRUG_PREFIXES) or c in DRUG_EXACT:
            drug_cols.append(c)
    sample_cols = [c for c in feat_cols if c not in drug_cols]

    # Order: sample first, drug second (for CrossAttentionNet)
    ordered_cols = sample_cols + drug_cols
    sample_dim = len(sample_cols)

    X = df[ordered_cols].fillna(0.0).values.astype(np.float32)
    y = df["label_regression"].values.astype(np.float32)
    drug_ids = df["canonical_drug_id"].values

    dt = time.time() - t0
    print(f"  Loaded: {X.shape[0]} x {X.shape[1]} features ({dt:.1f}s)")
    print(f"  Sample features (pathway+target): {sample_dim}")
    print(f"  Drug features: {len(drug_cols)}")
    print(f"  Unique drugs: {len(np.unique(drug_ids))}")
    print(f"  CV: GroupKFold(n_splits={N_FOLDS})")
    return X, y, drug_ids, sample_dim


# ── Model Definitions (architecture unchanged) ──

class ResidualMLP(nn.Module):
    def __init__(self, in_dim, hidden=512, n_blocks=3, dropout=0.3):
        super().__init__()
        self.input_proj = nn.Linear(in_dim, hidden)
        self.blocks = nn.ModuleList()
        for _ in range(n_blocks):
            self.blocks.append(nn.Sequential(
                nn.LayerNorm(hidden),
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
                nn.Dropout(dropout),
            ))
        self.head = nn.Sequential(nn.LayerNorm(hidden), nn.Linear(hidden, 1))

    def forward(self, x):
        h = self.input_proj(x)
        for block in self.blocks:
            h = h + block(h)
        return self.head(h).squeeze(-1)


class FlatMLP(nn.Module):
    def __init__(self, in_dim, layers=[1024, 512, 256], dropout=0.3):
        super().__init__()
        modules = []
        prev = in_dim
        for h in layers:
            modules += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.GELU(), nn.Dropout(dropout)]
            prev = h
        modules.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*modules)

    def forward(self, x):
        return self.net(x).squeeze(-1)


class TabNet(nn.Module):
    def __init__(self, in_dim, n_steps=3, hidden=256, attn_bottleneck=256, dropout=0.3):
        super().__init__()
        self.bn = nn.BatchNorm1d(in_dim)
        self.steps = nn.ModuleList()
        for _ in range(n_steps):
            self.steps.append(nn.ModuleDict({
                'attn': nn.Sequential(
                    nn.Linear(in_dim, attn_bottleneck),
                    nn.GELU(),
                    nn.Linear(attn_bottleneck, in_dim),
                    nn.Sigmoid(),
                ),
                'fc': nn.Sequential(
                    nn.Linear(in_dim, hidden), nn.BatchNorm1d(hidden),
                    nn.GELU(), nn.Dropout(dropout),
                ),
            }))
        self.head = nn.Linear(hidden * n_steps, 1)

    def forward(self, x):
        x = self.bn(x)
        outs = []
        for step in self.steps:
            mask = step['attn'](x)
            h = step['fc'](x * mask)
            outs.append(h)
        return self.head(torch.cat(outs, dim=1)).squeeze(-1)


class FTTransformer(nn.Module):
    def __init__(self, in_dim, d_model=128, nhead=4, n_layers=2, dropout=0.2):
        super().__init__()
        self.n_tokens = 64
        chunk_size = in_dim // self.n_tokens + 1
        self.chunk_size = chunk_size
        self.token_proj = nn.Linear(chunk_size, d_model)
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model*2,
            dropout=dropout, batch_first=True, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Sequential(nn.LayerNorm(d_model), nn.Linear(d_model, 1))

    def forward(self, x):
        B = x.size(0)
        pad_len = self.n_tokens * self.chunk_size - x.size(1)
        if pad_len > 0:
            x = torch.cat([x, torch.zeros(B, pad_len, device=x.device)], dim=1)
        x = x.view(B, self.n_tokens, self.chunk_size)
        tokens = self.token_proj(x)
        cls = self.cls_token.expand(B, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        h = self.transformer(tokens)
        return self.head(h[:, 0]).squeeze(-1)


class CrossAttentionNet(nn.Module):
    def __init__(self, in_dim, sample_dim, d_model=128, nhead=4, dropout=0.2):
        super().__init__()
        drug_dim = in_dim - sample_dim
        self.sample_dim = sample_dim
        self.sample_proj = nn.Sequential(nn.Linear(sample_dim, d_model), nn.GELU())
        self.drug_proj = nn.Sequential(nn.Linear(drug_dim, d_model), nn.GELU())
        self.cross_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.ffn = nn.Sequential(
            nn.LayerNorm(d_model * 2),
            nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_model, 1),
        )

    def forward(self, x):
        sample_x = x[:, :self.sample_dim]
        drug_x = x[:, self.sample_dim:]
        s = self.sample_proj(sample_x).unsqueeze(1)
        d = self.drug_proj(drug_x).unsqueeze(1)
        attn_out, _ = self.cross_attn(s, d, d)
        combined = torch.cat([attn_out.squeeze(1), s.squeeze(1)], dim=1)
        return self.ffn(combined).squeeze(-1)


# ── Training Loop ──

def train_model(model, X_tr, y_tr, X_val, y_val, epochs=100, lr=1e-3, batch_size=256, patience=15):
    if DEVICE.type == "mps":
        torch.mps.empty_cache()
    model = model.to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    X_tr_t = torch.tensor(X_tr, device=DEVICE)
    y_tr_t = torch.tensor(y_tr, device=DEVICE)
    X_val_t = torch.tensor(X_val, device=DEVICE)

    train_ds = TensorDataset(X_tr_t, y_tr_t)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)

    best_val_loss = float('inf')
    best_state = None
    wait = 0

    for epoch in range(epochs):
        model.train()
        for xb, yb in train_dl:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_pred = model(X_val_t).cpu().numpy()
            val_loss = mean_squared_error(y_val, val_pred)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        y_pred_val = model(X_val_t).cpu().numpy()
        y_pred_tr = model(X_tr_t).cpu().numpy()
    return y_pred_val, y_pred_tr


def compute_metrics(y_true, y_pred, y_tr_true=None, y_tr_pred=None):
    sp, _ = spearmanr(y_true, y_pred)
    pe, _ = pearsonr(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    m = {"spearman": sp, "pearson": pe, "rmse": rmse, "r2": r2}
    if y_tr_true is not None:
        tr_sp, _ = spearmanr(y_tr_true, y_tr_pred)
        m["train_spearman"] = tr_sp
        m["gap_spearman"] = tr_sp - sp
    return m


def run_dl_cv(name, model_cls, model_kwargs, X, y, drug_ids, epochs=100, lr=1e-3, batch_size=256):
    print(f"\n{'─'*60}")
    print(f"  [{name}] Training with 5-fold GroupKFold CV...")
    print(f"{'─'*60}")

    gkf = GroupKFold(n_splits=N_FOLDS)
    fold_metrics = []
    total_t0 = time.time()

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=drug_ids)):
        t0 = time.time()
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr).astype(np.float32)
        X_val_s = scaler.transform(X_val).astype(np.float32)

        torch.manual_seed(SEED + fold_idx)
        if DEVICE.type == "mps":
            torch.mps.empty_cache()
        model = model_cls(**model_kwargs)
        y_pred_val, y_pred_tr = train_model(model, X_tr_s, y_tr, X_val_s, y_val,
                                             epochs=epochs, lr=lr, batch_size=batch_size)

        m = compute_metrics(y_val, y_pred_val, y_tr, y_pred_tr)
        m["fold"] = fold_idx
        fold_metrics.append(m)
        dt = time.time() - t0
        print(f"  Fold {fold_idx}: Sp={m['spearman']:.4f}  RMSE={m['rmse']:.4f}  "
              f"R2={m['r2']:.4f}  Gap(Sp)={m['gap_spearman']:.4f}  ({dt:.1f}s)")

    total_time = time.time() - total_t0
    df = pd.DataFrame(fold_metrics)
    summary = {
        "model": name,
        "spearman_mean": float(df["spearman"].mean()),
        "spearman_std": float(df["spearman"].std()),
        "rmse_mean": float(df["rmse"].mean()),
        "rmse_std": float(df["rmse"].std()),
        "pearson_mean": float(df["pearson"].mean()),
        "r2_mean": float(df["r2"].mean()),
        "r2_std": float(df["r2"].std()),
        "train_spearman_mean": float(df["train_spearman"].mean()),
        "gap_spearman_mean": float(df["gap_spearman"].mean()),
        "elapsed_sec": total_time,
        "folds": fold_metrics,
    }

    sp_flag = "PASS" if summary["spearman_mean"] >= BENCH_SP else "FAIL"
    rm_flag = "PASS" if summary["rmse_mean"] <= BENCH_RMSE else "FAIL"
    print(f"\n  >>> {name} SUMMARY:")
    print(f"      Spearman: {summary['spearman_mean']:.4f} +/- {summary['spearman_std']:.4f}  [{sp_flag} vs {BENCH_SP}]")
    print(f"      RMSE:     {summary['rmse_mean']:.4f} +/- {summary['rmse_std']:.4f}  [{rm_flag} vs {BENCH_RMSE}]")
    print(f"      Pearson:  {summary['pearson_mean']:.4f}")
    print(f"      R2:       {summary['r2_mean']:.4f} +/- {summary['r2_std']:.4f}")
    print(f"      Train Sp: {summary['train_spearman_mean']:.4f}  Gap: {summary['gap_spearman_mean']:.4f}")
    print(f"      Time:     {total_time/60:.1f} min")

    return summary


# ── Main ──

def main():
    run_only = sys.argv[1] if len(sys.argv) > 1 else "all"

    X, y, drug_ids, sample_dim = load_data()
    in_dim = X.shape[1]

    print(f"  in_dim={in_dim}, sample_dim={sample_dim}, drug_dim={in_dim - sample_dim}")

    models_config = [
        ("9_ResidualMLP", ResidualMLP, {"in_dim": in_dim, "hidden": 512, "n_blocks": 3, "dropout": 0.3},
         {"epochs": 100, "lr": 1e-3, "batch_size": 256}),
        ("10_FlatMLP", FlatMLP, {"in_dim": in_dim, "layers": [1024, 512, 256], "dropout": 0.3},
         {"epochs": 100, "lr": 1e-3, "batch_size": 256}),
        ("11_TabNet", TabNet, {"in_dim": in_dim, "n_steps": 3, "hidden": 256, "dropout": 0.3},
         {"epochs": 100, "lr": 1e-3, "batch_size": 256}),
        ("12_FT_Transformer", FTTransformer, {"in_dim": in_dim, "d_model": 128, "nhead": 4, "n_layers": 2, "dropout": 0.2},
         {"epochs": 80, "lr": 5e-4, "batch_size": 128}),
        ("13_Cross_Attention", CrossAttentionNet, {"in_dim": in_dim, "sample_dim": sample_dim, "d_model": 128, "nhead": 4, "dropout": 0.2},
         {"epochs": 80, "lr": 5e-4, "batch_size": 256}),
    ]

    if run_only != "all":
        models_config = [m for m in models_config if m[0] == run_only]
        if not models_config:
            print(f"Model '{run_only}' not found!")
            return

    all_results = []
    for name, cls, kwargs, train_kwargs in models_config:
        result = run_dl_cv(name, cls, kwargs, X, y, drug_ids, **train_kwargs)
        all_results.append(result)

    # Summary table
    if len(all_results) > 1:
        print("\n" + "=" * 90)
        print(f"  DL MODELS SUMMARY TABLE (GroupKFold)")
        print("=" * 90)
        print(f"{'Model':<22} {'Val Sp':>8} {'  std':>6} {'Train Sp':>9} {'Gap(Sp)':>8} "
              f"{'RMSE':>8} {'  std':>6} {'Pearson':>8} {'R2':>8} {'Time':>6}")
        print("-" * 90)
        for r in all_results:
            sp_f = " *" if r["spearman_mean"] >= BENCH_SP else ""
            rm_f = " *" if r["rmse_mean"] <= BENCH_RMSE else ""
            print(f"{r['model']:<22} {r['spearman_mean']:>8.4f}{sp_f:>2} "
                  f"{r['spearman_std']:>6.4f} {r['train_spearman_mean']:>9.4f} "
                  f"{r['gap_spearman_mean']:>8.4f} {r['rmse_mean']:>8.4f}{rm_f:>2} "
                  f"{r['rmse_std']:>6.4f} {r['pearson_mean']:>8.4f} {r['r2_mean']:>8.4f} "
                  f"{r['elapsed_sec']/60:>5.1f}m")
        print("-" * 90)
        print(f"  Benchmark: Spearman >= {BENCH_SP}, RMSE <= {BENCH_RMSE}  (* = meets benchmark)")

    # Save
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        return obj

    out_path = OUTPUT_DIR / "dl_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=convert)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
