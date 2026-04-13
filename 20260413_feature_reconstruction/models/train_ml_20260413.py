#!/usr/bin/env python3
"""
ML Model Training (8 models) with GroupKFold CV
Data: final_features_20260413.parquet (local, CRISPR→Pathway+Target 대체)
CV: GroupKFold(n_splits=5, groups=canonical_drug_id)
Models: LightGBM, LightGBM-DART, XGBoost, CatBoost, RF, ExtraTrees, Stacking(Ridge), RSF
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score
from scipy.stats import spearmanr, pearsonr

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"

N_FOLDS = 5
SEED = 42
OUTPUT_DIR = PROJECT_ROOT / "results" / "ml_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BENCH_SPEARMAN = 0.713
BENCH_RMSE = 1.385

ID_COLS = ["sample_id", "canonical_drug_id"]
LABEL_PREFIX = "label_"


def load_data():
    """Load final_features parquet (local)."""
    print("=" * 70)
    print("Loading data from local parquet...")
    t0 = time.time()

    df = pd.read_parquet(DATA_PATH)

    label_cols = [c for c in df.columns if c.startswith(LABEL_PREFIX)]
    feat_cols = [c for c in df.columns if c not in ID_COLS + label_cols]

    X = df[feat_cols].fillna(0.0).values.astype(np.float32)
    y_reg = df["label_regression"].values.astype(np.float64)
    y_bin = df["label_binary"].values.astype(np.int32)
    drug_ids = df["canonical_drug_id"].values

    dt = time.time() - t0
    print(f"  Loaded: {X.shape[0]} samples x {X.shape[1]} features ({dt:.1f}s)")
    print(f"  y_reg: mean={y_reg.mean():.3f}, std={y_reg.std():.3f}")
    print(f"  y_bin: {y_bin.sum()}/{len(y_bin)} positive ({y_bin.mean()*100:.1f}%)")
    print(f"  Unique drugs: {len(np.unique(drug_ids))}")
    print(f"  CV: GroupKFold(n_splits={N_FOLDS})")
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


# ── Model Definitions (hyperparams unchanged from original) ──

def lgbm_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    import lightgbm as lgb
    dtrain = lgb.Dataset(X_tr, label=y_tr, feature_name=feat_names)
    dval = lgb.Dataset(X_val, label=y_val, feature_name=feat_names, reference=dtrain)
    params = {
        "objective": "regression", "metric": "rmse",
        "boosting_type": "gbdt", "learning_rate": 0.05,
        "num_leaves": 63, "max_depth": 7, "min_child_samples": 20,
        "feature_fraction": 0.7, "bagging_fraction": 0.8, "bagging_freq": 5,
        "reg_alpha": 0.1, "reg_lambda": 1.0,
        "verbose": -1, "seed": SEED + fold_idx, "n_jobs": -1,
    }
    callbacks = [lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)]
    model = lgb.train(params, dtrain, num_boost_round=1500, valid_sets=[dval], callbacks=callbacks)
    return model, model.predict(X_val), model.predict(X_tr)


def lgbm_dart_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    import lightgbm as lgb
    dtrain = lgb.Dataset(X_tr, label=y_tr, feature_name=feat_names)
    dval = lgb.Dataset(X_val, label=y_val, feature_name=feat_names, reference=dtrain)
    params = {
        "objective": "regression", "metric": "rmse",
        "boosting_type": "dart", "learning_rate": 0.05,
        "num_leaves": 63, "max_depth": 7, "min_child_samples": 20,
        "feature_fraction": 0.7, "bagging_fraction": 0.8, "bagging_freq": 5,
        "drop_rate": 0.1, "skip_drop": 0.5,
        "reg_alpha": 0.1, "reg_lambda": 1.0,
        "verbose": -1, "seed": SEED + fold_idx, "n_jobs": -1,
    }
    model = lgb.train(params, dtrain, num_boost_round=500, valid_sets=[dval],
                      callbacks=[lgb.log_evaluation(0)])
    return model, model.predict(X_val), model.predict(X_tr)


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


def extratrees_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from sklearn.ensemble import ExtraTreesRegressor
    model = ExtraTreesRegressor(
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


def rsf_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from sksurv.ensemble import RandomSurvivalForest

    variances = np.var(X_tr, axis=0)
    top_k = min(500, X_tr.shape[1])
    top_idx = np.argsort(variances)[-top_k:]
    X_tr_sub = X_tr[:, top_idx]
    X_val_sub = X_val[:, top_idx]

    all_y = np.concatenate([y_tr, y_val])
    shift = -all_y.min() + 1.0

    threshold = np.quantile(y_tr, 0.3)
    event_tr = (y_tr <= threshold).astype(bool)

    time_tr = y_tr + shift

    y_surv_tr = np.array([(e, t) for e, t in zip(event_tr, time_tr)],
                         dtype=[("event", bool), ("time", float)])

    model = RandomSurvivalForest(
        n_estimators=100, max_depth=None, max_features="sqrt",
        min_samples_leaf=10, n_jobs=-1, random_state=SEED + fold_idx,
    )
    model.fit(X_tr_sub, y_surv_tr)

    risk_val = model.predict(X_val_sub)
    risk_tr = model.predict(X_tr_sub)
    pred_val = -risk_val
    pred_tr = -risk_tr

    return model, pred_val, pred_tr


def rsf_extra_metrics(model, X_tr, y_tr, X_val, y_val, fold_idx):
    from sksurv.metrics import concordance_index_censored

    variances = np.var(X_tr, axis=0)
    top_k = min(500, X_tr.shape[1])
    top_idx = np.argsort(variances)[-top_k:]
    X_val_sub = X_val[:, top_idx]

    all_y = np.concatenate([y_tr, y_val])
    shift = -all_y.min() + 1.0
    threshold = np.quantile(y_tr, 0.3)
    event_val = (y_val <= threshold).astype(bool)
    time_val = y_val + shift

    risk_val = model.predict(X_val_sub)
    c_idx = concordance_index_censored(event_val, time_val, risk_val)

    try:
        auroc = roc_auc_score(event_val.astype(int), risk_val)
    except:
        auroc = float("nan")

    return {"c_index": c_idx[0], "auroc": auroc}


# ── Main ──

def main():
    X, y_reg, y_bin, feat_names, drug_ids = load_data()

    all_results = []
    models_config = [
        ("1_LightGBM",      lgbm_model),
        ("2_LightGBM_DART", lgbm_dart_model),
        ("3_XGBoost",       xgboost_model),
        ("4_CatBoost",      catboost_model),
        ("5_RandomForest",  rf_model),
        ("6_ExtraTrees",    extratrees_model),
        ("7_Stacking_Ridge", stacking_model),
        ("8_RSF",           rsf_model),
    ]

    total_start = time.time()

    for name, fn in models_config:
        t0 = time.time()
        result = run_cv(name, fn, X, y_reg, y_bin, feat_names, drug_ids)
        result["elapsed_sec"] = time.time() - t0

        if name == "8_RSF":
            print("  Computing RSF extra metrics (C-index, AUROC)...")
            gkf = GroupKFold(n_splits=N_FOLDS)
            c_indices, aurocs = [], []
            for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y_reg, groups=drug_ids)):
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y_reg[train_idx], y_reg[val_idx]
                model, _, _ = rsf_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names)
                extra = rsf_extra_metrics(model, X_tr, y_tr, X_val, y_val, fold_idx)
                c_indices.append(extra["c_index"])
                aurocs.append(extra["auroc"])
            result["c_index_mean"] = np.mean(c_indices)
            result["c_index_std"] = np.std(c_indices)
            result["auroc_mean"] = np.nanmean(aurocs)
            result["auroc_std"] = np.nanstd(aurocs)
            print(f"      C-index: {result['c_index_mean']:.4f} +/- {result['c_index_std']:.4f}")
            print(f"      AUROC:   {result['auroc_mean']:.4f} +/- {result['auroc_std']:.4f}")

        all_results.append(result)

    total_elapsed = time.time() - total_start

    # ── Summary Table ──
    print("\n" + "=" * 90)
    print(f"  ML MODELS SUMMARY TABLE (GroupKFold, Total: {total_elapsed/60:.1f} min)")
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

    # Save
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    results_path = OUTPUT_DIR / "ml_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=convert)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
