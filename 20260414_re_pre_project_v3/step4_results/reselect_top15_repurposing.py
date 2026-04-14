#!/usr/bin/env python3
"""
Top 15 재선정: 치료제 분리, 재창출 전용
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

INPUT_TOP30 = BASE_DIR / "step6_final/step6_top30_full.csv"
OUTPUT_DIR = BASE_DIR / "step6_final"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# FDA 유방암 승인 약물 목록 (정규화용)
# ============================================================================
FDA_BRCA_DRUGS = {
    "docetaxel", "paclitaxel", "vinblastine", "vinorelbine",
    "doxorubicin", "epirubicin", "cyclophosphamide", "capecitabine",
    "methotrexate", "fluorouracil", "carboplatin", "cisplatin",
    "gemcitabine", "eribulin", "irinotecan", "mitoxantrone",
    "tamoxifen", "letrozole", "anastrozole", "exemestane",
    "fulvestrant", "trastuzumab", "pertuzumab", "lapatinib",
    "neratinib", "tucatinib", "palbociclib", "ribociclib",
    "abemaciclib", "olaparib", "talazoparib", "alpelisib",
    "sacituzumab", "pembrolizumab", "topotecan"
}

def normalize_name(name):
    """약물명 정규화 (소문자, 공백/하이픈/언더스코어 제거)"""
    if pd.isna(name):
        return ""
    return str(name).lower().replace(" ", "").replace("-", "").replace("_", "")

# ============================================================================
# MAIN
# ============================================================================
print("=" * 100)
print("Top 15 재선정: 치료제 분리, 재창출 전용")
print("=" * 100)

# ============================================================================
# 1. Validation 분리 (검증용)
# ============================================================================
print("\n[Step 1] Validation 분리 (FDA 유방암 치료제)")
print("=" * 100)

df_top30 = pd.read_csv(INPUT_TOP30)

# FDA 치료제 추출
df_top30['normalized_name'] = df_top30['drug_name'].apply(normalize_name)
df_top30['is_fda_brca'] = df_top30['normalized_name'].isin(FDA_BRCA_DRUGS)

validation_drugs = df_top30[df_top30['is_fda_brca']].copy()
validation_drugs = validation_drugs.sort_values('rank').reset_index(drop=True)

print(f"✓ FDA 유방암 치료제: {len(validation_drugs)}개")
for _, row in validation_drugs.iterrows():
    print(f"  - {row['drug_name']} (rank={row['rank']}, score={row['final_score']:.4f})")

validation_drugs.to_csv(OUTPUT_DIR / "validation_top.csv", index=False)

# ============================================================================
# 2. Repurposing 후보 필터링
# ============================================================================
print("\n[Step 2] Repurposing 후보 필터링 (FDA 치료제 제외)")
print("=" * 100)

repurposing_candidates = df_top30[~df_top30['is_fda_brca']].copy()
print(f"✓ 재창출 후보: {len(repurposing_candidates)}개")

# ============================================================================
# 3. 중복 제거
# ============================================================================
print("\n[Step 3] 중복 제거 (drug_name 기준, final_score 최대)")
print("=" * 100)

# drug_name으로 그룹화하여 final_score가 가장 높은 것만 유지
repurposing_dedup = repurposing_candidates.sort_values('final_score', ascending=False).drop_duplicates(
    subset='drug_name', keep='first'
).reset_index(drop=True)

removed_count = len(repurposing_candidates) - len(repurposing_dedup)
print(f"✓ 중복 제거: {removed_count}개")
print(f"✓ 남은 후보: {len(repurposing_dedup)}개")

# ============================================================================
# 4. Top 15 선정
# ============================================================================
print("\n[Step 4] Top 15 선정 (final_score 내림차순)")
print("=" * 100)

# final_score로 정렬
repurposing_sorted = repurposing_dedup.sort_values('final_score', ascending=False).reset_index(drop=True)

# Top 15 선택 (후보가 15개 미만이면 전부 사용)
n_candidates = len(repurposing_sorted)
n_select = min(15, n_candidates)

top15_repurposing = repurposing_sorted.head(n_select).copy()
top15_repurposing['repurposing_rank'] = range(1, n_select + 1)

print(f"✓ 선정: {n_select}개")
for idx, row in top15_repurposing.iterrows():
    print(f"  [{row['repurposing_rank']}] {row['drug_name']}: score={row['final_score']:.4f}, category={row['category']}")

# ============================================================================
# 5. 결과 저장
# ============================================================================
print("\n[Step 5] 결과 저장")
print("=" * 100)

top15_repurposing.to_csv(OUTPUT_DIR / "repurposing_top15.csv", index=False)

# JSON 기본 통계
n_approved = len(top15_repurposing[top15_repurposing['category'] == "Category 1: 유방암 치료제 (FDA 승인)"])
n_research = len(top15_repurposing[top15_repurposing['category'] == "Category 2: 유방암 연구 중"])
n_novel = len(top15_repurposing[top15_repurposing['category'] == "Category 3: 유방암 미적용"])

repurposing_basic = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_total': n_select,
    'n_approved': n_approved,
    'n_research': n_research,
    'n_novel': n_novel,
}

with open(OUTPUT_DIR / "repurposing_top15.json", 'w') as f:
    json.dump(repurposing_basic, f, indent=2)

print(f"✓ repurposing_top15.csv 저장")
print(f"✓ repurposing_top15.json 저장")

# ============================================================================
# 6. 추가 분석
# ============================================================================
print("\n[Step 6] 추가 분석")
print("=" * 100)

# MOA 분포
pathway_counts = Counter(top15_repurposing['pathway'].dropna())
moa_distribution = dict(pathway_counts.most_common(10))

print(f"✓ MOA 분포:")
for moa, count in moa_distribution.items():
    print(f"  - {moa}: {count}개")

# Target coverage
all_targets = []
for targets_str in top15_repurposing['target_matches'].dropna():
    if targets_str != 'None':
        all_targets.extend([t.strip() for t in str(targets_str).split(',')])

unique_targets = set(all_targets)
target_coverage = len(unique_targets)

print(f"\n✓ Target coverage: {target_coverage}개 고유 타겟")
print(f"  Targets: {', '.join(sorted(unique_targets))}")

# Subtype coverage
subtype_counts = {
    'ER+': int(top15_repurposing['subtypes'].str.contains(r'ER\+', regex=True).sum()),
    'HER2+': int(top15_repurposing['subtypes'].str.contains(r'HER2\+', regex=True).sum()),
    'TNBC': int(top15_repurposing['subtypes'].str.contains('TNBC').sum()),
}

print(f"\n✓ Subtype coverage:")
for subtype, count in subtype_counts.items():
    print(f"  - {subtype}: {count}개")

# Top30 대비 Jaccard
top30_drugs = set(df_top30['drug_name'])
top15_drugs = set(top15_repurposing['drug_name'])
intersection = top30_drugs & top15_drugs
union = top30_drugs | top15_drugs
jaccard = len(intersection) / len(union) if len(union) > 0 else 0.0

print(f"\n✓ Jaccard similarity with Top 30: {jaccard:.4f}")

# ============================================================================
# 약물별 추천 이유 + 한계/주의사항
# ============================================================================
drug_details = []

for idx, row in top15_repurposing.iterrows():
    drug_name = row['drug_name']
    category = row['category']
    target = row.get('target_matches', 'Unknown')
    pathway = row.get('pathway', 'Unknown')
    subtypes = row.get('subtypes', 'Unknown')
    final_score = row['final_score']
    tanimoto = row.get('tanimoto', 0.0)
    survival_score = row.get('survival_score', 0.0)

    # 추천 이유
    reasons = []
    if final_score > 0.3:
        reasons.append("높은 multi-objective score")
    if tanimoto > 0.3:
        reasons.append(f"FDA 유방암 약물과 높은 유사도 (Tanimoto={tanimoto:.2f})")
    if survival_score > 0.5:
        reasons.append("생존 예측 개선 가능성")
    if target != 'None' and target != 'Unknown':
        reasons.append(f"유방암 관련 타겟 ({target})")
    if category == "Category 2: 유방암 연구 중":
        reasons.append("유방암 임상 연구 진행 중")

    if not reasons:
        reasons.append("IC50 예측 기반 선정")

    # 한계/주의사항
    limitations = []
    if tanimoto < 0.1:
        limitations.append("FDA 약물과 구조적 유사도 낮음")
    if survival_score == 0:
        limitations.append("생존 데이터 부재")
    if 'Unknown' in subtypes:
        limitations.append("서브타입 매칭 불확실")
    if category == "Category 3: 유방암 미적용":
        limitations.append("유방암 연구 사례 부족, 추가 검증 필요")

    if not limitations:
        limitations.append("일반적인 임상 검증 필요")

    drug_details.append({
        'rank': row['repurposing_rank'],
        'drug_name': drug_name,
        'category': category,
        'final_score': float(final_score),
        'target': target,
        'pathway': pathway,
        'subtypes': subtypes,
        'tanimoto': float(tanimoto),
        'survival_score': float(survival_score),
        'recommendation_reasons': reasons,
        'limitations': limitations,
    })

# ============================================================================
# Summary JSON 저장
# ============================================================================
summary = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_total': n_select,
    'category_distribution': {
        'approved': n_approved,
        'research': n_research,
        'novel': n_novel,
    },
    'moa_distribution': moa_distribution,
    'target_coverage': target_coverage,
    'unique_targets': sorted(list(unique_targets)),
    'subtype_coverage': subtype_counts,
    'jaccard_with_top30': float(jaccard),
    'drug_details': drug_details,
}

with open(OUTPUT_DIR / "repurposing_summary.json", 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"\n✓ repurposing_summary.json 저장")

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 100)
print("✅ Top 15 재선정 완료")
print("=" * 100)

print(f"\n재창출 약물 Top 15:")
print(f"  - 승인 약물: {n_approved}개")
print(f"  - 연구 중: {n_research}개")
print(f"  - 신규 재창출: {n_novel}개")

print(f"\n저장된 파일:")
print(f"  - validation_top.csv (FDA 치료제 검증용, {len(validation_drugs)}개)")
print(f"  - repurposing_top15.csv (재창출 전용, {n_select}개)")
print(f"  - repurposing_top15.json")
print(f"  - repurposing_summary.json (상세 분석)")

print("\n" + "=" * 100)
print("모든 작업 완료.")
print("=" * 100)
