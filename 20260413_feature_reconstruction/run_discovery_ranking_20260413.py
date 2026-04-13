#!/usr/bin/env python3
"""
Discovery-oriented Ranking (Top 28 Dedup 기반)
═══════════════════════════════════════════════════════════════
  Novelty Score 기반 재순위화:
    1. Known drug penalty (A=0.5, B-advanced=0.3, B-early=0.1, C=0.0)
    2. Target novelty (표준=0.2, 중간=0.5, 신규=1.0)
    3. Pathway novelty (Mitosis/DNA rep=0.2, PI3K=0.5, Cell cycle/Apoptosis=0.6, 기타=1.0)
    4. discovery_score = (-pred_IC50) × (1 - known_penalty) × (target_novelty×0.5 + pathway_novelty×0.5)

  출력:
    - Discovery Top 15
    - Validation vs Discovery ranking 비교
    - Category 분포 변화
    - results/discovery_ranking_20260413/discovery_top15_20260413.csv
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

# ── Category 분류 ──
CATEGORY_A_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
    "Dactinomycin", "Epirubicin", "Topotecan", "Irinotecan",
    "Rapamycin", "Fulvestrant", "Methotrexate",
}
CATEGORY_C_DRUGS = {"Avagacestat", "Tozasertib"}

# ── Known Drug Penalty ──
# Category B 세분화: Phase II+ vs Phase I/전임상
CATEGORY_B_ADVANCED = {
    # Phase II 이상 임상시험 진행 이력 (유방암 또는 고형암)
    "Temsirolimus",    # FDA 승인(신세포암), 유방암 Phase II 진행
    "AZD2014",         # Phase II (MANTA trial, HR+ 유방암)
    "MK-2206",         # Phase II (유방암 다수)
    "Pictilisib",      # Phase II (FERGI trial, 유방암)
    "Tanespimycin",    # Phase II (유방암, trastuzumab 병용)
    "Mitoxantrone",    # FDA 승인(전립선암/AML), 유방암 Phase III
}

# 나머지 Category B는 Phase I/전임상
# CDK9_5576, CDK9_5038, SL0101, Teniposide, TW 37,
# Sabutoclax, ABT737, LMP744, AZD5582


def get_category(drug_name):
    if drug_name in CATEGORY_A_DRUGS:
        return "A"
    if drug_name in CATEGORY_C_DRUGS:
        return "C"
    return "B"


def get_known_penalty(drug_name, category):
    """Known drug penalty 산출."""
    if category == "A":
        return 0.5
    elif category == "C":
        return 0.0
    else:  # B
        if drug_name in CATEGORY_B_ADVANCED:
            return 0.3  # Phase II+
        else:
            return 0.1  # Phase I/전임상


# ── Target Novelty ──
# 표준 BRCA target (잘 알려진 → 낮은 novelty)
STANDARD_BRCA_TARGETS = {
    "Microtubule stabiliser",
    "Microtubule destabiliser",
    "Anthracycline",
    "Antimetabolite",
    "TOP1",
    "TOP2",
    "MTOR",
    "MTORC1",
    "ESR",
}

# 중간 novelty (BRCA 연구 중이나 표준은 아닌 target)
MODERATE_TARGETS = {
    "mTORC1, mTORC2",   # mTOR 이중 억제
    "PI3K (class 1)",   # PI3K 억제
    "AKT1, AKT2",       # AKT 억제
    "HSP90",            # HSP90 억제
    "RNA polymerase",   # RNA 합성 억제
}


def get_target_novelty(target_str):
    """Target novelty score: 표준=0.2, 중간=0.5, 신규=1.0"""
    target = str(target_str).strip()
    if target in STANDARD_BRCA_TARGETS:
        return 0.2, "standard"
    if target in MODERATE_TARGETS:
        return 0.5, "moderate"
    # 부분 매칭 확인 (표준 target 키워드 포함 시)
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
    "Mitosis":                0.2,   # 잘 알려짐
    "DNA replication":        0.2,   # 잘 알려짐
    "PI3K/MTOR signaling":    0.5,   # 활발히 연구 중
    "Cell cycle":             0.6,   # 새로운 표적 개발 중
    "Apoptosis regulation":   0.6,   # 새로운 BH3 mimetics
    "Hormone-related":        0.3,   # ER 표적은 잘 알려짐
}


def get_pathway_novelty(pathway_str):
    """Pathway novelty score."""
    pathway = str(pathway_str).strip()
    if pathway in PATHWAY_NOVELTY_MAP:
        return PATHWAY_NOVELTY_MAP[pathway], pathway
    return 1.0, pathway  # 기타/새로운 pathway


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Discovery-oriented Ranking (Top 28 Dedup)")
    print("=" * 70)

    # ── 1. 입력 로드 ──
    print(f"\n  Loading: {INPUT_CSV.name}")
    df = pd.read_csv(INPUT_CSV)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    print(f"    Drugs: {len(df)}")

    # ── 2. Category 및 Novelty Score 계산 ──
    print(f"\n  Computing novelty scores...")

    records = []
    for _, row in df.iterrows():
        drug_name = str(row["drug_name"])
        target = str(row.get("target", ""))
        pathway = str(row.get("pathway", ""))
        pred_ic50 = float(row["mean_pred_ic50"])
        category = get_category(drug_name)

        # 1. Known penalty
        known_penalty = get_known_penalty(drug_name, category)

        # 2. Target novelty
        target_novelty, target_class = get_target_novelty(target)

        # 3. Pathway novelty
        pathway_novelty, pathway_name = get_pathway_novelty(pathway)

        # 4. Discovery score
        efficacy = -pred_ic50  # 높을수록 효과적
        novelty_factor = (1 - known_penalty)
        combined_novelty = target_novelty * 0.5 + pathway_novelty * 0.5
        discovery_score = efficacy * novelty_factor * combined_novelty

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
            "known_penalty": known_penalty,
            "target_novelty": target_novelty,
            "target_class": target_class,
            "pathway_novelty": pathway_novelty,
            "combined_novelty": combined_novelty,
            "efficacy_component": round(efficacy, 4),
            "novelty_factor": round(novelty_factor, 2),
            "discovery_score": round(discovery_score, 4),
        })

    result = pd.DataFrame(records)
    result = result.sort_values("discovery_score", ascending=False)
    result["discovery_rank"] = range(1, len(result) + 1)

    # ── 3. 결과 출력 ──
    print(f"\n{'='*110}")
    print(f"  DISCOVERY RANKING (Top 15)")
    print(f"{'='*110}")
    print(f"  {'D#':>3} {'V#':>3} {'Δ':>4} {'Cat':>3} {'Drug':<22} "
          f"{'Pred IC50':>9} {'KnPen':>5} {'TgtNov':>6} {'PwNov':>5} "
          f"{'D-Score':>8} {'Target Class':<10}")
    print(f"  {'-'*107}")

    top15 = result.head(15)
    for _, r in top15.iterrows():
        delta = r["validation_rank"] - r["discovery_rank"]
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        print(f"  {int(r['discovery_rank']):>3} {int(r['validation_rank']):>3} "
              f"{delta_str:>4} {r['category']:>3} {r['drug_name']:<22} "
              f"{r['mean_pred_ic50']:>9.4f} {r['known_penalty']:>5.1f} "
              f"{r['target_novelty']:>6.1f} {r['pathway_novelty']:>5.1f} "
              f"{r['discovery_score']:>8.4f} {r['target_class']:<10}")

    # ── 4. Full 28 ranking ──
    print(f"\n{'='*110}")
    print(f"  FULL DISCOVERY RANKING (28 drugs)")
    print(f"{'='*110}")
    print(f"  {'D#':>3} {'V#':>3} {'Δ':>4} {'Cat':>3} {'Drug':<22} "
          f"{'Pred IC50':>9} {'D-Score':>8} {'Target Class':<10}")
    print(f"  {'-'*80}")

    for _, r in result.iterrows():
        delta = r["validation_rank"] - r["discovery_rank"]
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        marker = " ←" if r["discovery_rank"] <= 15 else ""
        print(f"  {int(r['discovery_rank']):>3} {int(r['validation_rank']):>3} "
              f"{delta_str:>4} {r['category']:>3} {r['drug_name']:<22} "
              f"{r['mean_pred_ic50']:>9.4f} {r['discovery_score']:>8.4f} "
              f"{r['target_class']:<10}{marker}")

    # ── 5. Validation vs Discovery 비교 ──
    print(f"\n{'='*70}")
    print(f"  Validation Ranking vs Discovery Ranking 비교")
    print(f"{'='*70}")

    val_top15_ids = set(df.head(15)["canonical_drug_id"].values)
    disc_top15_ids = set(top15["canonical_drug_id"].values)

    entered = disc_top15_ids - val_top15_ids
    exited = val_top15_ids - disc_top15_ids

    entered_drugs = result[result["canonical_drug_id"].isin(entered)][
        ["discovery_rank", "validation_rank", "drug_name", "category", "discovery_score"]
    ].sort_values("discovery_rank")

    exited_drugs = result[result["canonical_drug_id"].isin(exited)][
        ["discovery_rank", "validation_rank", "drug_name", "category", "discovery_score"]
    ].sort_values("validation_rank")

    print(f"\n  신규 진입 (Discovery Top 15에만):")
    if len(entered_drugs) > 0:
        for _, r in entered_drugs.iterrows():
            print(f"    D#{int(r['discovery_rank'])} ← V#{int(r['validation_rank'])} "
                  f"{r['drug_name']} (Cat {r['category']}, score={r['discovery_score']:.4f})")
    else:
        print(f"    없음")

    print(f"\n  탈락 (Validation Top 15에만):")
    if len(exited_drugs) > 0:
        for _, r in exited_drugs.iterrows():
            print(f"    V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
                  f"{r['drug_name']} (Cat {r['category']}, score={r['discovery_score']:.4f})")
    else:
        print(f"    없음")

    # ── 6. Category 분포 변화 ──
    print(f"\n{'='*70}")
    print(f"  Category 분포 변화")
    print(f"{'='*70}")

    val_top15_cats = df.head(15)["drug_name"].map(get_category).value_counts().sort_index()
    disc_top15_cats = top15["category"].value_counts().sort_index()

    cat_labels = {"A": "Known BRCA", "B": "BRCA 연구", "C": "완전 재창출"}
    print(f"\n  {'Cat':<3} {'Label':<15} {'Validation':>10} {'Discovery':>10} {'변화':>8}")
    print(f"  {'-'*52}")
    for cat in ["A", "B", "C"]:
        v_cnt = int(val_top15_cats.get(cat, 0))
        d_cnt = int(disc_top15_cats.get(cat, 0))
        diff = d_cnt - v_cnt
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"  {cat:<3} {cat_labels[cat]:<15} {v_cnt:>10} {d_cnt:>10} {diff_str:>8}")

    v_a_pct = int(val_top15_cats.get("A", 0)) / 15 * 100
    d_a_pct = int(disc_top15_cats.get("A", 0)) / 15 * 100
    print(f"\n  Category A 비율: {v_a_pct:.0f}% → {d_a_pct:.0f}%")

    # ── 7. 가장 큰 순위 변동 ──
    print(f"\n{'='*70}")
    print(f"  Top 5 순위 상승 / 하락")
    print(f"{'='*70}")

    result["rank_delta"] = result["validation_rank"] - result["discovery_rank"]

    top_risers = result.nlargest(5, "rank_delta")
    top_fallers = result.nsmallest(5, "rank_delta")

    print(f"\n  순위 상승 (Discovery에서 유리):")
    for _, r in top_risers.iterrows():
        print(f"    {r['drug_name']:<22} V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
              f"(Δ+{int(r['rank_delta'])}, Cat {r['category']}, "
              f"target={r['target_class']})")

    print(f"\n  순위 하락 (Discovery에서 불리):")
    for _, r in top_fallers.iterrows():
        print(f"    {r['drug_name']:<22} V#{int(r['validation_rank'])} → D#{int(r['discovery_rank'])} "
              f"(Δ{int(r['rank_delta'])}, Cat {r['category']}, "
              f"target={r['target_class']})")

    # ── 8. 저장 ──
    # Discovery Top 15 CSV
    save_cols = [
        "discovery_rank", "validation_rank", "canonical_drug_id",
        "drug_name", "category", "target", "pathway",
        "mean_pred_ic50", "sensitivity_rate", "n_samples",
        "known_penalty", "target_novelty", "target_class",
        "pathway_novelty", "combined_novelty",
        "efficacy_component", "novelty_factor", "discovery_score",
    ]
    csv_path = OUTPUT_DIR / "discovery_top15_20260413.csv"
    top15[save_cols].to_csv(csv_path, index=False)
    print(f"\n  Saved CSV (Top 15): {csv_path}")

    # Full 28 CSV
    full_csv = OUTPUT_DIR / "discovery_full28_20260413.csv"
    result[save_cols + ["rank_delta"]].to_csv(full_csv, index=False)
    print(f"  Saved CSV (Full 28): {full_csv}")

    # JSON summary
    json_path = OUTPUT_DIR / "discovery_ranking_summary.json"
    summary = {
        "description": "Discovery-oriented Ranking (novelty-weighted)",
        "formula": "discovery_score = (-pred_IC50) × (1 - known_penalty) × (target_novelty×0.5 + pathway_novelty×0.5)",
        "n_drugs": len(result),
        "top15_discovery": top15[save_cols].to_dict(orient="records"),
        "comparison": {
            "entered_discovery_top15": entered_drugs.to_dict(orient="records") if len(entered_drugs) > 0 else [],
            "exited_discovery_top15": exited_drugs.to_dict(orient="records") if len(exited_drugs) > 0 else [],
        },
        "category_distribution": {
            "validation_top15": val_top15_cats.to_dict(),
            "discovery_top15": disc_top15_cats.to_dict(),
        },
        "scoring_params": {
            "known_penalty": {"A": 0.5, "B_advanced": 0.3, "B_early": 0.1, "C": 0.0},
            "target_novelty": {"standard": 0.2, "moderate": 0.5, "novel": 1.0},
            "pathway_novelty": PATHWAY_NOVELTY_MAP,
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
