# Vinblastine — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1004 |
| **Dedup Rank** | 4 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | Microtubule destabiliser |
| **Pathway** | Mitosis |
| **Pred IC50** | -1.2843 (ln scale) |
| **Sensitivity Rate** | 100% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 9.25 |

## 1. Mechanism of Action (작용 기전)

Vinca alkaloid 계열로, tubulin의 중합(polymerization)을 억제하여 미세소관 형성을 방해한다. Taxane과 반대 기전이지만 동일하게 유사분열 정지를 유도한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

전이성 유방암에서 2/3차 치료제로 사용. CMF 요법의 대안으로 활용 가능. 미세소관 표적 약물에 대한 유방암의 높은 감수성이 확인됨.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 9.25

## 3. Supporting Evidence (근거 자료)

유방암 세포주에서 강력한 세포독성 확인(GDSC sensitivity rate 100%). 단독 또는 병용 요법으로 전이성 유방암에 사용 이력 있음.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 27
- 앙상블 예측 IC50 (ln): -1.2843
- 예측 감수성률: 100%
- 실제 IC50 (ln): -2.7355
- 실제 감수성률: 89%

> Vinblastine은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 7.83 |
| **검사 수** | 12 / 22 |
| **Pass** | 7 |
| **Caution** | 1 |
| **No Data** | 10 |
| **Flags** | None |

**해석**: 양호 (기승인 약물, 주요 독성 플래그 없음)

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