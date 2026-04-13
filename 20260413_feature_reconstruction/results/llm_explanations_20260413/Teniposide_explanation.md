# Teniposide — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1809 |
| **Dedup Rank** | 10 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | nan |
| **Pathway** | DNA replication |
| **Pred IC50** | -0.1727 (ln scale) |
| **Sensitivity Rate** | 69% |
| **ADMET Decision** | **CAUTION** |
| **Validation Score** | 5.4 |


> **CAUTION**: 이 약물은 ADMET 검증에서 주의(CAUTION) 판정을 받았습니다. Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+)

## 1. Mechanism of Action (작용 기전)

반합성 podophyllotoxin 유도체로, topoisomerase II와 DNA의 절단 복합체를 안정화시켜 DNA 이중가닥 절단을 유도한다. Etoposide와 유사하나 지질 용해도가 높아 CNS 투과성이 우수하다.

## 2. Relevance to Breast Cancer (유방암 관련성)

DNA 복제 경로 억제제로, 유방암 세포의 높은 증식률을 표적할 수 있음. TOP2 억제제(doxorubicin, epirubicin 등)는 유방암 표준 치료에 이미 포함되어 있어 기전적 근거 존재.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 5.4

## 3. Supporting Evidence (근거 자료)

소아 ALL에 주로 사용. 유방암 임상 데이터는 제한적이나, 같은 TOP2 억제 기전의 anthracycline이 유방암에서 입증됨.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): -0.1727
- 예측 감수성률: 69%
- 실제 IC50 (ln): 1.6095
- 실제 감수성률: 23%

> Teniposide은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **CAUTION** |
| **Safety Score** | 3.61 |
| **검사 수** | 18 / 22 |
| **Pass** | 11 |
| **Caution** | 3 |
| **No Data** | 4 |
| **Flags** | Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+) |

**해석**: 주의 (연구 약물, 중대 독성: Ames Mutagenicity(+))

**카테고리 B 기준**: BRCA 연구 약물로서 중대 독성 플래그가 있어 추가 안전성 연구가 필요합니다. 임상 진입 전 독성 프로파일 재평가 권고.

## 5. Repurposing Potential (재창출 가능성)

**종합 평가: 조건부 (Conditional)**

긍정적 요인:
- (+) 높은 예측 감수성
- (+) 타겟 발현 확인
- (+) 생존 분석 유의

부정적 요인:
- (-) ADMET 주의 판정
- (-) 중대 독성 플래그

**권고**: ADMET 주의 판정으로 독성 프로파일 재평가 필요. 전임상 독성 시험 우선 수행 후 임상 적용 검토.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*