# 3개 실험 최종 비교 보고서
> 생성일: 2026-04-13 18:47
> BRCA Drug Repurposing ML Pipeline

## 1. 실험 설계 비교

| 항목 | 20260410 Multimodal | Pipeline A (Mechanism) | Pipeline B (Drug Chem) |
|------|---------------------|----------------------|----------------------|
| **CV 방식** | KFold(5) random split | GroupKFold(5) by drug | GroupKFold(5) by drug |
| **Leakage** | **있음** (동일 약물 train/test 혼재) | **없음** (약물 단위 분리) | **없음** (약물 단위 분리) |
| **모델 수** | 7 (GB3 + DL4) | 4 (Stacking, CB, RF, XG) | 4 (Stacking, CB, RF, XG) |
| **앙상블** | Spearman 비례 7-model | Spearman 비례 4-model | Spearman 비례 4-model |
| **Feature 수** | ~20,000+ (5 modality) | 2,182 (base + mech) | 2,059 (drug chem only) |
| **CRISPR** | O (18,310) | O (18,310) | **X** |
| **Morgan FP** | O (2,048) | O (2,048) | O (2,048) |
| **Drug Desc** | O (9) | O (9) | O (9) |
| **LINCS** | O (5) | O (5) | **X** |
| **Target Gene** | O (10) | O (10) | **X** |
| **Mechanism** | X | O (v1=5, v2=10) | **X** |
| **Pathway** | X | O (포함) | **X** |

### Leakage 문제 (20260410)

20260410 실험은 **KFold random split**을 사용하여 동일 약물의 다른 세포주 데이터가 
train/test에 동시 존재합니다. 이는 약물 수준 예측의 **과대평가**를 초래합니다.

- Main CV Spearman: ~0.805 (과대평가)
- Drug Group Test Spearman: ~0.496 (실제 일반화 성능)
- **Gap: ~0.31** → leakage로 인한 과대평가 확인

## 2. 성능 비교

### 2.1 전체 성능 비교 (Best Model 기준)

| 지표 | 20260410 (CV) | 20260410 (DrugGroup) | Pipeline A | Pipeline B |
|------|-------------|---------------------|------------|------------|
| **Spearman** | N/A | N/A | 0.5182 | 0.3323 |
| **RMSE** | N/A | N/A | N/A | 2.3404 |
| **Leakage** | O | O | X | X |
| **공정 비교** | X | **O** | **O** | **O** |

### 2.2 모델별 상세 비교 (Pipeline A vs B)

| 모델 | A Spearman | B Spearman | Delta | A Gap | B Gap |
|------|-----------|-----------|-------|-------|-------|
| Stacking_Ridge | 0.5182 | 0.3275 | -0.1907 | N/A | 0.4047 |
| CatBoost | 0.5140 | 0.3319 | -0.1821 | N/A | 0.3569 |
| RandomForest | 0.5064 | 0.2929 | -0.2135 | N/A | 0.4388 |
| XGBoost | 0.4908 | 0.3323 | -0.1585 | N/A | 0.3948 |

### 2.3 성능 해석

- **20260410**: CV Spearman 0.805는 leakage로 과대평가. Drug Group Test 0.496이 실제 성능
- **Pipeline A**: GroupKFold 기반 0.518로 가장 **공정하고 신뢰할 수 있는** 성능
- **Pipeline B**: 약물 구조만으로 0.332 → 생물학적 feature 없이는 한계 명확
- **A→B 성능 하락**: 0.1859 → CRISPR/pathway/mechanism features가 전체 성능의 **36%** 기여

## 3. 추천 약물 비교

### 3.1 약물 겹침 요약

| 비교 | 약물 수 |
|------|--------|
| 20260410 Top 15 전체 | 15 |
| Pipeline A Top 30 전체 | 28 |
| Pipeline B Top 30 전체 | 28 |
| **3개 실험 공통** | **7** |
| Pipeline A ∩ B | 22 |
| 20260410 ∩ Pipeline A | 7 |
| 20260410 ∩ Pipeline B | 8 |

### 3.2 3개 실험 공통 약물 (가장 신뢰도 높음)

| 약물 | 20260410 | Pipeline A Rank | Pipeline B Rank |
|------|---------|----------------|----------------|
| **Dactinomycin** | Top 15 | #2 | #2 |
| **Docetaxel** | Top 15 | #1 | #1 |
| **Epirubicin** | Top 15 | #11 | #12 |
| **Paclitaxel** | Top 15 | #3 | #3 |
| **Rapamycin** | Top 15 | #17 | #17 |
| **Vinblastine** | Top 15 | #4 | #8 |
| **Vinorelbine** | Top 15 | #5 | #6 |

### 3.3 Pipeline A ∩ B 공통 약물

| 약물 | A Rank | B Rank | A Pred IC50 | B Pred IC50 |
|------|--------|--------|------------|------------|
| ABT737 | #23 | #22 | 1.8215 | 1.7302 |
| AZD2014 | #15 | #15 | 1.3807 | 1.2730 |
| AZD5582 | #26 | #18 | 1.8581 | 1.4983 |
| Avagacestat | #19 | #13 | 1.5645 | 1.0691 |
| Dactinomycin | #2 | #2 | -2.2883 | -3.5968 |
| Docetaxel | #1 | #1 | -4.0820 | -4.0509 |
| Epirubicin | #11 | #12 | 0.4393 | 1.0338 |
| LMP744 | #25 | #19 | 1.8375 | 1.6007 |
| MK-2206 | #22 | #24 | 1.7145 | 1.8567 |
| Methotrexate | #18 | #29 | 1.5282 | 2.0516 |
| Mitoxantrone | #12 | #14 | 0.8630 | 1.2729 |
| Paclitaxel | #3 | #3 | -2.1565 | -2.1254 |
| Pictilisib | #24 | #23 | 1.8369 | 1.7861 |
| Rapamycin | #17 | #17 | 1.4856 | 1.4333 |
| SL0101 | #9 | #9 | -0.2720 | -0.4067 |
| Sabutoclax | #21 | #20 | 1.6995 | 1.6449 |
| Tanespimycin | #16 | #16 | 1.4131 | 1.3541 |
| Temsirolimus | #6 | #4 | -1.0676 | -1.8734 |
| Teniposide | #10 | #10 | -0.1727 | 0.0564 |
| Topotecan | #7 | #11 | -0.4962 | 0.1582 |
| Vinblastine | #4 | #8 | -1.2843 | -1.0049 |
| Vinorelbine | #5 | #6 | -1.1783 | -1.4049 |

### 3.4 각 실험 고유 약물

**20260410에만 있는 약물** (7개):
- Bortezomib
- Camptothecin
- Dinaciclib
- Luminespib
- SN-38
- Sepantronium bromide
- Staurosporine

**Pipeline A에만 있는 약물** (6개):
- CDK9_5038
- CDK9_5576
- Fulvestrant
- Irinotecan
- TW 37
- Tozasertib

**Pipeline B에만 있는 약물** (5개):
- AZD6738
- Bromosporine
- EPZ004777
- Elephantin
- Refametinib

## 4. 결론

### 4.1 실험별 평가

#### 20260410 Multimodal Fusion
- **장점**: 다양한 모달리티 활용, 높은 표면 성능 (0.805)
- **치명적 문제**: KFold random split → **약물 수준 leakage**
- **실제 성능**: Drug Group Test Spearman 0.496
- **판정**: 성능 수치 신뢰 불가, CV 방식 교정 필요

#### Pipeline A (Mechanism Engine)
- **장점**: GroupKFold로 leakage 제거, 생물학적 feature 활용
- **성능**: Spearman 0.518 (공정 평가)
- **특징**: CRISPR + pathway + mechanism features가 예측력의 핵심
- **판정**: **가장 신뢰할 수 있는 파이프라인**

#### Pipeline B (Drug Chemistry Only)
- **장점**: GroupKFold로 leakage 제거, 약물 구조만으로 독립적 검증
- **성능**: Spearman 0.332 (공정 평가)
- **특징**: 약물 구조 정보만으로의 예측 한계 확인
- **판정**: 단독 사용 부적합, Pipeline A의 ablation study로 가치 있음

### 4.2 Feature 기여도 분석

Pipeline A vs B 비교를 통한 feature 기여도:

| Feature Group | 기여도 (추정) |
|------|--------|
| 약물 화학 구조 (Morgan FP + Desc) | 0.3323 (64.1%) |
| 생물학적 features (CRISPR + pathway + target + mechanism) | +0.1859 (35.9%) |
| **총 성능** | **0.5182 (100%)** |

→ 약물 구조가 기본 예측력을 제공하지만, **생물학적 context가 성능의 ~36%를 추가**로 기여

### 4.3 재창출 관점 권장 파이프라인

```
권장: Pipeline A (Mechanism Engine)
```

**이유:**
1. **공정한 평가**: GroupKFold로 약물 수준 leakage 완전 제거
2. **최고 성능**: Spearman 0.518 (공정 비교 기준)
3. **생물학적 해석 가능**: Mechanism features가 약물 작용 기전 설명
4. **약물 발견 적합**: 새로운 약물에 대한 일반화 능력 검증됨

**Pipeline B의 역할:**
- Pipeline A의 ablation study로서 feature 기여도 검증
- 약물 구조만의 baseline 성능 제공
- Pipeline A 추천 약물의 교차 검증 (A∩B 공통 약물 = 높은 신뢰도)

**20260410의 교훈:**
- 높은 CV 성능이 실제 일반화를 보장하지 않음
- 약물 수준 예측에서는 반드시 GroupKFold(by drug) 사용
- Drug Group Test 결과 (0.496)는 Pipeline A (0.518)보다 낮음
  → 올바른 CV가 더 정직하고 더 나은 모델을 만듦

---
*Generated: 2026-04-13 18:47*
