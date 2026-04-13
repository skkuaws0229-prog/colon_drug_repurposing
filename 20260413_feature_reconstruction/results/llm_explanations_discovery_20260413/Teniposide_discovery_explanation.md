# Teniposide — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#6 / 15 |
| **Validation Rank** | V#10 / 28 |
| **Rank Delta** | +4 (상승) |
| **Category** | **B** (BRCA Research) |
| **Target** | nan |
| **Pathway** | DNA replication |
| **Discovery Score** | 0.6093 |
| **ADMET** | CAUTION |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.6786 + 0.5 x (0.60 x (1 - 0.1))
               = 0.3393 + 0.5400
               = 0.6093
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.6786 | 28개 약물 중 67.9% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 0.2 | DNA replication |
| novelty_score | 0.60 | 0.5×target + 0.5×pathway |
| known_penalty | 0.1 | Cat B 기반 |
| novelty_component | 0.5400 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#10 → D#6, +4):**
- 높은 target novelty (1.0, novel)
- 낮은 known penalty (0.1, Cat B)

## 2. Mechanism of Action (작용 기전)

반합성 podophyllotoxin 유도체로, topoisomerase II와 DNA의 절단 복합체를 안정화시켜 DNA 이중가닥 절단을 유도한다. Etoposide와 유사하나 지질 용해도가 높아 CNS 투과성이 우수하다.

**유방암 관련성:**
DNA 복제 경로 억제제로, 유방암 세포의 높은 증식률을 표적할 수 있음. TOP2 억제제(doxorubicin, epirubicin 등)는 유방암 표준 치료에 이미 포함되어 있어 기전적 근거 존재.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** DNA replication (pathway_novelty=0.2)

**기존 BRCA 치료제 대비 차별점:**
Topoisomerase II 억제제로 기존 BRCA 치료(anthracycline)와 유사한 경로이나, 특정 타겟 정보가 불명확(target=NaN)하여 novel로 분류됨. Etoposide 유사체로 다른 약동학 프로파일 보유.

**새로운 기전의 의미:**
Pathway는 기존(DNA replication, novelty=0.2)이나 target 미상으로 target_novelty=1.0 배정. 실제 기전은 TOP2 경로 관련 가능성 높으며, novelty 점수가 과대평가되었을 수 있어 해석 시 주의 필요.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

소아 ALL에 주로 사용. 유방암 임상 데이터는 제한적이나, 같은 TOP2 억제 기전의 anthracycline이 유방암에서 입증됨.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): -0.1727
- 예측 감수성률: 69%
- GDSC2 유방암 세포주 수: 26
- 실제 감수성률: 23%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 관련 경로
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 5.4
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category B: 전임상/초기 임상 근거 존재. 유방암 특이적 임상시험 검토 가능.
- 표적의 유방암 관련성에 대한 문헌 근거가 축적 중인 단계.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **CAUTION** |
| **Safety Score** | 3.61 |
| **검사 수** | 18 / 22 |
| **Pass** | 11 |
| **Caution** | 3 |
| **Flags** | Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+) |

**해석:** 주의 (연구 약물, 중대 독성: Ames Mutagenicity(+))

> **CAUTION 경고:** Teniposide은(는) ADMET 검증에서 주의(CAUTION) 판정. Cat B 기준 추가 안전성 연구 필요. Flags: Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 조건부 (Conditional — ADMET 재평가 필요)**

긍정적 요인:
- (+) novel target class
- (+) 양호한 base 효능 (percentile=0.68)
- (+) METABRIC 검증 양호 (5.4)

부정적 요인:
- (-) ADMET 주의 판정

**다음 검증 단계:**
1. 표적 발현의 유방암 아형별 검증 (TCGA/METABRIC)
2. 전임상 유방암 세포주/오가노이드 효능 확인
3. 기존 BRCA 치료제와의 병용 시너지 탐색
4. 유방암 Phase I/II 임상시험 설계 검토

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*