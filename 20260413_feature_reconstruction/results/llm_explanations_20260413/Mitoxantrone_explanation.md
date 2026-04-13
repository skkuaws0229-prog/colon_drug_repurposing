# Mitoxantrone — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1810 |
| **Dedup Rank** | 12 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | TOP2 |
| **Pathway** | DNA replication |
| **Pred IC50** | 0.8630 (ln scale) |
| **Sensitivity Rate** | 8% |
| **ADMET Decision** | **CAUTION** |
| **Validation Score** | 5.3 |


> **CAUTION**: 이 약물은 ADMET 검증에서 주의(CAUTION) 판정을 받았습니다. Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+)

## 1. Mechanism of Action (작용 기전)

Anthracenedione 계열로, topoisomerase II를 억제하고 DNA intercalation을 통해 작용한다. Anthracycline과 유사하나 구조적으로 다르며, 활성산소 생성이 적어 심장독성이 상대적으로 낮다.

## 2. Relevance to Breast Cancer (유방암 관련성)

전이성 유방암에서 2/3차 치료제로 사용 이력. Anthracycline 내성 또는 심장독성 우려 시 대안. TOP2 경로는 유방암에서 검증된 표적.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 5.3

## 3. Supporting Evidence (근거 자료)

전이성 유방암 Phase III 연구 다수. 단독 반응률 20-35%. GDSC 데이터에서 낮은 sensitivity rate(8%)은 예측 기반 값.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): 0.8630
- 예측 감수성률: 8%
- 실제 IC50 (ln): 1.8554
- 실제 감수성률: 15%

> Mitoxantrone은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **CAUTION** |
| **Safety Score** | 2.5 |
| **검사 수** | 12 / 22 |
| **Pass** | 6 |
| **Caution** | 3 |
| **No Data** | 10 |
| **Flags** | Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+) |

**해석**: 주의 (연구 약물, 중대 독성: Ames Mutagenicity(+))

**카테고리 B 기준**: BRCA 연구 약물로서 중대 독성 플래그가 있어 추가 안전성 연구가 필요합니다. 임상 진입 전 독성 프로파일 재평가 권고.

## 5. Repurposing Potential (재창출 가능성)

**종합 평가: 조건부 (Conditional)**

긍정적 요인:
- (+) 타겟 발현 확인
- (+) 생존 분석 유의

부정적 요인:
- (-) 낮은 예측 감수성
- (-) ADMET 주의 판정
- (-) 중대 독성 플래그

**권고**: ADMET 주의 판정으로 독성 프로파일 재평가 필요. 전임상 독성 시험 우선 수행 후 임상 적용 검토.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*