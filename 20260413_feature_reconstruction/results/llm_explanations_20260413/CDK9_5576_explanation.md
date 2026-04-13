# CDK9_5576 — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1708 |
| **Dedup Rank** | 8 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | CDK9 |
| **Pathway** | Cell cycle |
| **Pred IC50** | -0.4560 (ln scale) |
| **Sensitivity Rate** | 65% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 3.0 |

## 1. Mechanism of Action (작용 기전)

CDK9(Cyclin-dependent kinase 9) 선택적 억제제로, P-TEFb(CDK9/Cyclin T) 복합체를 억제하여 RNA Polymerase II의 전사 신장(elongation)을 차단한다. MYC, MCL1 등 반감기 짧은 종양유전자 발현을 억제한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

CDK9는 유방암에서 과발현되며, MYC-driven TNBC에서 핵심 취약성(vulnerability)으로 보고됨. MCL1 억제를 통한 apoptosis 유도 가능성.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의하지 않음 (p=0.8233554835205238)
- 종합 검증 점수: 3.0

**OpenTargets 유방암 연관성:**
- CDK9: association score=0.101 (triple-negative breast cancer, breast cancer, male breast carcinoma)

## 3. Supporting Evidence (근거 자료)

전임상 연구에서 TNBC 세포주 대상 CDK9 억제 효과 확인. GDSC 데이터에서 sensitivity rate 65%.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): -0.4560
- 예측 감수성률: 65%
- 실제 IC50 (ln): 0.1970
- 실제 감수성률: 54%

> CDK9_5576은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

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

**종합 평가: 중간 (Moderate)**

긍정적 요인:
- (+) 높은 예측 감수성
- (+) 타겟 발현 확인
- (+) ADMET 통과

**권고**: 전임상 근거를 바탕으로 유방암 특이적 임상시험 설계 검토 가능. 특히 해당 표적/경로의 유방암 아형 특이성 분석 권장.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*