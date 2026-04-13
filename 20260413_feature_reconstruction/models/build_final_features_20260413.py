#!/usr/bin/env python3
"""
Final Feature Integration (20260413)

CRISPR raw 18,310개 제거 → Pathway 50 + Target 53으로 대체.
Drug modality (Morgan FP, LINCS, Drug Desc 등)는 그대로 유지.

입력:
  - S3 features.parquet + pair_features_newfe_v2.parquet
    → drug_morgan_* (2048), lincs_* (5), drug_desc_* (9),
      drug__has_smiles (1), drug_has_valid_smiles (1)
  - 로컬 pathway_features_hallmark_20260413.parquet (50)
  - 로컬 target_features_20260413.parquet (53)

출력: data/final_features_20260413.parquet
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/features.parquet"
PAIR_FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/pair_features/pair_features_newfe_v2.parquet"
LABELS_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/labels.parquet"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PATHWAY_PATH = DATA_DIR / "pathway_features_hallmark_20260413.parquet"
TARGET_PATH = DATA_DIR / "target_features_20260413.parquet"
OUT_PATH = DATA_DIR / "final_features_20260413.parquet"

# S3에서 추출할 feature prefix/이름
KEEP_PREFIXES = ["drug_morgan_", "lincs_", "drug_desc_"]
KEEP_EXACT = ["drug__has_smiles", "drug_has_valid_smiles"]
ID_COLS = ["sample_id", "canonical_drug_id"]


def main():
    print("=" * 70)
    print("  Build Final Features (20260413)")
    print("  CRISPR raw → Pathway(50) + Target(53) 대체")
    print("=" * 70)

    # ── 1. S3 feature 로딩 + 필요 컬럼만 추출 ──
    print("\n[1] Loading S3 features...")
    t0 = time.time()
    features = pd.read_parquet(FEATURES_URI)
    pair_features = pd.read_parquet(PAIR_FEATURES_URI)

    merged = features.merge(pair_features, on=ID_COLS, how="inner")
    dt = time.time() - t0
    print(f"  Merged: {merged.shape[0]:,} rows x {merged.shape[1]:,} cols ({dt:.1f}s)")

    # 추출 대상 컬럼 선별
    all_cols = merged.columns.tolist()
    keep_cols = []
    group_counts = {}

    for prefix in KEEP_PREFIXES:
        cols = sorted([c for c in all_cols if c.startswith(prefix)])
        keep_cols.extend(cols)
        group_counts[prefix.rstrip("_")] = len(cols)

    for col_name in KEEP_EXACT:
        if col_name in all_cols:
            keep_cols.append(col_name)
            group_counts[col_name] = 1
        else:
            print(f"  WARNING: {col_name} not found in S3 data")

    s3_df = merged[ID_COLS + keep_cols].copy()
    n_s3 = len(keep_cols)
    print(f"  Extracted from S3: {n_s3} features")
    for name, cnt in group_counts.items():
        print(f"    {name}: {cnt}")

    # ── 2. Pathway features 로딩 ──
    print(f"\n[2] Loading pathway features...")
    pw = pd.read_parquet(PATHWAY_PATH)
    pw_cols = [c for c in pw.columns if c not in ID_COLS]
    n_pw = len(pw_cols)
    print(f"  Shape: {pw.shape}  ({n_pw} features)")

    # ── 3. Target features 로딩 ──
    print(f"\n[3] Loading target features...")
    tg = pd.read_parquet(TARGET_PATH)
    tg_cols = [c for c in tg.columns if c not in ID_COLS]
    n_tg = len(tg_cols)
    print(f"  Shape: {tg.shape}  ({n_tg} features)")

    # ── 4. Labels 로딩 ──
    print(f"\n[4] Loading labels...")
    labels = pd.read_parquet(LABELS_URI)
    label_cols = [c for c in labels.columns if c not in ID_COLS]
    print(f"  Shape: {labels.shape}  ({label_cols})")

    # ── 5. 병합 ──
    print(f"\n[5] Merging on {ID_COLS}...")
    t0 = time.time()
    result = s3_df.merge(pw, on=ID_COLS, how="inner")
    n_after_pw = result.shape[0]

    result = result.merge(tg, on=ID_COLS, how="inner")
    n_after_tg = result.shape[0]

    result = result.merge(labels, on=ID_COLS, how="inner")
    n_final = result.shape[0]

    dt = time.time() - t0
    print(f"  After pathway merge: {n_after_pw:,} rows")
    print(f"  After target merge:  {n_after_tg:,} rows")
    print(f"  After labels merge:  {n_final:,} rows ({dt:.1f}s)")

    if n_final != merged.shape[0]:
        print(f"  WARNING: Row count changed ({merged.shape[0]:,} → {n_final:,})")

    # ── 6. Feature 그룹 요약 ──
    feat_cols = [c for c in result.columns if c not in ID_COLS + label_cols]
    n_total = len(feat_cols)

    print(f"\n[6] Feature group summary")
    print(f"  {'Group':30s} {'Count':>7s}")
    print(f"  {'-'*40}")
    print(f"  {'drug_morgan_*':30s} {group_counts.get('drug_morgan', 0):>7,}")
    print(f"  {'lincs_*':30s} {group_counts.get('lincs', 0):>7,}")
    print(f"  {'drug_desc_*':30s} {group_counts.get('drug_desc', 0):>7,}")
    print(f"  {'drug__has_smiles':30s} {group_counts.get('drug__has_smiles', 0):>7,}")
    print(f"  {'drug_has_valid_smiles':30s} {group_counts.get('drug_has_valid_smiles', 0):>7,}")
    print(f"  {'pathway_hallmark (NEW)':30s} {n_pw:>7,}")
    print(f"  {'target_features (NEW)':30s} {n_tg:>7,}")
    print(f"  {'-'*40}")
    print(f"  {'TOTAL features':30s} {n_total:>7,}")
    print(f"  {'Label columns':30s} {len(label_cols):>7,}")

    # ── 7. 기초 통계 ──
    print(f"\n[7] Basic statistics")
    print(f"  Rows: {n_final:,}")
    print(f"  Feature cols: {n_total}")
    print(f"  Label cols: {label_cols}")

    # Null check
    null_counts = result[feat_cols].isnull().sum()
    n_null_cols = (null_counts > 0).sum()
    print(f"\n  Null check:")
    print(f"    Columns with nulls: {n_null_cols} / {n_total}")
    if n_null_cols > 0:
        print(f"    {'Column':40s} {'Null Count':>10s} {'Null %':>8s}")
        for col in null_counts[null_counts > 0].index[:10]:
            cnt = null_counts[col]
            pct = 100 * cnt / n_final
            print(f"    {col[:40]:40s} {cnt:>10,} {pct:>7.1f}%")
        if n_null_cols > 10:
            print(f"    ... ({n_null_cols - 10} more)")

    # Feature stats by group
    print(f"\n  Feature stats (sample):")
    print(f"  {'Column':40s} {'mean':>10s} {'std':>10s} {'min':>10s} {'max':>10s}")
    print(f"  {'-'*85}")

    sample_cols = (
        keep_cols[:3]
        + pw_cols[:2]
        + tg_cols[:3]
    )
    for col in sample_cols:
        vals = result[col].dropna()
        print(f"  {col[:40]:40s} {vals.mean():>10.4f} {vals.std():>10.4f} "
              f"{vals.min():>10.4f} {vals.max():>10.4f}")

    # ── 8. 저장 ──
    print(f"\n[8] Saving...")
    result.to_parquet(OUT_PATH, index=False)
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"  Path: {OUT_PATH}")
    print(f"  Size: {size_kb:,.0f} KB")
    print(f"  Shape: {result.shape}")

    # ── 비교 ──
    print(f"\n[9] Before vs After comparison")
    print(f"  {'':25s} {'Before':>10s} {'After':>10s} {'Change':>10s}")
    print(f"  {'-'*58}")
    orig_feat = merged.shape[1] - 2  # exclude ID cols
    print(f"  {'Features':25s} {orig_feat:>10,} {n_total:>10,} {n_total - orig_feat:>+10,}")
    print(f"  {'  CRISPR raw':25s} {'18,310':>10s} {'0':>10s} {'-18,310':>10s}")
    print(f"  {'  Pathway (new)':25s} {'0':>10s} {n_pw:>10,} {f'+{n_pw}':>10s}")
    print(f"  {'  Target (new)':25s} {'0':>10s} {n_tg:>10,} {f'+{n_tg}':>10s}")
    print(f"  {'  Drug modality':25s} {n_s3:>10,} {n_s3:>10,} {'0':>10s}")
    print(f"  {'Rows':25s} {merged.shape[0]:>10,} {n_final:>10,} {'':>10s}")

    print(f"\n{'='*70}")
    print(f"  Done.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
