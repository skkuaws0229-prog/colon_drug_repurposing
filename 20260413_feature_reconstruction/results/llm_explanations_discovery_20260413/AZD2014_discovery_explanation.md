# AZD2014 — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#15 / 15 |
| **Validation Rank** | V#15 / 28 |
| **Rank Delta** | 0 (변동 없음) |
| **Category** | **B** (BRCA Research) |
| **Target** | mTORC1, mTORC2 |
| **Pathway** | PI3K/MTOR signaling |
| **Discovery Score** | 0.4000 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.5000 + 0.5 x (0.50 x (1 - 0.4))
               = 0.2500 + 0.3000
               = 0.4000
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.5000 | 28개 약물 중 50.0% 위치 |
| target_novelty | 0.5 | moderate |
| pathway_novelty | 0.5 | PI3K/MTOR signaling |
| novelty_score | 0.50 | 0.5×target + 0.5×pathway |
| known_penalty | 0.4 | Cat B 기반 |
| novelty_component | 0.3000 | novelty × (1 - penalty) |

**순위 변동 없음 (V#15 = D#15):** 효능과 novelty가 균형을 이룸.

## 2. Mechanism of Action (작용 기전)

mTORC1/mTORC2 이중 억제제(vistusertib). Rapamycin 유사체(rapalog)와 달리 mTORC2도 억제하여 AKT 피드백 활성화를 차단한다. PI3K/AKT/mTOR 경로를 보다 완전하게 억제.

**유방암 관련성:**
PI3K/AKT/mTOR 경로 과활성은 HR+/HER2- 유방암의 핵심 발암기전. mTORC1만 억제하는 everolimus 대비 mTORC2 추가 억제로 저항성 극복 가능성. 유방암 Phase II 임상 진행됨.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** moderate (target_novelty=0.5)
**Pathway:** PI3K/MTOR signaling (pathway_novelty=0.5)

**기존 BRCA 치료제 대비 차별점:**
mTORC1/mTORC2 이중 억제제로, 기존 mTORC1 단독 억제(rapalog)와 차별화. mTORC2 추가 억제로 AKT 피드백 활성화 차단.

**새로운 기전의 의미:**
PI3K/mTOR 경로(pathway_novelty=0.5) + moderate target. Discovery D#15=V#15로 순위 변동 없음. 기존 경로이나 이중 억제라는 차별점이 있어 중간 수준의 novelty.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

MANTA 연구(HR+ 전이성 유방암)에서 fulvestrant 병용 평가. 전임상에서 everolimus 내성 극복 효과 확인.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): 1.3807
- 예측 감수성률: 0%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 4%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 5.15
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.
- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 10.0 |
| **검사 수** | 2 / 22 |
| **Pass** | 2 |
| **Caution** | 0 |
| **Flags** | None |

**해석:** 양호 (주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 중간 (Moderate)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=0.50)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (5.15)

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*