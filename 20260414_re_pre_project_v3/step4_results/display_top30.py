#!/usr/bin/env python3
import pandas as pd

# Use the comprehensive Top 30 from previous work (CatBoost-based)
top30_file = "/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260413_feature_reconstruction/results/top30_reextract_20260413/top30_reextract.csv"

df = pd.read_csv(top30_file)

print("="*100)
print("Top 30 Drugs from CatBoost IC50 Predictions")
print("="*100)
print(f"\n{'Rank':<6}{'Drug ID':<10}{'약물명':<25}{'예측 IC50':<15}{'Target':<35}{'Pathway/MOA':<30}")
print("-" * 100)

for idx, row in df.iterrows():
    rank = row['rank']
    drug_id = row['canonical_drug_id']
    drug_name = row['drug_name']
    ic50 = row['mean_pred_ic50']
    target = str(row['target']) if pd.notna(row['target']) else 'Unknown'
    pathway = str(row['pathway']) if pd.notna(row['pathway']) else 'Unknown'
    
    # Truncate long fields
    drug_name_short = drug_name[:23] if len(drug_name) > 23 else drug_name
    target_short = target[:33] if len(target) > 33 else target
    pathway_short = pathway[:28] if len(pathway) > 28 else pathway
    
    print(f"{rank:<6}{drug_id:<10}{drug_name_short:<25}{ic50:<15.4f}{target_short:<35}{pathway_short:<30}")

print("="*100)
print(f"\n✓ Total: 30 drugs")
print(f"✓ IC50 range: {df['mean_pred_ic50'].min():.4f} to {df['mean_pred_ic50'].max():.4f}")
print(f"✓ Source: CatBoost OOF predictions (5-fold cross-validation)")
print("="*100)
