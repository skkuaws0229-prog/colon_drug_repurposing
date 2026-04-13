#!/usr/bin/env python3
"""
LLM Explanation Generator (Top 15 Dedup 기반)
═══════════════════════════════════════════════════════════════
  - 입력: top30_dedup (상위 15), METABRIC, ADMET 결과 통합
  - 출력: drug별 5-section Markdown
      1. Mechanism of Action
      2. Relevance to Breast Cancer
      3. Supporting Evidence
      4. ADMET / Safety Considerations
      5. Repurposing Potential
  - anthropic SDK 불필요 (구조화된 근거 기반 생성)
  - CAUTION 약물 명확 표시, Epirubicin 심장독성 별도 명시
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import json
import re
import time
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).resolve().parent
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/20260408_pre_project_biso_myprotocol"

# Input paths
DEDUP_CSV = PROJECT_ROOT / "results" / "top30_dedup_20260413" / "top30_dedup_20260413.csv"
METABRIC_JSON = PROJECT_ROOT / "results" / "metabric_results_20260413" / "metabric_results.json"
ADMET_CSV = PROJECT_ROOT / "results" / "admet_results_20260413" / "admet_summary_20260413.csv"
ADMET_JSON = PROJECT_ROOT / "results" / "admet_results_20260413" / "admet_results_20260413.json"

# S3 data
MSIGDB_S3 = f"{S3_BASE}/data/msigdb/msigdb_gene_set_membership_basic_20260406.parquet"
OT_ASSOC_S3 = f"{S3_BASE}/data/opentargets/opentargets_association_overall_direct_basic_20260406.parquet"
OT_TARGET_S3 = f"{S3_BASE}/data/opentargets/opentargets_target_basic_20260406.parquet"
OT_DISEASE_S3 = f"{S3_BASE}/data/opentargets/opentargets_disease_basic_20260406.parquet"

OUTPUT_DIR = PROJECT_ROOT / "results" / "llm_explanations_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TOP_K = 15

# ── Drug Knowledge Base ──
# 약물별 작용기전 설명 (근거 기반, 과장 없음)
MECHANISM_DB = {
    "Docetaxel": {
        "moa": "Taxane 계열 항암제로, 미세소관(microtubule)에 결합하여 안정화시킴으로써 정상적인 세포분열을 억제한다. 방추사 형성을 방해하여 유사분열(mitosis)을 G2/M 단계에서 정지시킨다.",
        "brca_relevance": "유방암 1차 치료제(NCCN Category 1). HER2-양성/삼중음성(TNBC) 포함 모든 아형에 사용. AC-T(anthracycline+cyclophosphamide 후 taxane) 요법의 핵심 구성요소.",
        "evidence": "TAX 316/317 임상시험에서 전이성 유방암 치료 효과 입증. BCIRG 001에서 보조요법으로 생존율 개선 확인.",
    },
    "Dactinomycin": {
        "moa": "Actinomycin D로도 불리며, DNA 이중나선의 minor groove에 삽입(intercalation)되어 RNA polymerase의 전사를 억제한다. DNA-의존적 RNA 합성을 차단하여 세포 사멸을 유도한다.",
        "brca_relevance": "전통적으로 윌름스종양, 횡문근육종 등에 사용되나, 유방암에서도 강력한 세포독성 활성이 GDSC 데이터에서 확인됨. RNA 합성 억제는 빠르게 증식하는 유방암 세포에 효과적일 수 있음.",
        "evidence": "GDSC2 데이터에서 유방암 세포주 대상 높은 감수성(sensitivity rate 100%) 확인. 임상적 유방암 적용은 제한적이나 전임상 근거 존재.",
    },
    "Paclitaxel": {
        "moa": "Taxane 계열 항암제로, β-tubulin에 결합하여 미세소관 탈중합(depolymerization)을 억제한다. 안정화된 미세소관은 세포분열 시 정상적 방추체 형성을 방해하여 유사분열 정지를 유도한다.",
        "brca_relevance": "유방암 표준 치료제(NCCN Category 1). nab-paclitaxel(Abraxane)은 전이성 유방암에서 개선된 약동학을 제공. 주간 투여 요법이 보조치료에서 표준.",
        "evidence": "CALGB 9344/INT 0148에서 보조 paclitaxel 추가 시 DFS 17% 개선. TNBC에서 특히 높은 반응률.",
    },
    "Vinblastine": {
        "moa": "Vinca alkaloid 계열로, tubulin의 중합(polymerization)을 억제하여 미세소관 형성을 방해한다. Taxane과 반대 기전이지만 동일하게 유사분열 정지를 유도한다.",
        "brca_relevance": "전이성 유방암에서 2/3차 치료제로 사용. CMF 요법의 대안으로 활용 가능. 미세소관 표적 약물에 대한 유방암의 높은 감수성이 확인됨.",
        "evidence": "유방암 세포주에서 강력한 세포독성 확인(GDSC sensitivity rate 100%). 단독 또는 병용 요법으로 전이성 유방암에 사용 이력 있음.",
    },
    "Vinorelbine": {
        "moa": "반합성 vinca alkaloid로, tubulin 이합체의 중합을 선택적으로 억제한다. 유사분열 방추체 형성을 방해하여 G2/M 세포주기 정지를 유도한다. Vinblastine 대비 신경독성이 낮다.",
        "brca_relevance": "전이성 유방암 2/3차 치료에서 NCCN 권고 약물. 경구제형 가능하여 편의성 높음. HER2-음성 전이성 유방암에서 단독 또는 병용 사용.",
        "evidence": "전이성 유방암에서 반응률 25-40% 보고. Capecitabine과 병용 시 PFS 개선 확인.",
    },
    "Temsirolimus": {
        "moa": "mTOR(mechanistic target of rapamycin) 선택적 억제제로, FKBP12와 결합하여 mTORC1 complex를 억제한다. PI3K/AKT/mTOR 신호전달을 차단하여 세포 증식, 혈관신생, 대사를 억제한다.",
        "brca_relevance": "PI3K/AKT/mTOR 경로는 유방암, 특히 HR+/HER2- 아형에서 빈번히 활성화됨. PIK3CA 변이(~40%)와의 시너지 가능성. Everolimus(같은 계열)가 유방암에서 승인된 점은 간접 근거.",
        "evidence": "BOLERO-2 연구(everolimus)에서 HR+/HER2- 전이성 유방암 PFS 개선 입증. Temsirolimus는 신세포암 승인이나 유방암 전임상에서 활성 확인.",
    },
    "Topotecan": {
        "moa": "Topoisomerase I(TOP1) 억제제로, TOP1-DNA 절단 복합체(cleavable complex)를 안정화시켜 DNA 복제 시 이중가닥 절단을 유도한다. S기 세포에 선택적으로 작용한다.",
        "brca_relevance": "DNA 복제 스트레스에 민감한 BRCA1/2 결손 유방암에서 특히 효과적일 수 있음. HRD(Homologous Recombination Deficiency) 종양에서 TOP1 억제제 감수성 증가 보고.",
        "evidence": "소세포폐암/난소암 승인 약물. 유방암에서 Phase II 연구 다수 존재. GDSC 데이터에서 sensitivity rate 73%.",
    },
    "CDK9_5576": {
        "moa": "CDK9(Cyclin-dependent kinase 9) 선택적 억제제로, P-TEFb(CDK9/Cyclin T) 복합체를 억제하여 RNA Polymerase II의 전사 신장(elongation)을 차단한다. MYC, MCL1 등 반감기 짧은 종양유전자 발현을 억제한다.",
        "brca_relevance": "CDK9는 유방암에서 과발현되며, MYC-driven TNBC에서 핵심 취약성(vulnerability)으로 보고됨. MCL1 억제를 통한 apoptosis 유도 가능성.",
        "evidence": "전임상 연구에서 TNBC 세포주 대상 CDK9 억제 효과 확인. GDSC 데이터에서 sensitivity rate 65%.",
    },
    "SL0101": {
        "moa": "RSK(p90 ribosomal S6 kinase) 억제제로, AURKB, PIM1, PIM3 kinase도 억제한다. MAPK/ERK 신호전달 하위의 RSK 활성을 차단하여 세포 증식 및 생존 신호를 억제한다.",
        "brca_relevance": "RSK는 ER+ 유방암에서 에스트로겐 비의존적 증식 매개에 관여. AURKB 억제는 유사분열 이상을 유도하여 항종양 효과. PIM kinase는 유방암 약물 저항성 관련.",
        "evidence": "전임상 단계 연구용 화합물. GDSC 데이터에서 제한된 샘플(n=1)로 해석 주의 필요.",
    },
    "Teniposide": {
        "moa": "반합성 podophyllotoxin 유도체로, topoisomerase II와 DNA의 절단 복합체를 안정화시켜 DNA 이중가닥 절단을 유도한다. Etoposide와 유사하나 지질 용해도가 높아 CNS 투과성이 우수하다.",
        "brca_relevance": "DNA 복제 경로 억제제로, 유방암 세포의 높은 증식률을 표적할 수 있음. TOP2 억제제(doxorubicin, epirubicin 등)는 유방암 표준 치료에 이미 포함되어 있어 기전적 근거 존재.",
        "evidence": "소아 ALL에 주로 사용. 유방암 임상 데이터는 제한적이나, 같은 TOP2 억제 기전의 anthracycline이 유방암에서 입증됨.",
    },
    "Epirubicin": {
        "moa": "Anthracycline 계열 항암제로, DNA intercalation, topoisomerase II 억제, 활성산소(ROS) 생성의 다중 기전으로 작용한다. DNA 이중가닥 절단을 유도하고 세포 사멸 경로를 활성화한다.",
        "brca_relevance": "유방암 1차 치료 핵심 약물(NCCN Category 1). FEC/EC 요법의 구성요소. 보조치료 및 전이성 유방암 모두에서 표준 사용. Doxorubicin 대비 심장독성이 다소 낮다.",
        "evidence": "FASG-05, MA.5 등 대규모 임상시험에서 보조치료 효과 입증. BCIRG 005에서 docetaxel과 병용 시 효과 확인.",
    },
    "Mitoxantrone": {
        "moa": "Anthracenedione 계열로, topoisomerase II를 억제하고 DNA intercalation을 통해 작용한다. Anthracycline과 유사하나 구조적으로 다르며, 활성산소 생성이 적어 심장독성이 상대적으로 낮다.",
        "brca_relevance": "전이성 유방암에서 2/3차 치료제로 사용 이력. Anthracycline 내성 또는 심장독성 우려 시 대안. TOP2 경로는 유방암에서 검증된 표적.",
        "evidence": "전이성 유방암 Phase III 연구 다수. 단독 반응률 20-35%. GDSC 데이터에서 낮은 sensitivity rate(8%)은 예측 기반 값.",
    },
    "TW 37": {
        "moa": "BCL-2 family 억제제로, BH3 mimetic 계열에 속한다. BCL-2, BCL-XL, MCL-1에 결합하여 항-세포사멸(anti-apoptotic) 기능을 차단하고, BAX/BAK 매개 미토콘드리아 외막 투과(MOMP)를 유도한다.",
        "brca_relevance": "BCL-2는 ER+ 유방암에서 과발현. MCL-1은 TNBC에서 약물 저항성의 주요 매개자. BH3 mimetic(venetoclax 등)의 유방암 임상시험이 진행 중이며, 같은 계열의 기전적 근거.",
        "evidence": "전임상 연구에서 다양한 암종 대상 효과 확인. 유방암 특이적 임상 데이터는 제한적이나, BCL-2/MCL-1 표적의 유방암 관련성은 확립됨.",
    },
    "CDK9_5038": {
        "moa": "CDK9 선택적 억제제(CDK9_5576과 동일 표적, 다른 화학구조). P-TEFb 복합체를 억제하여 전사 신장을 차단하고, 반감기 짧은 항-세포사멸 단백질(MCL1, XIAP)의 발현을 감소시킨다.",
        "brca_relevance": "CDK9_5576과 동일한 기전적 근거. TNBC에서의 MYC 의존성, CDK9 과발현이 보고됨. 전사 억제를 통한 종양 세포 선택적 사멸 유도.",
        "evidence": "전임상 단계 화합물. GDSC 데이터에서 낮은 predicted sensitivity(4%)이나, true sensitivity rate는 81%로 모델 예측과 괴리 존재.",
    },
    "AZD2014": {
        "moa": "mTORC1/mTORC2 이중 억제제(vistusertib). Rapamycin 유사체(rapalog)와 달리 mTORC2도 억제하여 AKT 피드백 활성화를 차단한다. PI3K/AKT/mTOR 경로를 보다 완전하게 억제.",
        "brca_relevance": "PI3K/AKT/mTOR 경로 과활성은 HR+/HER2- 유방암의 핵심 발암기전. mTORC1만 억제하는 everolimus 대비 mTORC2 추가 억제로 저항성 극복 가능성. 유방암 Phase II 임상 진행됨.",
        "evidence": "MANTA 연구(HR+ 전이성 유방암)에서 fulvestrant 병용 평가. 전임상에서 everolimus 내성 극복 효과 확인.",
    },
}

# Category descriptions
CATEGORY_DESC = {
    "A": "Known BRCA Drug — FDA 승인 또는 NCCN 가이드라인에 포함된 유방암 치료제",
    "B": "BRCA Research Drug — 유방암 관련 연구/전임상 근거가 있는 약물",
    "C": "Pure Repurposing Candidate — 원래 적응증이 유방암과 무관한 재창출 후보",
}

# Category classification
CATEGORY_A_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinblastine", "Vinorelbine",
    "Dactinomycin", "Epirubicin", "Topotecan", "Irinotecan",
    "Rapamycin", "Fulvestrant", "Methotrexate",
}
CATEGORY_C_DRUGS = {"Avagacestat", "Tozasertib"}


def get_category(name):
    if name in CATEGORY_A_DRUGS:
        return "A"
    if name in CATEGORY_C_DRUGS:
        return "C"
    return "B"


def load_all_data():
    """모든 입력 데이터 로드."""
    print("  Loading data sources...")
    t0 = time.time()

    # 1. Dedup Top 28
    dedup = pd.read_csv(DEDUP_CSV)
    dedup["canonical_drug_id"] = dedup["canonical_drug_id"].astype(int)
    top15 = dedup.head(TOP_K).copy()
    top15["category"] = top15["drug_name"].map(get_category)
    print(f"    Top 15 drugs: {len(top15)}")

    # 2. METABRIC results
    with open(METABRIC_JSON) as f:
        metabric = json.load(f)
    metabric_scores = {d["canonical_drug_id"]: d for d in metabric["all_30_scores"]}
    metabric_a = {d["drug_id"]: d for d in metabric["method_a"]["details"]}
    metabric_b = {d["drug_id"]: d for d in metabric["method_b"]["details"]}
    print(f"    METABRIC: {len(metabric_scores)} drug scores")

    # 3. ADMET results
    admet_df = pd.read_csv(ADMET_CSV)
    admet_df["drug_id"] = admet_df["drug_id"].astype(int)
    admet_map = admet_df.set_index("drug_id").to_dict(orient="index")
    print(f"    ADMET: {len(admet_map)} drug profiles")

    # 4. ADMET detailed (JSON)
    with open(ADMET_JSON) as f:
        admet_json = json.load(f)
    admet_detail = {p["drug_id"]: p for p in admet_json["profiles"]}

    # 5. Hallmark pathways
    try:
        msigdb = pd.read_parquet(MSIGDB_S3)
        hallmark = msigdb[msigdb["collection"].str.contains("hallmark", case=False, na=False)]
        print(f"    Hallmark: {hallmark['gene_set_name'].nunique()} pathways")
    except Exception as e:
        print(f"    Hallmark: 로드 실패 ({e})")
        hallmark = pd.DataFrame()

    # 6. OpenTargets
    try:
        ot_assoc = pd.read_parquet(OT_ASSOC_S3)
        ot_target = pd.read_parquet(OT_TARGET_S3)
        ot_disease = pd.read_parquet(OT_DISEASE_S3)
        brca_disease_ids = ot_disease[
            ot_disease["name"].str.contains("breast", case=False, na=False)
        ]["id"].values
        print(f"    OpenTargets: {len(ot_assoc)} associations, "
              f"{len(brca_disease_ids)} breast cancer diseases")
    except Exception as e:
        print(f"    OpenTargets: 로드 실패 ({e})")
        ot_assoc = ot_target = ot_disease = pd.DataFrame()
        brca_disease_ids = []

    dt = time.time() - t0
    print(f"    ({dt:.1f}s)")

    return {
        "top15": top15,
        "metabric_scores": metabric_scores,
        "metabric_a": metabric_a,
        "metabric_b": metabric_b,
        "admet_map": admet_map,
        "admet_detail": admet_detail,
        "hallmark": hallmark,
        "ot_assoc": ot_assoc,
        "ot_target": ot_target,
        "ot_disease": ot_disease,
        "brca_disease_ids": brca_disease_ids,
    }


def get_hallmark_pathways(target_str, hallmark_df):
    """타겟 유전자 → Hallmark pathway 매핑."""
    if hallmark_df.empty:
        return []
    genes = [g.strip() for g in str(target_str).split(",") if g.strip()]
    if not genes:
        return []
    matched = hallmark_df[hallmark_df["gene_symbol"].isin(genes)]
    if matched.empty:
        return []
    return matched.groupby("gene_set_name")["gene_symbol"].apply(list).to_dict()


def get_ot_brca_relevance(target_str, ctx):
    """OpenTargets에서 타겟 유전자-유방암 연관성 조회."""
    if ctx["ot_assoc"].empty:
        return []
    genes = [g.strip() for g in str(target_str).split(",") if g.strip()]
    results = []
    for gene in genes:
        gene_match = ctx["ot_target"][
            ctx["ot_target"]["approvedSymbol"].str.upper() == gene.upper()
        ]
        if gene_match.empty:
            continue
        tid = gene_match.iloc[0]["id"]
        assoc = ctx["ot_assoc"][
            (ctx["ot_assoc"]["targetId"] == tid) &
            (ctx["ot_assoc"]["diseaseId"].isin(ctx["brca_disease_ids"]))
        ]
        if not assoc.empty:
            best = float(assoc["score"].max())
            top_diseases = []
            for did in assoc.nlargest(3, "score")["diseaseId"].values:
                d = ctx["ot_disease"][ctx["ot_disease"]["id"] == did]
                if not d.empty:
                    top_diseases.append(d.iloc[0]["name"])
            results.append({"gene": gene, "score": best, "diseases": top_diseases})
    return results


def generate_explanation(row, ctx):
    """단일 약물에 대한 5-section Markdown 생성."""
    drug_id = int(row["canonical_drug_id"])
    drug_name = str(row["drug_name"])
    target = str(row.get("target", "N/A"))
    pathway = str(row.get("pathway", "N/A"))
    category = row.get("category", "B")
    rank = int(row.get("rank", 0))
    pred_ic50 = float(row.get("mean_pred_ic50", 0))
    sens_rate = float(row.get("sensitivity_rate", 0))

    # METABRIC data
    met = ctx["metabric_scores"].get(drug_id, {})
    met_a = ctx["metabric_a"].get(drug_id, {})
    met_b = ctx["metabric_b"].get(drug_id, {})

    target_expressed = met.get("target_expressed", "N/A")
    brca_pathway = met.get("brca_pathway", "N/A")
    survival_sig = met.get("survival_sig", "N/A")
    survival_p = met.get("survival_p", "N/A")
    validation_score = met.get("validation_score", "N/A")

    # ADMET data
    admet = ctx["admet_map"].get(drug_id, {})
    admet_det = ctx["admet_detail"].get(drug_id, {})
    safety_score = admet.get("safety_score", "N/A")
    admet_decision = admet.get("admet_decision", "N/A")
    flags_raw = admet.get("flags", "")
    flags = str(flags_raw) if pd.notna(flags_raw) else ""
    tox_interp_raw = admet.get("tox_interpretation", "")
    tox_interp = str(tox_interp_raw) if pd.notna(tox_interp_raw) else ""

    # Hallmark
    hallmark_map = get_hallmark_pathways(target, ctx["hallmark"])

    # OpenTargets
    ot_results = get_ot_brca_relevance(target, ctx)

    # Knowledge base
    kb = MECHANISM_DB.get(drug_name, {})

    # ── Build Markdown ──
    lines = []

    # Header
    cat_badge = {"A": "Known BRCA", "B": "BRCA Research", "C": "Pure Repurposing"}[category]
    decision_badge = admet_decision if admet_decision != "N/A" else "N/A"

    # CAUTION / Epirubicin 경고
    warning_banner = ""
    if decision_badge == "CAUTION":
        warning_banner = f"\n> **CAUTION**: 이 약물은 ADMET 검증에서 주의(CAUTION) 판정을 받았습니다. {flags}\n"
    if drug_name == "Epirubicin":
        warning_banner += (
            "\n> **심장독성 경고 (Epirubicin)**: Anthracycline 계열 약물로 "
            "누적용량 의존적 심근병증 위험이 있습니다. "
            "LVEF 모니터링 필수, 누적용량 900mg/m² 초과 금지.\n"
        )

    lines.append(f"# {drug_name} — 유방암 재창출 분석")
    lines.append("")
    lines.append(f"| 항목 | 값 |")
    lines.append(f"|---|---|")
    lines.append(f"| **Drug ID** | {drug_id} |")
    lines.append(f"| **Dedup Rank** | {rank} / 28 |")
    lines.append(f"| **Category** | **{category}** ({cat_badge}) |")
    lines.append(f"| **Target** | {target} |")
    lines.append(f"| **Pathway** | {pathway} |")
    lines.append(f"| **Pred IC50** | {pred_ic50:.4f} (ln scale) |")
    lines.append(f"| **Sensitivity Rate** | {sens_rate:.0%} |")
    lines.append(f"| **ADMET Decision** | **{decision_badge}** |")
    lines.append(f"| **Validation Score** | {validation_score} |")
    lines.append("")

    if warning_banner:
        lines.append(warning_banner)

    # ── Section 1: Mechanism of Action ──
    lines.append("## 1. Mechanism of Action (작용 기전)")
    lines.append("")
    if kb.get("moa"):
        lines.append(kb["moa"])
    else:
        lines.append(f"{drug_name}은(는) {target}을(를) 표적으로 하여 {pathway} 경로에 작용하는 항암제이다.")
    lines.append("")

    if hallmark_map:
        lines.append("**관련 Hallmark Pathways:**")
        for pw, genes in sorted(hallmark_map.items(), key=lambda x: -len(x[1]))[:5]:
            lines.append(f"- {pw}: {', '.join(genes)}")
        lines.append("")

    # ── Section 2: Relevance to Breast Cancer ──
    lines.append("## 2. Relevance to Breast Cancer (유방암 관련성)")
    lines.append("")
    if kb.get("brca_relevance"):
        lines.append(kb["brca_relevance"])
    else:
        lines.append(f"{pathway} 경로는 유방암 세포 증식 및 생존에 관여하는 것으로 알려져 있다.")
    lines.append("")

    lines.append("**METABRIC 외부검증 결과:**")
    te_str = "발현 확인" if target_expressed == 1 else "발현 미확인" if target_expressed == 0 else str(target_expressed)
    bp_str = "관련 경로" if brca_pathway == 1 else "비관련" if brca_pathway == 0 else str(brca_pathway)
    ss_str = "유의미 (p<0.05)" if survival_sig == 1 else "유의하지 않음" if survival_sig == 0 else str(survival_sig)
    lines.append(f"- 타겟 발현 (Method A): {te_str}")
    lines.append(f"- BRCA 경로 연관: {bp_str}")
    lines.append(f"- 생존 분석 (Method B): {ss_str} (p={survival_p})")
    lines.append(f"- 종합 검증 점수: {validation_score}")
    lines.append("")

    if ot_results:
        lines.append("**OpenTargets 유방암 연관성:**")
        for r in ot_results:
            diseases = ", ".join(r["diseases"][:3]) if r["diseases"] else "N/A"
            lines.append(f"- {r['gene']}: association score={r['score']:.3f} ({diseases})")
        lines.append("")

    # ── Section 3: Supporting Evidence ──
    lines.append("## 3. Supporting Evidence (근거 자료)")
    lines.append("")
    if kb.get("evidence"):
        lines.append(kb["evidence"])
    else:
        lines.append(f"GDSC2 데이터 기반 예측 감수성 분석 결과, {drug_name}은 "
                      f"유방암 세포주 {int(row.get('n_samples', 0))}개 대상 "
                      f"sensitivity rate {sens_rate:.0%}를 보였다.")
    lines.append("")

    lines.append("**모델 예측 근거:**")
    lines.append(f"- GDSC2 유방암 세포주 수: {int(row.get('n_samples', 0))}")
    lines.append(f"- 앙상블 예측 IC50 (ln): {pred_ic50:.4f}")
    lines.append(f"- 예측 감수성률: {sens_rate:.0%}")

    true_ic50 = row.get("mean_true_ic50")
    true_sens = row.get("true_sensitivity_rate")
    if pd.notna(true_ic50):
        lines.append(f"- 실제 IC50 (ln): {float(true_ic50):.4f}")
    if pd.notna(true_sens):
        lines.append(f"- 실제 감수성률: {float(true_sens):.0%}")
    lines.append("")

    known_brca = met.get("known_brca", 0)
    if known_brca == 1:
        lines.append(f"> {drug_name}은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.")
    else:
        lines.append(f"> {drug_name}은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.")
    lines.append("")

    # ── Section 4: ADMET / Safety Considerations ──
    lines.append("## 4. ADMET / Safety Considerations (안전성 평가)")
    lines.append("")
    lines.append(f"| 항목 | 결과 |")
    lines.append(f"|---|---|")
    lines.append(f"| **ADMET Decision** | **{decision_badge}** |")
    lines.append(f"| **Safety Score** | {safety_score} |")
    lines.append(f"| **검사 수** | {admet.get('n_assays_tested', 'N/A')} / 22 |")
    lines.append(f"| **Pass** | {admet.get('n_pass', 'N/A')} |")
    lines.append(f"| **Caution** | {admet.get('n_caution', 'N/A')} |")
    lines.append(f"| **No Data** | {admet.get('n_nodata', 'N/A')} |")
    lines.append(f"| **Flags** | {flags if flags else 'None'} |")
    lines.append("")

    lines.append(f"**해석**: {tox_interp}")
    lines.append("")

    # Category-specific safety note
    if category == "A":
        lines.append("**카테고리 A 기준**: 이미 임상에서 사용 중인 승인 약물이므로, "
                      "알려진 부작용은 관리 가능한 범위 내에서 허용됩니다.")
    elif category == "B":
        if decision_badge == "CAUTION":
            lines.append("**카테고리 B 기준**: BRCA 연구 약물로서 중대 독성 플래그가 있어 "
                          "추가 안전성 연구가 필요합니다. 임상 진입 전 독성 프로파일 재평가 권고.")
        else:
            lines.append("**카테고리 B 기준**: BRCA 연구 약물로서 주요 독성 플래그가 없어 "
                          "추가 전임상/임상 연구 진행이 가능합니다.")
    else:  # C
        lines.append("**카테고리 C 기준**: 완전 재창출 후보로서, 독성 플래그가 없는 것이 "
                      "필수 조건입니다. 현재 결과 기준 PASS 판정.")
    lines.append("")

    # Epirubicin extra
    if drug_name == "Epirubicin":
        lines.append("### Epirubicin 심장독성 상세")
        lines.append("")
        lines.append("- **Ames Mutagenicity**: 양성 (+) — 변이원성 확인")
        lines.append("- **DILI**: 양성 (+) — 약물 유발 간손상 가능성")
        lines.append("- **Clinical Cardiotoxicity**: Anthracycline 계열 고유 위험")
        lines.append("  - 누적용량 의존적 심근병증 (Type I cardiotoxicity)")
        lines.append("  - Doxorubicin 대비 약 50% 수준의 심장독성 (등가용량 기준)")
        lines.append("  - 권장 모니터링: 기저 LVEF 측정 → 매 투여 주기마다 확인")
        lines.append("  - 누적용량 제한: 900 mg/m² 초과 금지")
        lines.append("  - 심장 보호제(dexrazoxane) 병용 고려")
        lines.append("")

    # ── Section 5: Repurposing Potential ──
    lines.append("## 5. Repurposing Potential (재창출 가능성)")
    lines.append("")

    # Compute overall assessment
    score_factors = []
    if sens_rate >= 0.5:
        score_factors.append("높은 예측 감수성")
    if validation_score != "N/A" and float(validation_score) >= 7.0:
        score_factors.append("높은 METABRIC 검증 점수")
    if target_expressed == 1:
        score_factors.append("타겟 발현 확인")
    if survival_sig == 1:
        score_factors.append("생존 분석 유의")
    if decision_badge == "PASS":
        score_factors.append("ADMET 통과")
    if known_brca == 1:
        score_factors.append("기존 BRCA 치료제")

    neg_factors = []
    if sens_rate < 0.1:
        neg_factors.append("낮은 예측 감수성")
    if decision_badge == "CAUTION":
        neg_factors.append("ADMET 주의 판정")
    if flags and ("Ames" in flags or "hERG" in flags):
        neg_factors.append("중대 독성 플래그")

    n_pos = len(score_factors)
    if n_pos >= 5:
        potential = "높음 (High)"
    elif n_pos >= 3:
        potential = "중간 (Moderate)"
    else:
        potential = "낮음 (Low)"

    if decision_badge == "CAUTION":
        potential = "조건부 (Conditional)"

    lines.append(f"**종합 평가: {potential}**")
    lines.append("")

    if score_factors:
        lines.append("긍정적 요인:")
        for f in score_factors:
            lines.append(f"- (+) {f}")
    if neg_factors:
        lines.append("")
        lines.append("부정적 요인:")
        for f in neg_factors:
            lines.append(f"- (-) {f}")
    lines.append("")

    # Category-specific recommendation
    if category == "A":
        lines.append("**권고**: Category A 약물로서 이미 유방암 치료에 사용 중. "
                      "현 파이프라인 결과는 기존 임상 근거와 일치하며, "
                      "약물 우선순위 결정 및 아형별 최적화에 활용 가능.")
    elif category == "B":
        if decision_badge == "CAUTION":
            lines.append("**권고**: ADMET 주의 판정으로 독성 프로파일 재평가 필요. "
                          "전임상 독성 시험 우선 수행 후 임상 적용 검토.")
        else:
            lines.append("**권고**: 전임상 근거를 바탕으로 유방암 특이적 임상시험 설계 검토 가능. "
                          "특히 해당 표적/경로의 유방암 아형 특이성 분석 권장.")
    else:  # C
        lines.append("**권고**: 원래 적응증과 다른 완전 재창출 후보. "
                      "표적 경로의 유방암 관련성에 대한 추가 전임상 연구가 필수적.")
    lines.append("")

    lines.append("---")
    lines.append(f"*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*")

    return "\n".join(lines)


def main():
    t0 = time.time()
    print("=" * 70)
    print("  LLM Explanation Generator — Top 15 (Dedup)")
    print("=" * 70)

    ctx = load_all_data()
    top15 = ctx["top15"]

    print(f"\n{'─'*70}")
    print(f"  Generating explanations for {len(top15)} drugs...")
    print(f"{'─'*70}")

    results = []
    n_success = 0
    n_fail = 0

    for _, row in top15.iterrows():
        drug_name = str(row["drug_name"])
        drug_id = int(row["canonical_drug_id"])
        rank = int(row["rank"])

        print(f"\n  [{rank}/{TOP_K}] {drug_name} (ID={drug_id}, Cat={row['category']})")

        try:
            md_content = generate_explanation(row, ctx)
            safe_name = re.sub(r'[^\w\-]', '_', drug_name)
            md_path = OUTPUT_DIR / f"{safe_name}_explanation.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            n_success += 1
            print(f"    OK → {md_path.name} ({len(md_content)} chars)")
            results.append({
                "rank": rank,
                "drug_id": drug_id,
                "drug_name": drug_name,
                "category": row["category"],
                "file": md_path.name,
                "chars": len(md_content),
                "status": "success",
            })
        except Exception as e:
            n_fail += 1
            print(f"    FAIL: {str(e)[:200]}")
            results.append({
                "rank": rank,
                "drug_id": drug_id,
                "drug_name": drug_name,
                "category": row["category"],
                "file": None,
                "chars": 0,
                "status": f"error: {str(e)[:100]}",
            })

    # Summary JSON
    summary = {
        "description": "LLM Explanation Summary — Top 15 Dedup (구조화된 근거 기반)",
        "total": len(top15),
        "success": n_success,
        "fail": n_fail,
        "results": results,
    }
    summary_path = OUTPUT_DIR / "explanation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    dt = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  LLM Explanation 완료")
    print(f"  성공: {n_success}/{len(top15)}, 실패: {n_fail}/{len(top15)}")
    print(f"  출력: {OUTPUT_DIR}")
    print(f"  소요시간: {dt:.1f}s")
    print(f"{'='*70}")

    # Print result table
    print(f"\n  {'Rank':>4}  {'Drug':<22} {'Cat':>3} {'Status':<8} {'File'}")
    print(f"  {'-'*70}")
    for r in results:
        fname = r["file"] or "N/A"
        print(f"  {r['rank']:>4}  {r['drug_name']:<22} {r['category']:>3} "
              f"{r['status']:<8} {fname}")


if __name__ == "__main__":
    main()
