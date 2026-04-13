# Docetaxel — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#8 / 15 |
| **Validation Rank** | V#1 / 28 |
| **Rank Delta** | -7 (하락) |
| **Category** | **A** (Known BRCA) |
| **Target** | Microtubule stabiliser |
| **Pathway** | Mitosis |
| **Discovery Score** | 0.5300 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 1.0000 + 0.5 x (0.20 x (1 - 0.7))
               = 0.5000 + 0.0600
               = 0.5300
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 1.0000 | 28개 약물 중 100.0% 위치 |
| target_novelty | 0.2 | standard |
| pathway_novelty | 0.2 | Mitosis |
| novelty_score | 0.20 | 0.5×target + 0.5×pathway |
| known_penalty | 0.7 | Cat A 기반 |
| novelty_component | 0.0600 | novelty × (1 - penalty) |

**Discovery 하락 사유 (V#1 → D#8, -7):**
- 높은 known penalty (0.7, Cat A 기승인 약물)
- 낮은 target novelty (0.2, standard)
- 낮은 pathway novelty (0.2)

## 2. Mechanism of Action (작용 기전)

Taxane 계열 항암제로, 미세소관(microtubule)에 결합하여 안정화시킴으로써 정상적인 세포분열을 억제한다. 방추사 형성을 방해하여 유사분열(mitosis)을 G2/M 단계에서 정지시킨다.

**유방암 관련성:**
유방암 1차 치료제(NCCN Category 1). HER2-양성/삼중음성(TNBC) 포함 모든 아형에 사용. AC-T(anthracycline+cyclophosphamide 후 taxane) 요법의 핵심 구성요소.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** standard (target_novelty=0.2)
**Pathway:** Mitosis (pathway_novelty=0.2)

**기존 BRCA 치료제 대비 차별점:**
미세소관 안정화 약물로, 유방암 1차 표준 치료제. 가장 잘 확립된 기존 BRCA 약물 중 하나로 novelty는 낮음.

**새로운 기전의 의미:**
Discovery ranking에서 D#8로 하락한 것은 높은 base_norm(1.0)에도 불구하고 낮은 novelty(0.2)와 높은 penalty(0.7) 때문. 효능은 최고이나 새로운 치료 전략으로서의 가치는 제한적.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

TAX 316/317 임상시험에서 전이성 유방암 치료 효과 입증. BCIRG 001에서 보조요법으로 생존율 개선 확인.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -4.0820
- 예측 감수성률: 100%
- GDSC2 유방암 세포주 수: 25
- 실제 감수성률: 72%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 9.45
- Known BRCA: 기존 치료제

**근거 수준 (Category별):**
- Category A: 임상 근거 확립. FDA 승인 또는 NCCN 가이드라인 포함.
- Discovery 관점에서 새로운 적응증 발굴보다는 기존 효능 재확인에 해당.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 6.83 |
| **검사 수** | 12 / 22 |
| **Pass** | 7 |
| **Caution** | 1 |
| **Flags** | DILI (Drug-Induced Liver Injury)(+) |

**해석:** 허용 (기승인 약물, 관리 가능한 독성: DILI (Drug-Induced Liver Injury)(+))

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 해당 없음 — 이미 BRCA 승인 약물 (기존 효능 재확인)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=1.00)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (9.45)

**다음 검증 단계:**
1. 기존 임상 데이터와 모델 예측의 일치성 재확인
2. 아형별(TNBC/HR+/HER2+) 감수성 차이 분석
3. 기존 병용 요법에서의 최적 위치 재평가

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*