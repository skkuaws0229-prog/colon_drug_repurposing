# AZD2014 — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1441 |
| **Dedup Rank** | 15 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | mTORC1, mTORC2 |
| **Pathway** | PI3K/MTOR signaling |
| **Pred IC50** | 1.3807 (ln scale) |
| **Sensitivity Rate** | 0% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 5.15 |

## 1. Mechanism of Action (작용 기전)

mTORC1/mTORC2 이중 억제제(vistusertib). Rapamycin 유사체(rapalog)와 달리 mTORC2도 억제하여 AKT 피드백 활성화를 차단한다. PI3K/AKT/mTOR 경로를 보다 완전하게 억제.

## 2. Relevance to Breast Cancer (유방암 관련성)

PI3K/AKT/mTOR 경로 과활성은 HR+/HER2- 유방암의 핵심 발암기전. mTORC1만 억제하는 everolimus 대비 mTORC2 추가 억제로 저항성 극복 가능성. 유방암 Phase II 임상 진행됨.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 5.15

## 3. Supporting Evidence (근거 자료)

MANTA 연구(HR+ 전이성 유방암)에서 fulvestrant 병용 평가. 전임상에서 everolimus 내성 극복 효과 확인.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): 1.3807
- 예측 감수성률: 0%
- 실제 IC50 (ln): 2.1850
- 실제 감수성률: 4%

> AZD2014은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

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

**종합 평가: 중간 (Moderate)**

긍정적 요인:
- (+) 타겟 발현 확인
- (+) 생존 분석 유의
- (+) ADMET 통과

부정적 요인:
- (-) 낮은 예측 감수성

**권고**: 전임상 근거를 바탕으로 유방암 특이적 임상시험 설계 검토 가능. 특히 해당 표적/경로의 유방암 아형 특이성 분석 권장.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*