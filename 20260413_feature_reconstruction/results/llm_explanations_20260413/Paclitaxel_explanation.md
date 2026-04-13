# Paclitaxel — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1080 |
| **Dedup Rank** | 3 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | Microtubule stabiliser |
| **Pathway** | Mitosis |
| **Pred IC50** | -2.1565 (ln scale) |
| **Sensitivity Rate** | 100% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 9.35 |

## 1. Mechanism of Action (작용 기전)

Taxane 계열 항암제로, β-tubulin에 결합하여 미세소관 탈중합(depolymerization)을 억제한다. 안정화된 미세소관은 세포분열 시 정상적 방추체 형성을 방해하여 유사분열 정지를 유도한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

유방암 표준 치료제(NCCN Category 1). nab-paclitaxel(Abraxane)은 전이성 유방암에서 개선된 약동학을 제공. 주간 투여 요법이 보조치료에서 표준.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 9.35

## 3. Supporting Evidence (근거 자료)

CALGB 9344/INT 0148에서 보조 paclitaxel 추가 시 DFS 17% 개선. TNBC에서 특히 높은 반응률.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 28
- 앙상블 예측 IC50 (ln): -2.1565
- 예측 감수성률: 100%
- 실제 IC50 (ln): -2.7797
- 실제 감수성률: 93%

> Paclitaxel은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 6.83 |
| **검사 수** | 12 / 22 |
| **Pass** | 7 |
| **Caution** | 1 |
| **No Data** | 10 |
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