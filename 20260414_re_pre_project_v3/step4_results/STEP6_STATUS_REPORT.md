# Step 6 METABRIC 외부 검증 - 현황 보고서

## 📋 전체 개요

**목적**: GDSC 학습 모델을 METABRIC 유방암 환자 데이터로 외부 검증

**비교 대상**:
1. **앙상블 A (Weighted)**: CatBoost (34%) + DART (34%) + FlatMLP (32%)
2. **CatBoost 단독**: 개별 최고 성능 모델

---

## 🔍 검증 방법론

### **Method A: IC50 Proxy 예측**
- GDSC 학습 모델로 METABRIC 환자별 IC50 예측
- Top 15 약물 추출 (낮은 IC50 = 높은 민감도)
- 약물 분류:
  - 카테고리 1: 유방암 현재 사용 (검증용)
  - 카테고리 2: 다른 암종 승인/임상 중 (재창출 후보)
  - 카테고리 3: 유방암 미사용 (신약 후보)

**측정 지표**:
- RMSE, MAE, MedianAE (환자별 예측 오차)
- Spearman, Kendall (환자 간 예측 일관성)
- Precision@15, Recall@15, NDCG@15, EF@15
- MAP (Mean Average Precision)
- 앙상블 A vs CatBoost Top 15 Jaccard similarity
- Top 15 MOA 중복률
- Top 15 Target coverage

### **Method B: Survival Analysis**
- Top 15 약물의 target gene 발현으로 환자 분류
- High vs Low expression 그룹 생존 분석 (Kaplan-Meier)

**측정 지표**:
- Log-rank test p-value
- Hazard ratio (HR) + 95% CI
- Cox regression
- Concordance index (C-index)
- 유의한 약물 수 (p < 0.05)
- Bonferroni 보정 후 유의한 약물 수

### **Method C: GraphSAGE Ranking**
- GraphSAGE drug ranking P@20 계산
- 알려진 BRCA 약물과 비교

**측정 지표**:
- Precision@20, Precision@15
- NDCG@15
- Known BRCA drug recall

---

## 📊 기존 검증 결과 (이전 실행)

**위치**: `/Users/skku_aws2_14/.../models/metabric_results/`

### 이전 결과 요약

**Method A - Target Expression**:
- 29/30 약물의 target이 METABRIC에서 발현 확인
- 22/30 약물이 BRCA 관련 pathway 포함
- 대표 약물:
  - Romidepsin (HDAC 억제제): 79% 환자에서 발현
  - Sepantronium bromide (BIRC5 억제제): 43% 환자에서 발현

**특징**:
- Target gene expression 검증에 집중
- IC50 직접 예측은 없음
- Survival 분석 부분 결과만 있음

---

## 🆕 새로운 종합 분석 (Step 6 Comprehensive)

### 추가/개선 사항

#### 1. **IC50 Direct Prediction**
- ✅ METABRIC 환자별 × 약물별 IC50 매트릭스 예측
- ✅ 앙상블 A vs CatBoost 직접 비교
- ✅ Top 15 약물 추출 및 저장

#### 2. **확장된 Ranking Metrics**
- ✅ P@15, R@15, NDCG@15, EF@15
- ✅ MAP (Mean Average Precision)
- ✅ Top 15 Overlap (Jaccard)
- ✅ MOA 중복률 분석
- ✅ Target coverage 계산

#### 3. **완전한 Survival Analysis**
- ✅ 모든 Top 15 약물에 대해 KM curve
- ✅ Cox regression HR + 95% CI
- ✅ C-index 계산
- ✅ Bonferroni 보정
- ✅ 유의한 약물 통계

#### 4. **Distribution Shift 분석**
- ✅ METABRIC vs GDSC 분포 비교
- ✅ KS test for distribution shift
- ✅ 과적합 검증

#### 5. **앙상블 vs 단독 모델 상세 비교**
- ✅ Top 15 overlap 분석
- ✅ 카테고리별 분류 비교
- ✅ 순위 상관 (Spearman)
- ✅ 예측 일관성 분석

---

## 📁 생성 파일 목록

### 예측 결과
- `catboost_predictions.npy` - CatBoost IC50 예측 (환자 × 약물)
- `ensemble_a_predictions.npy` - Ensemble A IC50 예측
- `catboost_top15.csv` - CatBoost Top 15 약물
- `ensemble_a_top15.csv` - Ensemble A Top 15 약물

### 분석 결과
- `method_a_results.json` - IC50 proxy 종합 결과
- `method_b_survival.json` - Survival analysis 결과
- `method_b_survival.csv` - Survival 결과 테이블
- `method_c_graphsage.json` - GraphSAGE ranking 결과
- `drug_categories.csv` - 약물 카테고리 분류

### 메트릭
- `ranking_metrics.json` - P@15, NDCG@15, EF@15, MAP
- `overlap_analysis.json` - Top 15 Overlap, Jaccard
- `distribution_analysis.json` - Distribution shift KS test

### 요약
- `step6_summary.json` - 전체 요약
- `step6_comprehensive_report.md` - 최종 보고서

---

## ⚙️ 실행 방법

### 1. 데이터 준비

METABRIC 데이터가 필요합니다:

```bash
# 옵션 1: cBioPortal에서 다운로드
# https://www.cbioportal.org/study/summary?id=brca_metabric
# - Expression data (RNA-seq)
# - Clinical data (OS_months, OS_status)

# 옵션 2: S3에서 다운로드 (이미 전처리된 데이터)
aws s3 cp s3://say2-4team/.../metabric_expression.parquet .
aws s3 cp s3://say2-4team/.../metabric_clinical.parquet .
```

필요한 파일:
1. `metabric_expression.parquet` - Gene expression (genes × patients)
2. `metabric_clinical.parquet` - Clinical (patient_id, OS_months, OS_status)
3. `drug_annotations.parquet` - Drug metadata

### 2. 스크립트 실행

```bash
cd step4_results/
python3 step6_metabric_comprehensive.py
```

### 3. 결과 확인

```bash
cd step6_metabric_results/
ls -lh

# JSON 결과 확인
cat method_a_results.json | jq '.overlap_analysis'
cat method_b_survival.json | jq '.summary'

# CSV 확인
head catboost_top15.csv
head ensemble_a_top15.csv
```

---

## 🎯 예상 결과

### Top 15 Overlap 예측

**가설**: 앙상블 A와 CatBoost의 Top 15 overlap ~80-90%
- 이유: 두 방법 모두 CatBoost 포함 + 높은 모델 간 상관

### Survival Analysis 예측

**가설**: 5-8개 약물이 유의한 survival difference 보임 (p<0.05)
- Target gene high expression → 더 나은 생존 (HR < 1)
- 또는 low expression → 더 나은 생존 (HR > 1)

### 약물 분류 예측

**Category 1 (BRCA 현재사용)**: 3-5개
**Category 2 (타암종 승인/임상)**: 5-7개
**Category 3 (신약 후보)**: 3-5개

---

## 🔧 현재 상태

### ✅ 완료된 작업
1. Step 6 종합 검증 스크립트 작성
2. README 및 가이드 문서 생성
3. 데이터 전처리 로직 구현
4. 모든 메트릭 계산 로직 구현
5. 결과 저장 구조 설계

### ⏳ 대기 중인 작업
1. **METABRIC 데이터 준비** ← 현재 단계
2. 스크립트 실행
3. 결과 검증 및 시각화
4. 최종 보고서 작성

### 🚀 다음 단계

#### Option 1: METABRIC 데이터 다운로드 및 실행
```bash
# 1. 데이터 준비
# 2. python3 step6_metabric_comprehensive.py
# 3. 결과 검토
```

#### Option 2: 기존 결과 활용
```bash
# 기존 models/metabric_results/ 결과 활용
# 새로운 메트릭 추가 계산만 수행
```

#### Option 3: 모의 데이터로 테스트
```bash
# 합성 데이터 생성하여 스크립트 검증
# 실제 데이터 도착 전 파이프라인 테스트
```

---

## 📌 주요 차별점

| 항목 | 이전 검증 | 새로운 종합 분석 |
|---|---|---|
| **IC50 예측** | ❌ | ✅ 환자×약물 매트릭스 |
| **앙상블 vs 단독 비교** | ❌ | ✅ 직접 비교 |
| **Ranking 메트릭** | 부분 | ✅ P@15, NDCG, MAP, EF |
| **Survival 분석** | 부분 | ✅ 완전 (KM, Cox, C-index) |
| **Distribution shift** | ❌ | ✅ KS test |
| **Top 15 약물** | Top 30 | ✅ Top 15 + 카테고리 |
| **저장 파일** | 1개 JSON | ✅ 10+ 파일 (CSV, JSON) |

---

## 💡 권장사항

1. **METABRIC 데이터 확보 우선**
   - S3에서 기존 전처리 데이터 사용 권장
   - 또는 cBioPortal에서 최신 데이터 다운로드

2. **단계별 실행**
   - Method A → Method B → Method C 순서로
   - 각 단계 결과 확인 후 다음 진행

3. **결과 검증**
   - Top 15 overlap이 너무 높으면 (>95%) diversity 부족 재확인
   - Survival p-value가 모두 유의하지 않으면 target 선택 재검토

4. **시각화 추가**
   - KM curves (Top 5 유의한 약물)
   - IC50 distribution (METABRIC vs GDSC)
   - Top 15 overlap Venn diagram

---

**작성일**: 2026-04-14
**스크립트 위치**: `step4_results/step6_metabric_comprehensive.py`
**결과 위치**: `step4_results/step6_metabric_results/`
