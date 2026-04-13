#!/usr/bin/env python3
"""
Mechanism Engine v1: 생물학적 근거 기반 feature 5개 생성
════════════════════════════════════════════════════════
Neo4j 없이 로컬 + S3 데이터만 사용

입력 데이터:
  1. nextflow/data/drug_target_mapping.parquet              (로컬)
  2. 20260413_.../data/pathway_features_hallmark_20260413    (로컬)
  3. 20260413_.../data/final_features_20260413.parquet       (로컬, lincs_*)
  4. S3 curated_date/opentargets/  (disease association)
  5. S3 curated_date/msigdb/       (gene set membership)

출력 (295 drugs x 5 features):
  1. target_overlap_count       : drug target ∩ BRCA disease gene overlap 수
  2. target_overlap_ratio       : overlap / drug별 total target 수
  3. target_disease_score_mean  : BRCA disease association score 평균
  4. pathway_match_score        : drug target이 속한 Hallmark pathway 수
  5. lincs_mean_score           : LINCS signature 평균 (보수적 집계)

저장: mechanism/mechanism_features_v1_20260413.parquet
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

DRUG_TARGET_PATH = PROJECT_ROOT / "nextflow" / "data" / "drug_target_mapping.parquet"
PATHWAY_PATH = (
    PROJECT_ROOT
    / "20260413_feature_reconstruction"
    / "data"
    / "pathway_features_hallmark_20260413.parquet"
)
FEATURES_PATH = (
    PROJECT_ROOT
    / "20260413_feature_reconstruction"
    / "data"
    / "final_features_20260413.parquet"
)
OUT_PATH = Path(__file__).resolve().parent / "mechanism_features_v1_20260413.parquet"

# S3 경로
BUCKET = "say2-4team"
S3_OT_ASSOC = "curated_date/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
S3_OT_TARGET = "curated_date/opentargets/opentargets_target_basic_20260406.parquet"
S3_OT_DISEASE = "curated_date/opentargets/opentargets_disease_basic_20260406.parquet"
S3_MSIGDB_MEMBER = "curated_date/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"

# gene symbol 패턴: 1~11자 대문자+숫자 (예: TOP1, EGFR, BCL2, MTOR)
GENE_RE = re.compile(r"^[A-Z][A-Z0-9]{0,10}$")


# ── helpers ──────────────────────────────────────────────────
def read_s3_parquet(key: str, columns: list[str] | None = None) -> pd.DataFrame:
    """S3에서 parquet 읽기"""
    print(f"    S3: s3://{BUCKET}/{key}")
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(io.BytesIO(resp["Body"].read()), columns=columns)
    print(f"       → {len(df):,} rows x {len(df.columns)} cols")
    return df


def is_gene_symbol(s: str) -> bool:
    return bool(GENE_RE.match(str(s)))


def load_brca_gene_scores() -> tuple[set, pd.DataFrame]:
    """OpenTargets에서 BRCA disease gene 목록 + score 로드 (1회 호출, 공유)

    Returns:
        brca_genes:  BRCA association score > 0인 gene symbol set
        gene_scores: DataFrame[gene_symbol, disease_score]
    """
    print("\n" + "─" * 60)
    print("  OpenTargets BRCA gene scores 로드")
    print("─" * 60)

    try:
        # 1) BRCA disease IDs
        df_dis = read_s3_parquet(S3_OT_DISEASE, columns=["id", "name"])
        brca_ids = set(
            df_dis[df_dis["name"].str.contains("breast", case=False, na=False)]["id"]
        )
        print(f"    BRCA disease IDs: {len(brca_ids)}")

        # 2) Ensembl → gene symbol
        df_tgt = read_s3_parquet(S3_OT_TARGET, columns=["id", "approvedSymbol"])
        ensembl_to_gene = dict(zip(df_tgt["id"], df_tgt["approvedSymbol"]))

        # 3) BRCA association scores
        df_assoc = read_s3_parquet(
            S3_OT_ASSOC, columns=["targetId", "diseaseId", "score"]
        )
        df_assoc = df_assoc[df_assoc["diseaseId"].isin(brca_ids)].copy()
        df_assoc["gene_symbol"] = df_assoc["targetId"].map(ensembl_to_gene)
        df_assoc = df_assoc.dropna(subset=["gene_symbol"])

        # gene별 best score (BRCA subtype 중 최대)
        gene_scores = (
            df_assoc.groupby("gene_symbol")["score"]
            .max()
            .reset_index()
            .rename(columns={"score": "disease_score"})
        )

        # score > 0 → 17,129 genes (인간 유전체 85%), 사실상 전체 → ratio가 binary화
        # score >= 0.1 → 5,210 genes, OpenTargets 표준 evidence threshold
        BRCA_SCORE_THRESHOLD = 0.1
        brca_genes = set(
            gene_scores[gene_scores["disease_score"] >= BRCA_SCORE_THRESHOLD][
                "gene_symbol"
            ]
        )
        print(f"    BRCA genes (score>={BRCA_SCORE_THRESHOLD}): {len(brca_genes):,}")

        return brca_genes, gene_scores

    except Exception as e:
        print(f"    ⚠ OpenTargets 로드 실패: {e}")
        print("    → target_overlap / disease_score = 0 으로 대체")
        return set(), pd.DataFrame(columns=["gene_symbol", "disease_score"])


# ════════════════════════════════════════════════════════════
#  Feature 1 & 2: target_overlap_count / target_overlap_ratio
# ════════════════════════════════════════════════════════════
def build_target_features(
    df_dtm: pd.DataFrame, brca_genes: set
) -> pd.DataFrame:
    """drug_targets ∩ brca_genes overlap 기반 feature

    target_overlap_count = len(drug_targets ∩ brca_genes)
    target_overlap_ratio = overlap_count / n_drug_targets  (drug별 분모)
    """
    print("\n" + "─" * 60)
    print("  [1/5] target_overlap_count  (drug_targets ∩ BRCA genes)")
    print("  [2/5] target_overlap_ratio  (overlap / drug별 target 수)")
    print("─" * 60)

    # gene symbol만 필터
    mask = df_dtm["target_gene_symbol"].apply(is_gene_symbol)
    df_gene = df_dtm[mask].copy()

    print(f"    Gene symbol rows: {len(df_gene)}/{len(df_dtm)}")
    print(f"    Unique gene symbols: {df_gene['target_gene_symbol'].nunique()}")
    print(f"    BRCA disease genes: {len(brca_genes)}")

    # drug별 집계: overlap = drug_targets ∩ brca_genes
    all_drugs = sorted(df_dtm["canonical_drug_id"].unique())
    records = []
    for drug_id in all_drugs:
        drug_targets = set(
            df_gene.loc[
                df_gene["canonical_drug_id"] == drug_id, "target_gene_symbol"
            ]
        )
        n_total = len(drug_targets)
        n_overlap = len(drug_targets & brca_genes)
        ratio = n_overlap / n_total if n_total > 0 else 0.0
        records.append(
            {
                "canonical_drug_id": drug_id,
                "target_overlap_count": n_overlap,
                "target_overlap_ratio": round(ratio, 6),
            }
        )

    df_out = pd.DataFrame(records)

    matched = (df_out["target_overlap_count"] > 0).sum()
    print(f"    결과: {matched}/{len(df_out)} drugs with BRCA overlap")
    print(
        f"    target_overlap_count : "
        f"mean={df_out['target_overlap_count'].mean():.2f}, "
        f"max={df_out['target_overlap_count'].max()}"
    )
    print(
        f"    target_overlap_ratio : "
        f"mean={df_out['target_overlap_ratio'].mean():.4f}, "
        f"max={df_out['target_overlap_ratio'].max():.4f}"
    )

    return df_out


# ════════════════════════════════════════════════════════════
#  Feature 3: target_disease_score_mean (OpenTargets BRCA)
# ════════════════════════════════════════════════════════════
def build_disease_score(
    df_dtm: pd.DataFrame, gene_scores: pd.DataFrame
) -> pd.DataFrame:
    """각 drug target의 BRCA disease association score 평균

    gene_scores: load_brca_gene_scores()에서 사전 로드된 DataFrame
    """
    print("\n" + "─" * 60)
    print("  [3/5] target_disease_score_mean (OpenTargets)")
    print("─" * 60)

    all_drugs = sorted(df_dtm["canonical_drug_id"].unique())

    if len(gene_scores) == 0:
        print("    ⚠ gene_scores 비어있음 → 0 으로 대체")
        return pd.DataFrame(
            {"canonical_drug_id": all_drugs, "target_disease_score_mean": 0.0}
        )

    print(f"    BRCA gene scores: {len(gene_scores):,}")

    # drug target gene symbols만
    df_gene = df_dtm[df_dtm["target_gene_symbol"].apply(is_gene_symbol)].copy()
    df_merged = df_gene.merge(
        gene_scores,
        left_on="target_gene_symbol",
        right_on="gene_symbol",
        how="left",
    )
    df_merged["disease_score"] = df_merged["disease_score"].fillna(0.0)

    matched_genes = df_merged[df_merged["disease_score"] > 0][
        "target_gene_symbol"
    ].nunique()
    total_genes = df_gene["target_gene_symbol"].nunique()
    print(f"    Gene-score 매칭: {matched_genes}/{total_genes}")

    # drug별 평균
    drug_score = (
        df_merged.groupby("canonical_drug_id")["disease_score"]
        .mean()
        .reset_index()
        .rename(columns={"disease_score": "target_disease_score_mean"})
    )

    df_out = pd.DataFrame({"canonical_drug_id": all_drugs})
    df_out = df_out.merge(drug_score, on="canonical_drug_id", how="left")
    df_out["target_disease_score_mean"] = (
        df_out["target_disease_score_mean"].fillna(0.0).round(6)
    )

    matched = (df_out["target_disease_score_mean"] > 0).sum()
    print(f"    결과: {matched}/{len(df_out)} drugs with disease scores")
    print(
        f"    target_disease_score_mean : "
        f"mean={df_out['target_disease_score_mean'].mean():.4f}, "
        f"max={df_out['target_disease_score_mean'].max():.4f}"
    )

    return df_out[["canonical_drug_id", "target_disease_score_mean"]]


# ════════════════════════════════════════════════════════════
#  Feature 4: pathway_match_score (MSigDB Hallmark)
# ════════════════════════════════════════════════════════════
def build_pathway_score(df_dtm: pd.DataFrame) -> pd.DataFrame:
    """drug target이 속한 Hallmark pathway 수 (MSigDB 기반)

    # v1: simple Hallmark membership count
    # v2 예정: BRCA-weighted pathway score (pathway별 disease relevance 가중)
    """
    print("\n" + "─" * 60)
    print("  [4/5] pathway_match_score (MSigDB Hallmark)")
    print("─" * 60)

    all_drugs = sorted(df_dtm["canonical_drug_id"].unique())
    default = pd.DataFrame(
        {"canonical_drug_id": all_drugs, "pathway_match_score": 0}
    )

    try:
        # MSigDB gene set membership
        df_msig = read_s3_parquet(
            S3_MSIGDB_MEMBER,
            columns=["gene_set_name", "gene_symbol", "collection_code"],
        )

        # Hallmark (collection_code = 'H') 만 필터
        df_hallmark = df_msig[df_msig["collection_code"] == "H"].copy()
        hallmark_sets = df_hallmark["gene_set_name"].nunique()
        print(f"    Hallmark gene sets: {hallmark_sets}")
        print(f"    Hallmark memberships: {len(df_hallmark):,}")

        # drug target genes 필터
        df_gene = df_dtm[df_dtm["target_gene_symbol"].apply(is_gene_symbol)].copy()

        # target → Hallmark pathway 매칭
        df_hit = df_gene.merge(
            df_hallmark[["gene_symbol", "gene_set_name"]],
            left_on="target_gene_symbol",
            right_on="gene_symbol",
            how="inner",
        )
        print(f"    Target-Pathway hits: {len(df_hit):,}")

        # drug별 unique pathway count
        pathway_score = (
            df_hit.groupby("canonical_drug_id")["gene_set_name"]
            .nunique()
            .reset_index()
            .rename(columns={"gene_set_name": "pathway_match_score"})
        )

        df_out = pd.DataFrame({"canonical_drug_id": all_drugs})
        df_out = df_out.merge(pathway_score, on="canonical_drug_id", how="left")
        df_out["pathway_match_score"] = (
            df_out["pathway_match_score"].fillna(0).astype(int)
        )

    except Exception as e:
        print(f"    ⚠ MSigDB 로드 실패: {e}")
        print("    → pathway_match_score = 0 으로 대체")
        df_out = default

    matched = (df_out["pathway_match_score"] > 0).sum()
    print(f"    결과: {matched}/{len(df_out)} drugs with pathway matches")
    print(
        f"    pathway_match_score : "
        f"mean={df_out['pathway_match_score'].mean():.2f}, "
        f"max={df_out['pathway_match_score'].max()}"
    )

    return df_out[["canonical_drug_id", "pathway_match_score"]]


# ════════════════════════════════════════════════════════════
#  Feature 5: lincs_anti_corr_score
# ════════════════════════════════════════════════════════════
def build_lincs_score() -> pd.DataFrame:
    """LINCS L1000 signature 평균 (보수적 집계)

    lincs_* 컬럼 5개:
      - lincs_cosine, lincs_pearson, lincs_spearman
            : drug-cell LINCS signature correlation (similarity 방향)
      - lincs_reverse_score_top100, lincs_reverse_score_top50
            : disease gene reversal score (높을수록 억제)

    ※ correlation 계열 (similarity)과 reversal 계열의 방향이 혼재하여
      부호 반전 없이 단순 평균으로 보수적 집계
    # v2 예정: column별 방향 분리 후 directional score 계산
    """
    print("\n" + "─" * 60)
    print("  [5/5] lincs_mean_score (LINCS L1000)")
    print("─" * 60)

    df = pd.read_parquet(FEATURES_PATH)
    lincs_cols = [c for c in df.columns if c.startswith("lincs_")]
    print(f"    LINCS columns ({len(lincs_cols)}): {lincs_cols}")
    print(f"    Samples: {len(df):,}")
    print(
        "    ※ 방향 혼재 (cosine/pearson/spearman=similarity, "
        "reverse_score=reversal) → 단순 평균"
    )

    # sample별 lincs 평균 → drug별 평균 (부호 반전 없음)
    df["_lincs_row_mean"] = df[lincs_cols].mean(axis=1)

    drug_lincs = (
        df.groupby("canonical_drug_id")["_lincs_row_mean"]
        .mean()
        .reset_index()
        .rename(columns={"_lincs_row_mean": "lincs_mean_score"})
    )
    drug_lincs["lincs_mean_score"] = drug_lincs["lincs_mean_score"].round(6)

    nonzero = (drug_lincs["lincs_mean_score"].abs() > 1e-8).sum()
    print(f"    결과: {nonzero}/{len(drug_lincs)} drugs with non-zero LINCS")
    print(
        f"    lincs_mean_score : "
        f"mean={drug_lincs['lincs_mean_score'].mean():.6f}, "
        f"min={drug_lincs['lincs_mean_score'].min():.6f}, "
        f"max={drug_lincs['lincs_mean_score'].max():.6f}"
    )

    return drug_lincs[["canonical_drug_id", "lincs_mean_score"]]


# ════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    print("=" * 60)
    print("  Mechanism Engine v1  —  build_mechanism_v1_20260413")
    print("=" * 60)

    # ── 데이터 로딩 ──
    print(f"\n  drug_target_mapping: {DRUG_TARGET_PATH.name}")
    df_dtm = pd.read_parquet(DRUG_TARGET_PATH)
    n_drugs = df_dtm["canonical_drug_id"].nunique()
    n_genes = df_dtm[df_dtm["target_gene_symbol"].apply(is_gene_symbol)][
        "target_gene_symbol"
    ].nunique()
    print(f"    {len(df_dtm)} rows, {n_drugs} drugs, {n_genes} unique gene symbols")

    # ── OpenTargets BRCA gene 로드 (Feature 1,2,3 공유) ──
    brca_genes, gene_scores = load_brca_gene_scores()

    # ── 5개 feature 생성 ──
    df_target = build_target_features(df_dtm, brca_genes)  # 1, 2
    df_disease = build_disease_score(df_dtm, gene_scores)   # 3
    df_pathway = build_pathway_score(df_dtm)                # 4
    df_lincs = build_lincs_score()                          # 5

    # ── 통합 ──
    print("\n" + "=" * 60)
    print("  통합 & 저장")
    print("=" * 60)

    df_out = df_target.copy()
    df_out = df_out.merge(df_disease, on="canonical_drug_id", how="left")
    df_out = df_out.merge(df_pathway, on="canonical_drug_id", how="left")
    df_out = df_out.merge(df_lincs, on="canonical_drug_id", how="left")

    # NaN 채우기
    df_out = df_out.fillna(0)
    df_out["target_overlap_count"] = df_out["target_overlap_count"].astype(int)
    df_out["pathway_match_score"] = df_out["pathway_match_score"].astype(int)

    # ── 결과 보고 ──
    feature_cols = [
        "target_overlap_count",
        "target_overlap_ratio",
        "target_disease_score_mean",
        "pathway_match_score",
        "lincs_mean_score",
    ]

    print(f"\n  Shape: {df_out.shape}")
    print(f"  Columns: {list(df_out.columns)}")
    print(f"\n  {'Feature':<30s}  {'mean':>8s}  {'std':>8s}  {'min':>8s}  {'max':>8s}  {'nonzero':>8s}")
    print("  " + "─" * 78)
    for col in feature_cols:
        s = df_out[col]
        nz = int((s.abs() > 1e-8).sum())
        print(
            f"  {col:<30s}  {s.mean():8.4f}  {s.std():8.4f}  "
            f"{s.min():8.4f}  {s.max():8.4f}  {nz:>5d}/{len(s)}"
        )

    # ── 저장 ──
    df_out.to_parquet(OUT_PATH, index=False)

    print(f"\n  저장: {OUT_PATH}")
    print(f"  크기: {OUT_PATH.stat().st_size / 1024:.0f} KB")
    print(f"  소요: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
