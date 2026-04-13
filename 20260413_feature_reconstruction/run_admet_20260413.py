#!/usr/bin/env python3
"""
Step 2: ADMET 재검증 (Top 30 Dedup 기반)
═══════════════════════════════════════════════════════════════
  - 입력: top30_dedup_20260413.csv (28개)
  - 22개 ADMET assay Tanimoto 매칭
  - 카테고리별 해석:
      A (Known BRCA): 독성 있어도 허용 (이미 임상 사용)
      B (BRCA 연구):  독성 있으면 주의 (추가 연구 필요)
      C (완전 재창출): 독성 있으면 탈락 (신규 적응증)
  - Epirubicin 심장독성 별도 표시
  - 기반: models/run_step7_admet.py 로직
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import time
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import DataStructs, AllChem

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"

DRUG_CATALOG = f"{S3_BASE}/data/drug_features_catalog.parquet"
ADMET_BASE = f"{S3_BASE}/data/admet"
DRUG_ANN = f"{S3_BASE}/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet"

INPUT_CSV = PROJECT_ROOT / "results" / "top30_dedup_20260413" / "top30_dedup_20260413.csv"
OUTPUT_DIR = PROJECT_ROOT / "results" / "admet_results_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 약물 카테고리 분류 ──
# A: Known BRCA drugs (FDA 승인 또는 NCCN 가이드라인 포함)
CATEGORY_A_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
    "Dactinomycin", "Epirubicin", "Topotecan", "Irinotecan",
    "Rapamycin", "Fulvestrant", "Methotrexate",
}

# C: Pure repurposing (원래 적응증이 BRCA 무관)
CATEGORY_C_DRUGS = {
    "Avagacestat",  # Alzheimer's → Notch pathway
    "Tozasertib",   # Leukemia → Aurora kinase
}

# B: 나머지 (BRCA 연구/전임상 근거 있음)

# ── Epirubicin 심장독성 특별 플래그 ──
EPIRUBICIN_CARDIOTOX_NOTE = (
    "Epirubicin: 알려진 심장독성 (anthracycline). "
    "누적용량 의존적 심근병증 위험. "
    "LVEF 모니터링 필수, 누적용량 900mg/m² 초과 금지."
)

# ── 22 ADMET Assays ──
ADMET_ASSAYS = {
    # Absorption
    "caco2_wang":       {"category": "Absorption", "name": "Caco-2 Permeability", "type": "regression", "good_direction": "high", "unit": "log(cm/s)", "threshold": -5.15},
    "hia_hou":          {"category": "Absorption", "name": "HIA (Human Intestinal Absorption)", "type": "binary", "good_value": 1},
    "pgp_broccatelli":  {"category": "Absorption", "name": "P-gp Inhibitor", "type": "binary", "good_value": 0},
    "bioavailability_ma": {"category": "Absorption", "name": "Oral Bioavailability (F>20%)", "type": "binary", "good_value": 1},
    # Distribution
    "bbb_martins":      {"category": "Distribution", "name": "BBB Penetration", "type": "binary", "good_value": None},
    "ppbr_az":          {"category": "Distribution", "name": "Plasma Protein Binding Rate", "type": "regression", "good_direction": "low", "unit": "%", "threshold": 90},
    "vdss_lombardo":    {"category": "Distribution", "name": "Volume of Distribution", "type": "regression", "good_direction": None, "unit": "L/kg"},
    # Metabolism
    "cyp2c9_veith":     {"category": "Metabolism", "name": "CYP2C9 Inhibitor", "type": "binary", "good_value": 0},
    "cyp2d6_veith":     {"category": "Metabolism", "name": "CYP2D6 Inhibitor", "type": "binary", "good_value": 0},
    "cyp3a4_veith":     {"category": "Metabolism", "name": "CYP3A4 Inhibitor", "type": "binary", "good_value": 0},
    "cyp2c9_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2C9 Substrate", "type": "binary", "good_value": None},
    "cyp2d6_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2D6 Substrate", "type": "binary", "good_value": None},
    "cyp3a4_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP3A4 Substrate", "type": "binary", "good_value": None},
    # Excretion
    "clearance_hepatocyte_az": {"category": "Excretion", "name": "Hepatocyte Clearance", "type": "regression", "good_direction": None, "unit": "uL/min/10^6 cells"},
    "clearance_microsome_az":  {"category": "Excretion", "name": "Microsome Clearance", "type": "regression", "good_direction": None, "unit": "mL/min/g"},
    "half_life_obach":  {"category": "Excretion", "name": "Half-Life", "type": "regression", "good_direction": "high", "unit": "hr", "threshold": 3},
    # Toxicity
    "ames":             {"category": "Toxicity", "name": "Ames Mutagenicity", "type": "binary", "good_value": 0},
    "dili":             {"category": "Toxicity", "name": "DILI (Drug-Induced Liver Injury)", "type": "binary", "good_value": 0},
    "herg":             {"category": "Toxicity", "name": "hERG Cardiotoxicity", "type": "binary", "good_value": 0},
    "ld50_zhu":         {"category": "Toxicity", "name": "Acute Toxicity (LD50)", "type": "regression", "good_direction": "high", "unit": "log(mol/kg)"},
    # Properties
    "lipophilicity_astrazeneca": {"category": "Properties", "name": "Lipophilicity (logD)", "type": "regression", "good_direction": None, "unit": "logD", "ideal_range": (-0.4, 5.6)},
    "solubility_aqsoldb": {"category": "Properties", "name": "Aqueous Solubility", "type": "regression", "good_direction": "high", "unit": "logS"},
}


def get_drug_category(drug_name):
    """약물 카테고리 반환: A/B/C"""
    if drug_name in CATEGORY_A_DRUGS:
        return "A"
    elif drug_name in CATEGORY_C_DRUGS:
        return "C"
    else:
        return "B"


def load_data():
    """입력 데이터 및 SMILES 매핑."""
    print("  Loading data...")
    t0 = time.time()

    drugs = pd.read_csv(INPUT_CSV)
    drugs["canonical_drug_id"] = drugs["canonical_drug_id"].astype(int)
    print(f"    Input drugs: {len(drugs)}")

    drug_catalog = pd.read_parquet(DRUG_CATALOG)
    drug_ann = pd.read_parquet(DRUG_ANN)

    # SMILES 매핑
    smiles_map = drug_catalog.set_index("DRUG_ID")["canonical_smiles"].to_dict()
    drugs["smiles"] = drugs["canonical_drug_id"].map(smiles_map)

    has_smiles = drugs["smiles"].notna().sum()
    print(f"    SMILES 매핑: {has_smiles}/{len(drugs)}")

    # 카테고리 분류
    drugs["category"] = drugs["drug_name"].map(get_drug_category)
    cat_counts = drugs["category"].value_counts().sort_index()
    for cat, cnt in cat_counts.items():
        label = {"A": "Known BRCA", "B": "BRCA 연구", "C": "완전 재창출"}[cat]
        print(f"    Category {cat} ({label}): {cnt}")

    print(f"    ({time.time()-t0:.1f}s)")
    return drugs, drug_catalog


def lookup_admet(drugs):
    """22개 ADMET assay에 대해 Tanimoto 매칭."""
    print(f"\n{'='*70}")
    print(f"  ADMET Assay Lookup (22 assays x {len(drugs)} drugs)")
    print(f"{'='*70}")

    # Morgan fingerprint 사전 계산
    drug_fps = {}
    for _, row in drugs.iterrows():
        smiles = row.get("smiles")
        if pd.notna(smiles):
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                drug_fps[row["canonical_drug_id"]] = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

    print(f"  Valid fingerprints: {len(drug_fps)}/{len(drugs)}")

    results = {}  # drug_id -> {assay_name: result}

    for assay_name, assay_info in ADMET_ASSAYS.items():
        try:
            train = pd.read_parquet(f"{ADMET_BASE}/{assay_name}/train_val_basic_clean_20260406.parquet")
            test = pd.read_parquet(f"{ADMET_BASE}/{assay_name}/test_basic_clean_20260406.parquet")
            assay_data = pd.concat([train, test], ignore_index=True)
        except Exception as e:
            print(f"  WARNING: {assay_name} 로드 실패: {e}")
            continue

        # Assay fingerprint DB 구축
        assay_smiles = assay_data["Drug"].values
        assay_labels = assay_data["Y"].values
        assay_fps = []
        valid_idx = []
        for i, smi in enumerate(assay_smiles):
            mol = Chem.MolFromSmiles(smi)
            if mol:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                assay_fps.append(fp)
                valid_idx.append(i)

        n_found = 0
        for _, row in drugs.iterrows():
            drug_id = row["canonical_drug_id"]
            if drug_id not in results:
                results[drug_id] = {}

            if drug_id not in drug_fps:
                results[drug_id][assay_name] = {
                    "value": None, "match_type": "no_smiles",
                    "similarity": 0.0, **assay_info,
                }
                continue

            my_fp = drug_fps[drug_id]
            best_sim = 0.0
            best_val = None

            for j, afp in enumerate(assay_fps):
                sim = DataStructs.TanimotoSimilarity(my_fp, afp)
                if sim > best_sim:
                    best_sim = sim
                    best_val = assay_labels[valid_idx[j]]

            if best_sim >= 0.99:
                match_type = "exact"
                n_found += 1
            elif best_sim >= 0.85:
                match_type = "close_analog"
                n_found += 1
            elif best_sim >= 0.70:
                match_type = "analog"
            else:
                match_type = "no_match"
                best_val = None

            results[drug_id][assay_name] = {
                "value": float(best_val) if best_val is not None else None,
                "match_type": match_type,
                "similarity": float(best_sim),
                **assay_info,
            }

        print(f"  {assay_info['category']:<12} {assay_info['name']:<35} matched: {n_found}/{len(drugs)}")

    return results


def compute_safety_profiles(drugs, admet_results):
    """Safety profile 산출 + 카테고리별 해석."""
    print(f"\n{'='*70}")
    print(f"  Safety Profile Assessment (카테고리별 해석 포함)")
    print(f"{'='*70}")

    profiles = []

    for _, row in drugs.iterrows():
        drug_id = row["canonical_drug_id"]
        drug_name = row.get("drug_name", f"Drug_{drug_id}")
        category = row.get("category", "B")
        drug_results = admet_results.get(drug_id, {})

        n_assays_tested = 0
        n_pass = 0
        n_caution = 0
        n_fail = 0
        n_nodata = 0
        flags = []
        assay_details = {}

        for assay_name, assay_info in ADMET_ASSAYS.items():
            r = drug_results.get(assay_name, {})
            val = r.get("value")
            match = r.get("match_type", "no_match")

            if val is None or match in ("no_match", "no_smiles"):
                status = "no_data"
                n_nodata += 1
            elif assay_info["type"] == "binary":
                n_assays_tested += 1
                good_val = assay_info.get("good_value")
                if good_val is None:
                    status = "info"
                elif int(val) == good_val:
                    status = "pass"
                    n_pass += 1
                else:
                    if assay_name in ("ames", "dili", "herg"):
                        status = "caution"
                        n_caution += 1
                        flags.append(f"{assay_info['name']}(+)")
                    else:
                        status = "minor"
                        n_caution += 1
            else:
                n_assays_tested += 1
                status = "measured"
                n_pass += 1

            assay_details[assay_name] = {
                "value": val,
                "status": status,
                "match_type": match,
                "similarity": r.get("similarity", 0),
            }

        # Safety score 계산 (0-12, 높을수록 안전)
        if n_assays_tested > 0:
            safety_score = n_pass / max(n_assays_tested, 1) * 10
            for flag in flags:
                if "hERG" in flag:
                    safety_score -= 2
                elif "Ames" in flag:
                    safety_score -= 1.5
                elif "DILI" in flag:
                    safety_score -= 1
        else:
            safety_score = 5.0

        # Known approved drug 보너스
        known_approved = drug_name in {
            "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
            "Rapamycin", "Dactinomycin", "Epirubicin", "Topotecan",
            "Irinotecan", "Fulvestrant", "Methotrexate",
        }
        if known_approved:
            safety_score += 2.0

        # ── 카테고리별 해석 ──
        if category == "A":
            # Known BRCA: 독성 있어도 허용 (이미 임상 사용 중)
            if flags:
                tox_interpretation = f"허용 (기승인 약물, 관리 가능한 독성: {', '.join(flags)})"
            else:
                tox_interpretation = "양호 (기승인 약물, 주요 독성 플래그 없음)"
            admet_decision = "PASS"
        elif category == "B":
            # BRCA 연구: 독성 있으면 주의
            critical_flags = [f for f in flags if "hERG" in f or "Ames" in f]
            if critical_flags:
                tox_interpretation = f"주의 (연구 약물, 중대 독성: {', '.join(critical_flags)})"
                admet_decision = "CAUTION"
            elif flags:
                tox_interpretation = f"조건부 허용 (경미한 독성: {', '.join(flags)})"
                admet_decision = "CONDITIONAL"
            else:
                tox_interpretation = "양호 (주요 독성 플래그 없음)"
                admet_decision = "PASS"
        else:  # category == "C"
            # 완전 재창출: 독성 있으면 탈락
            if flags:
                tox_interpretation = f"탈락 (신규 적응증, 독성 불허: {', '.join(flags)})"
                admet_decision = "FAIL"
            else:
                tox_interpretation = "통과 (신규 적응증, 주요 독성 없음)"
                admet_decision = "PASS"

        # ── Epirubicin 심장독성 별도 표시 ──
        epirubicin_note = None
        if drug_name == "Epirubicin":
            epirubicin_note = EPIRUBICIN_CARDIOTOX_NOTE
            # hERG assay 외에도 임상적 심장독성 명시
            if "hERG Cardiotoxicity(+)" not in flags:
                flags.append("Clinical Cardiotoxicity (anthracycline)")
            tox_interpretation = (
                "허용 (기승인 약물이나 심장독성 주의). "
                "anthracycline 계열 누적용량 의존적 심근병증 위험. "
                "LVEF 모니터링 필수."
            )

        profiles.append({
            "drug_id": drug_id,
            "drug_name": drug_name,
            "category": category,
            "target": row.get("target", "N/A"),
            "pathway": row.get("pathway", "N/A"),
            "mean_pred_ic50": row.get("mean_pred_ic50", 0),
            "sensitivity_rate": row.get("sensitivity_rate", 0),
            "rank": int(row.get("rank", 0)),
            "n_assays_tested": n_assays_tested,
            "n_pass": n_pass,
            "n_caution": n_caution,
            "n_nodata": n_nodata,
            "safety_score": round(safety_score, 2),
            "flags": flags,
            "known_approved": known_approved,
            "tox_interpretation": tox_interpretation,
            "admet_decision": admet_decision,
            "epirubicin_note": epirubicin_note,
            "assay_details": assay_details,
        })

    # Combined score: safety + efficacy rank
    for p in profiles:
        ic50_rank = sorted(profiles, key=lambda x: x["mean_pred_ic50"]).index(p)
        p["efficacy_rank"] = ic50_rank + 1
        p["combined_score"] = p["safety_score"] + (len(profiles) - ic50_rank) * 0.5

    profiles.sort(key=lambda x: -x["combined_score"])

    # ── 요약 출력 ──
    print(f"\n  {'#':<3} {'Cat':>3} {'Drug':<22} {'IC50':>7} {'Safe':>5} "
          f"{'Pass':>5} {'Caut':>5} {'Decision':<12} {'Flags'}")
    print(f"  {'-'*95}")
    for i, p in enumerate(profiles, 1):
        flags_str = ", ".join(p["flags"]) if p["flags"] else "-"
        print(f"  {i:<3} {p['category']:>3} {p['drug_name']:<22} "
              f"{p['mean_pred_ic50']:>7.3f} {p['safety_score']:>5.1f} "
              f"{p['n_pass']:>5} {p['n_caution']:>5} "
              f"{p['admet_decision']:<12} {flags_str}")

    # ── 카테고리별 요약 ──
    print(f"\n  카테고리별 ADMET 요약:")
    for cat in ["A", "B", "C"]:
        cat_drugs = [p for p in profiles if p["category"] == cat]
        if not cat_drugs:
            continue
        label = {"A": "Known BRCA", "B": "BRCA 연구", "C": "완전 재창출"}[cat]
        n_pass = sum(1 for p in cat_drugs if p["admet_decision"] == "PASS")
        n_cond = sum(1 for p in cat_drugs if p["admet_decision"] == "CONDITIONAL")
        n_caut = sum(1 for p in cat_drugs if p["admet_decision"] == "CAUTION")
        n_fail = sum(1 for p in cat_drugs if p["admet_decision"] == "FAIL")
        print(f"    {cat} ({label}): {len(cat_drugs)}개 → "
              f"PASS={n_pass}, CONDITIONAL={n_cond}, CAUTION={n_caut}, FAIL={n_fail}")

    # ── Epirubicin 별도 표시 ──
    epi = [p for p in profiles if p["drug_name"] == "Epirubicin"]
    if epi:
        print(f"\n  {'='*70}")
        print(f"  [특별 표시] {EPIRUBICIN_CARDIOTOX_NOTE}")
        print(f"  {'='*70}")

    return profiles


def save_results(profiles):
    """결과 저장."""
    # ── JSON ──
    def convert(obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64, np.bool_)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    # 상세 결과 (assay_details 포함)
    json_path = OUTPUT_DIR / "admet_results_20260413.json"
    summary = {
        "description": "ADMET 재검증 결과 (Top 30 dedup 기반, 카테고리별 해석)",
        "n_assays": len(ADMET_ASSAYS),
        "n_drugs": len(profiles),
        "category_interpretation": {
            "A": "Known BRCA: 독성 있어도 허용 (이미 임상 사용)",
            "B": "BRCA 연구: 독성 있으면 주의 (추가 연구 필요)",
            "C": "완전 재창출: 독성 있으면 탈락 (신규 적응증)",
        },
        "epirubicin_note": EPIRUBICIN_CARDIOTOX_NOTE,
        "profiles": profiles,
        "assay_list": {k: v["name"] for k, v in ADMET_ASSAYS.items()},
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=convert, ensure_ascii=False)
    print(f"\n  Saved JSON: {json_path}")

    # ── CSV (요약) ──
    csv_rows = []
    for p in profiles:
        csv_rows.append({
            "rank": p["rank"],
            "drug_id": p["drug_id"],
            "drug_name": p["drug_name"],
            "category": p["category"],
            "target": p["target"],
            "pathway": p["pathway"],
            "mean_pred_ic50": p["mean_pred_ic50"],
            "safety_score": p["safety_score"],
            "n_assays_tested": p["n_assays_tested"],
            "n_pass": p["n_pass"],
            "n_caution": p["n_caution"],
            "n_nodata": p["n_nodata"],
            "admet_decision": p["admet_decision"],
            "flags": "; ".join(p["flags"]) if p["flags"] else "",
            "tox_interpretation": p["tox_interpretation"],
            "combined_score": p["combined_score"],
        })

    csv_df = pd.DataFrame(csv_rows)
    csv_path = OUTPUT_DIR / "admet_summary_20260413.csv"
    csv_df.to_csv(csv_path, index=False)
    print(f"  Saved CSV: {csv_path}")
    print(f"    Rows: {len(csv_df)}, Decision 분포: {csv_df['admet_decision'].value_counts().to_dict()}")


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Step 2: ADMET 재검증 (Top 30 Dedup 기반)")
    print("=" * 70)

    drugs, drug_catalog = load_data()
    admet_results = lookup_admet(drugs)
    profiles = compute_safety_profiles(drugs, admet_results)
    save_results(profiles)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  ADMET 재검증 완료 ({elapsed/60:.1f} min)")
    print(f"  {len(profiles)}개 약물 프로파일 생성")

    n_pass = sum(1 for p in profiles if p["admet_decision"] == "PASS")
    n_cond = sum(1 for p in profiles if p["admet_decision"] == "CONDITIONAL")
    n_caut = sum(1 for p in profiles if p["admet_decision"] == "CAUTION")
    n_fail = sum(1 for p in profiles if p["admet_decision"] == "FAIL")
    print(f"  PASS={n_pass}, CONDITIONAL={n_cond}, CAUTION={n_caut}, FAIL={n_fail}")
    print("=" * 70)


if __name__ == "__main__":
    main()
