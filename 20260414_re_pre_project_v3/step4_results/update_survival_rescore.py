#!/usr/bin/env python3
"""
Survival 매핑 완료 후 전체 재계산
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

INPUT_MAPPING = BASE_DIR / "survival_drug_mapping_final.json"
INPUT_TOP30 = BASE_DIR / "step6_final/step6_top30_full.csv"
OUTPUT_DIR = BASE_DIR / "step6_final"

print("=" * 100)
print("Survival 매핑 완료 후 전체 재계산")
print("=" * 100)

# ============================================================================
# 1. Survival 매핑 로드
# ============================================================================
print("\n[Step 1] Survival 매핑 로드")
print("=" * 100)

with open(INPUT_MAPPING) as f:
    survival_mapping = json.load(f)

print(f"✓ 로드: {len(survival_mapping)}개")
print(f"\n{'drug_idx':>10} | {'canonical_drug_id':>18} | {'drug_name':>30} | {'p_value':>10}")
print("-" * 80)
for m in survival_mapping:
    print(f"{m['drug_idx']:>10} | {m['canonical_drug_id']:>18} | {m['drug_name']:>30} | {m['p_value']:>10.4f}")

# canonical_drug_id → p_value 맵 생성
survival_map = {}
for m in survival_mapping:
    canonical_id = str(m['canonical_drug_id'])
    p_value = m['p_value']
    survival_map[canonical_id] = p_value
    survival_map[int(canonical_id)] = p_value  # 정수 버전도 추가

# ============================================================================
# 2. Top 30 로드 및 survival_score 업데이트
# ============================================================================
print("\n[Step 2] Top 30 로드 및 survival_score 업데이트")
print("=" * 100)

df = pd.read_csv(INPUT_TOP30)
print(f"✓ Top 30 로드: {len(df)}개")

# Before 통계
before_survival_count = (df['survival_score'] > 0).sum()
print(f"✓ 업데이트 전 survival_score > 0: {before_survival_count}개")

# Survival score 업데이트
updated_count = 0
for idx, row in df.iterrows():
    canonical_id = row['canonical_drug_id']

    # survival_map에서 p_value 찾기
    p_value = survival_map.get(canonical_id) or survival_map.get(str(canonical_id))

    if p_value is not None:
        # p_value가 낮을수록 생존 예측 개선 (1.0 - p_value)
        survival_score = max(0, 1.0 - p_value)
        df.at[idx, 'survival_p'] = p_value
        df.at[idx, 'survival_score'] = survival_score
        updated_count += 1
        print(f"  ✓ {row['drug_name']:20s} → p={p_value:.4f}, survival_score={survival_score:.4f}")

# After 통계
after_survival_count = (df['survival_score'] > 0).sum()
print(f"\n✓ 업데이트 후 survival_score > 0: {after_survival_count}개 (+{after_survival_count - before_survival_count})")

# ============================================================================
# 3. Multi-objective scoring 재계산
# ============================================================================
print("\n[Step 3] Multi-objective scoring 재계산")
print("=" * 100)

# IC50, Tanimoto, Target, Clinical은 그대로, Survival만 업데이트
# Final score = 0.30*ic50 + 0.20*survival + 0.20*tanimoto + 0.20*target + 0.10*clinical

for idx, row in df.iterrows():
    ic50_score = row['ic50_score']
    survival_score = row['survival_score']
    tanimoto_score = row['tanimoto']
    target_score = row['target_score']
    clinical_score = row['clinical_score']

    final_score = (
        0.30 * ic50_score +
        0.20 * survival_score +
        0.20 * tanimoto_score +
        0.20 * target_score +
        0.10 * clinical_score
    )

    old_score = row['final_score']
    df.at[idx, 'final_score'] = final_score

    if abs(final_score - old_score) > 0.01:  # 변화가 있으면 출력
        print(f"  {row['drug_name']:20s}: {old_score:.4f} → {final_score:.4f} (Δ={final_score - old_score:+.4f})")

# ============================================================================
# 4. 결과 저장
# ============================================================================
print("\n[Step 4] 결과 저장")
print("=" * 100)

# CSV 저장
df.to_csv(OUTPUT_DIR / "step6_top30_full.csv", index=False)
print("✓ step6_top30_full.csv 업데이트")

# JSON 요약
subtype_counts = {
    'ER+': int(df['subtypes'].str.contains(r'ER\+', regex=True).sum()),
    'HER2+': int(df['subtypes'].str.contains(r'HER2\+', regex=True).sum()),
    'TNBC': int(df['subtypes'].str.contains('TNBC').sum()),
}

category_counts = df['category'].value_counts().to_dict()

summary = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_drugs': len(df),
    'final_score_stats': {
        'max': float(df['final_score'].max()),
        'min': float(df['final_score'].min()),
        'mean': float(df['final_score'].mean()),
    },
    'survival_non_zero': int(after_survival_count),
    'target_non_zero': int((df['target_score'] > 0).sum()),
    'category_distribution': {k: int(v) for k, v in category_counts.items()},
    'subtype_coverage': subtype_counts,
}

with open(OUTPUT_DIR / "step6_top30_full.json", 'w') as f:
    json.dump(summary, f, indent=2)

print("✓ step6_top30_full.json 업데이트")

# ============================================================================
# 5. Before/After 비교
# ============================================================================
print("\n[Step 5] Before/After 비교")
print("=" * 100)

print(f"\nSurvival 매핑: {before_survival_count}개 → {after_survival_count}개 (+{after_survival_count - before_survival_count})")
print(f"\nTop 5 약물 (Final Score 기준):")
top5 = df.nlargest(5, 'final_score')
for idx, row in top5.iterrows():
    print(f"  {row['rank']:2d}. {row['drug_name']:20s}: {row['final_score']:.4f} (survival_score={row['survival_score']:.4f})")

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 100)
print("✅ Survival 업데이트 완료")
print("=" * 100)

print(f"\n핵심 개선:")
print(f"  - Survival mapping: 1개 → {after_survival_count}개 (+{after_survival_count - 1})")
print(f"  - Multi-objective scoring 재계산 완료")
print(f"  - Top 30 결과 업데이트 완료")

print("\n다음 단계: Top 15 재선정 필요")
print("=" * 100)
