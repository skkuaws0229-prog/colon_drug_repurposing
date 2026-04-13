#!/usr/bin/env python3
"""
CRISPR gene-level → Pathway score 변환
- MSigDB Hallmark 50 gene sets (gseapy)
- 각 pathway: 해당 gene들의 CRISPR score 평균
- 출력: data/pathway_features_hallmark_20260413.parquet
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── S3 paths (train_ensemble.py와 동일) ──
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/features.parquet"

CRISPR_PREFIX = "sample__crispr__"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

OUT_PATH = DATA_DIR / "pathway_features_hallmark_20260413.parquet"


def load_hallmark_gene_sets():
    """MSigDB Hallmark 50 gene sets를 gseapy로 로딩."""
    import gseapy as gp

    print("  Loading MSigDB Hallmark gene sets via gseapy...")
    hallmark = gp.get_library("MSigDB_Hallmark_2020", organism="Human")

    print(f"  Loaded: {len(hallmark)} pathways")
    for name in sorted(hallmark.keys())[:5]:
        print(f"    {name}: {len(hallmark[name])} genes")
    print(f"    ... ({len(hallmark) - 5} more)")

    return hallmark


def main():
    print("=" * 70)
    print("  Build Pathway Features (Hallmark 50)")
    print("=" * 70)

    # ── 1. Load Hallmark gene sets ──
    print("\n[1] MSigDB Hallmark gene sets")
    hallmark = load_hallmark_gene_sets()

    # ── 2. Load CRISPR features from S3 ──
    print(f"\n[2] Loading CRISPR features from S3...")
    t0 = time.time()
    features = pd.read_parquet(FEATURES_URI)

    # sample_id + canonical_drug_id를 index로 보존
    id_cols = ["sample_id", "canonical_drug_id"]
    ids = features[id_cols].copy()

    # CRISPR 컬럼만 추출
    crispr_cols = sorted([c for c in features.columns if c.startswith(CRISPR_PREFIX)])
    crispr_df = features[crispr_cols].fillna(0.0)

    dt = time.time() - t0
    print(f"  Loaded: {crispr_df.shape[0]:,} rows x {crispr_df.shape[1]:,} CRISPR cols ({dt:.1f}s)")

    # gene symbol 추출: "sample__crispr__TP53" → "TP53"
    gene_map = {col: col.replace(CRISPR_PREFIX, "") for col in crispr_cols}
    available_genes = set(gene_map.values())
    print(f"  Available CRISPR genes: {len(available_genes):,}")

    # ── 3. Pathway score 계산 ──
    print(f"\n[3] Computing pathway scores...")
    pathway_scores = {}
    stats = []

    for pathway_name, gene_list in sorted(hallmark.items()):
        # Hallmark gene set과 CRISPR gene 매칭
        matched_genes = [g for g in gene_list if g in available_genes]
        n_total = len(gene_list)
        n_matched = len(matched_genes)

        if n_matched == 0:
            stats.append({
                "pathway": pathway_name,
                "total_genes": n_total,
                "matched_genes": 0,
                "match_rate": 0.0,
                "status": "SKIP",
            })
            continue

        # 매칭된 gene들의 CRISPR 컬럼명 복원
        matched_cols = [f"{CRISPR_PREFIX}{g}" for g in matched_genes]

        # pathway score = 해당 gene들의 평균
        pathway_scores[pathway_name] = crispr_df[matched_cols].mean(axis=1).values

        match_rate = n_matched / n_total
        stats.append({
            "pathway": pathway_name,
            "total_genes": n_total,
            "matched_genes": n_matched,
            "match_rate": match_rate,
            "status": "OK" if match_rate >= 0.5 else "LOW",
        })

    # ── 4. 결과 출력 ──
    stats_df = pd.DataFrame(stats)
    n_ok = (stats_df["status"] == "OK").sum()
    n_low = (stats_df["status"] == "LOW").sum()
    n_skip = (stats_df["status"] == "SKIP").sum()

    print(f"\n  {'Pathway':50s} {'Total':>6s} {'Matched':>8s} {'Rate':>6s} {'Status':>6s}")
    print(f"  {'-'*80}")
    for _, row in stats_df.iterrows():
        print(f"  {row['pathway']:50s} {row['total_genes']:>6d} {row['matched_genes']:>8d} "
              f"{row['match_rate']:>5.1%} {row['status']:>6s}")

    print(f"\n  Summary:")
    print(f"    OK (>=50% match)  : {n_ok}")
    print(f"    LOW (<50% match)  : {n_low}")
    print(f"    SKIP (0 match)    : {n_skip}")
    print(f"    Total pathways    : {len(stats_df)}")
    print(f"    Used as features  : {len(pathway_scores)}")

    # ── 5. DataFrame 생성 + 저장 ──
    print(f"\n[4] Building output DataFrame...")
    pathway_df = pd.DataFrame(pathway_scores)
    result = pd.concat([ids.reset_index(drop=True), pathway_df], axis=1)

    print(f"  Output shape: {result.shape}")
    print(f"  Columns: {id_cols} + {len(pathway_scores)} pathway scores")
    print(f"  Sample pathway stats:")
    print(f"    {'':30s} {'mean':>8s} {'std':>8s} {'min':>8s} {'max':>8s}")
    for col in list(pathway_scores.keys())[:5]:
        vals = pathway_df[col]
        print(f"    {col[:30]:30s} {vals.mean():>8.4f} {vals.std():>8.4f} "
              f"{vals.min():>8.4f} {vals.max():>8.4f}")

    result.to_parquet(OUT_PATH, index=False)
    print(f"\n  Saved: {OUT_PATH}")
    print(f"  Size: {OUT_PATH.stat().st_size / 1024:.0f} KB")

    print(f"\n{'='*70}")
    print(f"  Done.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
