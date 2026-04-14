#!/usr/bin/env python3
"""
Top 15 약물 전체 상세 테이블 생성
- 3개 카테고리 분류
- 전체 약물 상세 정보
- 추천 이유 및 한계사항 (카테고리 2, 3)
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Paths
STEP6_DIR = Path(__file__).parent / "step6_metabric_results"
STEP7_DIR = Path(__file__).parent / "step7_admet_results"
DATA_DIR = Path(__file__).parent / "20260414_re_pre_project_v3" / "20260414_re_pre_project_v3" / "data"
OUTPUT_DIR = Path(__file__).parent / "top15_comprehensive_tables"
OUTPUT_DIR.mkdir(exist_ok=True)

# Known drug information database
DRUG_DATABASE = {
    "Entinostat": {
        "moa": "HDAC (Histone Deacetylase) inhibitor - epigenetic modulator",
        "indications": "Advanced breast cancer (in clinical trials), Hodgkin lymphoma",
        "route": "Oral",
        "clinical_phase": "Phase III (breast cancer)",
        "brca_subtype": "ER+ (Hormone receptor positive)",
        "brca_rationale": "HDAC inhibition can restore hormone sensitivity in ER+ breast cancer. E2112 trial showed benefit with exemestane in advanced ER+ disease.",
        "similar_approved": "Vorinostat (HDAC inhibitor, approved for CTCL)",
        "limitations": "Limited to ER+ subtype, not effective in TNBC or HER2+"
    },
    "Cediranib": {
        "moa": "Multi-kinase inhibitor (VEGFR, PDGFR, c-KIT) - anti-angiogenic",
        "indications": "Ovarian cancer, glioblastoma (trials), metastatic breast cancer (trials)",
        "route": "Oral",
        "clinical_phase": "Phase II/III (breast cancer)",
        "brca_subtype": "TNBC, HER2+ (angiogenesis-dependent tumors)",
        "brca_rationale": "VEGF inhibition reduces tumor angiogenesis. Bevacizumab (anti-VEGF) is approved for metastatic HER2- breast cancer.",
        "similar_approved": "Bevacizumab (anti-VEGF antibody, breast cancer approved)",
        "limitations": "Hypertension, bleeding risk, may not benefit ER+ low-grade tumors"
    },
    "Vinblastine": {
        "moa": "Microtubule destabilizer (vinca alkaloid) - mitotic arrest",
        "indications": "Hodgkin lymphoma, testicular cancer, Kaposi sarcoma, breast cancer",
        "route": "Intravenous (IV)",
        "clinical_phase": "Approved (standard chemotherapy)",
        "brca_subtype": "All subtypes (chemotherapy backbone)",
        "brca_rationale": "Established chemotherapy for breast cancer. Part of VAC regimen historically.",
        "similar_approved": "Paclitaxel, Docetaxel (microtubule-targeting, breast cancer approved)",
        "limitations": "Neurotoxicity, myelosuppression, broad cytotoxicity"
    },
    "ML323": {
        "moa": "USP1-UAF1 complex inhibitor - DNA damage response modulator",
        "indications": "Investigational (DNA repair-deficient cancers)",
        "route": "Oral (preclinical)",
        "clinical_phase": "Preclinical/Phase I",
        "brca_subtype": "TNBC (especially BRCA1/2 mutant)",
        "brca_rationale": "USP1 inhibition enhances PARP inhibitor sensitivity in BRCA-deficient tumors. Synergy with olaparib in preclinical models.",
        "similar_approved": "Olaparib (PARP inhibitor, BRCA-mutant breast cancer approved)",
        "limitations": "Early development, toxicity profile unknown, limited clinical data"
    },
    "YK-4-279": {
        "moa": "EWS-FLI1 inhibitor - disrupts oncogenic transcription factor",
        "indications": "Ewing sarcoma (investigational)",
        "route": "Oral (preclinical)",
        "clinical_phase": "Preclinical",
        "brca_subtype": "TNBC (transcription-dependent subtypes)",
        "brca_rationale": "RNA helicase A is overexpressed in TNBC. May disrupt oncogenic transcription programs.",
        "similar_approved": "None (novel MOA)",
        "limitations": "Very early stage, Ewing sarcoma-specific target, no breast cancer clinical data"
    },
    "AZ6102": {
        "moa": "Tankyrase (TNKS1/2) inhibitor - Wnt/β-catenin pathway inhibitor",
        "indications": "Colorectal cancer (investigational)",
        "route": "Oral",
        "clinical_phase": "Phase I/II",
        "brca_subtype": "TNBC (Wnt-activated tumors)",
        "brca_rationale": "Wnt/β-catenin pathway is activated in ~50% TNBC. Tankyrase inhibition stabilizes AXIN, suppressing Wnt signaling.",
        "similar_approved": "None (Wnt pathway inhibitors in development)",
        "limitations": "GI toxicity, limited efficacy as monotherapy, needs biomarker selection"
    },
    "SB590885": {
        "moa": "BRAF inhibitor (selective for BRAF V600E)",
        "indications": "Melanoma with BRAF V600E mutation",
        "route": "Oral",
        "clinical_phase": "Phase I/II (discontinued)",
        "brca_subtype": "Rare BRAF-mutant breast cancer",
        "brca_rationale": "BRAF mutations occur in <5% breast cancers. May benefit BRAF V600E-positive cases.",
        "similar_approved": "Vemurafenib (BRAF inhibitor, melanoma approved)",
        "limitations": "Very rare mutation in breast cancer, development discontinued, paradoxical MAPK activation"
    },
    "BMS-345541": {
        "moa": "IKK inhibitor - NF-κB pathway inhibitor (anti-inflammatory)",
        "indications": "Inflammatory diseases (investigational)",
        "route": "Oral",
        "clinical_phase": "Preclinical/Phase I",
        "brca_subtype": "TNBC (inflammation-driven tumors)",
        "brca_rationale": "NF-κB is constitutively active in TNBC and mediates chemoresistance. IKK inhibition may enhance chemotherapy sensitivity.",
        "similar_approved": "None (NF-κB inhibitors investigational)",
        "limitations": "Immune suppression risk, no clinical cancer data, may affect normal immunity"
    },
    "PFI3": {
        "moa": "SMARCA4/BRD4 bromodomain inhibitor - epigenetic reader inhibitor",
        "indications": "Solid tumors (investigational)",
        "route": "Oral",
        "clinical_phase": "Preclinical",
        "brca_subtype": "TNBC, ER+ (epigenetically dysregulated)",
        "brca_rationale": "BRD4 drives oncogenic transcription in breast cancer. Bromodomain inhibitors show activity in ER+ and TNBC models.",
        "similar_approved": "None (bromodomain inhibitors in trials)",
        "limitations": "Thrombocytopenia, GI toxicity, early development"
    },
    "AT13148": {
        "moa": "Pan-AKT inhibitor - PI3K/AKT/mTOR pathway inhibitor",
        "indications": "Solid tumors with PI3K/AKT pathway activation",
        "route": "Oral",
        "clinical_phase": "Phase I/II",
        "brca_subtype": "ER+, HER2+ (PI3K-activated tumors)",
        "brca_rationale": "PI3K/AKT pathway is hyperactivated in 70% ER+ and 30% HER2+ breast cancers. AKT inhibition can overcome endocrine resistance.",
        "similar_approved": "Alpelisib (PI3K inhibitor, ER+ breast cancer approved)",
        "limitations": "Hyperglycemia, diarrhea, rash. Requires PIK3CA mutation or PTEN loss."
    },
    "AZD2014": {
        "moa": "Dual mTORC1/mTORC2 inhibitor - PI3K/AKT/mTOR pathway inhibitor",
        "indications": "Advanced solid tumors (investigational)",
        "route": "Oral",
        "clinical_phase": "Phase I/II",
        "brca_subtype": "ER+, HER2+ (mTOR-activated tumors)",
        "brca_rationale": "mTOR pathway is activated in 70% ER+ breast cancers. Dual mTORC1/2 inhibition overcomes resistance to everolimus (mTORC1 inhibitor).",
        "similar_approved": "Everolimus (mTORC1 inhibitor, ER+ breast cancer approved)",
        "limitations": "Metabolic toxicity (hyperglycemia, hyperlipidemia), stomatitis, immunosuppression"
    },
    "Bicalutamide": {
        "moa": "Androgen receptor (AR) antagonist - hormone therapy",
        "indications": "Prostate cancer (FDA approved)",
        "route": "Oral",
        "clinical_phase": "Phase II (breast cancer)",
        "brca_subtype": "AR+ TNBC (luminal AR subtype)",
        "brca_rationale": "30% of TNBC express AR. Bicalutamide shows activity in AR+ TNBC (luminal AR subtype). Enzalutamide is being tested in AR+ breast cancer.",
        "similar_approved": "Enzalutamide (AR antagonist, prostate cancer approved)",
        "limitations": "DILI (hepatotoxicity) risk, gynaecomastia, limited to AR+ subset (~10-15% of all breast cancers)"
    },
    "Nutlin-3a (-)": {
        "moa": "MDM2 inhibitor - p53 pathway activator",
        "indications": "p53 wild-type solid tumors (investigational)",
        "route": "Oral (preclinical)",
        "clinical_phase": "Preclinical (Nutlin-3a is tool compound)",
        "brca_subtype": "ER+, HER2+ (p53 wild-type tumors)",
        "brca_rationale": "85% of breast cancers retain wild-type p53. MDM2 inhibition restores p53 tumor suppressor function. Idasanutlin (MDM2i) showed activity in AML.",
        "similar_approved": "None (MDM2 inhibitors in trials)",
        "limitations": "Hematologic toxicity (thrombocytopenia, neutropenia), GI toxicity, p53 mutation status required"
    },
    "AZD1332": {
        "moa": "Pan-TRK inhibitor (NTRK1/2/3) - neurotrophic receptor inhibitor",
        "indications": "NTRK fusion-positive solid tumors",
        "route": "Oral",
        "clinical_phase": "Phase I/II",
        "brca_subtype": "NTRK fusion-positive breast cancer (rare <1%)",
        "brca_rationale": "NTRK fusions are oncogenic drivers in <1% breast cancers (secretory breast carcinoma). TRK inhibitors show dramatic responses in NTRK+ tumors.",
        "similar_approved": "Larotrectinib, Entrectinib (TRK inhibitors, tumor-agnostic NTRK+ approval)",
        "limitations": "Extremely rare in breast cancer (<1%), requires NTRK fusion testing, neurotoxicity"
    },
    "GSK2801": {
        "moa": "Unknown (GSK compound - possibly kinase inhibitor)",
        "indications": "Unknown (investigational)",
        "route": "Unknown (likely oral)",
        "clinical_phase": "Preclinical",
        "brca_subtype": "Unknown",
        "brca_rationale": "Target and MOA unknown. Predicted active by GDSC model based on molecular features.",
        "similar_approved": "N/A",
        "limitations": "No public data available. Target, MOA, toxicity unknown. High uncertainty."
    }
}

def load_physicochemical_properties():
    """Calculate physicochemical properties from SMILES using RDKit"""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, Crippen, MolSurf

    catalog = pd.read_parquet(DATA_DIR / "drug_info" / "drug_features_catalog.parquet")

    results = []
    for _, row in catalog.iterrows():
        smiles = row['canonical_smiles']
        drug_id = row['DRUG_ID']

        if pd.notna(smiles):
            try:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    mw = Descriptors.MolWt(mol)
                    logp = Crippen.MolLogP(mol)
                    hbd = Lipinski.NumHDonors(mol)
                    hba = Lipinski.NumHAcceptors(mol)
                    tpsa = MolSurf.TPSA(mol)

                    # Lipinski violations
                    violations = 0
                    if mw > 500:
                        violations += 1
                    if logp > 5:
                        violations += 1
                    if hbd > 5:
                        violations += 1
                    if hba > 10:
                        violations += 1

                    results.append({
                        'DRUG_ID': drug_id,
                        'MW': mw,
                        'LogP': logp,
                        'HBD': hbd,
                        'HBA': hba,
                        'TPSA': tpsa,
                        'Lipinski_violations': violations
                    })
            except:
                pass

    return pd.DataFrame(results)

def classify_cyp3a4(drug_name, admet_data):
    """Classify CYP3A4 inhibition based on ADMET data"""
    # Get CYP3A4 value from detailed assays
    drug_admet = admet_data[admet_data['drug_name'] == drug_name]
    cyp3a4_rows = drug_admet[drug_admet['assay_name'] == 'cyp3a4_veith']

    if len(cyp3a4_rows) > 0:
        val = cyp3a4_rows.iloc[0]['value']
        match_type = cyp3a4_rows.iloc[0]['match_type']

        if pd.notna(val):
            if val == 1.0:
                return "Strong inhibitor", "High"
            elif val == 0.0:
                return "Non-inhibitor", "Low"
            else:
                return "Weak inhibitor", "Medium"
        else:
            # No data - use similarity to infer
            if match_type in ('exact', 'close_analog'):
                return "Unknown (matched analog)", "Medium"
            else:
                return "Unknown (no data)", "Low"

    return "Unknown (no data)", "Low"

def get_toxicity_flags(drug_name, admet_data):
    """Get toxicity flags from ADMET data"""
    drug_admet = admet_data[admet_data['drug_name'] == drug_name]

    flags = {}

    # DILI
    dili = drug_admet[drug_admet['assay_name'] == 'dili']
    if len(dili) > 0 and pd.notna(dili.iloc[0]['value']):
        flags['DILI'] = "Yes" if dili.iloc[0]['value'] == 1.0 else "No"
    else:
        flags['DILI'] = "Unknown"

    # hERG
    herg = drug_admet[drug_admet['assay_name'] == 'herg']
    if len(herg) > 0 and pd.notna(herg.iloc[0]['value']):
        flags['hERG'] = "Yes" if herg.iloc[0]['value'] == 1.0 else "No"
    else:
        flags['hERG'] = "Unknown"

    # AMES
    ames = drug_admet[drug_admet['assay_name'] == 'ames']
    if len(ames) > 0 and pd.notna(ames.iloc[0]['value']):
        flags['AMES'] = "Yes" if ames.iloc[0]['value'] == 1.0 else "No"
    else:
        flags['AMES'] = "Unknown"

    return flags

def create_comprehensive_table():
    """Create comprehensive drug table with all information"""

    # Load base data
    top15 = pd.read_csv(STEP6_DIR / "ensemble_top15_detailed.csv")
    admet_summary = pd.read_csv(STEP7_DIR / "admet_summary.csv")
    admet_detailed = pd.read_csv(STEP7_DIR / "admet_detailed_assays.csv")
    physchem = load_physicochemical_properties()

    # Merge datasets
    df = top15.merge(admet_summary[['drug_name', 'safety_score', 'combined_score',
                                     'n_assays_tested', 'flags']],
                     on='drug_name', how='left')

    df = df.merge(physchem, left_on='canonical_id', right_on='DRUG_ID', how='left')

    # Build comprehensive table
    results = []

    for idx, row in df.iterrows():
        drug_name = row['drug_name']
        drug_info = DRUG_DATABASE.get(drug_name, {})

        # Get toxicity flags
        tox_flags = get_toxicity_flags(drug_name, admet_detailed)

        # Get CYP3A4 classification
        cyp3a4_class, ddi_risk = classify_cyp3a4(drug_name, admet_detailed)

        record = {
            # Basic info
            "약물명": drug_name,
            "Drug_ID": row['canonical_id'],
            "Target": row['target'],
            "MOA": drug_info.get('moa', 'Unknown'),
            "적응증": drug_info.get('indications', 'Unknown'),
            "FDA_승인": row['fda_approval'],
            "임상시험_단계": drug_info.get('clinical_phase', 'Unknown'),
            "투여방법": drug_info.get('route', 'Unknown'),

            # ADMET scores
            "ADMET_Safety_Score": row.get('safety_score', 0),
            "ADMET_Combined_Score": row.get('combined_score', 0),

            # Toxicity
            "DILI": tox_flags.get('DILI', 'Unknown'),
            "hERG": tox_flags.get('hERG', 'Unknown'),
            "AMES": tox_flags.get('AMES', 'Unknown'),

            # Drug interactions
            "CYP3A4_분류": cyp3a4_class,
            "DDI_위험도": ddi_risk,

            # Physicochemical
            "Lipinski_위반수": int(row.get('Lipinski_violations', 0)),
            "LogP": round(row.get('LogP', 0), 2),
            "분자량_MW": round(row.get('MW', 0), 1),
            "TPSA": round(row.get('TPSA', 0), 1),

            # Clinical evidence
            "ClinicalTrials_수": row.get('clinical_trials', 0),
            "PubMed_논문수": "N/A",  # Would need API call

            # Category
            "카테고리": row['category'],

            # Special notes
            "특이사항": drug_info.get('limitations', 'No specific notes'),
        }

        # Add recommendation rationale for categories 2 and 3
        if row['category'] in ('Other Cancer Approved/Clinical', 'New Candidate'):
            record["추천_이유"] = f"""
Target 중요성: {drug_info.get('brca_rationale', 'Data not available')}
적합 Subtype: {drug_info.get('brca_subtype', 'Unknown')}
유사 승인약: {drug_info.get('similar_approved', 'None')}
GDSC 순위: {idx+1}/15
METABRIC 결과: Step 6에서 검증됨 (Mock data로 인한 제한)
""".strip()

            record["한계사항"] = f"""
독성 이슈: DILI={tox_flags.get('DILI', 'Unknown')}, hERG={tox_flags.get('hERG', 'Unknown')}
약물 상호작용: CYP3A4 {cyp3a4_class} (DDI risk: {ddi_risk})
데이터 한계: ADMET assay matched: {row.get('n_assays_tested', 0)}/22
Distribution shift: GDSC vs METABRIC 발현 데이터 불일치
기타: {drug_info.get('limitations', 'None')}
""".strip()
        else:
            # Category 1 (BRCA Current Use) - no recommendation needed
            record["추천_이유"] = "검증용 약물 - 현재 유방암 치료에 사용 중"
            record["한계사항"] = "N/A (established therapy)"

        results.append(record)

    return pd.DataFrame(results)

def save_by_category(df):
    """Save tables by category"""

    categories = {
        "BRCA Current Use": "1_유방암_치료제",
        "Other Cancer Approved/Clinical": "2_유방암_연구중",
        "New Candidate": "3_유방암_미적용"
    }

    saved_files = []

    for cat_en, cat_ko in categories.items():
        cat_df = df[df['카테고리'] == cat_en].copy()

        if len(cat_df) > 0:
            # CSV
            csv_path = OUTPUT_DIR / f"{cat_ko}.csv"
            cat_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            saved_files.append(csv_path)
            print(f"✓ Saved: {csv_path} ({len(cat_df)} drugs)")

            # JSON
            json_path = OUTPUT_DIR / f"{cat_ko}.json"
            records = cat_df.to_dict('records')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            saved_files.append(json_path)
            print(f"✓ Saved: {json_path}")

    # Save combined table
    csv_all = OUTPUT_DIR / "전체_Top15_상세정보.csv"
    df.to_csv(csv_all, index=False, encoding='utf-8-sig')
    saved_files.append(csv_all)
    print(f"\n✓ Saved combined: {csv_all}")

    json_all = OUTPUT_DIR / "전체_Top15_상세정보.json"
    with open(json_all, 'w', encoding='utf-8') as f:
        json.dump(df.to_dict('records'), f, indent=2, ensure_ascii=False)
    saved_files.append(json_all)
    print(f"✓ Saved combined: {json_all}")

    return saved_files

def main():
    print("="*80)
    print("Top 15 약물 전체 상세 테이블 생성")
    print("="*80)

    # Create comprehensive table
    df = create_comprehensive_table()

    # Print summary
    print(f"\n총 {len(df)} 약물 처리 완료")
    print(f"\n카테고리 분포:")
    for cat, count in df['카테고리'].value_counts().items():
        print(f"  - {cat}: {count}개")

    # Save by category
    print(f"\n결과 저장 중...")
    files = save_by_category(df)

    print(f"\n" + "="*80)
    print(f"완료! {len(files)} 파일 생성됨")
    print(f"저장 위치: {OUTPUT_DIR}/")
    print("="*80)

    return df

if __name__ == "__main__":
    df = main()
