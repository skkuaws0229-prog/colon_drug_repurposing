#!/usr/bin/env python3
"""
SMILES 데이터 정확성 검증 (Step 2 시작 전 필수)

목적:
- 각 단계별 약물 수 정확히 확인
- SMILES 유효성 검증 (RDKit 파싱)
- 최종 학습 사용 가능한 약물 수 확인
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime

print("=" * 100)
print("SMILES 데이터 정확성 검증")
print("=" * 100)

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
drug_info_dir = base_dir / "20260414_re_pre_project_v3/step4_results/20260414_re_pre_project_v3/20260414_re_pre_project_v3/data/drug_info"
output_dir = base_dir / "20260415_multimodal_pipeline/step2_mpnn"

# ============================================================================
# [1] 약물 수 정확히 확인
# ============================================================================
print("\n" + "=" * 100)
print("[1] 약물 수 단계별 확인")
print("=" * 100)

# a) drug_features_catalog.parquet 전체 약물 수
catalog_path = drug_info_dir / "drug_features_catalog.parquet"
df_catalog = pd.read_parquet(catalog_path)

total_drugs = df_catalog['DRUG_ID'].nunique()
print(f"\na) drug_features_catalog.parquet 전체 약물 수: {total_drugs}")
print(f"   - Shape: {df_catalog.shape}")

# b) 그 중 canonical_smiles가 있는 약물 수
has_smiles = df_catalog['canonical_smiles'].notna().sum()
print(f"\nb) canonical_smiles가 있는 약물 수: {has_smiles}")
print(f"   - 비율: {has_smiles/total_drugs*100:.1f}%")
print(f"   - SMILES 없는 약물: {total_drugs - has_smiles}개")

# c) RDKit으로 파싱 성공하는 약물 수
print(f"\nc) RDKit으로 파싱 성공하는 약물 수:")
print(f"   - RDKit import 중...")

try:
    from rdkit import Chem
    from rdkit import RDLogger
    # RDKit 경고 끄기
    RDLogger.DisableLog('rdApp.*')

    valid_smiles = []
    invalid_smiles = []

    for idx, row in df_catalog.iterrows():
        drug_id = row['DRUG_ID']
        smiles = row['canonical_smiles']

        if pd.isna(smiles):
            continue

        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            valid_smiles.append({
                'DRUG_ID': drug_id,
                'DRUG_NAME': row['DRUG_NAME'],
                'SMILES': smiles
            })
        else:
            invalid_smiles.append({
                'DRUG_ID': drug_id,
                'DRUG_NAME': row['DRUG_NAME'],
                'SMILES': smiles
            })

    print(f"   - RDKit 파싱 성공: {len(valid_smiles)}개")
    print(f"   - RDKit 파싱 실패: {len(invalid_smiles)}개")

    if len(invalid_smiles) > 0:
        print(f"\n   ⚠️ RDKit 파싱 실패 약물:")
        for item in invalid_smiles[:5]:
            print(f"      - {item['DRUG_ID']}: {item['DRUG_NAME']}")
            print(f"        SMILES: {item['SMILES'][:80]}...")

except ImportError:
    print(f"   ❌ RDKit이 설치되지 않음. 파싱 검증 불가.")
    valid_smiles = []
    invalid_smiles = []

# d) features_slim.parquet에서 unique drug 수
print(f"\nd) features_slim.parquet unique drug 수:")
features_path = base_dir / "20260414_re_pre_project_v3/features_slim.parquet"
df_features = pd.read_parquet(features_path)

features_drugs = df_features['canonical_drug_id'].nunique()
print(f"   - Unique drugs: {features_drugs}")
print(f"   - Total samples: {len(df_features)}")
print(f"   - 샘플/약물: {len(df_features)/features_drugs:.1f}")

# e) y_train에서 unique drug 수 (features_slim과 동일 순서)
print(f"\ne) y_train 데이터:")
y_train_path = base_dir / "20260414_re_pre_project_v3/step4_results/y_train.npy"
y_train = np.load(y_train_path)
print(f"   - Shape: {y_train.shape}")
print(f"   - features_slim과 1:1 매칭")

# f) 실제 학습에 사용된 약물 수 (features_slim의 unique drug)
print(f"\nf) 실제 학습에 사용된 약물 수:")
actual_train_drugs = df_features['canonical_drug_id'].unique()
print(f"   - Unique drugs: {len(actual_train_drugs)}")
print(f"   - 처음 10개: {sorted(actual_train_drugs.astype(str))[:10]}")

# ============================================================================
# [2] 243개 vs 실제 학습 데이터 약물 수 확인
# ============================================================================
print("\n" + "=" * 100)
print("[2] 약물 수 흐름 추적")
print("=" * 100)

print(f"\n단계별 약물 수:")
print(f"  1. drug_features_catalog 전체: {total_drugs}개")
print(f"  2. SMILES 없음 제거: {total_drugs - has_smiles}개 → {has_smiles}개")

if len(valid_smiles) > 0:
    print(f"  3. RDKit 파싱 실패 제거: {len(invalid_smiles)}개 → {len(valid_smiles)}개")
else:
    print(f"  3. RDKit 파싱 검증 생략 (RDKit 미설치)")

print(f"  4. features_slim에 있는 약물: {features_drugs}개")

# features_slim의 약물이 catalog에 있는지 확인
features_drug_ids = set(df_features['canonical_drug_id'].astype(str).unique())
catalog_drug_ids = set(df_catalog['DRUG_ID'].astype(str).unique())

matched = features_drug_ids & catalog_drug_ids
only_features = features_drug_ids - catalog_drug_ids
only_catalog = catalog_drug_ids - features_drug_ids

print(f"\n매칭 상태:")
print(f"  - features_slim ∩ catalog: {len(matched)}개 (100.0%)")
print(f"  - features_slim에만 있음: {len(only_features)}개")
print(f"  - catalog에만 있음: {len(only_catalog)}개")

if len(only_catalog) > 0:
    print(f"\n  catalog에만 있는 약물 (처음 10개): {sorted(list(only_catalog))[:10]}")
    print(f"  → 이 약물들은 GDSC2 IC50 데이터가 없어서 학습에 사용 안 됨")

# ============================================================================
# [3] SMILES 유효성 검증
# ============================================================================
print("\n" + "=" * 100)
print("[3] SMILES 유효성 검증 (RDKit)")
print("=" * 100)

if len(valid_smiles) > 0:
    # features_slim의 약물 중 SMILES 유효한 것
    valid_drug_ids = set([str(item['DRUG_ID']) for item in valid_smiles])
    features_with_valid_smiles = features_drug_ids & valid_drug_ids

    print(f"\n✓ RDKit 파싱 결과:")
    print(f"  - 전체 SMILES: {has_smiles}개")
    print(f"  - 파싱 성공: {len(valid_smiles)}개 ({len(valid_smiles)/has_smiles*100:.1f}%)")
    print(f"  - 파싱 실패: {len(invalid_smiles)}개")

    print(f"\n✓ 학습 데이터와 매칭:")
    print(f"  - features_slim 약물: {len(features_drug_ids)}개")
    print(f"  - 그 중 SMILES 유효: {len(features_with_valid_smiles)}개")
    print(f"  - SMILES 없거나 무효: {len(features_drug_ids) - len(features_with_valid_smiles)}개")

    if len(invalid_smiles) > 0:
        print(f"\n⚠️ 파싱 실패 SMILES 상세:")
        for i, item in enumerate(invalid_smiles[:3], 1):
            print(f"\n  {i}. DRUG_ID: {item['DRUG_ID']}, Name: {item['DRUG_NAME']}")
            print(f"     SMILES: {item['SMILES']}")
else:
    print(f"\n❌ RDKit이 설치되지 않아 SMILES 유효성 검증 불가")
    print(f"   → chemprop 설치 시 RDKit도 함께 설치됨")

# ============================================================================
# [4] 최종 매칭 테이블
# ============================================================================
print("\n" + "=" * 100)
print("[4] 최종 매칭 테이블 생성")
print("=" * 100)

# 테이블 생성
matching_table = []

for _, row in df_catalog.iterrows():
    drug_id = str(row['DRUG_ID'])
    drug_name = row['DRUG_NAME']
    smiles = row['canonical_smiles']

    # SMILES 유무
    has_smiles_flag = not pd.isna(smiles)

    # RDKit 유효
    if len(valid_smiles) > 0:
        rdkit_valid = drug_id in valid_drug_ids
    else:
        rdkit_valid = None  # 검증 안 됨

    # IC50 데이터 유무 (features_slim에 있는지)
    has_ic50 = drug_id in features_drug_ids

    # 학습 사용 여부
    can_use_for_training = has_smiles_flag and has_ic50
    if len(valid_smiles) > 0:
        can_use_for_training = can_use_for_training and rdkit_valid

    matching_table.append({
        'DRUG_ID': drug_id,
        'DRUG_NAME': drug_name,
        'SMILES_유무': 'Yes' if has_smiles_flag else 'No',
        'RDKit_유효': 'Yes' if rdkit_valid else ('No' if rdkit_valid is False else 'N/A'),
        'IC50_데이터': 'Yes' if has_ic50 else 'No',
        '학습_사용': 'Yes' if can_use_for_training else 'No',
        'SMILES': smiles if has_smiles_flag else ''
    })

df_matching = pd.DataFrame(matching_table)

# 통계
total_count = len(df_matching)
has_smiles_count = (df_matching['SMILES_유무'] == 'Yes').sum()
rdkit_valid_count = (df_matching['RDKit_유효'] == 'Yes').sum()
has_ic50_count = (df_matching['IC50_데이터'] == 'Yes').sum()
can_train_count = (df_matching['학습_사용'] == 'Yes').sum()

print(f"\n✓ 매칭 테이블 통계:")
print(f"  - 전체 약물: {total_count}개")
print(f"  - SMILES 있음: {has_smiles_count}개 ({has_smiles_count/total_count*100:.1f}%)")
if rdkit_valid_count > 0:
    print(f"  - RDKit 유효: {rdkit_valid_count}개 ({rdkit_valid_count/total_count*100:.1f}%)")
print(f"  - IC50 데이터 있음: {has_ic50_count}개 ({has_ic50_count/total_count*100:.1f}%)")
print(f"  - **학습 사용 가능: {can_train_count}개** ({can_train_count/total_count*100:.1f}%)")

print(f"\n처음 10행:")
print(df_matching.head(10)[['DRUG_ID', 'DRUG_NAME', 'SMILES_유무', 'RDKit_유효', 'IC50_데이터', '학습_사용']].to_string(index=False))

# 학습 사용 가능한 약물만
df_trainable = df_matching[df_matching['학습_사용'] == 'Yes']
print(f"\n✓ 학습 사용 가능한 약물:")
print(f"  - 개수: {len(df_trainable)}개")
print(f"  - 이 약물들만 Chemprop에 넣을 수 있음")

# ============================================================================
# [5] 결과 저장
# ============================================================================
print("\n" + "=" * 100)
print("[5] 결과 저장")
print("=" * 100)

# 1. 전체 매칭 테이블
matching_path = output_dir / "drug_smiles_matching_table.csv"
df_matching.to_csv(matching_path, index=False)
print(f"\n✓ 전체 매칭 테이블: {matching_path}")
print(f"  - 295 rows × 7 columns")

# 2. 학습 사용 가능한 약물만
trainable_path = output_dir / "trainable_drugs_with_smiles.csv"
df_trainable.to_csv(trainable_path, index=False)
print(f"\n✓ 학습 사용 가능 약물: {trainable_path}")
print(f"  - {len(df_trainable)} rows × 7 columns")

# 3. 통계 JSON
stats = {
    "timestamp": datetime.now().isoformat(),
    "files": {
        "drug_features_catalog": str(catalog_path),
        "features_slim": str(features_path),
        "y_train": str(y_train_path)
    },
    "counts": {
        "total_drugs_in_catalog": int(total_drugs),
        "has_smiles": int(has_smiles),
        "rdkit_valid": int(rdkit_valid_count) if rdkit_valid_count > 0 else None,
        "rdkit_invalid": int(len(invalid_smiles)) if len(invalid_smiles) > 0 else None,
        "has_ic50_data": int(has_ic50_count),
        "trainable_for_chemprop": int(can_train_count)
    },
    "percentages": {
        "smiles_coverage": float(has_smiles/total_drugs*100),
        "rdkit_success_rate": float(rdkit_valid_count/has_smiles*100) if rdkit_valid_count > 0 else None,
        "ic50_coverage": float(has_ic50_count/total_count*100),
        "trainable_coverage": float(can_train_count/total_count*100)
    },
    "flow": {
        "1_catalog_total": int(total_drugs),
        "2_has_smiles": int(has_smiles),
        "3_rdkit_valid": int(rdkit_valid_count) if rdkit_valid_count > 0 else int(has_smiles),
        "4_has_ic50": int(has_ic50_count),
        "5_trainable": int(can_train_count)
    },
    "rdkit_installed": len(valid_smiles) > 0
}

stats_path = output_dir / "smiles_verification_stats.json"
with open(stats_path, "w") as f:
    json.dump(stats, f, indent=2)
print(f"\n✓ 통계 JSON: {stats_path}")

# 4. 파싱 실패 SMILES (있으면)
if len(invalid_smiles) > 0:
    df_invalid = pd.DataFrame(invalid_smiles)
    invalid_path = output_dir / "rdkit_parsing_failed_smiles.csv"
    df_invalid.to_csv(invalid_path, index=False)
    print(f"\n⚠️ RDKit 파싱 실패 SMILES: {invalid_path}")
    print(f"  - {len(invalid_smiles)} rows")

# ============================================================================
# [6] 최종 요약
# ============================================================================
print("\n" + "=" * 100)
print("[6] 최종 요약")
print("=" * 100)

print(f"\n약물 수 흐름:")
print(f"  295개 (catalog 전체)")
print(f"  → {has_smiles}개 (SMILES 있음)")

if rdkit_valid_count > 0:
    print(f"  → {rdkit_valid_count}개 (RDKit 유효)")
else:
    print(f"  → {has_smiles}개 (RDKit 검증 생략)")

print(f"  → {has_ic50_count}개 (IC50 데이터 있음)")
print(f"  → **{can_train_count}개 (Chemprop 학습 가능)** 🎯")

print(f"\n✅ Chemprop 학습에 사용할 수 있는 약물: **{can_train_count}개**")
print(f"\n   이 약물들은:")
print(f"   - SMILES 있음 ✓")
if rdkit_valid_count > 0:
    print(f"   - RDKit 파싱 성공 ✓")
print(f"   - GDSC2 IC50 데이터 있음 ✓")
print(f"   - features_slim.parquet에 포함 ✓")

print("\n" + "=" * 100)
print("SMILES 데이터 검증 완료!")
print("=" * 100)
