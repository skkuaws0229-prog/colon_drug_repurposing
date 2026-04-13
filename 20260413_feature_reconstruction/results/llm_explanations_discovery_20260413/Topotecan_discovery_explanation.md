# Topotecan — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#14 / 15 |
| **Validation Rank** | V#7 / 28 |
| **Rank Delta** | -7 (하락) |
| **Category** | **A** (Known BRCA) |
| **Target** | TOP1 |
| **Pathway** | DNA replication |
| **Discovery Score** | 0.4229 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.7857 + 0.5 x (0.20 x (1 - 0.7))
               = 0.3928 + 0.0600
               = 0.4229
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.7857 | 28개 약물 중 78.6% 위치 |
| target_novelty | 0.2 | standard |
| pathway_novelty | 0.2 | DNA replication |
| novelty_score | 0.20 | 0.5×target + 0.5×pathway |
| known_penalty | 0.7 | Cat A 기반 |
| novelty_component | 0.0600 | novelty × (1 - penalty) |

**Discovery 하락 사유 (V#7 → D#14, -7):**
- 높은 known penalty (0.7, Cat A 기승인 약물)
- 낮은 target novelty (0.2, standard)
- 낮은 pathway novelty (0.2)

## 2. Mechanism of Action (작용 기전)

Topoisomerase I(TOP1) 억제제로, TOP1-DNA 절단 복합체(cleavable complex)를 안정화시켜 DNA 복제 시 이중가닥 절단을 유도한다. S기 세포에 선택적으로 작용한다.

**유방암 관련성:**
DNA 복제 스트레스에 민감한 BRCA1/2 결손 유방암에서 특히 효과적일 수 있음. HRD(Homologous Recombination Deficiency) 종양에서 TOP1 억제제 감수성 증가 보고.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** standard (target_novelty=0.2)
**Pathway:** DNA replication (pathway_novelty=0.2)

**기존 BRCA 치료제 대비 차별점:**
TOP1 억제제로, DNA replication 경로의 표준 항암 표적. 유방암에서 직접 승인되지는 않았으나, 동일 경로의 약물이 표준치료에 포함.

**새로운 기전의 의미:**
Discovery D#14로 크게 하락(V#7). 높은 효능에도 불구하고 standard target + high penalty(0.7)로 discovery 점수 저하.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

소세포폐암/난소암 승인 약물. 유방암에서 Phase II 연구 다수 존재. GDSC 데이터에서 sensitivity rate 73%.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -0.4962
- 예측 감수성률: 73%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 31%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=6.331006623497154e-05)
- 검증 점수: 7.55
- Known BRCA: 기존 치료제

**근거 수준 (Category별):**
- Category A: 임상 근거 확립. FDA 승인 또는 NCCN 가이드라인 포함.
- Discovery 관점에서 새로운 적응증 발굴보다는 기존 효능 재확인에 해당.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 11.0 |
| **검사 수** | 10 / 22 |
| **Pass** | 9 |
| **Caution** | 0 |
| **Flags** | None |

**해석:** 양호 (기승인 약물, 주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 해당 없음 — 이미 BRCA 승인 약물 (기존 효능 재확인)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=0.79)
- (+) ADMET 통과
- (+) METABRIC 검증 양호 (7.55)

**다음 검증 단계:**
1. 기존 임상 데이터와 모델 예측의 일치성 재확인
2. 아형별(TNBC/HR+/HER2+) 감수성 차이 분석
3. 기존 병용 요법에서의 최적 위치 재평가

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*