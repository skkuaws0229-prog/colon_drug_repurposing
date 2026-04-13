#!/usr/bin/env python3
"""
ML Top4 + Mechanism v1 + v2 Features Training with GroupKFold CV
Data: final_features(2167) + v1(5) + v2(10) merge
CV: GroupKFold(n_splits=5, groups=canonical_drug_id)
Models: Stacking_Ridge, CatBoost, RandomForest, XGBoost
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import spearmanr, pearsonr

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MECH_DIR = Path(__file__).resolve().parent

FINAL_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"
V1_PATH = MECH_DIR / "mechanism_features_v1_20260413.parquet"
V2_PATH = MECH_DIR / "mechanism_features_v2_20260413.parquet"

N_FOLDS = 5
SEED = 42
OUTPUT_DIR = PROJECT_ROOT / "results" / "ml_mechanism_v2_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BENCH_SPEARMAN = 0.713
BENCH_RMSE = 1.385

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


def load_data():
    """Load final_features + v1 (295 drugs) + v2 (7730 rows) merge."""
    print("=" * 70)
    print("Loading data...")
    t0 = time.time()

    df = pd.read_parquet(FINAL_PATH)
    n_final = len(df)
    n_final_feat = len([c for c in df.columns if c not in ID_COLS
                        and not c.startswith(LABEL_PREFIX)])

    # v1: per-drug (295 rows), merge on canonical_drug_id
    df_v1 = pd.read_parquet(V1_PATH)
    df = df.merge(df_v1, on="canonical_drug_id", how="left")

    # v2: per-sample (7730 rows), merge on (sample_id, canonical_drug_id)
    df_v2 = pd.read_parquet(V2_PATH)
    df = df.merge(df_v2, on=["sample_id", "canonical_drug_id"], how="left")

    n_merged = len(df)

    # null 채우기
    for col in V1_FEATURE_COLS + V2_FEATURE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    label_cols = [c for c in df.columns if c.startswith(LABEL_PREFIX)]
    feat_cols = [c for c in df.columns if c not in ID_COLS + label_cols]

    X = df[feat_cols].fillna(0.0).values.astype(np.float32)
    y_reg = df["label_regression"].values.astype(np.float64)
    y_bin = df["label_binary"].values.astype(np.int32)
    drug_ids = df["canonical_drug_id"].values

    n_v1 = len([c for c in V1_FEATURE_COLS if c in feat_cols])
    n_v2 = len([c for c in V2_FEATURE_COLS if c in feat_cols])
    n_total = len(feat_cols)
    n_expected = 2167 + 5 + 10

    dt = time.time() - t0
    print(f"  final_features: {n_final} rows, {n_final_feat} features")
    print(f"  v1 mechanism:   {len(df_v1)} drugs × {n_v1} features")
    print(f"  v2 mechanism:   {len(df_v2)} rows × {n_v2} features")
    print(f"  Merged: {n_merged} rows (유지: {'OK' if n_final == n_merged else 'FAIL'})")
    print(f"  Total features: {n_total} (final {n_final_feat} + v1 {n_v1} + v2 {n_v2})")
    if n_total != n_expected:
        print(f"  ※ 기대값 {n_expected}과 차이: {n_total - n_expected:+d}"
              f" (final features가 {n_final_feat}개, 기준 2167과 {n_final_feat - 2167:+d} 차이)")
    print(f"  y_reg: mean={y_reg.mean():.3f}, std={y_reg.std():.3f}")
    print(f"  y_bin: {y_bin.sum()}/{len(y_bin)} positive ({y_bin.mean()*100:.1f}%)")
    print(f"  Unique drugs: {len(np.unique(drug_ids))}")
    print(f"  CV: GroupKFold(n_splits={N_FOLDS})")
    print(f"  ({dt:.1f}s)")
    print("=" * 70)
    return X, y_reg, y_bin, feat_cols, drug_ids


def compute_metrics(y_true, y_pred, y_train_true=None, y_train_pred=None):
    sp, _ = spearmanr(y_true, y_pred)
    pe, _ = pearsonr(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    m = {"spearman": sp, "pearson": pe, "rmse": rmse, "r2": r2}
    if y_train_true is not None and y_train_pred is not None:
        tr_sp, _ = spearmanr(y_train_true, y_train_pred)
        tr_rmse = np.sqrt(mean_squared_error(y_train_true, y_train_pred))
        m["train_spearman"] = tr_sp
        m["train_rmse"] = tr_rmse
        m["gap_spearman"] = tr_sp - sp
        m["gap_rmse"] = rmse - tr_rmse
    return m


def run_cv(model_name, model_fn, X, y_reg, y_bin, feature_names, drug_ids):
    print(f"\n{'─'*60}")
    print(f"  [{model_name}] Training with 5-fold GroupKFold CV...")
    print(f"{'─'*60}")

    gkf = GroupKFold(n_splits=N_FOLDS)
    fold_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y_reg, groups=drug_ids)):
        t0 = time.time()
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y_reg[train_idx], y_reg[val_idx]

        model, y_pred_val, y_pred_tr = model_fn(
            X_tr, y_tr, X_val, y_val, fold_idx, feature_names
        )

        m = compute_metrics(y_val, y_pred_val, y_tr, y_pred_tr)
        m["fold"] = fold_idx
        fold_metrics.append(m)

        dt = time.time() - t0
        print(f"  Fold {fold_idx}: Spearman={m['spearman']:.4f}  RMSE={m['rmse']:.4f}  "
              f"R2={m['r2']:.4f}  Gap(Sp)={m['gap_spearman']:.4f}  ({dt:.1f}s)")

    df = pd.DataFrame(fold_metrics)
    summary = {
        "model": model_name,
        "spearman_mean": df["spearman"].mean(),
        "spearman_std": df["spearman"].std(),
        "rmse_mean": df["rmse"].mean(),
        "rmse_std": df["rmse"].std(),
        "pearson_mean": df["pearson"].mean(),
        "r2_mean": df["r2"].mean(),
        "r2_std": df["r2"].std(),
        "train_spearman_mean": df["train_spearman"].mean(),
        "gap_spearman_mean": df["gap_spearman"].mean(),
        "gap_rmse_mean": df["gap_rmse"].mean(),
        "folds": fold_metrics,
    }

    beat_sp = "PASS" if summary["spearman_mean"] >= BENCH_SPEARMAN else "FAIL"
    beat_rm = "PASS" if summary["rmse_mean"] <= BENCH_RMSE else "FAIL"
    print(f"\n  >>> {model_name} SUMMARY:")
    print(f"      Spearman: {summary['spearman_mean']:.4f} +/- {summary['spearman_std']:.4f}  [{beat_sp} vs {BENCH_SPEARMAN}]")
    print(f"      RMSE:     {summary['rmse_mean']:.4f} +/- {summary['rmse_std']:.4f}  [{beat_rm} vs {BENCH_RMSE}]")
    print(f"      Pearson:  {summary['pearson_mean']:.4f}")
    print(f"      R2:       {summary['r2_mean']:.4f} +/- {summary['r2_std']:.4f}")
    print(f"      Train Sp: {summary['train_spearman_mean']:.4f}  Gap: {summary['gap_spearman_mean']:.4f}")

    return summary


# ── Model Definitions (hyperparams unchanged) ──

def xgboost_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
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
    return model, model.predict(dval), model.predict(dtrain)


def catboost_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from catboost import CatBoostRegressor
    model = CatBoostRegressor(
        iterations=1500, learning_rate=0.05, depth=7,
        l2_leaf_reg=3.0, rsm=0.7, subsample=0.8,
        early_stopping_rounds=50, random_seed=SEED + fold_idx,
        verbose=0, thread_count=-1,
    )
    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
    return model, model.predict(X_val), model.predict(X_tr)


def rf_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(
        n_estimators=500, max_depth=None, max_features="sqrt",
        min_samples_leaf=5, n_jobs=-1, random_state=SEED + fold_idx,
    )
    model.fit(X_tr, y_tr)
    return model, model.predict(X_val), model.predict(X_tr)


def stacking_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
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
    return model, model.predict(X_val), model.predict(X_tr)


# ── Main ──

def main():
    X, y_reg, y_bin, feat_names, drug_ids = load_data()

    all_results = []
    models_config = [
        ("1_XGBoost",        xgboost_model),
        ("2_CatBoost",       catboost_model),
        ("3_RandomForest",   rf_model),
        ("4_Stacking_Ridge", stacking_model),
    ]

    total_start = time.time()

    for name, fn in models_config:
        t0 = time.time()
        result = run_cv(name, fn, X, y_reg, y_bin, feat_names, drug_ids)
        result["elapsed_sec"] = time.time() - t0
        all_results.append(result)

    total_elapsed = time.time() - total_start

    # ── Summary Table ──
    print("\n" + "=" * 90)
    print(f"  ML+MECHANISM v2 TOP4 SUMMARY (GroupKFold, Total: {total_elapsed/60:.1f} min)")
    print("=" * 90)
    print(f"{'Model':<22} {'Spearman':>10} {'  std':>6} {'RMSE':>8} {'  std':>6} "
          f"{'Pearson':>8} {'R2':>8} {'Gap(Sp)':>8} {'Time':>6}")
    print("-" * 90)

    for r in all_results:
        sp_flag = " *" if r["spearman_mean"] >= BENCH_SPEARMAN else ""
        rm_flag = " *" if r["rmse_mean"] <= BENCH_RMSE else ""
        print(f"{r['model']:<22} {r['spearman_mean']:>8.4f}{sp_flag:>2} "
              f"{r['spearman_std']:>6.4f} {r['rmse_mean']:>8.4f}{rm_flag:>2} "
              f"{r['rmse_std']:>6.4f} {r['pearson_mean']:>8.4f} {r['r2_mean']:>8.4f} "
              f"{r['gap_spearman_mean']:>8.4f} {r['elapsed_sec']/60:>5.1f}m")

    print("-" * 90)
    print(f"  Benchmark: Spearman >= {BENCH_SPEARMAN}, RMSE <= {BENCH_RMSE}   (* = meets benchmark)")
    print("=" * 90)

    # ── Baseline 비교 (v1 우선, fallback to original ML) ──
    baseline_candidates = [
        (PROJECT_ROOT / "results" / "ml_mechanism_results_20260413" / "ml_mechanism_results.json", "v1 mechanism"),
        (PROJECT_ROOT / "results" / "ml_results_20260413" / "ml_results.json", "original ML"),
    ]

    for bl_path, bl_label in baseline_candidates:
        if not bl_path.exists():
            continue

        with open(bl_path) as f:
            baseline = json.load(f)

        baseline_dict = {r["model"]: r for r in baseline}

        # v1 mechanism 결과와 비교할 때는 이름 동일 (1_XGBoost 등)
        # original ML과 비교할 때는 이름 매핑 필요
        if bl_label == "original ML":
            name_map = {
                "1_XGBoost": "3_XGBoost",
                "2_CatBoost": "4_CatBoost",
                "3_RandomForest": "5_RandomForest",
                "4_Stacking_Ridge": "7_Stacking_Ridge",
            }
        else:
            name_map = {n: n for n, _ in models_config}

        print(f"\n{'─'*90}")
        print(f"  BASELINE ({bl_label}) vs v2 MECHANISM  (Spearman / RMSE)")
        print(f"{'─'*90}")
        print(f"{'Model':<22} {'Base Sp':>8} {'v2 Sp':>8} {'Delta':>7}  {'Base RMSE':>10} {'v2 RMSE':>10} {'Delta':>7}")
        print("-" * 90)

        for r in all_results:
            bl_name = name_map.get(r["model"])
            if bl_name and bl_name in baseline_dict:
                bl = baseline_dict[bl_name]
                sp_delta = r["spearman_mean"] - bl["spearman_mean"]
                rm_delta = r["rmse_mean"] - bl["rmse_mean"]
                sp_arrow = "+" if sp_delta > 0 else ""
                rm_arrow = "+" if rm_delta > 0 else ""
                print(f"{r['model']:<22} {bl['spearman_mean']:>8.4f} {r['spearman_mean']:>8.4f} "
                      f"{sp_arrow}{sp_delta:>6.4f}  {bl['rmse_mean']:>10.4f} {r['rmse_mean']:>10.4f} "
                      f"{rm_arrow}{rm_delta:>6.4f}")

        print("-" * 90)
        break  # 첫 번째 존재하는 baseline만 출력

    # Save
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    results_path = OUTPUT_DIR / "ml_mechanism_v2_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=convert)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
