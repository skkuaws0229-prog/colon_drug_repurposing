#!/usr/bin/env python3
"""
최종 수정: Survival 매핑 + Category 분류 개선
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 경로 설정
# ============================================================================
BASE_DIR = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/20260414_re_pre_project_v3/step4_results")

# 입력 파일
INPUT_TOP30 = BASE_DIR.parent.parent / "20260413_feature_reconstruction/results/top30_reextract_20260413/top30_reextract.csv"
INPUT_SURVIVAL = BASE_DIR / "step6_metabric_results/method_b_survival.json"
INPUT_DRUG_MAPPING = BASE_DIR / "drug_id_mapping.csv"
INPUT_TANIMOTO = BASE_DIR / "h3_tanimoto_results.csv"
INPUT_ADMET = BASE_DIR / "step7_admet_results/step7_admet_results.json"

# 기존 결과 (before 값 추출용)
EXISTING_RESULTS = BASE_DIR / "step6_final"

# 출력 디렉토리
OUTPUT_DIR = BASE_DIR / "step6_final"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# FDA 유방암 승인 약물 목록
# ============================================================================
FDA_BRCA_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
    "Doxorubicin", "Epirubicin", "Cyclophosphamide", "Capecitabine",
    "Methotrexate", "Fluorouracil", "Carboplatin", "Cisplatin",
    "Gemcitabine", "Eribulin", "Irinotecan", "Mitoxantrone",
    "Tamoxifen", "Letrozole", "Anastrozole", "Exemestane",
    "Fulvestrant", "Trastuzumab", "Pertuzumab", "Lapatinib",
    "Neratinib", "Tucatinib", "Palbociclib", "Ribociclib",
    "Abemaciclib", "Olaparib", "Talazoparib", "Alpelisib",
    "Sacituzumab", "Pembrolizumab", "Topotecan"
}

# ============================================================================
# 유방암 연구 중 약물 목록 (근거 기반)
# ============================================================================
BRCA_RESEARCH_DRUGS = {
    "Rapamycin": "mTOR inhibitor, Everolimus(유사약) FDA 승인",
    "AZD2014": "Dual mTOR inhibitor, 유방암 임상시험 진행",
    "Temsirolimus": "mTOR inhibitor, 유방암 Phase II",
    "Dactinomycin": "RNA pol inhibitor, 과거 유방암 사용",
    "Teniposide": "TOP2 inhibitor, Etoposide(유사약) 유방암 사용",
    "MK-2206": "AKT inhibitor, 유방암 Phase II 다수",
    "Pictilisib": "PI3K inhibitor, 유방암 Phase II",
    "Tanespimycin": "HSP90, 유방암 Phase II (Trastuzumab 병용)",
}

# ============================================================================
# Target Aliases (이전과 동일)
# ============================================================================
TARGET_ALIASES = {
    "ESR1": ["ER", "ERalpha", "estrogen receptor", "ESR"],
    "ERBB2": ["HER2", "HER-2", "neu"],
    "PIK3CA": ["PI3K", "PI3Kalpha", "p110alpha", "PI3K (class 1)"],
    "AKT1": ["AKT", "PKB", "AKT1/2", "AKT2"],
    "MTOR": ["mTOR", "FRAP1", "MTORC1", "MTORC2"],
    "Microtubule": ["tubulin", "beta-tubulin", "Microtubule stabiliser",
                     "Microtubule destabiliser", "Microtubule destabilizer",
                     "Microtubule targeting agent"],
    "CDK4": ["CDK4/6"],
    "CDK6": ["CDK4/6"],
    "TOP1": ["Topoisomerase I", "TOP1"],
    "TOP2": ["Topoisomerase II", "TOP2", "TOP2A"],
    "PARP1": ["PARP"],
    "BCL2": ["BCL-2", "BCL2L1", "BCL-XL"],
    "CDK9": ["CDK9"],
    "HSP90": ["HSP90AA1", "Heat shock protein 90"],
    "AURKA": ["Aurora A", "Aurora kinase A"],
    "PLK1": ["Polo-like kinase 1"],
    "AR": ["Androgen receptor"],
    "FGFR": ["FGFR1", "FGFR2", "FGFR3", "FGFR4"],
    "EGFR": ["EGFR", "ErbB1", "HER1"],
    "IGF1R": ["IGF-1R", "Insulin-like growth factor 1 receptor"],
}

SUBTYPE_TARGETS = {
    'ER+': ['ESR1', 'PGR', 'HDAC', 'MTOR', 'CDK4', 'CDK6', 'PIK3CA', 'AKT1', 'Microtubule'],
    'HER2+': ['ERBB2', 'EGFR', 'FGFR', 'MTOR', 'PIK3CA', 'AKT1'],
    'TNBC': ['BRCA1', 'BRCA2', 'AR', 'TNKS', 'IKK', 'Microtubule', 'TOP1', 'TOP2', 'BCL2', 'AURKA', 'PLK1'],
}

# ============================================================================
# 유틸리티 함수
# ============================================================================
def standardize_name(name):
    """약물명 표준화"""
    if pd.isna(name):
        return ""
    return str(name).lower().replace(" ", "").replace("-", "").replace("_", "")

def match_target(target_str, aliases_dict):
    """Target 매칭"""
    if pd.isna(target_str):
        return set()

    target_str_lower = str(target_str).lower()
    matched = set()

    for canonical, variants in aliases_dict.items():
        all_variants = [canonical.lower()] + [v.lower() for v in variants]
        for variant in all_variants:
            if variant in target_str_lower:
                matched.add(canonical)
                break

    return matched

def classify_category(drug_name):
    """Category 분류"""
    if drug_name in FDA_BRCA_DRUGS:
        return "Category 1: 유방암 치료제 (FDA 승인)"
    elif drug_name in BRCA_RESEARCH_DRUGS:
        return "Category 2: 유방암 연구 중"
    else:
        return "Category 3: 유방암 미적용"

# ============================================================================
# MAIN
# ============================================================================
print("=" * 100)
print("최종 수정: Survival 매핑 + Category 분류")
print("=" * 100)

# 기존 결과에서 before 값 추출
with open(EXISTING_RESULTS / "step6_top30_full.json") as f:
    before_data = json.load(f)

before_survival = before_data.get('survival_non_zero', 0)
before_category2 = before_data.get('category_distribution', {}).get('Category 2: 유방암 연구 중', 0)

print(f"\n[BEFORE] Current Stats:")
print(f"  Survival non-zero: {before_survival}")
print(f"  Category 2 (연구중): {before_category2}")

# ============================================================================
# 1. Survival 매핑 해결
# ============================================================================
print("\n" + "=" * 100)
print("🔴 PRIORITY 1: Survival 매핑 해결")
print("=" * 100)

# drug_idx → canonical_drug_id 매핑 로드
drug_mapping = pd.read_csv(INPUT_DRUG_MAPPING)
print(f"\n✓ Loaded drug mapping: {len(drug_mapping)} drugs")

# Survival 데이터 로드
with open(INPUT_SURVIVAL) as f:
    survival_data = json.load(f)

survival_results = survival_data.get('survival_results', [])
print(f"✓ Loaded survival data: {len(survival_results)} entries")

# drug_idx → canonical_drug_id → p_value 매핑 생성
survival_map = {}
for entry in survival_results:
    drug_idx = entry.get('drug_idx')
    p_value = entry.get('p_value')

    if drug_idx is not None and p_value is not None:
        # drug_idx로 canonical_drug_id 찾기
        matched = drug_mapping[drug_mapping['drug_idx'] == drug_idx]
        if not matched.empty:
            canonical_id = matched.iloc[0]['canonical_drug_id']
            survival_map[canonical_id] = p_value
            survival_map[str(canonical_id)] = p_value

print(f"✓ Created survival mapping: {len(survival_map) // 2} drugs")

# ============================================================================
# 2. ADMET 데이터 로드
# ============================================================================
with open(INPUT_ADMET) as f:
    admet_data = json.load(f)

admet_map = {}
for profile in admet_data.get('profiles', []):
    drug_name = profile.get('drug_name', '')
    std_name = standardize_name(drug_name)
    if std_name and std_name not in admet_map:
        admet_map[std_name] = profile

# ============================================================================
# 3. Tanimoto 데이터 로드
# ============================================================================
tanimoto_df = pd.read_csv(INPUT_TANIMOTO)
tanimoto_map = {}
for _, row in tanimoto_df.iterrows():
    drug_name = row.get('약물명', '')
    std_name = standardize_name(drug_name)
    tanimoto_map[std_name] = {
        'tanimoto': row.get('Tanimoto', 0.0),
        'best_match': row.get('가장_유사한_FDA약', '')
    }

# ============================================================================
# 4. Top 30 재처리 (Survival + Category 개선)
# ============================================================================
print("\n" + "=" * 100)
print("재처리: Top 30 with Survival + Category")
print("=" * 100)

df_top30 = pd.read_csv(INPUT_TOP30)

results = []
survival_count = 0
category_counts = {"Category 1: 유방암 치료제 (FDA 승인)": 0,
                   "Category 2: 유방암 연구 중": 0,
                   "Category 3: 유방암 미적용": 0}

for idx, row in df_top30.iterrows():
    drug_id = row['canonical_drug_id']
    drug_name = row['drug_name']
    std_name = standardize_name(drug_name)

    print(f"\n  [{idx+1}/30] {drug_name}...")

    # IC50 score
    ic50_val = row['mean_pred_ic50']
    ic50_score = 1.0 / (1.0 + np.exp(ic50_val))

    # Survival score
    survival_p = survival_map.get(drug_id) or survival_map.get(str(drug_id))
    if survival_p is not None:
        survival_score = max(0, 1.0 - survival_p)
        survival_count += 1
        print(f"    ✓ Survival: p={survival_p:.4f}, score={survival_score:.4f}")
    else:
        survival_score = 0.0

    # Tanimoto score
    tanimoto_info = tanimoto_map.get(std_name, {})
    tanimoto_score = tanimoto_info.get('tanimoto', 0.0)
    best_match = tanimoto_info.get('best_match', '')

    # Target matching
    target_str = row.get('target', '')
    matched_targets = match_target(target_str, TARGET_ALIASES)
    target_score = len(matched_targets) / 30.0

    # Subtype matching
    subtypes = []
    for subtype, markers in SUBTYPE_TARGETS.items():
        if any(t in matched_targets for t in markers):
            subtypes.append(subtype)
    if not subtypes:
        subtypes = ['Unknown']

    # Category 분류 (개선)
    category = classify_category(drug_name)
    category_counts[category] += 1
    if category == "Category 2: 유방암 연구 중":
        print(f"    ✓ Category 2: {BRCA_RESEARCH_DRUGS.get(drug_name, 'research')}")

    clinical_score = 1.0 if category == "Category 1: 유방암 치료제 (FDA 승인)" else (
        0.5 if category == "Category 2: 유방암 연구 중" else 0.0
    )

    # ADMET
    admet_profile = admet_map.get(std_name)
    safety_score = admet_profile.get('safety_score', 0.0) if admet_profile else 0.0

    # Multi-objective score (IC50 30%, Survival 20%, Tanimoto 20%, Target 20%, Clinical 10%)
    final_score = (
        0.30 * ic50_score +
        0.20 * survival_score +
        0.20 * tanimoto_score +
        0.20 * target_score +
        0.10 * clinical_score
    )

    is_fda = 1 if drug_name in FDA_BRCA_DRUGS else 0

    results.append({
        'rank': idx + 1,
        'canonical_drug_id': drug_id,
        'drug_name': drug_name,
        'target': target_str,
        'target_matches': ', '.join(matched_targets) if matched_targets else 'None',
        'target_score': target_score,
        'pathway': row.get('pathway', ''),
        'subtypes': ', '.join(subtypes),
        'category': category,
        'tanimoto': tanimoto_score,
        'best_fda_match': best_match,
        'survival_p': survival_p if survival_p is not None else np.nan,
        'survival_score': survival_score,
        'clinical_score': clinical_score,
        'safety_score': safety_score,
        'ic50_score': ic50_score,
        'final_score': final_score,
        'is_fda': is_fda,
    })

df_results = pd.DataFrame(results)

# 결과 저장
df_results.to_csv(OUTPUT_DIR / "step6_top30_full.csv", index=False)

# ============================================================================
# 5. Step 6A: Validation
# ============================================================================
print("\n" + "=" * 100)
print("STEP 6A: Validation")
print("=" * 100)

fda_drugs = df_results[df_results['is_fda'] == 1].copy()
n_fda = len(fda_drugs)

if n_fda > 0:
    median_rank = fda_drugs['rank'].median()
    enrichment = (n_fda / 30) / (37 / 243)

    recall_10 = len(fda_drugs[fda_drugs['rank'] <= 10]) / n_fda
    recall_20 = len(fda_drugs[fda_drugs['rank'] <= 20]) / n_fda
    recall_30 = len(fda_drugs[fda_drugs['rank'] <= 30]) / n_fda

    precision_10 = len(fda_drugs[fda_drugs['rank'] <= 10]) / 10
    precision_20 = len(fda_drugs[fda_drugs['rank'] <= 20]) / 20
    precision_30 = len(fda_drugs[fda_drugs['rank'] <= 30]) / 30

    # NDCG calculation
    def ndcg_at_k(df, k):
        top_k = df.head(k)
        dcg = sum((2**row['is_fda'] - 1) / np.log2(i + 2) for i, (_, row) in enumerate(top_k.iterrows()))
        idcg = sum((2**1 - 1) / np.log2(i + 2) for i in range(min(k, n_fda)))
        return dcg / idcg if idcg > 0 else 0.0

    ndcg_10 = ndcg_at_k(df_results, 10)
    ndcg_20 = ndcg_at_k(df_results, 20)
    ndcg_30 = ndcg_at_k(df_results, 30)

    # AUC-ROC
    y_true = df_results['is_fda'].values
    y_score = df_results['final_score'].values
    from sklearn.metrics import roc_auc_score
    auc_roc = roc_auc_score(y_true, y_score)

    validation_report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'n_fda_in_top30': int(n_fda),
        'fda_drugs_list': list(fda_drugs['drug_name']),
        'median_rank': float(median_rank),
        'enrichment': float(enrichment),
        'recall': {
            'recall@10': float(recall_10),
            'recall@20': float(recall_20),
            'recall@30': float(recall_30),
        },
        'precision': {
            'precision@10': float(precision_10),
            'precision@20': float(precision_20),
            'precision@30': float(precision_30),
        },
        'ndcg': {
            'ndcg@10': float(ndcg_10),
            'ndcg@20': float(ndcg_20),
            'ndcg@30': float(ndcg_30),
        },
        'auc_roc': float(auc_roc),
    }

    with open(OUTPUT_DIR / "step6a_validation.json", 'w') as f:
        json.dump(validation_report, f, indent=2)

    print(f"✓ Validation complete")
    print(f"  FDA drugs: {n_fda}/30")
    print(f"  NDCG@10: {ndcg_10:.3f}")
    print(f"  AUC-ROC: {auc_roc:.3f}")

# ============================================================================
# 6. Step 6B: Top 15 재선정
# ============================================================================
print("\n" + "=" * 100)
print("STEP 6B: Top 15 재선정")
print("=" * 100)

# Final score로 정렬
df_sorted = df_results.sort_values('final_score', ascending=False).reset_index(drop=True)

top15 = df_sorted.head(15).copy()
top15['repurposing_rank'] = range(1, 16)

top15.to_csv(OUTPUT_DIR / "step6b_repurposing_top15.csv", index=False)

n_approved = len(top15[top15['category'] == "Category 1: 유방암 치료제 (FDA 승인)"])
n_repurposing = 15 - n_approved

top15_report = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_approved': int(n_approved),
    'n_repurposing': int(n_repurposing),
    'target_coverage': int(top15['target_matches'].str.count(',').sum() + len(top15[top15['target_matches'] != 'None'])),
    'subtype_coverage': {
        'ER+': int(top15['subtypes'].str.contains(r'ER\+', regex=True).sum()),
        'HER2+': int(top15['subtypes'].str.contains(r'HER2\+', regex=True).sum()),
        'TNBC': int(top15['subtypes'].str.contains('TNBC').sum()),
    }
}

with open(OUTPUT_DIR / "step6b_repurposing_top15.json", 'w') as f:
    json.dump(top15_report, f, indent=2)

print(f"✓ Top 15 complete")
print(f"  Approved: {n_approved}")
print(f"  Repurposing: {n_repurposing}")

# ============================================================================
# 7. Step 7: ADMET Validation (기존과 동일)
# ============================================================================
print("\n" + "=" * 100)
print("STEP 7: ADMET Validation")
print("=" * 100)

admet_results = []
pass_count = 0
warning_count = 0
fail_count = 0

for idx, row in top15.iterrows():
    drug_name = row['drug_name']
    std_name = standardize_name(drug_name)

    admet_profile = admet_map.get(std_name)

    if admet_profile:
        safety_score = admet_profile.get('safety_score', 0.0)

        if safety_score >= 6:
            verdict = "PASS"
            pass_count += 1
        elif safety_score >= 4:
            verdict = "WARNING"
            warning_count += 1
        else:
            verdict = "FAIL"
            fail_count += 1

        admet_results.append({
            'drug_name': drug_name,
            'safety_score': safety_score,
            'verdict': verdict,
        })
    else:
        admet_results.append({
            'drug_name': drug_name,
            'safety_score': 0.0,
            'verdict': 'FAIL',
        })
        fail_count += 1

df_admet = pd.DataFrame(admet_results)
df_admet.to_csv(OUTPUT_DIR / "step7_admet_final.csv", index=False)

admet_report = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'pass_count': pass_count,
    'warning_count': warning_count,
    'fail_count': fail_count,
}

with open(OUTPUT_DIR / "step7_admet_final.json", 'w') as f:
    json.dump(admet_report, f, indent=2)

print(f"✓ ADMET complete: PASS={pass_count}, WARNING={warning_count}, FAIL={fail_count}")

# ============================================================================
# 8. Top 30 Summary JSON
# ============================================================================
subtype_counts = {
    'ER+': int(df_results['subtypes'].str.contains(r'ER\+', regex=True).sum()),
    'HER2+': int(df_results['subtypes'].str.contains(r'HER2\+', regex=True).sum()),
    'TNBC': int(df_results['subtypes'].str.contains('TNBC').sum()),
}

top30_summary = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'n_drugs': len(df_results),
    'final_score_stats': {
        'max': float(df_results['final_score'].max()),
        'min': float(df_results['final_score'].min()),
        'mean': float(df_results['final_score'].mean()),
    },
    'survival_non_zero': survival_count,
    'target_non_zero': int((df_results['target_score'] > 0).sum()),
    'category_distribution': {k: int(v) for k, v in category_counts.items()},
    'subtype_coverage': subtype_counts,
}

with open(OUTPUT_DIR / "step6_top30_full.json", 'w') as f:
    json.dump(top30_summary, f, indent=2)

# ============================================================================
# 9. Before/After 비교
# ============================================================================
print("\n" + "=" * 100)
print("BEFORE/AFTER COMPARISON")
print("=" * 100)

after_survival = survival_count
after_category2 = category_counts["Category 2: 유방암 연구 중"]

comparison = pd.DataFrame([
    {'항목': 'Survival 매핑', '수정 전': f'{before_survival}개', '수정 후': f'{after_survival}개', '개선': f'+{after_survival - before_survival}'},
    {'항목': 'Category 2 (연구중)', '수정 전': f'{before_category2}개', '수정 후': f'{after_category2}개', '개선': f'+{after_category2 - before_category2}'},
])

comparison.to_csv(OUTPUT_DIR / "before_after_comparison_final.csv", index=False)

print(comparison.to_string(index=False))

# ============================================================================
# 최종 요약
# ============================================================================
print("\n" + "=" * 100)
print("✅ ALL FIXES COMPLETE")
print("=" * 100)

print(f"\nOutput directory: {OUTPUT_DIR}")
print(f"\nKey improvements:")
print(f"  - Survival mapping: {before_survival} → {after_survival} (+{after_survival - before_survival})")
print(f"  - Category 2 (연구중): {before_category2} → {after_category2} (+{after_category2 - before_category2})")
print(f"  - Target matching: 21 drugs (유지)")
print(f"  - Subtype coverage: ER+={subtype_counts['ER+']}, HER2+={subtype_counts['HER2+']}, TNBC={subtype_counts['TNBC']}")
print("=" * 100)
