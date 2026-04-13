#!/usr/bin/env python3
"""
Pipeline B Training — Drug Chemistry Only
═══════════════════════════════════════════════════════════════
  Features: 2,059 (Morgan FP 2048 + Drug Desc 9 + SMILES flags 2)
  Models:   Stacking_Ridge, CatBoost, RandomForest, XGBoost
  CV:       GroupKFold(n_splits=5, groups=canonical_drug_id)
  Label:    label_regression from final_features_20260413.parquet

  Pipeline A 대비 제외:
    - CRISPR / pathway / LINCS
    - target gene 관련 전부
    - mechanism v1/v2/v3 전부
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
PROJECT_ROOT = Path(__file__).resolve().parent

PIPELINE_B_PATH = PROJECT_ROOT / "data" / "pipeline_b_features_20260413.parquet"
FINAL_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"

N_FOLDS = 5
SEED = 42
OUTPUT_DIR = PROJECT_ROOT / "results" / "pipeline_b_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ID_COLS = ["sample_id", "canonical_drug_id"]

# Pipeline A (v2 mechanism) reference scores
PIPELINE_A_SPEARMAN = {
    "Stacking_Ridge": 0.5182,
    "CatBoost":       0.5140,
    "RandomForest":   0.5064,
    "XGBoost":        0.4908,
}


def load_data():
    """Pipeline B features + label join."""
    print("=" * 70)
    print("  Loading Pipeline B data (drug chemistry only)...")
    t0 = time.time()

    # 1. Pipeline B features
    df_b = pd.read_parquet(PIPELINE_B_PATH)
    print(f"  Pipeline B features: {df_b.shape}")

    # 2. Labels from final_features
    df_labels = pd.read_parquet(FINAL_PATH, columns=ID_COLS + ["label_regression"])
    print(f"  Labels: {df_labels.shape}")

    # 3. Merge
    df = df_b.merge(df_labels, on=ID_COLS, how="inner")
    print(f"  Merged: {len(df)} rows (원본 {len(df_b)} rows)")

    # Null check
    n_null_label = df["label_regression"].isnull().sum()
    n_null_feat = df.drop(columns=ID_COLS + ["label_regression"]).isnull().sum().sum()
    print(f"  Label nulls: {n_null_label}")
    print(f"  Feature nulls: {n_null_feat}")

    # Feature columns
    feat_cols = [c for c in df.columns if c not in ID_COLS + ["label_regression"]]

    # Feature breakdown
    n_morgan = sum(1 for c in feat_cols if c.startswith("drug_morgan_"))
    n_desc = sum(1 for c in feat_cols if c.startswith("drug_desc_"))
    n_flags = sum(1 for c in feat_cols if c in {"drug__has_smiles", "drug_has_valid_smiles"})

    X = df[feat_cols].fillna(0.0).values.astype(np.float32)
    y_reg = df["label_regression"].values.astype(np.float64)
    drug_ids = df["canonical_drug_id"].values

    dt = time.time() - t0
    print(f"\n  Feature breakdown:")
    print(f"    drug_morgan_*:         {n_morgan}")
    print(f"    drug_desc_*:           {n_desc}")
    print(f"    drug flags:            {n_flags}")
    print(f"    ─────────────────────")
    print(f"    Total features:        {len(feat_cols)}")
    print(f"  y_reg: mean={y_reg.mean():.3f}, std={y_reg.std():.3f}")
    print(f"  Unique drugs: {len(np.unique(drug_ids))}")
    print(f"  CV: GroupKFold(n_splits={N_FOLDS})")
    print(f"  ({dt:.1f}s)")
    print("=" * 70)

    return X, y_reg, feat_cols, drug_ids


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


def run_cv(model_name, model_fn, X, y_reg, feature_names, drug_ids):
    print(f"\n{'─'*60}")
    print(f"  [{model_name}] Training with 5-fold GroupKFold CV...")
    print(f"{'─'*60}")

    gkf = GroupKFold(n_splits=N_FOLDS)
    fold_metrics = []
    importance_acc = np.zeros(len(feature_names), dtype=np.float64)

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

        imp = get_importance(model, model_name, feature_names)
        if imp is not None:
            importance_acc += imp

        dt = time.time() - t0
        print(f"  Fold {fold_idx}: Spearman={m['spearman']:.4f}  RMSE={m['rmse']:.4f}  "
              f"R2={m['r2']:.4f}  Gap(Sp)={m['gap_spearman']:.4f}  ({dt:.1f}s)")

    df = pd.DataFrame(fold_metrics)
    summary = {
        "model": model_name,
        "spearman_mean": float(df["spearman"].mean()),
        "spearman_std": float(df["spearman"].std()),
        "rmse_mean": float(df["rmse"].mean()),
        "rmse_std": float(df["rmse"].std()),
        "pearson_mean": float(df["pearson"].mean()),
        "r2_mean": float(df["r2"].mean()),
        "r2_std": float(df["r2"].std()),
        "train_spearman_mean": float(df["train_spearman"].mean()),
        "gap_spearman_mean": float(df["gap_spearman"].mean()),
        "gap_rmse_mean": float(df["gap_rmse"].mean()),
        "folds": fold_metrics,
    }

    print(f"\n  >>> {model_name} SUMMARY:")
    print(f"      Spearman: {summary['spearman_mean']:.4f} +/- {summary['spearman_std']:.4f}")
    print(f"      RMSE:     {summary['rmse_mean']:.4f} +/- {summary['rmse_std']:.4f}")
    print(f"      Pearson:  {summary['pearson_mean']:.4f}")
    print(f"      R2:       {summary['r2_mean']:.4f} +/- {summary['r2_std']:.4f}")
    print(f"      Train Sp: {summary['train_spearman_mean']:.4f}  Gap: {summary['gap_spearman_mean']:.4f}")

    # Pipeline A comparison
    clean_name = model_name.split("_", 1)[1] if "_" in model_name else model_name
    if clean_name in PIPELINE_A_SPEARMAN:
        pa_sp = PIPELINE_A_SPEARMAN[clean_name]
        delta = summary["spearman_mean"] - pa_sp
        arrow = "+" if delta > 0 else ""
        print(f"      vs Pipeline A: {pa_sp:.4f} → {summary['spearman_mean']:.4f}  "
              f"(delta={arrow}{delta:.4f})")

    imp_mean = importance_acc / N_FOLDS if importance_acc.sum() > 0 else None
    return summary, imp_mean


def get_importance(model, model_name, feature_names):
    try:
        if "XGBoost" in model_name:
            imp_dict = model.get_score(importance_type="gain")
            imp = np.zeros(len(feature_names))
            for fname, val in imp_dict.items():
                if fname in feature_names:
                    idx = feature_names.index(fname)
                    imp[idx] = val
            return imp
        elif "CatBoost" in model_name:
            return np.array(model.get_feature_importance(), dtype=np.float64)
        elif "RandomForest" in model_name:
            return np.array(model.feature_importances_, dtype=np.float64)
    except Exception:
        pass
    return None


# ── Model Definitions (동일 하이퍼파라미터) ──

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


# ── Feature Importance Report ──

def report_feature_importance(importances, feature_names, top_k=20):
    print("\n" + "=" * 90)
    print("  FEATURE IMPORTANCE REPORT (averaged across 5 folds)")
    print("=" * 90)

    fi_report = {}

    for model_name, imp in importances.items():
        if imp is None:
            continue

        total = imp.sum()
        if total == 0:
            continue
        imp_norm = imp / total
        sorted_idx = np.argsort(imp_norm)[::-1]

        print(f"\n{'─'*70}")
        print(f"  [{model_name}] Top {top_k} Features")
        print(f"{'─'*70}")
        print(f"  {'Rank':>4}  {'Feature':<45s}  {'Importance':>10s}  {'%':>6s}  {'Type'}")
        print("  " + "-" * 78)

        for rank, idx in enumerate(sorted_idx[:top_k], 1):
            fname = feature_names[idx]
            if fname.startswith("drug_morgan_"):
                ftype = "Morgan"
            elif fname.startswith("drug_desc_"):
                ftype = "Desc"
            else:
                ftype = "Flag"
            print(f"  {rank:>4}  {fname:<45s}  {imp_norm[idx]:>10.6f}  "
                  f"{imp_norm[idx]*100:>5.2f}%  {ftype}")

        # Morgan vs Desc vs Flags aggregated importance
        morgan_imp = sum(imp_norm[i] for i, c in enumerate(feature_names) if c.startswith("drug_morgan_"))
        desc_imp = sum(imp_norm[i] for i, c in enumerate(feature_names) if c.startswith("drug_desc_"))
        flag_imp = sum(imp_norm[i] for i, c in enumerate(feature_names) if c in {"drug__has_smiles", "drug_has_valid_smiles"})

        print(f"\n  Feature Type Importance Summary:")
        print(f"    Morgan FP (2048):    {morgan_imp*100:>6.2f}%")
        print(f"    Drug Desc (9):       {desc_imp*100:>6.2f}%")
        print(f"    SMILES Flags (2):    {flag_imp*100:>6.2f}%")

        # Drug desc individual ranking
        print(f"\n  Drug Descriptor Rankings:")
        desc_cols = [c for c in feature_names if c.startswith("drug_desc_")]
        for dc in desc_cols:
            dc_idx = feature_names.index(dc)
            dc_rank = int((sorted_idx == dc_idx).argmax()) + 1
            dc_pct = imp_norm[dc_idx] * 100
            print(f"    {dc:<40s}  rank={dc_rank:>5d}  ({dc_pct:.3f}%)")

        # Save for JSON
        top20 = [
            {"rank": i + 1, "feature": feature_names[idx],
             "importance": float(imp_norm[idx])}
            for i, idx in enumerate(sorted_idx[:top_k])
        ]
        fi_report[model_name] = {
            "top20": top20,
            "type_summary": {
                "morgan_fp_pct": float(morgan_imp * 100),
                "drug_desc_pct": float(desc_imp * 100),
                "smiles_flags_pct": float(flag_imp * 100),
            },
        }

    return fi_report


# ── Main ──

def main():
    X, y_reg, feat_names, drug_ids = load_data()

    all_results = []
    importances = {}

    models_config = [
        ("1_Stacking_Ridge", stacking_model),
        ("2_CatBoost",       catboost_model),
        ("3_RandomForest",   rf_model),
        ("4_XGBoost",        xgboost_model),
    ]

    total_start = time.time()

    for name, fn in models_config:
        t0 = time.time()
        result, imp = run_cv(name, fn, X, y_reg, feat_names, drug_ids)
        result["elapsed_sec"] = time.time() - t0
        all_results.append(result)
        importances[name] = imp

    total_elapsed = time.time() - total_start

    # ── Pipeline A vs B Comparison ──
    print("\n" + "=" * 90)
    print(f"  PIPELINE A vs PIPELINE B COMPARISON (Total: {total_elapsed/60:.1f} min)")
    print("=" * 90)
    print(f"  Pipeline A: 2,182 features (base 2167 + mech v1 5 + mech v2 10)")
    print(f"  Pipeline B: {len(feat_names)} features (drug chemistry only)")
    print(f"  제외: CRISPR, pathway, LINCS, target gene, mechanism v1/v2/v3")
    print()
    print(f"{'Model':<22} {'A Sp':>8} {'B Sp':>8} {'Delta':>7} "
          f"{'B Train':>8} {'B Gap':>7} {'A-B Gap':>8} {'Time':>6}")
    print("-" * 90)

    for r in all_results:
        clean_name = r["model"].split("_", 1)[1] if "_" in r["model"] else r["model"]
        pa_sp = PIPELINE_A_SPEARMAN.get(clean_name, None)
        if pa_sp is not None:
            delta = r["spearman_mean"] - pa_sp
            arrow = "+" if delta >= 0 else ""
            # Pipeline A gap (from reference data)
            pa_gap_ref = {
                "Stacking_Ridge": 0.386,
                "CatBoost": 0.331,
                "RandomForest": 0.352,
                "XGBoost": 0.387,
            }
            pa_gap = pa_gap_ref.get(clean_name, "N/A")
            print(f"{clean_name:<22} {pa_sp:>8.4f} {r['spearman_mean']:>8.4f} "
                  f"{arrow}{delta:>6.4f} {r['train_spearman_mean']:>8.4f} "
                  f"{r['gap_spearman_mean']:>7.4f} {pa_gap:>8} "
                  f"{r['elapsed_sec']/60:>5.1f}m")
        else:
            print(f"{r['model']:<22} {'N/A':>8} {r['spearman_mean']:>8.4f} "
                  f"{'N/A':>7} {r['train_spearman_mean']:>8.4f} "
                  f"{r['gap_spearman_mean']:>7.4f} {'N/A':>8} "
                  f"{r['elapsed_sec']/60:>5.1f}m")

    print("-" * 90)
    print(f"  Pipeline A features: base(2167) + v1 target/pathway(5) + v2 interactions(10)")
    print(f"  Pipeline B features: Morgan FP(2048) + Drug Desc(9) + SMILES flags(2)")
    print("=" * 90)

    # ── Detailed metrics ──
    print(f"\n{'─'*90}")
    print(f"  Pipeline B Detailed Metrics")
    print(f"{'─'*90}")
    print(f"{'Model':<22} {'Spearman':>10} {'  std':>6} {'RMSE':>8} {'  std':>6} "
          f"{'Pearson':>8} {'R2':>8}")
    print("-" * 90)

    for r in all_results:
        clean_name = r["model"].split("_", 1)[1] if "_" in r["model"] else r["model"]
        print(f"{clean_name:<22} {r['spearman_mean']:>8.4f}   "
              f"{r['spearman_std']:>6.4f} {r['rmse_mean']:>8.4f}   "
              f"{r['rmse_std']:>6.4f} {r['pearson_mean']:>8.4f} {r['r2_mean']:>8.4f}")

    print("-" * 90)

    # ── Feature Importance ──
    fi_report = report_feature_importance(importances, feat_names, top_k=20)

    # ── Save ──
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    save_data = {
        "description": "Pipeline B: Drug Chemistry Only (Morgan FP + Drug Desc + SMILES flags)",
        "n_features": len(feat_names),
        "feature_breakdown": {
            "drug_morgan": 2048,
            "drug_desc": 9,
            "smiles_flags": 2,
        },
        "pipeline_a_reference": PIPELINE_A_SPEARMAN,
        "model_results": [
            {k: v for k, v in r.items() if k != "folds"}
            for r in all_results
        ],
        "model_folds": {r["model"]: r["folds"] for r in all_results},
        "feature_importance": fi_report,
    }

    results_path = OUTPUT_DIR / "pipeline_b_results.json"
    with open(results_path, "w") as f:
        json.dump(save_data, f, indent=2, default=convert)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
