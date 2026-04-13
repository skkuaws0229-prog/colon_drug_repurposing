# Dactinomycin — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#7 / 15 |
| **Validation Rank** | V#2 / 28 |
| **Rank Delta** | -5 (하락) |
| **Category** | **A** (Known BRCA) |
| **Target** | RNA polymerase |
| **Pathway** | Other |
| **Discovery Score** | 0.5946 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.9643 + 0.5 x (0.75 x (1 - 0.7))
               = 0.4822 + 0.2250
               = 0.5946
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.9643 | 28개 약물 중 96.4% 위치 |
| target_novelty | 0.5 | moderate |
| pathway_novelty | 1.0 | Other |
| novelty_score | 0.75 | 0.5×target + 0.5×pathway |
| known_penalty | 0.7 | Cat A 기반 |
| novelty_component | 0.2250 | novelty × (1 - penalty) |

**Discovery 하락 사유 (V#2 → D#7, -5):**
- 높은 known penalty (0.7, Cat A 기승인 약물)

## 2. Mechanism of Action (작용 기전)

Actinomycin D로도 불리며, DNA 이중나선의 minor groove에 삽입(intercalation)되어 RNA polymerase의 전사를 억제한다. DNA-의존적 RNA 합성을 차단하여 세포 사멸을 유도한다.

**유방암 관련성:**
전통적으로 윌름스종양, 횡문근육종 등에 사용되나, 유방암에서도 강력한 세포독성 활성이 GDSC 데이터에서 확인됨. RNA 합성 억제는 빠르게 증식하는 유방암 세포에 효과적일 수 있음.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** moderate (target_novelty=0.5)
**Pathway:** Other (pathway_novelty=1.0)

**기존 BRCA 치료제 대비 차별점:**
RNA polymerase 억제제로, 전사 차단을 통해 작용. 기존 BRCA 치료에서 RNA 합성 직접 억제 약물은 사용되지 않으며, DNA 수준이 아닌 RNA 수준에서의 작용이 차별점.

**새로운 기전의 의미:**
Known BRCA 치료제(Category A)이나, 유방암에서의 사용은 제한적. RNA 합성 억제 기전은 빠르게 증식하는 세포에 선택적이며, 기존 DNA 표적 약물과 비교차 저항성 기대.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

GDSC2 데이터에서 유방암 세포주 대상 높은 감수성(sensitivity rate 100%) 확인. 임상적 유방암 적용은 제한적이나 전임상 근거 존재.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -2.2883
- 예측 감수성률: 100%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 96%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 비관련
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 7.9
- Known BRCA: 기존 치료제

**근거 수준 (Category별):**
- Category A: 임상 근거 확립. FDA 승인 또는 NCCN 가이드라인 포함.
- Discovery 관점에서 새로운 적응증 발굴보다는 기존 효능 재확인에 해당.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 7.0 |
| **검사 수** | 5 / 22 |
| **Pass** | 3 |
| **Caution** | 1 |
| **Flags** | DILI (Drug-Induced Liver Injury)(+) |

**해석:** 허용 (기승인 약물, 관리 가능한 독성: DILI (Drug-Induced Liver Injury)(+))

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 해당 없음 — 이미 BRCA 승인 약물 (기존 효능 재확인)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=0.96)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (7.9)

**다음 검증 단계:**
1. 기존 임상 데이터와 모델 예측의 일치성 재확인
2. 아형별(TNBC/HR+/HER2+) 감수성 차이 분석
3. 기존 병용 요법에서의 최적 위치 재평가

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*