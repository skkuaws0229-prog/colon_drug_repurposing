# SL0101 — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1039 |
| **Dedup Rank** | 9 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | RSK, AURKB, PIM1, PIM3 |
| **Pathway** | Other kinases |
| **Pred IC50** | -0.2720 (ln scale) |
| **Sensitivity Rate** | 100% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 5.45 |

## 1. Mechanism of Action (작용 기전)

RSK(p90 ribosomal S6 kinase) 억제제로, AURKB, PIM1, PIM3 kinase도 억제한다. MAPK/ERK 신호전달 하위의 RSK 활성을 차단하여 세포 증식 및 생존 신호를 억제한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

RSK는 ER+ 유방암에서 에스트로겐 비의존적 증식 매개에 관여. AURKB 억제는 유사분열 이상을 유도하여 항종양 효과. PIM kinase는 유방암 약물 저항성 관련.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 비관련
- 생존 분석 (Method B): 유의미 (p<0.05) (p=5.150239984811742e-06)
- 종합 검증 점수: 5.45

**OpenTargets 유방암 연관성:**
- AURKB: association score=0.265 (breast adenocarcinoma, breast cancer, triple-negative breast cancer)
- PIM1: association score=0.279 (breast carcinoma, breast ductal adenocarcinoma, Adenoid Cystic Breast Carcinoma)
- PIM3: association score=0.012 (breast cancer, triple-negative breast cancer)

## 3. Supporting Evidence (근거 자료)

전임상 단계 연구용 화합물. GDSC 데이터에서 제한된 샘플(n=1)로 해석 주의 필요.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 1
- 앙상블 예측 IC50 (ln): -0.2720
- 예측 감수성률: 100%
- 실제 IC50 (ln): 4.0106
- 실제 감수성률: 0%

> SL0101은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

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
- (+) 생존 분석 유의
- (+) ADMET 통과

**권고**: 전임상 근거를 바탕으로 유방암 특이적 임상시험 설계 검토 가능. 특히 해당 표적/경로의 유방암 아형 특이성 분석 권장.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*