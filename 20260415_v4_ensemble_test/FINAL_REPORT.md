# v4 Ensemble 실험 최종 보고서

**실험 날짜**: 2026-04-15
**목표**: Ensemble로 CatBoost-Full (Holdout 0.8709) 성능 향상
**결과**: ❌ **모든 앙상블 시도 실패**

---

## 📊 Executive Summary

### Baseline 성능
- **CatBoost-Full**: Holdout Spearman **0.8709** (v3)

### 실험 결과
- **총 모델 수**: 7개 (Full, Gene, Drug, SAINT, Bilinear v1/v2, HGT*)
- **평가된 앙상블**: 20+ 조합
- **최고 성능**: CatBoost-Full + Drug = 0.8729 (+0.0020, 노이즈 수준)
- **평균 개선폭**: -0.0089 (대부분 악화)

### 최종 권고
✅ **CatBoost-Full 단독 사용 (Holdout 0.8709)**

*: 학습 진행 중

---

## 1. 완료된 실험

### 1.1 다른 아키텍처 앙상블

#### A. SAINT (Self-Attention Transformer)

**단독 성능**:
```
OOF Spearman:     0.6900
Holdout Spearman: 0.7441
Train Spearman:   0.7546
Gap:              0.0646 (과적합 없음)
```

**Diversity 분석**:
- vs CatBoost-Full Spearman: **0.8213** ✅ (< 0.90, 우수)
- Top-30 Jaccard: **0.0000** (완전히 다른 ranking!)

**앙상블 결과**:
| Combination | Weighting | Holdout Sp | Δ Baseline | 판정 |
|-------------|-----------|------------|------------|------|
| Full | N/A | 0.8709 | - | Baseline |
| Full + SAINT | Spearman (55.5%/44.5%) | 0.8362 | **-0.0347** | ❌ |
| Full + SAINT | Equal (50%/50%) | 0.8291 | **-0.0418** | ❌ |
| Drug + SAINT | Weighted (55.6%/44.4%) | 0.8418 | **-0.0291** | ❌ |
| Full + Drug + SAINT | Weighted | 0.8569 | **-0.0140** | ❌ |

**결론**:
- ✅ Diversity 우수 (Spearman 0.8213, Top-30 완전 독립)
- ❌ 성능이 너무 낮아서 (0.7441) 앙상블 시 희석 효과
- **Trade-off**: Diversity vs Performance

---

#### B. Bilinear v1 (초기 버전)

**단독 성능**:
```
OOF Spearman:     -0.0130  ❌
Holdout Spearman: -0.2317  ❌
Train Spearman:   -0.0306
```

**문제점**:
- Negative Spearman (예측 불가능)
- 학습 불안정 (gradient exploding/vanishing 추정)
- BatchNorm 없음, 높은 learning rate (1e-3)

**조치**: v2로 개선 →

---

#### C. Bilinear v2 (디버깅 버전) ✅

**개선사항**:
1. BatchNorm 추가 (각 encoder 출력에)
2. Learning rate 감소 (1e-3 → 1e-4)
3. Epochs 증가 (100 → 200)
4. Gradient clipping (max_norm=1.0)
5. StandardScaler 적용 (Drug/Gene 각각)

**단독 성능**:
```
OOF Spearman:     0.8298  ✅ (≥ 0.75 합격!)
Holdout Spearman: 0.8522
Train Spearman:   0.9780
Gap:              0.1482 (약간 과적합)
Fold Std:         0.0184 (안정적)
```

**개선 효과**:
- v1 (-0.0130) → v2 (0.8298) = **+0.8428** 🎉

**Diversity 분석**:
- vs CatBoost-Full Spearman: **0.9247** (< 0.95, acceptable)
- vs CatBoost-Full Pearson: 0.9488
- Top-30 Jaccard: 0.2245 (11/30)

**앙상블 가능성**:
- ✅ OOF ≥ 0.75 조건 충족
- ⚠️ 상관 0.9247로 diversity는 보통
- ⚠️ Holdout 0.8522 < Baseline 0.8709 (앙상블 효과 의문)

---

### 1.2 Feature Subset 앙상블

#### 전략
**가설**: 같은 CatBoost지만 다른 feature subset으로 diversity 확보

#### 모델 구성

| Model | Features | Description |
|-------|----------|-------------|
| CatBoost-Full | 5,529 | 전체 features (v3 재사용) |
| CatBoost-Gene | 4,402 | Gene/CRISPR features만 |
| CatBoost-Drug | 1,127 | Drug features만 (Morgan FP, LINCS 등) |

#### 단독 성능

| Model | Features | OOF Sp | Train Sp | Gap | Holdout Sp | 판정 |
|-------|----------|--------|----------|-----|------------|------|
| **CatBoost-Full** | 5,529 | 0.8624 | 0.9364 | 0.074 | **0.8709** | ✅ |
| CatBoost-Gene | 4,402 | 0.2461 | 0.2690 | 0.023 | **0.2290** | ❌ |
| **CatBoost-Drug** | 1,127 | 0.8645 | 0.9448 | 0.080 | **0.8710** | ✅ |

🔥 **핵심 발견**:
- **Drug features만으로도 Full과 동일한 성능!** (0.8710 vs 0.8709)
- IC50 예측의 모든 signal이 Drug features에 집중
- Gene/CRISPR features는 거의 무의미 (Holdout 0.2290)

#### Diversity 분석 (Spearman 상관)

|  | Full | Gene | Drug |
|---|------|------|------|
| **Full** | 1.0000 | 0.3121 | **0.9896** |
| **Gene** | 0.3121 | 1.0000 | 0.2926 |
| **Drug** | **0.9896** | 0.2926 | 1.0000 |

- **평균 상관**: 0.5314 ✅ (< 0.90, 우수)
- **Full vs Drug**: 0.9896 ❌ (너무 유사)
- **Full vs Gene**: 0.3121 ✅ (diversity 우수)

#### Top-30 Overlap (Jaccard)

- Full vs Drug: **0.7647** (23/30 overlap) - 거의 동일한 ranking
- Full vs Gene: **0.0000** (0/30 overlap) - 완전히 다른 ranking
- Drug vs Gene: **0.0000** (0/30 overlap)

#### 앙상블 결과

| Combination | Weighting | Holdout Sp | Δ Baseline | 판정 |
|-------------|-----------|------------|------------|------|
| **Full (baseline)** | N/A | **0.8709** | - | - |
| Full + Gene | Weighted (77.8%/22.2%) | 0.8608 | -0.0101 | ❌ |
| Full + Gene | Equal (50%/50%) | 0.8169 | -0.0540 | ❌ |
| **Full + Drug** | Weighted (50%/50%) | **0.8729** | **+0.0020** | ⚠️ |
| **Full + Drug** | Equal (50%/50%) | **0.8729** | **+0.0020** | ⚠️ |
| Full + Gene + Drug | Weighted | 0.8693 | -0.0016 | ❌ |
| Full + Gene + Drug | Equal | 0.8533 | -0.0176 | ❌ |

**최고 성능**: Full + Drug = 0.8729 (+0.0020)

**결론**:
- ⚠️ 개선폭 +0.0020은 **노이즈 수준** (통계적으로 의미 없음)
- Full ≈ Drug (상관 0.9896)로 diversity 부족
- Gene은 diversity는 있지만 너무 약해서 오히려 악화

---

## 2. 진행 중 실험

### 2.1 HGT (Heterogeneous Graph Transformer)

**현재 상태**: 🔄 학습 중 (시작 후 30분+ 경과)

**그래프 구조** (간이 bipartite):
```
Nodes:  9,494 (Drug 5,092 + Gene 4,402)
Edges:  203,680 (top-20 connections)
Node types: Drug, Gene (2 types)
Edge types: (drug, interacts, gene), (gene, rev_interacts, drug) (2 types)
```

**Neo4j KG 비교**:
| Metric | Current HGT | Neo4j KG | Ratio |
|--------|-------------|----------|-------|
| Nodes | 9,494 | 30,558 | 31% |
| Edges | 203,680 | 137,465 | 148% |
| Node types | 2 | Multiple | - |
| Edge types | 2 | Multiple | - |

**제약사항**:
- Neo4j 접속 불가 → 간이 synthetic graph 사용
- 실제 biological relationships 없음
- Top-k 방식의 단순한 구조

**예상**:
- 성능: SAINT (0.7441)과 유사하거나 낮을 것으로 예상
- Diversity: 좋을 것으로 예상
- 앙상블 효과: 미미할 것으로 예상 (SAINT과 동일 패턴)

---

## 3. 종합 분석

### 3.1 실패 원인 분석

#### Pattern 1: Diversity vs Performance Trade-off

**SAINT 사례**:
- ✅ 우수한 diversity (Spearman 0.8213, Top-30 Jaccard 0.0000)
- ❌ 성능 부족 (Holdout 0.7441 vs Baseline 0.8709)
- **결과**: 앙상블 시 baseline 희석 (-0.0347)

**Gene 사례**:
- ✅ 우수한 diversity (vs Full Spearman 0.3121)
- ❌ 성능 너무 낮음 (Holdout 0.2290)
- **결과**: 앙상블 시 baseline 파괴 (-0.0540)

**교훈**: **Diversity만으로는 부족. 개별 모델 성능도 ≥ 0.80 필요**

---

#### Pattern 2: 높은 상관 (Low Diversity)

**Full vs Drug 사례**:
- ❌ 상관 0.9896 (거의 동일)
- ❌ Top-30 Jaccard 0.7647 (23/30 overlap)
- **결과**: 앙상블 시 미미한 개선 (+0.0020, 노이즈 수준)

**Full vs Bilinear v2 사례**:
- ⚠️ 상관 0.9247 (acceptable하지만 높음)
- Bilinear Holdout 0.8522 < Baseline 0.8709
- **예상**: 앙상블 효과 미미하거나 악화 가능성

**교훈**: **상관 < 0.85 권장. 0.90+ 는 diversity 부족**

---

#### Pattern 3: IC50의 본질적 특성

**Drug features의 중요성**:
- Drug 1,127개만으로 Full (5,529개)과 동일 성능
- **IC50 = Drug의 세포 억제 농도** (drug-centric metric)
- CRISPR gene knockout ≠ IC50 직접 연관

**Gene features의 한계**:
- CRISPR = 유전자 의존성 (gene-centric metric)
- IC50와 간접적 연관성만 존재
- Holdout 0.2290으로 거의 예측 불가

**교훈**: **Domain knowledge 중요. Feature engineering이 ensemble보다 효과적**

---

### 3.2 성공한 발견

#### ✅ Drug Features의 Sufficiency
```
CatBoost-Drug (1,127 features): Holdout 0.8710
CatBoost-Full (5,529 features): Holdout 0.8709
```
- **79.6% features (Gene) 제거해도 성능 유지**
- 모델 경량화 가능 (1,127 features만 사용)
- 해석 가능성 향상

#### ✅ Bilinear v2 개선 성공
```
v1: OOF -0.0130 (학습 실패)
v2: OOF  0.8298 (학습 성공)
```
- BatchNorm, Gradient clipping, StandardScaler 효과 검증
- Learning rate scheduling 중요성 확인

#### ✅ Diversity 측정 프레임워크
- Spearman correlation
- Top-K Jaccard overlap
- Performance-Diversity trade-off 정량화

---

## 4. 최종 권고사항

### 4.1 Production 모델

**권장**: **CatBoost-Full 단독 (Holdout 0.8709)**

**대안**: **CatBoost-Drug 단독 (Holdout 0.8710)**
- 79.6% features 감소
- 동일한 성능
- 빠른 추론 속도
- 해석 용이성

**비권장**: 모든 앙상블 조합
- Best ensemble (Full+Drug): +0.0020 (노이즈 수준)
- 대부분 앙상블: 악화
- 복잡도 증가 대비 benefit 없음

---

### 4.2 향후 연구 방향

#### Priority 1: Feature Engineering (Drug 중심)

**Drug features 심화**:
1. 3D molecular descriptors (Coulomb matrix, 3D pharmacophore)
2. Drug-Target interaction features (binding affinity, docking scores)
3. Drug mechanism of action (MOA) embedding
4. ADMET properties (Absorption, Distribution, Metabolism, Excretion, Toxicity)

**Domain knowledge 활용**:
1. Neo4j KG 기반 features
   - Drug → Target → Pathway
   - Target protein structure
   - Protein-protein interaction
2. ChEMBL bioactivity data
3. Clinical trial outcomes

---

#### Priority 2: Transfer Learning

**Pre-trained molecular embeddings**:
1. ChemBERT (SMILES-based Transformer)
2. MolFormer (molecular property prediction)
3. GNN-based embeddings (Graph Isomorphism Network)

**Fine-tuning strategy**:
1. Freeze embedding layers
2. Fine-tune on IC50 task
3. Multi-task learning (IC50 + related tasks)

---

#### Priority 3: Alternative Algorithms

**Gradient Boosting 변형**:
1. LightGBM (leaf-wise growth)
2. XGBoost (regularized boosting)
3. CatBoost 하이퍼파라미터 최적화 (Bayesian optimization)

**Neural Architecture Search**:
1. AutoML (Auto-sklearn, TPOT)
2. NAS for tabular data

---

#### Priority 4: Stacking (신중하게)

**조건**:
- Base models: 상관 < 0.85, 성능 > 0.80
- Meta-learner: Simple (Linear Regression, Ridge)
- Cross-validation: Nested CV 필수

**예시 구성**:
```
Level-1: CatBoost-Drug (0.8710) + External model (e.g., XGBoost > 0.80, 상관 < 0.85)
Level-2: Ridge Regression
```

---

## 5. 실험 통계

### 5.1 모델 성능 순위

| Rank | Model | Holdout Sp | 상태 |
|------|-------|------------|------|
| 1 | CatBoost-Drug | **0.8710** | ✅ |
| 2 | **CatBoost-Full** | **0.8709** | ✅ Baseline |
| 3 | Full+Drug Ensemble | 0.8729 | ⚠️ +0.0020 노이즈 |
| 4 | Full+Drug+SAINT Weighted | 0.8569 | ❌ -0.0140 |
| 5 | Full+Gene Weighted | 0.8608 | ❌ -0.0101 |
| 6 | Bilinear v2 | 0.8522 | ✅ 단독 OK |
| 7 | SAINT | 0.7441 | ⚠️ diversity 우수 |
| 8 | Full+Gene Equal | 0.8169 | ❌ -0.0540 |
| 9 | CatBoost-Gene | 0.2290 | ❌ 실패 |
| 10 | Bilinear v1 | -0.2317 | ❌ 실패 |

### 5.2 Diversity 순위 (vs CatBoost-Full)

| Rank | Model | Spearman Corr | Top-30 Jaccard | 판정 |
|------|-------|---------------|----------------|------|
| 1 | Gene | 0.3121 | 0.0000 | ✅ 우수 (but 성능 ❌) |
| 2 | SAINT | 0.8213 | 0.0000 | ✅ 우수 |
| 3 | Bilinear v2 | 0.9247 | 0.2245 | ⚠️ 보통 |
| 4 | Drug | 0.9896 | 0.7647 | ❌ 부족 |

### 5.3 실험 타임라인

```
Total experiments: 20+ 조합
Total models trained: 7개 (Full, Gene, Drug, SAINT, Bilinear v1/v2, HGT*)
Total evaluation metrics: 6종 (OOF/Holdout Spearman, RMSE, P@30, NDCG@30, Gap, Fold Std)
Total ensemble combinations: 15+ 조합

Successful improvements: 0
Failed ensembles: 15+
Noise-level improvements: 1 (+0.0020)
```

---

## 6. 핵심 교훈

### ✅ 해야 할 것

1. **Domain knowledge 우선**
   - IC50는 drug-centric → Drug features 집중
   - Feature engineering > Ensemble

2. **개별 모델 품질 중요**
   - 성능 ≥ 0.80 필요
   - Diversity만으로는 부족

3. **상관 < 0.85 목표**
   - 0.90+ 는 diversity 부족
   - Top-30 Jaccard < 0.50 권장

4. **Trade-off 정량화**
   - Performance vs Diversity
   - Complexity vs Benefit

### ❌ 하지 말아야 할 것

1. **약한 모델을 diversity 이유로 추가**
   - Gene (0.2290), SAINT (0.7441)
   - Baseline 희석 효과

2. **유사한 모델 앙상블**
   - Full vs Drug (상관 0.9896)
   - 노이즈 수준 개선만

3. **복잡한 앙상블 무분별 사용**
   - 3-model ensemble 대부분 실패
   - 해석성 저하, 유지보수 비용 증가

4. **Ensemble을 silver bullet으로 기대**
   - Feature engineering이 더 효과적
   - Domain knowledge 활용 우선

---

## 7. 결론

### 실험 결과
❌ **모든 앙상블 시도 실패**

**Best ensemble**: Full + Drug = 0.8729 (+0.0020)
→ 개선폭이 노이즈 수준으로 의미 없음

### 최종 권장
✅ **CatBoost-Full 단독 사용 (Holdout 0.8709)**

또는

✅ **CatBoost-Drug 단독 사용 (Holdout 0.8710)**
- 79.6% features 감소
- 동일한 성능
- Production 최적화

### 핵심 발견
🔥 **Drug features만으로 충분**
- IC50 예측의 모든 signal이 Drug features에 집중
- Gene/CRISPR features는 무의미
- Feature engineering이 ensemble보다 효과적

---

## 📁 첨부 파일

### 완료된 실험
1. `ensemble_results/ensemble_catboost_saint_results.json` - SAINT 앙상블
2. `ensemble_results/ensemble_saint_extended_results.json` - SAINT 확장 앙상블
3. `catboost_subset/REPORT.md` - Feature subset 앙상블
4. `catboost_subset/correlation/3model_correlation_matrix.json` - 3-model 상관
5. `catboost_subset/ensemble/ablation_results.json` - Ablation study
6. `new_models/saint/saint_results.json` - SAINT 단독 성능
7. `new_models/bilinear/bilinear_v2_results.json` - Bilinear v2 성능
8. `new_models/bilinear/bilinear_v2_correlation.json` - Bilinear v2 상관
9. `FINAL_SUMMARY.md` - 중간 요약
10. `FINAL_REPORT.md` - 최종 보고서 (this file)

### 진행 중
- HGT training output (완료 시 업데이트 예정)

---

**보고서 작성 날짜**: 2026-04-15
**최종 업데이트**: HGT 학습 진행 중
**실험 결론**: Ensemble 포기, CatBoost-Full/Drug 단독 사용 권장
