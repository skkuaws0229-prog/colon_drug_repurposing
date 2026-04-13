# TW 37 — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#4 / 15 |
| **Validation Rank** | V#13 / 28 |
| **Rank Delta** | +9 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | BCL2, BCL-XL, MCL1 |
| **Pathway** | Apoptosis regulation |
| **Discovery Score** | 0.6457 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.5714 + 0.5 x (0.80 x (1 - 0.1))
               = 0.2857 + 0.7200
               = 0.6457
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.5714 | 28개 약물 중 57.1% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 0.6 | Apoptosis regulation |
| novelty_score | 0.80 | 0.5×target + 0.5×pathway |
| known_penalty | 0.1 | Cat B 기반 |
| novelty_component | 0.7200 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#13 → D#4, +9):**
- 높은 target novelty (1.0, novel)
- 높은 pathway novelty (0.6)
- 낮은 known penalty (0.1, Cat B)

## 2. Mechanism of Action (작용 기전)

BCL-2 family 억제제로, BH3 mimetic 계열에 속한다. BCL-2, BCL-XL, MCL-1에 결합하여 항-세포사멸(anti-apoptotic) 기능을 차단하고, BAX/BAK 매개 미토콘드리아 외막 투과(MOMP)를 유도한다.

**유방암 관련성:**
BCL-2는 ER+ 유방암에서 과발현. MCL-1은 TNBC에서 약물 저항성의 주요 매개자. BH3 mimetic(venetoclax 등)의 유방암 임상시험이 진행 중이며, 같은 계열의 기전적 근거.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** Apoptosis regulation (pathway_novelty=0.6)

**기존 BRCA 치료제 대비 차별점:**
BCL-2/BCL-XL/MCL-1 동시 억제 BH3 mimetic. 기존 BRCA 치료제 중 apoptosis 직접 유도 약물은 없음. Venetoclax(BCL-2 선택적)가 혈액암에서 승인되었으나 고형암은 미개척.

**새로운 기전의 의미:**
유방암, 특히 TNBC에서 MCL-1 과발현이 약물 저항성의 주요 원인. BCL-2 + MCL-1 동시 억제는 단일 표적 BH3 mimetic 대비 더 넓은 항종양 스펙트럼 기대. Apoptosis 직접 유도는 기존 세포독성 항암제와 다른 기전으로 병용 가능성 높음.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

전임상 연구에서 다양한 암종 대상 효과 확인. 유방암 특이적 임상 데이터는 제한적이나, BCL-2/MCL-1 표적의 유방암 관련성은 확립됨.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): 1.1938
- 예측 감수성률: 0%
- GDSC2 유방암 세포주 수: 14
- 실제 감수성률: 7%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의하지 않음 (p=0.10534012238172552)
- 검증 점수: 2.75
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

**재창출 가치 평가: 높음 (High)**

긍정적 요인:
- (+) Discovery Top 5 (D#4)
- (+) 높은 novelty (0.8)
- (+) novel target class
- (+) 양호한 base 효능 (percentile=0.57)
- (+) ADMET 통과

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*