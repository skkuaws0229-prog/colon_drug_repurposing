#!/usr/bin/env python3
"""
LightGBM Ranker + Mechanism v1 + v2 Features with GroupKFold CV
═══════════════════════════════════════════════════════════════
Data: final_features(2167) + v1(5) + v2(10) merge
Label: IC50 → normalized rank within sample (lower IC50 = higher relevance [0,1])
CV: GroupKFold(n_splits=5, groups=canonical_drug_id)
Ranking query: sample_id
Metrics: NDCG@10, NDCG@20
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from sklearn.model_selection import GroupKFold
from sklearn.metrics import ndcg_score
from scipy.stats import spearmanr

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MECH_DIR = Path(__file__).resolve().parent

FINAL_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"
V1_PATH = MECH_DIR / "mechanism_features_v1_20260413.parquet"
V2_PATH = MECH_DIR / "mechanism_features_v2_20260413.parquet"

N_FOLDS = 5
SEED = 42
OUTPUT_DIR = PROJECT_ROOT / "results" / "ranking_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    """Load final_features + v1 + v2, compute ranking labels."""
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
    drug_ids = df["canonical_drug_id"].values
    sample_ids = df["sample_id"].values

    # ── Ranking label: within each sample, lower IC50 → higher relevance ──
    # rank(ascending=True): lowest IC50 → rank 1
    # Float relevance [0, 1]: for sklearn NDCG evaluation
    # Integer grade [0, 4]: for LightGBM (quintile-based, LambdaRank requires int)
    rank_asc = df.groupby("sample_id")["label_regression"].rank(
        method="average", ascending=True
    )
    n_per_sample = df.groupby("sample_id")["label_regression"].transform("count")
    y_rank_float = np.where(
        n_per_sample > 1,
        (n_per_sample - rank_asc) / (n_per_sample - 1),
        0.0,
    ).astype(np.float32)

    # Integer grade 0-4 (quintile): 0=bottom 20%, 4=top 20%
    # gain: 2^0-1=0, 2^1-1=1, 2^2-1=3, 2^3-1=7, 2^4-1=15
    y_rank_int = np.clip((y_rank_float * 5).astype(np.int32), 0, 4)

    n_v1 = len([c for c in V1_FEATURE_COLS if c in feat_cols])
    n_v2 = len([c for c in V2_FEATURE_COLS if c in feat_cols])
    n_total = len(feat_cols)

    dt = time.time() - t0
    print(f"  final_features: {n_final} rows, {n_final_feat} features")
    print(f"  v1 mechanism:   {len(df_v1)} drugs × {n_v1} features")
    print(f"  v2 mechanism:   {len(df_v2)} rows × {n_v2} features")
    print(f"  Merged: {n_merged} rows (유지: {'OK' if n_final == n_merged else 'FAIL'})")
    print(f"  Total features: {n_total}")

    # Query 구성 확인
    sample_counts = pd.Series(sample_ids).value_counts()
    print(f"  Unique samples: {len(sample_counts)}, Unique drugs: {len(np.unique(drug_ids))}")
    print(f"  Drugs per sample: min={sample_counts.min()}, max={sample_counts.max()}, "
          f"mean={sample_counts.mean():.1f}")
    print(f"  y_reg (IC50): mean={y_reg.mean():.3f}, std={y_reg.std():.3f}")
    print(f"  y_rank float [0,1]: mean={y_rank_float.mean():.3f}, std={y_rank_float.std():.3f}")
    print(f"  y_rank int [0-4] distribution: {dict(zip(*np.unique(y_rank_int, return_counts=True)))}")
    print(f"  CV: GroupKFold(n_splits={N_FOLDS}, groups=drug_id)")
    print(f"  Ranking query: sample_id")
    print(f"  ({dt:.1f}s)")
    print("=" * 70)
    return X, y_reg, y_rank_float, y_rank_int, feat_cols, drug_ids, sample_ids


def prepare_ranking_groups(sample_ids, indices):
    """Sort indices by sample_id for contiguous query groups.
    Returns (sorted_indices, sorted_sample_ids, group_sizes)."""
    sids = sample_ids[indices]
    sort_order = np.argsort(sids, kind="stable")
    sorted_indices = indices[sort_order]
    sorted_sids = sids[sort_order]
    _, group_sizes = np.unique(sorted_sids, return_counts=True)
    return sorted_indices, sorted_sids, group_sizes.tolist()


def compute_ndcg_per_query(y_true, y_pred, sample_ids, k):
    """Compute mean NDCG@k across query groups (samples)."""
    ndcgs = []
    for sid in np.unique(sample_ids):
        mask = sample_ids == sid
        n = mask.sum()
        if n < 2:
            continue
        true = y_true[mask].reshape(1, -1)
        pred = y_pred[mask].reshape(1, -1)
        ndcgs.append(ndcg_score(true, pred, k=min(k, n)))
    return np.mean(ndcgs) if ndcgs else 0.0


def main():
    import lightgbm as lgb

    X, y_reg, y_rank_float, y_rank_int, feat_names, drug_ids, sample_ids = load_data()

    print(f"\n{'─'*70}")
    print(f"  [LightGBM Ranker] {N_FOLDS}-fold GroupKFold CV")
    print(f"  objective=lambdarank, label=int grade [0-4], eval_at=[10, 20]")
    print(f"{'─'*70}")

    gkf = GroupKFold(n_splits=N_FOLDS)
    fold_metrics = []
    total_start = time.time()

    for fold_idx, (train_idx, val_idx) in enumerate(
        gkf.split(X, y_rank_int, groups=drug_ids)
    ):
        t0 = time.time()

        # ── Fold별 ranking query 구성 ──
        train_sorted, train_sids, train_groups = prepare_ranking_groups(
            sample_ids, train_idx
        )
        val_sorted, val_sids, val_groups = prepare_ranking_groups(
            sample_ids, val_idx
        )

        # int labels for LightGBM training, float labels for NDCG evaluation
        X_tr = X[train_sorted]
        X_val = X[val_sorted]
        y_tr_int = y_rank_int[train_sorted]
        y_val_int = y_rank_int[val_sorted]
        y_tr_float = y_rank_float[train_sorted]
        y_val_float = y_rank_float[val_sorted]
        yr_val = y_reg[val_sorted]

        n_train_drugs = len(np.unique(drug_ids[train_idx]))
        n_val_drugs = len(np.unique(drug_ids[val_idx]))

        print(f"\n  Fold {fold_idx} ranking query 구성:")
        print(f"    Train: {len(train_idx):,} rows, {n_train_drugs} drugs, "
              f"{len(train_groups)} queries "
              f"(avg {np.mean(train_groups):.1f} items/query)")
        print(f"    Val:   {len(val_idx):,} rows, {n_val_drugs} drugs, "
              f"{len(val_groups)} queries "
              f"(avg {np.mean(val_groups):.1f} items/query)")
        print(f"    Train group range: [{min(train_groups)}, {max(train_groups)}]")
        print(f"    Val group range:   [{min(val_groups)}, {max(val_groups)}]")

        # ── Train LightGBM Ranker ──
        model = lgb.LGBMRanker(
            objective="lambdarank",
            n_estimators=1500,
            learning_rate=0.05,
            num_leaves=63,
            max_depth=7,
            colsample_bytree=0.7,
            subsample=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            min_child_samples=20,
            n_jobs=-1,
            random_state=SEED + fold_idx,
            verbose=-1,
            eval_at=[10, 20],
        )
        model.fit(
            X_tr, y_tr_int,
            group=train_groups,
            eval_set=[(X_val, y_val_int)],
            eval_group=[val_groups],
            callbacks=[
                lgb.early_stopping(50, verbose=False),
                lgb.log_evaluation(0),
            ],
        )

        # ── Predict & Evaluate ──
        y_pred_val = model.predict(X_val)
        y_pred_tr = model.predict(X_tr)

        # NDCG: use float relevance labels for finer-grained evaluation
        ndcg_10 = compute_ndcg_per_query(y_val_float, y_pred_val, val_sids, 10)
        ndcg_20 = compute_ndcg_per_query(y_val_float, y_pred_val, val_sids, 20)
        train_ndcg_10 = compute_ndcg_per_query(y_tr_float, y_pred_tr, train_sids, 10)
        train_ndcg_20 = compute_ndcg_per_query(y_tr_float, y_pred_tr, train_sids, 20)

        # Spearman: float relevance label vs predicted score
        sp_rank, _ = spearmanr(y_val_float, y_pred_val)
        # Spearman: negative IC50 vs predicted score (higher pred = lower IC50 expected)
        sp_ic50, _ = spearmanr(-yr_val, y_pred_val)

        m = {
            "fold": fold_idx,
            "ndcg_10": float(ndcg_10),
            "ndcg_20": float(ndcg_20),
            "train_ndcg_10": float(train_ndcg_10),
            "train_ndcg_20": float(train_ndcg_20),
            "gap_ndcg_10": float(train_ndcg_10 - ndcg_10),
            "gap_ndcg_20": float(train_ndcg_20 - ndcg_20),
            "spearman_rank": float(sp_rank),
            "spearman_ic50": float(sp_ic50),
            "n_train_queries": len(train_groups),
            "n_val_queries": len(val_groups),
            "best_iteration": model.best_iteration_,
        }
        fold_metrics.append(m)

        dt = time.time() - t0
        print(f"  Fold {fold_idx} result: NDCG@10={ndcg_10:.4f}  NDCG@20={ndcg_20:.4f}  "
              f"Sp(rank)={sp_rank:.4f}  Sp(IC50)={sp_ic50:.4f}  "
              f"Gap(N@10)={m['gap_ndcg_10']:.4f}  iter={model.best_iteration_}  ({dt:.1f}s)")

    total_elapsed = time.time() - total_start

    # ── Summary ──
    df_m = pd.DataFrame(fold_metrics)
    summary = {
        "model": "LightGBM_Ranker",
        "ndcg_10_mean": float(df_m["ndcg_10"].mean()),
        "ndcg_10_std": float(df_m["ndcg_10"].std()),
        "ndcg_20_mean": float(df_m["ndcg_20"].mean()),
        "ndcg_20_std": float(df_m["ndcg_20"].std()),
        "train_ndcg_10_mean": float(df_m["train_ndcg_10"].mean()),
        "train_ndcg_20_mean": float(df_m["train_ndcg_20"].mean()),
        "gap_ndcg_10_mean": float(df_m["gap_ndcg_10"].mean()),
        "gap_ndcg_20_mean": float(df_m["gap_ndcg_20"].mean()),
        "spearman_rank_mean": float(df_m["spearman_rank"].mean()),
        "spearman_ic50_mean": float(df_m["spearman_ic50"].mean()),
        "folds": fold_metrics,
        "elapsed_sec": total_elapsed,
    }

    print("\n" + "=" * 80)
    print(f"  LightGBM RANKER SUMMARY (GroupKFold, {total_elapsed/60:.1f} min)")
    print("=" * 80)
    print(f"  NDCG@10:        {summary['ndcg_10_mean']:.4f} +/- {summary['ndcg_10_std']:.4f}")
    print(f"  NDCG@20:        {summary['ndcg_20_mean']:.4f} +/- {summary['ndcg_20_std']:.4f}")
    print(f"  Spearman(rank): {summary['spearman_rank_mean']:.4f}")
    print(f"  Spearman(IC50): {summary['spearman_ic50_mean']:.4f}")
    print(f"  Train N@10:     {summary['train_ndcg_10_mean']:.4f}  "
          f"Gap: {summary['gap_ndcg_10_mean']:.4f}")
    print(f"  Train N@20:     {summary['train_ndcg_20_mean']:.4f}  "
          f"Gap: {summary['gap_ndcg_20_mean']:.4f}")
    print("-" * 80)

    # Per-fold table
    print(f"\n  {'Fold':>4}  {'NDCG@10':>8}  {'NDCG@20':>8}  {'Sp(rank)':>8}  "
          f"{'Sp(IC50)':>8}  {'Gap(N@10)':>9}  {'Iter':>5}")
    print("  " + "-" * 60)
    for m in fold_metrics:
        print(f"  {m['fold']:>4}  {m['ndcg_10']:>8.4f}  {m['ndcg_20']:>8.4f}  "
              f"{m['spearman_rank']:>8.4f}  {m['spearman_ic50']:>8.4f}  "
              f"{m['gap_ndcg_10']:>9.4f}  {m['best_iteration']:>5}")
    print("=" * 80)

    # ── Save ──
    results_path = OUTPUT_DIR / "ranking_results.json"
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
