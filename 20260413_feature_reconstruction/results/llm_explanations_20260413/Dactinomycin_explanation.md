# Dactinomycin — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1811 |
| **Dedup Rank** | 2 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | RNA polymerase |
| **Pathway** | Other |
| **Pred IC50** | -2.2883 (ln scale) |
| **Sensitivity Rate** | 100% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 7.9 |

## 1. Mechanism of Action (작용 기전)

Actinomycin D로도 불리며, DNA 이중나선의 minor groove에 삽입(intercalation)되어 RNA polymerase의 전사를 억제한다. DNA-의존적 RNA 합성을 차단하여 세포 사멸을 유도한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

전통적으로 윌름스종양, 횡문근육종 등에 사용되나, 유방암에서도 강력한 세포독성 활성이 GDSC 데이터에서 확인됨. RNA 합성 억제는 빠르게 증식하는 유방암 세포에 효과적일 수 있음.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 비관련
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 7.9

## 3. Supporting Evidence (근거 자료)

GDSC2 데이터에서 유방암 세포주 대상 높은 감수성(sensitivity rate 100%) 확인. 임상적 유방암 적용은 제한적이나 전임상 근거 존재.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): -2.2883
- 예측 감수성률: 100%
- 실제 IC50 (ln): -1.8155
- 실제 감수성률: 96%

> Dactinomycin은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 7.0 |
| **검사 수** | 5 / 22 |
| **Pass** | 3 |
| **Caution** | 1 |
| **No Data** | 17 |
| **Flags** | DILI (Drug-Induced Liver Injury)(+) |

**해석**: 허용 (기승인 약물, 관리 가능한 독성: DILI (Drug-Induced Liver Injury)(+))

**카테고리 A 기준**: 이미 임상에서 사용 중인 승인 약물이므로, 알려진 부작용은 관리 가능한 범위 내에서 허용됩니다.

## 5. Repurposing Potential (재창출 가능성)

**종합 평가: 높음 (High)**

긍정적 요인:
- (+) 높은 예측 감수성
- (+) 높은 METABRIC 검증 점수
- (+) 타겟 발현 확인
- (+) 생존 분석 유의
- (+) ADMET 통과
- (+) 기존 BRCA 치료제

**권고**: Category A 약물로서 이미 유방암 치료에 사용 중. 현 파이프라인 결과는 기존 임상 근거와 일치하며, 약물 우선순위 결정 및 아형별 최적화에 활용 가능.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*