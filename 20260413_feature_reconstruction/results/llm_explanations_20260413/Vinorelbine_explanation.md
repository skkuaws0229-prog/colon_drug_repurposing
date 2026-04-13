# Vinorelbine — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 2048 |
| **Dedup Rank** | 5 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | Microtubule destabiliser |
| **Pathway** | Mitosis |
| **Pred IC50** | -1.1783 (ln scale) |
| **Sensitivity Rate** | 96% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 9.2 |

## 1. Mechanism of Action (작용 기전)

반합성 vinca alkaloid로, tubulin 이합체의 중합을 선택적으로 억제한다. 유사분열 방추체 형성을 방해하여 G2/M 세포주기 정지를 유도한다. Vinblastine 대비 신경독성이 낮다.

## 2. Relevance to Breast Cancer (유방암 관련성)

전이성 유방암 2/3차 치료에서 NCCN 권고 약물. 경구제형 가능하여 편의성 높음. HER2-음성 전이성 유방암에서 단독 또는 병용 사용.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 9.2

## 3. Supporting Evidence (근거 자료)

전이성 유방암에서 반응률 25-40% 보고. Capecitabine과 병용 시 PFS 개선 확인.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 28
- 앙상블 예측 IC50 (ln): -1.1783
- 예측 감수성률: 96%
- 실제 IC50 (ln): -2.7805
- 실제 감수성률: 96%

> Vinorelbine은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 8.0 |
| **검사 수** | 10 / 22 |
| **Pass** | 6 |
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