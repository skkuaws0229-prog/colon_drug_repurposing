"""
Step 7: ADMET Gate (TDC ML 예측 버전)

v1과 동일하게 TDC (Therapeutics Data Commons) 사용
22개 ADMET assay 실제 ML 예측
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Try importing TDC
try:
    from tdc import ADMET
    from tdc.generation import MolGen
    TDC_AVAILABLE = True
    print("✓ TDC library available")
except ImportError:
    TDC_AVAILABLE = False
    print("⚠️  TDC not available. Installing...")
    import subprocess
    subprocess.run(['pip', 'install', 'PyTDC'], check=False)
    try:
        from tdc import ADMET
        TDC_AVAILABLE = True
        print("✓ TDC installed successfully")
    except:
        TDC_AVAILABLE = False
        print("❌ TDC installation failed. Using fallback.")

# RDKit for molecular property calculation
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, Crippen, MolSurf
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    print("⚠️  RDKit not available")

print("=" * 80)
print("Step 7: ADMET Gate (TDC ML 예측)")
print("=" * 80)

# ============================================================================
# Configuration
# ============================================================================

RESULTS_DIR = Path("step7_admet_results_tdc")
RESULTS_DIR.mkdir(exist_ok=True)

# TDC ADMET assay names (v1과 동일)
TDC_ASSAYS = {
    # Absorption
    'Caco2_Wang': {'name': 'Caco-2 Permeability', 'type': 'regression'},
    'HIA_Hou': {'name': 'Human Intestinal Absorption', 'type': 'classification'},
    'Pgp_Broccatelli': {'name': 'P-glycoprotein Inhibitor', 'type': 'classification'},
    'Bioavailability_Ma': {'name': 'Oral Bioavailability (F>20%)', 'type': 'classification'},

    # Distribution
    'BBB_Martins': {'name': 'Blood-Brain Barrier Penetration', 'type': 'classification'},
    'PPBR_AZ': {'name': 'Plasma Protein Binding Rate', 'type': 'regression'},
    'VDss_Lombardo': {'name': 'Volume of Distribution', 'type': 'regression'},

    # Metabolism
    'CYP2C9_Veith': {'name': 'CYP2C9 Inhibitor', 'type': 'classification'},
    'CYP2D6_Veith': {'name': 'CYP2D6 Inhibitor', 'type': 'classification'},
    'CYP3A4_Veith': {'name': 'CYP3A4 Inhibitor', 'type': 'classification'},
    'CYP2C9_Substrate_CarbonMangels': {'name': 'CYP2C9 Substrate', 'type': 'classification'},
    'CYP2D6_Substrate_CarbonMangels': {'name': 'CYP2D6 Substrate', 'type': 'classification'},
    'CYP3A4_Substrate_CarbonMangels': {'name': 'CYP3A4 Substrate', 'type': 'classification'},

    # Excretion
    'Clearance_Hepatocyte_AZ': {'name': 'Hepatocyte Clearance', 'type': 'regression'},
    'Clearance_Microsome_AZ': {'name': 'Microsome Clearance', 'type': 'regression'},
    'Half_Life_Obach': {'name': 'Half-Life', 'type': 'regression'},

    # Toxicity
    'AMES': {'name': 'Ames Mutagenicity', 'type': 'classification'},
    'DILI': {'name': 'Drug-Induced Liver Injury', 'type': 'classification'},
    'hERG': {'name': 'hERG Cardiotoxicity', 'type': 'classification'},
    'LD50_Zhu': {'name': 'Acute Toxicity (LD50)', 'type': 'regression'},

    # Physicochemical
    'Lipophilicity_AstraZeneca': {'name': 'Lipophilicity (logD)', 'type': 'regression'},
    'Solubility_AqSolDB': {'name': 'Aqueous Solubility', 'type': 'regression'},
}

print(f"Results directory: {RESULTS_DIR}")
print(f"TDC available: {TDC_AVAILABLE}")
print(f"Total assays: {len(TDC_ASSAYS)}")

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
# 1. TDC ADMET Prediction
# ============================================================================

def predict_tdc_admet(smiles, assay_name):
    """Predict ADMET property using TDC"""
    if not TDC_AVAILABLE or pd.isna(smiles):
        return None

    try:
        # Load TDC model for the assay
        model = ADMET(name=assay_name)

        # Prepare input
        data = pd.DataFrame({'Drug': [smiles]})

        # Get prediction
        prediction = model.predict(data)

        if isinstance(prediction, (list, np.ndarray)):
            return float(prediction[0])
        else:
            return float(prediction)

    except Exception as e:
        print(f"  ⚠️  Error predicting {assay_name}: {e}")
        return None

def calculate_all_admet(drug_row):
    """Calculate all 22 ADMET properties for a drug"""
    smiles = drug_row['canonical_smiles']
    drug_name = drug_row['drug_name']

    print(f"\n  Processing: {drug_name}")

    results = {
        'drug_idx': drug_row['drug_idx'],
        'drug_name': drug_name,
        'canonical_id': drug_row['canonical_id'],
        'smiles': smiles,
    }

    if pd.isna(smiles):
        print(f"    ⚠️  No SMILES available")
        return results

    # Predict all assays
    n_success = 0
    for assay_name, assay_info in TDC_ASSAYS.items():
        pred = predict_tdc_admet(smiles, assay_name)
        results[assay_name] = pred
        if pred is not None:
            n_success += 1

    print(f"    ✓ {n_success}/{len(TDC_ASSAYS)} assays completed")

    return results

# ============================================================================
# 2. ADMET Filtering and Scoring
# ============================================================================

def calculate_safety_score(admet_results):
    """Calculate safety score based on ADMET results"""
    score = 10.0  # Start with perfect score
    flags = []

    # Toxicity penalties
    if admet_results.get('AMES') == 1:  # Mutagenic
        score -= 2.0
        flags.append('AMES(+)')

    if admet_results.get('DILI') == 1:  # Hepatotoxic
        score -= 1.0
        flags.append('DILI(+)')

    if admet_results.get('hERG') == 1:  # Cardiotoxic
        score -= 2.0
        flags.append('hERG(+)')

    # LD50 (lower is more toxic)
    ld50 = admet_results.get('LD50_Zhu')
    if ld50 is not None and ld50 < 2.0:
        score -= 1.5
        flags.append('LD50_low')

    # Absorption issues
    if admet_results.get('HIA_Hou') == 0:  # Poor absorption
        score -= 0.5
        flags.append('HIA_poor')

    if admet_results.get('Bioavailability_Ma') == 0:  # Low bioavailability
        score -= 0.5
        flags.append('Bioavailability_low')

    # Metabolism issues (CYP inhibition - drug interactions)
    if admet_results.get('CYP3A4_Veith') == 1:
        score -= 0.5
        flags.append('CYP3A4_inhibitor')

    # Keep score >= 0
    score = max(0.0, score)

    return score, flags

def filter_and_rank_drugs(admet_df):
    """Filter and rank drugs based on ADMET"""
    print("\n" + "=" * 80)
    print("ADMET 필터링 및 순위 계산")
    print("=" * 80)

    results = []

    for idx, row in admet_df.iterrows():
        # Calculate safety score
        safety_score, flags = calculate_safety_score(row)

        # Count available assays
        n_assays_tested = sum(1 for k, v in row.items()
                             if k in TDC_ASSAYS.keys() and v is not None)

        # Categorize
        if safety_score >= 7.0:
            category = 'Safe'
        elif safety_score >= 5.0:
            category = 'Acceptable'
        elif safety_score >= 3.0:
            category = 'Caution'
        else:
            category = 'High Risk'

        # ADMET pass criteria
        admet_pass = (
            safety_score >= 5.0 and
            row.get('AMES', 1) == 0 and  # Not mutagenic
            row.get('hERG', 1) == 0 and  # Not cardiotoxic
            row.get('HIA_Hou', 0) == 1   # Good absorption
        )

        results.append({
            'drug_idx': row['drug_idx'],
            'drug_name': row['drug_name'],
            'canonical_id': row['canonical_id'],
            'safety_score': safety_score,
            'n_assays_tested': n_assays_tested,
            'category': category,
            'flags': '; '.join(flags) if flags else 'None',
            'ADMET_PASS': admet_pass,
            **{k: row.get(k) for k in TDC_ASSAYS.keys()}
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('safety_score', ascending=False)
    results_df['rank'] = range(1, len(results_df) + 1)

    # Summary
    total = len(results_df)
    passed = results_df['ADMET_PASS'].sum()
    print(f"\n✓ 필터링 완료")
    print(f"  - 총 약물: {total}")
    print(f"  - ADMET 통과: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"  - Safe: {(results_df['category'] == 'Safe').sum()}")
    print(f"  - Acceptable: {(results_df['category'] == 'Acceptable').sum()}")
    print(f"  - Caution: {(results_df['category'] == 'Caution').sum()}")
    print(f"  - High Risk: {(results_df['category'] == 'High Risk').sum()}")

    return results_df

# ============================================================================
# 3. Generate Reports
# ============================================================================

def generate_reports(results_df):
    """Generate comprehensive ADMET reports"""
    print("\n" + "=" * 80)
    print("리포트 생성")
    print("=" * 80)

    # 1. Passed drugs
    passed_df = results_df[results_df['ADMET_PASS']].copy()
    passed_df.to_csv(RESULTS_DIR / 'admet_passed_drugs.csv', index=False)
    print(f"✓ Saved: admet_passed_drugs.csv ({len(passed_df)} drugs)")

    # 2. Failed drugs
    failed_df = results_df[~results_df['ADMET_PASS']].copy()
    failed_df.to_csv(RESULTS_DIR / 'admet_failed_drugs.csv', index=False)
    print(f"✓ Saved: admet_failed_drugs.csv ({len(failed_df)} drugs)")

    # 3. Full profile
    results_df.to_csv(RESULTS_DIR / 'admet_full_profile.csv', index=False)
    print(f"✓ Saved: admet_full_profile.csv")

    # 4. Summary JSON
    summary = {
        'timestamp': datetime.now().isoformat(),
        'library': 'TDC (Therapeutics Data Commons)',
        'n_assays': len(TDC_ASSAYS),
        'total_drugs': len(results_df),
        'passed_drugs': int(passed_df.shape[0]),
        'pass_rate': float(passed_df.shape[0] / len(results_df) * 100) if len(results_df) > 0 else 0,
        'passed_drug_names': passed_df['drug_name'].tolist() if len(passed_df) > 0 else [],
        'failed_drug_names': failed_df['drug_name'].tolist() if len(failed_df) > 0 else [],
        'category_distribution': results_df['category'].value_counts().to_dict(),
        'top_3_safest': results_df.nlargest(3, 'safety_score')[['rank', 'drug_name', 'safety_score', 'category']].to_dict('records'),
    }

    with open(RESULTS_DIR / 'admet_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Saved: admet_summary.json")

    # 5. CYP3A4 report
    cyp_report = results_df[['rank', 'drug_name', 'CYP3A4_Veith', 'CYP3A4_Substrate_CarbonMangels',
                              'safety_score', 'category']].copy()
    cyp_report.to_csv(RESULTS_DIR / 'cyp3a4_report.csv', index=False)
    print(f"✓ Saved: cyp3a4_report.csv")

    return summary

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("Step 7 ADMET Gate (TDC ML) 시작")
    print("=" * 80)

    if not TDC_AVAILABLE:
        print("\n❌ TDC library not available. Cannot proceed with ML predictions.")
        print("Please install TDC: pip install PyTDC")
        return None

    # Load Top 15
    top15_df = load_top15_drugs()

    # Predict ADMET for all drugs
    print("\n" + "=" * 80)
    print("1. TDC ADMET 예측 (22 assays)")
    print("=" * 80)

    admet_results = []
    for idx, row in top15_df.iterrows():
        result = calculate_all_admet(row)
        admet_results.append(result)

    admet_df = pd.DataFrame(admet_results)

    # Filter and rank
    results_df = filter_and_rank_drugs(admet_df)

    # Generate reports
    summary = generate_reports(results_df)

    # Final summary
    print("\n" + "=" * 80)
    print("Step 7 ADMET Gate (TDC ML) 완료")
    print("=" * 80)
    print(f"총 약물: {summary['total_drugs']}")
    print(f"ADMET 통과: {summary['passed_drugs']}/{summary['total_drugs']} ({summary['pass_rate']:.1f}%)")
    print()
    if summary['passed_drug_names']:
        print(f"✅ 통과 약물: {', '.join(summary['passed_drug_names'])}")
    if summary['failed_drug_names']:
        print(f"❌ 탈락 약물: {', '.join(summary['failed_drug_names'])}")
    print()
    print(f"Top 3 Safest Drugs:")
    for drug in summary['top_3_safest']:
        print(f"  {drug['rank']}. {drug['drug_name']} - Safety Score: {drug['safety_score']:.2f} ({drug['category']})")
    print()
    print(f"결과 저장: {RESULTS_DIR}/")
    print("  - admet_passed_drugs.csv")
    print("  - admet_failed_drugs.csv")
    print("  - admet_full_profile.csv")
    print("  - admet_summary.json")
    print("  - cyp3a4_report.csv")
    print("=" * 80)

    return summary

if __name__ == "__main__":
    summary = main()
