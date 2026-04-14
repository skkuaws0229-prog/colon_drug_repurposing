#!/usr/bin/env python3
"""
Step 7 ADMET v1: Tanimoto Similarity-based Matching
Top 15 + Positive Control 5개 = 20개
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
import json
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

ADMET_DIR = BASE_DIR / "admet_assays"
INPUT_COMPREHENSIVE = BASE_DIR / "step6_final/step7_comprehensive_final.csv"
OUTPUT_DIR = BASE_DIR / "step6_final"

# ============================================================================
# ADMET Assays
# ============================================================================
ADMET_ASSAYS = {
    'ames': {'category': 'Toxicity', 'name': 'Ames Mutagenicity', 'weight': -2.0},
    'dili': {'category': 'Toxicity', 'name': 'DILI (Drug-Induced Liver Injury)', 'weight': -2.0},
    'herg': {'category': 'Toxicity', 'name': 'hERG Cardiotoxicity', 'weight': -1.5},
    'ld50_zhu': {'category': 'Toxicity', 'name': 'Acute Toxicity (LD50)', 'weight': 1.0},
    'bioavailability_ma': {'category': 'Absorption', 'name': 'Oral Bioavailability (F>20%)', 'weight': 1.0},
    'bbb_martins': {'category': 'Distribution', 'name': 'BBB Penetration', 'weight': 0.5},
    'caco2_wang': {'category': 'Absorption', 'name': 'Caco-2 Permeability', 'weight': 0.5},
    'hia_hou': {'category': 'Absorption', 'name': 'HIA (Human Intestinal Absorption)', 'weight': 0.5},
    'pgp_broccatelli': {'category': 'Absorption', 'name': 'P-gp Inhibitor', 'weight': -0.5},
    'ppbr_az': {'category': 'Distribution', 'name': 'Plasma Protein Binding Rate', 'weight': 0.3},
    'vdss_lombardo': {'category': 'Distribution', 'name': 'Volume of Distribution', 'weight': 0.3},
    'cyp2c9_veith': {'category': 'Metabolism', 'name': 'CYP2C9 Inhibitor', 'weight': -0.5},
    'cyp2d6_veith': {'category': 'Metabolism', 'name': 'CYP2D6 Inhibitor', 'weight': -0.5},
    'cyp3a4_veith': {'category': 'Metabolism', 'name': 'CYP3A4 Inhibitor', 'weight': -0.5},
    'cyp2c9_substrate_carbonmangels': {'category': 'Metabolism', 'name': 'CYP2C9 Substrate', 'weight': 0.2},
    'cyp2d6_substrate_carbonmangels': {'category': 'Metabolism', 'name': 'CYP2D6 Substrate', 'weight': 0.2},
    'cyp3a4_substrate_carbonmangels': {'category': 'Metabolism', 'name': 'CYP3A4 Substrate', 'weight': 0.2},
    'clearance_hepatocyte_az': {'category': 'Excretion', 'name': 'Hepatocyte Clearance', 'weight': 0.5},
    'clearance_microsome_az': {'category': 'Excretion', 'name': 'Microsome Clearance', 'weight': 0.5},
    'half_life_obach': {'category': 'Excretion', 'name': 'Half-Life', 'weight': 0.5},
    'lipophilicity_astrazeneca': {'category': 'Properties', 'name': 'Lipophilicity (logD)', 'weight': 0.3},
    'solubility_aqsoldb': {'category': 'Properties', 'name': 'Aqueous Solubility', 'weight': 0.5},
}

# Tanimoto thresholds
SIMILARITY_THRESHOLDS = {
    'exact': 1.0,
    'close_analog': 0.85,
    'analog': 0.70,
}

print("=" * 140)
print("Step 7 ADMET v1: Tanimoto Similarity-based Matching (22 Assays)")
print("=" * 140)

# ============================================================================
# 1. 약물 데이터 로드
# ============================================================================
print("\n[Step 1] 약물 데이터 로드")
print("=" * 140)

df_drugs = pd.read_csv(INPUT_COMPREHENSIVE)
print(f"✓ 총 약물: {len(df_drugs)}개")

df_with_smiles = df_drugs[df_drugs['smiles'].notna()].copy()
print(f"✓ SMILES 있음: {len(df_with_smiles)}개")

# ============================================================================
# 2. ADMET Assay 데이터 로드 및 Fingerprint 생성
# ============================================================================
print("\n[Step 2] ADMET Assay 데이터 로드 및 Fingerprint 생성")
print("=" * 140)

def get_fingerprint(smiles):
    """Morgan fingerprint 생성"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    except:
        pass
    return None

# Assay 데이터 로드 및 fingerprint 생성
assay_libraries = {}

for assay_name, assay_info in ADMET_ASSAYS.items():
    assay_path = ADMET_DIR / assay_name / "train_val_basic_clean_20260406.parquet"
    if not assay_path.exists():
        continue

    df_assay = pd.read_parquet(assay_path)

    # Fingerprint 생성
    fps = []
    y_values = []
    valid_indices = []

    for idx, row in df_assay.iterrows():
        smiles = row.get('Drug', '')
        y = row.get('Y')

        fp = get_fingerprint(smiles)
        if fp is not None:
            fps.append(fp)
            y_values.append(y)
            valid_indices.append(idx)

    if fps:
        assay_libraries[assay_name] = {
            'fps': fps,
            'y_values': y_values,
            'info': assay_info,
            'n_compounds': len(fps)
        }
        print(f"  ✓ {assay_name:40s}: {len(fps):6d} compounds with fingerprints")

print(f"\n✓ 로드 완료: {len(assay_libraries)}/22개 assay")

# ============================================================================
# 3. Tanimoto Similarity 기반 매칭
# ============================================================================
print("\n[Step 3] Tanimoto Similarity 기반 매칭 (threshold > 0.7)")
print("=" * 140)

admet_results = {}

for idx, row in df_with_smiles.iterrows():
    drug_name = row['drug_name']
    smiles = row['smiles']

    # Drug fingerprint
    drug_fp = get_fingerprint(smiles)
    if drug_fp is None:
        continue

    result = {
        'drug_name': drug_name,
        'smiles': smiles,
        'assays': {},
        'n_exact': 0,
        'n_close_analog': 0,
        'n_analog': 0,
        'n_total': 0,
    }

    # 각 assay에 대해 가장 유사한 화합물 찾기
    for assay_name, assay_lib in assay_libraries.items():
        best_similarity = 0.0
        best_y = None
        best_match_type = None

        # 모든 assay 화합물과 비교
        for assay_fp, y_value in zip(assay_lib['fps'], assay_lib['y_values']):
            try:
                similarity = DataStructs.TanimotoSimilarity(drug_fp, assay_fp)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_y = y_value

                    # Match type 결정
                    if similarity >= SIMILARITY_THRESHOLDS['exact']:
                        best_match_type = 'exact'
                    elif similarity >= SIMILARITY_THRESHOLDS['close_analog']:
                        best_match_type = 'close_analog'
                    elif similarity >= SIMILARITY_THRESHOLDS['analog']:
                        best_match_type = 'analog'
            except:
                pass

        # Threshold 이상이면 저장
        if best_similarity >= SIMILARITY_THRESHOLDS['analog']:
            result['assays'][assay_name] = {
                'value': best_y,
                'similarity': best_similarity,
                'match_type': best_match_type,
                'weight': assay_lib['info']['weight']
            }
            result['n_total'] += 1

            if best_match_type == 'exact':
                result['n_exact'] += 1
            elif best_match_type == 'close_analog':
                result['n_close_analog'] += 1
            elif best_match_type == 'analog':
                result['n_analog'] += 1

    admet_results[drug_name] = result

# 결과 요약
print(f"\n약물별 매칭 결과:")
for drug_name, result in admet_results.items():
    n_total = result['n_total']
    n_exact = result['n_exact']
    n_close = result['n_close_analog']
    n_analog = result['n_analog']

    if n_total > 0:
        print(f"  ✓ {drug_name:30s}: {n_total:2d}/22 assays (exact={n_exact}, close={n_close}, analog={n_analog})")

total_matches = sum(r['n_total'] for r in admet_results.values())
print(f"\n✓ 총 매칭: {total_matches}개 (평균 {total_matches/len(admet_results):.1f} assays/drug)")

# ============================================================================
# 4. Safety Score 계산 (v1 방법론)
# ============================================================================
print("\n[Step 4] Safety Score 계산 (v1 방법론)")
print("=" * 140)

for drug_name, result in admet_results.items():
    safety_score = 5.0  # Base score
    n_assays = result['n_total']

    if n_assays > 0:
        # 가중치 적용
        weighted_sum = 0.0
        for assay_name, assay_result in result['assays'].items():
            y_value = assay_result['value']
            weight = assay_result['weight']
            similarity = assay_result['similarity']

            # Similarity로 weight 조정
            adjusted_weight = weight * similarity

            try:
                # Normalize y_value
                if isinstance(y_value, (int, float)):
                    if y_value > 1:  # Regression
                        normalized = np.tanh(y_value / 10.0)  # -1 ~ 1
                    else:  # Binary or normalized
                        normalized = y_value

                    weighted_sum += adjusted_weight * normalized
            except:
                pass

        # Final score
        safety_score = 5.0 + weighted_sum + (n_assays * 0.15)
        safety_score = max(0, min(10, safety_score))

    result['safety_score'] = safety_score

    # 판정
    if safety_score >= 6:
        verdict = "PASS"
    elif safety_score >= 4:
        verdict = "WARNING"
    else:
        verdict = "FAIL"

    result['verdict'] = verdict

# ============================================================================
# 5. 결과 업데이트
# ============================================================================
print("\n[Step 5] 결과 업데이트")
print("=" * 140)

for idx, row in df_drugs.iterrows():
    drug_name = row['drug_name']

    if drug_name in admet_results:
        result = admet_results[drug_name]

        df_drugs.at[idx, 'admet_v1_assays_total'] = result['n_total']
        df_drugs.at[idx, 'admet_v1_assays_exact'] = result['n_exact']
        df_drugs.at[idx, 'admet_v1_assays_analog'] = result['n_close_analog'] + result['n_analog']
        df_drugs.at[idx, 'admet_v1_safety_score'] = result['safety_score']
        df_drugs.at[idx, 'admet_v1_verdict'] = result['verdict']

        n = result['n_total']
        score = result['safety_score']
        verdict = result['verdict']

        if n > 0:
            print(f"  ✓ {drug_name:30s}: {n:2d} assays, safety={score:.2f}, verdict={verdict}")

# ============================================================================
# 6. 저장
# ============================================================================
print("\n[Step 6] 결과 저장")
print("=" * 140)

# CSV 업데이트
df_drugs.to_csv(OUTPUT_DIR / "step7_comprehensive_final.csv", index=False)
print("✓ step7_comprehensive_final.csv 업데이트 (v1 결과)")

# 상세 결과 저장
admet_detailed = []
for drug_name, result in admet_results.items():
    assay_details = []
    for assay_name, assay_data in result['assays'].items():
        assay_details.append({
            'assay': assay_name,
            'category': ADMET_ASSAYS[assay_name]['category'],
            'value': float(assay_data['value']) if isinstance(assay_data['value'], (int, float, np.number)) else str(assay_data['value']),
            'similarity': float(assay_data['similarity']),
            'match_type': assay_data['match_type']
        })

    admet_detailed.append({
        'drug_name': drug_name,
        'n_total': result['n_total'],
        'n_exact': result['n_exact'],
        'n_close_analog': result['n_close_analog'],
        'n_analog': result['n_analog'],
        'safety_score': float(result['safety_score']),
        'verdict': result['verdict'],
        'assays': assay_details
    })

with open(OUTPUT_DIR / "admet_v1_detailed_results.json", 'w') as f:
    json.dump(admet_detailed, f, indent=2)
print("✓ admet_v1_detailed_results.json 저장")

# 요약
summary = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'method': 'Tanimoto Similarity v1',
    'threshold': 0.7,
    'n_drugs': len(df_drugs),
    'n_drugs_with_smiles': len(df_with_smiles),
    'n_assays_loaded': len(assay_libraries),
    'total_matches': total_matches,
    'avg_assays_per_drug': total_matches / len(admet_results) if admet_results else 0,
    'verdict_distribution': {
        'PASS': int((df_drugs['admet_v1_verdict'] == 'PASS').sum()),
        'WARNING': int((df_drugs['admet_v1_verdict'] == 'WARNING').sum()),
        'FAIL': int((df_drugs['admet_v1_verdict'] == 'FAIL').sum()),
    }
}

with open(OUTPUT_DIR / "admet_v1_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)
print("✓ admet_v1_summary.json 저장")

# ============================================================================
# 7. 결과 테이블 생성
# ============================================================================
print("\n" + "=" * 140)
print("✅ Step 7 ADMET v1 완료")
print("=" * 140)

print(f"\n📊 최종 결과 테이블:")
print("=" * 140)
print(f"{'약물명':^30} | {'매칭 Assays':^15} | {'Safety':^8} | {'판정':^10} | {'주요 발견':^50}")
print("=" * 140)

for drug_name, result in sorted(admet_results.items(), key=lambda x: x[1]['safety_score'], reverse=True):
    n_total = result['n_total']
    n_exact = result['n_exact']
    n_analog = result['n_close_analog'] + result['n_analog']
    safety = result['safety_score']
    verdict = result['verdict']

    # 주요 발견
    key_findings = []
    for assay_name, assay_data in result['assays'].items():
        if assay_data['match_type'] == 'exact' and assay_data['value'] in [0, 1]:
            assay_short = assay_name.split('_')[0]
            key_findings.append(f"{assay_short}={assay_data['value']}")

    findings_str = ', '.join(key_findings[:3]) if key_findings else '-'

    assay_str = f"{n_total}/22 (E:{n_exact} A:{n_analog})"

    print(f"{drug_name:^30} | {assay_str:^15} | {safety:^8.2f} | {verdict:^10} | {findings_str:^50}")

print("=" * 140)

print(f"\n📈 요약 통계:")
print(f"  - 총 약물: {len(df_drugs)}개")
print(f"  - SMILES 있음: {len(df_with_smiles)}개")
print(f"  - 평균 매칭: {total_matches/len(admet_results):.1f} assays/drug")
print(f"\n  판정:")
print(f"  - PASS: {summary['verdict_distribution']['PASS']}개")
print(f"  - WARNING: {summary['verdict_distribution']['WARNING']}개")
print(f"  - FAIL: {summary['verdict_distribution']['FAIL']}개")

print("\n생성 파일:")
print("  - step7_comprehensive_final.csv (v1 결과로 업데이트)")
print("  - admet_v1_detailed_results.json")
print("  - admet_v1_summary.json")
print("=" * 140)
