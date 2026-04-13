#!/usr/bin/env python3
"""
Mechanism Engine v3: PPI-based features (non-Neo4j)
══════════════════════════════════════════════════════
STRING PPI graph + OpenTargets + MSigDB → 3 graph-propagation features

Data sources (S3 direct):
  1. STRING links          (combined_score >= 700, high confidence)
  2. STRING protein_info   (ENSP → gene symbol via preferred_name)
  3. OpenTargets            (BRCA gene scores, score >= 0.1)
  4. MSigDB Hallmark        (50 gene sets)
  5. drug_target_mapping    (local, nextflow/data/)

Features (per-drug, 295 rows):
  1. ppi_neighbor_disease_score
     = mean over targets of Σ((ppi_score/1000) × disease_score)
       for BRCA-overlapping PPI 1-hop neighbors

  2. pathway_propagation_score
     = mean of 50 Hallmark overlap_ratios
       gene_pool = targets ∪ PPI 1-hop neighbors

  3. target_diffusion_score
     = mean over targets of Σ(1/(shortest_path+1)) to BRCA genes
       BFS max 3-hop, unreachable → 0

Output: mechanism/mechanism_features_v3_20260413.parquet
"""

import io
import re
import time
from collections import defaultdict, deque
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MECH_DIR = Path(__file__).resolve().parent
DRUG_TARGET_PATH = PROJECT_ROOT / "nextflow" / "data" / "drug_target_mapping.parquet"
OUT_PATH = MECH_DIR / "mechanism_features_v3_20260413.parquet"

BUCKET = "say2-4team"
S3_STRING_LINKS = "curated_date/string/string_links_basic_20260406.parquet"
S3_STRING_INFO = "curated_date/string/string_protein_info_basic_20260406.parquet"
S3_OT_ASSOC = "curated_date/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
S3_OT_TARGET = "curated_date/opentargets/opentargets_target_basic_20260406.parquet"
S3_OT_DISEASE = "curated_date/opentargets/opentargets_disease_basic_20260406.parquet"
S3_MSIGDB = "curated_date/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"

PPI_SCORE_THRESHOLD = 700
BRCA_SCORE_THRESHOLD = 0.1
MAX_HOPS = 3
GENE_RE = re.compile(r"^[A-Z][A-Z0-9]{0,10}$")


# ── Helpers ───────────────────────────────────────────────
def read_s3_parquet(key, columns=None):
    print(f"    S3: {key.split('/')[-1]}")
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"       → {len(df):,} rows × {len(df.columns)} cols")
    return df


def is_gene_symbol(s):
    return bool(GENE_RE.match(str(s)))


# ════════════════════════════════════════════════════════════
#  Data Loading
# ════════════════════════════════════════════════════════════
def load_ppi_graph():
    """Load STRING PPI, filter >= 700, map ENSP → gene symbol, build adjacency."""
    print("\n" + "─" * 60)
    print("  STRING PPI Graph 구성 (score >= 700)")
    print("─" * 60)

    # ENSP → gene symbol (preferred_name)
    df_info = read_s3_parquet(
        S3_STRING_INFO, columns=["string_protein_id", "preferred_name"]
    )
    ensp_to_gene = dict(zip(df_info["string_protein_id"], df_info["preferred_name"]))
    print(f"    ENSP → gene mapping: {len(ensp_to_gene):,} proteins")

    # PPI links
    df_ppi = read_s3_parquet(S3_STRING_LINKS)
    n_total = len(df_ppi)
    df_ppi = df_ppi[df_ppi["combined_score"] >= PPI_SCORE_THRESHOLD].copy()
    print(f"    Score >= {PPI_SCORE_THRESHOLD}: {len(df_ppi):,} / {n_total:,} "
          f"({len(df_ppi)/n_total*100:.1f}%)")

    # Map to gene symbols
    df_ppi["gene1"] = df_ppi["protein1"].map(ensp_to_gene)
    df_ppi["gene2"] = df_ppi["protein2"].map(ensp_to_gene)
    n_before = len(df_ppi)
    df_ppi = df_ppi.dropna(subset=["gene1", "gene2"])
    print(f"    Gene symbol 매핑 후: {len(df_ppi):,} / {n_before:,}")

    # Build adjacency: gene → {neighbor: max_score}
    adj = defaultdict(dict)
    for g1, g2, score in zip(
        df_ppi["gene1"].values, df_ppi["gene2"].values, df_ppi["combined_score"].values
    ):
        score = int(score)
        adj[g1][g2] = max(adj[g1].get(g2, 0), score)
        adj[g2][g1] = max(adj[g2].get(g1, 0), score)

    n_nodes = len(adj)
    n_edges = sum(len(v) for v in adj.values()) // 2
    print(f"    Graph: {n_nodes:,} nodes, {n_edges:,} edges")

    return dict(adj)


def load_brca_genes():
    """Load OpenTargets BRCA gene scores (score >= 0.1)."""
    print("\n" + "─" * 60)
    print("  OpenTargets BRCA gene scores")
    print("─" * 60)

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
    gene_score_dict = dict(
        zip(gene_scores["gene_symbol"], gene_scores["disease_score"])
    )

    brca_genes = set(
        gene_scores[
            gene_scores["disease_score"] >= BRCA_SCORE_THRESHOLD
        ]["gene_symbol"]
    )
    print(f"    BRCA genes (score >= {BRCA_SCORE_THRESHOLD}): {len(brca_genes):,}")
    return gene_score_dict, brca_genes


def load_hallmark():
    """Load MSigDB Hallmark pathway gene sets."""
    print("\n" + "─" * 60)
    print("  MSigDB Hallmark pathways")
    print("─" * 60)

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


def load_drug_targets():
    """Load drug_target_mapping, filter valid gene symbols."""
    print("\n" + "─" * 60)
    print("  Drug target mapping")
    print("─" * 60)

    df = pd.read_parquet(DRUG_TARGET_PATH)
    all_drugs = sorted(df["canonical_drug_id"].unique())
    df_gene = df[df["target_gene_symbol"].apply(is_gene_symbol)].copy()

    drug_targets = {}
    for drug_id in all_drugs:
        drug_targets[drug_id] = set(
            df_gene.loc[df_gene["canonical_drug_id"] == drug_id, "target_gene_symbol"]
        )

    n_with = sum(1 for v in drug_targets.values() if v)
    n_genes = df_gene["target_gene_symbol"].nunique()
    print(f"    {len(all_drugs)} drugs, {n_with} with valid gene targets")
    print(f"    {n_genes} unique gene symbols")
    return all_drugs, drug_targets


# ════════════════════════════════════════════════════════════
#  Gene Coverage Check
# ════════════════════════════════════════════════════════════
def check_gene_coverage(drug_targets, adj):
    """Report drug target gene coverage in PPI graph."""
    all_genes = set()
    for targets in drug_targets.values():
        all_genes |= targets

    in_ppi = all_genes & set(adj.keys())
    not_in_ppi = all_genes - set(adj.keys())

    print("\n" + "─" * 60)
    print("  Gene symbol coverage (drug targets ↔ STRING PPI)")
    print("─" * 60)
    print(f"    Drug target unique genes: {len(all_genes)}")
    print(f"    Mapped to PPI graph:      {len(in_ppi)} "
          f"({len(in_ppi)/len(all_genes)*100:.1f}%)")
    print(f"    Unmapped:                 {len(not_in_ppi)}")
    if not_in_ppi:
        print(f"    Unmapped list: {sorted(not_in_ppi)}")

    # Drug-level coverage
    drugs_with_ppi = sum(
        1 for targets in drug_targets.values()
        if targets and (targets & set(adj.keys()))
    )
    drugs_with_targets = sum(1 for v in drug_targets.values() if v)
    print(f"    Drugs with PPI-mapped targets: {drugs_with_ppi} / {drugs_with_targets}")

    return in_ppi, not_in_ppi


# ════════════════════════════════════════════════════════════
#  Feature 1: ppi_neighbor_disease_score
# ════════════════════════════════════════════════════════════
def build_feature_1(all_drugs, drug_targets, adj, gene_score_dict, brca_genes):
    """
    ppi_neighbor_disease_score (per-drug)
    ──────────────────────────────────────
    For each drug:
      1. Get target genes
      2. For each target, collect PPI 1-hop neighbors
      3. For each neighbor ∈ BRCA disease genes:
           contribution = (ppi_score / 1000) × disease_score
      4. Sum all contributions across all targets
      5. Divide by n_targets (mean normalization)

    Captures: how strongly the drug's targets connect to
    disease-relevant genes via direct protein interactions.
    """
    print("\n" + "═" * 60)
    print("  [1/3] ppi_neighbor_disease_score")
    print("═" * 60)

    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({"canonical_drug_id": drug_id,
                            "ppi_neighbor_disease_score": 0.0})
            continue

        total_score = 0.0
        for tgt in targets:
            neighbors = adj.get(tgt, {})
            for neighbor, ppi_score in neighbors.items():
                if neighbor in brca_genes:
                    ds = gene_score_dict.get(neighbor, 0.0)
                    total_score += (ppi_score / 1000.0) * ds

        score = total_score / len(targets)
        records.append({"canonical_drug_id": drug_id,
                        "ppi_neighbor_disease_score": round(score, 6)})

    df = pd.DataFrame(records)
    s = df["ppi_neighbor_disease_score"]
    nz = (s.abs() > 1e-8).sum()
    print(f"    mean={s.mean():.4f}, std={s.std():.4f}, "
          f"max={s.max():.4f}, nz={nz}/{len(df)}")
    return df


# ════════════════════════════════════════════════════════════
#  Feature 2: pathway_propagation_score
# ════════════════════════════════════════════════════════════
def build_feature_2(all_drugs, drug_targets, adj, pw_to_genes):
    """
    pathway_propagation_score (per-drug)
    ─────────────────────────────────────
    For each drug:
      1. gene_pool = target_genes ∪ PPI 1-hop neighbors of all targets
      2. For each of 50 Hallmark pathways:
           overlap_ratio = |gene_pool ∩ pathway_genes| / |pathway_genes|
      3. score = mean(50 overlap_ratios)

    Captures: how broadly the drug's influence (via PPI propagation)
    covers known cancer-related pathways.
    Wider than v2 pathway_similarity (which uses only direct targets).
    """
    print("\n" + "═" * 60)
    print("  [2/3] pathway_propagation_score")
    print("═" * 60)

    pw_names = sorted(pw_to_genes.keys())

    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({"canonical_drug_id": drug_id,
                            "pathway_propagation_score": 0.0})
            continue

        # Build gene pool: targets + 1-hop PPI neighbors
        gene_pool = set(targets)
        for tgt in targets:
            gene_pool.update(adj.get(tgt, {}).keys())

        # Overlap with each Hallmark pathway
        ratios = []
        for pw_name in pw_names:
            pw_genes = pw_to_genes[pw_name]
            overlap = len(gene_pool & pw_genes)
            ratios.append(overlap / len(pw_genes) if pw_genes else 0.0)

        score = float(np.mean(ratios))
        records.append({"canonical_drug_id": drug_id,
                        "pathway_propagation_score": round(score, 6)})

    df = pd.DataFrame(records)
    s = df["pathway_propagation_score"]
    nz = (s.abs() > 1e-8).sum()
    print(f"    mean={s.mean():.6f}, std={s.std():.6f}, "
          f"max={s.max():.6f}, nz={nz}/{len(df)}")

    # gene pool size stats
    pool_sizes = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if targets:
            pool = set(targets)
            for tgt in targets:
                pool.update(adj.get(tgt, {}).keys())
            pool_sizes.append(len(pool))
    if pool_sizes:
        print(f"    Gene pool size: mean={np.mean(pool_sizes):.0f}, "
              f"max={max(pool_sizes)}, min={min(pool_sizes)}")
    return df


# ════════════════════════════════════════════════════════════
#  Feature 3: target_diffusion_score
# ════════════════════════════════════════════════════════════
def bfs_limited(adj, start, max_hops):
    """BFS from start node, limited to max_hops.
    Returns dict {node: shortest_distance} for all reachable nodes."""
    distances = {start: 0}
    queue = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        if dist >= max_hops:
            continue
        for neighbor in adj.get(node, {}):
            if neighbor not in distances:
                distances[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))
    return distances


def build_feature_3(all_drugs, drug_targets, adj, brca_genes):
    """
    target_diffusion_score (per-drug)
    ──────────────────────────────────
    For each drug:
      1. For each target gene:
           - BFS from target (max MAX_HOPS hops)
           - For each reachable BRCA gene:
               contribution = 1 / (shortest_path + 1)
           - Sum contributions for this target
      2. score = total_sum / n_targets (mean)
      3. Distance > MAX_HOPS or unreachable → 0

    Captures: network proximity of the drug's targets
    to disease-relevant genes through the PPI network.
    """
    print("\n" + "═" * 60)
    print(f"  [3/3] target_diffusion_score (max {MAX_HOPS}-hop BFS)")
    print("═" * 60)

    # Collect unique target genes present in PPI graph
    unique_targets = set()
    for targets in drug_targets.values():
        unique_targets |= targets
    in_ppi = unique_targets & set(adj.keys())
    print(f"    Target genes in PPI: {len(in_ppi)} / {len(unique_targets)}")

    # Pre-compute BFS from each unique target (cached)
    print(f"    BFS from {len(in_ppi)} genes (max {MAX_HOPS} hops)...")
    t0 = time.time()
    bfs_cache = {}
    for gene in sorted(in_ppi):
        bfs_cache[gene] = bfs_limited(adj, gene, MAX_HOPS)
    dt = time.time() - t0
    print(f"    BFS 완료: {dt:.1f}s")

    # Reachability stats
    reach_counts = [len(d) for d in bfs_cache.values()]
    if reach_counts:
        print(f"    Reachable nodes per BFS: mean={np.mean(reach_counts):.0f}, "
              f"max={max(reach_counts)}, min={min(reach_counts)}")

    # Compute score per drug
    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({"canonical_drug_id": drug_id,
                            "target_diffusion_score": 0.0})
            continue

        total_score = 0.0
        for tgt in targets:
            if tgt not in bfs_cache:
                continue
            distances = bfs_cache[tgt]
            for brca_gene in brca_genes:
                if brca_gene in distances:
                    d = distances[brca_gene]
                    total_score += 1.0 / (d + 1)

        score = total_score / len(targets)
        records.append({"canonical_drug_id": drug_id,
                        "target_diffusion_score": round(score, 6)})

    df = pd.DataFrame(records)
    s = df["target_diffusion_score"]
    nz = (s.abs() > 1e-8).sum()
    print(f"    mean={s.mean():.4f}, std={s.std():.4f}, "
          f"max={s.max():.4f}, nz={nz}/{len(df)}")
    return df


# ════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    print("=" * 60)
    print("  Mechanism Engine v3  —  PPI-based (non-Neo4j)")
    print("=" * 60)

    # ── Load data ──
    adj = load_ppi_graph()
    gene_score_dict, brca_genes = load_brca_genes()
    pw_to_genes = load_hallmark()
    all_drugs, drug_targets = load_drug_targets()

    # ── Coverage check ──
    in_ppi, not_in_ppi = check_gene_coverage(drug_targets, adj)

    # ── Build features ──
    df1 = build_feature_1(all_drugs, drug_targets, adj, gene_score_dict, brca_genes)
    df2 = build_feature_2(all_drugs, drug_targets, adj, pw_to_genes)
    df3 = build_feature_3(all_drugs, drug_targets, adj, brca_genes)

    # ── Merge ──
    df_out = df1.merge(df2, on="canonical_drug_id").merge(df3, on="canonical_drug_id")

    # ── 최종 보고 ──
    feature_cols = [
        "ppi_neighbor_disease_score",
        "pathway_propagation_score",
        "target_diffusion_score",
    ]

    print("\n" + "=" * 60)
    print("  최종 결과")
    print("=" * 60)
    print(f"  Shape: {df_out.shape}")
    print(f"\n  {'Feature':<30s}  {'mean':>8s}  {'std':>8s}  "
          f"{'min':>8s}  {'max':>8s}  {'nonzero':>10s}")
    print("  " + "─" * 72)
    for col in feature_cols:
        s = df_out[col]
        nz = int((s.abs() > 1e-8).sum())
        print(f"  {col:<30s}  {s.mean():8.4f}  {s.std():8.4f}  "
              f"{s.min():8.4f}  {s.max():8.4f}  {nz:>5d}/{len(s)}")

    # Coverage summary
    any_nz = (df_out[feature_cols].abs() > 1e-8).any(axis=1).sum()
    print(f"\n  Any feature non-zero: {any_nz} / {len(df_out)} drugs")
    print(f"  STRING gene mapping: {len(in_ppi)} mapped, {len(not_in_ppi)} unmapped")

    # ── Save ──
    df_out.to_parquet(OUT_PATH, index=False)
    print(f"\n  저장: {OUT_PATH}")
    print(f"  크기: {OUT_PATH.stat().st_size / 1024:.0f} KB")
    print(f"  소요: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
