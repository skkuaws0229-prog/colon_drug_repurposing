#!/usr/bin/env python3
"""
Target-based Feature Engineering (20260413)

데이터 소스:
  - S3 features.parquet → CRISPR gene scores
  - S3 pair_features_newfe_v2.parquet → sample_id, canonical_drug_id
  - 로컬 drug_target_mapping.parquet → drug-target gene 매핑
  - 로컬 pathway_features_hallmark_20260413.parquet → 50 pathway scores

생성 feature:
  1. target_crispr_mean/std: drug target gene들의 CRISPR score 평균/std (sample별)
  2. target_pathway_activity: target gene 속한 pathway score 평균 (sample별)
  3. target_pathway_overlap_*: target gene과 50 pathway 간 overlap score (50개)

출력: data/target_features_20260413.parquet
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import gseapy as gp

# ── Paths ──
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/features/features.parquet"
PAIR_FEATURES_URI = f"{S3_BASE}/fe_output/20260408_fe_v1/pair_features/pair_features_newfe_v2.parquet"

CRISPR_PREFIX = "sample__crispr__"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
DRUG_TARGET_PATH = REPO_ROOT / "nextflow" / "data" / "drug_target_mapping.parquet"
PATHWAY_FEATURES_PATH = PROJECT_ROOT / "data" / "pathway_features_hallmark_20260413.parquet"

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_PATH = DATA_DIR / "target_features_20260413.parquet"


def load_drug_target_mapping():
    """drug_target_mapping 로딩 + gene-like symbol만 필터링."""
    print("  Loading drug_target_mapping...")
    dtm = pd.read_parquet(DRUG_TARGET_PATH)
    print(f"  Raw: {dtm.shape[0]} rows, {dtm['canonical_drug_id'].nunique()} drugs")

    # mechanism label 제거: 공백 포함 or 소문자 포함 → mechanism
    # gene symbol: 대문자+숫자+하이픈만 (BCL-XL, BRAF, TP53 등)
    def is_gene_symbol(s):
        if pd.isna(s) or s == "<NA>":
            return False
        if " " in s:
            return False
        # 전부 대문자+숫자+하이픈이면 gene
        return all(c.isupper() or c.isdigit() or c == "-" for c in s)

    mask = dtm["target_gene_symbol"].apply(is_gene_symbol)
    dtm_genes = dtm[mask].copy()

    n_mech = (~mask).sum()
    print(f"  Gene symbols: {mask.sum()} rows ({dtm_genes['target_gene_symbol'].nunique()} unique)")
    print(f"  Mechanism labels (excluded): {n_mech} rows")
    print(f"  Drugs with gene targets: {dtm_genes['canonical_drug_id'].nunique()}")

    return dtm_genes


def main():
    print("=" * 70)
    print("  Build Target Features (20260413)")
    print("=" * 70)

    # ── 1. Load drug-target mapping ──
    print("\n[1] Drug-target mapping")
    dtm = load_drug_target_mapping()

    # drug → set of target genes
    drug_targets = dtm.groupby("canonical_drug_id")["target_gene_symbol"].apply(set).to_dict()

    # ── 2. Load CRISPR features ──
    print(f"\n[2] Loading CRISPR features from S3...")
    t0 = time.time()
    features = pd.read_parquet(FEATURES_URI)
    pair_features = pd.read_parquet(PAIR_FEATURES_URI)

    # Merge to get (sample_id, canonical_drug_id) pairs
    merged = features.merge(pair_features, on=["sample_id", "canonical_drug_id"], how="inner")

    # CRISPR columns
    crispr_cols = sorted([c for c in merged.columns if c.startswith(CRISPR_PREFIX)])
    gene_to_col = {col.replace(CRISPR_PREFIX, ""): col for col in crispr_cols}
    available_genes = set(gene_to_col.keys())
    dt = time.time() - t0
    print(f"  Merged: {merged.shape[0]:,} rows ({dt:.1f}s)")
    print(f"  CRISPR genes: {len(available_genes):,}")

    # Target gene → CRISPR match check
    all_target_genes = set()
    for genes in drug_targets.values():
        all_target_genes.update(genes)
    matched_targets = all_target_genes & available_genes
    print(f"  Target genes (gene-like): {len(all_target_genes)}")
    print(f"  Matched in CRISPR: {len(matched_targets)} ({100*len(matched_targets)/len(all_target_genes):.1f}%)")

    # ── 3. Load Hallmark pathway gene sets + pathway features ──
    print(f"\n[3] Loading Hallmark pathways...")
    hallmark = gp.get_library("MSigDB_Hallmark_2020", organism="Human")
    pathway_features = pd.read_parquet(PATHWAY_FEATURES_PATH)
    pathway_names = [c for c in pathway_features.columns
                     if c not in ("sample_id", "canonical_drug_id")]
    print(f"  Pathways: {len(pathway_names)}")
    print(f"  Pathway features shape: {pathway_features.shape}")

    # pathway_name → gene set
    pathway_gene_sets = {name: set(hallmark[name]) for name in hallmark}

    # ── 4. Compute features ──
    print(f"\n[4] Computing target features for {merged.shape[0]:,} rows...")
    t0 = time.time()

    sample_ids = merged["sample_id"].values
    drug_ids = merged["canonical_drug_id"].values

    # Pre-extract CRISPR matrix
    crispr_matrix = merged[crispr_cols].fillna(0.0).values.astype(np.float32)
    gene_names = [col.replace(CRISPR_PREFIX, "") for col in crispr_cols]
    gene_idx_map = {g: i for i, g in enumerate(gene_names)}

    # Pre-extract pathway scores (aligned with merged index)
    pw_merged = merged[["sample_id", "canonical_drug_id"]].merge(
        pathway_features, on=["sample_id", "canonical_drug_id"], how="left",
    )
    pw_matrix = pw_merged[pathway_names].fillna(0.0).values.astype(np.float32)

    # Pre-compute: drug → CRISPR gene indices
    drug_crispr_idx = {}
    for drug_id, targets in drug_targets.items():
        idx = [gene_idx_map[g] for g in targets if g in gene_idx_map]
        drug_crispr_idx[str(drug_id)] = idx

    # Pre-compute: drug → pathway overlap ratios (50-dim vector)
    drug_pathway_overlap = {}
    for drug_id, targets in drug_targets.items():
        overlaps = []
        for pw_name in pathway_names:
            if pw_name in pathway_gene_sets:
                pw_genes = pathway_gene_sets[pw_name]
                n_overlap = len(targets & pw_genes)
                ratio = n_overlap / len(targets) if targets else 0.0
            else:
                ratio = 0.0
            overlaps.append(ratio)
        drug_pathway_overlap[str(drug_id)] = np.array(overlaps, dtype=np.float32)

    # Feature arrays
    n = merged.shape[0]
    target_crispr_mean = np.zeros(n, dtype=np.float32)
    target_crispr_std = np.zeros(n, dtype=np.float32)
    target_pathway_activity = np.zeros(n, dtype=np.float32)
    target_pw_overlap = np.zeros((n, len(pathway_names)), dtype=np.float32)

    for i in range(n):
        drug_str = str(drug_ids[i])
        # Feature 1: target CRISPR score mean/std
        idx = drug_crispr_idx.get(drug_str, [])
        if idx:
            vals = crispr_matrix[i, idx]
            target_crispr_mean[i] = vals.mean()
            target_crispr_std[i] = vals.std() if len(vals) > 1 else 0.0

        # Feature 2: target pathway activity
        overlap_vec = drug_pathway_overlap.get(drug_str)
        if overlap_vec is not None:
            active_mask = overlap_vec > 0
            if active_mask.any():
                target_pathway_activity[i] = pw_matrix[i, active_mask].mean()

        # Feature 3: target-pathway overlap scores
        if overlap_vec is not None:
            target_pw_overlap[i] = overlap_vec

    dt = time.time() - t0
    print(f"  Computed in {dt:.1f}s")

    # ── 5. Build result DataFrame ──
    print(f"\n[5] Building output DataFrame...")
    result = pd.DataFrame({
        "sample_id": sample_ids,
        "canonical_drug_id": drug_ids,
        "target_crispr_mean": target_crispr_mean,
        "target_crispr_std": target_crispr_std,
        "target_pathway_activity": target_pathway_activity,
    })

    # Add 50 pathway overlap columns
    for j, pw_name in enumerate(pathway_names):
        result[f"target_pw_overlap_{pw_name}"] = target_pw_overlap[:, j]

    n_features = result.shape[1] - 2  # exclude id cols
    print(f"  Output shape: {result.shape}")
    print(f"  Feature columns: {n_features}")
    print(f"    - target_crispr_mean/std: 2")
    print(f"    - target_pathway_activity: 1")
    print(f"    - target_pw_overlap_*: {len(pathway_names)}")

    # Stats
    feat_cols = [c for c in result.columns if c not in ("sample_id", "canonical_drug_id")]
    print(f"\n  Feature stats:")
    print(f"  {'Feature':40s} {'mean':>8s} {'std':>8s} {'min':>8s} {'max':>8s} {'nz%':>6s}")
    print(f"  {'-'*75}")
    for col in feat_cols[:5]:
        vals = result[col]
        nz = (vals != 0).mean() * 100
        print(f"  {col[:40]:40s} {vals.mean():>8.4f} {vals.std():>8.4f} "
              f"{vals.min():>8.4f} {vals.max():>8.4f} {nz:>5.1f}%")
    if len(feat_cols) > 5:
        # overlap columns summary
        overlap_cols = [c for c in feat_cols if c.startswith("target_pw_overlap_")]
        overlap_vals = result[overlap_cols].values
        nz_per_col = (overlap_vals != 0).mean(axis=0)
        print(f"  {'(overlap 50 cols summary)':40s} "
              f"{overlap_vals.mean():>8.4f} {overlap_vals.std():>8.4f} "
              f"{overlap_vals.min():>8.4f} {overlap_vals.max():>8.4f} "
              f"{(overlap_vals != 0).mean()*100:>5.1f}%")
        n_active = (nz_per_col > 0).sum()
        print(f"  Active overlap pathways (any nonzero): {n_active}/{len(overlap_cols)}")

    # ── 6. Save ──
    result.to_parquet(OUT_PATH, index=False)
    print(f"\n  Saved: {OUT_PATH}")
    print(f"  Size: {OUT_PATH.stat().st_size / 1024:.0f} KB")

    print(f"\n{'='*70}")
    print(f"  Done.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
