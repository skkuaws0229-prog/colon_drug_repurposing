#!/usr/bin/env python3
"""
Mechanism Engine v2: 10 features (7730 rows, per sample×drug)
════════════════════════════════════════════════════════════

입력 데이터 (S3 raw CRISPR 로딩 없음):
  1. mechanism/mechanism_features_v1_20260413.parquet    (v1: target_disease_score_mean 재사용)
  2. data/target_features_20260413.parquet               (target_crispr_mean 등)
  3. data/pathway_features_hallmark_20260413.parquet      (Hallmark 50 pathway)
  4. data/final_features_20260413.parquet                 (lincs_* 컬럼)
  5. nextflow/data/drug_target_mapping.parquet            (drug → gene)
  6. S3 OpenTargets  (BRCA gene scores, score >= 0.1)
  7. S3 MSigDB Hallmark  (gene set membership)

출력 (7730 rows × sample_id + canonical_drug_id + 10 features):
  1. target_expr_weighted_score      target_crispr_mean × target_disease_score_mean
  2. target_disease_weighted_sum     Σ(disease_score per target)
  3. target_disease_weighted_mean    weighted_sum / n_targets
  4. pathway_similarity_score        cosine(disease_hallmark_vec, drug_hallmark_vec)
  5. pathway_disease_overlap_ratio   Jaccard(disease_pathways, drug_pathways)
  6. lincs_similarity_score          mean(-cosine, -pearson, -spearman), drug 평균
  7. lincs_reversal_score            mean(reverse_top100, reverse_top50), drug 평균
  8. target_x_pathway                feat1 × feat4
  9. target_x_lincs                  feat1 × feat7
  10. disease_x_pathway              feat3 × feat4

저장: mechanism/mechanism_features_v2_20260413.parquet
"""

import io
import re
import time
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

# ── 경로 설정 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MECH_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "20260413_feature_reconstruction" / "data"

V1_PATH = MECH_DIR / "mechanism_features_v1_20260413.parquet"
TARGET_PATH = DATA_DIR / "target_features_20260413.parquet"
PATHWAY_PATH = DATA_DIR / "pathway_features_hallmark_20260413.parquet"
FEATURES_PATH = DATA_DIR / "final_features_20260413.parquet"
DRUG_TARGET_PATH = PROJECT_ROOT / "nextflow" / "data" / "drug_target_mapping.parquet"
OUT_PATH = MECH_DIR / "mechanism_features_v2_20260413.parquet"

# S3
BUCKET = "say2-4team"
S3_OT_ASSOC = "curated_date/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
S3_OT_TARGET = "curated_date/opentargets/opentargets_target_basic_20260406.parquet"
S3_OT_DISEASE = "curated_date/opentargets/opentargets_disease_basic_20260406.parquet"
S3_MSIGDB_MEMBER = "curated_date/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"

BRCA_SCORE_THRESHOLD = 0.1
GENE_RE = re.compile(r"^[A-Z][A-Z0-9]{0,10}$")


# ── helpers ──────────────────────────────────────────────────
def read_s3_parquet(key: str, columns: list[str] | None = None) -> pd.DataFrame:
    print(f"    S3: s3://{BUCKET}/{key.split('/')[-1]}")
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"       → {len(df):,} rows x {len(df.columns)} cols")
    return df


def is_gene_symbol(s: str) -> bool:
    return bool(GENE_RE.match(str(s)))


def load_opentargets():
    """OpenTargets BRCA gene scores + brca_genes 로드"""
    print("\n" + "─" * 60)
    print("  OpenTargets BRCA gene scores 로드")
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
    gene_score_dict = dict(zip(gene_scores["gene_symbol"], gene_scores["disease_score"]))

    brca_genes = set(
        gene_scores[gene_scores["disease_score"] >= BRCA_SCORE_THRESHOLD]["gene_symbol"]
    )
    print(f"    BRCA genes (score>={BRCA_SCORE_THRESHOLD}): {len(brca_genes):,}")
    return gene_score_dict, brca_genes


# ════════════════════════════════════════════════════════════
#  Feature 1: target_expr_weighted_score
# ════════════════════════════════════════════════════════════
def build_feature_1(df_base, df_v1):
    """target_crispr_mean × target_disease_score_mean (v1 재사용)"""
    print("\n" + "─" * 60)
    print("  [1/10] target_expr_weighted_score")
    print("         = target_crispr_mean × target_disease_score_mean")
    print("─" * 60)

    df = df_base.merge(
        df_v1[["canonical_drug_id", "target_disease_score_mean"]],
        on="canonical_drug_id",
        how="left",
    )
    df["target_disease_score_mean"] = df["target_disease_score_mean"].fillna(0.0)
    df["target_expr_weighted_score"] = (
        df["target_crispr_mean"] * df["target_disease_score_mean"]
    ).round(6)

    s = df["target_expr_weighted_score"]
    nz = (s.abs() > 1e-8).sum()
    print(f"    결과: {nz}/{len(df)} rows non-zero")
    print(f"    mean={s.mean():.6f}, std={s.std():.6f}, max={s.max():.6f}")

    return df[["sample_id", "canonical_drug_id", "target_expr_weighted_score"]]


# ════════════════════════════════════════════════════════════
#  Feature 2 & 3: target_disease_weighted_sum / mean
# ════════════════════════════════════════════════════════════
def build_features_2_3(all_drugs, drug_targets, gene_score_dict):
    """Σ(disease_score per target) and sum / n_targets"""
    print("\n" + "─" * 60)
    print("  [2/10] target_disease_weighted_sum")
    print("  [3/10] target_disease_weighted_mean")
    print("─" * 60)

    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        if not targets:
            records.append({
                "canonical_drug_id": drug_id,
                "target_disease_weighted_sum": 0.0,
                "target_disease_weighted_mean": 0.0,
            })
            continue
        scores = [gene_score_dict.get(g, 0.0) for g in targets]
        wsum = sum(scores)
        wmean = wsum / len(targets)
        records.append({
            "canonical_drug_id": drug_id,
            "target_disease_weighted_sum": round(wsum, 6),
            "target_disease_weighted_mean": round(wmean, 6),
        })

    df = pd.DataFrame(records)
    for col in ["target_disease_weighted_sum", "target_disease_weighted_mean"]:
        s = df[col]
        nz = (s.abs() > 1e-8).sum()
        print(f"    {col}: mean={s.mean():.4f}, nz={nz}/{len(df)}")
    return df


# ════════════════════════════════════════════════════════════
#  Feature 4 & 5: pathway_similarity / overlap_ratio
# ════════════════════════════════════════════════════════════
def build_features_4_5(all_drugs, drug_targets, brca_genes):
    """cosine(disease_vec, drug_vec), Jaccard(disease_pws, drug_pws)"""
    print("\n" + "─" * 60)
    print("  [4/10] pathway_similarity_score (cosine)")
    print("  [5/10] pathway_disease_overlap_ratio (Jaccard)")
    print("─" * 60)

    df_msig = read_s3_parquet(
        S3_MSIGDB_MEMBER,
        columns=["gene_set_name", "gene_symbol", "collection_code"],
    )
    df_hallmark = df_msig[df_msig["collection_code"] == "H"].copy()
    hallmark_names = sorted(df_hallmark["gene_set_name"].unique())
    print(f"    Hallmark pathways: {len(hallmark_names)}")

    # pathway → gene set
    pw_to_genes = {}
    for pw in hallmark_names:
        pw_to_genes[pw] = set(
            df_hallmark[df_hallmark["gene_set_name"] == pw]["gene_symbol"]
        )

    # disease vector (50-dim binary)
    disease_vec = np.zeros(len(hallmark_names))
    disease_pws = set()
    for i, pw in enumerate(hallmark_names):
        if pw_to_genes[pw] & brca_genes:
            disease_vec[i] = 1.0
            disease_pws.add(i)
    norm_disease = np.linalg.norm(disease_vec)
    print(f"    Disease-active pathways: {int(disease_vec.sum())}/50")

    records = []
    for drug_id in all_drugs:
        targets = drug_targets.get(drug_id, set())
        drug_vec = np.zeros(len(hallmark_names))
        drug_pws = set()
        for i, pw in enumerate(hallmark_names):
            if pw_to_genes[pw] & targets:
                drug_vec[i] = 1.0
                drug_pws.add(i)

        # cosine
        norm_drug = np.linalg.norm(drug_vec)
        cos_sim = (
            float(np.dot(disease_vec, drug_vec) / (norm_disease * norm_drug))
            if norm_disease > 0 and norm_drug > 0
            else 0.0
        )

        # Jaccard
        union = disease_pws | drug_pws
        jaccard = len(disease_pws & drug_pws) / len(union) if union else 0.0

        records.append({
            "canonical_drug_id": drug_id,
            "pathway_similarity_score": round(cos_sim, 6),
            "pathway_disease_overlap_ratio": round(jaccard, 6),
        })

    df = pd.DataFrame(records)
    for col in ["pathway_similarity_score", "pathway_disease_overlap_ratio"]:
        s = df[col]
        nz = (s.abs() > 1e-8).sum()
        print(f"    {col}: mean={s.mean():.4f}, nz={nz}/{len(df)}")
    return df


# ════════════════════════════════════════════════════════════
#  Feature 6 & 7: lincs_similarity / lincs_reversal
# ════════════════════════════════════════════════════════════
def build_features_6_7(all_drugs):
    """
    6. lincs_similarity_score = mean(-similarity_cols), drug 평균
    7. lincs_reversal_score   = mean(reversal_cols), drug 평균
    """
    print("\n" + "─" * 60)
    print("  [6/10] lincs_similarity_score")
    print("  [7/10] lincs_reversal_score")
    print("─" * 60)

    df = pd.read_parquet(FEATURES_PATH)

    # 존재하는 컬럼만 사용
    sim_candidates = ["lincs_cosine", "lincs_pearson", "lincs_spearman"]
    rev_candidates = ["lincs_reverse_score_top100", "lincs_reverse_score_top50"]
    sim_cols = [c for c in sim_candidates if c in df.columns]
    rev_cols = [c for c in rev_candidates if c in df.columns]
    print(f"    Similarity cols found: {sim_cols}")
    print(f"    Reversal cols found:   {rev_cols}")

    # similarity: 음수 = disease reversal → negate하여 양수 = reversal
    if sim_cols:
        df["_sim"] = (-df[sim_cols]).mean(axis=1)
    else:
        df["_sim"] = 0.0

    if rev_cols:
        df["_rev"] = df[rev_cols].mean(axis=1)
    else:
        df["_rev"] = 0.0

    # drug 평균
    drug_lincs = (
        df.groupby("canonical_drug_id")[["_sim", "_rev"]]
        .mean()
        .reset_index()
        .rename(columns={
            "_sim": "lincs_similarity_score",
            "_rev": "lincs_reversal_score",
        })
    )
    drug_lincs["lincs_similarity_score"] = drug_lincs["lincs_similarity_score"].round(6)
    drug_lincs["lincs_reversal_score"] = drug_lincs["lincs_reversal_score"].round(6)

    df_out = pd.DataFrame({"canonical_drug_id": all_drugs})
    df_out = df_out.merge(drug_lincs, on="canonical_drug_id", how="left").fillna(0.0)

    for col in ["lincs_similarity_score", "lincs_reversal_score"]:
        s = df_out[col]
        nz = (s.abs() > 1e-8).sum()
        print(f"    {col}: mean={s.mean():.6f}, nz={nz}/{len(df_out)}")
    return df_out


# ════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    print("=" * 60)
    print("  Mechanism Engine v2  —  build_mechanism_v2_20260413")
    print("=" * 60)

    # ── 로컬 데이터 로드 ──
    print(f"\n  v1 features: {V1_PATH.name}")
    df_v1 = pd.read_parquet(V1_PATH)
    print(f"    {df_v1.shape[0]} drugs x {df_v1.shape[1]} cols")

    print(f"  target features: {TARGET_PATH.name}")
    df_target = pd.read_parquet(TARGET_PATH)
    print(f"    {df_target.shape[0]} rows x {df_target.shape[1]} cols")

    print(f"  drug_target_mapping: {DRUG_TARGET_PATH.name}")
    df_dtm = pd.read_parquet(DRUG_TARGET_PATH)
    df_gene = df_dtm[df_dtm["target_gene_symbol"].apply(is_gene_symbol)].copy()
    all_drugs = sorted(df_dtm["canonical_drug_id"].unique())
    print(f"    {len(df_dtm)} rows, {len(all_drugs)} drugs, {df_gene['target_gene_symbol'].nunique()} gene symbols")

    # drug → target genes
    drug_targets = {}
    for drug_id in all_drugs:
        drug_targets[drug_id] = set(
            df_gene.loc[df_gene["canonical_drug_id"] == drug_id, "target_gene_symbol"]
        )

    # ── S3 데이터 로드 ──
    gene_score_dict, brca_genes = load_opentargets()

    # ── Base frame (7730 rows) ──
    df_base = df_target[["sample_id", "canonical_drug_id", "target_crispr_mean"]].copy()

    # ── Feature 1: per-sample ──
    df_feat1 = build_feature_1(df_base, df_v1)

    # ── Features 2-3: per-drug ──
    df_feat23 = build_features_2_3(all_drugs, drug_targets, gene_score_dict)

    # ── Features 4-5: per-drug ──
    df_feat45 = build_features_4_5(all_drugs, drug_targets, brca_genes)

    # ── Features 6-7: per-drug ──
    df_feat67 = build_features_6_7(all_drugs)

    # ── 통합 (7730 rows) ──
    print("\n" + "=" * 60)
    print("  통합 & Cross Features 생성")
    print("=" * 60)

    df_out = df_feat1.copy()
    for df_drug in [df_feat23, df_feat45, df_feat67]:
        df_out = df_out.merge(df_drug, on="canonical_drug_id", how="left")
    df_out = df_out.fillna(0.0)

    # ── Cross Features 8-10 ──
    print("  [8/10] target_x_pathway  = target_expr_weighted_score × pathway_similarity_score")
    df_out["target_x_pathway"] = (
        df_out["target_expr_weighted_score"] * df_out["pathway_similarity_score"]
    ).round(6)

    print("  [9/10] target_x_lincs    = target_expr_weighted_score × lincs_reversal_score")
    df_out["target_x_lincs"] = (
        df_out["target_expr_weighted_score"] * df_out["lincs_reversal_score"]
    ).round(6)

    print("  [10/10] disease_x_pathway = target_disease_weighted_mean × pathway_similarity_score")
    df_out["disease_x_pathway"] = (
        df_out["target_disease_weighted_mean"] * df_out["pathway_similarity_score"]
    ).round(6)

    # ── 결과 보고 ──
    feature_cols = [
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

    df_out = df_out[["sample_id", "canonical_drug_id"] + feature_cols]

    print(f"\n  Shape: {df_out.shape}")
    print(f"\n  {'Feature':<35s}  {'mean':>8s}  {'std':>8s}  {'min':>8s}  {'max':>8s}  {'nonzero':>10s}")
    print("  " + "─" * 82)
    for col in feature_cols:
        s = df_out[col]
        nz = int((s.abs() > 1e-8).sum())
        print(
            f"  {col:<35s}  {s.mean():8.4f}  {s.std():8.4f}  "
            f"{s.min():8.4f}  {s.max():8.4f}  {nz:>5d}/{len(s)}"
        )

    # ── 저장 ──
    df_out.to_parquet(OUT_PATH, index=False)
    print(f"\n  저장: {OUT_PATH}")
    print(f"  크기: {OUT_PATH.stat().st_size / 1024:.0f} KB")
    print(f"  소요: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
