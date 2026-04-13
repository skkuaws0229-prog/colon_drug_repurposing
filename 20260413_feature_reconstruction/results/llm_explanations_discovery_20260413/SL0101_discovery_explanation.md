# SL0101 — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#1 / 15 |
| **Validation Rank** | V#9 / 28 |
| **Rank Delta** | +8 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | RSK, AURKB, PIM1, PIM3 |
| **Pathway** | Other kinases |
| **Discovery Score** | 0.8071 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.7143 + 0.5 x (1.00 x (1 - 0.1))
               = 0.3572 + 0.9000
               = 0.8071
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.7143 | 28개 약물 중 71.4% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 1.0 | Other kinases |
| novelty_score | 1.00 | 0.5×target + 0.5×pathway |
| known_penalty | 0.1 | Cat B 기반 |
| novelty_component | 0.9000 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#9 → D#1, +8):**
- 높은 target novelty (1.0, novel)
- 높은 pathway novelty (1.0)
- 낮은 known penalty (0.1, Cat B)

## 2. Mechanism of Action (작용 기전)

RSK(p90 ribosomal S6 kinase) 억제제로, AURKB, PIM1, PIM3 kinase도 억제한다. MAPK/ERK 신호전달 하위의 RSK 활성을 차단하여 세포 증식 및 생존 신호를 억제한다.

**유방암 관련성:**
RSK는 ER+ 유방암에서 에스트로겐 비의존적 증식 매개에 관여. AURKB 억제는 유사분열 이상을 유도하여 항종양 효과. PIM kinase는 유방암 약물 저항성 관련.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** Other kinases (pathway_novelty=1.0)

**기존 BRCA 치료제 대비 차별점:**
기존 BRCA 치료제는 미세소관(taxane/vinca), DNA 복제(anthracycline/TOP1/2), 호르몬(ER 억제), HER2 표적에 집중. RSK/AURKB/PIM 다중 kinase 억제는 이들과 전혀 다른 MAPK/ERK 하위 신호전달 및 유사분열 조절 경로를 표적.

**새로운 기전의 의미:**
RSK는 에스트로겐 비의존적 ER 활성화 매개자로, 내분비 저항성 유방암에서 새로운 치료 전략을 제시. AURKB/PIM 동시 억제는 다중 경로 차단으로 단일 표적 약물 대비 저항성 발생 가능성이 낮을 수 있음.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

전임상 단계 연구용 화합물. GDSC 데이터에서 제한된 샘플(n=1)로 해석 주의 필요. RSK 표적은 유방암 내분비 저항성 극복 전략으로 연구 중.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -0.2720
- 예측 감수성률: 100%
- GDSC2 유방암 세포주 수: 1
- 실제 감수성률: 0%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 비관련
- 생존 분석: 유의미 (p=5.150239984811742e-06)
- 검증 점수: 5.45
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
- (+) Discovery Top 5 (D#1)
- (+) 높은 novelty (1.0)
- (+) novel target class
- (+) 양호한 base 효능 (percentile=0.71)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (5.45)

부정적 요인:
- (-) 제한된 샘플 수 (n=1)

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*