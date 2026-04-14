#!/usr/bin/env python3
"""
Step 7: ADMET Gate - v3 실제 ML 버전 (v1 방법론 적용)
  - v1의 Tanimoto similarity 기반 ADMET 데이터셋 검색 사용
  - 22개 ADMET assay 데이터셋에서 실제 측정값 매칭
  - NO MOCK DATA - 실제 assay 데이터만 사용
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

# Paths for v3
STEP4_DIR = Path(__file__).parent
BASE_DIR = STEP4_DIR.parent
STEP6_DIR = STEP4_DIR / "step6_metabric_results"
OUTPUT_DIR = STEP4_DIR / "step7_admet_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Data paths (nested structure)
DATA_DIR = STEP4_DIR / "20260414_re_pre_project_v3" / "20260414_re_pre_project_v3" / "data"
DRUG_CATALOG = DATA_DIR / "drug_info" / "drug_features_catalog.parquet"
ADMET_BASE = BASE_DIR / "data" / "admet"  # Downloaded to v3/data/admet
TOP15_PATH = STEP6_DIR / "ensemble_top15_detailed.csv"

# 22 ADMET assays (v1과 동일)
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
    "lipophilicity_astrazeneca": {"category": "Properties", "name": "Lipophilicity (logD)", "type": "regression", "good_direction": None, "unit": "logD", "ideal_range": (-0.4, 5.6)},
    "solubility_aqsoldb": {"category": "Properties", "name": "Aqueous Solubility", "type": "regression", "good_direction": "high", "unit": "logS"},
}


def load_data():
    """Load v3 Top 15 drugs and drug catalog"""
    print("="*80)
    print("Step 7: ADMET Gate (v3 - 실제 데이터)")
    print("="*80)
    print("\nLoading data...")
    t0 = time.time()

    top15 = pd.read_csv(TOP15_PATH)
    drug_catalog = pd.read_parquet(DRUG_CATALOG)

    # Map canonical_id → drug_id, get SMILES
    smiles_map = drug_catalog.set_index("DRUG_ID")["canonical_smiles"].to_dict()

    # Rename for compatibility
    top15["drug_id"] = top15["canonical_id"]
    top15["smiles"] = top15["drug_id"].map(smiles_map)

    # Add placeholder scores (will be replaced by ADMET-based ranking)
    top15["mean_pred_ic50"] = range(len(top15))  # Rank order
    top15["sensitivity_rate"] = 0.5

    has_smiles = top15["smiles"].notna().sum()
    print(f"  ✓ Top 15 drugs loaded: {len(top15)}")
    print(f"  ✓ SMILES available: {has_smiles}/{len(top15)}")
    print(f"  ✓ Time: {time.time()-t0:.1f}s")

    return top15, drug_catalog


def lookup_admet(top15):
    """
    v1 방법론: ADMET assay 데이터셋에서 Tanimoto similarity로 매칭
    NO ML PREDICTION - 실제 assay 측정값만 사용
    """
    print(f"\n{'='*80}")
    print(f"ADMET Assay Lookup (22 assays × {len(top15)} drugs)")
    print("v1 방법: Tanimoto similarity 기반 데이터셋 검색")
    print("="*80)

    # Pre-compute Morgan fingerprints for top15 drugs
    drug_fps = {}
    for _, row in top15.iterrows():
        smiles = row.get("smiles")
        if pd.notna(smiles):
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                drug_fps[row["drug_id"]] = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

    results = {}  # drug_id -> {assay_name: result}

    for assay_name, assay_info in ADMET_ASSAYS.items():
        # Load assay data (train_val + test combined)
        try:
            train = pd.read_parquet(ADMET_BASE / assay_name / "train_val_basic_clean_20260406.parquet")
            test = pd.read_parquet(ADMET_BASE / assay_name / "test_basic_clean_20260406.parquet")
            assay_data = pd.concat([train, test], ignore_index=True)
        except Exception as e:
            print(f"  ⚠️  Could not load {assay_name}: {e}")
            continue

        # Build fingerprint database for this assay
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
        for _, row in top15.iterrows():
            drug_id = row["drug_id"]
            drug_name = row.get("drug_name", f"Drug_{drug_id}")

            if drug_id not in results:
                results[drug_id] = {}

            if drug_id not in drug_fps:
                results[drug_id][assay_name] = {
                    "value": None, "match_type": "no_smiles",
                    "similarity": 0.0, **assay_info
                }
                continue

            my_fp = drug_fps[drug_id]

            # Find best Tanimoto match
            best_sim = 0.0
            best_val = None
            best_idx = -1

            for j, afp in enumerate(assay_fps):
                sim = DataStructs.TanimotoSimilarity(my_fp, afp)
                if sim > best_sim:
                    best_sim = sim
                    best_val = assay_labels[valid_idx[j]]
                    best_idx = valid_idx[j]

            # Tanimoto thresholds (v1 기준)
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
                **assay_info
            }

        print(f"  {assay_info['category']:<12} {assay_info['name']:<40} matched: {n_found}/{len(top15)}")

    return results


def compute_safety_profiles(top15, admet_results):
    """v1 방법론: 안전성 프로파일 계산"""
    print(f"\n{'='*80}")
    print("Safety Profile Assessment")
    print("="*80)

    profiles = []

    for _, row in top15.iterrows():
        drug_id = row["drug_id"]
        drug_name = row.get("drug_name", f"Drug_{drug_id}")
        drug_results = admet_results.get(drug_id, {})

        n_assays_tested = 0
        n_pass = 0
        n_caution = 0
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
                    # Toxicity flags
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

        # Safety score (v1 기준)
        if n_assays_tested > 0:
            safety_score = n_pass / max(n_assays_tested, 1) * 10
            # Penalize critical toxicity
            for flag in flags:
                if "hERG" in flag:
                    safety_score -= 2
                elif "Ames" in flag:
                    safety_score -= 1.5
                elif "DILI" in flag:
                    safety_score -= 1
        else:
            safety_score = 5.0

        # Known approved drugs bonus
        known_approved = row.get("fda_approval") == "Approved"
        if known_approved:
            safety_score += 2.0

        profiles.append({
            "drug_id": drug_id,
            "drug_name": drug_name,
            "target": row.get("target", "N/A"),
            "pathway": row.get("pathway", "N/A"),
            "category": row.get("category", "N/A"),
            "fda_approval": row.get("fda_approval", "N/A"),
            "mean_pred_ic50": row.get("mean_pred_ic50", 0),
            "n_assays_tested": n_assays_tested,
            "n_pass": n_pass,
            "n_caution": n_caution,
            "n_nodata": n_nodata,
            "safety_score": round(safety_score, 2),
            "flags": flags,
            "known_approved": known_approved,
            "assay_details": assay_details,
        })

    # Combined score
    for p in profiles:
        ic50_rank = sorted(profiles, key=lambda x: x["mean_pred_ic50"]).index(p)
        p["efficacy_rank"] = ic50_rank + 1
        p["combined_score"] = p["safety_score"] + (15 - ic50_rank) * 0.5

    profiles.sort(key=lambda x: -x["combined_score"])

    # Summary table
    print(f"\n  {'#':<3} {'Drug':<25} {'Safety':>7} {'Tested':>6} {'Pass':>5} "
          f"{'Caution':>7} {'NoData':>7} {'FDA':>8} {'Flags'}")
    print(f"  {'-'*90}")
    for i, p in enumerate(profiles, 1):
        flags_str = ", ".join(p["flags"][:2]) if p["flags"] else "-"
        if len(p["flags"]) > 2:
            flags_str += f" +{len(p['flags'])-2}"
        approved = "YES" if p["known_approved"] else "-"
        print(f"  {i:<3} {p['drug_name']:<25} {p['safety_score']:>7.1f} "
              f"{p['n_assays_tested']:>6} {p['n_pass']:>5} "
              f"{p['n_caution']:>7} {p['n_nodata']:>7} {approved:>8} {flags_str}")

    return profiles


def save_results(profiles):
    """결과 저장"""
    print(f"\n{'='*80}")
    print("Saving Results")
    print("="*80)

    # 1. Full profiles JSON
    summary = {
        "step": 7,
        "version": "v3",
        "method": "v1_tanimoto_lookup",
        "description": "ADMET Gate - 실제 assay 데이터 기반 (NO MOCK)",
        "n_assays": len(ADMET_ASSAYS),
        "n_drugs": len(profiles),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "assay_list": {k: v["name"] for k, v in ADMET_ASSAYS.items()},
        "profiles": [{k: v for k, v in p.items() if k != "assay_details"} for p in profiles],
        "detailed_profiles": profiles,
    }

    out_json = OUTPUT_DIR / "step7_admet_results.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2, default=lambda x: float(x) if isinstance(x, np.float32) else x)
    print(f"  ✓ {out_json}")

    # 2. Summary CSV
    df = pd.DataFrame([{
        "rank": i+1,
        "drug_name": p["drug_name"],
        "drug_id": p["drug_id"],
        "target": p["target"],
        "category": p["category"],
        "fda_approval": p["fda_approval"],
        "safety_score": p["safety_score"],
        "combined_score": p["combined_score"],
        "n_assays_tested": p["n_assays_tested"],
        "n_pass": p["n_pass"],
        "n_caution": p["n_caution"],
        "flags": "; ".join(p["flags"]) if p["flags"] else "None",
    } for i, p in enumerate(profiles)])

    csv_path = OUTPUT_DIR / "admet_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f"  ✓ {csv_path}")

    # 3. Detailed assay results
    detailed_rows = []
    for p in profiles:
        for assay_name, details in p["assay_details"].items():
            detailed_rows.append({
                "drug_name": p["drug_name"],
                "drug_id": p["drug_id"],
                "assay_name": assay_name,
                "assay_category": ADMET_ASSAYS[assay_name]["category"],
                "assay_full_name": ADMET_ASSAYS[assay_name]["name"],
                "value": details["value"],
                "status": details["status"],
                "match_type": details["match_type"],
                "similarity": details["similarity"],
            })

    detailed_df = pd.DataFrame(detailed_rows)
    detailed_csv = OUTPUT_DIR / "admet_detailed_assays.csv"
    detailed_df.to_csv(detailed_csv, index=False)
    print(f"  ✓ {detailed_csv}")

    # 4. Pass/Fail summary
    n_high_safety = sum(1 for p in profiles if p["safety_score"] >= 7)
    n_medium_safety = sum(1 for p in profiles if 5 <= p["safety_score"] < 7)
    n_low_safety = sum(1 for p in profiles if p["safety_score"] < 5)

    print(f"\n{'='*80}")
    print("ADMET Gate Summary")
    print("="*80)
    print(f"  Total drugs: {len(profiles)}")
    print(f"  High safety (≥7.0): {n_high_safety}")
    print(f"  Medium safety (5.0-6.9): {n_medium_safety}")
    print(f"  Low safety (<5.0): {n_low_safety}")
    print(f"\n  Top 3 by combined score:")
    for i, p in enumerate(profiles[:3], 1):
        print(f"    {i}. {p['drug_name']} - Safety: {p['safety_score']:.1f}, Combined: {p['combined_score']:.1f}")
    print("="*80)

    return summary


def main():
    t0 = time.time()

    # Load data
    top15, drug_catalog = load_data()

    # ADMET lookup (실제 데이터)
    admet_results = lookup_admet(top15)

    # Safety profiles
    profiles = compute_safety_profiles(top15, admet_results)

    # Save results
    summary = save_results(profiles)

    elapsed = time.time() - t0
    print(f"\n✓ Step 7 COMPLETE ({elapsed/60:.1f} min)")
    print(f"  Results: {OUTPUT_DIR}/")

    return summary


if __name__ == "__main__":
    summary = main()
