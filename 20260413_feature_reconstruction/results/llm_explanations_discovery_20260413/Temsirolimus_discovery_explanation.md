# Temsirolimus — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#9 / 15 |
| **Validation Rank** | V#6 / 28 |
| **Rank Delta** | -3 (하락) |
| **Category** | **B** (BRCA Research) |
| **Target** | MTOR |
| **Pathway** | PI3K/MTOR signaling |
| **Discovery Score** | 0.5157 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.8214 + 0.5 x (0.35 x (1 - 0.4))
               = 0.4107 + 0.2100
               = 0.5157
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.8214 | 28개 약물 중 82.1% 위치 |
| target_novelty | 0.2 | standard |
| pathway_novelty | 0.5 | PI3K/MTOR signaling |
| novelty_score | 0.35 | 0.5×target + 0.5×pathway |
| known_penalty | 0.4 | Cat B 기반 |
| novelty_component | 0.2100 | novelty × (1 - penalty) |

**Discovery 하락 사유 (V#6 → D#9, -3):**
- 낮은 target novelty (0.2, standard)

## 2. Mechanism of Action (작용 기전)

mTOR(mechanistic target of rapamycin) 선택적 억제제로, FKBP12와 결합하여 mTORC1 complex를 억제한다. PI3K/AKT/mTOR 신호전달을 차단하여 세포 증식, 혈관신생, 대사를 억제한다.

**유방암 관련성:**
PI3K/AKT/mTOR 경로는 유방암, 특히 HR+/HER2- 아형에서 빈번히 활성화됨. PIK3CA 변이(~40%)와의 시너지 가능성. Everolimus(같은 계열)가 유방암에서 승인된 점은 간접 근거.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** standard (target_novelty=0.2)
**Pathway:** PI3K/MTOR signaling (pathway_novelty=0.5)

**기존 BRCA 치료제 대비 차별점:**
mTOR 억제제로, PI3K/AKT/mTOR 경로 표적. 같은 계열의 everolimus가 유방암에서 승인되어 있어 완전한 신규 기전은 아니나, temsirolimus 자체의 유방암 적용은 새로운 시도.

**새로운 기전의 의미:**
경로 novelty(0.5)는 중간 수준. 이미 검증된 PI3K/mTOR 경로이나, temsirolimus의 유방암 특이적 임상 데이터가 축적되면 everolimus의 한계를 극복할 수 있는 대안이 될 수 있음.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

BOLERO-2 연구(everolimus)에서 HR+/HER2- 전이성 유방암 PFS 개선 입증. Temsirolimus는 신세포암 승인이나 유방암 전임상에서 활성 확인.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -1.0676
- 예측 감수성률: 96%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 12%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의하지 않음 (p=0.3447146812541515)
- 검증 점수: 4.65
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.
- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 5.71 |
| **검사 수** | 7 / 22 |
| **Pass** | 4 |
| **Caution** | 0 |
| **Flags** | None |

**해석:** 양호 (주요 독성 플래그 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 중간 (Moderate)**

긍정적 요인:
- (+) 양호한 base 효능 (percentile=0.82)
- (+) ADMET 통과

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*