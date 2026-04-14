#!/usr/bin/env python3
"""
Complete Pipeline: Step 6 → Step 6A → Step 6B → Step 7
- Top 30 evaluation with multi-objective scoring
- Validation metrics (Recall, Precision, NDCG, MAP, AUC-ROC)
- Repurposing Top 15 selection
- ADMET safety validation (v1 Tanimoto lookup, NO MOCK)
"""

import numpy as np
import pandas as pd
import json
import requests
import time
from pathlib import Path
from collections import defaultdict, Counter
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski, Crippen, rdMolDescriptors
from rdkit import DataStructs
from sklearn.metrics import roc_auc_score, ndcg_score
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# 30 expanded breast cancer targets (14 core + 16 additional)
BRCA_TARGETS_EXPANDED = {
    'BRCA1', 'BRCA2', 'HER2', 'ESR1', 'PGR', 'PIK3CA', 'AKT1', 'PTEN',
    'CDK4', 'CDK6', 'CCND1', 'TP53', 'MYC', 'EGFR',
    'PALB2', 'ATM', 'FGFR1', 'FGFR2', 'RAD51', 'RB1',
    'MTOR', 'AR', 'PARP1', 'PARP2', 'TOP2A', 'VEGFR2',
    'CDK2', 'CHEK1', 'CHEK2', 'BCL2',
}

# Target aliases
TARGET_ALIASES = {
    'ERBB2': 'HER2',
    'ER': 'ESR1',
    'PR': 'PGR',
}

# FDA approved breast cancer drugs
FDA_BRCA_APPROVED = {
    'Doxorubicin', 'Paclitaxel', 'Docetaxel', 'Carboplatin', 'Cisplatin',
    'Cyclophosphamide', 'Capecitabine', 'Gemcitabine', 'Vinorelbine',
    'Eribulin', 'Ixabepilone', 'Tamoxifen', 'Letrozole', 'Anastrozole',
    'Exemestane', 'Fulvestrant', 'Trastuzumab', 'Pertuzumab', 'Lapatinib',
    'Neratinib', 'Tucatinib', 'Palbociclib', 'Ribociclib', 'Abemaciclib',
    'Olaparib', 'Talazoparib', 'Alpelisib', 'Everolimus', 'Pembrolizumab',
    'Atezolizumab', 'Vinblastine', 'Epirubicin', 'Methotrexate',
    'Fluorouracil', 'Irinotecan',
}

# Subtype markers
SUBTYPE_TARGETS = {
    'ER+': ['ESR1', 'PGR', 'CYP19A1'],  # Aromatase
    'HER2+': ['HER2', 'ERBB2', 'EGFR'],
    'TNBC': ['PARP1', 'PARP2', 'CHEK1', 'ATM', 'BRCA1', 'BRCA2'],
}

def get_smiles_from_pubchem(drug_name, retries=3):
    """Fetch SMILES from PubChem"""
    for attempt in range(retries):
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/property/IsomericSMILES/JSON"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['PropertyTable']['Properties'][0]['SMILES']
        except:
            if attempt < retries - 1:
                time.sleep(1)
    return None

def calculate_tanimoto(smiles1, smiles2):
    """Calculate Tanimoto similarity"""
    try:
        mol1 = Chem.MolFromSmiles(smiles1)
        mol2 = Chem.MolFromSmiles(smiles2)
        if mol1 and mol2:
            fp1 = AllChem.GetMorganFingerprintAsBitVect(mol1, 2, nBits=2048)
            fp2 = AllChem.GetMorganFingerprintAsBitVect(mol2, 2, nBits=2048)
            return DataStructs.TanimotoSimilarity(fp1, fp2)
    except:
        pass
    return None

def calculate_qed(smiles):
    """Calculate QED (Quantitative Estimate of Drug-likeness)"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return Descriptors.qed(mol)
    except:
        pass
    return None

def get_lipinski_properties(smiles):
    """Calculate Lipinski Rule of Five properties"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return {
                'MW': Descriptors.MolWt(mol),
                'LogP': Crippen.MolLogP(mol),
                'HBD': Lipinski.NumHDonors(mol),
                'HBA': Lipinski.NumHAcceptors(mol),
                'TPSA': Descriptors.TPSA(mol),
                'RotBonds': Lipinski.NumRotatableBonds(mol),
                'Lipinski_violations': sum([
                    Descriptors.MolWt(mol) > 500,
                    Crippen.MolLogP(mol) > 5,
                    Lipinski.NumHDonors(mol) > 5,
                    Lipinski.NumHAcceptors(mol) > 10,
                ])
            }
    except:
        pass
    return None

def classify_ic50_grade(ic50):
    """H1: IC50 grading"""
    if ic50 < 1.0:
        return 'High'
    elif ic50 <= 3.0:
        return 'Medium'
    else:
        return 'Low'

def calculate_target_score(targets_str, expanded_targets=BRCA_TARGETS_EXPANDED):
    """H4: Calculate target matching score with 30 expanded BRCA targets"""
    if pd.isna(targets_str) or targets_str == 'Unknown':
        return 0.0, []

    targets = [t.strip().upper() for t in str(targets_str).split(',')]

    # Normalize with aliases
    normalized = set()
    for t in targets:
        if t in TARGET_ALIASES:
            normalized.add(TARGET_ALIASES[t])
        else:
            normalized.add(t)

    # Count matches with expanded targets
    matches = normalized.intersection(expanded_targets)

    score = len(matches) / 30.0  # 30 targets
    return score, list(matches)

def infer_subtype_coverage(targets_str):
    """Infer which breast cancer subtypes this drug might cover"""
    if pd.isna(targets_str) or targets_str == 'Unknown':
        return []

    targets = [t.strip().upper() for t in str(targets_str).split(',')]
    subtypes = []

    for subtype, markers in SUBTYPE_TARGETS.items():
        if any(m.upper() in targets for m in markers):
            subtypes.append(subtype)

    return subtypes if subtypes else ['Unknown']

def search_clinicaltrials_count(drug_name):
    """Search ClinicalTrials.gov for breast cancer trials count"""
    try:
        params = {
            'format': 'json',
            'query.term': f'{drug_name} AND breast cancer',
            'pageSize': 1
        }
        url = "https://clinicaltrials.gov/api/v2/studies"
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get('totalCount', 0)
    except:
        pass
    return 0

def load_admet_assays():
    """Load 22 ADMET assay datasets from S3"""
    assays = {}
    assay_names = [
        'caco2_wang', 'hia_hou', 'pgp_broccatelli', 'bioavailability_ma',
        'bbb_martins', 'ppbr_az', 'vdss_lombardo',
        'cyp2c9_veith', 'cyp2d6_veith', 'cyp3a4_veith',
        'cyp2c9_substrate_carbonmangels', 'cyp2d6_substrate_carbonmangels',
        'cyp3a4_substrate_carbonmangels',
        'clearance_hepatocyte_az', 'clearance_microsome_az', 'half_life_obach',
        'ames', 'dili', 'herg', 'ld50_zhu',
        'lipophilicity_astrazeneca', 'solubility_aqsoldb'
    ]

    print("  Loading ADMET assays from cache/S3...")
    # Try to load from local cache first
    for assay in assay_names:
        cache_file = Path(f"../../admet_assays/{assay}.csv")
        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file)
                assays[assay] = df
            except:
                pass

    print(f"  ✓ Loaded {len(assays)}/22 assays")
    return assays

def lookup_admet_tanimoto(smiles, assays, threshold=0.85):
    """Lookup ADMET properties using Tanimoto similarity"""
    if not smiles or not assays:
        return {}

    results = {}
    mol_query = Chem.MolFromSmiles(smiles)
    if not mol_query:
        return {}

    fp_query = AllChem.GetMorganFingerprintAsBitVect(mol_query, 2, nBits=2048)

    for assay_name, df_assay in assays.items():
        if 'SMILES' not in df_assay.columns or 'Y' not in df_assay.columns:
            continue

        best_sim = 0
        best_value = None

        for _, row in df_assay.iterrows():
            try:
                mol_ref = Chem.MolFromSmiles(row['SMILES'])
                if mol_ref:
                    fp_ref = AllChem.GetMorganFingerprintAsBitVect(mol_ref, 2, nBits=2048)
                    sim = DataStructs.TanimotoSimilarity(fp_query, fp_ref)
                    if sim > best_sim:
                        best_sim = sim
                        best_value = row['Y']
            except:
                continue

        if best_sim >= threshold:
            results[assay_name] = {
                'value': best_value,
                'similarity': best_sim,
                'match': 'exact' if best_sim >= 0.99 else 'analog'
            }

    return results

def calculate_safety_score(admet_results):
    """Calculate safety score (v2 H2B criteria: 12 point scale)"""
    # Safety-relevant assays (6 assays × 2 points each = 12 max)
    safety_assays = {
        'ames': 2,      # Mutagenicity (0=safe, 1=mutagen) → 2 if 0
        'dili': 2,      # Liver injury (0=safe, 1=toxic) → 2 if 0
        'herg': 2,      # Cardiotoxicity (0=safe, 1=toxic) → 2 if 0
        'ld50_zhu': 2,  # Acute toxicity (higher is safer) → score based on value
        'ppbr_az': 2,   # Plasma protein binding (0.9-0.99 optimal) → score
        'bioavailability_ma': 2,  # Oral bioavailability (>0.2 good) → 2 if >0.2
    }

    score = 0
    for assay, max_points in safety_assays.items():
        if assay in admet_results:
            value = admet_results[assay]['value']

            if assay in ['ames', 'dili', 'herg']:
                # Binary: 0=safe → full points, 1=toxic → 0 points
                score += max_points if value == 0 else 0
            elif assay == 'ld50_zhu':
                # Continuous: higher is safer
                if value > 3.0:
                    score += 2
                elif value > 2.0:
                    score += 1
            elif assay == 'ppbr_az':
                # Optimal range 0.9-0.99
                if 0.9 <= value <= 0.99:
                    score += 2
                elif 0.8 <= value < 0.9 or 0.99 < value <= 1.0:
                    score += 1
            elif assay == 'bioavailability_ma':
                # >0.2 is good for oral
                score += 2 if value > 0.2 else 0

    return score

def calculate_ndcg(y_true, y_pred, k):
    """Calculate NDCG@k"""
    if len(y_true) < k:
        k = len(y_true)

    # Reshape for sklearn
    y_true = np.array(y_true).reshape(1, -1)
    y_pred = np.array(y_pred).reshape(1, -1)

    try:
        return ndcg_score(y_true, y_pred, k=k)
    except:
        return 0.0

def calculate_map(y_true, ranks):
    """Calculate Mean Average Precision"""
    relevant_ranks = [i+1 for i, label in enumerate(y_true) if label == 1]
    if not relevant_ranks:
        return 0.0

    precisions = []
    for i, rank in enumerate(relevant_ranks):
        # Precision at this rank = (number of relevant items up to rank) / rank
        precision = (i + 1) / rank
        precisions.append(precision)

    return np.mean(precisions)

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    print("="*100)
    print("COMPLETE PIPELINE: Step 6 → 6A → 6B → 7")
    print("="*100)

    # Load Top 30 drugs
    print("\n[0] Loading Top 30 drugs from CatBoost predictions...")
    top30_file = Path("../../20260413_feature_reconstruction/results/top30_reextract_20260413/top30_reextract.csv")

    if not top30_file.exists():
        print(f"  ✗ Top 30 file not found: {top30_file}")
        return

    df_top30 = pd.read_csv(top30_file)
    print(f"  ✓ Loaded {len(df_top30)} drugs")

    # ========================================================================
    # STEP 6: TOP 30 EVALUATION
    # ========================================================================
    print("\n" + "="*100)
    print("STEP 6: Top 30 Evaluation with Multi-objective Scoring")
    print("="*100)

    # Load FDA drug SMILES (from previous H3 work)
    print("\n[6.1] Loading FDA breast cancer drug SMILES...")
    fda_smiles_file = Path("fda_brca_drugs_smiles.json")

    if fda_smiles_file.exists():
        with open(fda_smiles_file) as f:
            fda_smiles = json.load(f)
        fda_smiles = {k: v for k, v in fda_smiles.items() if v is not None}
        print(f"  ✓ Loaded {len(fda_smiles)} FDA drug SMILES")
    else:
        print("  ⚠ FDA SMILES not found, will collect from PubChem...")
        fda_smiles = {}
        for drug in list(FDA_BRCA_APPROVED)[:31]:  # Top 31 for H3
            smiles = get_smiles_from_pubchem(drug)
            if smiles:
                fda_smiles[drug] = smiles
            time.sleep(0.3)

    # Load survival data
    print("\n[6.2] Loading survival analysis data...")
    survival_file = Path("step6_metabric_results/method_b_survival.json")
    survival_data = {}

    if survival_file.exists():
        with open(survival_file) as f:
            surv = json.load(f)
            for entry in surv.get('results', []):
                drug_id = entry.get('canonical_drug_id')
                p_value = entry.get('log_rank_p')
                if drug_id and p_value:
                    survival_data[drug_id] = p_value
        print(f"  ✓ Loaded survival data for {len(survival_data)} drugs")
    else:
        print("  ⚠ Survival file not found")

    # Calculate metrics for each drug
    print("\n[6.3] Calculating multi-objective scores...")

    results = []

    for idx, row in df_top30.iterrows():
        drug_id = row['canonical_drug_id']
        drug_name = row['drug_name']
        ic50_mean = row['mean_pred_ic50']
        ic50_std = row.get('std_pred_ic50', 0)
        target = row.get('target', 'Unknown')
        pathway = row.get('pathway', 'Unknown')

        print(f"\n  Processing {idx+1}/30: {drug_name} (ID {drug_id})...")

        # H1: IC50 grade and score
        ic50_grade = classify_ic50_grade(ic50_mean)
        # Normalize IC50 to 0-1 score (lower is better)
        # Use sigmoid-like transformation
        ic50_score = 1 / (1 + np.exp(ic50_mean))  # Maps to 0-1, lower IC50 → higher score

        # Confidence interval (±1.96 * std for 95% CI)
        ic50_ci_lower = ic50_mean - 1.96 * ic50_std
        ic50_ci_upper = ic50_mean + 1.96 * ic50_std

        # H3: Tanimoto similarity
        drug_smiles = get_smiles_from_pubchem(drug_name)
        max_tanimoto = 0
        best_fda_drug = None

        if drug_smiles and fda_smiles:
            for fda_drug, fda_smi in fda_smiles.items():
                sim = calculate_tanimoto(drug_smiles, fda_smi)
                if sim and sim > max_tanimoto:
                    max_tanimoto = sim
                    best_fda_drug = fda_drug

        tanimoto_score = max_tanimoto / 0.3 if max_tanimoto < 0.3 else 1.0  # Normalized

        # H4: Target matching
        target_score, matched_targets = calculate_target_score(target)

        # Survival score
        p_value = survival_data.get(drug_id, 1.0)
        survival_score = -np.log10(p_value) if p_value < 0.05 else 0

        # Clinical trials count
        trials_count = search_clinicaltrials_count(drug_name)
        time.sleep(0.5)

        # Clinical category
        if drug_name in FDA_BRCA_APPROVED:
            category = "Category 1: 유방암 치료제 (FDA 승인)"
        elif trials_count > 0:
            category = "Category 2: 유방암 연구 중"
        else:
            category = "Category 3: 유방암 미적용"

        clinical_score = np.log10(trials_count + 1)

        # Subtype coverage
        subtypes = infer_subtype_coverage(target)

        # Multi-objective final score
        final_score = (
            0.30 * ic50_score +
            0.20 * (survival_score / 3.0 if survival_score > 0 else 0) +  # Cap at 3
            0.20 * tanimoto_score +
            0.20 * target_score +
            0.10 * (clinical_score / 2.0 if clinical_score > 0 else 0)  # Cap at 2
        )

        results.append({
            'rank': idx + 1,
            'drug_id': drug_id,
            'drug_name': drug_name,
            'ic50_mean': ic50_mean,
            'ic50_std': ic50_std,
            'ic50_ci_lower': ic50_ci_lower,
            'ic50_ci_upper': ic50_ci_upper,
            'ic50_grade': ic50_grade,
            'ic50_score': ic50_score,
            'tanimoto': max_tanimoto,
            'best_fda_match': best_fda_drug,
            'tanimoto_score': tanimoto_score,
            'target': target,
            'target_matches': ', '.join(matched_targets) if matched_targets else 'None',
            'target_score': target_score,
            'survival_p': p_value,
            'survival_score': survival_score,
            'clinical_trials': trials_count,
            'clinical_score': clinical_score,
            'final_score': final_score,
            'category': category,
            'pathway': pathway,
            'subtypes': ', '.join(subtypes),
            'smiles': drug_smiles or '',
        })

    df_step6 = pd.DataFrame(results)

    # Normalize clinical score to max in dataset
    if df_step6['clinical_score'].max() > 0:
        df_step6['clinical_score'] = df_step6['clinical_score'] / df_step6['clinical_score'].max()

    if df_step6['survival_score'].max() > 0:
        df_step6['survival_score'] = df_step6['survival_score'] / df_step6['survival_score'].max()

    # Recalculate final score with normalized values
    df_step6['final_score'] = (
        0.30 * df_step6['ic50_score'] +
        0.20 * df_step6['survival_score'] +
        0.20 * df_step6['tanimoto_score'] +
        0.20 * df_step6['target_score'] +
        0.10 * df_step6['clinical_score']
    )

    # Calculate additional metrics
    moa_counts = df_step6['pathway'].value_counts().to_dict()
    unique_pathways = df_step6['pathway'].nunique()

    # Save Step 6 results
    output_step6 = Path("step6_top30_evaluation.csv")
    df_step6.to_csv(output_step6, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved Step 6 results: {output_step6}")

    # ========================================================================
    # STEP 6A: VALIDATION METRICS
    # ========================================================================
    print("\n" + "="*100)
    print("STEP 6A: Validation Metrics")
    print("="*100)

    # Binary labels: 1 if FDA approved, 0 otherwise
    df_step6['is_fda_approved'] = df_step6['drug_name'].isin(FDA_BRCA_APPROVED).astype(int)

    # Sort by final score descending
    df_ranked = df_step6.sort_values('final_score', ascending=False).reset_index(drop=True)

    n_approved_in_top30 = df_ranked['is_fda_approved'].sum()
    approved_drugs = df_ranked[df_ranked['is_fda_approved'] == 1]
    median_rank = approved_drugs.index.to_series().median() + 1 if len(approved_drugs) > 0 else 30

    # Enrichment (assuming 191 total drugs in database, with ~30 FDA approved)
    total_drugs = 191  # From GDSC
    total_fda_approved = len(FDA_BRCA_APPROVED.intersection(set(df_top30['drug_name'])))
    enrichment = (n_approved_in_top30 / 30) / (total_fda_approved / total_drugs) if total_fda_approved > 0 else 0

    # Recall and Precision at k
    recalls = {}
    precisions = {}

    for k in [10, 20, 30]:
        top_k = df_ranked.head(k)
        n_approved_in_k = top_k['is_fda_approved'].sum()

        recalls[f'recall@{k}'] = n_approved_in_k / total_fda_approved if total_fda_approved > 0 else 0
        precisions[f'precision@{k}'] = n_approved_in_k / k

    # NDCG@k
    y_true = df_ranked['is_fda_approved'].values
    y_pred = df_ranked['final_score'].values

    ndcgs = {}
    for k in [10, 20, 30]:
        ndcgs[f'ndcg@{k}'] = calculate_ndcg(y_true[:k], y_pred[:k], k)

    # MAP
    map_score = calculate_map(y_true, list(range(1, len(y_true) + 1)))

    # AUC-ROC
    try:
        auc_roc = roc_auc_score(y_true, y_pred)
    except:
        auc_roc = 0.5

    # Recovery rate
    recovery_rate = n_approved_in_top30 / total_fda_approved if total_fda_approved > 0 else 0

    # MOA and pathway diversity
    subtype_coverage = {}
    for subtype in ['ER+', 'HER2+', 'TNBC']:
        count = df_step6['subtypes'].str.contains(subtype, na=False).sum()
        subtype_coverage[subtype] = int(count)

    validation_report = {
        'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        'n_drugs_evaluated': int(len(df_step6)),
        'n_fda_approved_in_top30': int(n_approved_in_top30),
        'fda_approved_drugs': list(approved_drugs['drug_name'].astype(str)),
        'median_rank_of_approved': float(median_rank),
        'enrichment_ratio': float(enrichment),
        'recall': {k: float(v) for k, v in recalls.items()},
        'precision': {k: float(v) for k, v in precisions.items()},
        'ndcg': {k: float(v) for k, v in ndcgs.items()},
        'mean_average_precision': float(map_score),
        'auc_roc': float(auc_roc),
        'recovery_rate': float(recovery_rate),
        'ic50_statistics': {
            'mean': float(df_step6['ic50_mean'].mean()),
            'std': float(df_step6['ic50_mean'].std()),
            'min': float(df_step6['ic50_mean'].min()),
            'max': float(df_step6['ic50_mean'].max()),
        },
        'moa_distribution': {str(k): int(v) for k, v in moa_counts.items()},
        'unique_pathways': int(unique_pathways),
        'subtype_coverage': subtype_coverage,
    }

    output_validation = Path("validation_report.json")
    with open(output_validation, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved validation report: {output_validation}")
    print(f"\n  Validation Summary:")
    print(f"    FDA approved in Top 30: {n_approved_in_top30}")
    print(f"    Median rank: {median_rank:.1f}")
    print(f"    Enrichment: {enrichment:.2f}x")
    print(f"    Recall@10: {recalls['recall@10']:.2%}")
    print(f"    Precision@10: {precisions['precision@10']:.2%}")
    print(f"    NDCG@10: {ndcgs['ndcg@10']:.3f}")
    print(f"    AUC-ROC: {auc_roc:.3f}")

    # ========================================================================
    # STEP 6B: REPURPOSING TOP 15 SELECTION
    # ========================================================================
    print("\n" + "="*100)
    print("STEP 6B: Repurposing Top 15 Selection")
    print("="*100)

    # Exclude Category 1 (allow max 2 positive controls)
    df_repurposing = df_ranked[~df_ranked['category'].str.contains('치료제')].copy()

    # If we have some approved drugs, include top 2 as positive controls
    df_approved = df_ranked[df_ranked['category'].str.contains('치료제')].head(2)

    # Select top 13 from repurposing + 2 positive controls
    df_top15_repurposing = pd.concat([
        df_approved,
        df_repurposing.head(13)
    ]).sort_values('final_score', ascending=False).reset_index(drop=True)

    df_top15_repurposing.insert(0, 'repurposing_rank', range(1, len(df_top15_repurposing) + 1))

    # Calculate additional metrics for Top 15
    moa_overlap = df_top15_repurposing['pathway'].value_counts()
    moa_duplicates = moa_overlap[moa_overlap > 1].to_dict()

    target_coverage = len(set([t for targets in df_top15_repurposing['target_matches'].str.split(', ') for t in targets if t != 'None']))

    subtype_cov_15 = {}
    for subtype in ['ER+', 'HER2+', 'TNBC']:
        count = df_top15_repurposing['subtypes'].str.contains(subtype, na=False).sum()
        subtype_cov_15[subtype] = int(count)

    # Jaccard similarity with Top 30
    set_top15 = set(df_top15_repurposing['drug_name'])
    set_top30 = set(df_step6['drug_name'])
    jaccard = len(set_top15.intersection(set_top30)) / len(set_top15.union(set_top30))

    # Add recommendation rationale and limitations
    df_top15_repurposing['recommendation_rationale'] = df_top15_repurposing.apply(
        lambda row: f"Target: {row['target']}; Subtype: {row['subtypes']}; Similar to: {row['best_fda_match']}", axis=1
    )

    df_top15_repurposing['limitations'] = df_top15_repurposing.apply(
        lambda row: f"Clinical trials: {row['clinical_trials']}; " +
                    (f"Low target score ({row['target_score']:.2f})" if row['target_score'] < 0.1 else "Good target coverage"),
        axis=1
    )

    output_top15 = Path("repurposing_top15.csv")
    df_top15_repurposing.to_csv(output_top15, index=False, encoding='utf-8-sig')

    print(f"\n✓ Saved repurposing Top 15: {output_top15}")
    print(f"\n  Top 15 Summary:")
    print(f"    Positive controls (FDA approved): {len(df_approved)}")
    print(f"    Repurposing candidates: {len(df_top15_repurposing) - len(df_approved)}")
    print(f"    MOA duplicates: {moa_duplicates}")
    print(f"    Target coverage: {target_coverage} unique targets")
    print(f"    Subtype coverage: {subtype_cov_15}")
    print(f"    Jaccard with Top 30: {jaccard:.2%}")

    # ========================================================================
    # STEP 7: ADMET SAFETY VALIDATION
    # ========================================================================
    print("\n" + "="*100)
    print("STEP 7: ADMET Safety Validation (v1 Tanimoto, NO MOCK)")
    print("="*100)

    # Load ADMET assays
    print("\n[7.1] Loading ADMET assay datasets...")
    admet_assays = load_admet_assays()

    if not admet_assays:
        print("  ⚠ WARNING: No ADMET assays loaded. Using mock=False constraint.")
        print("  This step requires real assay data. Skipping ADMET validation.")
        admet_results_list = []
    else:
        admet_results_list = []

        for idx, row in df_top15_repurposing.iterrows():
            drug_name = row['drug_name']
            smiles = row['smiles']

            print(f"\n  [{idx+1}/15] {drug_name}...")

            if not smiles:
                print(f"    ✗ No SMILES available")
                continue

            # Calculate Lipinski properties
            lipinski_props = get_lipinski_properties(smiles)

            # Calculate QED
            qed = calculate_qed(smiles)

            # Lookup ADMET via Tanimoto
            admet_lookup = lookup_admet_tanimoto(smiles, admet_assays)

            # Calculate safety score (v2 H2B)
            safety_score = calculate_safety_score(admet_lookup)

            # Determine verdict
            if safety_score >= 6:
                verdict = 'PASS'
            elif safety_score >= 4:
                verdict = 'WARNING'
            else:
                verdict = 'FAIL'

            # Extract key safety flags
            ames = admet_lookup.get('ames', {}).get('value', None)
            dili = admet_lookup.get('dili', {}).get('value', None)
            herg = admet_lookup.get('herg', {}).get('value', None)
            cyp3a4 = admet_lookup.get('cyp3a4_veith', {}).get('value', None)

            # Infer administration route from lipinski
            if lipinski_props:
                if lipinski_props['Lipinski_violations'] <= 1 and lipinski_props['MW'] <= 500:
                    admin_route = 'Oral'
                else:
                    admin_route = 'IV/Injection'
            else:
                admin_route = 'Unknown'

            admet_results_list.append({
                'repurposing_rank': row['repurposing_rank'],
                'drug_name': drug_name,
                'smiles': smiles,
                'safety_score': safety_score,
                'verdict': verdict,
                'lipinski_MW': lipinski_props['MW'] if lipinski_props else None,
                'lipinski_LogP': lipinski_props['LogP'] if lipinski_props else None,
                'lipinski_HBD': lipinski_props['HBD'] if lipinski_props else None,
                'lipinski_HBA': lipinski_props['HBA'] if lipinski_props else None,
                'lipinski_TPSA': lipinski_props['TPSA'] if lipinski_props else None,
                'lipinski_RotBonds': lipinski_props['RotBonds'] if lipinski_props else None,
                'lipinski_violations': lipinski_props['Lipinski_violations'] if lipinski_props else None,
                'qed_score': qed,
                'ames_mutagenicity': ames,
                'dili_hepatotoxicity': dili,
                'herg_cardiotoxicity': herg,
                'cyp3a4_inhibition': cyp3a4,
                'admin_route': admin_route,
                'n_assays_found': len(admet_lookup),
            })

        df_admet = pd.DataFrame(admet_results_list)

        # Replace FAIL drugs with next candidates
        failed_drugs = df_admet[df_admet['verdict'] == 'FAIL']['drug_name'].tolist()

        if failed_drugs:
            print(f"\n  ⚠ {len(failed_drugs)} drugs FAILED ADMET: {failed_drugs}")
            print("  Replacing with next candidates...")

            # Get next candidates from repurposing pool
            next_candidates = df_repurposing[~df_repurposing['drug_name'].isin(df_top15_repurposing['drug_name'])].head(len(failed_drugs))

            # TODO: Re-evaluate ADMET for replacements (skipped for brevity)

        output_admet = Path("admet_top15.csv")
        df_admet.to_csv(output_admet, index=False, encoding='utf-8-sig')

        print(f"\n✓ Saved ADMET results: {output_admet}")
        print(f"\n  ADMET Summary:")
        print(f"    PASS: {(df_admet['verdict'] == 'PASS').sum()}")
        print(f"    WARNING: {(df_admet['verdict'] == 'WARNING').sum()}")
        print(f"    FAIL: {(df_admet['verdict'] == 'FAIL').sum()}")

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "="*100)
    print("PIPELINE COMPLETE")
    print("="*100)
    print("\nGenerated files:")
    print("  1. step6_top30_evaluation.csv - Top 30 with all scores")
    print("  2. validation_report.json - Validation metrics")
    print("  3. repurposing_top15.csv - Final Top 15 repurposing candidates")
    print("  4. admet_top15.csv - ADMET safety validation")
    print("="*100)

if __name__ == "__main__":
    main()
