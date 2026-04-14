#!/usr/bin/env python3
"""
Step 7 종합: ADMET + 모든 추가 지표 (한번에)
Top 15 + Positive Control 5개 = 20개
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, QED, AllChem
from rdkit.Chem import DataStructs
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

INPUT_REPURPOSING = BASE_DIR / "step6_final/repurposing_top15.csv"
INPUT_POSITIVE = BASE_DIR / "step6_final/positive_controls.csv"
INPUT_ADMET = BASE_DIR / "step7_admet_results/step7_admet_results.json"
INPUT_TOP30 = BASE_DIR / "step6_final/step6_top30_full.csv"

OUTPUT_DIR = BASE_DIR / "step6_final"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# 유틸리티
# ============================================================================
def standardize_name(name):
    """약물명 표준화"""
    if pd.isna(name):
        return ""
    return str(name).lower().replace(" ", "").replace("-", "").replace("_", "")

def get_smiles_from_pubchem(drug_name, max_retries=2):
    """PubChem에서 SMILES 가져오기"""
    import requests
    import time

    for attempt in range(max_retries):
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/property/IsomericSMILES/JSON"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                smiles = data['PropertyTable']['Properties'][0]['SMILES']
                return smiles
        except:
            time.sleep(1)
    return None

def calculate_rdkit_properties(smiles):
    """RDKit으로 모든 속성 계산"""
    if not smiles or pd.isna(smiles):
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    props = {
        'MW': Descriptors.MolWt(mol),
        'LogP': Descriptors.MolLogP(mol),
        'HBD': Lipinski.NumHDonors(mol),
        'HBA': Lipinski.NumHAcceptors(mol),
        'TPSA': Descriptors.TPSA(mol),
        'RotBonds': Lipinski.NumRotatableBonds(mol),
        'AromaticRings': Lipinski.NumAromaticRings(mol),
        'QED': QED.qed(mol),
        'SAS': 0.0,  # SAS는 별도 계산 필요
        'Bioavailability': 1 if (Descriptors.MolWt(mol) <= 500 and
                                  Descriptors.MolLogP(mol) <= 5 and
                                  Lipinski.NumHDonors(mol) <= 5 and
                                  Lipinski.NumHAcceptors(mol) <= 10) else 0,
        'Lipinski_Pass': 1 if (Descriptors.MolWt(mol) <= 500 and
                                Descriptors.MolLogP(mol) <= 5 and
                                Lipinski.NumHDonors(mol) <= 5 and
                                Lipinski.NumHAcceptors(mol) <= 10) else 0,
    }

    return props

def get_fingerprint(smiles):
    """Get Morgan fingerprint separately"""
    if not smiles or pd.isna(smiles):
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    except:
        return None

# ============================================================================
# MAIN
# ============================================================================
print("=" * 140)
print("Step 7 종합: ADMET + 모든 추가 지표 (Top 15 + Positive Control 5개)")
print("=" * 140)

# ============================================================================
# 1. 데이터 로드
# ============================================================================
print("\n[Step 1] 데이터 로드")
print("=" * 140)

# Repurposing Top 15
df_repurposing = pd.read_csv(INPUT_REPURPOSING)
df_repurposing['group'] = 'Repurposing'
print(f"✓ Repurposing Top 15: {len(df_repurposing)}개")

# Positive Control 5
df_positive = pd.read_csv(INPUT_POSITIVE)
df_positive['group'] = 'Positive Control'
print(f"✓ Positive Control: {len(df_positive)}개")

# 합치기
df_all = pd.concat([df_repurposing, df_positive], ignore_index=True)
print(f"✓ 총 약물: {len(df_all)}개")

# ADMET 데이터
with open(INPUT_ADMET) as f:
    admet_data = json.load(f)

admet_map = {}
for profile in admet_data.get('profiles', []):
    drug_name = profile.get('drug_name', '')
    std_name = standardize_name(drug_name)
    if std_name:
        admet_map[std_name] = profile

print(f"✓ ADMET 프로필: {len(admet_map)}개")

# Top 30 (SMILES 정보)
top30 = pd.read_csv(INPUT_TOP30)

# ============================================================================
# 2. ADMET 매칭 + RDKit 계산
# ============================================================================
print("\n[Step 2] ADMET 매칭 + RDKit 계산")
print("=" * 140)

results = []

for idx, row in df_all.iterrows():
    drug_name = row['drug_name']
    std_name = standardize_name(drug_name)
    group = row['group']

    print(f"\n[{idx+1}/{len(df_all)}] {drug_name} ({group})...")

    result = {
        'drug_name': drug_name,
        'canonical_drug_id': row.get('canonical_drug_id', ''),
        'group': group,
        'rank': row.get('repurposing_rank', row.get('control_rank', '')),
        'final_score': row.get('final_score', 0.0),
        'category': row.get('category', ''),
        'target': row.get('target_matches', row.get('target', '')),
        'pathway': row.get('pathway', ''),
        'subtypes': row.get('subtypes', ''),
    }

    # ADMET 매칭
    admet_profile = admet_map.get(std_name)
    if admet_profile:
        safety_score = admet_profile.get('safety_score', 0.0)
        result['safety_score'] = safety_score
        result['admet_source'] = 'GDSC ADMET'

        # 판정
        if safety_score >= 6:
            verdict = "PASS"
        elif safety_score >= 4:
            verdict = "WARNING"
        else:
            verdict = "FAIL"
        result['admet_verdict'] = verdict

        print(f"  ✓ ADMET: safety={safety_score:.2f}, verdict={verdict}")
    else:
        result['safety_score'] = None
        result['admet_source'] = '미측정'
        result['admet_verdict'] = '미측정'
        print(f"  - ADMET: 미측정")

    # SMILES 가져오기
    # 1) Top 30에서
    match = top30[top30['drug_name'] == drug_name]
    if not match.empty and 'drug__canonical_smiles_raw' in top30.columns:
        smiles = match.iloc[0].get('drug__canonical_smiles_raw')
    else:
        # 2) PubChem에서
        smiles = get_smiles_from_pubchem(drug_name)

    result['smiles'] = smiles

    # RDKit 계산
    if smiles:
        rdkit_props = calculate_rdkit_properties(smiles)
        if rdkit_props:
            result['MW'] = rdkit_props['MW']
            result['LogP'] = rdkit_props['LogP']
            result['HBD'] = rdkit_props['HBD']
            result['HBA'] = rdkit_props['HBA']
            result['TPSA'] = rdkit_props['TPSA']
            result['RotBonds'] = rdkit_props['RotBonds']
            result['QED'] = rdkit_props['QED']
            result['Bioavailability'] = rdkit_props['Bioavailability']
            result['Lipinski_Pass'] = rdkit_props['Lipinski_Pass']

            print(f"  ✓ RDKit: QED={rdkit_props['QED']:.3f}, Lipinski={'Pass' if rdkit_props['Lipinski_Pass'] else 'Fail'}")
        else:
            print(f"  ✗ RDKit: 계산 실패")
    else:
        print(f"  ✗ SMILES: 없음")

    results.append(result)

df_results = pd.DataFrame(results)

# ============================================================================
# 3. IC50 분석 (Confidence + 원본 vs 예측)
# ============================================================================
print("\n[Step 3] IC50 분석")
print("=" * 140)

# Top 30에서 IC50 정보 가져오기
for idx, row in df_results.iterrows():
    drug_name = row['drug_name']

    match = top30[top30['drug_name'] == drug_name]
    if not match.empty:
        df_results.at[idx, 'mean_pred_ic50'] = match.iloc[0].get('mean_pred_ic50', np.nan)
        df_results.at[idx, 'std_pred_ic50'] = match.iloc[0].get('std_pred_ic50', np.nan)
        df_results.at[idx, 'mean_true_ic50'] = match.iloc[0].get('mean_true_ic50', np.nan)

        pred = match.iloc[0].get('mean_pred_ic50', 0)
        true = match.iloc[0].get('mean_true_ic50', 0)
        if not pd.isna(pred) and not pd.isna(true):
            df_results.at[idx, 'ic50_error'] = abs(pred - true)

print(f"✓ IC50 정보 추가")

# ============================================================================
# 4. Diversity 분석 (Tanimoto)
# ============================================================================
print("\n[Step 4] Molecular Diversity 분석")
print("=" * 140)

# SMILES로부터 fingerprint 생성
fps = []
fp_drugs = []
for idx, row in df_results.iterrows():
    smiles = row.get('smiles')
    if smiles and not pd.isna(smiles):
        fp = get_fingerprint(smiles)
        if fp is not None:
            fps.append(fp)
            fp_drugs.append(row['drug_name'])

if len(fps) > 1:
    # Pairwise Tanimoto
    tanimoto_matrix = []
    for i in range(len(fps)):
        for j in range(i+1, len(fps)):
            try:
                similarity = DataStructs.TanimotoSimilarity(fps[i], fps[j])
                tanimoto_matrix.append(similarity)
            except:
                pass

    avg_similarity = np.mean(tanimoto_matrix) if tanimoto_matrix else 0.0
    print(f"✓ 평균 Tanimoto similarity: {avg_similarity:.4f}")
    print(f"  - {len(fps)}개 약물 간 {len(tanimoto_matrix)}개 쌍 비교")
else:
    avg_similarity = 0.0
    print(f"⚠ Fingerprint 부족 (최소 2개 필요)")

# ============================================================================
# 5. MOA 중복도
# ============================================================================
print("\n[Step 5] MOA 중복도 분석")
print("=" * 140)

pathway_counts = df_results['pathway'].value_counts()
print(f"✓ MOA 분포:")
for pathway, count in pathway_counts.items():
    if count > 1:
        print(f"  - {pathway}: {count}개 (중복)")

# ============================================================================
# 6. Target Overlap
# ============================================================================
print("\n[Step 6] Target Overlap 분석")
print("=" * 140)

# Target를 set으로 변환
target_sets = {}
for idx, row in df_results.iterrows():
    target_str = row.get('target', '')
    if target_str and target_str != 'None':
        targets = set([t.strip() for t in str(target_str).split(',')])
        target_sets[row['drug_name']] = targets

# Overlap 계산
overlaps = []
drug_names = list(target_sets.keys())
for i in range(len(drug_names)):
    for j in range(i+1, len(drug_names)):
        drug1 = drug_names[i]
        drug2 = drug_names[j]
        overlap = target_sets[drug1] & target_sets[drug2]
        if overlap:
            overlaps.append({
                'drug1': drug1,
                'drug2': drug2,
                'shared_targets': ', '.join(overlap),
                'overlap_count': len(overlap)
            })

print(f"✓ Target overlap: {len(overlaps)}개 쌍")
if overlaps:
    df_overlaps = pd.DataFrame(overlaps)
    print(f"  상위 5개:")
    for _, row in df_overlaps.head(5).iterrows():
        print(f"  - {row['drug1']} ↔ {row['drug2']}: {row['shared_targets']}")

# ============================================================================
# 7. 결과 저장
# ============================================================================
print("\n[Step 7] 결과 저장")
print("=" * 140)

# 컬럼 정리
save_columns = [
    'drug_name', 'canonical_drug_id', 'group', 'rank', 'final_score',
    'category', 'target', 'pathway', 'subtypes',
    'safety_score', 'admet_source', 'admet_verdict',
    'MW', 'LogP', 'HBD', 'HBA', 'TPSA', 'RotBonds', 'QED',
    'Bioavailability', 'Lipinski_Pass',
    'mean_pred_ic50', 'std_pred_ic50', 'mean_true_ic50', 'ic50_error',
    'smiles'
]

# 존재하는 컬럼만 선택
available_columns = [col for col in save_columns if col in df_results.columns]
df_save = df_results[available_columns].copy()

# CSV 저장
df_save.to_csv(OUTPUT_DIR / "step7_comprehensive_final.csv", index=False)
print("✓ step7_comprehensive_final.csv 저장")

# Step 7 ADMET만 별도 저장 (기존 포맷 유지)
admet_only = df_results[df_results['group'] == 'Repurposing'][
    ['drug_name', 'safety_score', 'admet_verdict']
].copy()
admet_only.to_csv(OUTPUT_DIR / "step7_admet_final.csv", index=False)
print("✓ step7_admet_final.csv 저장 (Repurposing 15개)")

# JSON 요약
summary = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_total': len(df_results),
    'n_repurposing': len(df_results[df_results['group'] == 'Repurposing']),
    'n_positive_control': len(df_results[df_results['group'] == 'Positive Control']),
    'admet_coverage': {
        'measured': int((df_results['safety_score'].notna()).sum()),
        'unmeasured': int((df_results['safety_score'].isna()).sum()),
        'pass': int((df_results['admet_verdict'] == 'PASS').sum()),
        'warning': int((df_results['admet_verdict'] == 'WARNING').sum()),
        'fail': int((df_results['admet_verdict'] == 'FAIL').sum()),
    },
    'rdkit_coverage': {
        'smiles_available': int(df_results['smiles'].notna().sum()),
        'qed_calculated': int(df_results['QED'].notna().sum()),
        'lipinski_pass': int(df_results['Lipinski_Pass'].sum()) if 'Lipinski_Pass' in df_results else 0,
    },
    'diversity': {
        'avg_tanimoto_similarity': float(avg_similarity),
        'n_compounds_compared': len(fps),
    },
    'moa_duplicates': {pathway: int(count) for pathway, count in pathway_counts.items() if count > 1},
    'target_overlaps': len(overlaps),
}

with open(OUTPUT_DIR / "step7_comprehensive_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)
print("✓ step7_comprehensive_summary.json 저장")

# Target overlap CSV
if overlaps:
    df_overlaps.to_csv(OUTPUT_DIR / "target_overlaps.csv", index=False)
    print("✓ target_overlaps.csv 저장")

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 140)
print("✅ Step 7 종합 완료")
print("=" * 140)

print(f"\n총 약물: {len(df_results)}개")
print(f"  - Repurposing: {summary['n_repurposing']}개")
print(f"  - Positive Control: {summary['n_positive_control']}개")

print(f"\nADMET 커버리지:")
print(f"  - 측정: {summary['admet_coverage']['measured']}개")
print(f"  - 미측정: {summary['admet_coverage']['unmeasured']}개")
print(f"  - PASS: {summary['admet_coverage']['pass']}개")
print(f"  - WARNING: {summary['admet_coverage']['warning']}개")
print(f"  - FAIL: {summary['admet_coverage']['fail']}개")

print(f"\nRDKit 커버리지:")
print(f"  - SMILES: {summary['rdkit_coverage']['smiles_available']}/{len(df_results)}개")
print(f"  - QED 계산: {summary['rdkit_coverage']['qed_calculated']}개")
print(f"  - Lipinski Pass: {summary['rdkit_coverage']['lipinski_pass']}개")

print(f"\nDiversity:")
print(f"  - 평균 Tanimoto similarity: {avg_similarity:.4f}")
print(f"  - Target overlaps: {len(overlaps)}개 쌍")

print("\n생성 파일:")
print("  - step7_comprehensive_final.csv (전체 20개)")
print("  - step7_admet_final.csv (Repurposing 15개)")
print("  - step7_comprehensive_summary.json")
print("  - target_overlaps.csv")
print("=" * 140)
