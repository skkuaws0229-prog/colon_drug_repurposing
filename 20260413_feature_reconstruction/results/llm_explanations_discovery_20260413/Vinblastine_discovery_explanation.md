# Vinblastine — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#11 / 15 |
| **Validation Rank** | V#4 / 28 |
| **Rank Delta** | -7 (하락) |
| **Category** | **A** (Known BRCA) |
| **Target** | Microtubule destabiliser |
| **Pathway** | Mitosis |
| **Discovery Score** | 0.4764 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.8929 + 0.5 x (0.20 x (1 - 0.7))
               = 0.4465 + 0.0600
               = 0.4764
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.8929 | 28개 약물 중 89.3% 위치 |
| target_novelty | 0.2 | standard |
| pathway_novelty | 0.2 | Mitosis |
| novelty_score | 0.20 | 0.5×target + 0.5×pathway |
| known_penalty | 0.7 | Cat A 기반 |
| novelty_component | 0.0600 | novelty × (1 - penalty) |

**Discovery 하락 사유 (V#4 → D#11, -7):**
- 높은 known penalty (0.7, Cat A 기승인 약물)
- 낮은 target novelty (0.2, standard)
- 낮은 pathway novelty (0.2)

## 2. Mechanism of Action (작용 기전)

Vinca alkaloid 계열로, tubulin의 중합(polymerization)을 억제하여 미세소관 형성을 방해한다. Taxane과 반대 기전이지만 동일하게 유사분열 정지를 유도한다.

**유방암 관련성:**
전이성 유방암에서 2/3차 치료제로 사용. CMF 요법의 대안으로 활용 가능. 미세소관 표적 약물에 대한 유방암의 높은 감수성이 확인됨.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** standard (target_novelty=0.2)
**Pathway:** Mitosis (pathway_novelty=0.2)

**기존 BRCA 치료제 대비 차별점:**
미세소관 탈안정화 약물로, Taxane과 반대 기전이지만 동일 Mitosis 경로. 기존 BRCA 치료에 포함.

**새로운 기전의 의미:**
Discovery D#11. 높은 효능이나 novelty=0.2, penalty=0.7로 discovery 점수가 크게 감소.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

유방암 세포주에서 강력한 세포독성 확인(GDSC sensitivity rate 100%). 단독 또는 병용 요법으로 전이성 유방암에 사용 이력 있음.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -1.2843
- 예측 감수성률: 100%
- GDSC2 유방암 세포주 수: 27
- 실제 감수성률: 89%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 9.25
- Known BRCA: 기존 치료제

**근거 수준 (Category별):**
- Category A: 임상 근거 확립. FDA 승인 또는 NCCN 가이드라인 포함.
- Discovery 관점에서 새로운 적응증 발굴보다는 기존 효능 재확인에 해당.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 7.83 |
| **검사 수** | 12 / 22 |
| **Pass** | 7 |
| **Caution** | 1 |
| **Flags** | None |

**해석:** 양호 (기승인 약물, 주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 해당 없음 — 이미 BRCA 승인 약물 (기존 효능 재확인)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=0.89)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (9.25)

**다음 검증 단계:**
1. 기존 임상 데이터와 모델 예측의 일치성 재확인
2. 아형별(TNBC/HR+/HER2+) 감수성 차이 분석
3. 기존 병용 요법에서의 최적 위치 재평가

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*