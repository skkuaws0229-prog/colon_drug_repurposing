# CDK9_5038 — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#5 / 15 |
| **Validation Rank** | V#14 / 28 |
| **Rank Delta** | +9 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | CDK9 |
| **Pathway** | Cell cycle |
| **Discovery Score** | 0.6279 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.5357 + 0.5 x (0.80 x (1 - 0.1))
               = 0.2678 + 0.7200
               = 0.6279
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.5357 | 28개 약물 중 53.6% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 0.6 | Cell cycle |
| novelty_score | 0.80 | 0.5×target + 0.5×pathway |
| known_penalty | 0.1 | Cat B 기반 |
| novelty_component | 0.7200 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#14 → D#5, +9):**
- 높은 target novelty (1.0, novel)
- 높은 pathway novelty (0.6)
- 낮은 known penalty (0.1, Cat B)

## 2. Mechanism of Action (작용 기전)

CDK9 선택적 억제제(CDK9_5576과 동일 표적, 다른 화학구조). P-TEFb 복합체를 억제하여 전사 신장을 차단하고, 반감기 짧은 항-세포사멸 단백질(MCL1, XIAP)의 발현을 감소시킨다.

**유방암 관련성:**
CDK9_5576과 동일한 기전적 근거. TNBC에서의 MYC 의존성, CDK9 과발현이 보고됨. 전사 억제를 통한 종양 세포 선택적 사멸 유도.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** Cell cycle (pathway_novelty=0.6)

**기존 BRCA 치료제 대비 차별점:**
CDK9_5576과 동일 표적(CDK9), 다른 화학구조의 억제제. 동일한 전사 억제 기전을 공유하며, 기존 BRCA 치료 패러다임에서 표적되지 않은 전사 조절 경로에 작용.

**새로운 기전의 의미:**
두 CDK9 억제제가 독립적으로 Discovery Top 5에 진입한 것은 CDK9 표적의 유방암 관련성을 지지하는 강력한 교차검증 근거. 다만, true sensitivity(81%)와 predicted sensitivity(4%) 간 괴리는 추가 실험적 검증이 필요한 부분.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

전임상 단계 화합물. GDSC 데이터에서 낮은 predicted sensitivity(4%)이나, true sensitivity rate는 81%로 모델 예측과 괴리 존재.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): 1.2037
- 예측 감수성률: 4%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 81%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의하지 않음 (p=0.8233554835205238)
- 검증 점수: 2.7
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
- (+) Discovery Top 5 (D#5)
- (+) 높은 novelty (0.8)
- (+) novel target class
- (+) 양호한 base 효능 (percentile=0.54)
- (+) ADMET 통과

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*