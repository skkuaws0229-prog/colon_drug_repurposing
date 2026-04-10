#!/usr/bin/env python3
"""
Multimodal Fusion Training — Cross-Attention (Sample Q × Drug K/V)

Data: S3 features.parquet + pair_features_newfe_v2.parquet + labels.parquet
Model: MultiModalFusionNet (5 encoders + cross-attention)
Task: IC50 regression (MSELoss)
"""
import warnings
warnings.filterwarnings("ignore")

import gc
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr, pearsonr

from multimodal_fusion import MultiModalFusionNet, DATA_PATHS, MODALITY_COLUMNS

# ── Config ───────────────────────────────────────────────────────

SEED = 42
EPOCHS = 50
BATCH_SIZE = 256
LR = 1e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 10
VAL_RATIO = 0.2

# Pre-project benchmarks for comparison
BENCH_SPEARMAN = 0.713
BENCH_RMSE = 1.385

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

torch.manual_seed(SEED)
np.random.seed(SEED)

# Device
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")


# ── Data Loading ─────────────────────────────────────────────────

def load_data():
    """Load from S3, merge, and split into per-modality arrays."""
    print("=" * 70)
    print("Loading data from S3...")
    t0 = time.time()

    features = pd.read_parquet(DATA_PATHS["features"])
    pair_features = pd.read_parquet(DATA_PATHS["pair_features"])
    labels = pd.read_parquet(DATA_PATHS["labels"])

    merged = features.merge(
        pair_features, on=["sample_id", "canonical_drug_id"], how="inner",
    )
    labels = labels.set_index(["sample_id", "canonical_drug_id"])
    merged = merged.set_index(["sample_id", "canonical_drug_id"])
    labels = labels.loc[merged.index]

    y = labels["label_regression"].values.astype(np.float32)
    dt = time.time() - t0
    print(f"  Merged: {merged.shape[0]:,} rows x {merged.shape[1]:,} cols ({dt:.1f}s)")

    # Split columns by modality prefix
    col_groups = {}
    for mod_name, spec in MODALITY_COLUMNS.items():
        cols = sorted([c for c in merged.columns if c.startswith(spec["prefix"])])
        assert len(cols) == spec["count"], (
            f"{mod_name}: expected {spec['count']} cols, got {len(cols)}"
        )
        col_groups[mod_name] = cols
        print(f"  {mod_name:12s}: {len(cols):>6,} cols")

    # Extract numpy arrays per modality
    X_crispr = merged[col_groups["crispr"]].values.astype(np.float32)
    X_morgan = merged[col_groups["morgan_fp"]].values.astype(np.float32)
    X_lincs = merged[col_groups["lincs"]].values.astype(np.float32)
    X_target = merged[col_groups["target"]].values.astype(np.float32)
    X_drugdesc = merged[col_groups["drug_desc"]].values.astype(np.float32)

    # Fill NaN
    for arr in (X_crispr, X_morgan, X_lincs, X_target, X_drugdesc):
        np.nan_to_num(arr, copy=False, nan=0.0)

    print(f"  y: mean={y.mean():.3f}, std={y.std():.3f}")
    print("=" * 70)

    return X_crispr, X_morgan, X_lincs, X_target, X_drugdesc, y


def make_dataloaders(X_crispr, X_morgan, X_lincs, X_target, X_drugdesc, y):
    """Train/val split → StandardScaler per modality → DataLoaders."""
    idx_tr, idx_val = train_test_split(
        np.arange(len(y)), test_size=VAL_RATIO, random_state=SEED,
    )

    # Per-modality standardisation (fit on train only)
    scalers = {}
    arrays_tr, arrays_val = {}, {}
    for name, X_all in [
        ("crispr", X_crispr), ("morgan", X_morgan), ("lincs", X_lincs),
        ("target", X_target), ("drugdesc", X_drugdesc),
    ]:
        sc = StandardScaler()
        arrays_tr[name] = sc.fit_transform(X_all[idx_tr]).astype(np.float32)
        arrays_val[name] = sc.transform(X_all[idx_val]).astype(np.float32)
        scalers[name] = sc

    y_tr, y_val = y[idx_tr], y[idx_val]

    def _to_dl(arrs, y_arr, shuffle):
        tensors = [torch.from_numpy(arrs[k]) for k in
                   ["crispr", "morgan", "lincs", "target", "drugdesc"]]
        tensors.append(torch.from_numpy(y_arr))
        ds = TensorDataset(*tensors)
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle, drop_last=shuffle)

    train_dl = _to_dl(arrays_tr, y_tr, shuffle=True)
    val_dl = _to_dl(arrays_val, y_val, shuffle=False)

    print(f"  Train: {len(idx_tr):,}  Val: {len(idx_val):,}")
    return train_dl, val_dl, y_val


# ── Training Loop ────────────────────────────────────────────────

def train(model, train_dl, val_dl):
    model = model.to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    best_state = None
    wait = 0
    history = {"train_loss": [], "val_loss": []}

    print(f"\n{'='*70}")
    print(f"  Training MultiModalFusionNet  |  device={DEVICE}")
    print(f"  epochs={EPOCHS}  batch={BATCH_SIZE}  lr={LR}  patience={PATIENCE}")
    print(f"{'='*70}")

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()

        # ── Train ──
        model.train()
        train_losses = []
        for batch in train_dl:
            cr, mg, li, tg, dd, yb = [b.to(DEVICE) for b in batch]
            optimizer.zero_grad()
            pred = model(cr, mg, li, tg, dd)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item() * len(yb))
        scheduler.step()
        train_loss = sum(train_losses) / sum(len(b[0]) for b in train_dl)

        # ── Val ──
        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch in val_dl:
                cr, mg, li, tg, dd, yb = [b.to(DEVICE) for b in batch]
                pred = model(cr, mg, li, tg, dd)
                loss = criterion(pred, yb)
                val_losses.append(loss.item() * len(yb))
        val_loss = sum(val_losses) / sum(len(b[0]) for b in val_dl)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        dt = time.time() - t0
        marker = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
            marker = " *"
        else:
            wait += 1

        print(f"  Epoch {epoch:3d}/{EPOCHS}  "
              f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  "
              f"({dt:.1f}s){marker}")

        if wait >= PATIENCE:
            print(f"  Early stopping at epoch {epoch} (patience={PATIENCE})")
            break

    # Restore best
    if best_state:
        model.load_state_dict(best_state)
    model_path = RESULTS_DIR / "best_multimodal_model.pt"
    torch.save(best_state, model_path)
    print(f"\n  Best model saved: {model_path}  (val_loss={best_val_loss:.4f})")

    return model, history


# ── Evaluation ───────────────────────────────────────────────────

def evaluate(model, val_dl, y_val_np):
    model.eval()
    preds = []
    with torch.no_grad():
        for batch in val_dl:
            cr, mg, li, tg, dd, _ = [b.to(DEVICE) for b in batch]
            pred = model(cr, mg, li, tg, dd)
            preds.append(pred.cpu().numpy())
    y_pred = np.concatenate(preds)

    rmse = float(np.sqrt(mean_squared_error(y_val_np, y_pred)))
    mae = float(mean_absolute_error(y_val_np, y_pred))
    r2 = float(r2_score(y_val_np, y_pred))
    sp, _ = spearmanr(y_val_np, y_pred)
    pe, _ = pearsonr(y_val_np, y_pred)

    sp_flag = "PASS" if sp >= BENCH_SPEARMAN else "FAIL"
    rm_flag = "PASS" if rmse <= BENCH_RMSE else "FAIL"

    print(f"\n{'='*70}")
    print(f"  Validation Metrics")
    print(f"{'='*70}")
    print(f"  RMSE     : {rmse:.4f}   [{rm_flag} vs benchmark {BENCH_RMSE}]")
    print(f"  MAE      : {mae:.4f}")
    print(f"  R²       : {r2:.4f}")
    print(f"  Spearman : {sp:.4f}   [{sp_flag} vs benchmark {BENCH_SPEARMAN}]")
    print(f"  Pearson  : {pe:.4f}")
    print(f"{'='*70}")

    return {"rmse": rmse, "mae": mae, "r2": r2, "spearman": float(sp), "pearson": float(pe)}, y_pred


# ── Overfitting Diagnostics ──────────────────────────────────────

def overfitting_diagnostics(history, y_val_np, y_pred):
    """Compute and print overfitting diagnostics."""
    train_losses = history["train_loss"]
    val_losses = history["val_loss"]
    total_epochs = len(train_losses)

    final_train = train_losses[-1]
    final_val = val_losses[-1]
    best_val = min(val_losses)
    best_epoch = val_losses.index(best_val) + 1

    # Best epoch의 train loss로 ratio 계산
    best_train = train_losses[best_epoch - 1]
    overfit_ratio = best_val / best_train if best_train > 0 else float("inf")

    if overfit_ratio <= 1.2:
        overfit_label = "NORMAL"
    elif overfit_ratio <= 1.5:
        overfit_label = "WARNING"
    else:
        overfit_label = "OVERFITTING"

    # 학습 안정성: 마지막 5 epoch 변화량
    n_tail = min(5, total_epochs)
    tail_train = train_losses[-n_tail:]
    tail_val = val_losses[-n_tail:]
    train_delta = tail_train[-1] - tail_train[0]
    val_delta = tail_val[-1] - tail_val[0]
    train_std = float(np.std(tail_train))
    val_std = float(np.std(tail_val))
    converged = train_std < 0.05 and val_std < 0.05

    # 예측값 분포
    pred_stats = {
        "mean": float(np.mean(y_pred)),
        "std": float(np.std(y_pred)),
        "min": float(np.min(y_pred)),
        "max": float(np.max(y_pred)),
    }
    actual_stats = {
        "mean": float(np.mean(y_val_np)),
        "std": float(np.std(y_val_np)),
        "min": float(np.min(y_val_np)),
        "max": float(np.max(y_val_np)),
    }

    # ── Print ──
    print(f"\n{'='*70}")
    print(f"  Overfitting Diagnostics")
    print(f"{'='*70}")

    print(f"\n  [1] Train vs Val Loss")
    print(f"      Final train_loss : {final_train:.4f}")
    print(f"      Final val_loss   : {final_val:.4f}")
    print(f"      Best  val_loss   : {best_val:.4f}  (epoch {best_epoch})")
    print(f"      Gap (val-train)  : {final_val - final_train:+.4f}")

    print(f"\n  [2] Overfitting Ratio  (best_val / best_train)")
    print(f"      {best_val:.4f} / {best_train:.4f} = {overfit_ratio:.4f}")
    print(f"      판정: {overfit_label}  (1.0~1.2: 정상 / 1.2~1.5: 경계 / 1.5+: 과적합)")

    print(f"\n  [3] Learning Stability  (last {n_tail} epochs)")
    print(f"      Train Δ : {train_delta:+.4f}   std={train_std:.4f}")
    print(f"      Val   Δ : {val_delta:+.4f}   std={val_std:.4f}")
    print(f"      수렴 여부 : {'YES' if converged else 'NO'}  (std < 0.05)")
    print(f"      Early stop epoch : {total_epochs} / {EPOCHS}")

    print(f"\n  [4] Prediction Distribution")
    print(f"      {'':12s} {'mean':>8s} {'std':>8s} {'min':>8s} {'max':>8s}")
    print(f"      {'Actual':12s} {actual_stats['mean']:8.3f} {actual_stats['std']:8.3f} "
          f"{actual_stats['min']:8.3f} {actual_stats['max']:8.3f}")
    print(f"      {'Predicted':12s} {pred_stats['mean']:8.3f} {pred_stats['std']:8.3f} "
          f"{pred_stats['min']:8.3f} {pred_stats['max']:8.3f}")
    mean_gap = abs(pred_stats["mean"] - actual_stats["mean"])
    std_gap = abs(pred_stats["std"] - actual_stats["std"])
    print(f"      Mean gap : {mean_gap:.3f}   Std gap : {std_gap:.3f}")

    print(f"{'='*70}")

    return {
        "final_train_loss": final_train,
        "final_val_loss": final_val,
        "best_val_loss": best_val,
        "best_epoch": best_epoch,
        "gap_val_minus_train": round(final_val - final_train, 4),
        "overfitting_ratio": round(overfit_ratio, 4),
        "overfitting_label": overfit_label,
        "stability": {
            "last_n_epochs": n_tail,
            "train_delta": round(train_delta, 4),
            "val_delta": round(val_delta, 4),
            "train_std": round(train_std, 4),
            "val_std": round(val_std, 4),
            "converged": converged,
            "early_stop_epoch": total_epochs,
        },
        "pred_distribution": pred_stats,
        "actual_distribution": actual_stats,
    }


# ── Plot Training Curve ──────────────────────────────────────────

def plot_curve(history):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed, skipping training curve plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    epochs = range(1, len(history["train_loss"]) + 1)
    ax.plot(epochs, history["train_loss"], label="Train Loss", linewidth=2)
    ax.plot(epochs, history["val_loss"], label="Val Loss", linewidth=2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("MultiModalFusionNet Training Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path = RESULTS_DIR / "training_curve.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Training curve saved: {out_path}")


# ── Main ─────────────────────────────────────────────────────────

def main():
    total_t0 = time.time()
    print(f"Device: {DEVICE}")

    # 1. Load & split
    X_crispr, X_morgan, X_lincs, X_target, X_drugdesc, y = load_data()
    train_dl, val_dl, y_val = make_dataloaders(
        X_crispr, X_morgan, X_lincs, X_target, X_drugdesc, y,
    )

    # 2. Train
    model = MultiModalFusionNet(d_model=128, nhead=4, dropout=0.2)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model params: {n_params:,}")

    model, history = train(model, train_dl, val_dl)

    # 3. Evaluate
    metrics, y_pred = evaluate(model, val_dl, y_val)

    # 4. Overfitting diagnostics
    diag = overfitting_diagnostics(history, y_val, y_pred)

    # 5. Plot
    plot_curve(history)

    # 6. Save results JSON
    results = {
        "model": "MultiModalFusionNet",
        "architecture": "5-encoder cross-attention fusion",
        "config": {
            "d_model": 128, "nhead": 4, "dropout": 0.2,
            "epochs": EPOCHS, "batch_size": BATCH_SIZE,
            "lr": LR, "weight_decay": WEIGHT_DECAY,
            "patience": PATIENCE, "val_ratio": VAL_RATIO,
        },
        "modality_dims": {
            "crispr": 18310, "morgan_fp": 2048,
            "lincs": 5, "target": 10, "drug_desc": 9,
        },
        "total_params": n_params,
        "device": str(DEVICE),
        "metrics": metrics,
        "overfitting_diagnostics": diag,
        "benchmark": {"spearman": BENCH_SPEARMAN, "rmse": BENCH_RMSE},
        "training_epochs": len(history["train_loss"]),
        "best_val_loss": float(min(history["val_loss"])),
        "elapsed_min": round((time.time() - total_t0) / 60, 1),
    }
    results_path = RESULTS_DIR / "multimodal_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {results_path}")
    print(f"  Total time: {results['elapsed_min']} min")

    # 7. Memory cleanup
    cleanup_memory(model, train_dl, val_dl)


def cleanup_memory(*objects):
    """학습 완료 후 GPU/CPU 메모리 해제."""
    import psutil

    print(f"\n{'='*70}")
    print(f"  Memory Cleanup")
    print(f"{'='*70}")

    ram_before = psutil.virtual_memory()
    print(f"  정리 전 여유 RAM: {ram_before.available / 1024**3:.1f} GB ({100 - ram_before.percent:.1f}%)")

    # 참조 해제
    for obj in objects:
        del obj

    # MPS 캐시 해제
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    elif torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Python GC
    gc.collect()

    ram_after = psutil.virtual_memory()
    freed = (ram_after.available - ram_before.available) / 1024**2
    print(f"  정리 후 여유 RAM: {ram_after.available / 1024**3:.1f} GB ({100 - ram_after.percent:.1f}%)")
    print(f"  해제된 메모리  : {freed:+.0f} MB")
    print(f"  메모리 정리 완료")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
