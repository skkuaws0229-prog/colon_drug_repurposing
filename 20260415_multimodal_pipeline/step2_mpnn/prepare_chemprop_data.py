"""
멀티모달 Step 2: Chemprop 입력 데이터 준비

입력:
- trainable_drugs_with_smiles.csv: 243개 약물의 SMILES
- features_slim.parquet: 6,366행 × 5,529열 (Drug 1,127 + Gene 4,402)
- y_train.npy: 6,366개 IC50 값

출력:
- chemprop_input.csv: 6,366행 × (1 + 1 + 4,402)
  - smiles: canonical_smiles
  - target: IC50 (ln)
  - gene_0 ~ gene_4401: Gene features (4,402개)
"""
import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 100)
print("Chemprop 입력 데이터 준비")
print("=" * 100)

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step2_dir = base_dir / "20260415_multimodal_pipeline" / "step2_mpnn"
v3_dir = base_dir / "20260414_re_pre_project_v3"

# [1] 약물 SMILES 로드
print("\n[1] 약물 SMILES 로드")
print("-" * 100)
drug_smiles_path = step2_dir / "trainable_drugs_with_smiles.csv"
df_drugs = pd.read_csv(drug_smiles_path)
print(f"✓ 로드: {drug_smiles_path}")
print(f"  - 약물 수: {len(df_drugs)}")
print(f"  - 컬럼: {list(df_drugs.columns)}")

# DRUG_ID를 key로 하는 SMILES dict 생성
# DRUG_ID를 문자열로 변환 (features_slim의 canonical_drug_id가 str이므로)
drug_to_smiles = dict(zip(df_drugs['DRUG_ID'].astype(str), df_drugs['SMILES']))
print(f"  - SMILES 매핑: {len(drug_to_smiles)}개 약물")
print(f"  - Drug ID 타입: {type(list(drug_to_smiles.keys())[0])}")

# [2] Features 로드 (Drug + Gene)
print("\n[2] Features 로드")
print("-" * 100)
features_path = v3_dir / "features_slim.parquet"
df_features = pd.read_parquet(features_path)
print(f"✓ 로드: {features_path}")
print(f"  - Shape: {df_features.shape}")
print(f"  - Columns: {list(df_features.columns[:5])}... (total {len(df_features.columns)})")

# canonical_drug_id 확인
if 'canonical_drug_id' in df_features.columns:
    drug_id_col = 'canonical_drug_id'
elif 'DRUG_ID' in df_features.columns:
    drug_id_col = 'DRUG_ID'
else:
    raise ValueError(f"No drug ID column found. Available columns: {df_features.columns.tolist()}")

print(f"  - Drug ID 컬럼: {drug_id_col}")
print(f"  - Unique drugs: {df_features[drug_id_col].nunique()}")

# Gene features 추출 (sample__crispr__ prefix만)
gene_cols = [col for col in df_features.columns if col.startswith('sample__crispr__')]
gene_features = df_features[gene_cols].values
print(f"  - Gene (CRISPR) features: {len(gene_cols)}개")
print(f"  - Gene features shape: {gene_features.shape}")
print(f"  - 첫 번째: {gene_cols[0]}")
print(f"  - 마지막: {gene_cols[-1]}")

# [3] Labels 로드
print("\n[3] Labels 로드")
print("-" * 100)
labels_path = v3_dir / "step4_results" / "y_train.npy"
y_train = np.load(labels_path)
print(f"✓ 로드: {labels_path}")
print(f"  - Shape: {y_train.shape}")
print(f"  - Min: {y_train.min():.4f}, Max: {y_train.max():.4f}, Mean: {y_train.mean():.4f}")

# [4] Chemprop 입력 CSV 생성
print("\n[4] Chemprop 입력 CSV 생성")
print("-" * 100)

# SMILES 매핑
smiles_list = []
for drug_id in df_features[drug_id_col]:
    if drug_id in drug_to_smiles:
        smiles_list.append(drug_to_smiles[drug_id])
    else:
        print(f"  ⚠️  Warning: Drug {drug_id} not in SMILES mapping")
        smiles_list.append(None)

print(f"  - SMILES 매핑 완료: {len(smiles_list)}개")
print(f"  - None 개수: {smiles_list.count(None)}")

if smiles_list.count(None) > 0:
    raise ValueError(f"Found {smiles_list.count(None)} drugs without SMILES. All drugs should have SMILES.")

# DataFrame 생성
chemprop_data = pd.DataFrame({
    'smiles': smiles_list,
    'target': y_train
})

# Gene features 추가
gene_col_names = [f'gene_{i}' for i in range(gene_features.shape[1])]
df_gene = pd.DataFrame(gene_features, columns=gene_col_names)
chemprop_data = pd.concat([chemprop_data, df_gene], axis=1)

print(f"  - Chemprop 데이터 shape: {chemprop_data.shape}")
print(f"  - Columns: smiles, target, gene_0 ~ gene_{gene_features.shape[1]-1}")

# 결측치 확인
print(f"  - SMILES 결측: {chemprop_data['smiles'].isna().sum()}")
print(f"  - Target 결측: {chemprop_data['target'].isna().sum()}")
print(f"  - Gene features 결측: {df_gene.isna().sum().sum()}")

# [5] 저장
print("\n[5] 저장")
print("-" * 100)
output_path = step2_dir / "chemprop_input.csv"
chemprop_data.to_csv(output_path, index=False)
print(f"✓ 저장: {output_path}")
print(f"  - Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

# 샘플 확인
print("\n[6] 샘플 확인 (처음 3행)")
print("-" * 100)
sample = chemprop_data.head(3)
print(f"\nSMILES:")
for idx, smiles in enumerate(sample['smiles']):
    print(f"  {idx}: {smiles[:60]}...")
print(f"\nTarget: {sample['target'].tolist()}")
print(f"\nGene features (first 5):")
print(sample[gene_col_names[:5]])

print("\n" + "=" * 100)
print("✅ Chemprop 입력 데이터 준비 완료!")
print("=" * 100)
print(f"  - 총 샘플: {len(chemprop_data)}")
print(f"  - SMILES + Target + Gene features: 1 + 1 + {gene_features.shape[1]} = {chemprop_data.shape[1]} 컬럼")
print(f"  - 출력: {output_path}")
