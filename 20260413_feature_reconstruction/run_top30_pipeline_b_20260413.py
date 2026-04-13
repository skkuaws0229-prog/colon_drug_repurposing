#!/usr/bin/env python3
"""
Pipeline B Top 30 Drug Extraction
═══════════════════════════════════════════════════════════════
  1. 4 모델 재학습 → OOF prediction 수집
  2. Spearman 비례 앙상블 가중치 계산
  3. Drug별 평균 IC50 예측 → 상위 30개 추출
  4. Pipeline A Top 30과 비교

  Input:  data/pipeline_b_features_20260413.parquet
          data/final_features_20260413.parquet
  Output: results/pipeline_b_results_20260413/top30_pipeline_b_20260413.csv
          results/pipeline_b_results_20260413/pipeline_b_oof_predictions.parquet
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from sklearn.model_selection import GroupKFold
from scipy.stats import spearmanr

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent

PIPELINE_B_PATH = PROJECT_ROOT / "data" / "pipeline_b_features_20260413.parquet"
FINAL_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"
DRUG_ANN_S3 = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"

OUTPUT_DIR = PROJECT_ROOT / "results" / "pipeline_b_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pipeline A Top 30 (dedup, 28 drugs)
PIPELINE_A_TOP30_CSV = PROJECT_ROOT / "results" / "top30_dedup_20260413" / "top30_dedup_20260413.csv"

N_FOLDS = 5
SEED = 42
TOP_K = 30
SENSITIVITY_THRESHOLD = 0.0
ID_COLS = ["sample_id", "canonical_drug_id"]


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
    return model.predict(dval), model.predict(dtrain)


def catboost_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from catboost import CatBoostRegressor
    model = CatBoostRegressor(
        iterations=1500, learning_rate=0.05, depth=7,
        l2_leaf_reg=3.0, rsm=0.7, subsample=0.8,
        early_stopping_rounds=50, random_seed=SEED + fold_idx,
        verbose=0, thread_count=-1,
    )
    model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
    return model.predict(X_val), model.predict(X_tr)


def rf_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names):
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(
        n_estimators=500, max_depth=None, max_features="sqrt",
        min_samples_leaf=5, n_jobs=-1, random_state=SEED + fold_idx,
    )
    model.fit(X_tr, y_tr)
    return model.predict(X_val), model.predict(X_tr)


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
    return model.predict(X_val), model.predict(X_tr)


MODELS = [
    ("Stacking_Ridge", stacking_model),
    ("CatBoost",       catboost_model),
    ("RandomForest",   rf_model),
    ("XGBoost",        xgboost_model),
]


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Pipeline B Top 30 Drug Extraction")
    print("  (OOF prediction + Spearman 비례 앙상블)")
    print("=" * 70)

    # ── 1. Load Data ──
    print("\n  Loading data...")
    df_b = pd.read_parquet(PIPELINE_B_PATH)
    df_labels = pd.read_parquet(FINAL_PATH, columns=ID_COLS + ["label_regression"])
    df = df_b.merge(df_labels, on=ID_COLS, how="inner")
    print(f"    Shape: {df.shape} ({len(df)} samples, {df['canonical_drug_id'].nunique()} drugs)")

    feat_cols = [c for c in df.columns if c not in ID_COLS + ["label_regression"]]
    X = df[feat_cols].fillna(0.0).values.astype(np.float32)
    y = df["label_regression"].values.astype(np.float64)
    drug_ids = df["canonical_drug_id"].values
    sample_ids = df["sample_id"].values
    print(f"    Features: {len(feat_cols)}")

    # ── 2. Collect OOF Predictions ──
    print(f"\n  Collecting OOF predictions (4 models × 5 folds)...")
    gkf = GroupKFold(n_splits=N_FOLDS)
    folds = list(gkf.split(X, y, groups=drug_ids))

    # Initialize OOF arrays
    oof_preds = {}
    model_spearmans = {}

    for model_name, model_fn in MODELS:
        t_m = time.time()
        oof = np.full(len(y), np.nan)

        for fold_idx, (train_idx, val_idx) in enumerate(folds):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]

            y_pred_val, _ = model_fn(X_tr, y_tr, X_val, y_val, fold_idx, feat_cols)
            oof[val_idx] = y_pred_val

        sp, _ = spearmanr(y, oof)
        model_spearmans[model_name] = sp
        oof_preds[model_name] = oof
        dt_m = time.time() - t_m
        print(f"    {model_name:<20s}: Spearman={sp:.4f}  ({dt_m:.1f}s)")

    # ── 3. Spearman 비례 앙상블 가중치 ──
    print(f"\n  Computing Spearman-proportional ensemble weights...")
    total_sp = sum(model_spearmans.values())
    weights = {name: sp / total_sp for name, sp in model_spearmans.items()}

    print(f"    {'Model':<20s} {'Spearman':>10s} {'Weight':>8s}")
    print(f"    {'-'*40}")
    for name, w in weights.items():
        print(f"    {name:<20s} {model_spearmans[name]:>10.4f} {w:>8.4f}")
    print(f"    {'Total':<20s} {total_sp:>10.4f} {sum(weights.values()):>8.4f}")

    # ── 4. 앙상블 OOF 예측 ──
    oof_ensemble = np.zeros(len(y))
    for name, w in weights.items():
        oof_ensemble += oof_preds[name] * w

    sp_ens, _ = spearmanr(y, oof_ensemble)
    print(f"\n    Ensemble OOF Spearman: {sp_ens:.4f}")

    # ── 5. OOF predictions 저장 ──
    oof_df = pd.DataFrame({
        "sample_id": sample_ids,
        "canonical_drug_id": drug_ids,
        "y_true": y,
    })
    for name in oof_preds:
        oof_df[f"pred_{name}"] = oof_preds[name]
    oof_df["pred_ensemble"] = oof_ensemble

    oof_path = OUTPUT_DIR / "pipeline_b_oof_predictions.parquet"
    oof_df.to_parquet(oof_path, index=False)
    print(f"    Saved: {oof_path.name}")

    # ── 6. Drug별 평균 예측값 ──
    print(f"\n  Aggregating per-drug predictions...")
    drug_stats = oof_df.groupby("canonical_drug_id").agg(
        mean_pred_ic50=("pred_ensemble", "mean"),
        std_pred_ic50=("pred_ensemble", "std"),
        mean_true_ic50=("y_true", "mean"),
        std_true_ic50=("y_true", "std"),
        n_samples=("sample_id", "count"),
    ).reset_index()

    # Sensitivity rate
    sens = oof_df.groupby("canonical_drug_id").apply(
        lambda g: (g["pred_ensemble"] < SENSITIVITY_THRESHOLD).mean()
    ).reset_index(name="sensitivity_rate")
    drug_stats = drug_stats.merge(sens, on="canonical_drug_id")

    # True sensitivity rate
    true_sens = oof_df.groupby("canonical_drug_id").apply(
        lambda g: (g["y_true"] < SENSITIVITY_THRESHOLD).mean()
    ).reset_index(name="true_sensitivity_rate")
    drug_stats = drug_stats.merge(true_sens, on="canonical_drug_id")

    print(f"    Total drugs: {len(drug_stats)}")
    print(f"    Pred IC50 range: [{drug_stats['mean_pred_ic50'].min():.3f}, "
          f"{drug_stats['mean_pred_ic50'].max():.3f}]")

    # ── 7. Drug annotation 병합 ──
    print(f"\n  Loading drug annotations...")
    drug_ann = pd.read_parquet(DRUG_ANN_S3)
    drug_ann = drug_ann.rename(columns={"DRUG_ID": "canonical_drug_id"})
    drug_ann["canonical_drug_id"] = drug_ann["canonical_drug_id"].astype(str)
    drug_stats["canonical_drug_id"] = drug_stats["canonical_drug_id"].astype(str)

    drug_stats = drug_stats.merge(
        drug_ann[["canonical_drug_id", "DRUG_NAME", "PUTATIVE_TARGET_NORMALIZED",
                  "PATHWAY_NAME_NORMALIZED"]],
        on="canonical_drug_id", how="left",
    )
    drug_stats = drug_stats.rename(columns={
        "DRUG_NAME": "drug_name",
        "PUTATIVE_TARGET_NORMALIZED": "target",
        "PATHWAY_NAME_NORMALIZED": "pathway",
    })

    # ── 8. Top 30 선정 ──
    drug_stats = drug_stats.sort_values("mean_pred_ic50", ascending=True)
    drug_stats["rank"] = range(1, len(drug_stats) + 1)
    top30 = drug_stats.head(TOP_K).copy()

    # ── 9. 결과 출력 ──
    print(f"\n{'='*100}")
    print(f"  PIPELINE B TOP {TOP_K} DRUGS (Spearman 비례 앙상블, 낮은 IC50 = 효과적)")
    print(f"{'='*100}")
    print(f"  {'Rank':>4}  {'Drug':<25} {'Pred IC50':>10} {'True IC50':>10} "
          f"{'Sens%':>6} {'N':>4} {'Target':<25} {'Pathway':<20}")
    print(f"  {'-'*110}")

    for _, r in top30.iterrows():
        target = str(r.get("target", "N/A"))[:23]
        pathway = str(r.get("pathway", "N/A"))[:18]
        print(f"  {int(r['rank']):>4}  {str(r.get('drug_name', 'N/A')):<25} "
              f"{r['mean_pred_ic50']:>10.4f} {r['mean_true_ic50']:>10.4f} "
              f"{r['sensitivity_rate']:>5.0%} {int(r['n_samples']):>4} "
              f"{target:<25} {pathway:<20}")

    # ── 10. Pipeline A Top 30과 비교 ──
    print(f"\n{'='*100}")
    print(f"  PIPELINE A vs B TOP 30 COMPARISON")
    print(f"{'='*100}")

    if PIPELINE_A_TOP30_CSV.exists():
        pa_top30 = pd.read_csv(PIPELINE_A_TOP30_CSV)
        pa_drugs = set(pa_top30["drug_name"].dropna().values)
        pb_drugs = set(top30["drug_name"].dropna().values)

        common = pa_drugs & pb_drugs
        only_a = pa_drugs - pb_drugs
        only_b = pb_drugs - pa_drugs

        print(f"\n  Pipeline A Top {len(pa_drugs)}: {len(pa_drugs)} drugs (dedup 후)")
        print(f"  Pipeline B Top {TOP_K}: {TOP_K} drugs")
        print(f"\n  공통 약물: {len(common)}개")
        print(f"  {'─'*60}")

        # Common drugs with rank comparison
        if common:
            print(f"  {'Drug':<25} {'A Rank':>7} {'B Rank':>7} {'A Pred':>9} {'B Pred':>9}")
            print(f"  {'─'*60}")
            for drug in sorted(common):
                a_rank = int(pa_top30[pa_top30["drug_name"] == drug]["rank"].values[0])
                b_rank = int(top30[top30["drug_name"] == drug]["rank"].values[0])
                a_pred = float(pa_top30[pa_top30["drug_name"] == drug]["mean_pred_ic50"].values[0])
                b_pred = float(top30[top30["drug_name"] == drug]["mean_pred_ic50"].values[0])
                print(f"  {drug:<25} {a_rank:>7} {b_rank:>7} {a_pred:>9.4f} {b_pred:>9.4f}")

        print(f"\n  Pipeline A에만 있는 약물: {len(only_a)}개")
        if only_a:
            for drug in sorted(only_a):
                a_rank = int(pa_top30[pa_top30["drug_name"] == drug]["rank"].values[0])
                # B에서의 rank 찾기
                b_row = drug_stats[drug_stats["drug_name"] == drug]
                b_rank = int(b_row["rank"].values[0]) if len(b_row) > 0 else "N/A"
                print(f"    {drug:<25} A#{a_rank}  →  B#{b_rank}")

        print(f"\n  Pipeline B에만 있는 약물 (신규): {len(only_b)}개")
        if only_b:
            for drug in sorted(only_b):
                b_rank = int(top30[top30["drug_name"] == drug]["rank"].values[0])
                # A에서의 rank 찾기
                a_row = pa_top30[pa_top30["drug_name"] == drug]
                if len(a_row) > 0:
                    a_rank = int(a_row["rank"].values[0])
                    print(f"    {drug:<25} B#{b_rank}  (A#{a_rank} — 이미 A에 있었으나 순위 다름)")
                else:
                    print(f"    {drug:<25} B#{b_rank}  ★ Pipeline B 고유")
    else:
        print("  Pipeline A Top 30 CSV not found")

    # ── 11. 통계 요약 ──
    print(f"\n{'='*100}")
    print(f"  SUMMARY")
    print(f"{'='*100}")
    print(f"    Ensemble weights: {', '.join(f'{k}={v:.4f}' for k, v in weights.items())}")
    print(f"    Ensemble OOF Spearman: {sp_ens:.4f}")
    print(f"    Top {TOP_K} drugs pred IC50 mean: {top30['mean_pred_ic50'].mean():.4f}")
    print(f"    Top {TOP_K} drugs sensitivity rate: {top30['sensitivity_rate'].mean():.1%}")
    if PIPELINE_A_TOP30_CSV.exists():
        print(f"    Pipeline A 공통: {len(common)}/{TOP_K}")
        print(f"    Pipeline B 고유: {len(only_b)}개")

    # ── 12. 저장 ──
    save_cols = ["rank", "canonical_drug_id", "drug_name", "target", "pathway",
                 "mean_pred_ic50", "std_pred_ic50", "mean_true_ic50",
                 "sensitivity_rate", "true_sensitivity_rate", "n_samples"]

    csv_path = OUTPUT_DIR / "top30_pipeline_b_20260413.csv"
    top30[save_cols].to_csv(csv_path, index=False)
    print(f"\n  Saved: {csv_path}")

    # JSON summary
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    json_path = OUTPUT_DIR / "top30_pipeline_b_summary.json"
    with open(json_path, "w") as f:
        json.dump({
            "description": "Pipeline B Top 30 (drug chemistry only, Spearman-proportional ensemble)",
            "ensemble_weights": weights,
            "model_spearmans": model_spearmans,
            "ensemble_oof_spearman": float(sp_ens),
            "total_drugs": len(drug_stats),
            "top30_drugs": top30[save_cols].to_dict(orient="records"),
            "comparison_with_pipeline_a": {
                "common_drugs": sorted(list(common)) if PIPELINE_A_TOP30_CSV.exists() else [],
                "only_pipeline_a": sorted(list(only_a)) if PIPELINE_A_TOP30_CSV.exists() else [],
                "only_pipeline_b": sorted(list(only_b)) if PIPELINE_A_TOP30_CSV.exists() else [],
            },
        }, f, indent=2, default=convert)
    print(f"  Saved: {json_path}")

    dt = time.time() - t0
    print(f"\n  Completed in {dt:.1f}s ({dt/60:.1f}m)")
    print("=" * 70)


if __name__ == "__main__":
    main()
