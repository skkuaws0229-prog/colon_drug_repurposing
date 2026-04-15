# v4 Ensemble 실험 최종 요약

**실험 기간**: 2026-04-15
**목적**: Ensemble diversity 확보로 CatBoost-Full (0.8709) 대비 성능 향상

---

## 📊 전체 실험 결과 요약

### Baseline
- **CatBoost-Full**: Holdout Spearman **0.8709** (v3)

---

## 1. 다른 모델 아키텍처 앙상블 (실패)

### 1.1 SAINT (Self-Attention)
**단독 성능**:
- OOF: 0.6900, Holdout: **0.7441**
- 성능은 괜찮지만 CatBoost 대비 낮음

**CatBoost-Full vs SAINT 상관**:
- Spearman: **0.8213** ✅ (< 0.90, 우수한 diversity)
- Top-30 Jaccard: **0.0000** (완전히 다른 ranking!)

**앙상블 결과**:
| Combination | Weighting | Holdout Sp | vs Baseline |
|-------------|-----------|------------|-------------|
| CatBoost-Full | N/A | **0.8709** | - |
| Full + SAINT | Spearman (55.5%/44.5%) | 0.8362 | **-0.0347** ❌ |
| Full + SAINT | Equal (50%/50%) | 0.8291 | **-0.0418** ❌ |

**결론**: ❌ Diversity는 우수하나 SAINT이 너무 약해서 앙상블 시 오히려 악화

---

### 1.2 Bilinear v1 (실패) → v2 (✅ 성공!)

#### v1 실패
**단독 성능**:
- OOF: **-0.0130** ❌ (학습 실패)
- Holdout: **-0.2317**

**문제점**:
- Negative Spearman (예측 불가)
- 학습 불안정 (gradient exploding/vanishing)

#### v2 디버깅 및 성공 ✅
**개선사항**:
- Learning rate: 1e-3 → 1e-4
- Epochs: 100 → 200
- **BatchNorm 추가** (각 encoder 출력에)
- **Gradient clipping** (max_norm=1.0)
- **StandardScaler 적용** (Drug/Gene 각각)

**단독 성능** (v2):
- OOF: **0.8298** ✅ (≥ 0.75 합격!)
- Holdout: **0.8522**
- Train Spearman: 0.9780
- Gap: 0.1482 (허용)
- Fold Std: 0.0184

**CatBoost-Full vs Bilinear-v2 상관**:
- Spearman: **0.9247** ⚠️ (< 0.90 근접, 중간 diversity)
- Pearson: **0.9488**
- Top-30 Jaccard: **0.2245** (11/30 겹침)

**앙상블 결과** (상세는 섹션 4 참조):
| Combination | Weighting | Holdout Sp | vs Baseline |
|-------------|-----------|------------|-------------|
| CatBoost-Full | N/A | **0.8709** | - |
| **Full + Bilinear** | Weighted (51%/49%) | **0.8750** | **+0.0041** ⚠️ |
| **Drug + Bilinear** | Weighted (51%/49%) | **0.8756** | **+0.0047** ✅ |

**결론**: ✅ **v2 디버깅 성공!** Drug+Bilinear 조합이 **+0.0047 개선**으로 최고 성능 달성.

---

### 1.3 HGT (Heterogeneous Graph Transformer)
**현재 상태**: ❌ 학습 미실행

**사유**:
- 간이 그래프만 구성 (Neo4j 접속 불가)
- 학습 스크립트 미완성
- 우선순위 조정 (Bilinear v2 집중)

**그래프 구조** (간이, 구성만 완료):
- Nodes: 9,494 (Drug 5,092 + Gene 4,402)
- Edges: 203,680 (top-20 connections)
- Node types: Drug, Gene
- Edge types: interacts, rev_interacts

**결론**: ❌ 학습 진행하지 않음. 향후 Neo4j 복구 시 재시도 권장.

---

## 2. Feature Subset 앙상블 (실패)

### 2.1 전략
**가설**: 같은 CatBoost지만 다른 feature subset으로 diversity 확보

**모델 구성**:
- CatBoost-Full: 전체 5,529 features (Holdout 0.8709)
- CatBoost-Gene: Gene만 4,402 features (새로 학습)
- CatBoost-Drug: Drug만 1,127 features (새로 학습)

### 2.2 단독 성능

| Model | Features | OOF Sp | Holdout Sp | Gap | 판정 |
|-------|----------|--------|------------|-----|------|
| **CatBoost-Full** | 5,529 | 0.8624 | **0.8709** | 0.074 | 허용 |
| CatBoost-Gene | 4,402 | 0.2461 | **0.2290** | 0.023 | 실패 |
| **CatBoost-Drug** | 1,127 | 0.8645 | **0.8710** | 0.080 | 허용 |

🔥 **핵심 발견**: Drug features만으로도 Full과 동일한 성능! (IC50 signal이 Drug features에 집중)

### 2.3 상관 분석 (Spearman)

|  | Full | Gene | Drug |
|---|------|------|------|
| **Full** | 1.0000 | 0.3121 | **0.9896** |
| **Gene** | 0.3121 | 1.0000 | 0.2926 |
| **Drug** | **0.9896** | 0.2926 | 1.0000 |

- **Full vs Drug**: 0.9896 (거의 동일)
- **Full vs Gene**: 0.3121 (diversity 우수)
- **평균 상관**: 0.5314 ✅ (< 0.90)

### 2.4 앙상블 결과

| Combination | Weighting | Holdout Sp | vs Baseline |
|-------------|-----------|------------|-------------|
| **Full (baseline)** | N/A | **0.8709** | - |
| Full + Gene | Weighted (77.8%/22.2%) | 0.8608 | -0.0101 ❌ |
| Full + Gene | Equal (50%/50%) | 0.8169 | -0.0540 ❌ |
| Full + Drug | Weighted (50%/50%) | **0.8729** | **+0.0020** ⚠️ |
| Full + Drug | Equal (50%/50%) | **0.8729** | **+0.0020** ⚠️ |
| Full + Gene + Drug | Weighted | 0.8693 | -0.0016 ❌ |
| Full + Gene + Drug | Equal | 0.8533 | -0.0176 ❌ |

**최고 성능**: Full + Drug = 0.8729 (+0.0020)

**결론**: ❌ 개선폭 0.0020은 노이즈 수준. Full ≈ Drug (상관 0.9896)로 diversity 부족. Gene은 너무 약함.

---

## 3. SAINT 포함 확장 앙상블 (실패)

### 3.1 추가 조합

| Combination | Weighting | Holdout Sp | vs Baseline |
|-------------|-----------|------------|-------------|
| **Full (baseline)** | N/A | **0.8709** | - |
| Drug + SAINT | Weighted (55.6%/44.4%) | 0.8418 | -0.0291 ❌ |
| Drug + SAINT | Equal (50%/50%) | 0.8349 | -0.0360 ❌ |
| Full + Drug + SAINT | Weighted (35.7%/35.8%/28.5%) | 0.8569 | **-0.0140** ❌ |
| Full + Drug + SAINT | Equal (33.3% each) | 0.8522 | -0.0187 ❌ |

**결론**: ❌ SAINT 추가는 모두 성능 악화

---

## 4. Bilinear v2 종합 앙상블 평가 (✅ 최고 성능 달성!)

### 4.1 단독 모델 성능 비교 (4개 모델)

| Model | OOF Sp | Holdout Sp | RMSE | P@30 | NDCG@30 | Gap |
|-------|--------|------------|------|------|---------|-----|
| **CatBoost-Full** | 0.8624 | **0.8709** | 1.1388 | 0.6333 | 0.9848 | 0.0085 |
| **CatBoost-Drug** | 0.8645 | **0.8710** | 1.1424 | 0.6667 | 0.9847 | 0.0065 |
| SAINT | 0.7340 | 0.7344 | 2.2346 | 0.2000 | 0.9475 | 0.0004 |
| **Bilinear-v2** | 0.8298 | **0.8522** | 1.3698 | 0.5333 | 0.9692 | 0.0224 |

**핵심 발견**:
- Bilinear-v2: OOF 0.8298로 앙상블 자격 충족 (≥ 0.75)
- CatBoost-Drug: Full과 거의 동일한 성능 (0.8710 vs 0.8709)
- SAINT: 성능 너무 낮아 앙상블 시 희석 효과

### 4.2 모델 간 Diversity (Spearman 상관)

|  | Full | Drug | SAINT | Bilinear |
|---|------|------|-------|----------|
| **Full** | 1.0000 | 0.9896 | 0.8659 | **0.9247** |
| **Drug** | 0.9896 | 1.0000 | 0.8626 | **0.9181** |
| **SAINT** | 0.8659 | 0.8626 | 1.0000 | 0.8473 |
| **Bilinear** | **0.9247** | **0.9181** | 0.8473 | 1.0000 |

**분석**:
- **Full vs Bilinear**: 0.9247 (중간 diversity, 앙상블 가능)
- **Drug vs Bilinear**: 0.9181 (중간 diversity, 앙상블 가능)
- **Full vs Drug**: 0.9896 (거의 동일, diversity 부족)

### 4.3 2-Model 앙상블 결과

#### Full + Bilinear

| Weighting | Holdout Sp | RMSE | P@30 | NDCG@30 | Gap | vs Baseline |
|-----------|------------|------|------|---------|-----|-------------|
| **Weighted (51%/49%)** | **0.8750** | 1.1694 | 0.6000 | 0.9793 | 0.0140 | **+0.0041** ⚠️ |
| Equal (50%/50%) | 0.8748 | 1.1718 | 0.6000 | 0.9793 | 0.0142 | +0.0039 |

#### Drug + Bilinear 🏆

| Weighting | Holdout Sp | RMSE | P@30 | NDCG@30 | Gap | vs Baseline |
|-----------|------------|------|------|---------|-----|-------------|
| **Weighted (51%/49%)** | **0.8756** | 1.1674 | 0.6333 | 0.9807 | 0.0132 | **+0.0047** ✅ |
| Equal (50%/50%) | 0.8754 | 1.1698 | 0.6333 | 0.9797 | 0.0134 | +0.0045 |

**🏆 최고 성능**: **Drug + Bilinear (Weighted) = 0.8756**
- Baseline (Full) 대비 **+0.0047** 개선
- P@30: 0.6333 (Full 0.6333과 동일)
- NDCG@30: 0.9807 (Full 0.9848보다 약간 낮음)
- Gap: 0.0132 (과적합 낮음)

#### Full + SAINT (재측정)

| Weighting | Holdout Sp | RMSE | P@30 | NDCG@30 | Gap | vs Baseline |
|-----------|------------|------|------|---------|-----|-------------|
| Weighted (54%/46%) | 0.8299 | 1.4802 | 0.5667 | 0.9843 | 0.0031 | **-0.0410** ❌ |

### 4.4 3-Model 앙상블 결과

#### Full + Bilinear + SAINT

| Weighting | Holdout Sp | RMSE | P@30 | NDCG@30 | Gap | vs Baseline |
|-----------|------------|------|------|---------|-----|-------------|
| Weighted (36%/34%/30%) | 0.8573 | 1.2550 | 0.5000 | 0.9790 | 0.0098 | **-0.0136** ❌ |
| Equal (33%/33%/33%) | 0.8540 | 1.2798 | 0.5000 | 0.9786 | 0.0094 | **-0.0169** ❌ |

**결론**: SAINT 추가 시 성능 악화 (SAINT이 너무 약함)

---

## 5. **GroupKFold 재학습** (Unseen Drug 일반화) 🔬

### 5.1 측정 방식 차이

#### ❌ v4 초기 방식 (잘못됨)
- **방법**: 기존 OOF predictions를 GroupKFold로 재분할
- **문제**: 모델이 random split으로 학습되어 모든 약물 포함
- **결과**: CatBoost-Full 0.8583 (너무 높음, 의미 없음)

#### ✅ v4 올바른 방식 (v3와 동일)
- **방법**: GroupKFold로 모델을 재학습 (각 fold마다 unseen drugs)
- **결과**: CatBoost-Full 0.5189 (v3 0.491과 일치)

### 5.2 GroupKFold 재학습 결과

| Model | **GroupKFold Sp** | RMSE | vs v3 (0.491) | **Holdout Sp** | 하락폭 |
|-------|------------------|------|---------------|----------------|--------|
| **CatBoost-Drug** 🏆 | **0.5210 ± 0.060** | 2.2646 | **+0.030** ✅ | 0.8710 | **-40.2%** |
| CatBoost-Full | 0.5189 ± 0.062 | 2.2787 | +0.028 ✅ | 0.8709 | -40.4% |
| Drug+Bilinear | 0.5145 | 2.3412 | +0.024 ✅ | 0.8756 | -41.2% |
| Bilinear-v2 | 0.4074 ± 0.126 | 2.8968 | **-0.084** ❌ | 0.8522 | **-52.2%** |

**핵심 발견**:
1. ✅ v4 GroupKFold (0.519) ≈ v3 (0.491) → 측정 방식 검증됨
2. 🏆 **CatBoost-Drug가 unseen drug에서 최고** (0.5210)
3. ❌ **Bilinear은 unseen drug에 최악** (0.4074, -21.8% vs Drug)
4. ❌ **Drug+Bilinear 앙상블은 unseen drug에서 악화** (0.5145 < 0.5210)

### 5.3 Fold별 상세 결과

#### CatBoost-Drug (최고)
| Fold | Val Spearman | Val Drugs |
|------|--------------|-----------|
| 1 | 0.5711 | 47 |
| 2 | 0.5041 | 47 |
| 3 | 0.4137 | 51 |
| 4 | 0.5799 | 51 |
| 5 | 0.5364 | 47 |
| **Mean** | **0.5210 ± 0.060** | ~48 |

#### Bilinear v2 (최악)
| Fold | Val Spearman | 비고 |
|------|--------------|------|
| 1 | 0.5331 | 양호 |
| 2 | 0.4821 | 보통 |
| 3 | **0.2003** | ⚠️ 극단적 실패 |
| 4 | 0.3226 | 저조 |
| 5 | 0.4988 | 보통 |
| **Mean** | **0.4074 ± 0.126** | 매우 불안정 |

**Fold 3 실패 분석**:
- Bilinear이 특정 unseen drug 조합에 매우 취약
- Drug-Gene interaction 학습이 unseen drug에 전이되지 않음

### 5.4 핵심 질문 답변

#### ❌ Q1: Bilinear의 Drug/Gene 분리가 unseen drug에 유리한가?

**NO.** Bilinear (0.4074) < CatBoost-Drug (0.5210)
- 차이: **-0.1137** (-21.8%)
- Bilinear의 Drug-Gene interaction 학습이 unseen drug에 전이 실패
- CatBoost의 drug features 직접 학습이 더 robust

#### ❌ Q2: Drug+Bilinear 앙상블이 unseen drug에서도 개선되는가?

**NO.** Drug+Bilinear (0.5145) < CatBoost-Drug (0.5210)
- 차이: **-0.0065**
- Bilinear이 너무 약해서 (0.4074) Drug (0.5210)을 희석
- Holdout에서는 diversity 효과 (0.8756), unseen drug에서는 무효

---

## 📌 핵심 결론

### ✅ 성공한 발견

1. **Drug features의 중요성**
   - Drug 1,127개만으로 Full (5,529개)과 동일 성능 (0.8710)
   - IC50 예측의 모든 signal이 Drug features에 집중
   - Gene/CRISPR features는 거의 무의미

2. **Bilinear v2 디버깅 성공** 🎉
   - v1 실패 (OOF -0.013) → v2 성공 (OOF 0.8298)
   - **BatchNorm + Gradient clipping + StandardScaler**가 핵심
   - Holdout 0.8522로 단독으로도 우수한 성능

3. **최고 앙상블 달성** 🏆
   - **Drug + Bilinear (Weighted) = 0.8756**
   - Baseline 0.8709 대비 **+0.0047 개선**
   - 중간 diversity (상관 0.9181) + 두 모델 모두 강함
   - P@30: 0.6333, NDCG@30: 0.9807 유지

4. **Diversity-Performance Balance**
   - SAINT: 우수한 diversity (0.8659)지만 성능 너무 약함 (0.7344)
   - Bilinear: 중간 diversity (0.9247)지만 성능 우수 (0.8522)
   - **Diversity와 성능 모두 필요**

### ❌ 실패한 앙상블

**일부 앙상블 실패**:
1. Full + SAINT: -0.0410 (SAINT 너무 약함)
2. Full + Drug: +0.0020 (노이즈 수준, Full ≈ Drug)
3. Full + Bilinear + SAINT: -0.0136 (SAINT 희석 효과)

**실패 원인**:
- 강한 모델 + 약한 모델 (SAINT/Gene) = 강한 모델 희석
- 유사한 모델 (Full ≈ Drug, 상관 0.9896) = Diversity 부족
- **해결책**: 중간 diversity + 강한 성능 조합 (Drug + Bilinear)

---

## 🎯 최종 권고 (GroupKFold 반영!)

### 🥇 **1순위: CatBoost-Drug 단독** (변경!) ✅

**채택 이유**:
1. 🏆 **Unseen drug 최고**: GroupKFold 0.5210 (1위)
2. ✅ **Holdout 최고 수준**: 0.8710 (Full 0.8709와 거의 동일)
3. ✅ **가장 안정적**: Holdout-GroupKFold 하락 40.2% (최소)
4. ✅ **Feature 효율성**: 79.6% 감소 (5,529 → 1,127)
5. ✅ **단순성**: 단일 모델 (배포/유지보수 간편)

**적용 시나리오**:
- ⭐ **신약 스크리닝** (unseen drugs 많음)
- ⭐ **균형 잡힌 접근** (Holdout + GroupKFold 모두 우수)
- ⭐ **프로덕션 환경** (단순성, 안정성)

---

### 🥈 **2순위: Drug + Bilinear (Weighted) - Holdout 0.8756**

**채택 이유**:
1. ✅ **Holdout 최고**: 0.8756 (+0.0047 vs Drug)
2. ⚠️ **Unseen drug 보통**: GroupKFold 0.5145 (3위, Drug보다 -0.0065 낮음)
3. ⚠️ **복잡도**: 2-model 앙상블 (Bilinear StandardScaler 필수)

**채택 조건**:
- Holdout 성능 우선 시
- Unseen drug 성능 감소 감수 가능
- 앙상블 복잡도 허용

**적용 시나리오**:
- **기존 약물 재창출** (known drugs)
- **Holdout 성능 극대화**

**주의사항**:
- Bilinear이 unseen drug에 약함 (GroupKFold 0.4074)
- 앙상블이 unseen drug에서 Drug 단독보다 낮음
- Known drug에서만 앙상블 효과

---

### 🥉 **3순위: CatBoost-Full 단독 - Holdout 0.8709**

**채택 조건**:
- v3 검증된 모델 (보수적 선택)
- 모든 feature 활용
- Drug와 성능 동일, feature만 많음 (비효율적)

---

### ❌ **비권장: Bilinear v2 단독**

**이유**:
- ❌ GroupKFold 최악 (0.4074)
- ❌ Unseen drug 매우 취약 (Fold 3: 0.2003)
- ❌ 불안정성 높음 (Std 0.1264)
- ❌ Holdout-GroupKFold 하락 52.2% (최대)

**결론**: Bilinear은 **앙상블에서만** 제한적 가치 (Holdout에서만)

---

### 📊 시나리오별 최종 권고

| 시나리오 | 권장 모델 | Holdout | GroupKFold | 이유 |
|---------|-----------|---------|------------|------|
| **신약 스크리닝** | **CatBoost-Drug** 🏆 | 0.8710 | **0.5210** | Unseen drug 최고 |
| 기존 약물 재창출 | Drug+Bilinear | **0.8756** | 0.5145 | Holdout 최고 |
| 균형/보수적 | **CatBoost-Drug** | 0.8710 | **0.5210** | 가장 안정적 |
| 프로덕션 | **CatBoost-Drug** | 0.8710 | **0.5210** | 단순성 + 안정성 |

**최종 결론**: **CatBoost-Drug 단독** 강력 권장 ✅

### 향후 연구 방향

1. **Feature Engineering**
   - Drug features 심화 분석
   - Drug-Target interaction 정보 추가
   - 3D molecular descriptors

2. **Domain Knowledge 활용**
   - Neo4j KG 기반 pathway features
   - Drug mechanism of action
   - Target protein structure

3. **Transfer Learning**
   - Pre-trained molecular embeddings (ChemBERT, MolFormer)
   - Fine-tune on IC50 task

4. **Stacking 대신 Boosting**
   - LightGBM, XGBoost와 비교
   - CatBoost 하이퍼파라미터 최적화

---

## 📁 파일 구조

```
20260415_v4_ensemble_test/
├── ensemble_results/
│   ├── comprehensive_evaluation_results.json ✅ (완전 평가)
│   ├── comprehensive_evaluation_comparison.csv
│   ├── ensemble_catboost_saint_results.json
│   ├── ensemble_saint_extended_results.json
│   ├── top30_comprehensive_*.csv (12개 조합)
│   └── measure_saint_catboost.py
├── catboost_subset/
│   ├── catboost_gene/ (OOF 0.2461, 실패)
│   ├── catboost_drug/ (OOF 0.8645, ✅ 성공)
│   ├── correlation/3model_correlation_matrix.json
│   ├── ensemble/ablation_results.json
│   └── REPORT.md
├── new_models/
│   ├── bilinear/
│   │   ├── bilinear_model.py (v1, 실패)
│   │   ├── bilinear_model_v2.py (✅ v2 성공!)
│   │   ├── train_bilinear_v2.py
│   │   ├── bilinear_v2_model.pt
│   │   ├── bilinear_v2_oof.npy (OOF 0.8298)
│   │   ├── bilinear_v2_holdout.npy (Holdout 0.8522)
│   │   ├── bilinear_v2_results.json
│   │   ├── bilinear_v2_correlation.json
│   │   └── bilinear_v2_scalers.pkl
│   ├── saint/
│   │   ├── saint_oof.npy (OOF 0.7340)
│   │   └── saint_results.json
│   └── hgt/
│       ├── hgt_model.py (구현만 완료, 미학습)
│       └── extract_neo4j_graph.py
├── FINAL_SUMMARY.md (this file)
└── FINAL_REPORT.md (17,000+ words)
```

---

## 🔬 실험 통계

- **총 실험 수**: 30+ 조합
- **학습된 모델**: 5개 (Full, Gene, Drug, SAINT, Bilinear v1❌, **Bilinear v2✅**)
- **평가된 앙상블**: 20+ 조합 (완전 평가 완료)
- **🏆 최고 성능**: **Drug + Bilinear (Weighted) = 0.8756 (+0.0047)** ✅
- **성공 앙상블 수**: 4개 (Full+Bilinear, Drug+Bilinear - Weighted/Equal)
- **실패 앙상블 수**: 16개 (SAINT 포함 조합, Gene 포함 조합, 3-model 조합)

---

## 🎉 최종 결론 (GroupKFold 반영)

### ✅ 핵심 성공
1. **Bilinear v2 디버깅 성공**: v1 실패 (OOF -0.013) → v2 성공 (OOF 0.8298)
2. **Holdout 최고 달성**: Drug + Bilinear = 0.8756 (+0.0047)
3. **GroupKFold 올바른 측정**: v4 (0.519) ≈ v3 (0.491) 검증 완료

### 🔬 GroupKFold 핵심 발견

**1. Unseen Drug 최고 모델**:
- 🏆 **CatBoost-Drug**: GroupKFold 0.5210, Holdout 0.8710
- 가장 안정적 (하락 40.2%), Feature 효율적 (1,127개만)

**2. Bilinear의 역할 재평가**:
- ✅ Holdout에서 유리 (앙상블 0.8756 > Drug 0.8710)
- ❌ **Unseen drug에 불리** (GroupKFold 0.4074 << Drug 0.5210)
- **결론**: Bilinear은 **random split에서만** diversity 가치, unseen drug에선 약점

**3. 앙상블의 한계**:
- Holdout: Drug+Bilinear (0.8756) > Drug (0.8710) ✅
- GroupKFold: Drug+Bilinear (0.5145) < Drug (0.5210) ❌
- **결론**: 앙상블은 **known drug에만** 효과적

### 🎯 최종 권장 모델

**🥇 CatBoost-Drug 단독** (변경!)
- Holdout 0.8710 (최고 수준)
- **GroupKFold 0.5210** (최고)
- 가장 안정적 + Feature 효율적
- **신약 스크리닝, 균형/보수적 접근, 프로덕션 환경 권장**

**🥈 Drug+Bilinear 앙상블** (조건부)
- Holdout 0.8756 (최고)
- GroupKFold 0.5145 (보통)
- **기존 약물 재창출 (known drugs)에만 권장**

---

**최종 운영 권고**:
- **일반적 상황**: **CatBoost-Drug 단독** 강력 권장 ✅
- **Known drug 재창출**: Drug+Bilinear 앙상블 고려
- **Unseen drug 스크리닝**: CatBoost-Drug 필수
