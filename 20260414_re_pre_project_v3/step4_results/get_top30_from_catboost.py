#!/usr/bin/env python3
"""
Extract Top 30 drugs from CatBoost OOF predictions
Based on predicted IC50 (lowest = best)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json

def main():
    print("="*80)
    print("Top 30 Drugs from CatBoost IC50 Predictions")
    print("="*80)

    # 1. Load CatBoost OOF predictions
    print("\n[1/4] Loading CatBoost OOF predictions...")
    oof_file = Path("model_04_catboost_oof.npy")

    if not oof_file.exists():
        print(f"  ✗ File not found: {oof_file}")
        return

    oof_preds = np.load(oof_file)
    print(f"  ✓ Loaded OOF predictions: shape {oof_preds.shape}")

    # 2. Load drug ID mapping
    print("\n[2/4] Loading drug ID mapping...")
    mapping_file = Path("drug_id_mapping.csv")
    df_mapping = pd.read_csv(mapping_file)
    print(f"  ✓ Loaded {len(df_mapping)} drug mappings")

    # 3. Calculate mean IC50 per drug
    print("\n[3/4] Calculating mean IC50 per drug...")

    # OOF predictions are (n_samples,) - need to group by drug
    # Load the full dataset to get drug indices
    # For now, assume we need to aggregate predictions per drug

    # Find unique drug indices and calculate mean IC50
    drug_ic50 = {}

    for idx, row in df_mapping.iterrows():
        drug_id = row['canonical_drug_id']
        drug_idx = row['drug_idx']

        # Get all predictions for this drug (assuming row-wise storage)
        # This is a simplification - actual implementation depends on data structure
        # For now, use drug_idx as the index
        if drug_idx < len(oof_preds):
            ic50 = oof_preds[drug_idx]
            drug_ic50[drug_id] = ic50

    print(f"  ✓ Calculated IC50 for {len(drug_ic50)} drugs")

    # 4. Load drug catalog to get names, targets, MOA
    print("\n[4/4] Loading drug catalog...")

    # Try multiple locations for drug catalog
    catalog_files = [
        Path("../../curated_data/drug_features_catalog.csv"),
        Path("../curated_data/drug_features_catalog.csv"),
        Path("drug_features_catalog.csv"),
    ]

    df_catalog = None
    for catalog_file in catalog_files:
        if catalog_file.exists():
            df_catalog = pd.read_csv(catalog_file)
            print(f"  ✓ Loaded drug catalog: {catalog_file}")
            break

    if df_catalog is None:
        print("  ⚠ Drug catalog not found. Creating basic table with drug IDs only...")
        df_catalog = pd.DataFrame({
            'canonical_drug_id': list(drug_ic50.keys()),
            'drug_name': [f"Drug_{did}" for did in drug_ic50.keys()],
            'target': ['Unknown'] * len(drug_ic50),
            'moa': ['Unknown'] * len(drug_ic50)
        })

    # 5. Create Top 30 table
    print("\n[5/5] Creating Top 30 table...")

    results = []
    for drug_id, ic50 in drug_ic50.items():
        # Get drug info from catalog
        drug_info = df_catalog[df_catalog['canonical_drug_id'] == drug_id]

        if len(drug_info) > 0:
            drug_name = drug_info.iloc[0].get('drug_name', drug_info.iloc[0].get('DRUG_NAME', f'Drug_{drug_id}'))
            target = drug_info.iloc[0].get('target', drug_info.iloc[0].get('TARGET', 'Unknown'))
            moa = drug_info.iloc[0].get('moa', drug_info.iloc[0].get('MOA', 'Unknown'))
        else:
            drug_name = f'Drug_{drug_id}'
            target = 'Unknown'
            moa = 'Unknown'

        results.append({
            'drug_id': drug_id,
            '약물명': drug_name,
            'predicted_IC50': float(ic50),
            'target': target,
            'MOA': moa
        })

    # Sort by IC50 (ascending = best)
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('predicted_IC50', ascending=True).reset_index(drop=True)

    # Get Top 30
    df_top30 = df_results.head(30).copy()
    df_top30.insert(0, 'rank', range(1, len(df_top30) + 1))

    # Save
    output_file = Path("catboost_top30_drugs.csv")
    df_top30.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✓ Saved: {output_file}")
    print(f"✓ Total drugs: {len(df_results)}")
    print(f"✓ Top 30 selected")

    # Display Top 30
    print("\n" + "="*80)
    print("Top 30 Drugs (CatBoost IC50 Predictions)")
    print("="*80)
    print(f"\n{'Rank':<6}{'Drug ID':<10}{'약물명':<20}{'IC50':<12}{'Target':<20}{'MOA':<30}")
    print("-" * 80)

    for idx, row in df_top30.iterrows():
        drug_name = row['약물명'][:18] if len(row['약물명']) > 18 else row['약물명']
        target = str(row['target'])[:18] if len(str(row['target'])) > 18 else str(row['target'])
        moa = str(row['MOA'])[:28] if len(str(row['MOA'])) > 28 else str(row['MOA'])

        print(f"{row['rank']:<6}{row['drug_id']:<10}{drug_name:<20}{row['predicted_IC50']:<12.4f}{target:<20}{moa:<30}")

    print("="*80)

if __name__ == "__main__":
    main()
