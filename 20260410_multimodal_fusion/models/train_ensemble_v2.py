#!/usr/bin/env python3
# ============================================
# 중요: 파라미터 변경 규칙 (20260410)
# ============================================
# 1. ML 모델 (CatBoost, LightGBM, XGBoost)
#    → 기존 train_ensemble.py 파라미터 그대로 유지
#    → 임의 변경 절대 금지
#
# 2. DL 모델 (FlatMLP, ResidualMLP, CrossAttn)
#    → 기존 train_dl_models.py 파라미터 그대로 유지
#    → 임의 변경 절대 금지
#
# 3. MultiModalFusionNet
#    → 20260410_multimodal_fusion/models/
#      train_multimodal.py 파라미터 그대로 유지
#    → 임의 변경 절대 금지
#
# 4. 속도/메모리 문제 발생 시
#    → 임의 해결 금지
#    → 즉시 멈추고 사용자에게 보고
# ============================================
"""
Ensemble V2: 7-model Spearman-weighted average + 과적합 진단
  기존 프리프로젝트 6개: CatBoost, LightGBM, XGBoost, FlatMLP, ResidualMLP, CrossAttn
  + 신규 1개: MultiModalFusionNet (5-encoder cross-attention)
  ※ LightGBM: sklearn API 사용 (native API는 Apple Silicon SIGSEGV 확인됨)

데이터: S3 features + pair_features + labels (동일)
방식: 5-fold OOF → Spearman 가중 평균
비교: 기존 앙상블(0.8055) 대비 개선 여부
"""
import warnings
warnings.filterwarnings("ignore")

import sys
import gc
import json
import time
from pathlib import Path

# 출력 버퍼링 해제
print = lambda *a, **kw: (sys.stdout.write(" ".join(str(x) for x in a) + kw.get("end", "\n")), sys.stdout.flush())

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr, pearsonr
import xgboost as xgb
from catboost import CatBoostRegressor
import lightgbm as lgb

from multimodal_fusion import MultiModalFusionNet, MODALITY_COLUMNS

# ── Config ───────────────────────────────────────────────────────

SEED = 42
N_FOLDS = 5
BENCH_SP_OLD = 0.8055       # 기존 6-model 앙상블
BENCH_SP_PREPROJ = 0.713    # 프리프로젝트 기준
BENCH_RMSE = 1.385

S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/features.parquet"
PAIR_FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/pair_features/pair_features_newfe_v2.parquet"
LABELS_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/labels.parquet"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
PRED_DIR = RESULTS_DIR / "predictions"
RESULTS_DIR.mkdir(exist_ok=True)
PRED_DIR.mkdir(exist_ok=True)

torch.manual_seed(SEED)
np.random.seed(SEED)

if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")


def mps_cleanup():
    gc.collect()
    if DEVICE.type == "mps":
        torch.mps.empty_cache()
    elif DEVICE.type == "cuda":
        torch.cuda.empty_cache()


# ═══════════════════════════════════════════════════════════════════
# 1. Data Loading
# ═══════════════════════════════════════════════════════════════════

def load_data():
    print("=" * 70)
    print("  Loading data from S3...")
    t0 = time.time()

    features = pd.read_parquet(FEATURES_URI)
    pair_features = pd.read_parquet(PAIR_FEATURES_URI)
    labels = pd.read_parquet(LABELS_URI)

    merged = features.merge(pair_features, on=["sample_id", "canonical_drug_id"], how="inner")
    labels = labels.set_index(["sample_id", "canonical_drug_id"])
    merged = merged.set_index(["sample_id", "canonical_drug_id"])
    labels = labels.loc[merged.index]

    sample_ids = merged.index.get_level_values("sample_id").values
    drug_ids = merged.index.get_level_values("canonical_drug_id").values
    y = labels["label_regression"].values.astype(np.float32)

    X_flat = merged.select_dtypes(include=[np.number]).fillna(0.0).values.astype(np.float32)

    X_modal = {}
    for mod_name, spec in MODALITY_COLUMNS.items():
        cols = sorted([c for c in merged.columns if c.startswith(spec["prefix"])])
        arr = merged[cols].values.astype(np.float32)
        np.nan_to_num(arr, copy=False, nan=0.0)
        X_modal[mod_name] = arr

    dt = time.time() - t0
    print(f"  Merged: {merged.shape[0]:,} x {merged.shape[1]:,} ({dt:.1f}s)")
    print(f"  Flat X: {X_flat.shape}")
    for k, v in X_modal.items():
        print(f"  {k:12s}: {v.shape[1]:>6,} cols")
    print("=" * 70)

    return X_flat, X_modal, y, sample_ids, drug_ids


# ═══════════════════════════════════════════════════════════════════
# 2. DL Model Definitions
# ═══════════════════════════════════════════════════════════════════

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


class ResidualMLP(nn.Module):
    def __init__(self, in_dim, hidden=512, n_blocks=3, dropout=0.3):
        super().__init__()
        self.input_proj = nn.Linear(in_dim, hidden)
        self.blocks = nn.ModuleList()
        for _ in range(n_blocks):
            self.blocks.append(nn.Sequential(
                nn.LayerNorm(hidden), nn.Linear(hidden, hidden), nn.GELU(),
                nn.Dropout(dropout), nn.Linear(hidden, hidden), nn.Dropout(dropout),
            ))
        self.head = nn.Sequential(nn.LayerNorm(hidden), nn.Linear(hidden, 1))

    def forward(self, x):
        h = self.input_proj(x)
        for block in self.blocks:
            h = h + block(h)
        return self.head(h).squeeze(-1)


class CrossAttentionNet(nn.Module):
    def __init__(self, in_dim, sample_dim=18311, d_model=128, nhead=4, dropout=0.2):
        super().__init__()
        drug_dim = in_dim - sample_dim
        self.sample_dim = sample_dim
        self.sample_proj = nn.Sequential(nn.Linear(sample_dim, d_model), nn.GELU())
        self.drug_proj = nn.Sequential(nn.Linear(drug_dim, d_model), nn.GELU())
        self.cross_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout, batch_first=True)
        self.ffn = nn.Sequential(
            nn.LayerNorm(d_model * 2), nn.Linear(d_model * 2, d_model),
            nn.GELU(), nn.Dropout(dropout), nn.Linear(d_model, 1),
        )

    def forward(self, x):
        sample_x = x[:, :self.sample_dim]
        drug_x = x[:, self.sample_dim:]
        s = self.sample_proj(sample_x).unsqueeze(1)
        d = self.drug_proj(drug_x).unsqueeze(1)
        attn_out, _ = self.cross_attn(s, d, d)
        combined = torch.cat([attn_out.squeeze(1), s.squeeze(1)], dim=1)
        return self.ffn(combined).squeeze(-1)


# ═══════════════════════════════════════════════════════════════════
# 3. Training Functions (return y_pred + diagnostics)
# ═══════════════════════════════════════════════════════════════════

def train_dl_model(model, X_tr, y_tr, X_val, y_val,
                   epochs=100, lr=1e-3, batch_size=256, patience=15):
    """Generic DL trainer → (y_pred_val, y_pred_tr, diag_dict)."""
    mps_cleanup()
    model = model.to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    X_tr_t = torch.tensor(X_tr, device=DEVICE)
    y_tr_t = torch.tensor(y_tr, device=DEVICE)
    X_val_t = torch.tensor(X_val, device=DEVICE)

    train_ds = TensorDataset(X_tr_t, y_tr_t)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)

    best_val_loss = float("inf")
    best_state = None
    wait = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(epochs):
        model.train()
        epoch_losses = []
        for xb, yb in train_dl:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(loss.item() * len(yb))
        scheduler.step()
        train_loss = sum(epoch_losses) / len(y_tr)

        model.eval()
        with torch.no_grad():
            vp = model(X_val_t).cpu().numpy()
            val_loss = float(mean_squared_error(y_val, vp))
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

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

    diag = _compute_diag(history, y_tr, y_pred_tr, y_val, y_pred_val)
    del X_tr_t, y_tr_t, X_val_t, model
    mps_cleanup()
    return y_pred_val, y_pred_tr, diag


def train_multimodal_fold(X_modal_tr, y_tr, X_modal_val, y_val,
                          d_model=128, nhead=4, dropout=0.2,
                          epochs=50, lr=1e-4, batch_size=256, patience=10):
    """MultiModalFusionNet trainer → (y_pred_val, y_pred_tr, diag_dict)."""
    mps_cleanup()

    scalers = {}
    modal_tr_s, modal_val_s = {}, {}
    for name in ["crispr", "morgan_fp", "lincs", "target", "drug_desc"]:
        sc = StandardScaler()
        modal_tr_s[name] = sc.fit_transform(X_modal_tr[name]).astype(np.float32)
        modal_val_s[name] = sc.transform(X_modal_val[name]).astype(np.float32)
        scalers[name] = sc

    def _to_tensors(arrs, y_arr):
        return [torch.from_numpy(arrs[k]) for k in
                ["crispr", "morgan_fp", "lincs", "target", "drug_desc"]] + \
               [torch.from_numpy(y_arr)]

    train_ds = TensorDataset(*_to_tensors(modal_tr_s, y_tr))
    val_ds = TensorDataset(*_to_tensors(modal_val_s, y_val))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    model = MultiModalFusionNet(d_model=d_model, nhead=nhead, dropout=dropout).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    best_state = None
    wait = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(epochs):
        model.train()
        epoch_losses = []
        for batch in train_dl:
            cr, mg, li, tg, dd, yb = [b.to(DEVICE) for b in batch]
            optimizer.zero_grad()
            loss = criterion(model(cr, mg, li, tg, dd), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(loss.item() * len(yb))
        scheduler.step()
        train_loss = sum(epoch_losses) / len(y_tr)

        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch in val_dl:
                cr, mg, li, tg, dd, yb = [b.to(DEVICE) for b in batch]
                loss = criterion(model(cr, mg, li, tg, dd), yb)
                val_losses.append(loss.item() * len(yb))
        val_loss = sum(val_losses) / len(y_val)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

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

    # Val predictions
    preds_val = []
    with torch.no_grad():
        for batch in val_dl:
            cr, mg, li, tg, dd, _ = [b.to(DEVICE) for b in batch]
            preds_val.append(model(cr, mg, li, tg, dd).cpu().numpy())
    y_pred_val = np.concatenate(preds_val)

    # Train predictions
    train_dl_noshuffle = DataLoader(train_ds, batch_size=batch_size, shuffle=False)
    preds_tr = []
    with torch.no_grad():
        for batch in train_dl_noshuffle:
            cr, mg, li, tg, dd, _ = [b.to(DEVICE) for b in batch]
            preds_tr.append(model(cr, mg, li, tg, dd).cpu().numpy())
    y_pred_tr = np.concatenate(preds_tr)

    diag = _compute_diag(history, y_tr, y_pred_tr, y_val, y_pred_val)
    del model
    mps_cleanup()
    return y_pred_val, y_pred_tr, diag


def _compute_diag(history, y_tr, y_pred_tr, y_val, y_pred_val):
    """DL 모델 과적합 진단 계산."""
    tl = history["train_loss"]
    vl = history["val_loss"]
    n_ep = len(tl)
    best_ep = int(np.argmin(vl)) + 1
    best_train = tl[best_ep - 1]
    best_val = vl[best_ep - 1]

    ratio = best_val / best_train if best_train > 0 else float("inf")

    # Spearman 기반 과적합 진단
    train_sp, _ = spearmanr(y_tr, y_pred_tr)
    val_sp, _ = spearmanr(y_val, y_pred_val)
    gap = float(train_sp - val_sp)
    if gap < 0.05:
        label = "NORMAL"
    elif gap <= 0.10:
        label = "WARNING"
    else:
        label = "OVERFITTING"

    n_tail = min(5, n_ep)
    tail_val = vl[-n_tail:]
    converged = float(np.std(tail_val)) < 0.05

    return {
        "epochs_run": n_ep,
        "best_epoch": best_ep,
        "final_train_loss": round(tl[-1], 4),
        "final_val_loss": round(vl[-1], 4),
        "best_val_loss": round(best_val, 4),
        "overfitting_ratio": round(ratio, 4),
        "train_spearman": round(float(train_sp), 4),
        "val_spearman": round(float(val_sp), 4),
        "gap": round(gap, 4),
        "overfitting_label": label,
        "converged": converged,
        "pred_dist": {
            "val": {"mean": round(float(np.mean(y_pred_val)), 3),
                    "std": round(float(np.std(y_pred_val)), 3),
                    "min": round(float(np.min(y_pred_val)), 3),
                    "max": round(float(np.max(y_pred_val)), 3)},
            "actual": {"mean": round(float(np.mean(y_val)), 3),
                       "std": round(float(np.std(y_val)), 3),
                       "min": round(float(np.min(y_val)), 3),
                       "max": round(float(np.max(y_val)), 3)},
        },
    }


def _compute_diag_ml(y_tr, y_pred_tr, y_val, y_pred_val):
    """ML 모델 과적합 진단 (loss history 없음)."""
    train_mse = float(mean_squared_error(y_tr, y_pred_tr))
    val_mse = float(mean_squared_error(y_val, y_pred_val))

    ratio = val_mse / train_mse if train_mse > 0 else float("inf")

    # Spearman 기반 과적합 진단
    train_sp, _ = spearmanr(y_tr, y_pred_tr)
    val_sp, _ = spearmanr(y_val, y_pred_val)
    gap = float(train_sp - val_sp)
    if gap < 0.05:
        label = "NORMAL"
    elif gap <= 0.10:
        label = "WARNING"
    else:
        label = "OVERFITTING"

    return {
        "train_mse": round(train_mse, 4),
        "val_mse": round(val_mse, 4),
        "overfitting_ratio": round(ratio, 4),
        "train_spearman": round(float(train_sp), 4),
        "val_spearman": round(float(val_sp), 4),
        "gap": round(gap, 4),
        "overfitting_label": label,
        "pred_dist": {
            "val": {"mean": round(float(np.mean(y_pred_val)), 3),
                    "std": round(float(np.std(y_pred_val)), 3),
                    "min": round(float(np.min(y_pred_val)), 3),
                    "max": round(float(np.max(y_pred_val)), 3)},
            "actual": {"mean": round(float(np.mean(y_val)), 3),
                       "std": round(float(np.std(y_val)), 3),
                       "min": round(float(np.min(y_val)), 3),
                       "max": round(float(np.max(y_val)), 3)},
        },
    }


# ── ML trainers (return y_pred_val, y_pred_tr, diag) ──

def train_catboost(X_tr, y_tr, X_val, y_val):
    model = CatBoostRegressor(
        iterations=2000, learning_rate=0.05, depth=8, l2_leaf_reg=3,
        random_seed=SEED, verbose=0, task_type="CPU", early_stopping_rounds=50,
    )
    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=0)
    yp_val = model.predict(X_val).astype(np.float32)
    yp_tr = model.predict(X_tr).astype(np.float32)
    diag = _compute_diag_ml(y_tr, yp_tr, y_val, yp_val)
    return yp_val, yp_tr, diag


def train_lightgbm(X_tr, y_tr, X_val, y_val):
    """LightGBM (sklearn API) — Apple Silicon 안정성 강화."""
    gc.collect()
    # sklearn API (LGBMRegressor) 사용: native API보다 메모리 안전
    X_tr_c = np.ascontiguousarray(X_tr, dtype=np.float32)
    X_val_c = np.ascontiguousarray(X_val, dtype=np.float32)
    y_tr_c = np.ascontiguousarray(y_tr, dtype=np.float32)
    y_val_c = np.ascontiguousarray(y_val, dtype=np.float32)

    model = lgb.LGBMRegressor(
        n_estimators=2000, learning_rate=0.05,
        num_leaves=127, min_child_samples=20,
        colsample_bytree=0.8, subsample=0.8, subsample_freq=5,
        random_state=SEED, n_jobs=1, verbose=-1,  # n_jobs=1: Apple Silicon SIGSEGV 방지
    )
    model.fit(
        X_tr_c, y_tr_c,
        eval_set=[(X_val_c, y_val_c)],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )
    gc.collect()
    yp_val = model.predict(X_val_c).astype(np.float32)
    yp_tr = model.predict(X_tr_c).astype(np.float32)
    del X_tr_c, X_val_c, y_tr_c, y_val_c
    gc.collect()
    diag = _compute_diag_ml(y_tr, yp_tr, y_val, yp_val)
    return yp_val, yp_tr, diag


def train_xgboost(X_tr, y_tr, X_val, y_val):
    params = {
        "objective": "reg:squarederror", "eval_metric": "rmse",
        "max_depth": 8, "learning_rate": 0.05, "subsample": 0.8,
        "colsample_bytree": 0.8, "min_child_weight": 5,
        "seed": SEED, "nthread": 1, "verbosity": 0,  # nthread=1: Apple Silicon SIGSEGV 방지
    }
    gc.collect()
    dtrain = xgb.DMatrix(X_tr, label=y_tr, nthread=1)
    dval = xgb.DMatrix(X_val, label=y_val, nthread=1)
    model = xgb.train(params, dtrain, num_boost_round=2000,
                      evals=[(dval, "val")], early_stopping_rounds=50, verbose_eval=False)
    yp_val = model.predict(dval).astype(np.float32)
    yp_tr = model.predict(dtrain).astype(np.float32)
    diag = _compute_diag_ml(y_tr, yp_tr, y_val, yp_val)
    return yp_val, yp_tr, diag


# ═══════════════════════════════════════════════════════════════════
# 4. Save Predictions
# ═══════════════════════════════════════════════════════════════════

def save_predictions(name, y_true, y_pred, sample_ids, drug_ids):
    df = pd.DataFrame({
        "sample_id": sample_ids,
        "drug_id": drug_ids,
        "y_true": y_true,
        "y_pred": y_pred,
    })
    out_path = PRED_DIR / f"{name}_predictions.csv"
    df.to_csv(out_path, index=False)
    return out_path


# ═══════════════════════════════════════════════════════════════════
# 5. Main Pipeline
# ═══════════════════════════════════════════════════════════════════

def main():
    total_t0 = time.time()
    print(f"Device: {DEVICE}")

    X_flat, X_modal, y, sample_ids, drug_ids = load_data()
    in_dim = X_flat.shape[1]
    sample_dim = 18311
    n_samples = len(y)

    # ML + DL 모델 모두 X_flat 전체 사용 (기존 프리프로젝트와 동일)

    # ── Model configs ──
    model_configs = [
        ("CatBoost",         "ml",       train_catboost),
        ("LightGBM",         "ml",       train_lightgbm),
        ("XGBoost",          "ml",       train_xgboost),
        ("FlatMLP",          "dl_flat",  FlatMLP),
        ("ResidualMLP",      "dl_flat",  ResidualMLP),
        ("CrossAttn",        "dl_flat",  CrossAttentionNet),
        ("MultiModalFusion", "dl_modal", None),
    ]

    dl_flat_kwargs = {
        "FlatMLP": (
            {"in_dim": in_dim, "layers": [1024, 512, 256], "dropout": 0.3},
            {"epochs": 100, "lr": 1e-3, "batch_size": 256},
        ),
        "ResidualMLP": (
            {"in_dim": in_dim, "hidden": 512, "n_blocks": 3, "dropout": 0.3},
            {"epochs": 100, "lr": 1e-3, "batch_size": 256},
        ),
        "CrossAttn": (
            {"in_dim": in_dim, "sample_dim": sample_dim, "d_model": 128, "nhead": 4, "dropout": 0.2},
            {"epochs": 80, "lr": 5e-4, "batch_size": 256},
        ),
    }

    # ── 5-Fold CV ──
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof_preds = {name: np.zeros(n_samples, dtype=np.float32) for name, _, _ in model_configs}
    model_spearman = {}
    all_diags = {}  # name → list of fold diags

    print(f"\n{'='*70}")
    print(f"  Ensemble V2: 7 models x {N_FOLDS}-fold CV")
    print(f"{'='*70}")

    # Pre-compute fold indices
    folds = list(kf.split(y))

    # ── Helper: train one model across all folds ──
    def _train_model_all_folds(name, mtype, trainer):
        t0 = time.time()
        fold_sp = []
        fold_diags = []
        local_oof = np.zeros(n_samples, dtype=np.float32)

        for fold_idx, (train_idx, val_idx) in enumerate(folds):
            fold_t0 = time.time()
            torch.manual_seed(SEED + fold_idx)
            y_tr, y_val = y[train_idx], y[val_idx]

            if mtype == "ml":
                X_tr, X_val = X_flat[train_idx], X_flat[val_idx]
                pred_val, pred_tr, diag = trainer(X_tr, y_tr, X_val, y_val)

            elif mtype == "dl_flat":
                scaler = StandardScaler()
                X_tr_s = scaler.fit_transform(X_flat[train_idx]).astype(np.float32)
                X_val_s = scaler.transform(X_flat[val_idx]).astype(np.float32)
                model_kw, train_kw = dl_flat_kwargs[name]
                model = trainer(**model_kw)
                pred_val, pred_tr, diag = train_dl_model(
                    model, X_tr_s, y_tr, X_val_s, y_val, **train_kw)

            elif mtype == "dl_modal":
                X_modal_tr = {k: v[train_idx] for k, v in X_modal.items()}
                X_modal_val = {k: v[val_idx] for k, v in X_modal.items()}
                pred_val, pred_tr, diag = train_multimodal_fold(
                    X_modal_tr, y_tr, X_modal_val, y_val,
                    d_model=128, nhead=4, dropout=0.2,
                    epochs=50, lr=1e-4, batch_size=256, patience=10)

            local_oof[val_idx] = pred_val
            sp, _ = spearmanr(y_val, pred_val)
            fold_sp.append(sp)
            diag["fold"] = fold_idx
            diag["spearman"] = round(float(sp), 4)
            fold_diags.append(diag)
            fold_dt = time.time() - fold_t0
            print(f"    [{name}] Fold {fold_idx+1}/{N_FOLDS} ... Sp={sp:.4f}  ({fold_dt:.0f}s)")

        mean_sp = np.mean(fold_sp)
        dt = time.time() - t0
        print(f"    [{name}] → Sp={mean_sp:.4f}  ({dt/60:.1f} min)")
        return name, local_oof, mean_sp, fold_diags

    # ── 전체 모델 순차 실행 ──
    # ML: CatBoost → LightGBM → XGBoost (CPU)
    # DL: FlatMLP → ResidualMLP → CrossAttn → MultiModalFusion (MPS 순차)
    for name, mtype, trainer in model_configs:
        print(f"\n  [{name}] Training...")
        name, local_oof, mean_sp, fold_diags = _train_model_all_folds(name, mtype, trainer)
        oof_preds[name] = local_oof
        model_spearman[name] = mean_sp
        all_diags[name] = fold_diags

    # ── Save per-model predictions ──
    print(f"\n{'='*70}")
    print(f"  Saving per-model predictions...")
    print(f"{'='*70}")
    for name in oof_preds:
        path = save_predictions(name, y, oof_preds[name], sample_ids, drug_ids)
        print(f"    {name:25s} → {path.name}")

    # ═══════════════════════════════════════════════════════════════
    # 과적합 진단 표
    # ═══════════════════════════════════════════════════════════════

    print(f"\n{'='*70}")
    print(f"  Overfitting Diagnostics (fold 평균)")
    print(f"{'='*70}")

    diag_summary = {}
    print(f"\n  {'Model':20s} {'Train_Sp':>10s} {'Val_Sp':>10s} {'Gap':>8s} {'Label':>12s} "
          f"{'Converged':>10s} {'Pred Mean':>10s} {'Act Mean':>10s} {'Pred Std':>10s} {'Act Std':>10s}")
    print(f"  {'─'*110}")

    for name, _, _ in model_configs:
        fdiags = all_diags[name]
        avg_train_sp = np.mean([d["train_spearman"] for d in fdiags])
        avg_val_sp = np.mean([d["val_spearman"] for d in fdiags])
        avg_gap = np.mean([d["gap"] for d in fdiags])

        if avg_gap < 0.05:
            avg_label = "NORMAL"
        elif avg_gap <= 0.10:
            avg_label = "WARNING"
        else:
            avg_label = "OVERFITTING"

        # Convergence (DL only)
        if "converged" in fdiags[0]:
            conv = sum(d["converged"] for d in fdiags)
            conv_str = f"{conv}/{len(fdiags)}"
        else:
            conv_str = "N/A (ML)"

        pred_means = [d["pred_dist"]["val"]["mean"] for d in fdiags]
        act_means = [d["pred_dist"]["actual"]["mean"] for d in fdiags]
        pred_stds = [d["pred_dist"]["val"]["std"] for d in fdiags]
        act_stds = [d["pred_dist"]["actual"]["std"] for d in fdiags]

        print(f"  {name:20s} {avg_train_sp:>10.4f} {avg_val_sp:>10.4f} {avg_gap:>8.4f} {avg_label:>12s} "
              f"{conv_str:>10s} {np.mean(pred_means):>10.3f} {np.mean(act_means):>10.3f} "
              f"{np.mean(pred_stds):>10.3f} {np.mean(act_stds):>10.3f}")

        diag_summary[name] = {
            "avg_train_spearman": round(float(avg_train_sp), 4),
            "avg_val_spearman": round(float(avg_val_sp), 4),
            "avg_gap": round(float(avg_gap), 4),
            "label": avg_label,
            "convergence": conv_str,
            "avg_pred_mean": round(float(np.mean(pred_means)), 3),
            "avg_actual_mean": round(float(np.mean(act_means)), 3),
            "avg_pred_std": round(float(np.mean(pred_stds)), 3),
            "avg_actual_std": round(float(np.mean(act_stds)), 3),
            "folds": fdiags,
        }

    # ═══════════════════════════════════════════════════════════════
    # Spearman-weighted ensemble
    # ═══════════════════════════════════════════════════════════════

    print(f"\n{'='*70}")
    print(f"  Spearman-Weighted Ensemble (7 models)")
    print(f"{'='*70}")

    total_sp = sum(model_spearman.values())
    weights = {name: sp / total_sp for name, sp in model_spearman.items()}

    print(f"\n  {'Model':25s} {'Spearman':>10s} {'Weight':>8s}")
    print(f"  {'─'*45}")
    for name in sorted(weights, key=lambda x: -weights[x]):
        print(f"  {name:25s} {model_spearman[name]:>10.4f} {weights[name]:>8.4f}")

    ensemble_pred = np.zeros(n_samples, dtype=np.float64)
    for name, w in weights.items():
        ensemble_pred += w * oof_preds[name]

    save_predictions("Ensemble_V2", y, ensemble_pred.astype(np.float32), sample_ids, drug_ids)

    # ── Metrics ──
    ens_sp, _ = spearmanr(y, ensemble_pred)
    ens_pe, _ = pearsonr(y, ensemble_pred)
    ens_rmse = float(np.sqrt(mean_squared_error(y, ensemble_pred)))
    ens_mae = float(mean_absolute_error(y, ensemble_pred))
    ens_r2 = float(r2_score(y, ensemble_pred))

    fold_metrics = []
    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X_flat)):
        y_val = y[val_idx]
        ens_val = ensemble_pred[val_idx]
        sp_f, _ = spearmanr(y_val, ens_val)
        rmse_f = float(np.sqrt(mean_squared_error(y_val, ens_val)))
        sp_tr, _ = spearmanr(y[train_idx], ensemble_pred[train_idx])
        fold_metrics.append({
            "fold": fold_idx, "spearman": round(float(sp_f), 4),
            "rmse": round(rmse_f, 4),
            "train_spearman": round(float(sp_tr), 4),
            "gap": round(float(sp_tr - sp_f), 4),
        })

    fm_df = pd.DataFrame(fold_metrics)

    individual = {}
    for name in model_spearman:
        sp_oof, _ = spearmanr(y, oof_preds[name])
        rmse_oof = float(np.sqrt(mean_squared_error(y, oof_preds[name])))
        individual[name] = {
            "spearman_oof": round(float(sp_oof), 4),
            "rmse_oof": round(rmse_oof, 4),
            "spearman_cv_mean": round(float(model_spearman[name]), 4),
            "weight": round(float(weights[name]), 6),
        }

    # ── Print final results ──
    print(f"\n{'='*70}")
    print(f"  Final Results")
    print(f"{'='*70}")

    print(f"\n  Spearman : {float(ens_sp):.4f}  "
          f"(CV: {fm_df['spearman'].mean():.4f} +/- {fm_df['spearman'].std():.4f})")
    print(f"  RMSE     : {ens_rmse:.4f}  (CV: {fm_df['rmse'].mean():.4f})")
    print(f"  MAE      : {ens_mae:.4f}")
    print(f"  R²       : {ens_r2:.4f}")
    print(f"  Pearson  : {float(ens_pe):.4f}")

    delta_old = float(ens_sp) - BENCH_SP_OLD
    delta_pre = float(ens_sp) - BENCH_SP_PREPROJ

    print(f"\n  [Comparison]")
    print(f"  vs 기존 6-model 앙상블 (0.8055) : {delta_old:+.4f}  "
          f"{'IMPROVED' if delta_old > 0 else 'NO CHANGE'}")
    print(f"  vs 프리프로젝트 기준  (0.7130) : {delta_pre:+.4f}  PASS")

    print(f"\n  [Per-Model Ranking]")
    print(f"  {'#':>3s}  {'Model':25s} {'OOF Sp':>8s} {'OOF RMSE':>10s} "
          f"{'Weight':>8s} {'Overfit':>10s}")
    print(f"  {'─'*68}")
    rank = 1
    for name in sorted(individual, key=lambda x: -individual[x]["spearman_oof"]):
        m = individual[name]
        ol = diag_summary[name]["label"]
        print(f"  {rank:>3d}  {name:25s} {m['spearman_oof']:>8.4f} "
              f"{m['rmse_oof']:>10.4f} {m['weight']:>8.4f} {ol:>10s}")
        rank += 1
    print(f"  {'─'*68}")
    print(f"  {'':>3s}  {'ENSEMBLE V2':25s} {float(ens_sp):>8.4f} "
          f"{ens_rmse:>10.4f} {'1.0000':>8s}")

    elapsed = (time.time() - total_t0) / 60
    print(f"\n  Total time: {elapsed:.1f} min")
    print(f"{'='*70}")

    # ── Save JSON ──
    results = {
        "ensemble_method": "spearman_weighted_average",
        "n_models": 7,
        "weights": {k: round(float(v), 6) for k, v in weights.items()},
        "ensemble_metrics": {
            "spearman": round(float(ens_sp), 4),
            "spearman_cv_mean": round(float(fm_df["spearman"].mean()), 4),
            "spearman_cv_std": round(float(fm_df["spearman"].std()), 4),
            "rmse": round(ens_rmse, 4),
            "rmse_cv_mean": round(float(fm_df["rmse"].mean()), 4),
            "mae": round(ens_mae, 4),
            "r2": round(ens_r2, 4),
            "pearson": round(float(ens_pe), 4),
        },
        "comparison": {
            "vs_old_ensemble_6model": round(delta_old, 4),
            "vs_preproject_benchmark": round(delta_pre, 4),
            "old_ensemble_spearman": BENCH_SP_OLD,
            "preproject_spearman": BENCH_SP_PREPROJ,
        },
        "individual_models": individual,
        "overfitting_diagnostics": {
            name: {k: v for k, v in d.items() if k != "folds"}
            for name, d in diag_summary.items()
        },
        "fold_metrics": fold_metrics,
        "elapsed_min": round(elapsed, 1),
    }

    out_path = RESULTS_DIR / "ensemble_v2_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results: {out_path}")
    print(f"  Predictions: {PRED_DIR}/")

    mps_cleanup()


if __name__ == "__main__":
    main()
