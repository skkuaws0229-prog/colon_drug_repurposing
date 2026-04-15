#!/usr/bin/env python3
"""
인덱스 수정: X_train.npy는 이미 ID가 제외되어 있음
"""
import pandas as pd
import numpy as np
from pathlib import Path

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
fe_path = base_dir / "20260414_re_pre_project_v3/features_slim.parquet"
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"

# Feature 컬럼 다시 확인
df = pd.read_parquet(fe_path)
print(f"Parquet shape: {df.shape}")

# X_train 확인
X_train = np.load(step4_dir / "X_train.npy")
print(f"X_train shape: {X_train.shape}")

# ID 컬럼 찾기
id_cols = ['sample_id', 'canonical_drug_id']
feature_cols = [col for col in df.columns if col not in id_cols]

print(f"Feature columns in parquet (excluding IDs): {len(feature_cols)}")
print(f"X_train columns: {X_train.shape[1]}")

# 일치하는지 확인
if len(feature_cols) != X_train.shape[1]:
    print(f"\n⚠️  WARNING: 불일치! {len(feature_cols)} vs {X_train.shape[1]}")
    
    # X_train이 더 작으면 일부 feature가 빠졌을 가능성
    if X_train.shape[1] < len(feature_cols):
        print(f"  X_train이 {len(feature_cols) - X_train.shape[1]}개 적습니다.")
        print(f"  X_train 기준으로 인덱스를 생성합니다.")

# Drug/Gene 키워드
drug_keywords = [
    'morgan', 'fp', 'fingerprint', 'smiles', 'mol', 'drug',
    'lincs', 'l1000', 'compound', 'target', 'pathway'
]

# X_train 컬럼 수에 맞춰서 재정의
n_features = X_train.shape[1]
feature_cols_adjusted = feature_cols[:n_features]  # X_train 크기에 맞춤

drug_indices = []
gene_indices = []

for i, col in enumerate(feature_cols_adjusted):
    col_lower = col.lower()
    if any(kw in col_lower for kw in drug_keywords):
        drug_indices.append(i)
    else:
        gene_indices.append(i)

print(f"\n새 인덱스:")
print(f"  Drug: {len(drug_indices)}")
print(f"  Gene: {len(gene_indices)}")
print(f"  Total: {len(drug_indices) + len(gene_indices)}")

# 저장
np.save(output_dir / "drug_feature_indices.npy", np.array(drug_indices))
np.save(output_dir / "gene_feature_indices.npy", np.array(gene_indices))

print(f"\n✅ 인덱스 재저장 완료")
print(f"  최대 인덱스: {max(max(drug_indices), max(gene_indices))}")
print(f"  X_train 마지막 인덱스: {X_train.shape[1] - 1}")
