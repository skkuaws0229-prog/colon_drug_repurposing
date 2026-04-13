#!/usr/bin/env python3
"""
Discovery-oriented Ranking v2 (Top 28 Dedup 기반)
═══════════════════════════════════════════════════════════════
  v1 대비 변경점:
    1. Base normalization: percentile rank (0~1), IC50 낮을수록 1.0
    2. Scoring 구조: 0.5×base_norm + 0.5×(novelty×(1-penalty))
    3. 2-stage ranking: Stage1 base_norm Top 20 → Stage2 discovery_score 재정렬
    4. Category A penalty 강화: 0.5 → 0.7 (B advanced: 0.3→0.4)

  Formula:
    novelty_score = target_novelty×0.5 + pathway_novelty×0.5
    discovery_score = 0.5 × base_norm + 0.5 × (novelty_score × (1 - known_penalty))

  출력:
    results/discovery_ranking_20260413/
    ├── discovery_v2_top15_20260413.csv
    ├── discovery_v2_full28_20260413.csv
    └── discovery_v2_ranking_summary.json
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import json
import time
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_CSV = PROJECT_ROOT / "results" / "top30_dedup_20260413" / "top30_dedup_20260413.csv"
OUTPUT_DIR = PROJECT_ROOT / "results" / "discovery_ranking_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STAGE1_CUTOFF = 20  # base_norm 기준 상위 20개만 Stage 2 진입

# ── Category 분류 ──
CATEGORY_A_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
    "Dactinomycin", "Epirubicin", "Topotecan", "Irinotecan",
    "Rapamycin", "Fulvestrant", "Methotrexate",
}
CATEGORY_C_DRUGS = {"Avagacestat", "Tozasertib"}

# ── Known Drug Penalty (v2: A 강화) ──
CATEGORY_B_ADVANCED = {
    "Temsirolimus",    # FDA 승인(신세포암), 유방암 Phase II
    "AZD2014",         # Phase II (MANTA, HR+ 유방암)
    "MK-2206",         # Phase II (유방암 다수)
    "Pictilisib",      # Phase II (FERGI, 유방암)
    "Tanespimycin",    # Phase II (유방암, trastuzumab 병용)
    "Mitoxantrone",    # FDA 승인(전립선암/AML), 유방암 Phase III
}

PENALTY_MAP = {
    "A":          0.7,   # v1: 0.5 → v2: 0.7 (강화)
    "B_advanced": 0.4,   # v1: 0.3 → v2: 0.4
    "B_early":    0.1,   # 동일
    "C":          0.0,   # 동일
}


def get_category(drug_name):
    if drug_name in CATEGORY_A_DRUGS:
        return "A"
    if drug_name in CATEGORY_C_DRUGS:
        return "C"
    return "B"


def get_known_penalty(drug_name, category):
    if category == "A":
        return PENALTY_MAP["A"]
    elif category == "C":
        return PENALTY_MAP["C"]
    else:
        if drug_name in CATEGORY_B_ADVANCED:
            return PENALTY_MAP["B_advanced"]
        else:
            return PENALTY_MAP["B_early"]


# ── Target Novelty ──
STANDARD_BRCA_TARGETS = {
    "Microtubule stabiliser", "Microtubule destabiliser",
    "Anthracycline", "Antimetabolite",
    "TOP1", "TOP2", "MTOR", "MTORC1", "ESR",
}
MODERATE_TARGETS = {
    "mTORC1, mTORC2", "PI3K (class 1)",
    "AKT1, AKT2", "HSP90", "RNA polymerase",
}


def get_target_novelty(target_str):
    target = str(target_str).strip()
    if target in STANDARD_BRCA_TARGETS:
        return 0.2, "standard"
    if target in MODERATE_TARGETS:
        return 0.5, "moderate"
    target_lower = target.lower()
    for std in STANDARD_BRCA_TARGETS:
        if std.lower() in target_lower or target_lower in std.lower():
            return 0.2, "standard"
    for mod in MODERATE_TARGETS:
        if mod.lower() in target_lower or target_lower in mod.lower():
            return 0.5, "moderate"
    return 1.0, "novel"


# ── Pathway Novelty ──
PATHWAY_NOVELTY_MAP = {
    "Mitosis":              0.2,
    "DNA replication":      0.2,
    "Hormone-related":      0.3,
    "PI3K/MTOR signaling":  0.5,
    "Cell cycle":           0.6,
    "Apoptosis regulation": 0.6,
}


def get_pathway_novelty(pathway_str):
    pathway = str(pathway_str).strip()
    if pathway in PATHWAY_NOVELTY_MAP:
        return PATHWAY_NOVELTY_MAP[pathway], pathway
    return 1.0, pathway


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Discovery-oriented Ranking v2 (2-stage, normalized)")
    print("=" * 70)

    # ── 1. 입력 로드 ──
    print(f"\n  Loading: {INPUT_CSV.name}")
    df = pd.read_csv(INPUT_CSV)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    n_drugs = len(df)
    print(f"    Drugs: {n_drugs}")

    # ── 2. Base normalization: percentile rank (0~1) ──
    # IC50 낮을수록(=더 효과적) 높은 percentile
    print(f"\n  Computing base_norm (percentile rank)...")
    df_sorted = df.sort_values("mean_pred_ic50", ascending=True).reset_index(drop=True)
    df_sorted["base_norm"] = [(n_drugs - i) / n_drugs for i in range(n_drugs)]

    print(f"    base_norm range: [{df_sorted['base_norm'].min():.4f}, "
          f"{df_sorted['base_norm'].max():.4f}]")
    print(f"    IC50 가장 낮은 drug: {df_sorted.iloc[0]['drug_name']} "
          f"(IC50={df_sorted.iloc[0]['mean_pred_ic50']:.4f}, base_norm={df_sorted.iloc[0]['base_norm']:.4f})")

    # ── 3. Novelty + Penalty 계산 ──
    print(f"\n  Computing novelty scores & penalties...")

    records = []
    for _, row in df_sorted.iterrows():
        drug_name = str(row["drug_name"])
        target = str(row.get("target", ""))
        pathway = str(row.get("pathway", ""))
        pred_ic50 = float(row["mean_pred_ic50"])
        base_norm = float(row["base_norm"])
        category = get_category(drug_name)

        known_penalty = get_known_penalty(drug_name, category)
        target_novelty, target_class = get_target_novelty(target)
        pathway_novelty, _ = get_pathway_novelty(pathway)

        novelty_score = target_novelty * 0.5 + pathway_novelty * 0.5
        novelty_component = novelty_score * (1 - known_penalty)
        discovery_score = 0.5 * base_norm + 0.5 * novelty_component

        records.append({
            "canonical_drug_id": row["canonical_drug_id"],
            "drug_name": drug_name,
            "category": category,
            "target": target,
            "pathway": pathway,
            "mean_pred_ic50": pred_ic50,
            "sensitivity_rate": row.get("sensitivity_rate", 0),
            "n_samples": row.get("n_samples", 0),
            "validation_rank": int(row["rank"]),
            "base_norm": round(base_norm, 4),
            "known_penalty": known_penalty,
            "target_novelty": target_novelty,
            "target_class": target_class,
            "pathway_novelty": pathway_novelty,
            "novelty_score": round(novelty_score, 4),
            "novelty_component": round(novelty_component, 4),
            "discovery_score": round(discovery_score, 4),
        })

    result = pd.DataFrame(records)

    # ── 4. Stage 1: base_norm Top 20 필터링 ──
    print(f"\n{'='*70}")
    print(f"  STAGE 1: Base Efficacy Filter (Top {STAGE1_CUTOFF}/{n_drugs})")
    print(f"{'='*70}")

    stage1 = result.nlargest(STAGE1_CUTOFF, "base_norm").copy()
    stage1_excluded = result[~result.index.isin(stage1.index)].copy()

    print(f"  통과: {len(stage1)}개 (base_norm >= {stage1['base_norm'].min():.4f})")
    print(f"  탈락: {len(stage1_excluded)}개")

    if len(stage1_excluded) > 0:
        print(f"\n  Stage 1 탈락 약물:")
        for _, r in stage1_excluded.sort_values("base_norm", ascending=False).iterrows():
            print(f"    V#{int(r['validation_rank'])} {r['drug_name']:<22} "
                  f"Cat={r['category']} base_norm={r['base_norm']:.4f} "
                  f"IC50={r['mean_pred_ic50']:.4f}")

    # ── 5. Stage 2: Discovery score 정렬 ──
    print(f"\n{'='*70}")
    print(f"  STAGE 2: Discovery Score Ranking (Top 15 from {len(stage1)})")
    print(f"{'='*70}")

    stage2 = stage1.sort_values("discovery_score", ascending=False).copy()
    stage2["discovery_rank"] = range(1, len(stage2) + 1)

    # Full 28에도 discovery_rank 부여 (stage1 탈락 = 21~28)
    stage1_excluded_sorted = stage1_excluded.sort_values("discovery_score", ascending=False).copy()
    stage1_excluded_sorted["discovery_rank"] = range(len(stage2) + 1, n_drugs + 1)
    full28 = pd.concat([stage2, stage1_excluded_sorted], ignore_index=True)

    top15 = stage2.head(15)

    print(f"\n  {'D#':>3} {'V#':>3} {'Δ':>4} {'Cat':>3} {'Drug':<22} "
          f"{'IC50':>8} {'base_n':>6} {'KnPen':>5} {'TgtNov':>6} {'PwNov':>5} "
          f"{'Novelty':>7} {'D-Score':>8} {'TgtClass':<10}")
    print(f"  {'-'*112}")

    for _, r in top15.iterrows():
        delta = int(r["validation_rank"]) - int(r["discovery_rank"])
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        print(f"  {int(r['discovery_rank']):>3} {int(r['validation_rank']):>3} "
              f"{delta_str:>4} {r['category']:>3} {r['drug_name']:<22} "
              f"{r['mean_pred_ic50']:>8.4f} {r['base_norm']:>6.4f} "
              f"{r['known_penalty']:>5.1f} {r['target_novelty']:>6.1f} "
              f"{r['pathway_novelty']:>5.1f} {r['novelty_component']:>7.4f} "
              f"{r['discovery_score']:>8.4f} {r['target_class']:<10}")

    # ── 6. Full 28 ──
    print(f"\n{'='*90}")
    print(f"  FULL RANKING (28 drugs)")
    print(f"{'='*90}")
    print(f"  {'D#':>3} {'V#':>3} {'Δ':>4} {'Cat':>3} {'Drug':<22} "
          f"{'base_n':>6} {'D-Score':>8} {'Stage':<8}")
    print(f"  {'-'*70}")

    for _, r in full28.iterrows():
        delta = int(r["validation_rank"]) - int(r["discovery_rank"])
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        stage = "S1+S2" if int(r["discovery_rank"]) <= STAGE1_CUTOFF else "S1 out"
        marker = " ←" if int(r["discovery_rank"]) <= 15 else ""
        print(f"  {int(r['discovery_rank']):>3} {int(r['validation_rank']):>3} "
              f"{delta_str:>4} {r['category']:>3} {r['drug_name']:<22} "
              f"{r['base_norm']:>6.4f} {r['discovery_score']:>8.4f} "
              f"{stage:<8}{marker}")

    # ── 7. Validation vs Discovery v2 비교 ──
    print(f"\n{'='*70}")
    print(f"  Validation Top 15 vs Discovery v2 Top 15 비교")
    print(f"{'='*70}")

    val_top15_ids = set(df.head(15)["canonical_drug_id"].values)
    disc_top15_ids = set(top15["canonical_drug_id"].values)

    entered = disc_top15_ids - val_top15_ids
    exited = val_top15_ids - disc_top15_ids

    entered_drugs = full28[full28["canonical_drug_id"].isin(entered)].sort_values("discovery_rank")
    exited_drugs = full28[full28["canonical_drug_id"].isin(exited)].sort_values("validation_rank")

    print(f"\n  신규 진입 (Discovery v2 Top 15에만):")
    if len(entered_drugs) > 0:
        for _, r in entered_drugs.iterrows():
            print(f"    D#{int(r['discovery_rank'])} ← V#{int(r['validation_rank'])} "
                  f"{r['drug_name']} (Cat {r['category']}, D-score={r['discovery_score']:.4f})")
    else:
        print("    없음")

    print(f"\n  탈락 (Validation Top 15에만):")
    if len(exited_drugs) > 0:
        for _, r in exited_drugs.iterrows():
            print(f"    V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
                  f"{r['drug_name']} (Cat {r['category']}, D-score={r['discovery_score']:.4f})")
    else:
        print("    없음")

    # ── 8. v1 vs v2 비교 (v1 결과가 있으면) ──
    v1_csv = OUTPUT_DIR / "discovery_top15_20260413.csv"
    if v1_csv.exists():
        print(f"\n{'='*70}")
        print(f"  Discovery v1 vs v2 비교")
        print(f"{'='*70}")
        v1 = pd.read_csv(v1_csv)
        v1["canonical_drug_id"] = v1["canonical_drug_id"].astype(str)
        v1_ids = set(v1["canonical_drug_id"].values)
        v2_ids = set(top15["canonical_drug_id"].values)

        v2_only = v2_ids - v1_ids
        v1_only = v1_ids - v2_ids

        print(f"\n  v2에서 신규 진입 (v1에 없었음):")
        if v2_only:
            for did in v2_only:
                r = full28[full28["canonical_drug_id"] == did].iloc[0]
                print(f"    D#{int(r['discovery_rank'])} {r['drug_name']} "
                      f"(Cat {r['category']}, D-score={r['discovery_score']:.4f})")
        else:
            print("    없음")

        print(f"\n  v1에서 탈락 (v2에 없음):")
        if v1_only:
            for did in v1_only:
                rows = full28[full28["canonical_drug_id"] == did]
                if not rows.empty:
                    r = rows.iloc[0]
                    print(f"    D#{int(r['discovery_rank'])} {r['drug_name']} "
                          f"(Cat {r['category']}, D-score={r['discovery_score']:.4f})")
        else:
            print("    없음")

    # ── 9. Category 분포 변화 ──
    print(f"\n{'='*70}")
    print(f"  Category 분포 변화 (Validation / v1 / v2)")
    print(f"{'='*70}")

    val_cats = df.head(15)["drug_name"].map(get_category).value_counts().sort_index()

    # v1 분포
    if v1_csv.exists():
        v1_cats = v1["drug_name"].map(get_category).value_counts().sort_index()
    else:
        v1_cats = pd.Series(dtype=int)

    v2_cats = top15["category"].value_counts().sort_index()

    cat_labels = {"A": "Known BRCA", "B": "BRCA 연구", "C": "완전 재창출"}
    print(f"\n  {'Cat':<3} {'Label':<15} {'Validation':>10} {'v1':>10} {'v2':>10} {'v1→v2':>8}")
    print(f"  {'-'*62}")
    for cat in ["A", "B", "C"]:
        v_cnt = int(val_cats.get(cat, 0))
        v1_cnt = int(v1_cats.get(cat, 0)) if not v1_cats.empty else "—"
        v2_cnt = int(v2_cats.get(cat, 0))
        if isinstance(v1_cnt, int):
            diff = v2_cnt - v1_cnt
            diff_str = f"+{diff}" if diff > 0 else str(diff)
        else:
            diff_str = "—"
        print(f"  {cat:<3} {cat_labels[cat]:<15} {v_cnt:>10} "
              f"{str(v1_cnt):>10} {v2_cnt:>10} {diff_str:>8}")

    # ── 10. 순위 변동 Top 5 ──
    print(f"\n{'='*70}")
    print(f"  Top 5 순위 상승 / 하락 (Validation 대비)")
    print(f"{'='*70}")

    full28["rank_delta"] = full28["validation_rank"] - full28["discovery_rank"]

    top_risers = full28.nlargest(5, "rank_delta")
    top_fallers = full28.nsmallest(5, "rank_delta")

    print(f"\n  순위 상승:")
    for _, r in top_risers.iterrows():
        print(f"    {r['drug_name']:<22} V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
              f"(Δ+{int(r['rank_delta'])}, Cat {r['category']}, "
              f"novelty={r['novelty_component']:.4f})")

    print(f"\n  순위 하락:")
    for _, r in top_fallers.iterrows():
        print(f"    {r['drug_name']:<22} V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
              f"(Δ{int(r['rank_delta'])}, Cat {r['category']}, "
              f"novelty={r['novelty_component']:.4f})")

    # ── 11. 저장 ──
    save_cols = [
        "discovery_rank", "validation_rank", "canonical_drug_id",
        "drug_name", "category", "target", "pathway",
        "mean_pred_ic50", "sensitivity_rate", "n_samples",
        "base_norm", "known_penalty", "target_novelty", "target_class",
        "pathway_novelty", "novelty_score", "novelty_component",
        "discovery_score",
    ]

    csv_path = OUTPUT_DIR / "discovery_v2_top15_20260413.csv"
    top15[save_cols].to_csv(csv_path, index=False)
    print(f"\n  Saved CSV (Top 15): {csv_path}")

    full_csv = OUTPUT_DIR / "discovery_v2_full28_20260413.csv"
    full28[save_cols + ["rank_delta"]].to_csv(full_csv, index=False)
    print(f"  Saved CSV (Full 28): {full_csv}")

    json_path = OUTPUT_DIR / "discovery_v2_ranking_summary.json"
    summary = {
        "description": "Discovery-oriented Ranking v2 (2-stage, percentile-normalized)",
        "formula": "discovery_score = 0.5 × base_norm + 0.5 × (novelty_score × (1 - known_penalty))",
        "changes_from_v1": [
            "base_norm: percentile rank (0~1) instead of raw -IC50",
            "scoring: additive (0.5×base + 0.5×novelty) instead of multiplicative",
            "2-stage: base_norm Top 20 filter before discovery ranking",
            "penalty: A=0.7 (was 0.5), B_advanced=0.4 (was 0.3)",
        ],
        "stage1_cutoff": STAGE1_CUTOFF,
        "n_drugs": n_drugs,
        "penalty_map": PENALTY_MAP,
        "top15_discovery_v2": top15[save_cols].to_dict(orient="records"),
        "comparison": {
            "entered_discovery_v2_top15": entered_drugs[save_cols].to_dict(orient="records") if len(entered_drugs) > 0 else [],
            "exited_discovery_v2_top15": exited_drugs[save_cols].to_dict(orient="records") if len(exited_drugs) > 0 else [],
        },
        "category_distribution": {
            "validation_top15": val_cats.to_dict(),
            "discovery_v2_top15": v2_cats.to_dict(),
        },
    }

    def convert(obj):
        import numpy as np
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64, np.bool_)):
            return int(obj)
        return obj

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=convert, ensure_ascii=False)
    print(f"  Saved JSON: {json_path}")

    dt = time.time() - t0
    print(f"\n  Completed in {dt:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
