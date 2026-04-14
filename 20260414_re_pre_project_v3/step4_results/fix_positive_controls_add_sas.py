#!/usr/bin/env python3
"""
Positive Control 중복 제거 + SA Score 추가
"""

import pandas as pd
import numpy as np
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import RDConfig, Descriptors
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# SA Score 설정
# ============================================================================
try:
    sys.path.append(os.path.join(RDConfig.RDContribDir, 'SA_Score'))
    import sascorer
    HAS_SAS = True
    print("✓ SA_Score 모듈 로드 성공")
except:
    HAS_SAS = False
    print("⚠ SA_Score 모듈 없음, SAS 계산 스킵")

# ============================================================================
# 경로
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

INPUT_VALIDATION = BASE_DIR / "step6_final/validation_top.csv"
INPUT_POSITIVE = BASE_DIR / "step6_final/positive_controls.csv"
INPUT_COMPREHENSIVE = BASE_DIR / "step6_final/step7_comprehensive_final.csv"

OUTPUT_DIR = BASE_DIR / "step6_final"

print("=" * 140)
print("Positive Control 중복 제거 + SA Score 추가")
print("=" * 140)

# ============================================================================
# 1. Positive Control 중복 제거
# ============================================================================
print("\n[Step 1] Positive Control 중복 제거")
print("=" * 140)

# 기존 Positive Control 로드
pc = pd.read_csv(INPUT_POSITIVE)
print(f"✓ 기존 Positive Control: {len(pc)}개")

# 중복 확인
dup_drugs = pc[pc.duplicated('drug_name', keep=False)]
if len(dup_drugs) > 0:
    print(f"\n중복 약물 발견:")
    for name in dup_drugs['drug_name'].unique():
        dup_rows = pc[pc['drug_name'] == name]
        print(f"  - {name}: {len(dup_rows)}개")
        for idx, row in dup_rows.iterrows():
            print(f"    → rank={row.get('rank', '?')}, score={row.get('final_score', 0):.4f}")

    # 중복 제거 (final_score 높은 것만 유지)
    pc_dedup = pc.sort_values('final_score', ascending=False).drop_duplicates('drug_name', keep='first')
    removed = len(pc) - len(pc_dedup)
    print(f"\n✓ 중복 제거: {removed}개 제거, {len(pc_dedup)}개 남음")

    # 부족한 만큼 validation에서 추가
    validation = pd.read_csv(INPUT_VALIDATION)
    validation_sorted = validation.sort_values('final_score', ascending=False)

    # 이미 선정된 약물 제외
    selected_drugs = set(pc_dedup['drug_name'])
    remaining = validation_sorted[~validation_sorted['drug_name'].isin(selected_drugs)]

    # 부족한 개수만큼 추가
    need = 5 - len(pc_dedup)
    if need > 0 and len(remaining) >= need:
        additional = remaining.head(need).copy()
        additional['control_rank'] = range(len(pc_dedup) + 1, len(pc_dedup) + need + 1)

        pc_final = pd.concat([pc_dedup, additional], ignore_index=True)
        print(f"\n✓ 추가: {need}개")
        for _, row in additional.iterrows():
            print(f"  - {row['drug_name']}: score={row['final_score']:.4f}")
    else:
        pc_final = pc_dedup

    # control_rank 재정렬
    pc_final = pc_final.sort_values('final_score', ascending=False).reset_index(drop=True)
    pc_final['control_rank'] = range(1, len(pc_final) + 1)

else:
    pc_final = pc
    print("✓ 중복 없음")

# 저장
pc_final.to_csv(OUTPUT_DIR / "positive_controls.csv", index=False)
print(f"\n✓ positive_controls.csv 업데이트 ({len(pc_final)}개)")

# ============================================================================
# 2. SA Score 추가
# ============================================================================
print("\n[Step 2] SA Score 추가 (전체 20개)")
print("=" * 140)

# Comprehensive 데이터 로드
df = pd.read_csv(INPUT_COMPREHENSIVE)

print(f"✓ 전체 약물: {len(df)}개")

# SA Score 계산
if HAS_SAS:
    sas_scores = []
    for idx, row in df.iterrows():
        smiles = row.get('smiles')
        if smiles and not pd.isna(smiles):
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                sas = sascorer.calculateScore(mol)
                sas_scores.append(sas)
                print(f"  [{idx+1}/{len(df)}] {row['drug_name']:20s}: SAS={sas:.2f}")
            else:
                sas_scores.append(np.nan)
                print(f"  [{idx+1}/{len(df)}] {row['drug_name']:20s}: SAS=N/A (invalid SMILES)")
        else:
            sas_scores.append(np.nan)
            print(f"  [{idx+1}/{len(df)}] {row['drug_name']:20s}: SAS=N/A (no SMILES)")

    df['SAS'] = sas_scores
    print(f"\n✓ SA Score 계산 완료")
else:
    df['SAS'] = np.nan
    print("⚠ SA Score 스킵")

# 저장
df.to_csv(OUTPUT_DIR / "step7_comprehensive_final.csv", index=False)
print(f"✓ step7_comprehensive_final.csv 업데이트")

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 140)
print("✅ 완료")
print("=" * 140)

print(f"\n1. Positive Control:")
print(f"   - 최종: {len(pc_final)}개")
for _, row in pc_final.iterrows():
    print(f"     {row['control_rank']}. {row['drug_name']:20s}: {row['final_score']:.4f}")

if HAS_SAS:
    print(f"\n2. SA Score:")
    sas_valid = df['SAS'].dropna()
    if len(sas_valid) > 0:
        print(f"   - 계산 성공: {len(sas_valid)}/{len(df)}개")
        print(f"   - 평균: {sas_valid.mean():.2f}")
        print(f"   - 범위: {sas_valid.min():.2f} ~ {sas_valid.max():.2f}")
        print(f"   - 합성 난이도: 1~3=Easy, 4~6=Moderate, 7~10=Hard")

print("\n생성 파일:")
print("  - positive_controls.csv (중복 제거)")
print("  - step7_comprehensive_final.csv (SAS 추가)")
print("=" * 140)
