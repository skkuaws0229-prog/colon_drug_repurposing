# TW 37 — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1149 |
| **Dedup Rank** | 13 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | BCL2, BCL-XL, MCL1 |
| **Pathway** | Apoptosis regulation |
| **Pred IC50** | 1.1938 (ln scale) |
| **Sensitivity Rate** | 0% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 2.75 |

## 1. Mechanism of Action (작용 기전)

BCL-2 family 억제제로, BH3 mimetic 계열에 속한다. BCL-2, BCL-XL, MCL-1에 결합하여 항-세포사멸(anti-apoptotic) 기능을 차단하고, BAX/BAK 매개 미토콘드리아 외막 투과(MOMP)를 유도한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

BCL-2는 ER+ 유방암에서 과발현. MCL-1은 TNBC에서 약물 저항성의 주요 매개자. BH3 mimetic(venetoclax 등)의 유방암 임상시험이 진행 중이며, 같은 계열의 기전적 근거.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의하지 않음 (p=0.10534012238172552)
- 종합 검증 점수: 2.75

**OpenTargets 유방암 연관성:**
- BCL2: association score=0.373 (breast ductal adenocarcinoma, Breast hypertrophy, breast carcinoma)
- MCL1: association score=0.213 (breast adenocarcinoma, breast cancer, triple-negative breast cancer)

## 3. Supporting Evidence (근거 자료)

전임상 연구에서 다양한 암종 대상 효과 확인. 유방암 특이적 임상 데이터는 제한적이나, BCL-2/MCL-1 표적의 유방암 관련성은 확립됨.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 14
- 앙상블 예측 IC50 (ln): 1.1938
- 예측 감수성률: 0%
- 실제 IC50 (ln): 1.1052
- 실제 감수성률: 7%

> TW 37은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 10.0 |
| **검사 수** | 2 / 22 |
| **Pass** | 2 |
| **Caution** | 0 |
| **No Data** | 20 |
| **Flags** | None |

**해석**: 양호 (주요 독성 플래그 없음)

**카테고리 B 기준**: BRCA 연구 약물로서 주요 독성 플래그가 없어 추가 전임상/임상 연구 진행이 가능합니다.

## 5. Repurposing Potential (재창출 가능성)

**종합 평가: 낮음 (Low)**

긍정적 요인:
- (+) 타겟 발현 확인
- (+) ADMET 통과

부정적 요인:
- (-) 낮은 예측 감수성

**권고**: 전임상 근거를 바탕으로 유방암 특이적 임상시험 설계 검토 가능. 특히 해당 표적/경로의 유방암 아형 특이성 분석 권장.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*