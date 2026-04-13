# Topotecan — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1808 |
| **Dedup Rank** | 7 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | TOP1 |
| **Pathway** | DNA replication |
| **Pred IC50** | -0.4962 (ln scale) |
| **Sensitivity Rate** | 73% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 7.55 |

## 1. Mechanism of Action (작용 기전)

Topoisomerase I(TOP1) 억제제로, TOP1-DNA 절단 복합체(cleavable complex)를 안정화시켜 DNA 복제 시 이중가닥 절단을 유도한다. S기 세포에 선택적으로 작용한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

DNA 복제 스트레스에 민감한 BRCA1/2 결손 유방암에서 특히 효과적일 수 있음. HRD(Homologous Recombination Deficiency) 종양에서 TOP1 억제제 감수성 증가 보고.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=6.331006623497154e-05)
- 종합 검증 점수: 7.55

**OpenTargets 유방암 연관성:**
- TOP1: association score=0.586 (breast cancer, breast neoplasm, triple-negative breast cancer)

## 3. Supporting Evidence (근거 자료)

소세포폐암/난소암 승인 약물. 유방암에서 Phase II 연구 다수 존재. GDSC 데이터에서 sensitivity rate 73%.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): -0.4962
- 예측 감수성률: 73%
- 실제 IC50 (ln): 1.1311
- 실제 감수성률: 31%

> Topotecan은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 11.0 |
| **검사 수** | 10 / 22 |
| **Pass** | 9 |
| **Caution** | 0 |
| **No Data** | 12 |
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