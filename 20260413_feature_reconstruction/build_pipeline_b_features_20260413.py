#!/usr/bin/env python3
"""
Pipeline B Feature Builder
═══════════════════════════════════════════════════════════════
  약물 화학 구조만으로 구성된 feature set.

  포함:
    - drug_morgan_*   (2,048개) : Morgan Fingerprint
    - drug_desc_*     (9개)     : 물리화학적 기술자
    - drug__has_smiles (1개)    : SMILES 존재 여부
    - drug_has_valid_smiles (1개) : 유효 SMILES 여부
    합계: 2,059개 feature

  제외 (전부):
    - CRISPR / pathway / LINCS
    - target gene 관련 전부
    - mechanism v1/v2/v3 전부

  입력: data/final_features_20260413.parquet
  출력: data/pipeline_b_features_20260413.parquet
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import time
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_PATH = PROJECT_ROOT / "data" / "final_features_20260413.parquet"
OUTPUT_PATH = PROJECT_ROOT / "data" / "pipeline_b_features_20260413.parquet"

# Pipeline B: 약물 화학 구조 feature만
DRUG_PREFIXES = (
    "drug_morgan_",
    "drug_desc_",
)
DRUG_EXACT = {
    "drug__has_smiles",
    "drug_has_valid_smiles",
}
# ID + label columns to keep
META_COLS = {"sample_id", "canonical_drug_id", "ln_IC50"}


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Pipeline B Feature Builder")
    print("  약물 화학 구조 only (Morgan FP + Descriptors)")
    print("=" * 70)

    # 1. Load
    print(f"\n  Loading: {INPUT_PATH.name}")
    df = pd.read_parquet(INPUT_PATH)
    print(f"    Shape: {df.shape}")
    print(f"    Columns: {len(df.columns)}")

    # 2. Select drug-structure columns
    print(f"\n  Selecting drug-structure features...")
    all_cols = list(df.columns)

    # Meta columns
    meta = [c for c in all_cols if c in META_COLS]

    # Drug feature columns
    drug_features = []
    for c in all_cols:
        if any(c.startswith(p) for p in DRUG_PREFIXES):
            drug_features.append(c)
        elif c in DRUG_EXACT:
            drug_features.append(c)

    # Count by type
    n_morgan = sum(1 for c in drug_features if c.startswith("drug_morgan_"))
    n_desc = sum(1 for c in drug_features if c.startswith("drug_desc_"))
    n_has = sum(1 for c in drug_features if c in DRUG_EXACT)

    print(f"    drug_morgan_*: {n_morgan}")
    print(f"    drug_desc_*:   {n_desc}")
    print(f"    drug flags:    {n_has}")
    print(f"    ──────────────")
    print(f"    Feature 합계:  {len(drug_features)}")
    print(f"    Meta columns:  {meta}")

    # Validate
    expected = 2059
    if len(drug_features) != expected:
        print(f"\n  *** WARNING: Expected {expected} features, got {len(drug_features)} ***")
        # List what we found vs expected
        if n_morgan != 2048:
            print(f"      Expected 2048 morgan, got {n_morgan}")
        if n_desc != 9:
            print(f"      Expected 9 desc, got {n_desc}")
        if n_has != 2:
            print(f"      Expected 2 flags, got {n_has}")
            for name in DRUG_EXACT:
                if name not in drug_features:
                    print(f"      Missing: {name}")
    else:
        print(f"\n  ✓ Feature count matches expected: {expected}")

    # 3. Build output
    selected_cols = meta + drug_features
    df_out = df[selected_cols].copy()

    print(f"\n  Output shape: {df_out.shape}")
    print(f"    Rows (samples): {len(df_out):,}")
    print(f"    Cols (meta + features): {len(selected_cols)}")
    print(f"    Features only: {len(drug_features)}")

    # 4. Save
    print(f"\n  Saving: {OUTPUT_PATH.name}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_parquet(OUTPUT_PATH, index=False, compression="snappy")

    file_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"    Size: {file_mb:.1f} MB")

    # 5. Verify
    print(f"\n  Verifying saved file...")
    df_check = pd.read_parquet(OUTPUT_PATH)
    assert df_check.shape == df_out.shape, f"Shape mismatch: {df_check.shape} vs {df_out.shape}"
    print(f"    Shape OK: {df_check.shape}")

    # Show excluded categories
    all_feature_cols = [c for c in all_cols if c not in META_COLS]
    excluded = [c for c in all_feature_cols if c not in drug_features]
    excluded_prefixes = {}
    for c in excluded:
        prefix = c.split("_")[0] if "_" in c else c
        excluded_prefixes[prefix] = excluded_prefixes.get(prefix, 0) + 1

    print(f"\n  제외된 feature 카테고리:")
    for prefix, count in sorted(excluded_prefixes.items(), key=lambda x: -x[1]):
        print(f"    {prefix}_*: {count}개")
    print(f"    제외 합계: {len(excluded)}개")

    dt = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  Pipeline B Feature 완료")
    print(f"  Features: {len(drug_features)} (drug-structure only)")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Size: {file_mb:.1f} MB")
    print(f"  Time: {dt:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
