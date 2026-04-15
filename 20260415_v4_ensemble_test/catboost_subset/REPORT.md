# CatBoost Feature Subset 앙상블 실험 보고서

**실험 ID**: 20260415_v4_catboost_subset
**날짜**: 2026-04-15
**목적**: CatBoost Feature Subset으로 diversity 확보하여 앙상블 성능 향상

---

## 1. 실험 설계

### 1.1 가설
- 같은 CatBoost 모델이지만 다른 feature subset을 사용하면 diversity가 생겨서 앙상블 효과를 얻을 수 있을 것

### 1.2 모델 구성
- **CatBoost-Full**: 전체 features 5,529개 (v3 재사용, Holdout 0.8709)
- **CatBoost-Gene**: Gene block만 4,402개 (새로 학습)
- **CatBoost-Drug**: Drug block만 1,127개 (새로 학습)

### 1.3 학습 조건
- 동일한 하이퍼파라미터 (v3 CatBoost 설정)
- Seed=42, 5-fold CV, 20% holdout split
- 1,000 iterations, learning_rate=0.05, depth=6

---

## 2. 단독 성능 비교

| Model | Feature수 | OOF Sp | Train Sp | Gap | 판정 | Holdout Sp | Fold Std |
|-------|-----------|--------|----------|-----|------|------------|----------|
| **CatBoost-Full** | 5,529 | 0.8624 | 0.9364 | 0.074 | 허용 | **0.8709** | 0.0288 |
| **CatBoost-Gene** | 4,402 | 0.2461 | 0.2690 | 0.023 | 없음 | **0.2290** | 0.0266 |
| **CatBoost-Drug** | 1,127 | 0.8645 | 0.9448 | 0.080 | 허용 | **0.8710** | 0.0104 |

### 핵심 발견

🔥 **CatBoost-Drug만으로도 Full과 동일한 성능!**
- Drug features (1,127개)만으로 Holdout 0.8710 달성
- Gene features (4,402개)는 거의 무의미 (Holdout 0.2290)
- **IC50 예측에 필요한 모든 signal이 Drug features에 집중**

---

## 3. 상관 분석

### 3.1 Spearman 상관 행렬 (OOF)

|  | Full | Gene | Drug |
|---|------|------|------|
| **Full** | 1.0000 | 0.3121 | **0.9896** |
| **Gene** | 0.3121 | 1.0000 | 0.2926 |
| **Drug** | **0.9896** | 0.2926 | 1.0000 |

### 3.2 Top-30 Jaccard Overlap

- **Full vs Drug**: 0.7647 (23/30 overlap) - **거의 동일한 ranking**
- **Full vs Gene**: 0.0000 (0/30 overlap) - 완전히 다른 ranking
- **Drug vs Gene**: 0.0000 (0/30 overlap) - 완전히 다른 ranking

### 3.3 Diversity 판정

- **평균 Spearman 상관**: 0.5314 ✅ **우수 (< 0.90)**
- Full과 Drug는 너무 유사 (0.9896)
- Gene은 약하지만 diversity는 확보

---

## 4. 앙상블 결과

### 4.1 전체 조합 비교 (Holdout Spearman)

| Combination | Weighting | Holdout Sp | vs Baseline | 판정 |
|-------------|-----------|------------|-------------|------|
| **Full (baseline)** | N/A | **0.8709** | - | - |
| Full + Gene | Weighted (77.8%/22.2%) | 0.8608 | -0.0101 | ❌ 악화 |
| Full + Gene | Equal (50%/50%) | 0.8169 | -0.0540 | ❌ 악화 |
| **Full + Drug** | Weighted (49.9%/50.1%) | **0.8729** | **+0.0020** | ⚠️ 미미한 개선 |
| **Full + Drug** | Equal (50%/50%) | **0.8729** | **+0.0020** | ⚠️ 미미한 개선 |
| Full + Gene + Drug | Weighted (43.7%/12.5%/43.8%) | 0.8693 | -0.0016 | ❌ 악화 |
| Full + Gene + Drug | Equal (33.3% each) | 0.8533 | -0.0176 | ❌ 악화 |

### 4.2 Best Performer

🏆 **CatBoost-Full + CatBoost-Drug (Equal)**: 0.8729
- **개선폭**: +0.0020 (0.23%)
- **판정**: ⚠️ **개선이 너무 미미함 (노이즈 수준)**

### 4.3 상세 메트릭 (Best Ensemble)

| Metric | Full (baseline) | Full+Drug (Equal) | 변화 |
|--------|-----------------|-------------------|------|
| **Holdout Spearman** | 0.8709 | **0.8729** | +0.0020 |
| **Holdout RMSE** | 1.1388 | **1.1315** | -0.0073 |
| **P@30** | 0.6333 | 0.6333 | 0.0000 |
| **NDCG@30** | 0.9848 | **0.9862** | +0.0014 |

---

## 5. 실패 원인 분석

### 5.1 왜 앙상블이 실패했는가?

1. **Full ≈ Drug (상관 0.9896)**
   - Drug features가 Full features의 거의 모든 signal을 포함
   - 앙상블은 본질적으로 같은 모델을 평균한 것
   - Diversity가 거의 없어서 앙상블 효과 없음

2. **Gene은 너무 약함 (Holdout 0.2290)**
   - Gene features만으로는 IC50 예측 불가능
   - 앙상블에 추가하면 성능 좋은 Full/Drug를 희석
   - Diversity는 있지만 성능 trade-off가 너무 큼

3. **Feature 분포의 불균형**
   - Drug features: 1,127개 (20.4%) → 높은 signal
   - Gene features: 4,402개 (79.6%) → 낮은 signal
   - **IC50는 본질적으로 drug property** (CRISPR은 간접적)

### 5.2 Gene Features가 왜 약한가?

**이론적 배경**:
- IC50 = Drug의 세포 억제 농도 (drug-centric metric)
- CRISPR gene knockout = 유전자 의존성 (gene-centric metric)
- 두 개념의 직접적 연관성이 약함

**실험 결과**:
- Drug features만으로 0.8710 (Full과 동일)
- Gene features 추가해도 0.8729 (단 +0.0020)
- **Gene features는 redundant information만 제공**

---

## 6. 결론 및 권고사항

### 6.1 실험 결론

❌ **CatBoost Feature Subset 앙상블 실패**

- Best ensemble (Full+Drug): 0.8729 (+0.0020)
- **개선폭이 너무 미미함** (통계적으로 의미 없음)
- Full과 Drug의 높은 상관(0.9896)으로 diversity 부족
- Gene 추가는 오히려 성능 악화

### 6.2 최종 권고

**권장 모델**: **CatBoost-Full 단독 (0.8709)**

**이유**:
1. 앙상블의 미미한 개선(+0.0020)은 노이즈 수준
2. 모델 복잡도 증가 대비 benefit 없음
3. 단일 모델이 해석 가능성, 배포 용이성 측면에서 우수

### 6.3 향후 연구 방향

Feature subset 앙상블 대신 다음 접근 권장:

1. **다른 알고리즘 조합**
   - CatBoost + Neural Network (이미 시도: SAINT 실패)
   - CatBoost + Graph Network (HGT 학습 중)

2. **Stacking 접근**
   - Level-1: Multiple base models
   - Level-2: Meta-learner (CatBoost)

3. **Domain-specific features 추가**
   - Drug-Target interaction features
   - Pathway information from Neo4j KG
   - 3D molecular descriptors

4. **Transfer Learning**
   - Pre-trained molecular embeddings (ChemBERT, MolFormer)
   - Fine-tune on IC50 prediction task

---

## 7. 파일 목록

### 7.1 모델 Artifacts
- `catboost_gene/catboost_gene_model.pkl`
- `catboost_gene/catboost_gene_oof.npy` ✅
- `catboost_gene/catboost_gene_holdout.npy` ✅
- `catboost_gene/catboost_gene_results.json`
- `catboost_drug/catboost_drug_model.pkl`
- `catboost_drug/catboost_drug_oof.npy` ✅
- `catboost_drug/catboost_drug_holdout.npy` ✅
- `catboost_drug/catboost_drug_results.json`

### 7.2 분석 결과
- `correlation/3model_correlation_matrix.json` ✅
- `correlation/top30_overlap.json`
- `ensemble/ablation_results.json` ✅
- `ensemble/top30_*.csv` (7 files)

### 7.3 코드
- `train_catboost_subsets.py`
- `analyze_correlation.py`
- `ensemble_evaluation.py`
- `REPORT.md` ✅

---

## 8. 부록: 상세 메트릭

### 8.1 CatBoost-Gene 상세

```json
{
  "model": "CatBoost-Gene",
  "n_features": 4402,
  "metrics": {
    "train_spearman": 0.2690,
    "oof_spearman": 0.2461,
    "holdout_spearman": 0.2290,
    "gap": 0.0229,
    "fold_std": 0.0266,
    "overfitting_verdict": "없음"
  }
}
```

### 8.2 CatBoost-Drug 상세

```json
{
  "model": "CatBoost-Drug",
  "n_features": 1127,
  "metrics": {
    "train_spearman": 0.9448,
    "oof_spearman": 0.8645,
    "holdout_spearman": 0.8710,
    "gap": 0.0803,
    "fold_std": 0.0104,
    "overfitting_verdict": "허용"
  }
}
```

---

**실험 결론**: Feature subset 앙상블은 **실패**. CatBoost-Full 단독 사용 권장.
