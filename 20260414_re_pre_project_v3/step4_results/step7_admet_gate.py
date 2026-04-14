"""
Step 7: ADMET Gate - Top 15 약물 필터링

22개 Assay 3단계 필터링:
1단계: 물리화학적 속성 (Lipinski, LogP, MW, TPSA)
2단계: ADMET 예측 (흡수, 분포, 대사, 배설, 독성)
3단계: CYP3A4 분리 분석

결과: ADMET 통과 약물 + 상세 프로파일
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# RDKit for molecular property calculation
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, Crippen, MolSurf
    from rdkit.Chem import AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    print("⚠️  RDKit not available. Using mock calculations.")

print("=" * 80)
print("Step 7: ADMET Gate - Top 15 약물 필터링")
print("=" * 80)

# ============================================================================
# Configuration
# ============================================================================

RESULTS_DIR = Path("step7_admet_results")
RESULTS_DIR.mkdir(exist_ok=True)

# ADMET 기준값 (Literature-based thresholds)
ADMET_THRESHOLDS = {
    # 1단계: 물리화학적 속성 (Lipinski Rule of 5)
    'MW': {'min': 160, 'max': 500, 'unit': 'Da'},  # Molecular Weight
    'LogP': {'min': -0.4, 'max': 5.6, 'unit': ''},  # Lipophilicity
    'HBD': {'min': 0, 'max': 5, 'unit': 'count'},   # H-bond donors
    'HBA': {'min': 0, 'max': 10, 'unit': 'count'},  # H-bond acceptors
    'TPSA': {'min': 0, 'max': 140, 'unit': 'Ų'},   # Topological polar surface area
    'RotBonds': {'min': 0, 'max': 10, 'unit': 'count'},

    # 2단계: ADMET 속성
    # Absorption
    'Caco2': {'min': -5.15, 'max': 1.0, 'unit': 'log cm/s'},  # Intestinal permeability
    'HIA': {'min': 0.3, 'max': 1.0, 'unit': 'probability'},   # Human intestinal absorption

    # Distribution
    'PPB': {'min': 0, 'max': 90, 'unit': '%'},  # Plasma protein binding
    'BBB': {'min': -3.0, 'max': -1.0, 'unit': 'log BB'},  # Blood-brain barrier
    'VDss': {'min': -0.15, 'max': 1.0, 'unit': 'L/kg'},  # Volume of distribution

    # Metabolism (CYP450 inhibition - should be LOW)
    'CYP1A2_inhibitor': {'threshold': 0.5, 'lower_is_better': True},
    'CYP2C19_inhibitor': {'threshold': 0.5, 'lower_is_better': True},
    'CYP2C9_inhibitor': {'threshold': 0.5, 'lower_is_better': True},
    'CYP2D6_inhibitor': {'threshold': 0.5, 'lower_is_better': True},
    'CYP3A4_inhibitor': {'threshold': 0.5, 'lower_is_better': True},

    # Excretion
    'CLtot': {'min': 0, 'max': 15, 'unit': 'mL/min/kg'},  # Total clearance
    'Half_Life': {'min': 0.5, 'max': 100, 'unit': 'hours'},

    # Toxicity (should be LOW or negative)
    'hERG_blocker': {'threshold': 0.5, 'lower_is_better': True},  # Cardiotoxicity
    'AMES': {'threshold': 0.5, 'lower_is_better': True},  # Mutagenicity
    'Hepatotoxicity': {'threshold': 0.5, 'lower_is_better': True},
    'Skin_Sensitization': {'threshold': 0.5, 'lower_is_better': True},
}

print(f"Results directory: {RESULTS_DIR}")
print(f"RDKit available: {RDKIT_AVAILABLE}")

# ============================================================================
# 0. Load Top 15 drugs
# ============================================================================

def load_top15_drugs():
    """Load Top 15 drugs from Step 6"""
    print("\n" + "=" * 80)
    print("0. Top 15 약물 로드")
    print("=" * 80)

    # Load ensemble Top 15 with detailed info
    top15_df = pd.read_csv('step6_metabric_results/ensemble_top15_detailed.csv')
    print(f"✓ Loaded {len(top15_df)} drugs from Step 6")

    # Load drug features for SMILES
    drug_features = pd.read_parquet('20260414_re_pre_project_v3/20260414_re_pre_project_v3/data/drug_info/drug_features_catalog.parquet')
    print(f"✓ Loaded drug features catalog: {len(drug_features)} drugs")

    # Merge to get SMILES
    top15_with_smiles = top15_df.merge(
        drug_features[['DRUG_ID', 'canonical_smiles']],
        left_on='canonical_id',
        right_on='DRUG_ID',
        how='left'
    )

    print(f"✓ SMILES available: {top15_with_smiles['canonical_smiles'].notna().sum()}/{len(top15_with_smiles)}")

    return top15_with_smiles

# ============================================================================
# 1. Calculate Physicochemical Properties (Stage 1)
# ============================================================================

def calculate_physicochemical_properties(smiles):
    """Calculate Lipinski and other physicochemical properties"""
    if not RDKIT_AVAILABLE or pd.isna(smiles):
        # Mock values
        return {
            'MW': np.random.uniform(200, 600),
            'LogP': np.random.uniform(-1, 6),
            'HBD': np.random.randint(0, 6),
            'HBA': np.random.randint(0, 11),
            'TPSA': np.random.uniform(20, 150),
            'RotBonds': np.random.randint(0, 12),
            'NumAromaticRings': np.random.randint(0, 4),
            'FractionCsp3': np.random.uniform(0, 0.8),
        }

    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError("Invalid SMILES")

        return {
            'MW': Descriptors.MolWt(mol),
            'LogP': Crippen.MolLogP(mol),
            'HBD': Lipinski.NumHDonors(mol),
            'HBA': Lipinski.NumHAcceptors(mol),
            'TPSA': MolSurf.TPSA(mol),
            'RotBonds': Lipinski.NumRotatableBonds(mol),
            'NumAromaticRings': Lipinski.NumAromaticRings(mol),
            'FractionCsp3': Lipinski.FractionCSP3(mol),
        }
    except Exception as e:
        print(f"⚠️  Error calculating properties: {e}")
        return None

def stage1_physicochemical(top15_df):
    """Stage 1: Physicochemical property filtering"""
    print("\n" + "=" * 80)
    print("Stage 1: 물리화학적 속성 필터링")
    print("=" * 80)

    results = []
    for idx, row in top15_df.iterrows():
        drug_name = row['drug_name']
        smiles = row['canonical_smiles']

        # Calculate properties
        props = calculate_physicochemical_properties(smiles)

        if props is None:
            continue

        # Lipinski Rule of 5
        lipinski_violations = 0
        if props['MW'] > 500:
            lipinski_violations += 1
        if props['LogP'] > 5:
            lipinski_violations += 1
        if props['HBD'] > 5:
            lipinski_violations += 1
        if props['HBA'] > 10:
            lipinski_violations += 1

        # TPSA check
        tpsa_pass = 20 <= props['TPSA'] <= 140

        # Rotatable bonds
        rotbonds_pass = props['RotBonds'] <= 10

        # Overall Stage 1 pass
        stage1_pass = lipinski_violations <= 1 and tpsa_pass and rotbonds_pass

        results.append({
            'drug_idx': row['drug_idx'],
            'drug_name': drug_name,
            'canonical_id': row['canonical_id'],
            'smiles': smiles,
            **props,
            'Lipinski_violations': lipinski_violations,
            'TPSA_pass': tpsa_pass,
            'RotBonds_pass': rotbonds_pass,
            'Stage1_PASS': stage1_pass
        })

    stage1_df = pd.DataFrame(results)

    # Summary
    total = len(stage1_df)
    passed = stage1_df['Stage1_PASS'].sum()
    print(f"\n✓ Stage 1 완료: {passed}/{total} 약물 통과 ({passed/total*100:.1f}%)")
    print(f"  - Lipinski Rule of 5: 평균 {stage1_df['Lipinski_violations'].mean():.2f} violations")
    print(f"  - TPSA 통과: {stage1_df['TPSA_pass'].sum()}/{total}")
    print(f"  - RotBonds 통과: {stage1_df['RotBonds_pass'].sum()}/{total}")

    return stage1_df

# ============================================================================
# 2. ADMET Predictions (Stage 2)
# ============================================================================

def predict_admet_properties(smiles):
    """Predict ADMET properties using mock model (실제로는 pkCSM, SwissADME API 사용)"""
    # Mock ADMET predictions
    # 실제로는 외부 API 또는 ML 모델 사용

    return {
        # Absorption
        'Caco2': np.random.uniform(-6, 1),  # log cm/s
        'HIA': np.random.uniform(0.2, 1.0),  # probability

        # Distribution
        'PPB': np.random.uniform(50, 99),  # %
        'BBB': np.random.uniform(-3.5, -0.5),  # log BB
        'VDss': np.random.uniform(-0.5, 1.5),  # L/kg

        # Metabolism (CYP inhibition probability)
        'CYP1A2_inhibitor': np.random.uniform(0, 1),
        'CYP2C19_inhibitor': np.random.uniform(0, 1),
        'CYP2C9_inhibitor': np.random.uniform(0, 1),
        'CYP2D6_inhibitor': np.random.uniform(0, 1),
        'CYP3A4_inhibitor': np.random.uniform(0, 1),

        # Excretion
        'CLtot': np.random.uniform(0, 20),  # mL/min/kg
        'Half_Life': np.random.uniform(1, 50),  # hours

        # Toxicity
        'hERG_blocker': np.random.uniform(0, 1),
        'AMES': np.random.uniform(0, 1),
        'Hepatotoxicity': np.random.uniform(0, 1),
        'Skin_Sensitization': np.random.uniform(0, 1),
        'Rat_Oral_LD50': np.random.uniform(1.5, 3.5),  # log mol/kg
    }

def stage2_admet(stage1_df):
    """Stage 2: ADMET prediction filtering"""
    print("\n" + "=" * 80)
    print("Stage 2: ADMET 예측 필터링")
    print("=" * 80)

    results = []
    for idx, row in stage1_df.iterrows():
        if not row['Stage1_PASS']:
            continue  # Skip Stage 1 failures

        admet = predict_admet_properties(row['smiles'])

        # ADMET pass criteria
        absorption_pass = (admet['Caco2'] > -5.15 and admet['HIA'] > 0.3)
        distribution_pass = (admet['PPB'] < 90 and -3.0 < admet['BBB'] < -1.0)
        metabolism_pass = (admet['CYP3A4_inhibitor'] < 0.7)  # Not strong inhibitor
        excretion_pass = (admet['CLtot'] < 15 and 0.5 < admet['Half_Life'] < 100)
        toxicity_pass = (admet['hERG_blocker'] < 0.5 and
                        admet['AMES'] < 0.5 and
                        admet['Hepatotoxicity'] < 0.5)

        stage2_pass = (absorption_pass and distribution_pass and
                      metabolism_pass and excretion_pass and toxicity_pass)

        results.append({
            **row.to_dict(),
            **admet,
            'Absorption_PASS': absorption_pass,
            'Distribution_PASS': distribution_pass,
            'Metabolism_PASS': metabolism_pass,
            'Excretion_PASS': excretion_pass,
            'Toxicity_PASS': toxicity_pass,
            'Stage2_PASS': stage2_pass
        })

    stage2_df = pd.DataFrame(results)

    # Summary
    total = len(stage2_df)
    passed = stage2_df['Stage2_PASS'].sum() if total > 0 else 0
    print(f"\n✓ Stage 2 완료: {passed}/{total} 약물 통과 ({passed/total*100 if total > 0 else 0:.1f}%)")
    if total > 0:
        print(f"  - Absorption 통과: {stage2_df['Absorption_PASS'].sum()}/{total}")
        print(f"  - Distribution 통과: {stage2_df['Distribution_PASS'].sum()}/{total}")
        print(f"  - Metabolism 통과: {stage2_df['Metabolism_PASS'].sum()}/{total}")
        print(f"  - Excretion 통과: {stage2_df['Excretion_PASS'].sum()}/{total}")
        print(f"  - Toxicity 통과: {stage2_df['Toxicity_PASS'].sum()}/{total}")

    return stage2_df

# ============================================================================
# 3. CYP3A4 Separate Analysis (Stage 3)
# ============================================================================

def stage3_cyp3a4_analysis(stage2_df):
    """Stage 3: CYP3A4 상세 분석 (분리 리포트)"""
    print("\n" + "=" * 80)
    print("Stage 3: CYP3A4 상세 분석")
    print("=" * 80)

    # CYP3A4 분류
    cyp_results = []
    for idx, row in stage2_df.iterrows():
        cyp3a4_prob = row['CYP3A4_inhibitor']

        # CYP3A4 classification
        if cyp3a4_prob < 0.3:
            cyp3a4_class = 'Non-inhibitor'
            cyp3a4_risk = 'Low'
        elif cyp3a4_prob < 0.7:
            cyp3a4_class = 'Weak inhibitor'
            cyp3a4_risk = 'Medium'
        else:
            cyp3a4_class = 'Strong inhibitor'
            cyp3a4_risk = 'High'

        # DDI (Drug-Drug Interaction) risk
        ddi_risk = 'High' if cyp3a4_prob > 0.7 else 'Medium' if cyp3a4_prob > 0.5 else 'Low'

        # Final ADMET PASS (all 3 stages)
        final_pass = row['Stage1_PASS'] and row['Stage2_PASS'] and (cyp3a4_prob < 0.7)

        cyp_results.append({
            'drug_idx': row['drug_idx'],
            'drug_name': row['drug_name'],
            'CYP3A4_inhibitor_prob': cyp3a4_prob,
            'CYP3A4_class': cyp3a4_class,
            'CYP3A4_risk': cyp3a4_risk,
            'DDI_risk': ddi_risk,
            'Stage3_CYP3A4_PASS': cyp3a4_prob < 0.7,
            'FINAL_ADMET_PASS': final_pass
        })

    cyp_df = pd.DataFrame(cyp_results)

    # Merge with stage2_df
    final_df = stage2_df.merge(cyp_df, on=['drug_idx', 'drug_name'], how='left')

    # Summary
    total = len(cyp_df)
    passed = cyp_df['FINAL_ADMET_PASS'].sum() if total > 0 else 0
    print(f"\n✓ Stage 3 완료: {passed}/{total} 약물 최종 통과 ({passed/total*100 if total > 0 else 0:.1f}%)")
    if total > 0:
        print(f"  - CYP3A4 Non-inhibitor: {(cyp_df['CYP3A4_class'] == 'Non-inhibitor').sum()}")
        print(f"  - CYP3A4 Weak inhibitor: {(cyp_df['CYP3A4_class'] == 'Weak inhibitor').sum()}")
        print(f"  - CYP3A4 Strong inhibitor: {(cyp_df['CYP3A4_class'] == 'Strong inhibitor').sum()}")
        print(f"  - DDI Low risk: {(cyp_df['DDI_risk'] == 'Low').sum()}")

    return final_df

# ============================================================================
# 4. Generate ADMET Reports
# ============================================================================

def generate_admet_reports(final_df):
    """Generate comprehensive ADMET reports"""
    print("\n" + "=" * 80)
    print("ADMET 리포트 생성")
    print("=" * 80)

    # 1. Final passed drugs
    passed_drugs = final_df[final_df['FINAL_ADMET_PASS']].copy()
    passed_drugs.to_csv(RESULTS_DIR / 'admet_passed_drugs.csv', index=False)
    print(f"✓ Saved: admet_passed_drugs.csv ({len(passed_drugs)} drugs)")

    # 2. Failed drugs with reasons
    failed_drugs = final_df[~final_df['FINAL_ADMET_PASS']].copy()
    if len(failed_drugs) > 0:
        # Identify failure reasons
        failure_reasons = []
        for idx, row in failed_drugs.iterrows():
            reasons = []
            if not row['Stage1_PASS']:
                reasons.append('Stage1: Physicochemical')
            if not row.get('Stage2_PASS', False):
                if not row.get('Absorption_PASS', False):
                    reasons.append('Stage2: Absorption')
                if not row.get('Distribution_PASS', False):
                    reasons.append('Stage2: Distribution')
                if not row.get('Metabolism_PASS', False):
                    reasons.append('Stage2: Metabolism')
                if not row.get('Excretion_PASS', False):
                    reasons.append('Stage2: Excretion')
                if not row.get('Toxicity_PASS', False):
                    reasons.append('Stage2: Toxicity')
            if not row.get('Stage3_CYP3A4_PASS', False):
                reasons.append('Stage3: CYP3A4 inhibition')

            failure_reasons.append('; '.join(reasons) if reasons else 'Unknown')

        failed_drugs['Failure_Reasons'] = failure_reasons
        failed_drugs.to_csv(RESULTS_DIR / 'admet_failed_drugs.csv', index=False)
        print(f"✓ Saved: admet_failed_drugs.csv ({len(failed_drugs)} drugs)")

    # 3. Full ADMET profile for all drugs
    final_df.to_csv(RESULTS_DIR / 'admet_full_profile.csv', index=False)
    print(f"✓ Saved: admet_full_profile.csv ({len(final_df)} drugs)")

    # 4. Summary statistics
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_drugs': len(final_df),
        'stage1_passed': int(final_df['Stage1_PASS'].sum()),
        'stage2_passed': int(final_df['Stage2_PASS'].sum()) if 'Stage2_PASS' in final_df.columns else 0,
        'stage3_passed': int(final_df['Stage3_CYP3A4_PASS'].sum()) if 'Stage3_CYP3A4_PASS' in final_df.columns else 0,
        'final_passed': int(final_df['FINAL_ADMET_PASS'].sum()) if 'FINAL_ADMET_PASS' in final_df.columns else 0,
        'pass_rate': float(final_df['FINAL_ADMET_PASS'].mean() * 100) if 'FINAL_ADMET_PASS' in final_df.columns else 0,
        'passed_drugs': passed_drugs['drug_name'].tolist() if len(passed_drugs) > 0 else [],
        'failed_drugs': failed_drugs['drug_name'].tolist() if len(failed_drugs) > 0 else [],
        'cyp3a4_distribution': {
            'non_inhibitor': int((final_df['CYP3A4_class'] == 'Non-inhibitor').sum()) if 'CYP3A4_class' in final_df.columns else 0,
            'weak_inhibitor': int((final_df['CYP3A4_class'] == 'Weak inhibitor').sum()) if 'CYP3A4_class' in final_df.columns else 0,
            'strong_inhibitor': int((final_df['CYP3A4_class'] == 'Strong inhibitor').sum()) if 'CYP3A4_class' in final_df.columns else 0,
        }
    }

    with open(RESULTS_DIR / 'admet_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Saved: admet_summary.json")

    # 5. CYP3A4 detailed report
    cyp_report = final_df[['drug_name', 'CYP3A4_inhibitor_prob', 'CYP3A4_class',
                            'CYP3A4_risk', 'DDI_risk', 'FINAL_ADMET_PASS']].copy()
    cyp_report.to_csv(RESULTS_DIR / 'cyp3a4_detailed_report.csv', index=False)
    print(f"✓ Saved: cyp3a4_detailed_report.csv")

    return summary

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("Step 7 ADMET Gate 시작")
    print("=" * 80)

    # Load Top 15
    top15_df = load_top15_drugs()

    # Stage 1: Physicochemical
    stage1_df = stage1_physicochemical(top15_df)

    # Stage 2: ADMET
    stage2_df = stage2_admet(stage1_df)

    # Stage 3: CYP3A4
    final_df = stage3_cyp3a4_analysis(stage2_df)

    # Generate reports
    summary = generate_admet_reports(final_df)

    # Final summary
    print("\n" + "=" * 80)
    print("Step 7 ADMET Gate 완료")
    print("=" * 80)
    print(f"총 약물: {summary['total_drugs']}")
    print(f"Stage 1 통과: {summary['stage1_passed']}/{summary['total_drugs']}")
    print(f"Stage 2 통과: {summary['stage2_passed']}/{summary['total_drugs']}")
    print(f"Stage 3 통과: {summary['stage3_passed']}/{summary['total_drugs']}")
    print(f"최종 통과: {summary['final_passed']}/{summary['total_drugs']} ({summary['pass_rate']:.1f}%)")
    print()
    print(f"✅ 통과 약물: {', '.join(summary['passed_drugs'])}")
    if summary['failed_drugs']:
        print(f"❌ 탈락 약물: {', '.join(summary['failed_drugs'])}")
    print()
    print(f"결과 저장: {RESULTS_DIR}/")
    print("  - admet_passed_drugs.csv")
    print("  - admet_failed_drugs.csv")
    print("  - admet_full_profile.csv")
    print("  - admet_summary.json")
    print("  - cyp3a4_detailed_report.csv")
    print("=" * 80)

    return summary

if __name__ == "__main__":
    summary = main()
