# Epirubicin — 유방암 재창출 분석

| 항목 | 값 |
|---|---|
| **Drug ID** | 1511 |
| **Dedup Rank** | 11 / 28 |
| **Category** | **A** (Known BRCA) |
| **Target** | Anthracycline |
| **Pathway** | DNA replication |
| **Pred IC50** | 0.4393 (ln scale) |
| **Sensitivity Rate** | 29% |
| **ADMET Decision** | **PASS** |
| **Validation Score** | 7.35 |


> **심장독성 경고 (Epirubicin)**: Anthracycline 계열 약물로 누적용량 의존적 심근병증 위험이 있습니다. LVEF 모니터링 필수, 누적용량 900mg/m² 초과 금지.

## 1. Mechanism of Action (작용 기전)

Anthracycline 계열 항암제로, DNA intercalation, topoisomerase II 억제, 활성산소(ROS) 생성의 다중 기전으로 작용한다. DNA 이중가닥 절단을 유도하고 세포 사멸 경로를 활성화한다.

## 2. Relevance to Breast Cancer (유방암 관련성)

유방암 1차 치료 핵심 약물(NCCN Category 1). FEC/EC 요법의 구성요소. 보조치료 및 전이성 유방암 모두에서 표준 사용. Doxorubicin 대비 심장독성이 다소 낮다.

**METABRIC 외부검증 결과:**
- 타겟 발현 (Method A): 발현 확인
- BRCA 경로 연관: 관련 경로
- 생존 분석 (Method B): 유의미 (p<0.05) (p=0.01)
- 종합 검증 점수: 7.35

## 3. Supporting Evidence (근거 자료)

FASG-05, MA.5 등 대규모 임상시험에서 보조치료 효과 입증. BCIRG 005에서 docetaxel과 병용 시 효과 확인.

**모델 예측 근거:**
- GDSC2 유방암 세포주 수: 28
- 앙상블 예측 IC50 (ln): 0.4393
- 예측 감수성률: 29%
- 실제 IC50 (ln): 0.0628
- 실제 감수성률: 50%

> Epirubicin은(는) **기존 유방암 치료제 목록**에 포함된 약물입니다.

## 4. ADMET / Safety Considerations (안전성 평가)

| 항목 | 결과 |
|---|---|
| **ADMET Decision** | **PASS** |
| **Safety Score** | 4.83 |
| **검사 수** | 15 / 22 |
| **Pass** | 8 |
| **Caution** | 3 |
| **No Data** | 7 |
| **Flags** | Ames Mutagenicity(+); DILI (Drug-Induced Liver Injury)(+); Clinical Cardiotoxicity (anthracycline) |

**해석**: 허용 (기승인 약물이나 심장독성 주의). anthracycline 계열 누적용량 의존적 심근병증 위험. LVEF 모니터링 필수.

**카테고리 A 기준**: 이미 임상에서 사용 중인 승인 약물이므로, 알려진 부작용은 관리 가능한 범위 내에서 허용됩니다.

### Epirubicin 심장독성 상세

- **Ames Mutagenicity**: 양성 (+) — 변이원성 확인
- **DILI**: 양성 (+) — 약물 유발 간손상 가능성
- **Clinical Cardiotoxicity**: Anthracycline 계열 고유 위험
  - 누적용량 의존적 심근병증 (Type I cardiotoxicity)
  - Doxorubicin 대비 약 50% 수준의 심장독성 (등가용량 기준)
  - 권장 모니터링: 기저 LVEF 측정 → 매 투여 주기마다 확인
  - 누적용량 제한: 900 mg/m² 초과 금지
  - 심장 보호제(dexrazoxane) 병용 고려

## 5. Repurposing Potential (재창출 가능성)

**종합 평가: 높음 (High)**

긍정적 요인:
- (+) 높은 METABRIC 검증 점수
- (+) 타겟 발현 확인
- (+) 생존 분석 유의
- (+) ADMET 통과
- (+) 기존 BRCA 치료제

부정적 요인:
- (-) 중대 독성 플래그

**권고**: Category A 약물로서 이미 유방암 치료에 사용 중. 현 파이프라인 결과는 기존 임상 근거와 일치하며, 약물 우선순위 결정 및 아형별 최적화에 활용 가능.

---
*생성일: 2026-04-13 | 데이터 기반 구조화 분석 (GDSC2 + METABRIC + ADMET)*