#!/usr/bin/env python3
"""
Fix Step 6 Issues - Priority Order
1. Survival mapping
2. ADMET data loading
3. Target matching aliases
4. Subtype mapping
5. Clinical category improvement
"""

import numpy as np
import pandas as pd
import json
import requests
import time
from pathlib import Path
from collections import defaultdict
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski, Crippen
from rdkit import DataStructs
from sklearn.metrics import roc_auc_score, ndcg_score
import warnings
warnings.filterwarnings('ignore')

# Paths
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
INPUT_TOP30 = BASE_DIR / "20260413_feature_reconstruction/results/top30_reextract_20260413/top30_reextract.csv"
INPUT_SURVIVAL = BASE_DIR / "20260414_re_pre_project_v3/step4_results/step6_metabric_results/method_b_survival.json"
INPUT_H3 = BASE_DIR / "20260414_re_pre_project_v3/step4_results/h3_tanimoto_results.csv"
INPUT_ADMET1 = BASE_DIR / "20260414_re_pre_project_v3/step4_results/step7_admet_results/step7_admet_results.json"
INPUT_ADMET2 = BASE_DIR / "models/admet_results/step7_admet_results.json"
INPUT_FDA_SMILES = BASE_DIR / "20260414_re_pre_project_v3/step4_results/fda_brca_drugs_smiles.json"
OUTPUT_DIR = BASE_DIR / "20260414_re_pre_project_v3/step4_results/step6_final"

# Enhanced configurations
TARGET_ALIASES = {
    "ESR1": ["ER", "ERalpha", "estrogen receptor", "ESR"],
    "ERBB2": ["HER2", "HER-2", "neu"],
    "EGFR": ["HER1", "ERBB1"],
    "PIK3CA": ["PI3K", "PI3Kalpha", "p110alpha", "PI3K (class 1)"],
    "AKT1": ["AKT", "PKB", "AKT1/2", "AKT2"],
    "MTOR": ["mTOR", "FRAP1", "MTORC1", "MTORC2"],
    "HDAC1": ["HDAC", "histone deacetylase", "HDAC3"],
    "BRAF": ["B-RAF", "B-Raf"],
    "IKK": ["NF-kB", "NFkB", "NFKB1", "IKK-1", "IKK-2"],
    "TNKS": ["Tankyrase", "TNKS1", "TNKS2"],
    "NTRK": ["TRK", "TRKA", "NTRK1", "NTRK2", "NTRK3"],
    "USP1": ["USP1-UAF1"],
    "SMARCA": ["BRG1", "SWI/SNF", "SMARCA4", "SMARCA2", "Polybromo 1"],
    "Microtubule": ["tubulin", "beta-tubulin", "Microtubule stabiliser", "Microtubule destabiliser", "TUBB"],
    "TOP1": ["topoisomerase I", "Topotecan"],
    "TOP2": ["topoisomerase II", "TOP2A"],
    "BCL2": ["BCL-2", "Bcl-2", "BCL-XL", "BCL-W", "MCL1", "BFL1"],
    "MDM2": ["HDM2"],
    "CDK4": ["CDK4/6"],
    "CDK6": ["CDK4/6"],
    "CDK9": ["CDK9"],
    "AR": ["androgen receptor"],
    "VEGFR": ["VEGFR1", "VEGFR2", "VEGFR3", "FLT1", "FLT2", "FLT3", "FLT4", "KIT", "PDGFRB"],
    "FGFR": ["FGFR1", "FGFR2"],
    "MEK": ["MAPK"],
    "PARP1": ["PARP", "PARP2"],
    "BRCA1": ["BRCA1"],
    "BRCA2": ["BRCA2"],
    "TP53": ["p53", "TP53"],
    "CHEK1": ["CHK1", "CHEK1/2", "CHEK2"],
    "ATM": ["ATM"],
    "CCND1": ["Cyclin D1"],
    "MYC": ["c-Myc"],
    "PGR": ["PR", "progesterone receptor"],
}

BRCA_TARGETS_30 = {
    'BRCA1', 'BRCA2', 'HER2', 'ESR1', 'PGR', 'PIK3CA', 'AKT1', 'PTEN',
    'CDK4', 'CDK6', 'CCND1', 'TP53', 'MYC', 'EGFR', 'VEGFR', 'FGFR',
    'BRAF', 'MEK', 'MTOR', 'HDAC', 'AR', 'MDM2', 'IKK', 'TNKS',
    'NTRK', 'USP1', 'SMARCA', 'Microtubule', 'TOP1', 'TOP2',
    'ERBB2', 'BCL2', 'PARP1', 'CDK9', 'CHEK1', 'ATM',
}

SUBTYPE_TARGETS = {
    'ER+': ['ESR1', 'PGR', 'HDAC', 'MTOR', 'CDK4', 'CDK6', 'PIK3CA', 'AKT1', 'CCND1'],
    'HER2+': ['ERBB2', 'EGFR', 'FGFR', 'MTOR', 'PIK3CA', 'AKT1'],
    'TNBC': ['BRCA1', 'BRCA2', 'AR', 'TNKS', 'IKK', 'Microtubule', 'TOP1', 'TOP2', 'EGFR', 'BCL2', 'MYC', 'TP53', 'PARP1', 'CHEK1', 'ATM'],
}

FDA_BRCA_APPROVED = {
    'Doxorubicin', 'Paclitaxel', 'Docetaxel', 'Carboplatin', 'Cisplatin',
    'Cyclophosphamide', 'Capecitabine', 'Gemcitabine', 'Vinorelbine',
    'Eribulin', 'Ixabepilone', 'Tamoxifen', 'Letrozole', 'Anastrozole',
    'Exemestane', 'Fulvestrant', 'Trastuzumab', 'Pertuzumab', 'Lapatinib',
    'Neratinib', 'Tucatinib', 'Palbociclib', 'Ribociclib', 'Abemaciclib',
    'Olaparib', 'Talazoparib', 'Alpelisib', 'Everolimus', 'Pembrolizumab',
    'Atezolizumab', 'Vinblastine', 'Epirubicin', 'Methotrexate',
    'Fluorouracil', 'Irinotecan', 'Topotecan', 'Mitoxantrone',
}

def standardize_name(name):
    """Standardize drug name"""
    if pd.isna(name):
        return ""
    return str(name).lower().replace(" ", "").replace("-", "").replace("_", "")

def match_target_with_aliases(target_str):
    """Match targets using comprehensive alias dictionary"""
    if pd.isna(target_str) or target_str == '' or target_str == 'Unknown':
        return set(), []

    target_upper = str(target_str).upper()
    matched_targets = set()
    matched_aliases = []

    # Check each canonical target and its aliases
    for canonical, aliases in TARGET_ALIASES.items():
        # Check canonical name
        if canonical.upper() in target_upper:
            matched_targets.add(canonical)
            matched_aliases.append(f"{canonical} (direct)")
            continue

        # Check all aliases
        for alias in aliases:
            if alias.upper() in target_upper:
                matched_targets.add(canonical)
                matched_aliases.append(f"{canonical} (via {alias})")
                break

    # Also check against direct target list
    for target in BRCA_TARGETS_30:
        if target.upper() in target_upper:
            matched_targets.add(target)
            if not any(target in a for a in matched_aliases):
                matched_aliases.append(f"{target} (direct)")

    return matched_targets, matched_aliases

def infer_subtype_enhanced(matched_targets):
    """Infer subtypes from matched targets"""
    if not matched_targets:
        return ['Unknown']

    subtypes = []
    for subtype, markers in SUBTYPE_TARGETS.items():
        if any(m in matched_targets for m in markers):
            subtypes.append(subtype)

    return subtypes if subtypes else ['Unknown']

def calculate_ndcg(y_true, y_pred, k):
    if len(y_true) < k:
        k = len(y_true)
    y_true = np.array(y_true).reshape(1, -1)
    y_pred = np.array(y_pred).reshape(1, -1)
    try:
        return ndcg_score(y_true, y_pred, k=k)
    except:
        return 0.0

def calculate_map(y_true, ranks):
    relevant_ranks = [i+1 for i, label in enumerate(y_true) if label == 1]
    if not relevant_ranks:
        return 0.0
    precisions = []
    for i, rank in enumerate(relevant_ranks):
        precision = (i + 1) / rank
        precisions.append(precision)
    return np.mean(precisions)

def main():
    print("="*100)
    print("FIXING STEP 6 ISSUES - PRIORITY ORDER")
    print("="*100)

    # Load existing results for comparison
    with open(OUTPUT_DIR / "step6_top30_full.json") as f:
        old_results = json.load(f)

    print("\n[BEFORE] Current Stats:")
    print(f"  Survival non-zero: {old_results['survival_non_zero']}")
    print(f"  Target non-zero: {old_results['target_non_zero']}")
    print(f"  Subtype coverage: {old_results['subtype_coverage']}")
    print(f"  Category 2 (연구중): {old_results['category_distribution'].get('Category 2: 유방암 연구 중', 0)}")

    # ========================================================================
    # PRIORITY 1-1: SURVIVAL MAPPING
    # ========================================================================
    print("\n" + "="*100)
    print("🔴 PRIORITY 1-1: Fixing Survival Mapping")
    print("="*100)

    print("\n[1] Checking survival data structure...")
    with open(INPUT_SURVIVAL) as f:
        survival_data = json.load(f)

    print(f"  Type: {type(survival_data)}")
    if isinstance(survival_data, dict):
        print(f"  Keys: {list(survival_data.keys())}")
        results_key = 'results' if 'results' in survival_data else list(survival_data.keys())[0]
        print(f"  Using key: {results_key}")
        print(f"  First entry: {survival_data[results_key][0] if survival_data[results_key] else 'empty'}")

    print("\n[2] Checking Top 30 drug_id format...")
    df_top30 = pd.read_csv(INPUT_TOP30)
    print(f"  Columns: {df_top30.columns.tolist()}")
    print(f"  First 3 rows:")
    print(df_top30[['drug_name', 'canonical_drug_id']].head(3))

    print("\n[3] Creating survival mapping with aliases...")
    survival_map = {}
    survival_map_log = []

    for entry in survival_data.get('results', []):
        drug_id = entry.get('canonical_drug_id')
        drug_name = entry.get('drug_name', '')
        p_value = entry.get('log_rank_p')

        if drug_id and p_value is not None:
            survival_map[drug_id] = p_value
            survival_map[str(drug_id)] = p_value
            survival_map_log.append(f"ID {drug_id}: p={p_value:.4f}")

        if drug_name and p_value is not None:
            survival_map[standardize_name(drug_name)] = p_value
            survival_map_log.append(f"Name '{drug_name}': p={p_value:.4f}")

    print(f"  ✓ Created {len(survival_map)} survival entries")

    # ========================================================================
    # PRIORITY 1-2: ADMET DATA LOADING
    # ========================================================================
    print("\n" + "="*100)
    print("🔴 PRIORITY 1-2: Loading ADMET Data")
    print("="*100)

    admet_map = {}
    admet_sources = [
        INPUT_ADMET1,
        INPUT_ADMET2,
    ]

    for admet_file in admet_sources:
        if admet_file.exists():
            print(f"\n  Loading {admet_file.name}...")
            with open(admet_file) as f:
                admet_data = json.load(f)

            for profile in admet_data.get('profiles', []):
                drug_name = profile.get('drug_name', '')
                drug_id = profile.get('drug_id')
                std_name = standardize_name(drug_name)

                if std_name and std_name not in admet_map:
                    admet_map[std_name] = profile
                    print(f"    + {drug_name}: safety_score={profile.get('safety_score', 0)}")

                if drug_id and str(drug_id) not in admet_map:
                    admet_map[str(drug_id)] = profile

    print(f"\n  ✓ Loaded {len(admet_map)} ADMET profiles")

    # ========================================================================
    # RELOAD AND REPROCESS
    # ========================================================================
    print("\n" + "="*100)
    print("REPROCESSING WITH FIXES")
    print("="*100)

    # Load H3 and FDA SMILES
    df_h3 = pd.read_csv(INPUT_H3)
    h3_map = {}
    for _, row in df_h3.iterrows():
        drug = row['약물명']
        h3_map[standardize_name(drug)] = {
            'tanimoto': row['Tanimoto'],
            'best_fda': row['가장_유사한_FDA약']
        }

    with open(INPUT_FDA_SMILES) as f:
        fda_smiles = json.load(f)

    # Process each drug
    results = []
    survival_matched = 0
    target_matched = 0
    admet_matched = 0

    for idx, row in df_top30.iterrows():
        drug_id = row.get('canonical_drug_id')
        drug_name = row['drug_name']
        ic50_mean = row['mean_pred_ic50']
        ic50_std = row.get('std_pred_ic50', 0)
        target = row.get('target', '')
        pathway = row.get('pathway', 'Unknown')

        std_name = standardize_name(drug_name)

        print(f"\n  [{idx+1}/30] {drug_name}...")

        # Survival - FIXED
        p_value = survival_map.get(drug_id, survival_map.get(str(drug_id), survival_map.get(std_name, 1.0)))
        survival_score = -np.log10(p_value) if p_value < 0.05 else 0
        if survival_score > 0:
            survival_matched += 1
            print(f"    ✓ Survival: p={p_value:.4f}, score={survival_score:.4f}")

        # Target matching - FIXED
        matched_targets, matched_aliases = match_target_with_aliases(target)
        target_score = len(matched_targets) / 30.0
        if target_score > 0:
            target_matched += 1
            print(f"    ✓ Targets: {list(matched_targets)} ({target_score:.4f})")

        # Subtype - FIXED
        subtypes = infer_subtype_enhanced(matched_targets)
        print(f"    ✓ Subtypes: {subtypes}")

        # H3 Tanimoto
        h3_data = h3_map.get(std_name, {})
        tanimoto = h3_data.get('tanimoto', 0)
        best_fda = h3_data.get('best_fda', '')

        # Clinical category - FIXED (use FDA list directly)
        if drug_name in FDA_BRCA_APPROVED:
            category = "Category 1: 유방암 치료제 (FDA 승인)"
            clinical_score = 1.0
        elif tanimoto > 0.1:  # Has some similarity to FDA drugs
            category = "Category 2: 유방암 연구 중"
            clinical_score = 0.5
        else:
            category = "Category 3: 유방암 미적용"
            clinical_score = 0.0

        # ADMET - FIXED
        admet_profile = admet_map.get(std_name, admet_map.get(str(drug_id), {}))
        safety_score = admet_profile.get('safety_score', 0) if admet_profile else 0
        if safety_score > 0:
            admet_matched += 1
            print(f"    ✓ ADMET: safety_score={safety_score}")

        # IC50 grading
        if ic50_mean < 1.0:
            ic50_grade = 'High'
        elif ic50_mean <= 3.0:
            ic50_grade = 'Medium'
        else:
            ic50_grade = 'Low'

        ic50_ci_lower = ic50_mean - 1.96 * ic50_std
        ic50_ci_upper = ic50_mean + 1.96 * ic50_std

        results.append({
            'rank': idx + 1,
            'drug_id': drug_id,
            'drug_name': drug_name,
            'ic50_mean': ic50_mean,
            'ic50_std': ic50_std,
            'ic50_ci_lower': ic50_ci_lower,
            'ic50_ci_upper': ic50_ci_upper,
            'ic50_grade': ic50_grade,
            'tanimoto': tanimoto,
            'best_fda_match': best_fda,
            'target': target,
            'target_matches': ', '.join(matched_targets) if matched_targets else 'None',
            'target_score': target_score,
            'survival_p': p_value,
            'survival_score': survival_score,
            'clinical_score': clinical_score,
            'category': category,
            'pathway': pathway,
            'subtypes': ', '.join(subtypes),
            'safety_score': safety_score,
        })

    df_step6 = pd.DataFrame(results)

    # Normalize scores
    ic50_min = df_step6['ic50_mean'].min()
    ic50_max = df_step6['ic50_mean'].max()
    df_step6['ic50_score'] = 1 - (df_step6['ic50_mean'] - ic50_min) / (ic50_max - ic50_min) if ic50_max > ic50_min else 0.5

    surv_max = df_step6['survival_score'].max()
    df_step6['survival_score_norm'] = df_step6['survival_score'] / surv_max if surv_max > 0 else 0

    df_step6['tanimoto_score'] = df_step6['tanimoto']

    # Final score
    df_step6['final_score'] = (
        0.30 * df_step6['ic50_score'] +
        0.20 * df_step6['survival_score_norm'] +
        0.20 * df_step6['tanimoto_score'] +
        0.20 * df_step6['target_score'] +
        0.10 * df_step6['clinical_score']
    )

    # Remove duplicates
    df_step6 = df_step6.sort_values('final_score', ascending=False).drop_duplicates('drug_name', keep='first')

    # Calculate new statistics
    subtype_coverage = {}
    for st in ['ER+', 'HER2+', 'TNBC']:
        count = df_step6['subtypes'].str.contains(st, na=False).sum()
        subtype_coverage[st] = int(count)

    # Save updated Step 6
    df_step6.to_csv(OUTPUT_DIR / "step6_top30_full.csv", index=False, encoding='utf-8-sig')

    new_results = {
        'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        'n_drugs': len(df_step6),
        'final_score_stats': {
            'max': float(df_step6['final_score'].max()),
            'min': float(df_step6['final_score'].min()),
            'mean': float(df_step6['final_score'].mean()),
        },
        'survival_non_zero': int((df_step6['survival_score'] > 0).sum()),
        'target_non_zero': int((df_step6['target_score'] > 0).sum()),
        'category_distribution': df_step6['category'].value_counts().to_dict(),
        'moa_distribution': {str(k): int(v) for k, v in df_step6['pathway'].value_counts().to_dict().items()},
        'unique_pathways': int(df_step6['pathway'].nunique()),
        'subtype_coverage': subtype_coverage,
    }

    with open(OUTPUT_DIR / "step6_top30_full.json", 'w', encoding='utf-8') as f:
        json.dump(new_results, f, indent=2, ensure_ascii=False)

    # ========================================================================
    # STEP 6A, 6B, 6C - RECALCULATE
    # ========================================================================
    print("\n" + "="*100)
    print("RECALCULATING VALIDATION & TOP 15")
    print("="*100)

    # Step 6A
    df_step6['is_fda'] = df_step6['drug_name'].apply(lambda x: 1 if x in FDA_BRCA_APPROVED else 0)
    df_ranked = df_step6.sort_values('final_score', ascending=False).reset_index(drop=True)

    n_fda = df_ranked['is_fda'].sum()
    fda_drugs = df_ranked[df_ranked['is_fda'] == 1]
    median_rank = float(fda_drugs.index.to_series().median() + 1) if len(fda_drugs) > 0 else 30

    y_true = df_ranked['is_fda'].values
    y_pred = df_ranked['final_score'].values

    recalls = {}
    precisions = {}
    ndcgs = {}

    for k in [10, 20, 30]:
        top_k = df_ranked.head(k)
        n_fda_k = top_k['is_fda'].sum()
        recalls[f'recall@{k}'] = float(n_fda_k / n_fda) if n_fda > 0 else 0
        precisions[f'precision@{k}'] = float(n_fda_k / k)
        ndcgs[f'ndcg@{k}'] = calculate_ndcg(y_true[:k], y_pred[:k], k)

    map_score = calculate_map(y_true, list(range(1, len(y_true) + 1)))
    try:
        auc_roc = roc_auc_score(y_true, y_pred)
    except:
        auc_roc = 0.5

    validation_report = {
        'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        'n_fda_in_top30': int(n_fda),
        'fda_drugs_list': list(fda_drugs['drug_name'].astype(str)),
        'median_rank': float(median_rank),
        'recall': {k: float(v) for k, v in recalls.items()},
        'precision': {k: float(v) for k, v in precisions.items()},
        'ndcg': {k: float(v) for k, v in ndcgs.items()},
        'mean_average_precision': float(map_score),
        'auc_roc': float(auc_roc),
    }

    with open(OUTPUT_DIR / "step6a_validation.json", 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    # Step 6B
    df_approved = df_ranked[df_ranked['is_fda'] == 1].head(2)
    df_repurposing = df_ranked[df_ranked['is_fda'] == 0]
    df_top15 = pd.concat([df_approved, df_repurposing.head(13)]).sort_values('final_score', ascending=False).reset_index(drop=True)
    df_top15.insert(0, 'repurposing_rank', range(1, len(df_top15) + 1))

    df_top15.to_csv(OUTPUT_DIR / "step6b_repurposing_top15.csv", index=False, encoding='utf-8-sig')

    # Step 7
    admet_results = []
    for _, row in df_top15.iterrows():
        drug_name = row['drug_name']
        safety_score = row['safety_score']

        if safety_score >= 6:
            verdict = 'PASS'
        elif safety_score >= 4:
            verdict = 'WARNING'
        else:
            verdict = 'FAIL'

        admet_results.append({
            'repurposing_rank': row['repurposing_rank'],
            'drug_name': drug_name,
            'safety_score': safety_score,
            'verdict': verdict,
        })

    df_admet = pd.DataFrame(admet_results)
    df_admet.to_csv(OUTPUT_DIR / "step7_admet_final.csv", index=False, encoding='utf-8-sig')

    # ========================================================================
    # BEFORE/AFTER COMPARISON
    # ========================================================================
    print("\n" + "="*100)
    print("BEFORE/AFTER COMPARISON")
    print("="*100)

    comparison = pd.DataFrame([
        {
            '항목': 'Survival 매핑',
            '수정 전': f"{old_results['survival_non_zero']}개",
            '수정 후': f"{new_results['survival_non_zero']}개",
            '개선': f"+{new_results['survival_non_zero'] - old_results['survival_non_zero']}"
        },
        {
            '항목': 'Target 매칭',
            '수정 전': f"{old_results['target_non_zero']}개",
            '수정 후': f"{new_results['target_non_zero']}개",
            '개선': f"+{new_results['target_non_zero'] - old_results['target_non_zero']}"
        },
        {
            '항목': 'Subtype ER+',
            '수정 전': old_results['subtype_coverage']['ER+'],
            '수정 후': subtype_coverage['ER+'],
            '개선': f"+{subtype_coverage['ER+'] - old_results['subtype_coverage']['ER+']}"
        },
        {
            '항목': 'Subtype HER2+',
            '수정 전': old_results['subtype_coverage']['HER2+'],
            '수정 후': subtype_coverage['HER2+'],
            '개선': f"+{subtype_coverage['HER2+'] - old_results['subtype_coverage']['HER2+']}"
        },
        {
            '항목': 'Subtype TNBC',
            '수정 전': old_results['subtype_coverage']['TNBC'],
            '수정 후': subtype_coverage['TNBC'],
            '개선': f"+{subtype_coverage['TNBC'] - old_results['subtype_coverage']['TNBC']}"
        },
        {
            '항목': 'ADMET 매핑',
            '수정 전': '1개',
            '수정 후': f"{admet_matched}개",
            '개선': f"+{admet_matched - 1}"
        },
        {
            '항목': 'Category 2 (연구중)',
            '수정 전': f"{old_results['category_distribution'].get('Category 2: 유방암 연구 중', 0)}개",
            '수정 후': f"{new_results['category_distribution'].get('Category 2: 유방암 연구 중', 0)}개",
            '개선': f"+{new_results['category_distribution'].get('Category 2: 유방암 연구 중', 0) - old_results['category_distribution'].get('Category 2: 유방암 연구 중', 0)}"
        },
    ])

    print("\n" + comparison.to_string(index=False))

    comparison.to_csv(OUTPUT_DIR / "before_after_comparison.csv", index=False, encoding='utf-8-sig')

    print("\n" + "="*100)
    print("✅ ALL FIXES COMPLETE")
    print("="*100)
    print(f"\nFiles updated in: {OUTPUT_DIR}")
    print(f"\nKey improvements:")
    print(f"  - Survival mapping: +{new_results['survival_non_zero'] - old_results['survival_non_zero']}")
    print(f"  - Target matching: +{new_results['target_non_zero'] - old_results['target_non_zero']}")
    print(f"  - Subtype coverage: ER+={subtype_coverage['ER+']}, HER2+={subtype_coverage['HER2+']}, TNBC={subtype_coverage['TNBC']}")
    print(f"  - ADMET mapping: {admet_matched} drugs")
    print("="*100)

if __name__ == "__main__":
    main()
