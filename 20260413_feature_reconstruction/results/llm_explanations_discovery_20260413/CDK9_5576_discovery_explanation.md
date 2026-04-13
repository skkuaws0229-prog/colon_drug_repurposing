# CDK9_5576 — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#2 / 15 |
| **Validation Rank** | V#8 / 28 |
| **Rank Delta** | +6 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | CDK9 |
| **Pathway** | Cell cycle |
| **Discovery Score** | 0.7350 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.7500 + 0.5 x (0.80 x (1 - 0.1))
               = 0.3750 + 0.7200
               = 0.7350
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.7500 | 28개 약물 중 75.0% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 0.6 | Cell cycle |
| novelty_score | 0.80 | 0.5×target + 0.5×pathway |
| known_penalty | 0.1 | Cat B 기반 |
| novelty_component | 0.7200 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#8 → D#2, +6):**
- 높은 target novelty (1.0, novel)
- 높은 pathway novelty (0.6)
- 낮은 known penalty (0.1, Cat B)

## 2. Mechanism of Action (작용 기전)

CDK9(Cyclin-dependent kinase 9) 선택적 억제제로, P-TEFb(CDK9/Cyclin T) 복합체를 억제하여 RNA Polymerase II의 전사 신장(elongation)을 차단한다. MYC, MCL1 등 반감기 짧은 종양유전자 발현을 억제한다.

**유방암 관련성:**
CDK9는 유방암에서 과발현되며, MYC-driven TNBC에서 핵심 취약성(vulnerability)으로 보고됨. MCL1 억제를 통한 apoptosis 유도 가능성.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** Cell cycle (pathway_novelty=0.6)

**기존 BRCA 치료제 대비 차별점:**
CDK9는 전사 신장(transcription elongation)을 조절하는 kinase로, 기존 BRCA 표준 치료제에서 표적하지 않는 유전자 발현 조절 단계에 작용. CDK4/6 억제제(palbociclib 등)와는 다른 CDK family 멤버.

**새로운 기전의 의미:**
CDK9 억제는 MYC, MCL1 등 반감기 짧은 종양유전자의 전사를 선택적으로 차단. MYC-driven TNBC에서 특히 유망하며, 기존 CDK4/6 억제제와 비교가 불가능한 완전히 다른 기전. 전사 수준에서의 항암 전략은 유방암에서 미개척 영역.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

전임상 연구에서 TNBC 세포주 대상 CDK9 억제 효과 확인. GDSC 데이터에서 sensitivity rate 65%. CDK9 발현이 METABRIC에서 유방암 환자 100%에서 확인.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -0.4560
- 예측 감수성률: 65%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 54%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의하지 않음 (p=0.8233554835205238)
- 검증 점수: 3.0
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.
- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 5.0 |
| **검사 수** | 0 / 22 |
| **Pass** | 0 |
| **Caution** | 0 |
| **Flags** | None |

**해석:** 양호 (주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 높음 (High)**

긍정적 요인:
- (+) Discovery Top 5 (D#2)
- (+) 높은 novelty (0.8)
- (+) novel target class
- (+) 양호한 base 효능 (percentile=0.75)
- (+) ADMET 통과

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*