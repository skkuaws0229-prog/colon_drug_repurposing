#!/usr/bin/env python3
"""
Feature Block 분석 및 정의
features_slim.parquet의 컬럼을 drug/gene 관련으로 분류
"""
import pandas as pd
import numpy as np
from pathlib import Path

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
fe_path = base_dir / "20260414_re_pre_project_v3/features_slim.parquet"
output_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Feature Block 분석")
print("=" * 80)

# 데이터 로드
print(f"\nLoading features from: {fe_path}")
df = pd.read_parquet(fe_path)

print(f"Shape: {df.shape}")
print(f"Total columns: {len(df.columns)}")

# 컬럼 목록
columns = df.columns.tolist()

# Feature block 분류 규칙
print("\n" + "=" * 80)
print("Feature Block 분류")
print("=" * 80)

drug_keywords = [
    'morgan', 'fp', 'fingerprint', 'smiles', 'mol', 'drug',
    'lincs', 'l1000', 'compound', 'target', 'pathway',
    'canonical_drug_id', 'drug_name', 'mechanism'
]

gene_keywords = [
    'gene', 'expression', 'mut', 'mutation', 'cnv', 'copy_number',
    'rna', 'mrna', 'protein', 'pathway', 'depmap', 'ccle',
    'sample_id', 'cell_line', 'tissue', 'cancer_type'
]

# ID 컬럼 찾기
id_cols = []
drug_cols = []
gene_cols = []
other_cols = []

for col in columns:
    col_lower = col.lower()

    # ID 컬럼 (제외할 것들)
    if col in ['sample_id', 'canonical_drug_id', 'IC50']:
        id_cols.append(col)
    # Drug 관련
    elif any(kw in col_lower for kw in drug_keywords):
        drug_cols.append(col)
    # Gene 관련
    elif any(kw in col_lower for kw in gene_keywords):
        gene_cols.append(col)
    else:
        other_cols.append(col)

print(f"\nID columns ({len(id_cols)}):")
print(f"  {id_cols[:10]}")

print(f"\nDrug-related columns ({len(drug_cols)}):")
print(f"  First 20: {drug_cols[:20]}")
if len(drug_cols) > 20:
    print(f"  ... and {len(drug_cols) - 20} more")

print(f"\nGene/Pathway-related columns ({len(gene_cols)}):")
print(f"  First 20: {gene_cols[:20]}")
if len(gene_cols) > 20:
    print(f"  ... and {len(gene_cols) - 20} more")

print(f"\nOther columns ({len(other_cols)}):")
if other_cols:
    print(f"  {other_cols[:50]}")
    if len(other_cols) > 50:
        print(f"  ... and {len(other_cols) - 50} more")

# Feature block 정의
print("\n" + "=" * 80)
print("Feature Block 정의")
print("=" * 80)

# ID 제외
feature_cols = [col for col in columns if col not in id_cols]

print(f"\nTotal feature columns (excluding IDs): {len(feature_cols)}")
print(f"  - Drug-related: {len(drug_cols)}")
print(f"  - Gene-related: {len(gene_cols)}")
print(f"  - Other: {len(other_cols)}")

# Other 컬럼이 있으면 어디에 포함시킬지 결정
if other_cols:
    print("\n⚠️  'Other' 컬럼이 있습니다. 분류가 필요합니다.")
    print("  샘플 컬럼명을 확인하여 적절히 분류하겠습니다.")

    # 샘플 10개의 값 확인
    print("\n  Other 컬럼 샘플 값:")
    for col in other_cols[:10]:
        sample_vals = df[col].head(3).values
        print(f"    {col}: {sample_vals}")

# Block 정의 결정
if len(drug_cols) == 0 or len(gene_cols) == 0:
    print("\n⚠️  WARNING: Drug 또는 Gene 블록이 비어있습니다!")
    print("  Feature block 분리가 불가능합니다.")
    block_definition_possible = False
else:
    print("\n✅ Feature block 분리 가능")
    block_definition_possible = True

    # Other를 gene에 포함 (보수적 접근)
    gene_cols_extended = gene_cols + other_cols

    print(f"\n최종 Block 정의:")
    print(f"  - Block 1 (Drug): {len(drug_cols)} features")
    print(f"  - Block 2 (Gene/Other): {len(gene_cols_extended)} features")
    print(f"  - Total: {len(drug_cols) + len(gene_cols_extended)} features")

# 저장
feature_blocks = {
    "id_columns": id_cols,
    "drug_columns": drug_cols,
    "gene_columns": gene_cols_extended if block_definition_possible else [],
    "total_features": len(feature_cols),
    "drug_features": len(drug_cols),
    "gene_features": len(gene_cols_extended) if block_definition_possible else 0,
    "block_definition_possible": block_definition_possible
}

# Column list 저장
output_json = output_dir / "feature_blocks.json"
import json
with open(output_json, "w") as f:
    json.dump(feature_blocks, f, indent=2)

print(f"\n결과 저장: {output_json}")

# 인덱스 저장 (numpy 배열용)
if block_definition_possible:
    # feature_cols에서 각 블록의 인덱스 찾기
    drug_indices = [i for i, col in enumerate(feature_cols) if col in drug_cols]
    gene_indices = [i for i, col in enumerate(feature_cols) if col in gene_cols_extended]

    np.save(output_dir / "drug_feature_indices.npy", np.array(drug_indices))
    np.save(output_dir / "gene_feature_indices.npy", np.array(gene_indices))

    print(f"\n인덱스 저장:")
    print(f"  - drug_feature_indices.npy: {len(drug_indices)} indices")
    print(f"  - gene_feature_indices.npy: {len(gene_indices)} indices")

    # 검증: 겹치지 않는지 확인
    overlap = set(drug_indices) & set(gene_indices)
    if overlap:
        print(f"\n⚠️  WARNING: Drug/Gene 인덱스가 겹칩니다! {len(overlap)} 개")
    else:
        print(f"\n✅ Drug/Gene 인덱스가 겹치지 않습니다.")

    # 검증: 모든 feature를 커버하는지
    total_covered = len(set(drug_indices) | set(gene_indices))
    print(f"\n커버리지: {total_covered}/{len(feature_cols)} features")
    if total_covered < len(feature_cols):
        missing = len(feature_cols) - total_covered
        print(f"⚠️  {missing}개 feature가 누락되었습니다.")

print("\n분석 완료!")
