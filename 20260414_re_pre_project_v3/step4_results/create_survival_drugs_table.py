#!/usr/bin/env python3
"""
Survival 유의 약물 (Top 30 밖) 상세 테이블 생성
"""

import pandas as pd
import json

# ============================================================================
# 데이터 로드
# ============================================================================

# Drug annotations
annotations = pd.read_parquet("20260414_re_pre_project_v3/20260414_re_pre_project_v3/data/drug_info/gdsc2_drug_annotation_master_20260406.parquet")

# Survival 약물 목록
target_drugs = {
    '1180': {'name': 'Dinaciclib', 'p_value': 0.0466, 'drug_idx': 75},
    '2043': {'name': 'BIBR-1532', 'p_value': 0.0101, 'drug_idx': 209},
    '1248': {'name': 'Daporinad', 'p_value': 0.0500, 'drug_idx': 85},
    '2439': {'name': 'glutathione', 'p_value': 0.0407, 'drug_idx': 240},
    '1559': {'name': 'Luminespib', 'p_value': 0.0905, 'drug_idx': 109},
    '1908': {'name': 'Ulixertinib', 'p_value': 0.0325, 'drug_idx': 176},
    '1549': {'name': 'Sapitinib', 'p_value': 0.3806, 'drug_idx': 105},
    '1057': {'name': 'Dactolisib', 'p_value': 0.0806, 'drug_idx': 44},
}

# 유방암 연구 정보
brca_research = {
    "dinaciclib": "CDK inhibitor, 유방암 Phase II",
    "luminespib": "HSP90 inhibitor, 유방암 Phase I/II",
    "sapitinib": "EGFR/HER2 inhibitor, 유방암 Phase II",
    "dactolisib": "PI3K/mTOR inhibitor, 유방암 Phase I/II",
}

# ============================================================================
# 테이블 생성
# ============================================================================

results = []

for drug_id, info in target_drugs.items():
    drug_name = info['name']
    p_value = info['p_value']
    drug_idx = info['drug_idx']

    # Annotations에서 정보 추출
    match = annotations[annotations['DRUG_ID'].astype(str) == drug_id]

    if not match.empty:
        target = match.iloc[0]['PUTATIVE_TARGET']
        pathway = match.iloc[0]['PATHWAY_NAME']
    else:
        target = 'Unknown'
        pathway = 'Unknown'

    # 유방암 연구 여부
    normalized = drug_name.lower().replace("-", "").replace(" ", "")
    brca_status = brca_research.get(normalized, "미확인")
    category = "연구 중" if brca_status != "미확인" else "미적용"

    results.append({
        '순번': len(results) + 1,
        '약물명': drug_name,
        'Drug ID': drug_id,
        'drug_idx': drug_idx,
        'Target': target,
        'Pathway': pathway,
        'FDA 승인': 'No',
        '유방암 연구': brca_status,
        '카테고리': category,
        'Survival p-value': p_value,
        'IC50 순위': '>30 (Top 30 밖)',
    })

df = pd.DataFrame(results)

# ============================================================================
# 출력
# ============================================================================

print("=" * 160)
print("Survival 유의 약물 (Top 30 밖 8개) - 상세 정보")
print("=" * 160)

print("\n" + "=" * 160)
print(f"{'순번':^6} | {'약물명':^20} | {'Target':^40} | {'Pathway':^25} | {'유방암 연구':^45} | {'카테고리':^10} | {'p-value':^10}")
print("=" * 160)

for _, row in df.iterrows():
    print(f"{row['순번']:^6} | {row['약물명']:^20} | {row['Target']:^40} | {row['Pathway']:^25} | {row['유방암 연구']:^45} | {row['카테고리']:^10} | {row['Survival p-value']:^10.4f}")

print("=" * 160)

print("\n📊 요약:")
print(f"  - 총 8개 약물 (모두 Top 30 밖)")
print(f"  - 연구 중: {(df['카테고리'] == '연구 중').sum()}개")
print(f"  - 미적용: {(df['카테고리'] == '미적용').sum()}개")
print(f"  - 가장 유의미한 p-value: {df['Survival p-value'].min():.4f} ({df.loc[df['Survival p-value'].idxmin(), '약물명']})")

print("\n🎯 유방암 관련 약물 (4개):")
research_drugs = df[df['카테고리'] == '연구 중']
for _, row in research_drugs.iterrows():
    print(f"  {row['순번']}. {row['약물명']:20s} - {row['유방암 연구']}")

print("\n⚠️  유방암 연구 미확인 약물 (4개):")
novel_drugs = df[df['카테고리'] == '미적용']
for _, row in novel_drugs.iterrows():
    print(f"  {row['순번']}. {row['약물명']:20s} - Target: {row['Target']}")

# CSV 저장
df.to_csv("survival_drugs_outside_top30_detailed.csv", index=False, encoding='utf-8-sig')
print("\n✓ survival_drugs_outside_top30_detailed.csv 저장")

# ============================================================================
# 추가 분석: Pathway 분포
# ============================================================================

print("\n📈 Pathway 분포:")
pathway_counts = df['Pathway'].value_counts()
for pathway, count in pathway_counts.items():
    print(f"  - {pathway}: {count}개")

print("\n" + "=" * 160)
