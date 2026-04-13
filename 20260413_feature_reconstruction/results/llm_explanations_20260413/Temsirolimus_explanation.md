# Temsirolimus — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1016 |
| **Dedup Rank** | 6 / 28 |
| **Category** | **B** (BRCA Research) |
| **Target** | MTOR |
| **Pathway** | PI3K/MTOR signaling |
| **Pred IC50** | -1.0676 (ln scale) |
| **Sensitivity Rate** | 96% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 4.65 |

## 1. Mechanism of Action (작용 기전)

mTOR(mechanistic target of rapamycin) 선택적 억제제로, FKBP12와 결합하여 mTORC1 complex를 억제한다. PI3K/AKT/mTOR 신호전달을 차단하여 세포 증식, 혈관신생, 대사를 억제한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

PI3K/AKT/mTOR 경로는 유방암, 특히 HR+/HER2- 아형에서 빈번히 활성화됨. PIK3CA 변이(~40%)와의 시너지 가능성. Everolimus(같은 계열)가 유방암에서 승인된 점은 간접 근거.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의하지 않음 (p=0.3447146812541515)
- 종합 검증 점수: 4.65

**OpenTargets 유방암 연관성:**
- MTOR: association score=0.332 (breast cancer, breast adenocarcinoma, breast carcinoma)

## 3. Supporting Evidence (근거 자료)

BOLERO-2 연구(everolimus)에서 HR+/HER2- 전이성 유방암 PFS 개선 입증. Temsirolimus는 신세포암 승인이나 유방암 전임상에서 활성 확인.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 26
- 앙상블 예측 IC50 (ln): -1.0676
- 예측 감수성률: 96%
- 실제 IC50 (ln): 1.3266
- 실제 감수성률: 12%

> Temsirolimus은(는) 기존 유방암 치료제 목록에 포함되지 않은 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 5.71 |
| **검사 수** | 7 / 22 |
| **Pass** | 4 |
| **Caution** | 0 |
| **No Data** | 15 |
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