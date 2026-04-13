#!/usr/bin/env python3
"""
Step 1: Top 30 중복 약물 통합 처리
═══════════════════════════════════════════════════════════════
  - Docetaxel: 1819(rank1) + 1007(rank4) → 1819 대표 (pred IC50 더 낮음)
  - Dactinomycin: 1811(rank2) + 1911(rank8) → 1811 대표 (rank 더 높음)
  - 제거 ID + 사유 JSON 저장
  - 결과: top30_dedup_20260413.csv (28개, 재랭킹)
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import json
import time
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_CSV = PROJECT_ROOT / "results" / "top30_reextract_20260413" / "top30_reextract.csv"
OUTPUT_DIR = PROJECT_ROOT / "results" / "top30_dedup_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 중복 통합 규칙
DEDUP_RULES = {
    "Docetaxel": {
        "keep_id": "1819",
        "remove_id": "1007",
        "reason": "동일 약물, 1819가 pred IC50 더 낮음 (-4.082 vs -1.731)",
    },
    "Dactinomycin": {
        "keep_id": "1811",
        "remove_id": "1911",
        "reason": "동일 약물, 1811이 rank 더 높음 (rank 2 vs rank 8)",
    },
}


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Step 1: Top 30 중복 약물 통합 처리")
    print("=" * 70)

    # ── 1. 입력 로드 ──
    print(f"\n  Loading: {INPUT_CSV.name}")
    df = pd.read_csv(INPUT_CSV)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    print(f"    Shape: {df.shape}")
    print(f"    Drugs: {len(df)}")

    # ── 2. 중복 확인 ──
    print(f"\n  중복 약물 확인:")
    dup_names = df["drug_name"].value_counts()
    dup_names = dup_names[dup_names > 1]

    if len(dup_names) == 0:
        print("    중복 없음 → 종료")
        return

    for name, cnt in dup_names.items():
        ids = df[df["drug_name"] == name]["canonical_drug_id"].tolist()
        ranks = df[df["drug_name"] == name]["rank"].tolist()
        ic50s = df[df["drug_name"] == name]["mean_pred_ic50"].tolist()
        print(f"    {name}: {cnt}개 (IDs={ids}, ranks={ranks}, IC50={[f'{x:.3f}' for x in ic50s]})")

    # ── 3. 중복 제거 ──
    removal_log = []
    remove_ids = set()

    for drug_name, rule in DEDUP_RULES.items():
        keep_id = rule["keep_id"]
        remove_id = rule["remove_id"]

        # 대표 ID 존재 확인
        keep_row = df[df["canonical_drug_id"] == keep_id]
        remove_row = df[df["canonical_drug_id"] == remove_id]

        if keep_row.empty:
            print(f"    WARNING: 대표 ID {keep_id} ({drug_name}) 없음 → skip")
            continue
        if remove_row.empty:
            print(f"    WARNING: 제거 ID {remove_id} ({drug_name}) 없음 → skip")
            continue

        keep_rank = int(keep_row["rank"].values[0])
        keep_ic50 = float(keep_row["mean_pred_ic50"].values[0])
        remove_rank = int(remove_row["rank"].values[0])
        remove_ic50 = float(remove_row["mean_pred_ic50"].values[0])

        removal_log.append({
            "drug_name": drug_name,
            "removed_id": remove_id,
            "removed_rank": remove_rank,
            "removed_ic50": remove_ic50,
            "kept_id": keep_id,
            "kept_rank": keep_rank,
            "kept_ic50": keep_ic50,
            "reason": rule["reason"],
        })
        remove_ids.add(remove_id)

        print(f"\n    {drug_name}:")
        print(f"      KEEP   → ID={keep_id} (rank={keep_rank}, IC50={keep_ic50:.4f})")
        print(f"      REMOVE → ID={remove_id} (rank={remove_rank}, IC50={remove_ic50:.4f})")
        print(f"      사유: {rule['reason']}")

    # ── 4. 필터링 및 재랭킹 ──
    df_dedup = df[~df["canonical_drug_id"].isin(remove_ids)].copy()
    df_dedup = df_dedup.sort_values("mean_pred_ic50", ascending=True)
    df_dedup["rank"] = range(1, len(df_dedup) + 1)

    print(f"\n  결과: {len(df)} → {len(df_dedup)} drugs (제거: {len(remove_ids)})")

    # ── 5. 결과 출력 ──
    print(f"\n{'='*90}")
    print(f"  DEDUP TOP {len(df_dedup)} (재랭킹)")
    print(f"{'='*90}")
    print(f"  {'Rank':>4}  {'ID':>6}  {'Drug':<22} {'Pred IC50':>10} {'True IC50':>10} "
          f"{'Sens%':>6} {'N':>3}")
    print(f"  {'-'*75}")

    for _, r in df_dedup.iterrows():
        print(f"  {int(r['rank']):>4}  {r['canonical_drug_id']:>6}  "
              f"{str(r.get('drug_name', 'N/A')):<22} "
              f"{r['mean_pred_ic50']:>10.4f} {r['mean_true_ic50']:>10.4f} "
              f"{r['sensitivity_rate']:>5.0%} {int(r['n_samples']):>3}")

    # ── 6. 저장 ──
    # CSV
    csv_path = OUTPUT_DIR / "top30_dedup_20260413.csv"
    df_dedup.to_csv(csv_path, index=False)
    print(f"\n  Saved CSV: {csv_path}")
    print(f"    Rows: {len(df_dedup)}, Cols: {list(df_dedup.columns)}")

    # JSON (제거 기록)
    json_path = OUTPUT_DIR / "dedup_removal_log.json"
    log_data = {
        "description": "Top 30 중복 약물 통합 기록",
        "original_count": len(df),
        "dedup_count": len(df_dedup),
        "removed_count": len(remove_ids),
        "rules": {name: rule for name, rule in DEDUP_RULES.items()},
        "removal_log": removal_log,
        "removed_ids": sorted(remove_ids),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    print(f"  Saved JSON: {json_path}")

    dt = time.time() - t0
    print(f"\n  Completed in {dt:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
