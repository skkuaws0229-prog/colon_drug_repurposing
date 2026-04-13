# Tanespimycin — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#13 / 15 |
| **Validation Rank** | V#16 / 28 |
| **Rank Delta** | +3 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | HSP90 |
| **Pathway** | Protein stability and degradation |
| **Discovery Score** | 0.4571 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.4643 + 0.5 x (0.75 x (1 - 0.4))
               = 0.2321 + 0.4500
               = 0.4571
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.4643 | 28개 약물 중 46.4% 위치 |
| target_novelty | 0.5 | moderate |
| pathway_novelty | 1.0 | Protein stability and degradation |
| novelty_score | 0.75 | 0.5×target + 0.5×pathway |
| known_penalty | 0.4 | Cat B 기반 |
| novelty_component | 0.4500 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#16 → D#13, +3):**
- 높은 pathway novelty (1.0)

## 2. Mechanism of Action (작용 기전)

HSP90(Heat Shock Protein 90) 억제제로, HSP90 chaperone 기능을 차단하여 다수의 client protein(HER2, AKT, RAF 등)의 분해를 유도한다. 동시에 여러 종양 신호경로를 차단하는 다중 표적 효과.

**유방암 관련성:**
HSP90은 HER2 단백질 안정화에 필수적. HER2+ 유방암에서 trastuzumab 병용 Phase II 결과 존재. HSP90 억제는 PI3K/AKT, MAPK 등 다중 경로를 동시에 억제 가능.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** moderate (target_novelty=0.5)
**Pathway:** Protein stability and degradation (pathway_novelty=1.0)

**기존 BRCA 치료제 대비 차별점:**
HSP90 억제제로, 기존 BRCA 치료에서 사용되지 않는 단백질 안정성 표적. 다중 client protein(HER2, AKT, RAF) 분해를 동시 유도하는 독특한 기전.

**새로운 기전의 의미:**
Protein stability 경로(pathway_novelty=1.0)는 유방암에서 미개척 영역. HER2+ 유방암에서의 임상시험 데이터가 기전적 근거를 지지. Discovery V#16에서 D#13으로 소폭 상승.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

Phase II 임상에서 HER2+ 전이성 유방암 대상 trastuzumab 병용 평가. 반응률은 제한적이나, 기전적 근거와 안전성 데이터 확보.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): 1.4131
- 예측 감수성률: 0%
- GDSC2 유방암 세포주 수: 28
- 실제 감수성률: 50%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 5.1
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.
- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 5.0 |
| **검사 수** | 2 / 22 |
| **Pass** | 1 |
| **Caution** | 1 |
| **Flags** | None |

**해석:** 양호 (주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 중간 (Moderate)**

긍정적 요인:
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (5.1)

부정적 요인:
- (-) 낮은 효능/감수성

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*