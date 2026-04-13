# Avagacestat — Discovery 관점 분석

| 항목 | 값 |
|---|---|
| **Discovery Rank** | D#3 / 15 |
| **Validation Rank** | V#19 / 28 |
| **Rank Delta** | +16 (상승) |
| **Category** | **C** (Pure Repurposing) |
| **Target** | Amyloid beta20, Amyloid beta40 |
| **Pathway** | Other |
| **Discovery Score** | 0.6786 |
| **ADMET** | PASS |

## 1. Discovery Context (발견 맥락)

**Score 분해:**
```
discovery_score = 0.5 x base_norm + 0.5 x (novelty x (1 - penalty))
               = 0.5 x 0.3571 + 0.5 x (1.00 x (1 - 0.0))
               = 0.1785 + 1.0000
               = 0.6786
```

| 구성요소 | 값 | 해석 |
|---|---|---|
| base_norm (효능 percentile) | 0.3571 | 28개 약물 중 35.7% 위치 |
| target_novelty | 1.0 | novel |
| pathway_novelty | 1.0 | Other |
| novelty_score | 1.00 | 0.5×target + 0.5×pathway |
| known_penalty | 0.0 | Cat C 기반 |
| novelty_component | 1.0000 | novelty × (1 - penalty) |

**Discovery 상승 사유 (V#19 → D#3, +16):**
- 높은 target novelty (1.0, novel)
- 높은 pathway novelty (1.0)
- 낮은 known penalty (0.0, Cat C)

## 2. Mechanism of Action (작용 기전)

Gamma-secretase 억제제로, amyloid precursor protein(APP)의 절단을 억제하여 amyloid beta 20/40 생성을 차단한다. 원래 알츠하이머 치료제로 개발되었으나 Phase II에서 중단.

**유방암 관련성:**
Gamma-secretase는 Notch 신호전달 경로도 매개하며, Notch는 유방암 줄기세포(CSC) 유지 및 약물 저항성에 핵심적 역할. Gamma-secretase 억제제의 유방암 전임상 연구가 다수 보고됨.

## 3. Novelty vs Known BRCA Drugs (기존 치료제 대비 차별성)

**Target Class:** novel (target_novelty=1.0)
**Pathway:** Other (pathway_novelty=1.0)

**기존 BRCA 치료제 대비 차별점:**
원래 알츠하이머 치료제로 개발된 gamma-secretase 억제제. Amyloid beta 표적은 유방암과 직접적 연관성이 없으나, gamma-secretase의 Notch 경로 매개 기능이 유방암 재창출의 근거.

**새로운 기전의 의미:**
완전한 재창출(repurposing) 후보로, 기존 BRCA 치료 패러다임과 무관한 표적. Notch 신호전달은 유방암 줄기세포(CSC) 유지에 핵심적이며, CSC 표적 치료는 재발/전이 억제의 새로운 전략. 알츠하이머 임상 안전성 데이터가 이미 확보된 점이 개발 가속화 요인.

**참고 — 기존 BRCA 표준 표적:**
- Microtubule (Taxane/Vinca) — Mitosis 경로, novelty=0.2
- DNA TOP1/TOP2 (Topotecan/Anthracycline) — DNA replication, novelty=0.2
- Hormone (ER: Fulvestrant/Tamoxifen) — Hormone-related, novelty=0.3
- HER2 (Trastuzumab/Pertuzumab) — 본 데이터셋 미포함

## 4. Supporting Evidence (근거 자료)

알츠하이머 Phase II 임상 수행(안전성 데이터 존재). Gamma-secretase 억제제 계열(MK-0752, RO4929097)의 유방암 임상시험이 진행된 바 있음.

**모델 예측 데이터:**
- 앙상블 예측 IC50 (ln): 1.5645
- 예측 감수성률: 0%
- GDSC2 유방암 세포주 수: 28
- 실제 감수성률: 0%

**METABRIC 외부검증:**
- 타겟 발현: 발현 확인
- BRCA 경로: 비관련
- 생존 분석: 유의미 (p=0.01)
- 검증 점수: 3.45
- Known BRCA: 신규 후보

**근거 수준 (Category별):**
- Category C: 원래 적응증과 무관한 완전 재창출 후보.
- 기전적 연관성(예: 경로 교차) 기반의 가설 단계 근거.

## 5. ADMET / Safety (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 10.0 |
| **검사 수** | 1 / 22 |
| **Pass** | 1 |
| **Caution** | 0 |
| **Flags** | None |

**해석:** 통과 (신규 적응증, 주요 독성 없음)

## 6. Repurposing Potential (재창출 가능성)

**재창출 가치 평가: 높음 — 완전 재창출 (High Repurposing Value)**

긍정적 요인:
- (+) Discovery Top 5 (D#3)
- (+) 높은 novelty (1.0)
- (+) novel target class
- (+) ADMET 통과

부정적 요인:
- (-) 낮은 효능/감수성
- (-) 유방암 임상 근거 부재

**다음 검증 단계:**
1. 표적 기전의 유방암 관련성 전임상 검증 (필수)
2. 유방암 세포주/PDX 모델에서의 단독 효능 확인
3. Gamma-secretase/Notch 경로의 유방암 줄기세포 영향 분석
4. 기존 적응증(알츠하이머) 임상 안전성 데이터 재활용 검토
5. 유방암 Phase I basket trial 포함 가능성 탐색

---
*생성일: 2026-04-13 | Discovery Ranking v2 기반 분석 | 데이터: GDSC2 + METABRIC + ADMET*