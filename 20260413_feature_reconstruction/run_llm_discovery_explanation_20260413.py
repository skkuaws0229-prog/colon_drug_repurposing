#!/usr/bin/env python3
"""
Discovery Top 15 LLM Explanation Generator
═══════════════════════════════════════════════════════════════
  - 입력: discovery_v2_top15, admet_summary, top30_dedup
  - 출력: drug별 6-section Markdown (Discovery 관점)
      1. Discovery Context
      2. Mechanism of Action
      3. Novelty vs Known BRCA drugs
      4. Supporting Evidence
      5. ADMET / Safety
      6. Repurposing Potential
  - anthropic SDK 불필요 (구조화된 근거 기반 생성)
  - 실행은 승인 후
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

# Input paths
DISCOVERY_CSV = PROJECT_ROOT / "results" / "discovery_ranking_20260413" / "discovery_v2_top15_20260413.csv"
ADMET_CSV = PROJECT_ROOT / "results" / "admet_results_20260413" / "admet_summary_20260413.csv"
DEDUP_CSV = PROJECT_ROOT / "results" / "top30_dedup_20260413" / "top30_dedup_20260413.csv"
METABRIC_JSON = PROJECT_ROOT / "results" / "metabric_results_20260413" / "metabric_results.json"

OUTPUT_DIR = PROJECT_ROOT / "results" / "llm_explanations_discovery_20260413"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Drug Knowledge Base: Mechanism of Action ──
MECHANISM_DB = {
    "SL0101": {
        "moa": "RSK(p90 ribosomal S6 kinase) 억제제로, AURKB, PIM1, PIM3 kinase도 억제한다. MAPK/ERK 신호전달 하위의 RSK 활성을 차단하여 세포 증식 및 생존 신호를 억제한다.",
        "brca_relevance": "RSK는 ER+ 유방암에서 에스트로겐 비의존적 증식 매개에 관여. AURKB 억제는 유사분열 이상을 유도하여 항종양 효과. PIM kinase는 유방암 약물 저항성 관련.",
        "evidence": "전임상 단계 연구용 화합물. GDSC 데이터에서 제한된 샘플(n=1)로 해석 주의 필요. RSK 표적은 유방암 내분비 저항성 극복 전략으로 연구 중.",
    },
    "CDK9_5576": {
        "moa": "CDK9(Cyclin-dependent kinase 9) 선택적 억제제로, P-TEFb(CDK9/Cyclin T) 복합체를 억제하여 RNA Polymerase II의 전사 신장(elongation)을 차단한다. MYC, MCL1 등 반감기 짧은 종양유전자 발현을 억제한다.",
        "brca_relevance": "CDK9는 유방암에서 과발현되며, MYC-driven TNBC에서 핵심 취약성(vulnerability)으로 보고됨. MCL1 억제를 통한 apoptosis 유도 가능성.",
        "evidence": "전임상 연구에서 TNBC 세포주 대상 CDK9 억제 효과 확인. GDSC 데이터에서 sensitivity rate 65%. CDK9 발현이 METABRIC에서 유방암 환자 100%에서 확인.",
    },
    "Avagacestat": {
        "moa": "Gamma-secretase 억제제로, amyloid precursor protein(APP)의 절단을 억제하여 amyloid beta 20/40 생성을 차단한다. 원래 알츠하이머 치료제로 개발되었으나 Phase II에서 중단.",
        "brca_relevance": "Gamma-secretase는 Notch 신호전달 경로도 매개하며, Notch는 유방암 줄기세포(CSC) 유지 및 약물 저항성에 핵심적 역할. Gamma-secretase 억제제의 유방암 전임상 연구가 다수 보고됨.",
        "evidence": "알츠하이머 Phase II 임상 수행(안전성 데이터 존재). Gamma-secretase 억제제 계열(MK-0752, RO4929097)의 유방암 임상시험이 진행된 바 있음.",
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
    "Teniposide": {
        "moa": "반합성 podophyllotoxin 유도체로, topoisomerase II와 DNA의 절단 복합체를 안정화시켜 DNA 이중가닥 절단을 유도한다. Etoposide와 유사하나 지질 용해도가 높아 CNS 투과성이 우수하다.",
        "brca_relevance": "DNA 복제 경로 억제제로, 유방암 세포의 높은 증식률을 표적할 수 있음. TOP2 억제제(doxorubicin, epirubicin 등)는 유방암 표준 치료에 이미 포함되어 있어 기전적 근거 존재.",
        "evidence": "소아 ALL에 주로 사용. 유방암 임상 데이터는 제한적이나, 같은 TOP2 억제 기전의 anthracycline이 유방암에서 입증됨.",
    },
    "Dactinomycin": {
        "moa": "Actinomycin D로도 불리며, DNA 이중나선의 minor groove에 삽입(intercalation)되어 RNA polymerase의 전사를 억제한다. DNA-의존적 RNA 합성을 차단하여 세포 사멸을 유도한다.",
        "brca_relevance": "전통적으로 윌름스종양, 횡문근육종 등에 사용되나, 유방암에서도 강력한 세포독성 활성이 GDSC 데이터에서 확인됨. RNA 합성 억제는 빠르게 증식하는 유방암 세포에 효과적일 수 있음.",
        "evidence": "GDSC2 데이터에서 유방암 세포주 대상 높은 감수성(sensitivity rate 100%) 확인. 임상적 유방암 적용은 제한적이나 전임상 근거 존재.",
    },
    "Docetaxel": {
        "moa": "Taxane 계열 항암제로, 미세소관(microtubule)에 결합하여 안정화시킴으로써 정상적인 세포분열을 억제한다. 방추사 형성을 방해하여 유사분열(mitosis)을 G2/M 단계에서 정지시킨다.",
        "brca_relevance": "유방암 1차 치료제(NCCN Category 1). HER2-양성/삼중음성(TNBC) 포함 모든 아형에 사용. AC-T(anthracycline+cyclophosphamide 후 taxane) 요법의 핵심 구성요소.",
        "evidence": "TAX 316/317 임상시험에서 전이성 유방암 치료 효과 입증. BCIRG 001에서 보조요법으로 생존율 개선 확인.",
    },
    "Temsirolimus": {
        "moa": "mTOR(mechanistic target of rapamycin) 선택적 억제제로, FKBP12와 결합하여 mTORC1 complex를 억제한다. PI3K/AKT/mTOR 신호전달을 차단하여 세포 증식, 혈관신생, 대사를 억제한다.",
        "brca_relevance": "PI3K/AKT/mTOR 경로는 유방암, 특히 HR+/HER2- 아형에서 빈번히 활성화됨. PIK3CA 변이(~40%)와의 시너지 가능성. Everolimus(같은 계열)가 유방암에서 승인된 점은 간접 근거.",
        "evidence": "BOLERO-2 연구(everolimus)에서 HR+/HER2- 전이성 유방암 PFS 개선 입증. Temsirolimus는 신세포암 승인이나 유방암 전임상에서 활성 확인.",
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
    "Tanespimycin": {
        "moa": "HSP90(Heat Shock Protein 90) 억제제로, HSP90 chaperone 기능을 차단하여 다수의 client protein(HER2, AKT, RAF 등)의 분해를 유도한다. 동시에 여러 종양 신호경로를 차단하는 다중 표적 효과.",
        "brca_relevance": "HSP90은 HER2 단백질 안정화에 필수적. HER2+ 유방암에서 trastuzumab 병용 Phase II 결과 존재. HSP90 억제는 PI3K/AKT, MAPK 등 다중 경로를 동시에 억제 가능.",
        "evidence": "Phase II 임상에서 HER2+ 전이성 유방암 대상 trastuzumab 병용 평가. 반응률은 제한적이나, 기전적 근거와 안전성 데이터 확보.",
    },
    "Topotecan": {
        "moa": "Topoisomerase I(TOP1) 억제제로, TOP1-DNA 절단 복합체(cleavable complex)를 안정화시켜 DNA 복제 시 이중가닥 절단을 유도한다. S기 세포에 선택적으로 작용한다.",
        "brca_relevance": "DNA 복제 스트레스에 민감한 BRCA1/2 결손 유방암에서 특히 효과적일 수 있음. HRD(Homologous Recombination Deficiency) 종양에서 TOP1 억제제 감수성 증가 보고.",
        "evidence": "소세포폐암/난소암 승인 약물. 유방암에서 Phase II 연구 다수 존재. GDSC 데이터에서 sensitivity rate 73%.",
    },
    "AZD2014": {
        "moa": "mTORC1/mTORC2 이중 억제제(vistusertib). Rapamycin 유사체(rapalog)와 달리 mTORC2도 억제하여 AKT 피드백 활성화를 차단한다. PI3K/AKT/mTOR 경로를 보다 완전하게 억제.",
        "brca_relevance": "PI3K/AKT/mTOR 경로 과활성은 HR+/HER2- 유방암의 핵심 발암기전. mTORC1만 억제하는 everolimus 대비 mTORC2 추가 억제로 저항성 극복 가능성. 유방암 Phase II 임상 진행됨.",
        "evidence": "MANTA 연구(HR+ 전이성 유방암)에서 fulvestrant 병용 평가. 전임상에서 everolimus 내성 극복 효과 확인.",
    },
}

# ── Novelty Knowledge Base: Why each target is novel for BRCA ──
NOVELTY_DB = {
    "SL0101": {
        "target_class": "novel",
        "differentiation": (
            "기존 BRCA 치료제는 미세소관(taxane/vinca), DNA 복제(anthracycline/TOP1/2), "
            "호르몬(ER 억제), HER2 표적에 집중. RSK/AURKB/PIM 다중 kinase 억제는 "
            "이들과 전혀 다른 MAPK/ERK 하위 신호전달 및 유사분열 조절 경로를 표적."
        ),
        "novelty_significance": (
            "RSK는 에스트로겐 비의존적 ER 활성화 매개자로, 내분비 저항성 유방암에서 "
            "새로운 치료 전략을 제시. AURKB/PIM 동시 억제는 다중 경로 차단으로 "
            "단일 표적 약물 대비 저항성 발생 가능성이 낮을 수 있음."
        ),
    },
    "CDK9_5576": {
        "target_class": "novel",
        "differentiation": (
            "CDK9는 전사 신장(transcription elongation)을 조절하는 kinase로, "
            "기존 BRCA 표준 치료제에서 표적하지 않는 유전자 발현 조절 단계에 작용. "
            "CDK4/6 억제제(palbociclib 등)와는 다른 CDK family 멤버."
        ),
        "novelty_significance": (
            "CDK9 억제는 MYC, MCL1 등 반감기 짧은 종양유전자의 전사를 선택적으로 차단. "
            "MYC-driven TNBC에서 특히 유망하며, 기존 CDK4/6 억제제와 비교가 "
            "불가능한 완전히 다른 기전. 전사 수준에서의 항암 전략은 유방암에서 미개척 영역."
        ),
    },
    "Avagacestat": {
        "target_class": "novel",
        "differentiation": (
            "원래 알츠하이머 치료제로 개발된 gamma-secretase 억제제. "
            "Amyloid beta 표적은 유방암과 직접적 연관성이 없으나, "
            "gamma-secretase의 Notch 경로 매개 기능이 유방암 재창출의 근거."
        ),
        "novelty_significance": (
            "완전한 재창출(repurposing) 후보로, 기존 BRCA 치료 패러다임과 무관한 표적. "
            "Notch 신호전달은 유방암 줄기세포(CSC) 유지에 핵심적이며, "
            "CSC 표적 치료는 재발/전이 억제의 새로운 전략. "
            "알츠하이머 임상 안전성 데이터가 이미 확보된 점이 개발 가속화 요인."
        ),
    },
    "TW 37": {
        "target_class": "novel",
        "differentiation": (
            "BCL-2/BCL-XL/MCL-1 동시 억제 BH3 mimetic. "
            "기존 BRCA 치료제 중 apoptosis 직접 유도 약물은 없음. "
            "Venetoclax(BCL-2 선택적)가 혈액암에서 승인되었으나 고형암은 미개척."
        ),
        "novelty_significance": (
            "유방암, 특히 TNBC에서 MCL-1 과발현이 약물 저항성의 주요 원인. "
            "BCL-2 + MCL-1 동시 억제는 단일 표적 BH3 mimetic 대비 "
            "더 넓은 항종양 스펙트럼 기대. Apoptosis 직접 유도는 기존 "
            "세포독성 항암제와 다른 기전으로 병용 가능성 높음."
        ),
    },
    "CDK9_5038": {
        "target_class": "novel",
        "differentiation": (
            "CDK9_5576과 동일 표적(CDK9), 다른 화학구조의 억제제. "
            "동일한 전사 억제 기전을 공유하며, 기존 BRCA 치료 패러다임에서 "
            "표적되지 않은 전사 조절 경로에 작용."
        ),
        "novelty_significance": (
            "두 CDK9 억제제가 독립적으로 Discovery Top 5에 진입한 것은 "
            "CDK9 표적의 유방암 관련성을 지지하는 강력한 교차검증 근거. "
            "다만, true sensitivity(81%)와 predicted sensitivity(4%) 간 괴리는 "
            "추가 실험적 검증이 필요한 부분."
        ),
    },
    "Teniposide": {
        "target_class": "novel",
        "differentiation": (
            "Topoisomerase II 억제제로 기존 BRCA 치료(anthracycline)와 유사한 경로이나, "
            "특정 타겟 정보가 불명확(target=NaN)하여 novel로 분류됨. "
            "Etoposide 유사체로 다른 약동학 프로파일 보유."
        ),
        "novelty_significance": (
            "Pathway는 기존(DNA replication, novelty=0.2)이나 target 미상으로 "
            "target_novelty=1.0 배정. 실제 기전은 TOP2 경로 관련 가능성 높으며, "
            "novelty 점수가 과대평가되었을 수 있어 해석 시 주의 필요."
        ),
    },
    "Dactinomycin": {
        "target_class": "moderate",
        "differentiation": (
            "RNA polymerase 억제제로, 전사 차단을 통해 작용. "
            "기존 BRCA 치료에서 RNA 합성 직접 억제 약물은 사용되지 않으며, "
            "DNA 수준이 아닌 RNA 수준에서의 작용이 차별점."
        ),
        "novelty_significance": (
            "Known BRCA 치료제(Category A)이나, 유방암에서의 사용은 제한적. "
            "RNA 합성 억제 기전은 빠르게 증식하는 세포에 선택적이며, "
            "기존 DNA 표적 약물과 비교차 저항성 기대."
        ),
    },
    "Docetaxel": {
        "target_class": "standard",
        "differentiation": (
            "미세소관 안정화 약물로, 유방암 1차 표준 치료제. "
            "가장 잘 확립된 기존 BRCA 약물 중 하나로 novelty는 낮음."
        ),
        "novelty_significance": (
            "Discovery ranking에서 D#8로 하락한 것은 높은 base_norm(1.0)에도 "
            "불구하고 낮은 novelty(0.2)와 높은 penalty(0.7) 때문. "
            "효능은 최고이나 새로운 치료 전략으로서의 가치는 제한적."
        ),
    },
    "Temsirolimus": {
        "target_class": "standard",
        "differentiation": (
            "mTOR 억제제로, PI3K/AKT/mTOR 경로 표적. "
            "같은 계열의 everolimus가 유방암에서 승인되어 있어 "
            "완전한 신규 기전은 아니나, temsirolimus 자체의 유방암 적용은 새로운 시도."
        ),
        "novelty_significance": (
            "경로 novelty(0.5)는 중간 수준. 이미 검증된 PI3K/mTOR 경로이나, "
            "temsirolimus의 유방암 특이적 임상 데이터가 축적되면 "
            "everolimus의 한계를 극복할 수 있는 대안이 될 수 있음."
        ),
    },
    "Paclitaxel": {
        "target_class": "standard",
        "differentiation": (
            "미세소관 안정화 약물로, Docetaxel과 동일 계열의 표준 BRCA 치료제. "
            "novelty 최저(0.2)."
        ),
        "novelty_significance": (
            "Discovery D#10으로, Docetaxel과 유사한 패턴. "
            "높은 효능(base_norm=0.929)이나 기존 치료제로서 discovery 가치 제한적."
        ),
    },
    "Vinblastine": {
        "target_class": "standard",
        "differentiation": (
            "미세소관 탈안정화 약물로, Taxane과 반대 기전이지만 동일 Mitosis 경로. "
            "기존 BRCA 치료에 포함."
        ),
        "novelty_significance": (
            "Discovery D#11. 높은 효능이나 novelty=0.2, penalty=0.7로 "
            "discovery 점수가 크게 감소."
        ),
    },
    "Vinorelbine": {
        "target_class": "standard",
        "differentiation": (
            "Vinca alkaloid 계열. Vinblastine과 동일 기전 계열로 "
            "novelty 최저 그룹."
        ),
        "novelty_significance": (
            "Discovery D#12. Vinblastine과 유사한 패턴. "
            "기존 치료제로서의 효능은 검증되었으나 새로운 발견은 아님."
        ),
    },
    "Tanespimycin": {
        "target_class": "moderate",
        "differentiation": (
            "HSP90 억제제로, 기존 BRCA 치료에서 사용되지 않는 단백질 안정성 표적. "
            "다중 client protein(HER2, AKT, RAF) 분해를 동시 유도하는 독특한 기전."
        ),
        "novelty_significance": (
            "Protein stability 경로(pathway_novelty=1.0)는 유방암에서 미개척 영역. "
            "HER2+ 유방암에서의 임상시험 데이터가 기전적 근거를 지지. "
            "Discovery V#16에서 D#13으로 소폭 상승."
        ),
    },
    "Topotecan": {
        "target_class": "standard",
        "differentiation": (
            "TOP1 억제제로, DNA replication 경로의 표준 항암 표적. "
            "유방암에서 직접 승인되지는 않았으나, 동일 경로의 약물이 표준치료에 포함."
        ),
        "novelty_significance": (
            "Discovery D#14로 크게 하락(V#7). 높은 효능에도 불구하고 "
            "standard target + high penalty(0.7)로 discovery 점수 저하."
        ),
    },
    "AZD2014": {
        "target_class": "moderate",
        "differentiation": (
            "mTORC1/mTORC2 이중 억제제로, 기존 mTORC1 단독 억제(rapalog)와 차별화. "
            "mTORC2 추가 억제로 AKT 피드백 활성화 차단."
        ),
        "novelty_significance": (
            "PI3K/mTOR 경로(pathway_novelty=0.5) + moderate target. "
            "Discovery D#15=V#15로 순위 변동 없음. "
            "기존 경로이나 이중 억제라는 차별점이 있어 중간 수준의 novelty."
        ),
    },
}

# ── Category descriptions ──
CATEGORY_DESC = {
    "A": "Known BRCA Drug — FDA 승인 또는 NCCN 가이드라인에 포함된 유방암 치료제",
    "B": "BRCA Research Drug — 유방암 관련 연구/전임상 근거가 있는 약물",
    "C": "Pure Repurposing Candidate — 원래 적응증이 유방암과 무관한 재창출 후보",
}


def load_all_data():
    """모든 입력 데이터 로드."""
    print("  Loading data sources...")
    t0 = time.time()

    # 1. Discovery v2 Top 15
    disc = pd.read_csv(DISCOVERY_CSV)
    disc["canonical_drug_id"] = disc["canonical_drug_id"].astype(str)
    print(f"    Discovery Top 15: {len(disc)} drugs")

    # 2. ADMET results
    admet_df = pd.read_csv(ADMET_CSV)
    admet_df["drug_id"] = admet_df["drug_id"].astype(str)
    admet_map = admet_df.set_index("drug_id").to_dict(orient="index")
    print(f"    ADMET: {len(admet_map)} drug profiles")

    # 3. Dedup top 30 (for additional info)
    dedup = pd.read_csv(DEDUP_CSV)
    dedup["canonical_drug_id"] = dedup["canonical_drug_id"].astype(str)
    dedup_map = dedup.set_index("canonical_drug_id").to_dict(orient="index")
    print(f"    Dedup: {len(dedup_map)} drugs")

    # 4. METABRIC results
    metabric_scores = {}
    try:
        with open(METABRIC_JSON) as f:
            metabric = json.load(f)
        for d in metabric.get("all_30_scores", []):
            metabric_scores[str(d["canonical_drug_id"])] = d
        print(f"    METABRIC: {len(metabric_scores)} drug scores")
    except Exception as e:
        print(f"    METABRIC: 로드 실패 ({e})")

    dt = time.time() - t0
    print(f"    ({dt:.1f}s)")

    return {
        "discovery": disc,
        "admet_map": admet_map,
        "dedup_map": dedup_map,
        "metabric_scores": metabric_scores,
    }


def generate_discovery_explanation(row, ctx):
    """단일 약물에 대한 6-section Discovery Markdown 생성."""
    drug_id = str(row["canonical_drug_id"])
    drug_name = str(row["drug_name"])
    category = str(row["category"])
    target = str(row.get("target", "N/A"))
    pathway = str(row.get("pathway", "N/A"))
    d_rank = int(row["discovery_rank"])
    v_rank = int(row["validation_rank"])
    delta = v_rank - d_rank
    d_score = float(row["discovery_score"])
    base_norm = float(row["base_norm"])
    novelty_score = float(row["novelty_score"])
    novelty_component = float(row["novelty_component"])
    known_penalty = float(row["known_penalty"])
    target_novelty = float(row["target_novelty"])
    target_class = str(row["target_class"])
    pathway_novelty = float(row["pathway_novelty"])
    pred_ic50 = float(row.get("mean_pred_ic50", 0))
    sens_rate = float(row.get("sensitivity_rate", 0))

    # Additional data
    admet = ctx["admet_map"].get(drug_id, {})
    dedup = ctx["dedup_map"].get(drug_id, {})
    met = ctx["metabric_scores"].get(drug_id, {})

    admet_decision = admet.get("admet_decision", "N/A")
    flags_raw = admet.get("flags", "")
    flags = str(flags_raw) if pd.notna(flags_raw) else ""
    tox_interp_raw = admet.get("tox_interpretation", "")
    tox_interp = str(tox_interp_raw) if pd.notna(tox_interp_raw) else ""
    safety_score = admet.get("safety_score", "N/A")

    validation_score = met.get("validation_score", "N/A")
    known_brca = met.get("known_brca", 0)

    true_sens = dedup.get("true_sensitivity_rate")
    n_samples = dedup.get("n_samples", row.get("n_samples", "N/A"))

    # Knowledge bases
    kb = MECHANISM_DB.get(drug_name, {})
    nb = NOVELTY_DB.get(drug_name, {})

    lines = []

    # ── Header ──
    cat_badge = {"A": "Known BRCA", "B": "BRCA Research", "C": "Pure Repurposing"}.get(category, category)
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    delta_dir = "상승" if delta > 0 else ("하락" if delta < 0 else "변동 없음")

    lines.append(f"# {drug_name} — Discovery 관점 분석")
    lines.append("")
    lines.append(f"| 항목 | 값 |")
    lines.append(f"|---|---|")
    lines.append(f"| **Discovery Rank** | D#{d_rank} / 15 |")
    lines.append(f"| **Validation Rank** | V#{v_rank} / 28 |")
    lines.append(f"| **Rank Delta** | {delta_str} ({delta_dir}) |")
    lines.append(f"| **Category** | **{category}** ({cat_badge}) |")
    lines.append(f"| **Target** | {target} |")
    lines.append(f"| **Pathway** | {pathway} |")
    lines.append(f"| **Discovery Score** | {d_score:.4f} |")
    lines.append(f"| **ADMET** | {admet_decision} |")
    lines.append("")

    # ══ Section 1: Discovery Context ══
    lines.append("## 1. Discovery Context (발견 맥락)")
    lines.append("")

    lines.append("**Score 분해:**")
    lines.append(f"```")
    lines.append(f"discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))")
    lines.append(f"               = 0.5 x {base_norm:.4f} + 0.5 x ({novelty_score:.2f} x (1 - {known_penalty}))")
    lines.append(f"               = {0.5*base_norm:.4f} + {novelty_component:.4f}")
    lines.append(f"               = {d_score:.4f}")
    lines.append(f"```")
    lines.append("")

    lines.append(f"| 구성요소 | 값 | 해석 |")
    lines.append(f"|---|---|---|")
    lines.append(f"| base_norm (효능 percentile) | {base_norm:.4f} | 28개 약물 중 {base_norm*100:.1f}% 위치 |")
    lines.append(f"| target_novelty | {target_novelty} | {target_class} |")
    lines.append(f"| pathway_novelty | {pathway_novelty} | {pathway} |")
    lines.append(f"| novelty_score | {novelty_score:.2f} | 0.5×target + 0.5×pathway |")
    lines.append(f"| known_penalty | {known_penalty} | Cat {category} 기반 |")
    lines.append(f"| novelty_component | {novelty_component:.4f} | novelty × (1 - penalty) |")
    lines.append("")

    # Why high/low in discovery
    if delta > 0:
        lines.append(f"**Discovery 상승 사유 (V#{v_rank} → D#{d_rank}, {delta_str}):**")
        reasons = []
        if target_novelty >= 0.8:
            reasons.append(f"높은 target novelty ({target_novelty}, {target_class})")
        if pathway_novelty >= 0.6:
            reasons.append(f"높은 pathway novelty ({pathway_novelty})")
        if known_penalty <= 0.1:
            reasons.append(f"낮은 known penalty ({known_penalty}, Cat {category})")
        if not reasons:
            reasons.append("novelty 가중으로 인한 상대적 상승")
        for r in reasons:
            lines.append(f"- {r}")
    elif delta < 0:
        lines.append(f"**Discovery 하락 사유 (V#{v_rank} → D#{d_rank}, {delta_str}):**")
        reasons = []
        if known_penalty >= 0.5:
            reasons.append(f"높은 known penalty ({known_penalty}, Cat {category} 기승인 약물)")
        if target_novelty <= 0.3:
            reasons.append(f"낮은 target novelty ({target_novelty}, {target_class})")
        if pathway_novelty <= 0.3:
            reasons.append(f"낮은 pathway novelty ({pathway_novelty})")
        if not reasons:
            reasons.append("기존 치료제로서 novelty 가중에 의한 하락")
        for r in reasons:
            lines.append(f"- {r}")
    else:
        lines.append(f"**순위 변동 없음 (V#{v_rank} = D#{d_rank}):** 효능과 novelty가 균형을 이룸.")
    lines.append("")

    # ══ Section 2: Mechanism of Action ══
    lines.append("## 2. Mechanism of Action (작용 기전)")
    lines.append("")
    if kb.get("moa"):
        lines.append(kb["moa"])
    else:
        lines.append(f"{drug_name}은(는) {target}을(를) 표적으로 하여 {pathway} 경로에 작용한다.")
    lines.append("")

    if kb.get("brca_relevance"):
        lines.append("**유방암 관련성:**")
        lines.append(kb["brca_relevance"])
        lines.append("")

    # ══ Section 3: Novelty vs Known BRCA drugs ══
    lines.append("## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)")
    lines.append("")

    lines.append(f"**Target Class:** {target_class} (target_novelty={target_novelty})")
    lines.append(f"**Pathway:** {pathway} (pathway_novelty={pathway_novelty})")
    lines.append("")

    if nb.get("differentiation"):
        lines.append("**기존 BRCA 치료제 대비 차별점:**")
        lines.append(nb["differentiation"])
        lines.append("")

    if nb.get("novelty_significance"):
        lines.append("**새로운 기전의 의미:**")
        lines.append(nb["novelty_significance"])
        lines.append("")

    # Standard targets reference
    lines.append("**참고 — 기존 BRCA 표준 표적:**")
    lines.append("- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2")
    lines.append("- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2")
    lines.append("- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3")
    lines.append("- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함")
    lines.append("")

    # ══ Section 4: Supporting Evidence ══
    lines.append("## 4. Supporting Evidence (근거 자료)")
    lines.append("")

    if kb.get("evidence"):
        lines.append(kb["evidence"])
        lines.append("")

    lines.append("**모델 예측 데이터:**")
    lines.append(f"- 앙상블 예측 IC50 (ln): {pred_ic50:.4f}")
    lines.append(f"- 예측 감수성률: {sens_rate:.0%}")
    lines.append(f"- GDSC2 유방암 세포주 수: {n_samples}")
    if pd.notna(true_sens) if not isinstance(true_sens, str) else (true_sens and true_sens != 'nan'):
        try:
            lines.append(f"- 실제 감수성률: {float(true_sens):.0%}")
        except (ValueError, TypeError):
            pass
    lines.append("")

    # METABRIC
    if met:
        lines.append("**METABRIC 외부검증:**")
        te = "발현 확인" if met.get("target_expressed") == 1 else "발현 미확인"
        bp = "관련 경로" if met.get("brca_pathway") == 1 else "비관련"
        ss = "유의미" if met.get("survival_sig") == 1 else "유의하지 않음"
        kb_str = "기존 치료제" if known_brca == 1 else "신규 후보"
        lines.append(f"- 타겟 발현: {te}")
        lines.append(f"- BRCA 경로: {bp}")
        lines.append(f"- 생존 분석: {ss} (p={met.get('survival_p', 'N/A')})")
        lines.append(f"- 검증 점수: {validation_score}")
        lines.append(f"- Known BRCA: {kb_str}")
        lines.append("")

    # Category-specific evidence level
    lines.append("**근거 수준 (Category별):**")
    if category == "A":
        lines.append("- Category A: 임상 근거 확립. FDA 승인 또는 NCCN 가이드라인 포함.")
        lines.append("- Discovery 관점에서 새로운 적응증 발굴보다는 기존 효능 재확인에 해당.")
    elif category == "B":
        lines.append("- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.")
        lines.append("- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.")
    else:
        lines.append("- Category C: 원래 적응증과 무관한 완전 재창출 후보.")
        lines.append("- 기전적 연관성(예: 경로 교차) 기반의 가설 단계 근거.")
    lines.append("")

    # ══ Section 5: ADMET / Safety ══
    lines.append("## 5. ADMET / Safety (안전성 평가)")
    lines.append("")

    lines.append(f"| 항목 | 결과 |")
    lines.append(f"|---|---|")
    lines.append(f"| **ADMET Decision** | **{admet_decision}** |")
    lines.append(f"| **Safety Score** | {safety_score} |")
    lines.append(f"| **검사 수** | {admet.get('n_assays_tested', 'N/A')} / 22 |")
    lines.append(f"| **Pass** | {admet.get('n_pass', 'N/A')} |")
    lines.append(f"| **Caution** | {admet.get('n_caution', 'N/A')} |")
    lines.append(f"| **Flags** | {flags if flags else 'None'} |")
    lines.append("")

    lines.append(f"**해석:** {tox_interp if tox_interp else 'N/A'}")
    lines.append("")

    if admet_decision == "CAUTION":
        lines.append(f"> **CAUTION 경고:** {drug_name}은(는) ADMET 검증에서 주의(CAUTION) 판정. "
                      f"Cat {category} 기준 추가 안전성 연구 필요. Flags: {flags}")
        lines.append("")

    # ══ Section 6: Repurposing Potential ══
    lines.append("## 6. Repurposing Potential (재창출 가능성)")
    lines.append("")

    # Compute assessment factors
    pos_factors = []
    neg_factors = []

    if d_rank <= 5:
        pos_factors.append(f"Discovery Top 5 (D#{d_rank})")
    if novelty_score >= 0.8:
        pos_factors.append(f"높은 novelty ({novelty_score})")
    if target_class == "novel":
        pos_factors.append("novel target class")
    if base_norm >= 0.5:
        pos_factors.append(f"양호한 base 효능 (percentile={base_norm:.2f})")
    if admet_decision == "PASS":
        pos_factors.append("ADMET 통과")
    if validation_score != "N/A" and float(validation_score) >= 5.0:
        pos_factors.append(f"METABRIC 검증 양호 ({validation_score})")

    if admet_decision == "CAUTION":
        neg_factors.append("ADMET 주의 판정")
    if sens_rate < 0.1 and base_norm < 0.5:
        neg_factors.append("낮은 효능/감수성")
    if int(row.get("n_samples", 0)) <= 5:
        neg_factors.append(f"제한된 샘플 수 (n={row.get('n_samples', 'N/A')})")
    if known_brca == 0 and category == "C":
        neg_factors.append("유방암 임상 근거 부재")

    # Overall potential
    n_pos = len(pos_factors)
    if category == "C" and novelty_score >= 0.8:
        potential = "높음 — 완전 재창출 (High Repurposing Value)"
    elif admet_decision == "CAUTION":
        potential = "조건부 (Conditional — ADMET 재평가 필요)"
    elif n_pos >= 4:
        potential = "높음 (High)"
    elif n_pos >= 2:
        potential = "중간 (Moderate)"
    else:
        potential = "낮음 (Low)"

    # Category A는 재창출 가치가 다름
    if category == "A":
        potential = "해당 없음 — 이미 BRCA 승인 약물 (기존 효능 재확인)"

    lines.append(f"**재창출 가치 평가: {potential}**")
    lines.append("")

    if pos_factors:
        lines.append("긍정적 요인:")
        for f in pos_factors:
            lines.append(f"- (+) {f}")
        lines.append("")

    if neg_factors:
        lines.append("부정적 요인:")
        for f in neg_factors:
            lines.append(f"- (-) {f}")
        lines.append("")

    # Next steps
    lines.append("**다음 검증 단계:**")
    if category == "A":
        lines.append("1. 기존 임상 데이터와 모델 예측의 일치성 재확인")
        lines.append("2. 아형별(TNBC/HR+/HER2+) 감수성 차이 분석")
        lines.append("3. 기존 병용 요법에서의 최적 위치 재평가")
    elif category == "B":
        lines.append("1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)")
        lines.append("2. 전임상 유방암 세포주/오가노이드 효능 확인")
        lines.append("3. 기존 BRCA 치료제와의 병용 시너지 탐색")
        lines.append("4. 유방암 Phase I/II 임상시험 설계 검토")
    else:  # C
        lines.append("1. 표적 기전의 유방암 관련성 전임상 검증 (필수)")
        lines.append("2. 유방암 세포주/PDX 모델에서의 단독 효능 확인")
        lines.append("3. Gamma-secretase/Notch 경로의 유방암 줄기세포 영향 분석")
        lines.append("4. 기존 적응증(알츠하이머) 임상 안전성 데이터 재활용 검토")
        lines.append("5. 유방암 Phase I basket trial 포함 가능성 탐색")
    lines.append("")

    lines.append("---")
    lines.append(f"*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | "
                  f"데이터: GDSC2 + METABRIC + ADMET*")

    return "\n".join(lines)


def main():
    t0 = time.time()
    print("=" * 70)
    print("  Discovery Top 15 LLM Explanation Generator")
    print("=" * 70)

    ctx = load_all_data()
    disc = ctx["discovery"]

    print(f"\n{'─'*70}")
    print(f"  Generating discovery explanations for {len(disc)} drugs...")
    print(f"{'─'*70}")

    results = []
    n_success = 0
    n_fail = 0

    for _, row in disc.iterrows():
        drug_name = str(row["drug_name"])
        drug_id = str(row["canonical_drug_id"])
        d_rank = int(row["discovery_rank"])

        print(f"\n  [D#{d_rank}/{len(disc)}] {drug_name} (ID={drug_id}, Cat={row['category']})")

        try:
            md_content = generate_discovery_explanation(row, ctx)
            safe_name = re.sub(r'[^\w\-]', '_', drug_name)
            md_path = OUTPUT_DIR / f"{safe_name}_discovery_explanation.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            n_success += 1
            print(f"    OK → {md_path.name} ({len(md_content)} chars)")
            results.append({
                "discovery_rank": d_rank,
                "drug_id": drug_id,
                "drug_name": drug_name,
                "category": row["category"],
                "discovery_score": float(row["discovery_score"]),
                "file": md_path.name,
                "chars": len(md_content),
                "status": "success",
            })
        except Exception as e:
            n_fail += 1
            print(f"    FAIL: {str(e)[:200]}")
            results.append({
                "discovery_rank": d_rank,
                "drug_id": drug_id,
                "drug_name": drug_name,
                "category": row["category"],
                "discovery_score": float(row.get("discovery_score", 0)),
                "file": None,
                "chars": 0,
                "status": f"error: {str(e)[:100]}",
            })

    # Summary JSON
    summary = {
        "description": "Discovery Top 15 LLM Explanation Summary (v2 ranking 기반)",
        "total": len(disc),
        "success": n_success,
        "fail": n_fail,
        "results": results,
    }
    summary_path = OUTPUT_DIR / "discovery_explanation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    dt = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  Discovery Explanation 완료")
    print(f"  성공: {n_success}/{len(disc)}, 실패: {n_fail}/{len(disc)}")
    print(f"  출력: {OUTPUT_DIR}")
    print(f"  소요시간: {dt:.1f}s")
    print(f"{'='*70}")

    # Print result table
    print(f"\n  {'D#':>3}  {'Drug':<22} {'Cat':>3} {'Score':>6} {'Status':<8} {'File'}")
    print(f"  {'-'*70}")
    for r in results:
        fname = r["file"] or "N/A"
        print(f"  {r['discovery_rank']:>3}  {r['drug_name']:<22} {r['category']:>3} "
              f"{r['discovery_score']:>6.3f} {r['status']:<8} {fname}")


if __name__ == "__main__":
    main()
