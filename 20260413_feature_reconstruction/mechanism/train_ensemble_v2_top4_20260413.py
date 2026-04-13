#!/usr/bin/env python3
"""
Ensemble v2 Top4: 3 ensemble methods comparison
══════════════════════════════════════════════════
OOF predictions from 4 models → 3 ensemble strategies

Models (fixed order):
  1. Stacking_Ridge  (v2 Sp = 0.5182)
  2. CatBoost        (v2 Sp = 0.5140)
  3. RandomForest    (v2 Sp = 0.5064)
  4. XGBoost         (v2 Sp = 0.4908)

Ensemble methods:
  1. Equal weight:          [0.25, 0.25, 0.25, 0.25]
  2. Spearman-proportional: softmax(sp / T), T=0.02
  3. Grid search:           0.1~0.7 step 0.1, sum=1.0, max OOF Spearman

Data: final_features(2167) + v1(5) + v2(10) merge
CV: GroupKFold(n_splits=5, groups=canonical_drug_id)
Results: results/ensemble_v2_results_20260413/
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from itertools import product
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr, pearsonr
from scipy.special import softmax

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MECH_DIR = Path(__file__).resolve().parent

FINAL_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"
V1_PATH = MECH_DIR / "mechanism_features_v1_20260413.parquet"
V2_PATH = MECH_DIR / "mechanism_features_v2_20260413.parquet"

OOF_DIR = PROJECT_ROOT / "results" / "ml_mechanism_v2_results_20260413"
OOF_PATH = OOF_DIR / "oof_predictions.parquet"
OUTPUT_DIR = PROJECT_ROOT / "results" / "ensemble_v2_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_FOLDS = 5
SEED = 42

ID_COLS = ["sample_id", "canonical_drug_id"]
LABEL_PREFIX = "label_"

V1_FEATURE_COLS = [
    "target_overlap_count",
    "target_overlap_ratio",
    "target_disease_score_mean",
    "pathway_match_score",
    "lincs_mean_score",
]
V2_FEATURE_COLS = [
    "target_expr_weighted_score",
    "target_disease_weighted_sum",
    "target_disease_weighted_mean",
    "pathway_similarity_score",
    "pathway_disease_overlap_ratio",
    "lincs_similarity_score",
    "lincs_reversal_score",
    "target_x_pathway",
    "target_x_lincs",
    "disease_x_pathway",
]

MODEL_ORDER = ["Stacking_Ridge", "CatBoost", "RandomForest", "XGBoost"]
PRED_COLS = [f"pred_{m}" for m in MODEL_ORDER]

MODEL_SPEARMAN = {
    "Stacking_Ridge": 0.5182,
    "CatBoost": 0.5140,
    "RandomForest": 0.5064,
    "XGBoost": 0.4908,
}
TEMPERATURE = 0.02

GRID_RANGE = [round(w / 10, 1) for w in range(1, 8)]  # 0.1 ~ 0.7


# ════════════════════════════════════════════════════════════
#  Data Loading
# ════════════════════════════════════════════════════════════
def load_data():
    """Load final_features + v1 + v2 merge."""
    print("=" * 70)
    print("Loading data...")
    t0 = time.time()

    df = pd.read_parquet(FINAL_PATH)
    n_final = len(df)

    df_v1 = pd.read_parquet(V1_PATH)
    df = df.merge(df_v1, on="canonical_drug_id", how="left")

    df_v2 = pd.read_parquet(V2_PATH)
    df = df.merge(df_v2, on=["sample_id", "canonical_drug_id"], how="left")

    for col in V1_FEATURE_COLS + V2_FEATURE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    label_cols = [c for c in df.columns if c.startswith(LABEL_PREFIX)]
    feat_cols = [c for c in df.columns if c not in ID_COLS + label_cols]

    X = df[feat_cols].fillna(0.0).values.astype(np.float32)
    y_reg = df["label_regression"].values.astype(np.float64)
    drug_ids = df["canonical_drug_id"].values
    sample_ids = df["sample_id"].values
    df_ids = df[ID_COLS].copy()

    dt = time.time() - t0
    print(f"  Rows: {n_final}, Features: {len(feat_cols)}")
    print(f"  ({dt:.1f}s)")
    print("=" * 70)
    return X, y_reg, feat_cols, drug_ids, sample_ids, df_ids


# ════════════════════════════════════════════════════════════
#  Model Definitions (동일 하이퍼파라미터)
# ════════════════════════════════════════════════════════════
def _xgboost(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    import xgboost as xgb
    dtrain = xgb.DMatrix(X_tr, label=y_tr, feature_names=feat_names)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feat_names)
    params = {
        "objective": "reg:squarederror", "eval_metric": "rmse",
        "max_depth": 7, "learning_rate": 0.05,
        "colsample_bytree": 0.7, "subsample": 0.8,
        "reg_alpha": 0.1, "reg_lambda": 1.0, "min_child_weight": 5,
        "tree_method": "hist", "seed": SEED + fold_idx, "nthread": -1,
        "verbosity": 0,
    }
    model = xgb.train(params, dtrain, num_boost_round=1500,
                      evals=[(dval, "val")], early_stopping_rounds=50,
                      verbose_eval=False)
    return model.predict(dval)


def _catboost(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from catboost import CatBoostRegressor
    model = CatBoostRegressor(
        iterations=1500, learning_rate=0.05, depth=7,
        l2_leaf_reg=3.0, rsm=0.7, subsample=0.8,
        early_stopping_rounds=50, random_seed=SEED + fold_idx,
        verbose=0, thread_count=-1,
    )
    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
    return model.predict(X_val)


def _random_forest(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(
        n_estimators=500, max_depth=None, max_features="sqrt",
        min_samples_leaf=5, n_jobs=-1, random_state=SEED + fold_idx,
    )
    model.fit(X_tr, y_tr)
    return model.predict(X_val)


def _stacking_ridge(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestRegressor, StackingRegressor
    from sklearn.linear_model import Ridge
    import xgboost as xgb

    base_lgb = lgb.LGBMRegressor(
        n_estimators=500, learning_rate=0.05, num_leaves=63, max_depth=7,
        colsample_bytree=0.7, subsample=0.8, reg_alpha=0.1, reg_lambda=1.0,
        n_jobs=-1, verbose=-1, random_state=SEED + fold_idx,
    )
    base_rf = RandomForestRegressor(
        n_estimators=300, max_features="sqrt", min_samples_leaf=5,
        n_jobs=-1, random_state=SEED + fold_idx,
    )
    base_xgb = xgb.XGBRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=7,
        colsample_bytree=0.7, subsample=0.8, reg_alpha=0.1, reg_lambda=1.0,
        tree_method="hist", n_jobs=-1, verbosity=0, random_state=SEED + fold_idx,
    )

    model = StackingRegressor(
        estimators=[("lgb", base_lgb), ("xgb", base_xgb), ("rf", base_rf)],
        final_estimator=Ridge(alpha=1.0),
        cv=3, n_jobs=1, passthrough=False,
    )
    model.fit(X_tr, y_tr)
    return model.predict(X_val)


MODEL_FNS = {
    "Stacking_Ridge": _stacking_ridge,
    "CatBoost":       _catboost,
    "RandomForest":   _random_forest,
    "XGBoost":        _xgboost,
}


# ════════════════════════════════════════════════════════════
#  Phase 1: OOF Prediction 생성 (캐시 있으면 로드)
# ═══════════════════════════════════════════════════════���════
def generate_oof_predictions(X, y_reg, feat_names, drug_ids, sample_ids, df_ids):
    """Run 4 models × 5-fold GroupKFold CV, collect OOF predictions."""
    print("\n" + "=" * 70)
    print("  Phase 1: OOF Prediction 생성")
    print("=" * 70)

    gkf = GroupKFold(n_splits=N_FOLDS)
    n = len(X)
    oof_preds = {m: np.zeros(n, dtype=np.float64) for m in MODEL_ORDER}
    fold_indices = np.full(n, -1, dtype=np.int32)

    splits = list(gkf.split(X, y_reg, groups=drug_ids))

    for model_name in MODEL_ORDER:
        model_fn = MODEL_FNS[model_name]
        t0 = time.time()
        print(f"\n  [{model_name}] 5-fold OOF 생성 중...")

        for fold_idx, (train_idx, val_idx) in enumerate(splits):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y_reg[train_idx], y_reg[val_idx]

            y_pred_val = model_fn(X_tr, y_tr, X_val, y_val, fold_idx, feat_names)
            oof_preds[model_name][val_idx] = y_pred_val
            fold_indices[val_idx] = fold_idx

        sp, _ = spearmanr(y_reg, oof_preds[model_name])
        rmse = np.sqrt(mean_squared_error(y_reg, oof_preds[model_name]))
        dt = time.time() - t0
        print(f"    OOF Spearman={sp:.4f}, RMSE={rmse:.4f}  ({dt:.1f}s)")

    # Build DataFrame
    df_oof = df_ids.copy()
    df_oof["y_true"] = y_reg
    df_oof["fold"] = fold_indices
    for m in MODEL_ORDER:
        df_oof[f"pred_{m}"] = oof_preds[m]

    # 캐시 저장
    df_oof.to_parquet(OOF_PATH, index=False)
    print(f"\n  OOF 저장: {OOF_PATH}")
    print(f"  크기: {OOF_PATH.stat().st_size / 1024:.0f} KB")

    return df_oof


def load_oof_predictions():
    """Load cached OOF predictions."""
    print("\n" + "=" * 70)
    print("  Phase 1: OOF Prediction 로드 (캐시)")
    print("=" * 70)

    df_oof = pd.read_parquet(OOF_PATH)
    print(f"  {OOF_PATH.name}: {df_oof.shape}")
    return df_oof


# ═══════════════════════════════��════════════════════════════
#  Phase 2: 정렬 검증
# ═════════════════════════════════════════════════════��══════
def verify_alignment(df_oof):
    """Verify row count, ID alignment, fold indices."""
    print("\n" + "=" * 70)
    print("  Phase 2: 정렬 검증")
    print("=" * 70)

    errors = []

    # row 수
    n_rows = len(df_oof)
    print(f"  Row 수: {n_rows}")
    if n_rows != 7730:
        errors.append(f"Row 수 불일치: {n_rows} (expected 7730)")

    # pred 컬럼 존재
    for col in PRED_COLS:
        if col not in df_oof.columns:
            errors.append(f"컬럼 누락: {col}")
    print(f"  Pred 컬럼: {[c for c in PRED_COLS if c in df_oof.columns]}")

    # sample_id, canonical_drug_id null
    for col in ID_COLS:
        n_null = df_oof[col].isna().sum()
        if n_null > 0:
            errors.append(f"{col} null: {n_null}")
    print(f"  ID null: sample_id={df_oof['sample_id'].isna().sum()}, "
          f"drug_id={df_oof['canonical_drug_id'].isna().sum()}")

    # pred null / inf
    for col in PRED_COLS:
        if col not in df_oof.columns:
            continue
        n_null = df_oof[col].isna().sum()
        n_inf = np.isinf(df_oof[col]).sum()
        if n_null > 0:
            errors.append(f"{col} null: {n_null}")
        if n_inf > 0:
            errors.append(f"{col} inf: {n_inf}")
    print(f"  Pred null: {sum(df_oof[c].isna().sum() for c in PRED_COLS if c in df_oof.columns)}")

    # fold 인덱스
    folds = sorted(df_oof["fold"].unique())
    print(f"  Fold indices: {folds}")
    if folds != list(range(N_FOLDS)):
        errors.append(f"Fold 불일치: {folds}")

    # fold별 row 수
    fold_counts = df_oof["fold"].value_counts().sort_index()
    for f, cnt in fold_counts.items():
        print(f"    Fold {f}: {cnt} rows")

    # 모델 간 예측값 상관
    print(f"\n  모델 간 OOF 상관:")
    for i, m1 in enumerate(MODEL_ORDER):
        for m2 in MODEL_ORDER[i+1:]:
            c1, c2 = f"pred_{m1}", f"pred_{m2}"
            if c1 in df_oof.columns and c2 in df_oof.columns:
                corr, _ = pearsonr(df_oof[c1], df_oof[c2])
                print(f"    {m1} vs {m2}: Pearson={corr:.4f}")

    if errors:
        print(f"\n  *** 검증 실패: {errors}")
        raise ValueError(f"정렬 검증 실패: {errors}")

    print(f"\n  검증 통과 ✓")
    return True


# ═════════════════════════════════════════════════════��══════
#  Phase 3: Ensemble Methods
# ════════════════════════════════════════════════��═══════════
def compute_metrics(y_true, y_pred):
    sp, _ = spearmanr(y_true, y_pred)
    pe, _ = pearsonr(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return {"spearman": sp, "pearson": pe, "rmse": rmse}


def compute_fold_spearman(df_oof, y_pred):
    """Compute per-fold Spearman."""
    fold_sp = {}
    for fold_idx in range(N_FOLDS):
        mask = df_oof["fold"] == fold_idx
        sp, _ = spearmanr(df_oof.loc[mask, "y_true"], y_pred[mask])
        fold_sp[fold_idx] = sp
    return fold_sp


def ensemble_equal(pred_matrix):
    """방식 1: Equal weight average."""
    weights = np.array([0.25, 0.25, 0.25, 0.25])
    return pred_matrix @ weights, weights


def ensemble_spearman_weighted(pred_matrix, temperature=TEMPERATURE):
    """방식 2: Spearman-proportional softmax weight."""
    sp_values = np.array([MODEL_SPEARMAN[m] for m in MODEL_ORDER])
    weights = softmax(sp_values / temperature)
    return pred_matrix @ weights, weights


def ensemble_grid_search(pred_matrix, y_true):
    """방식 3: Grid search (0.1~0.7, step 0.1, sum=1.0)."""
    best_sp = -1.0
    best_weights = None
    n_checked = 0

    for w in product(GRID_RANGE, repeat=4):
        if abs(sum(w) - 1.0) > 1e-8:
            continue
        n_checked += 1
        pred = pred_matrix @ np.array(w)
        sp, _ = spearmanr(y_true, pred)
        if sp > best_sp:
            best_sp = sp
            best_weights = np.array(w)

    print(f"    Grid search: {n_checked} 조합 탐색 완료")
    return pred_matrix @ best_weights, best_weights


# ════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════��═════════════
def main():
    total_start = time.time()

    # ── Data ──
    X, y_reg, feat_names, drug_ids, sample_ids, df_ids = load_data()

    # ── Phase 1: OOF Predictions ──
    if OOF_PATH.exists():
        df_oof = load_oof_predictions()
    else:
        df_oof = generate_oof_predictions(
            X, y_reg, feat_names, drug_ids, sample_ids, df_ids
        )

    # ── Phase 2: 정렬 검증 ──
    verify_alignment(df_oof)

    # ── 개별 모델 OOF 성능 확인 ──
    print("\n" + "=" * 70)
    print("  개별 모델 OOF 성능")
    print("=" * 70)
    y_true = df_oof["y_true"].values
    pred_matrix = df_oof[PRED_COLS].values  # (N, 4)

    print(f"  {'Model':<18} {'Spearman':>9} {'Pearson':>9} {'RMSE':>8}")
    print("  " + "-" * 48)
    for i, m in enumerate(MODEL_ORDER):
        met = compute_metrics(y_true, pred_matrix[:, i])
        print(f"  {m:<18} {met['spearman']:>9.4f} {met['pearson']:>9.4f} {met['rmse']:>8.4f}")

    # ── Phase 3: Ensemble ──
    print("\n" + "=" * 70)
    print("  Phase 3: Ensemble 비교")
    print("=" * 70)

    results = []

    # 방식 1: Equal weight
    print(f"\n  [방식 1] Equal weight")
    pred_eq, w_eq = ensemble_equal(pred_matrix)
    met_eq = compute_metrics(y_true, pred_eq)
    fold_sp_eq = compute_fold_spearman(df_oof, pred_eq)
    print(f"    Weights: {'/'.join(f'{w:.2f}' for w in w_eq)}")
    print(f"    Spearman={met_eq['spearman']:.4f}, RMSE={met_eq['rmse']:.4f}")
    results.append({
        "method": "Equal",
        "weights": w_eq.tolist(),
        **met_eq,
        "fold_spearman": fold_sp_eq,
    })

    # 방식 2: Spearman-proportional
    print(f"\n  [방식 2] Spearman-proportional (T={TEMPERATURE})")
    pred_sp, w_sp = ensemble_spearman_weighted(pred_matrix)
    met_sp = compute_metrics(y_true, pred_sp)
    fold_sp_sp = compute_fold_spearman(df_oof, pred_sp)
    print(f"    Input Sp: {[MODEL_SPEARMAN[m] for m in MODEL_ORDER]}")
    print(f"    Weights:  {'/'.join(f'{w:.4f}' for w in w_sp)}")
    print(f"    Spearman={met_sp['spearman']:.4f}, RMSE={met_sp['rmse']:.4f}")
    results.append({
        "method": "Spearman_proportional",
        "weights": w_sp.tolist(),
        "temperature": TEMPERATURE,
        **met_sp,
        "fold_spearman": fold_sp_sp,
    })

    # 방식 3: Grid search
    print(f"\n  [방식 3] Grid search (range={GRID_RANGE[0]}~{GRID_RANGE[-1]}, step=0.1)")
    t0 = time.time()
    pred_gs, w_gs = ensemble_grid_search(pred_matrix, y_true)
    met_gs = compute_metrics(y_true, pred_gs)
    fold_sp_gs = compute_fold_spearman(df_oof, pred_gs)
    dt = time.time() - t0
    print(f"    Weights:  {'/'.join(f'{w:.1f}' for w in w_gs)}")
    print(f"    Spearman={met_gs['spearman']:.4f}, RMSE={met_gs['rmse']:.4f}  ({dt:.1f}s)")
    results.append({
        "method": "Grid_search",
        "weights": w_gs.tolist(),
        **met_gs,
        "fold_spearman": fold_sp_gs,
    })

    # ── Summary Table ──
    best_single = max(MODEL_SPEARMAN.values())
    target_low, target_high = 0.525, 0.535

    print("\n" + "=" * 90)
    print(f"  ENSEMBLE v2 TOP4 SUMMARY")
    print("=" * 90)
    print(f"  {'방식':<24} {'Spearman':>9} {'RMSE':>8} {'최적 Weight (St/Cb/RF/XG)':>32}")
    print("  " + "-" * 76)
    for r in results:
        w_str = "/".join(f"{w:.2f}" for w in r["weights"])
        delta = r["spearman"] - best_single
        flag = " ↑" if r["spearman"] >= target_low else ""
        print(f"  {r['method']:<24} {r['spearman']:>8.4f}{flag} {r['rmse']:>8.4f} "
              f" {w_str:>30}")
    print("  " + "-" * 76)
    print(f"  단일 최고 (Stacking_Ridge): {best_single:.4f}")
    print(f"  목표 범위: {target_low} ~ {target_high}")
    print("=" * 90)

    # ── Fold별 Spearman 비교 ──
    print(f"\n  Fold별 Spearman 비교:")
    print(f"  {'Fold':>4}  {'Equal':>8}  {'Sp비례':>8}  {'Grid':>8}  {'Best단일':>8}")
    print("  " + "-" * 42)
    for fold_idx in range(N_FOLDS):
        # best single model per fold
        best_fold_sp = max(
            compute_metrics(
                df_oof.loc[df_oof["fold"] == fold_idx, "y_true"].values,
                df_oof.loc[df_oof["fold"] == fold_idx, f"pred_{m}"].values,
            )["spearman"]
            for m in MODEL_ORDER
        )
        print(f"  {fold_idx:>4}  "
              f"{results[0]['fold_spearman'][fold_idx]:>8.4f}  "
              f"{results[1]['fold_spearman'][fold_idx]:>8.4f}  "
              f"{results[2]['fold_spearman'][fold_idx]:>8.4f}  "
              f"{best_fold_sp:>8.4f}")

    total_elapsed = time.time() - total_start
    print(f"\n  Total: {total_elapsed/60:.1f} min")

    # ── Save ──
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    results_path = OUTPUT_DIR / "ensemble_v2_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=convert)
    print(f"  Results saved to {results_path}")


if __name__ == "__main__":
    main()
