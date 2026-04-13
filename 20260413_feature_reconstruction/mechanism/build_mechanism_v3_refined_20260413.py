#!/usr/bin/env python3
"""
Mechanism v3 Refined: Gene alias mapping + feature refinement
═════════════════════════════════════════════════════════════════
Base: v3 PPI features (mechanism_features_v3_20260413.parquet)

Improvements over v3:
  1. Gene alias mapping (13 aliases) → unmapped 70 genes partially recovered
  2. Drop target_diffusion_score (noisy, rank 45-264 in importance)
  3. log1p(ppi_neighbor_disease_score) → variance reduction
  4. has_ppi_feature (0/1) → explicit missing indicator vs zero padding
  5. target_pathway_x_propagation interaction (per-sample)

Output features (4):
  1. ppi_neighbor_disease_score_log1p
  2. pathway_propagation_score
  3. has_ppi_feature
  4. target_pathway_x_propagation

Output: mechanism/mechanism_features_v3_refined_20260413.parquet
        (7730 rows × 6 cols: sample_id, drug_id, 4 features)
"""

import io
import re
import time
from collections import defaultdict
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

# ── Config ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_ROOT = Path(__file__).resolve().parents[1]
MECH_DIR = Path(__file__).resolve().parent

DRUG_TARGET_PATH = REPO_ROOT / "nextflow" / "data" / "drug_target_mapping.parquet"
FINAL_PATH = FEAT_ROOT / "data" / "final_features_20260413.parquet"
V2_PATH = MECH_DIR / "mechanism_features_v2_20260413.parquet"
V3_ORIG_PATH = MECH_DIR / "mechanism_features_v3_20260413.parquet"
OUT_PATH = MECH_DIR / "mechanism_features_v3_refined_20260413.parquet"

BUCKET = "say2-4team"
S3_STRING_LINKS = "curated_date/string/string_links_basic_20260406.parquet"
S3_STRING_INFO = "curated_date/string/string_protein_info_basic_20260406.parquet"
S3_OT_ASSOC = "curated_date/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
S3_OT_TARGET = "curated_date/opentargets/opentargets_target_basic_20260406.parquet"
S3_OT_DISEASE = "curated_date/opentargets/opentargets_disease_basic_20260406.parquet"
S3_MSIGDB = "curated_date/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"

PPI_SCORE_THRESHOLD = 700
BRCA_SCORE_THRESHOLD = 0.1
GENE_RE = re.compile(r"^[A-Z][A-Z0-9]{0,10}$")

# ── Gene Aliases ────────────────────────────────────────────
GENE_ALIASES = {
    "ABL": "ABL1",
    "AKT": "AKT1",
    "ERK1": "MAPK3",
    "ERK2": "MAPK1",
    "MEK1": "MAP2K1",
    "MEK2": "MAP2K2",
    "JNK": "MAPK8",
    "JNK2": "MAPK9",
    "RAF": "RAF1",
    "HSP90": "HSP90AA1",
    "MTOR": "MTOR",
    "VEGFR": "KDR",
    "PDGFR": "PDGFRA",
}


# ── Helpers ─────────────────────────────────────────────────
def read_s3_parquet(key, columns=None):
    print(f"    S3: {key.split('/')[-1]}")
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"       -> {len(df):,} rows x {len(df.columns)} cols")
    return df


def is_gene_symbol(s):
    return bool(GENE_RE.match(str(s)))


# ════════════════════════════════════════════════════════════
#  Data Loading
# ════════════════════════════════════════════════════════════
def load_ppi_graph():
    """STRING PPI graph (score >= 700)."""
    print("\n" + "-" * 60)
    print("  STRING PPI Graph (score >= 700)")
    print("-" * 60)

    df_info = read_s3_parquet(
        S3_STRING_INFO, columns=["string_protein_id", "preferred_name"]
    )
    ensp_to_gene = dict(zip(df_info["string_protein_id"], df_info["preferred_name"]))
    print(f"    ENSP -> gene mapping: {len(ensp_to_gene):,} proteins")

    df_ppi = read_s3_parquet(S3_STRING_LINKS)
    n_total = len(df_ppi)
    df_ppi = df_ppi[df_ppi["combined_score"] >= PPI_SCORE_THRESHOLD].copy()
    print(f"    Score >= {PPI_SCORE_THRESHOLD}: {len(df_ppi):,} / {n_total:,}")

    df_ppi["gene1"] = df_ppi["protein1"].map(ensp_to_gene)
    df_ppi["gene2"] = df_ppi["protein2"].map(ensp_to_gene)
    df_ppi = df_ppi.dropna(subset=["gene1", "gene2"])

    adj = defaultdict(dict)
    for g1, g2, score in zip(
        df_ppi["gene1"].values, df_ppi["gene2"].values,
        df_ppi["combined_score"].values,
    ):
        score = int(score)
        adj[g1][g2] = max(adj[g1].get(g2, 0), score)
        adj[g2][g1] = max(adj[g2].get(g1, 0), score)

    print(f"    Graph: {len(adj):,} nodes, {sum(len(v) for v in adj.values())//2:,} edges")
    return dict(adj)


def load_brca_genes():
    """OpenTargets BRCA gene scores."""
    print("\n" + "-" * 60)
    print("  OpenTargets BRCA genes")
    print("-" * 60)

    df_dis = read_s3_parquet(S3_OT_DISEASE, columns=["id", "name"])
    brca_ids = set(
        df_dis[df_dis["name"].str.contains("breast", case=False, na=False)]["id"]
    )
    print(f"    BRCA disease IDs: {len(brca_ids)}")

    df_tgt = read_s3_parquet(S3_OT_TARGET, columns=["id", "approvedSymbol"])
    ensembl_to_gene = dict(zip(df_tgt["id"], df_tgt["approvedSymbol"]))

    df_assoc = read_s3_parquet(
        S3_OT_ASSOC, columns=["targetId", "diseaseId", "score"]
    )
    df_assoc = df_assoc[df_assoc["diseaseId"].isin(brca_ids)].copy()
    df_assoc["gene_symbol"] = df_assoc["targetId"].map(ensembl_to_gene)
    df_assoc = df_assoc.dropna(subset=["gene_symbol"])

    gene_scores = (
        df_assoc.groupby("gene_symbol")["score"]
        .max()
        .reset_index()
        .rename(columns={"score": "disease_score"})
    )
    gene_score_dict = dict(zip(gene_scores["gene_symbol"], gene_scores["disease_score"]))
    brca_genes = set(
        gene_scores[gene_scores["disease_score"] >= BRCA_SCORE_THRESHOLD]["gene_symbol"]
    )
    print(f"    BRCA genes (score >= {BRCA_SCORE_THRESHOLD}): {len(brca_genes):,}")
    return gene_score_dict, brca_genes


def load_hallmark():
    """MSigDB Hallmark pathways."""
    print("\n" + "-" * 60)
    print("  MSigDB Hallmark pathways")
    print("-" * 60)

    df = read_s3_parquet(
        S3_MSIGDB, columns=["gene_set_name", "gene_symbol", "collection_code"]
    )
    df = df[df["collection_code"] == "H"].copy()

    pw_to_genes = {}
    for pw in sorted(df["gene_set_name"].unique()):
        pw_to_genes[pw] = set(df[df["gene_set_name"] == pw]["gene_symbol"])

    total_genes = len(set().union(*pw_to_genes.values()))
    print(f"    {len(pw_to_genes)} pathways, {total_genes:,} unique genes")
    return pw_to_genes


def load_drug_targets_with_aliases(adj):
    """Load drug targets with gene alias mapping."""
    print("\n" + "-" * 60)
    print("  Drug targets + Gene alias mapping")
    print("-" * 60)

    df = pd.read_parquet(DRUG_TARGET_PATH)
    all_drugs = sorted(df["canonical_drug_id"].unique())

    # Before aliases
    df_pre = df[df["target_gene_symbol"].apply(is_gene_symbol)].copy()
    genes_before = set(df_pre["target_gene_symbol"].unique())
    in_ppi_before = genes_before & set(adj.keys())

    # Apply aliases
    alias_log = []

    def apply_alias(gene):
        if gene in GENE_ALIASES:
            mapped = GENE_ALIASES[gene]
            if mapped != gene:
                alias_log.append((gene, mapped))
            return mapped
        return gene

    df["target_gene_symbol"] = df["target_gene_symbol"].apply(apply_alias)
    df_gene = df[df["target_gene_symbol"].apply(is_gene_symbol)].copy()

    drug_targets = {}
    for drug_id in all_drugs:
        drug_targets[drug_id] = set(
            df_gene.loc[df_gene["canonical_drug_id"] == drug_id, "target_gene_symbol"]
        )

    # After aliases
    genes_after = set(df_gene["target_gene_symbol"].unique())
    in_ppi_after = genes_after & set(adj.keys())
    not_in_ppi = genes_after - set(adj.keys())

    n_with = sum(1 for v in drug_targets.values() if v)
    drugs_with_ppi = sum(
        1 for targets in drug_targets.values()
        if targets and (targets & set(adj.keys()))
    )

    print(f"    {len(all_drugs)} drugs, {n_with} with valid targets")
    print(f"    Aliases applied: {len(set(alias_log))} unique mappings")
    for orig, mapped in sorted(set(alias_log)):
        status = "IN PPI" if mapped in adj else "NOT in PPI"
        print(f"      {orig:>8s} -> {mapped:<12s} [{status}]")
    print(f"    Gene -> PPI: before {len(in_ppi_before)}/{len(genes_before)}"
          f" -> after {len(in_ppi_after)}/{len(genes_after)}")
    print(f"    Still unmapped: {len(not_in_ppi)}")
    if not_in_ppi:
        show = sorted(not_in_ppi)[:15]
        print(f"    Examples: {show}{'...' if len(not_in_ppi) > 15 else ''}")
    print(f"    Drugs with PPI targets: {drugs_with_ppi} / {n_with}")

    return all_drugs, drug_targets, drugs_with_ppi


# ════════════════════════════════════════════════════════════
#  Feature computation (same formulas as v3)
# ════════════════════════════════════════════════════════════
def compute_ppi_neighbor_disease_score(all_drugs, drug_targets, adj,
                                       gene_score_dict, brca_genes):
    """v3 feature 1: PPI 1-hop neighbor disease score."""
    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({"canonical_drug_id": drug_id,
                            "ppi_neighbor_disease_score": 0.0})
            continue

        total = 0.0
        for tgt in targets:
            for neighbor, ppi_score in adj.get(tgt, {}).items():
                if neighbor in brca_genes:
                    total += (ppi_score / 1000.0) * gene_score_dict.get(neighbor, 0.0)

        records.append({"canonical_drug_id": drug_id,
                        "ppi_neighbor_disease_score": round(total / len(targets), 6)})
    return pd.DataFrame(records)


def compute_pathway_propagation_score(all_drugs, drug_targets, adj, pw_to_genes):
    """v3 feature 2: pathway propagation via PPI 1-hop expansion."""
    pw_names = sorted(pw_to_genes.keys())
    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({"canonical_drug_id": drug_id,
                            "pathway_propagation_score": 0.0})
            continue

        gene_pool = set(targets)
        for tgt in targets:
            gene_pool.update(adj.get(tgt, {}).keys())

        ratios = []
        for pw_name in pw_names:
            pw_genes = pw_to_genes[pw_name]
            ratios.append(len(gene_pool & pw_genes) / len(pw_genes) if pw_genes else 0.0)

        records.append({"canonical_drug_id": drug_id,
                        "pathway_propagation_score": round(float(np.mean(ratios)), 6)})
    return pd.DataFrame(records)


# ════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    print("=" * 60)
    print("  Mechanism v3 Refined")
    print("  Gene alias mapping + feature refinement")
    print("=" * 60)

    # ── Load original v3 for comparison ──
    print("\n  Loading original v3 for comparison...")
    df_v3_orig = pd.read_parquet(V3_ORIG_PATH)
    n_orig_nz = int((df_v3_orig["ppi_neighbor_disease_score"].abs() > 1e-8).sum())
    print(f"  Original v3: {len(df_v3_orig)} drugs, {n_orig_nz} non-zero")

    # ── Load S3 data ──
    adj = load_ppi_graph()
    gene_score_dict, brca_genes = load_brca_genes()
    pw_to_genes = load_hallmark()

    # ── Drug targets with aliases ──
    all_drugs, drug_targets, n_ppi_drugs = load_drug_targets_with_aliases(adj)

    # ── Compute features (with aliases applied) ──
    print("\n" + "=" * 60)
    print("  Computing features (with gene aliases)")
    print("=" * 60)

    df_ppi = compute_ppi_neighbor_disease_score(
        all_drugs, drug_targets, adj, gene_score_dict, brca_genes
    )
    df_pw = compute_pathway_propagation_score(
        all_drugs, drug_targets, adj, pw_to_genes
    )

    df_drug = df_ppi.merge(df_pw, on="canonical_drug_id")

    # Per-drug stats (before refinement)
    nz_ppi = int((df_drug["ppi_neighbor_disease_score"].abs() > 1e-8).sum())
    nz_pw = int((df_drug["pathway_propagation_score"].abs() > 1e-8).sum())
    print(f"\n  Per-drug scores (with aliases):")
    print(f"    ppi_neighbor_disease_score: nz={nz_ppi}/295")
    print(f"    pathway_propagation_score:  nz={nz_pw}/295")

    # ── Refinements ──
    print("\n" + "=" * 60)
    print("  Applying refinements")
    print("=" * 60)

    # 1. log1p scale
    df_drug["ppi_neighbor_disease_score_log1p"] = np.log1p(
        df_drug["ppi_neighbor_disease_score"]
    )
    s_log = df_drug["ppi_neighbor_disease_score_log1p"]
    print(f"  [1] log1p(ppi_score): mean={s_log.mean():.4f}, "
          f"std={s_log.std():.4f}, max={s_log.max():.4f}")

    # 2. Missing indicator
    df_drug["has_ppi_feature"] = (
        df_drug["ppi_neighbor_disease_score"].abs() > 1e-8
    ).astype(np.int32)
    h1 = int(df_drug["has_ppi_feature"].sum())
    print(f"  [2] has_ppi_feature: 1={h1}, 0={295 - h1}")

    # ── Coverage comparison ──
    print(f"\n  Coverage comparison:")
    print(f"    Original v3: {n_orig_nz} / 295 ({n_orig_nz/295*100:.1f}%)")
    print(f"    Refined v3:  {h1} / 295 ({h1/295*100:.1f}%)")
    print(f"    Gained:      +{h1 - n_orig_nz} drugs")

    # ── Merge to per-sample ──
    print("\n  Merging to per-sample (7730 rows)...")

    df_final = pd.read_parquet(FINAL_PATH, columns=["sample_id", "canonical_drug_id"])
    print(f"    Sample-drug pairs: {len(df_final):,}")

    df_v2 = pd.read_parquet(V2_PATH, columns=["sample_id", "canonical_drug_id",
                                                "target_x_pathway"])
    print(f"    v2 target_x_pathway loaded: {len(df_v2):,} rows")

    # Merge per-drug features onto sample-drug pairs
    select_cols = ["canonical_drug_id", "ppi_neighbor_disease_score_log1p",
                   "pathway_propagation_score", "has_ppi_feature"]
    df_out = df_final.merge(df_drug[select_cols], on="canonical_drug_id", how="left")
    df_out = df_out.merge(df_v2, on=["sample_id", "canonical_drug_id"], how="left")

    # Fill NaN
    for col in ["ppi_neighbor_disease_score_log1p", "pathway_propagation_score",
                "has_ppi_feature", "target_x_pathway"]:
        df_out[col] = df_out[col].fillna(0.0)
    df_out["has_ppi_feature"] = df_out["has_ppi_feature"].astype(np.int32)

    # 3. Interaction feature
    df_out["target_pathway_x_propagation"] = (
        df_out["target_x_pathway"] * df_out["pathway_propagation_score"]
    )
    print(f"  [3] target_pathway_x_propagation computed")

    # Drop helper column
    df_out = df_out.drop(columns=["target_x_pathway"])

    n_out = len(df_out)
    print(f"    Output rows: {n_out:,} ({'OK' if n_out == 7730 else 'MISMATCH'})")

    # ── Final report ──
    feature_cols = [
        "ppi_neighbor_disease_score_log1p",
        "pathway_propagation_score",
        "has_ppi_feature",
        "target_pathway_x_propagation",
    ]

    print("\n" + "=" * 60)
    print("  Final results")
    print("=" * 60)
    print(f"  Shape: {df_out.shape}")
    print(f"\n  {'Feature':<38s}  {'mean':>8s}  {'std':>8s}  "
          f"{'min':>8s}  {'max':>8s}  {'nonzero':>10s}")
    print("  " + "-" * 80)
    for col in feature_cols:
        s = df_out[col]
        nz = int((s.abs() > 1e-8).sum())
        print(f"  {col:<38s}  {s.mean():8.4f}  {s.std():8.4f}  "
              f"{s.min():8.4f}  {s.max():8.4f}  {nz:>5d}/{len(s)}")

    # has_ppi_feature per-sample distribution
    h0 = int((df_out["has_ppi_feature"] == 0).sum())
    h1s = int((df_out["has_ppi_feature"] == 1).sum())
    print(f"\n  has_ppi_feature distribution (per-sample):")
    print(f"    0 = {h0:,} ({h0/n_out*100:.1f}%)")
    print(f"    1 = {h1s:,} ({h1s/n_out*100:.1f}%)")

    # ── Save ──
    df_out.to_parquet(OUT_PATH, index=False)
    print(f"\n  Saved: {OUT_PATH}")
    print(f"  Size: {OUT_PATH.stat().st_size / 1024:.0f} KB")
    print(f"  Time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
