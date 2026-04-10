#!/usr/bin/env python3
"""
MultiModalFusionNet Inference — 신규 SMILES → 7-허들 약물 재창출 평가

사용법:
  python inference.py --smiles "CC(=O)Oc1ccccc1C(=O)O"
  python inference.py --smiles "CCO" "c1ccccc1" "CC(=O)Oc1ccccc1C(=O)O"
  python inference.py --smiles_file input_smiles.txt

허들 파이프라인:
  1. IC50 예측        (High/Medium/Low)
  2. ADMET Lipinski   (PASS/FAIL)
  3. Tanimoto 유사도  (PASS/WARNING/FAIL)
  4. 유방암 타겟 필터 (PASS/UNKNOWN)
  5. AlphaFold 도킹   (stub → UNKNOWN)
  6. 내성 변이 경고   (stub → WARNING/UNKNOWN)
  7. LLM-RAG 임상 근거 (미구현 → UNKNOWN)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors, DataStructs
RDLogger.logger().setLevel(RDLogger.ERROR)

from multimodal_fusion import MultiModalFusionNet, DATA_PATHS, MODALITY_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
MODEL_PATH = RESULTS_DIR / "best_multimodal_model.pt"

S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
ADMET_BASE = f"{S3_BASE}/data/admet"

DEVICE = torch.device("mps" if torch.backends.mps.is_available()
                       else "cuda" if torch.cuda.is_available() else "cpu")

# drug_desc 컬럼 순서 (학습과 동일)
DRUG_DESC_NAMES = [
    "drug_desc_frac_csp3",
    "drug_desc_hba",
    "drug_desc_hbd",
    "drug_desc_heavy_atoms",
    "drug_desc_logp",
    "drug_desc_mol_wt",
    "drug_desc_ring_count",
    "drug_desc_rot_bonds",
    "drug_desc_tpsa",
]


# ═══════════════════════════════════════════════════════════════════
# 허들 3: FDA 승인 유방암 치료제 SMILES (Tanimoto 비교용)
# ═══════════════════════════════════════════════════════════════════

FDA_BRCA_DRUGS = {
    # ── 기존 5개 (PubChem Canonical SMILES) ──
    "Tamoxifen":    "CCC(=C(c1ccccc1)c1ccc(OCCN(C)C)cc1)c1ccccc1",
    "Fulvestrant":  "CC12CCC3c4ccc(O)cc4CCC3C1CCC2CCCCCCCCCS(=O)CCCCF",
    "Lapatinib":    "CS(=O)(=O)CCNCc1ccc(-c2ccc3ncnc(Nc4ccc(OCc5cccc(F)c5)c(Cl)c4)c3c2)o1",
    "Palbociclib":  "CC(=O)c1c(C)c2cnc(Nc3ccc(N4CCNCC4)cn3)nc2n1C1CCCC1",
    "Olaparib":     "O=C1CCC(=O)N1Cc1ccc2c(c1)CC(=O)N2CC1CC1",
    # ── 추가 6개 (유방암 치료제 확대) ──
    "Cabazitaxel":  "CC(=O)O[C@@]12CO[C@@H]1C[C@H](OC)[C@@]1(C)C(=O)[C@H](OC)C3=C(C)[C@@H](OC(=O)[C@H](O)[C@@H](NC(=O)OC(C)(C)C)c4ccccc4)C[C@@](O)([C@@H](OC(=O)c4ccccc4)[C@H]21)C3(C)C",
    "Doxorubicin":  "COc1cccc2c1C(=O)c1c(O)c3c(c(O)c1C2=O)C[C@@](O)(C(=O)CO)C[C@@H]3O[C@H]1C[C@@H](N)[C@H](O)[C@@H](C)O1",
    "Ribociclib":   "CN1CCN(Cc2ccc3nc(Nc4ccc(CN5CCCC5=O)cn4)ncc3c2)CC1",
    "Abemaciclib":  "CCc1cn(C2CCNCC2)c2ncc(F)c(Nc3cc4c(cn3)N(C)C(=O)C4)c12",
    "Talazoparib":  "O=C1NCCc2cc3c(cc21)[nH]nc3-c1cnnc(N)n1",
    "Everolimus":   "C[C@@H]1CC[C@H]2C[C@@H](/C(=C/C=C/C=C/[C@H](C[C@H](C(=O)[C@@H]([C@@H](/C(=C/[C@H](C(=O)C[C@H](OC(=O)[C@@H]3CCCCN3C(=O)C(=O)[C@@]1(O2)O)[C@H](C)C[C@@H]4CC[C@H]([C@@H](C4)OC)OCCO)C)/C)O)OC)C)C)/C)OC",
}


# ═══════════════════════════════════════════════════════════════════
# 허들 4: 유방암 핵심 타겟 유전자
# ═══════════════════════════════════════════════════════════════════

BRCA_CORE_TARGETS = [
    "BRCA1", "BRCA2", "HER2", "ESR1", "PGR",
    "PIK3CA", "AKT1", "PTEN", "CDK4", "CDK6",
    "CCND1", "TP53", "MYC", "EGFR",
]

# +A 후보 (신규 연구에 따라 추가 가능)
# PALB2, ATM, FGFR1, FGFR2, RAD51, RB1
# 확장 가능한 리스트 구조로 설계

# HER2 alias 매핑 (데이터에서 ERBB2로 표기되는 경우)
TARGET_ALIASES = {"HER2": "ERBB2", "ERBB2": "HER2"}

# drug_target_mapping S3 경로
DRUG_TARGET_URI = (
    "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"
    "/fe_output/20260408_fe_v1/pair_features/drug_target_mapping.parquet"
)


# ═══════════════════════════════════════════════════════════════════
# 허들 6: 알려진 내성 변이 DB
# ═══════════════════════════════════════════════════════════════════

KNOWN_RESISTANCE_MUTATIONS = {
    "ESR1":   ["Y537S", "D538G", "E380Q"],
    "HER2":   ["T798I", "L869R"],
    "PIK3CA": ["H1047R", "E545K", "E542K"],
    "PTEN":   ["loss_of_function"],
}
# 향후 구현 방향:
# 1. 환자 WGS 데이터 연동
# 2. 변이형 AlphaFold 구조 예측
# 3. 야생형 vs 변이형 도킹 비교
# 4. 내성 발생 시점 예측 모델


# ═══════════════════════════════════════════════════════════════════
# 1. Feature Generation (허들 1-2)
# ═══════════════════════════════════════════════════════════════════

def smiles_to_morgan(smiles: str, radius: int = 2, nbits: int = 2048) -> np.ndarray:
    """SMILES → Morgan FP 2048-bit numpy array."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=radius, nBits=nbits)
    arr = np.zeros(nbits, dtype=np.float32)
    for i in fp.GetOnBits():
        arr[i] = 1.0
    return arr


def smiles_to_descriptors(smiles: str) -> dict:
    """SMILES → RDKit molecular descriptors (9개)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "drug_desc_mol_wt": Descriptors.MolWt(mol),
        "drug_desc_logp": Descriptors.MolLogP(mol),
        "drug_desc_tpsa": Descriptors.TPSA(mol),
        "drug_desc_hbd": Descriptors.NumHDonors(mol),
        "drug_desc_hba": Descriptors.NumHAcceptors(mol),
        "drug_desc_rot_bonds": Descriptors.NumRotatableBonds(mol),
        "drug_desc_ring_count": Descriptors.RingCount(mol),
        "drug_desc_heavy_atoms": Descriptors.HeavyAtomCount(mol),
        "drug_desc_frac_csp3": Descriptors.FractionCSP3(mol),
    }


def get_crispr_mean() -> np.ndarray:
    """학습 데이터에서 CRISPR 평균값 계산 (유방암 세포주 대표값)."""
    cache_path = RESULTS_DIR / "crispr_mean.npy"
    if cache_path.exists():
        return np.load(cache_path)

    print("  CRISPR 평균값 계산 중 (최초 1회)...")
    features = pd.read_parquet(DATA_PATHS["features"])
    crispr_cols = sorted([c for c in features.columns if c.startswith("sample__crispr__")])
    crispr_mean = features[crispr_cols].mean().values.astype(np.float32)
    np.save(cache_path, crispr_mean)
    print(f"  캐시 저장: {cache_path}")
    return crispr_mean


# ═══════════════════════════════════════════════════════════════════
# 허들 2A: Lipinski ADMET (투여 경로 고려)
# ═══════════════════════════════════════════════════════════════════

# IV 가능성 높은 항암 pathway (NCCN 기준)
IV_LIKELY_PATHWAYS = {
    "Mitosis", "Apoptosis regulation", "DNA replication",
    "Protein stability and degradation", "Chromatin histone acetylation",
    "Cell cycle", "RTK signaling", "Other",
}

_drug_ann_cache = None

def _load_drug_annotation():
    """drug annotation 로드 (1회 캐시)."""
    global _drug_ann_cache
    if _drug_ann_cache is not None:
        return _drug_ann_cache
    try:
        ann = pd.read_parquet(
            f"{S3_BASE}/data/gsdc/gdsc2_drug_annotation_master_20260406.parquet")
        _drug_ann_cache = ann
        return ann
    except Exception:
        return None


def infer_route(smiles: str, desc: dict) -> str:
    """투여 경로 자동 판단.

    PO: 경구 (Lipinski 엄격 적용)
    IV: 정맥주사 (Lipinski → WARNING으로 완화)
    UNKNOWN: 판단 불가 (WARNING으로 처리)

    판단 기준:
    - MW > 500 이면서 항암 pathway → IV 가능성
    - drug_annotation에서 pathway 참조
    """
    mw = desc["drug_desc_mol_wt"]

    # MW ≤ 500 이면 경구 가능성 높음
    if mw <= 500:
        return "PO"

    # MW > 500: 항암 pathway 확인
    ann = _load_drug_annotation()
    if ann is not None:
        smiles_match = None
        catalog_path = f"{S3_BASE}/data/drug_features_catalog.parquet"
        try:
            catalog = pd.read_parquet(catalog_path)
            matched = catalog[catalog["canonical_smiles"] == smiles]
            if not matched.empty:
                drug_id = matched.iloc[0]["DRUG_ID"]
                ann_row = ann[ann["DRUG_ID"] == drug_id]
                if not ann_row.empty:
                    pathway = str(ann_row.iloc[0].get("PATHWAY_NAME_NORMALIZED", ""))
                    if pathway in IV_LIKELY_PATHWAYS:
                        return "IV"
        except Exception:
            pass

    # MW > 500이면 IV 가능성 높음 (항암제 대부분)
    if mw > 700:
        return "IV"

    return "UNKNOWN"


def lipinski_filter(desc: dict, route: str = "PO") -> dict:
    """Lipinski Rule of Five + 투여 경로 고려.

    route:
        PO: 엄격 적용 (PASS/FAIL)
        IV: violations → WARNING (FAIL 아님)
        UNKNOWN: WARNING으로 처리
    """
    mw = desc["drug_desc_mol_wt"]
    logp = desc["drug_desc_logp"]
    hbd = desc["drug_desc_hbd"]
    hba = desc["drug_desc_hba"]
    tpsa = desc["drug_desc_tpsa"]

    violations = 0
    details = {}

    details["MW_ok"] = mw <= 500
    if not details["MW_ok"]:
        violations += 1
    details["LogP_ok"] = logp <= 5
    if not details["LogP_ok"]:
        violations += 1
    details["HBD_ok"] = hbd <= 5
    if not details["HBD_ok"]:
        violations += 1
    details["HBA_ok"] = hba <= 10
    if not details["HBA_ok"]:
        violations += 1

    details["TPSA_ok"] = tpsa <= 140
    details["violations"] = violations
    details["route"] = route
    details["oral_absorption"] = "Good" if tpsa <= 140 else "Poor"

    # 투여 경로별 판정
    if route == "PO":
        details["lipinski_pass"] = violations <= 1
        details["verdict"] = "PASS" if violations <= 1 else "FAIL"
    elif route == "IV":
        # IV 약물: Lipinski 위반은 WARNING (FAIL 아님)
        details["lipinski_pass"] = True  # IV 투여이므로 경구 흡수 무관
        details["verdict"] = "PASS" if violations <= 1 else "WARNING"
    else:  # UNKNOWN
        details["lipinski_pass"] = violations <= 1
        details["verdict"] = "PASS" if violations <= 1 else "WARNING"

    return details


# ═══════════════════════════════════════════════════════════════════
# 허들 2B: 22-assay ADMET (Step 7 통합)
# ═══════════════════════════════════════════════════════════════════

ADMET_ASSAYS = {
    # Absorption
    "caco2_wang":       {"category": "Absorption", "name": "Caco-2 Permeability", "type": "regression", "good_direction": "high", "threshold": -5.15},
    "hia_hou":          {"category": "Absorption", "name": "HIA", "type": "binary", "good_value": 1},
    "pgp_broccatelli":  {"category": "Absorption", "name": "P-gp Inhibitor", "type": "binary", "good_value": 0},
    "bioavailability_ma": {"category": "Absorption", "name": "Oral Bioavailability", "type": "binary", "good_value": 1},
    # Distribution
    "bbb_martins":      {"category": "Distribution", "name": "BBB Penetration", "type": "binary", "good_value": None},
    "ppbr_az":          {"category": "Distribution", "name": "Plasma Protein Binding", "type": "regression", "good_direction": "low", "threshold": 90},
    "vdss_lombardo":    {"category": "Distribution", "name": "Volume of Distribution", "type": "regression", "good_direction": None},
    # Metabolism
    "cyp2c9_veith":     {"category": "Metabolism", "name": "CYP2C9 Inhibitor", "type": "binary", "good_value": 0},
    "cyp2d6_veith":     {"category": "Metabolism", "name": "CYP2D6 Inhibitor", "type": "binary", "good_value": 0},
    "cyp3a4_veith":     {"category": "Metabolism", "name": "CYP3A4 Inhibitor", "type": "binary", "good_value": 0},
    "cyp2c9_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2C9 Substrate", "type": "binary", "good_value": None},
    "cyp2d6_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP2D6 Substrate", "type": "binary", "good_value": None},
    "cyp3a4_substrate_carbonmangels": {"category": "Metabolism", "name": "CYP3A4 Substrate", "type": "binary", "good_value": None},
    # Excretion
    "clearance_hepatocyte_az": {"category": "Excretion", "name": "Hepatocyte Clearance", "type": "regression", "good_direction": None},
    "clearance_microsome_az":  {"category": "Excretion", "name": "Microsome Clearance", "type": "regression", "good_direction": None},
    "half_life_obach":  {"category": "Excretion", "name": "Half-Life", "type": "regression", "good_direction": "high", "threshold": 3},
    # Toxicity
    "ames":             {"category": "Toxicity", "name": "Ames Mutagenicity", "type": "binary", "good_value": 0},
    "dili":             {"category": "Toxicity", "name": "DILI", "type": "binary", "good_value": 0},
    "herg":             {"category": "Toxicity", "name": "hERG Cardiotoxicity", "type": "binary", "good_value": 0},
    "ld50_zhu":         {"category": "Toxicity", "name": "Acute Toxicity LD50", "type": "regression", "good_direction": "high"},
    # Properties
    "lipophilicity_astrazeneca": {"category": "Properties", "name": "Lipophilicity logD", "type": "regression", "good_direction": None},
    "solubility_aqsoldb": {"category": "Properties", "name": "Aqueous Solubility", "type": "regression", "good_direction": "high"},
}

_admet_cache = {}  # assay_name → (fps_list, labels, valid_idx)


def _load_admet_assay(assay_name: str):
    """ADMET assay 데이터 로드 + FP 계산 (1회 캐시)."""
    if assay_name in _admet_cache:
        return _admet_cache[assay_name]

    try:
        train = pd.read_parquet(f"{ADMET_BASE}/{assay_name}/train_val_basic_clean_20260406.parquet")
        test = pd.read_parquet(f"{ADMET_BASE}/{assay_name}/test_basic_clean_20260406.parquet")
        data = pd.concat([train, test], ignore_index=True)
    except Exception:
        _admet_cache[assay_name] = None
        return None

    smiles_arr = data["Drug"].values
    labels = data["Y"].values
    fps = []
    valid_idx = []

    for i, smi in enumerate(smiles_arr):
        mol = Chem.MolFromSmiles(smi)
        if mol:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
            fps.append(fp)
            valid_idx.append(i)

    result = (fps, labels, valid_idx)
    _admet_cache[assay_name] = result
    return result


def admet_22assay_lookup(smiles: str) -> dict:
    """22-assay ADMET Tanimoto 기반 매칭.

    safety_score 계산:
      ≥ 6 → PASS
      4~6 → WARNING
      < 4 → FAIL

    Returns:
        dict with safety_score, verdict, assay_results, summary
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"verdict": "FAIL", "reason": "INVALID SMILES", "safety_score": 0}

    query_fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)

    n_tested = 0
    n_pass = 0
    n_caution = 0
    n_nodata = 0
    flags = []
    assay_results = {}
    category_summary = {}

    for assay_name, info in ADMET_ASSAYS.items():
        cache = _load_admet_assay(assay_name)
        if cache is None:
            assay_results[assay_name] = {"status": "no_data", "category": info["category"]}
            n_nodata += 1
            continue

        fps, labels, valid_idx = cache

        # Tanimoto 최대 유사도 검색
        best_sim = 0.0
        best_val = None
        for j, afp in enumerate(fps):
            sim = DataStructs.TanimotoSimilarity(query_fp, afp)
            if sim > best_sim:
                best_sim = sim
                best_val = labels[valid_idx[j]]

        if best_sim >= 0.85:
            match_type = "exact" if best_sim >= 0.99 else "close_analog"
        elif best_sim >= 0.70:
            match_type = "analog"
        else:
            match_type = "no_match"
            best_val = None

        if best_val is None or match_type == "no_match":
            assay_results[assay_name] = {
                "status": "no_match", "similarity": round(best_sim, 4),
                "category": info["category"],
            }
            n_nodata += 1
            continue

        # 판정
        n_tested += 1
        status = "pass"

        if info["type"] == "binary":
            good_val = info.get("good_value")
            if good_val is None:
                status = "info"
            elif int(best_val) == good_val:
                status = "pass"
                n_pass += 1
            else:
                if assay_name in ("ames", "dili", "herg"):
                    status = "caution"
                    n_caution += 1
                    flags.append(f"{info['name']}(+)")
                else:
                    status = "minor"
                    n_caution += 1
        else:
            # regression → measured
            status = "measured"
            n_pass += 1

        assay_results[assay_name] = {
            "value": round(float(best_val), 4),
            "status": status,
            "match_type": match_type,
            "similarity": round(best_sim, 4),
            "category": info["category"],
            "name": info["name"],
        }

        # 카테고리별 집계
        cat = info["category"]
        if cat not in category_summary:
            category_summary[cat] = {"pass": 0, "caution": 0, "total": 0}
        category_summary[cat]["total"] += 1
        if status in ("pass", "measured"):
            category_summary[cat]["pass"] += 1
        elif status in ("caution", "minor"):
            category_summary[cat]["caution"] += 1

    # safety_score (0~12)
    if n_tested > 0:
        safety_score = n_pass / max(n_tested, 1) * 10
        for flag in flags:
            if "hERG" in flag:
                safety_score -= 2
            elif "Ames" in flag:
                safety_score -= 1.5
            elif "DILI" in flag:
                safety_score -= 1
    else:
        safety_score = 5.0  # 데이터 없으면 neutral

    safety_score = round(max(0, min(12, safety_score)), 2)

    if safety_score >= 6:
        verdict = "PASS"
    elif safety_score >= 4:
        verdict = "WARNING"
    else:
        verdict = "FAIL"

    return {
        "safety_score": safety_score,
        "verdict": verdict,
        "n_tested": n_tested,
        "n_pass": n_pass,
        "n_caution": n_caution,
        "n_nodata": n_nodata,
        "flags": flags,
        "category_summary": category_summary,
        "assay_results": assay_results,
    }


def classify_ic50(ic50: float) -> str:
    """IC50 예측값 → 효과 가능성 판정."""
    if ic50 < 1.0:
        return "High"
    elif ic50 <= 3.0:
        return "Medium"
    else:
        return "Low"


# ═══════════════════════════════════════════════════════════════════
# 허들 3: Tanimoto 유사도
# ═══════════════════════════════════════════════════════════════════

def tanimoto_similarity(smiles: str) -> dict:
    """FDA 승인 유방암 치료제와의 Tanimoto 유사도 계산.

    Returns:
        dict with max_similarity, best_match, all_similarities, verdict
        - PASS:    max > 0.3
        - WARNING: 0.1 <= max <= 0.3
        - FAIL:    max < 0.1
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"verdict": "FAIL", "reason": "INVALID SMILES"}

    query_fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)

    similarities = {}
    for drug_name, drug_smiles in FDA_BRCA_DRUGS.items():
        ref_mol = Chem.MolFromSmiles(drug_smiles)
        if ref_mol is None:
            similarities[drug_name] = 0.0
            continue
        ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, radius=2, nBits=2048)
        sim = DataStructs.TanimotoSimilarity(query_fp, ref_fp)
        similarities[drug_name] = round(sim, 4)

    max_sim = max(similarities.values()) if similarities else 0.0
    best_match = max(similarities, key=similarities.get) if similarities else "N/A"

    if max_sim > 0.3:
        verdict = "PASS"
    elif max_sim >= 0.1:
        verdict = "WARNING"
    else:
        verdict = "FAIL"

    return {
        "max_similarity": round(max_sim, 4),
        "best_match": best_match,
        "all_similarities": similarities,
        "verdict": verdict,
    }


# ═══════════════════════════════════════════════════════════════════
# 허들 4: 유방암 타겟 필터
# ═══════════════════════════════════════════════════════════════════

_drug_target_cache = None

def _load_drug_target_mapping():
    """drug_target_mapping.parquet 로드 (1회 캐시)."""
    global _drug_target_cache
    if _drug_target_cache is not None:
        return _drug_target_cache

    try:
        df = pd.read_parquet(DRUG_TARGET_URI)
        _drug_target_cache = df
        return df
    except Exception as e:
        print(f"  [WARNING] drug_target_mapping 로드 실패: {e}")
        return None


def brca_target_filter(smiles: str) -> dict:
    """유방암 핵심 타겟 overlap 확인.

    drug_target_mapping.parquet에서 canonical_smiles 또는
    canonical_drug_id 기반으로 타겟 확인.

    Returns:
        dict with targets, overlap, verdict (PASS/UNKNOWN)
    """
    df = _load_drug_target_mapping()
    if df is None:
        return {
            "verdict": "UNKNOWN",
            "reason": "drug_target_mapping 데이터 없음",
            "targets": [],
            "overlap": [],
        }

    # SMILES 기반 매칭 시도
    smiles_col = None
    for col_name in ["canonical_smiles", "smiles", "SMILES"]:
        if col_name in df.columns:
            smiles_col = col_name
            break

    matched_targets = set()
    if smiles_col:
        matched_rows = df[df[smiles_col] == smiles]
        if not matched_rows.empty:
            target_col = None
            for col_name in ["target_gene", "gene_name", "target", "gene_symbol"]:
                if col_name in df.columns:
                    target_col = col_name
                    break
            if target_col:
                matched_targets = set(matched_rows[target_col].dropna().unique())

    if not matched_targets:
        return {
            "verdict": "UNKNOWN",
            "reason": "타겟 데이터 없음 (약물 미등록)",
            "targets": [],
            "overlap": [],
        }

    # BRCA 타겟과 교차 확인 (alias 포함)
    brca_set = set(BRCA_CORE_TARGETS)
    for alias_from, alias_to in TARGET_ALIASES.items():
        brca_set.add(alias_from)
        brca_set.add(alias_to)

    overlap = sorted(matched_targets & brca_set)

    if overlap:
        return {
            "verdict": "PASS",
            "targets": sorted(matched_targets),
            "overlap": overlap,
        }
    else:
        return {
            "verdict": "UNKNOWN",
            "reason": f"타겟 {sorted(matched_targets)}은 유방암 핵심 타겟 외",
            "targets": sorted(matched_targets),
            "overlap": [],
        }


# ═══════════════════════════════════════════════════════════════════
# 허들 5: AlphaFold 도킹 (stub)
# ═══════════════════════════════════════════════════════════════════

def alphafold_docking_stub(target_genes: list) -> dict:
    """AlphaFold 기반 도킹 평가 (stub).

    현재는 UNKNOWN 반환. 향후 구현 방향:
    # 1. PDB에서 구조 다운로드
    # 2. 없으면 AlphaFold DB 조회
    # 3. 변이형은 로컬 AlphaFold 실행
    # 4. AutoDock Vina로 도킹 계산
    """
    pdb_lookup = {}
    for gene in target_genes:
        # stub: PDB 조회 시도 (코드만)
        pdb_lookup[gene] = {
            "pdb_id": None,
            "alphafold_id": None,
            "docking_score": None,
            "status": "NOT_IMPLEMENTED",
        }

    return {
        "verdict": "UNKNOWN",
        "reason": "AlphaFold 도킹 미구현 (stub)",
        "target_structures": pdb_lookup,
    }


# ═══════════════════════════════════════════════════════════════════
# 허들 6: 내성 변이 경고 (stub)
# ═══════════════════════════════════════════════════════════════════

def resistance_mutation_check(target_genes: list) -> dict:
    """알려진 내성 변이 DB와 교차 확인 (stub).

    현재는 DB에 해당 타겟이 있으면 WARNING, 없으면 UNKNOWN.
    향후 구현 방향:
    # 1. 환자 WGS 데이터 연동
    # 2. 변이형 AlphaFold 구조 예측
    # 3. 야생형 vs 변이형 도킹 비교
    # 4. 내성 발생 시점 예측 모델
    """
    at_risk = {}
    for gene in target_genes:
        # alias 확인
        check_genes = [gene]
        if gene in TARGET_ALIASES:
            check_genes.append(TARGET_ALIASES[gene])

        for g in check_genes:
            if g in KNOWN_RESISTANCE_MUTATIONS:
                at_risk[g] = KNOWN_RESISTANCE_MUTATIONS[g]

    if at_risk:
        return {
            "verdict": "WARNING",
            "reason": "알려진 내성 변이 존재",
            "at_risk_genes": at_risk,
        }
    else:
        return {
            "verdict": "UNKNOWN",
            "reason": "내성 변이 데이터 없음 (CRISPR 교차 확인 미구현)",
            "at_risk_genes": {},
        }


# ═══════════════════════════════════════════════════════════════════
# 종합 판정
# ═══════════════════════════════════════════════════════════════════

def final_verdict(hurdle_results: dict) -> dict:
    """최종 종합 판정.

    PASS:    허들 1,2,3,4 모두 통과
    WARNING: 1개 이상 WARNING
    FAIL:    핵심 허들 탈락
    """
    core_hurdles = ["hurdle1_ic50", "hurdle2_admet", "hurdle3_tanimoto", "hurdle4_target"]
    all_hurdles = core_hurdles + ["hurdle5_docking", "hurdle6_resistance"]

    verdicts = {}
    for h in all_hurdles:
        if h in hurdle_results:
            verdicts[h] = hurdle_results[h].get("verdict", "UNKNOWN")

    # 핵심 허들 중 FAIL 있으면 → FAIL
    for h in core_hurdles:
        v = verdicts.get(h, "UNKNOWN")
        if v == "FAIL":
            return {"verdict": "FAIL", "reason": f"{h} 탈락", "details": verdicts}

    # WARNING 있으면 → WARNING
    has_warning = any(verdicts.get(h) == "WARNING" for h in all_hurdles)
    has_unknown = any(verdicts.get(h) == "UNKNOWN" for h in core_hurdles)

    if has_warning:
        return {"verdict": "WARNING", "reason": "일부 허들 주의", "details": verdicts}

    # UNKNOWN이 있으면 → WARNING (데이터 부족)
    if has_unknown:
        return {"verdict": "WARNING", "reason": "일부 데이터 부족 (UNKNOWN)", "details": verdicts}

    return {"verdict": "PASS", "reason": "모든 핵심 허들 통과", "details": verdicts}


# ═══════════════════════════════════════════════════════════════════
# Model Loading & Inference
# ═══════════════════════════════════════════════════════════════════

def load_model() -> MultiModalFusionNet:
    """학습된 모델 로드."""
    model = MultiModalFusionNet(d_model=128, nhead=4, dropout=0.2)
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    return model


def run_pipeline(model, smiles_list: list[str]) -> list[dict]:
    """전체 7-허들 파이프라인 실행."""
    crispr_mean = get_crispr_mean()
    all_results = []

    for smi in smiles_list:
        result = {"smiles": smi}

        # ── 기본 검증 ──
        morgan = smiles_to_morgan(smi)
        desc = smiles_to_descriptors(smi)

        if morgan is None or desc is None:
            result["valid"] = False
            result["final_verdict"] = {"verdict": "FAIL", "reason": "INVALID SMILES"}
            all_results.append(result)
            continue

        result["valid"] = True

        # ── 허들 1: IC50 예측 ──
        desc_arr = np.array([desc[k] for k in DRUG_DESC_NAMES], dtype=np.float32)
        t_crispr = torch.from_numpy(crispr_mean.reshape(1, -1)).to(DEVICE)
        t_morgan = torch.from_numpy(morgan.reshape(1, -1)).to(DEVICE)
        t_lincs = torch.zeros(1, 5, device=DEVICE)
        t_target = torch.zeros(1, 10, device=DEVICE)
        t_drugdesc = torch.from_numpy(desc_arr.reshape(1, -1)).to(DEVICE)

        with torch.no_grad():
            ic50 = float(model(t_crispr, t_morgan, t_lincs, t_target, t_drugdesc).cpu().numpy()[0])

        efficacy = classify_ic50(ic50)
        h1_verdict = "PASS" if efficacy in ("High", "Medium") else "FAIL"
        result["hurdle1_ic50"] = {
            "ic50_pred": round(ic50, 4),
            "efficacy": efficacy,
            "verdict": h1_verdict,
        }

        # ── 허들 2A: Lipinski ADMET (투여 경로 고려) ──
        route = infer_route(smi, desc)
        admet = lipinski_filter(desc, route=route)
        h2a_verdict = admet["verdict"]
        result["hurdle2a_lipinski"] = {
            "MW": round(desc["drug_desc_mol_wt"], 1),
            "LogP": round(desc["drug_desc_logp"], 2),
            "TPSA": round(desc["drug_desc_tpsa"], 1),
            "HBD": int(desc["drug_desc_hbd"]),
            "HBA": int(desc["drug_desc_hba"]),
            "RotBonds": int(desc["drug_desc_rot_bonds"]),
            "Rings": int(desc["drug_desc_ring_count"]),
            "violations": admet["violations"],
            "route": route,
            "lipinski_pass": admet["lipinski_pass"],
            "oral_absorption": admet["oral_absorption"],
            "verdict": h2a_verdict,
        }

        # ── 허들 2B: 22-assay ADMET ──
        print(f"  22-assay ADMET 검색 중...")
        result["hurdle2b_admet22"] = admet_22assay_lookup(smi)

        # 허들 2 종합: 2A FAIL이면 FAIL, 아니면 2B verdict 사용
        if h2a_verdict == "FAIL":
            h2_verdict = "FAIL"
        else:
            h2_verdict = result["hurdle2b_admet22"]["verdict"]
        result["hurdle2_admet"] = {"verdict": h2_verdict}

        # ── 허들 3: Tanimoto 유사도 ──
        result["hurdle3_tanimoto"] = tanimoto_similarity(smi)

        # ── 허들 4: 유방암 타겟 필터 ──
        result["hurdle4_target"] = brca_target_filter(smi)

        # ── 허들 5: AlphaFold 도킹 (stub) ──
        target_genes = result["hurdle4_target"].get("targets", [])
        result["hurdle5_docking"] = alphafold_docking_stub(target_genes)

        # ── 허들 6: 내성 변이 경고 (stub) ──
        result["hurdle6_resistance"] = resistance_mutation_check(target_genes)

        # ── 최종 종합 판정 ──
        result["final_verdict"] = final_verdict(result)

        all_results.append(result)

    return all_results


# ═══════════════════════════════════════════════════════════════════
# 결과 출력
# ═══════════════════════════════════════════════════════════════════

def print_hurdle_table(results: list[dict]):
    """전체 허들 결과 표 출력."""
    for r in results:
        smi = r["smiles"]
        print(f"\n{'='*70}")
        print(f"  SMILES: {smi}")
        print(f"{'='*70}")

        if not r.get("valid", False):
            print(f"  Status: INVALID SMILES")
            print(f"  최종 판정: FAIL")
            continue

        # 허들 표
        print(f"\n  {'허들':8s} {'항목':22s} {'결과':10s} {'판정':10s}")
        print(f"  {'─'*54}")

        # 허들 1
        h1 = r["hurdle1_ic50"]
        print(f"  {'1':8s} {'IC50 예측':22s} "
              f"{h1['ic50_pred']:.4f} ({h1['efficacy']}){'':>1s} {h1['verdict']:10s}")

        # 허들 2A
        h2a = r["hurdle2a_lipinski"]
        route = h2a.get("route", "PO")
        lip_str = f"viol={h2a['violations']} ({route})"
        print(f"  {'2A':8s} {'Lipinski':22s} {lip_str:18s} {h2a['verdict']:10s}")
        print(f"  {'':8s}   MW={h2a['MW']}  LogP={h2a['LogP']}  TPSA={h2a['TPSA']}")
        print(f"  {'':8s}   HBD={h2a['HBD']}  HBA={h2a['HBA']}  RotBonds={h2a['RotBonds']}  "
              f"경구흡수={h2a['oral_absorption']}  투여경로={route}")

        # 허들 2B
        h2b = r["hurdle2b_admet22"]
        score_str = f"{h2b['safety_score']}/12"
        print(f"  {'2B':8s} {'22-assay ADMET':22s} {score_str:10s} {h2b['verdict']:10s}")
        print(f"  {'':8s}   tested={h2b['n_tested']}  pass={h2b['n_pass']}  "
              f"caution={h2b['n_caution']}  nodata={h2b['n_nodata']}")
        if h2b.get("flags"):
            print(f"  {'':8s}   flags: {', '.join(h2b['flags'])}")
        if h2b.get("category_summary"):
            for cat, cs in h2b["category_summary"].items():
                print(f"  {'':8s}   {cat}: {cs['pass']}/{cs['total']} pass"
                      + (f"  ({cs['caution']} caution)" if cs['caution'] else ""))

        # 허들 3
        h3 = r["hurdle3_tanimoto"]
        if "max_similarity" in h3:
            sim_str = f"{h3['max_similarity']:.4f} ({h3['best_match']})"
            print(f"  {'3':8s} {'Tanimoto 유사도':22s} {sim_str:22s} {h3['verdict']:10s}")
            for drug, sim in h3.get("all_similarities", {}).items():
                print(f"  {'':8s}   {drug:15s}: {sim:.4f}")
        else:
            print(f"  {'3':8s} {'Tanimoto 유사도':22s} {'N/A':10s} {h3['verdict']:10s}")

        # 허들 4
        h4 = r["hurdle4_target"]
        if h4.get("overlap"):
            tgt_str = ", ".join(h4["overlap"])
        elif h4.get("targets"):
            tgt_str = ", ".join(h4["targets"])
        else:
            tgt_str = h4.get("reason", "N/A")
        print(f"  {'4':8s} {'유방암 타겟':22s} {tgt_str[:22]:22s} {h4['verdict']:10s}")

        # 허들 5
        h5 = r["hurdle5_docking"]
        print(f"  {'5':8s} {'AlphaFold 도킹':22s} {'(stub)':10s} {h5['verdict']:10s}")

        # 허들 6
        h6 = r["hurdle6_resistance"]
        if h6.get("at_risk_genes"):
            risk_genes = ", ".join(h6["at_risk_genes"].keys())
            print(f"  {'6':8s} {'내성 변이 경고':22s} {risk_genes[:22]:22s} {h6['verdict']:10s}")
            for gene, muts in h6["at_risk_genes"].items():
                print(f"  {'':8s}   {gene}: {', '.join(muts)}")
        else:
            print(f"  {'6':8s} {'내성 변이 경고':22s} {h6.get('reason', 'N/A')[:22]:22s} "
                  f"{h6['verdict']:10s}")

        # 최종 판정
        fv = r["final_verdict"]
        print(f"\n  {'─'*54}")
        verdict_str = fv["verdict"]
        reason = fv.get("reason", "")
        print(f"  최종 판정: {verdict_str}  ({reason})")
        print(f"{'='*70}")


def results_to_csv(results: list[dict]) -> pd.DataFrame:
    """결과를 CSV용 DataFrame으로 변환."""
    rows = []
    for r in results:
        if not r.get("valid", False):
            rows.append({"smiles": r["smiles"], "final_verdict": "FAIL"})
            continue

        h1 = r["hurdle1_ic50"]
        h2a = r["hurdle2a_lipinski"]
        h2b = r["hurdle2b_admet22"]
        h2 = r["hurdle2_admet"]
        h3 = r["hurdle3_tanimoto"]
        h4 = r["hurdle4_target"]
        h5 = r["hurdle5_docking"]
        h6 = r["hurdle6_resistance"]
        fv = r["final_verdict"]

        rows.append({
            "smiles": r["smiles"],
            # 허들 1
            "ic50_pred": h1["ic50_pred"],
            "efficacy": h1["efficacy"],
            "h1_verdict": h1["verdict"],
            # 허들 2A
            "MW": h2a["MW"],
            "LogP": h2a["LogP"],
            "TPSA": h2a["TPSA"],
            "HBD": h2a["HBD"],
            "HBA": h2a["HBA"],
            "lipinski_violations": h2a["violations"],
            "route": h2a.get("route", "PO"),
            "lipinski_pass": h2a["lipinski_pass"],
            "oral_absorption": h2a["oral_absorption"],
            "h2a_verdict": h2a["verdict"],
            # 허들 2B
            "safety_score": h2b["safety_score"],
            "admet_tested": h2b["n_tested"],
            "admet_pass": h2b["n_pass"],
            "admet_caution": h2b["n_caution"],
            "admet_flags": ", ".join(h2b.get("flags", [])),
            "h2b_verdict": h2b["verdict"],
            "h2_verdict": h2["verdict"],
            # 허들 3
            "tanimoto_max": h3.get("max_similarity"),
            "tanimoto_best_match": h3.get("best_match"),
            "h3_verdict": h3["verdict"],
            # 허들 4
            "brca_targets": ", ".join(h4.get("overlap", [])),
            "h4_verdict": h4["verdict"],
            # 허들 5
            "h5_verdict": h5["verdict"],
            # 허들 6
            "resistance_genes": ", ".join(h6.get("at_risk_genes", {}).keys()),
            "h6_verdict": h6["verdict"],
            # 최종
            "final_verdict": fv["verdict"],
            "verdict_reason": fv.get("reason", ""),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MultiModalFusionNet 7-Hurdle Inference")
    parser.add_argument("--smiles", nargs="+", help="SMILES string(s)")
    parser.add_argument("--smiles_file", type=str, help="File with one SMILES per line")
    args = parser.parse_args()

    smiles_list = []
    if args.smiles:
        smiles_list = args.smiles
    elif args.smiles_file:
        with open(args.smiles_file) as f:
            smiles_list = [line.strip() for line in f if line.strip()]
    else:
        parser.error("--smiles 또는 --smiles_file 중 하나를 지정해주세요.")

    print(f"{'='*70}")
    print(f"  MultiModalFusionNet 7-Hurdle Inference")
    print(f"  Device: {DEVICE}")
    print(f"  Input: {len(smiles_list)} SMILES")
    print(f"{'='*70}")

    t0 = time.time()

    print("\n  Loading model...")
    model = load_model()
    print(f"  Model loaded: {MODEL_PATH.name}")

    print(f"\n  Running 7-hurdle pipeline...")
    results = run_pipeline(model, smiles_list)
    dt = time.time() - t0

    # 허들 결과 표
    print_hurdle_table(results)

    # CSV 저장
    df = results_to_csv(results)
    out_path = RESULTS_DIR / "inference_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    print(f"  Time: {dt:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
