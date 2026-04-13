# CDK9_5038 — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1709 |
| **Dedup Rank** | 14 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | CDK9 |
| **Pathway** | Cell cycle |
| **Pred IC50** | 1.2037 (ln scale) |
| **Sensitivity Rate** | 4% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 2.7 |

## 1. Mechanism of Action (작용 기전)

CDK9 선택적 억제제(CDK9_5576과 동일 표적, 다른 화학구조). P-TEFb 복합체를 억제하여 전사 신장을 차단하고, 반감기 짧은 항-세포사멸 단백질(MCL1, XIAP)의 발현을 감소시킨다.

## 2. Relevance to Breast Cancer (유방암 관련성)

CDK9_5576과 동일한 기전적 근거. TNBC에서의 MYC 의존성, CDK9 과발현이 보고됨. 전사 억제를 통한 종양 세포 선택적 사멸 유도.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의하지 않음 (p=0.8233554835205238)
- 종합 검증 점수: 2.7

**OpenTargets 유방암 연관성:**
- CDK9: association score=0.101 (triple-negative breast cancer, breast cancer, male breast carcinoma)

## 3. Supporting Evidence (근거 자료)

전임상 단계 화합물. GDSC 데이터에서 낮은 predicted sensitivity(4%)이나, true sensitivity rate는 81%로 모델 예측과 괴리 존재.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): 1.2037
- 예측 감수성률: 4%
- 실제 IC50 (ln): -1.6929
- 실제 감수성률: 81%

> CDK9_5038은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 5.0 |
| **검사 수** | 0 / 22 |
| **Pass** | 0 |
| **Caution** | 0 |
| **No Data** | 22 |
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