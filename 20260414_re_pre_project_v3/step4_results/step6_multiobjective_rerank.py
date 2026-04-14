#!/usr/bin/env python3
"""
Step 6 Enhancement: Multi-objective Top 15 Re-selection
- Top 30 → Top 15 using 6 objective scores
- Category-balanced selection (3 approved + 7 research + 5 unapplied)
"""

import pandas as pd
import numpy as np
import requests
import json
import time
from pathlib import Path
from collections import defaultdict

# 14 core breast cancer targets from v2 H4 criteria
CORE_BRCA_TARGETS = {
    'BRCA1', 'BRCA2', 'HER2', 'ESR1', 'PGR',
    'PIK3CA', 'AKT1', 'PTEN', 'CDK4', 'CDK6',
    'CCND1', 'TP53', 'MYC', 'EGFR'
}

# Target aliases
TARGET_ALIASES = {
    'ERBB2': 'HER2',
    'ER': 'ESR1',
    'PR': 'PGR',
}

# Drug target database (from literature and databases)
DRUG_TARGETS = {
    "Entinostat": ["HDAC1", "HDAC2", "HDAC3"],
    "Cediranib": ["VEGFR1", "VEGFR2", "VEGFR3", "KIT"],
    "Vinblastine": ["Tubulin"],
    "ML323": ["USP1"],
    "YK-4-279": ["EWS-FLI1"],
    "AZ6102": ["BRD4"],
    "SB590885": ["BRAF"],
    "BMS-345541": ["IKK", "NFKB"],
    "PFI3": ["SMARCA2", "SMARCA4"],
    "AT13148": ["AKT1", "AKT2", "AKT3", "SGK"],
    "AZD2014": ["MTOR"],
    "Bicalutamide": ["AR"],
    "Nutlin-3a": ["MDM2", "TP53"],
    "GSK2801": ["BAZ2A", "BAZ2B"],
    "AZD1332": ["PI3K"],
    "Doxorubicin": ["TOP2A", "DNA"],
    "Paclitaxel": ["Tubulin"],
    "Carboplatin": ["DNA"],
    "Palbociclib": ["CDK4", "CDK6"],
    "Olaparib": ["PARP1", "PARP2"],
    "Trastuzumab": ["HER2"],
    "Letrozole": ["CYP19A1"],
    "Tamoxifen": ["ESR1", "ESR2"],
    "Lapatinib": ["EGFR", "HER2"],
    "Fulvestrant": ["ESR1"],
    "Anastrozole": ["CYP19A1"],
    "Exemestane": ["CYP19A1"],
    "Ribociclib": ["CDK4", "CDK6"],
    "Abemaciclib": ["CDK4", "CDK6"],
    "Neratinib": ["EGFR", "HER2"],
}

def search_clinicaltrials_breast_cancer(drug_name, max_retries=3):
    """Search ClinicalTrials.gov for breast cancer trials"""
    for attempt in range(max_retries):
        try:
            # Use format.json API v2
            params = {
                'format': 'json',
                'query.term': f'{drug_name} AND breast cancer',
                'filter.overallStatus': 'RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED',
                'pageSize': 100
            }

            url = "https://clinicaltrials.gov/api/v2/studies"
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                count = data.get('totalCount', 0)
                print(f"  {drug_name}: {count} trials")
                return count
            else:
                print(f"  {drug_name}: HTTP {response.status_code}")

        except Exception as e:
            print(f"  {drug_name}: {str(e)[:50]}")
            if attempt < max_retries - 1:
                time.sleep(1)

    return 0

def calculate_target_score(drug_name):
    """Calculate target match score with 14 core BRCA targets"""
    targets = DRUG_TARGETS.get(drug_name, [])

    # Normalize target names
    normalized_targets = set()
    for t in targets:
        t_upper = t.upper()
        # Check if it's an alias
        if t_upper in TARGET_ALIASES:
            normalized_targets.add(TARGET_ALIASES[t_upper])
        else:
            normalized_targets.add(t_upper)

    # Count matches with core targets
    matches = normalized_targets.intersection(CORE_BRCA_TARGETS)

    score = len(matches) / 14.0
    return score, list(matches)

def normalize_tanimoto_score(tanimoto):
    """Convert Tanimoto to 0-1 score using H3 criteria"""
    if pd.isna(tanimoto):
        return 0.0
    if tanimoto > 0.3:
        return 1.0
    elif tanimoto >= 0.1:
        return tanimoto / 0.3
    else:
        return 0.0

def classify_drug_category(drug_name, trial_count, known_fda_approved=None):
    """Classify drug into 3 categories based on clinical evidence"""
    if known_fda_approved and drug_name in known_fda_approved:
        return "Category 1: 유방암 치료제 (FDA 승인)"
    elif trial_count > 0:
        return "Category 2: 유방암 연구 중"
    else:
        return "Category 3: 유방암 미적용"

def main():
    print("="*80)
    print("Step 6 Multi-objective Re-ranking: Top 30 → Top 15")
    print("="*80)

    # Known FDA-approved breast cancer drugs
    FDA_APPROVED_BRCA = {
        'Doxorubicin', 'Paclitaxel', 'Docetaxel', 'Carboplatin', 'Cisplatin',
        'Cyclophosphamide', 'Capecitabine', 'Gemcitabine', 'Vinorelbine',
        'Eribulin', 'Ixabepilone', 'Tamoxifen', 'Letrozole', 'Anastrozole',
        'Exemestane', 'Fulvestrant', 'Trastuzumab', 'Pertuzumab', 'Lapatinib',
        'Neratinib', 'Tucatinib', 'Palbociclib', 'Ribociclib', 'Abemaciclib',
        'Olaparib', 'Talazoparib', 'Alpelisib', 'Everolimus', 'Pembrolizumab',
        'Atezolizumab', 'Vinblastine',  # Added based on reclassification
    }

    # 1. Load H3 Tanimoto results
    print("\n[1/7] Loading H3 Tanimoto results...")
    h3_file = Path("h3_tanimoto_results.csv")
    if not h3_file.exists():
        print(f"  ✗ File not found: {h3_file}")
        return

    df_h3 = pd.read_csv(h3_file)
    print(f"  ✓ Loaded {len(df_h3)} drugs with Tanimoto scores")

    # 2. Load ADMET results (Step 7)
    print("\n[2/7] Loading ADMET safety scores...")
    admet_file = Path("step7_admet_results/step7_admet_results.json")

    admet_scores = {}
    if admet_file.exists():
        with open(admet_file) as f:
            data = json.load(f)
            for profile in data.get('profiles', []):
                drug_name = profile.get('drug_name', '')
                safety_score = profile.get('safety_score', 0)
                admet_scores[drug_name] = safety_score

        print(f"  ✓ Loaded {len(admet_scores)} drugs with ADMET scores")
    else:
        print(f"  ⚠ ADMET file not found: {admet_file}")

    # 3. Load Step 6 survival results (if exists)
    print("\n[3/7] Loading survival analysis results...")
    survival_scores = {}

    step6_files = [
        Path("../step6_results/survival_analysis_results.csv"),
        Path("step6_results/survival_analysis_results.csv"),
    ]

    survival_found = False
    for step6_file in step6_files:
        if step6_file.exists():
            df_survival = pd.read_csv(step6_file)
            for _, row in df_survival.iterrows():
                drug = row.get('약물명', row.get('drug_name', ''))
                p_value = row.get('p_value', row.get('log_rank_p', 1.0))

                if pd.notna(p_value) and p_value < 0.05:
                    survival_scores[drug] = -np.log10(p_value)
                else:
                    survival_scores[drug] = 0.0

            print(f"  ✓ Loaded {len(survival_scores)} drugs with survival scores")
            survival_found = True
            break

    if not survival_found:
        print("  ⚠ Survival results not found, using 0 for all drugs")

    # 4. Load reclassification data (already has clinical trials + categories)
    print("\n[4/7] Loading reclassification data (clinical trials + categories)...")
    reclass_file = Path("drug_reclassification/reclassification_summary.csv")

    clinical_trials = {}
    categories_from_reclass = {}

    if reclass_file.exists():
        df_reclass = pd.read_csv(reclass_file)
        for _, row in df_reclass.iterrows():
            drug = row['약물명']
            trials = row['유방암_임상시험_수']
            papers = row['유방암_논문_수']
            category = row['재분류_카테고리']

            # Use papers as proxy for clinical evidence (more reliable than ClinicalTrials API)
            clinical_trials[drug] = papers
            categories_from_reclass[drug] = category

        print(f"  ✓ Loaded {len(clinical_trials)} drugs with clinical evidence (PubMed papers)")
        print(f"  ✓ Loaded {len(categories_from_reclass)} drugs with categories")
    else:
        print(f"  ⚠ Reclassification file not found: {reclass_file}")
        print("  Searching ClinicalTrials.gov instead...")
        for drug in df_h3['약물명']:
            trial_count = search_clinicaltrials_breast_cancer(drug)
            clinical_trials[drug] = trial_count
            time.sleep(0.5)

    # 5. Calculate all scores
    print("\n[5/7] Calculating multi-objective scores...")
    results = []

    for idx, row in df_h3.iterrows():
        drug = row['약물명']
        rank = idx + 1

        # Score 1: IC50 rank (assuming df_h3 is sorted by IC50)
        ic50_score = 1 - (rank / len(df_h3))

        # Score 2: Survival
        survival_score = survival_scores.get(drug, 0.0)

        # Score 3: H3 Tanimoto
        tanimoto = row.get('Tanimoto', 0)
        tanimoto_score = normalize_tanimoto_score(tanimoto)

        # Score 4: Target match
        target_score, matched_targets = calculate_target_score(drug)

        # Score 5: ADMET safety_score / 12
        safety_score = admet_scores.get(drug, 0)
        admet_score = safety_score / 12.0

        # Score 6: Clinical evidence
        trials = clinical_trials.get(drug, 0)
        clinical_score = np.log10(trials + 1)

        # Calculate final score (weighted sum)
        final_score = (
            0.25 * ic50_score +
            0.15 * survival_score +
            0.15 * tanimoto_score +
            0.15 * target_score +
            0.15 * admet_score +
            0.15 * clinical_score
        )

        # Get category from reclassification (or classify if not found)
        category = categories_from_reclass.get(drug, classify_drug_category(drug, trials, FDA_APPROVED_BRCA))

        results.append({
            '약물명': drug,
            'IC50_rank': rank,
            'IC50_score': round(ic50_score, 4),
            'Survival_score': round(survival_score, 4),
            'Tanimoto': round(tanimoto, 4) if pd.notna(tanimoto) else 0,
            'Tanimoto_score': round(tanimoto_score, 4),
            'Target_matches': ', '.join(matched_targets) if matched_targets else 'None',
            'Target_score': round(target_score, 4),
            'ADMET_safety': safety_score,
            'ADMET_score': round(admet_score, 4),
            'Clinical_trials': trials,
            'Clinical_score': round(clinical_score, 4),
            'Final_score': round(final_score, 4),
            'Category': category,
        })

    df_all = pd.DataFrame(results)

    # Normalize clinical_score to 0-1
    if df_all['Clinical_score'].max() > 0:
        df_all['Clinical_score'] = df_all['Clinical_score'] / df_all['Clinical_score'].max()

    # Recalculate final score with normalized clinical
    df_all['Final_score'] = (
        0.25 * df_all['IC50_score'] +
        0.15 * df_all['Survival_score'] +
        0.15 * df_all['Tanimoto_score'] +
        0.15 * df_all['Target_score'] +
        0.15 * df_all['ADMET_score'] +
        0.15 * df_all['Clinical_score']
    ).round(4)

    # 6. Category-balanced Top 15 selection
    print("\n[6/7] Selecting category-balanced Top 15...")

    cat1 = df_all[df_all['Category'].str.contains('치료제')].sort_values('Final_score', ascending=False)
    cat2 = df_all[df_all['Category'].str.contains('연구')].sort_values('Final_score', ascending=False)
    cat3 = df_all[df_all['Category'].str.contains('미적용')].sort_values('Final_score', ascending=False)

    print(f"  Category 1 (치료제): {len(cat1)}개")
    print(f"  Category 2 (연구 중): {len(cat2)}개")
    print(f"  Category 3 (미적용): {len(cat3)}개")

    # Target: 3 + 7 + 5 = 15
    selected = []

    # Take top from each category
    n_cat1 = min(3, len(cat1))
    n_cat2 = min(7, len(cat2))
    n_cat3 = min(5, len(cat3))

    selected.extend(cat1.head(n_cat1).to_dict('records'))
    selected.extend(cat2.head(n_cat2).to_dict('records'))
    selected.extend(cat3.head(n_cat3).to_dict('records'))

    # If we have less than 15, fill from remaining drugs by Final_score
    if len(selected) < 15:
        selected_drugs = [d['약물명'] for d in selected]
        remaining = df_all[~df_all['약물명'].isin(selected_drugs)].sort_values('Final_score', ascending=False)
        needed = 15 - len(selected)
        selected.extend(remaining.head(needed).to_dict('records'))

    df_top15 = pd.DataFrame(selected).sort_values('Final_score', ascending=False).reset_index(drop=True)
    df_top15.insert(0, 'Rank', range(1, len(df_top15) + 1))

    print(f"\n  ✓ Selected {len(df_top15)} drugs")
    print(f"    - Category 1: {len([d for d in selected if '치료제' in d['Category']])}개")
    print(f"    - Category 2: {len([d for d in selected if '연구' in d['Category']])}개")
    print(f"    - Category 3: {len([d for d in selected if '미적용' in d['Category']])}개")

    # 7. Save results
    print("\n[7/7] Saving results...")

    # Save all 30 scores
    output1 = Path("top30_all_scores.csv")
    df_all.to_csv(output1, index=False, encoding='utf-8-sig')
    print(f"  ✓ Saved: {output1}")

    # Save top 15
    output2 = Path("top15_reranked.csv")
    df_top15.to_csv(output2, index=False, encoding='utf-8-sig')
    print(f"  ✓ Saved: {output2}")

    # Save category classification
    output3 = Path("category_classification.csv")
    df_category = df_all[['약물명', 'Category', 'Clinical_trials', 'Final_score']].copy()
    df_category.to_csv(output3, index=False, encoding='utf-8-sig')
    print(f"  ✓ Saved: {output3}")

    # Save hurdle summary
    output4 = Path("hurdle_summary.json")
    hurdle_summary = {
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_drugs": len(df_all),
        "top15_drugs": len(df_top15),
        "scoring_weights": {
            "IC50_rank": 0.25,
            "Survival": 0.15,
            "H3_Tanimoto": 0.15,
            "H4_Target": 0.15,
            "ADMET": 0.15,
            "Clinical": 0.15
        },
        "category_distribution": {
            "Category_1_치료제": len(cat1),
            "Category_2_연구중": len(cat2),
            "Category_3_미적용": len(cat3)
        },
        "top15_category_distribution": {
            "Category_1_치료제": len([d for d in selected if '치료제' in d['Category']]),
            "Category_2_연구중": len([d for d in selected if '연구' in d['Category']]),
            "Category_3_미적용": len([d for d in selected if '미적용' in d['Category']])
        },
        "top15_drugs": df_top15['약물명'].tolist(),
        "score_statistics": {
            "mean_final_score": float(df_top15['Final_score'].mean()),
            "max_final_score": float(df_top15['Final_score'].max()),
            "min_final_score": float(df_top15['Final_score'].min())
        }
    }

    with open(output4, 'w', encoding='utf-8') as f:
        json.dump(hurdle_summary, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved: {output4}")

    # Display summary
    print("\n" + "="*80)
    print("Summary")
    print("="*80)

    print("\nTop 15 Re-ranked Drugs:")
    print("-" * 80)
    for _, row in df_top15.iterrows():
        cat_short = row['Category'].split(':')[0]
        print(f"  {row['Rank']:2d}. {row['약물명']:18s} "
              f"Final={row['Final_score']:.4f} | "
              f"IC50={row['IC50_score']:.2f} Tani={row['Tanimoto_score']:.2f} "
              f"Tgt={row['Target_score']:.2f} ADMET={row['ADMET_score']:.2f} | "
              f"{cat_short}")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
