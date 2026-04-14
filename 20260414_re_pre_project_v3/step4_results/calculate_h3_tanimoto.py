#!/usr/bin/env python3
"""
H3 Tanimoto Similarity Calculation
- Top 30 drugs vs FDA-approved breast cancer drugs
- SMILES from PubChem
- Morgan fingerprint, Tanimoto similarity
"""

import requests
import time
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import DataStructs
from pathlib import Path
import json

# FDA-approved breast cancer drugs (comprehensive list)
FDA_BRCA_DRUGS = {
    # Hormone therapy
    "Tamoxifen": None,
    "Letrozole": None,
    "Anastrozole": None,
    "Exemestane": None,
    "Fulvestrant": None,
    "Toremifene": None,
    "Raloxifene": None,

    # HER2-targeted (small molecules only)
    "Lapatinib": None,
    "Neratinib": None,
    "Tucatinib": None,

    # CDK4/6 inhibitors
    "Palbociclib": None,
    "Ribociclib": None,
    "Abemaciclib": None,

    # Chemotherapy (small molecules)
    "Doxorubicin": None,
    "Paclitaxel": None,
    "Docetaxel": None,
    "Cyclophosphamide": None,
    "Capecitabine": None,
    "Carboplatin": None,
    "Cisplatin": None,
    "Eribulin": None,
    "Ixabepilone": None,
    "Vinorelbine": None,
    "Gemcitabine": None,
    "Methotrexate": None,
    "Fluorouracil": None,
    "Epirubicin": None,

    # PARP inhibitors
    "Olaparib": None,
    "Talazoparib": None,

    # PI3K inhibitors
    "Alpelisib": None,

    # mTOR inhibitors
    "Everolimus": None,

    # Other targeted therapies
    "Bevacizumab": None,  # May not have SMILES (antibody)
}

def get_smiles_from_pubchem(drug_name, retries=3):
    """Fetch SMILES from PubChem by drug name"""
    for attempt in range(retries):
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/property/IsomericSMILES/JSON"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # IsomericSMILES returns key "SMILES", not "IsomericSMILES"
                smiles = data['PropertyTable']['Properties'][0]['SMILES']
                print(f"  ✓ {drug_name}: {smiles[:60]}{'...' if len(smiles) > 60 else ''}")
                return smiles
            elif response.status_code == 404:
                print(f"  ✗ {drug_name}: Not found in PubChem")
                return None
            else:
                print(f"  ⚠ {drug_name}: HTTP {response.status_code}")

        except Exception as e:
            print(f"  ⚠ {drug_name}: {str(e)}")
            if attempt < retries - 1:
                time.sleep(1)

    return None

def calculate_tanimoto(smiles1, smiles2):
    """Calculate Tanimoto similarity using Morgan fingerprints"""
    try:
        mol1 = Chem.MolFromSmiles(smiles1)
        mol2 = Chem.MolFromSmiles(smiles2)

        if mol1 is None or mol2 is None:
            return None

        fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
        fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)

        return DataStructs.TanimotoSimilarity(fp1, fp2)
    except:
        return None

def get_h3_verdict(similarity):
    """Apply H3 criteria from v2 protocol"""
    if similarity is None or np.isnan(similarity):
        return "UNKNOWN"
    if similarity > 0.3:
        return "PASS"
    elif similarity >= 0.1:
        return "WARNING"
    else:
        return "FAIL"

def main():
    print("="*80)
    print("H3 Tanimoto Similarity - Top 30 vs FDA Breast Cancer Drugs")
    print("="*80)

    # 1. Collect SMILES for FDA drugs
    print("\n[1/4] Collecting SMILES for FDA breast cancer drugs from PubChem...")
    fda_drugs = FDA_BRCA_DRUGS.copy()

    for drug_name in fda_drugs.keys():
        smiles = get_smiles_from_pubchem(drug_name)
        fda_drugs[drug_name] = smiles
        time.sleep(0.3)  # Rate limiting

    # Filter out drugs without SMILES
    fda_with_smiles = {k: v for k, v in fda_drugs.items() if v is not None}
    print(f"\n  FDA drugs with SMILES: {len(fda_with_smiles)}/{len(fda_drugs)}")

    # 2. Load Top 30 drugs
    print("\n[2/4] Loading Top 30 drugs...")
    step3_file = Path("step3_results/top30_drugs.csv")

    if not step3_file.exists():
        print(f"  ✗ File not found: {step3_file}")
        print("  Trying alternative locations...")

        # Try finding in step4_results
        alt_files = [
            Path("top30_drugs.csv"),
            Path("../step3_results/top30_drugs.csv"),
            Path("step4_results/top30_drugs.csv"),
        ]

        for alt_file in alt_files:
            if alt_file.exists():
                step3_file = alt_file
                print(f"  ✓ Found: {step3_file}")
                break

    if not step3_file.exists():
        # Create from reclassification summary
        print("  Creating Top 30 from reclassification data...")
        reclass_file = Path("drug_reclassification/reclassification_summary.csv")
        if reclass_file.exists():
            df_reclass = pd.read_csv(reclass_file)
            top30_drugs = df_reclass['약물명'].tolist()
            print(f"  ✓ Loaded {len(top30_drugs)} drugs from reclassification")
        else:
            print("  ✗ Cannot find drug list. Exiting.")
            return
    else:
        df_top30 = pd.read_csv(step3_file)
        top30_drugs = df_top30['약물명'].tolist() if '약물명' in df_top30.columns else df_top30.iloc[:, 0].tolist()
        print(f"  ✓ Loaded {len(top30_drugs)} drugs")

    # Get SMILES for Top 30
    print("\n[3/4] Collecting SMILES for Top 30 drugs...")
    top30_smiles = {}
    for drug in top30_drugs:
        smiles = get_smiles_from_pubchem(drug)
        if smiles:
            top30_smiles[drug] = smiles
        time.sleep(0.3)

    print(f"\n  Top 30 drugs with SMILES: {len(top30_smiles)}/{len(top30_drugs)}")

    # 3. Calculate Tanimoto similarities
    print("\n[4/4] Calculating Tanimoto similarities...")
    results = []

    for top30_drug, top30_smi in top30_smiles.items():
        print(f"\n  {top30_drug}:")
        similarities = {}

        for fda_drug, fda_smi in fda_with_smiles.items():
            sim = calculate_tanimoto(top30_smi, fda_smi)
            if sim is not None:
                similarities[fda_drug] = sim

        if similarities:
            # Find most similar FDA drug
            best_fda = max(similarities, key=similarities.get)
            best_sim = similarities[best_fda]
            verdict = get_h3_verdict(best_sim)

            print(f"    → Most similar: {best_fda} (Tanimoto: {best_sim:.4f}) [{verdict}]")

            results.append({
                "약물명": top30_drug,
                "SMILES": top30_smi,
                "가장_유사한_FDA약": best_fda,
                "Tanimoto": round(best_sim, 4),
                "H3_판정": verdict,
                "상위3_FDA약": ", ".join([f"{k}({v:.3f})" for k, v in sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:3]])
            })
        else:
            print(f"    → No valid similarities calculated")
            results.append({
                "약물명": top30_drug,
                "SMILES": top30_smi,
                "가장_유사한_FDA약": "N/A",
                "Tanimoto": None,
                "H3_판정": "UNKNOWN",
                "상위3_FDA약": ""
            })

    # 4. Save results
    if not results:
        print("\n  ✗ No valid results to save. Exiting.")
        return

    df_results = pd.DataFrame(results)

    # Sort by Tanimoto descending (if column exists)
    if 'Tanimoto' in df_results.columns and len(df_results) > 0:
        df_results = df_results.sort_values('Tanimoto', ascending=False, na_position='last')

    output_csv = Path("h3_tanimoto_results.csv")
    df_results.to_csv(output_csv, index=False, encoding='utf-8-sig')

    print("\n" + "="*80)
    print("Results Summary")
    print("="*80)

    # Count by verdict
    verdict_counts = df_results['H3_판정'].value_counts()
    print(f"\nH3 Verdict Distribution:")
    for verdict, count in verdict_counts.items():
        print(f"  {verdict}: {count}개")

    # Top 5 most similar
    print(f"\nTop 5 Most Similar to FDA Drugs:")
    print("-" * 80)
    for idx, row in df_results.head(5).iterrows():
        print(f"  {row['약물명']:20s} → {row['가장_유사한_FDA약']:20s} ({row['Tanimoto']:.4f}) [{row['H3_판정']}]")

    # Bottom 5 least similar
    print(f"\nTop 5 Least Similar to FDA Drugs:")
    print("-" * 80)
    valid_rows = df_results[df_results['Tanimoto'].notna()]
    for idx, row in valid_rows.tail(5).iterrows():
        print(f"  {row['약물명']:20s} → {row['가장_유사한_FDA약']:20s} ({row['Tanimoto']:.4f}) [{row['H3_판정']}]")

    print(f"\n✓ Saved: {output_csv}")
    print("="*80)

    # Save FDA drug SMILES for reference
    fda_json = Path("fda_brca_drugs_smiles.json")
    with open(fda_json, 'w', encoding='utf-8') as f:
        json.dump(fda_drugs, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved FDA drug SMILES: {fda_json}")

if __name__ == "__main__":
    main()
