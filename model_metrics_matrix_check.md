# 15개 모델 × 32개 지표 매트릭스 점검

**생성일:** 2026-04-14
**버전:** v3 기준

---

## 1. 32개 측정 지표 전체 목록

### 📈 예측 성능 (8개)
| No | 지표 | 설명 | 용도 |
|----|------|------|------|
| 1 | **Spearman** | 순위 상관 | 핵심 지표 |
| 2 | **Kendall tau** | 보수적 순위 상관 (동점 처리) | Spearman 보완 |
| 3 | **Pearson** | 선형 상관 | 선형 관계 확인 |
| 4 | **R²** | 설명력 (전체 분산 중 모델 설명 비율) | 전반적 적합도 |
| 5 | **RMSE** | 예측 오차 크기 | 핵심 지표 |
| 6 | **MAE** | 절대 오차 평균 | 이상치 덜 민감 |
| 7 | **MedianAE** | 절대 오차 중앙값 | 대부분 예측의 실제 정확도 |
| 8 | **P95 absolute error** | 최악 5% 오차 크기 | 꼬리 위험(tail risk) |

### 🔍 과적합 진단 (5개)
| No | 지표 | 설명 |
|----|------|------|
| 9 | **Train Spearman** | 학습 데이터 성능 |
| 10 | **OOF Spearman** | Out-of-Fold 전체 예측 성능 |
| 11 | **Gap (Train - OOF)** | 과적합 정도 |
| 12 | **Train/Val Ratio** | 과적합 비율 |
| 13 | **Fold별 Spearman std** | fold 간 성능 안정성 |

### 🎯 일반화 (Split별 6종 = 12개)
| No | Split | 기준 | 목적 | 주요 지표 |
|----|-------|------|------|----------|
| 14-15 | **Random 5CV** | 무작위 | 기본 평균 성능 | Spearman, RMSE |
| 16-17 | **Holdout** | 무작위 test | 최종 성능 | Spearman, RMSE |
| 18-19 | **GroupKFold (Drug)** | canonical_drug_id | 새 약물 일반화 | Spearman, RMSE |
| 20-21 | **Unseen Drug** | 약물 완전 분리 | 실제 배치 일반화 | Spearman, top-k recall |
| 22-23 | **Scaffold Split** | scaffold 완전 분리 | 구조 일반화 | Spearman, RMSE |
| 24-25 | **Stability (multi-seed)** | seed 변경 | 재현성 | mean±std, top-k overlap |

### 🔄 앙상블 품질 (4개)
| No | 지표 | 설명 |
|----|------|------|
| 26 | **앙상블 > 개별 Best** | 앙상블 의미 여부 |
| 27 | **앙상블 Gap** | 앙상블 과적합 |
| 28 | **가중치 분포** | 특정 모델 쏠림 여부 |
| 29 | **모델 간 예측 상관 (diversity)** | 상관 높으면 앙상블 효과 없음 |

### 🏆 약물 랭킹 품질 (7개)
| No | 지표 | 설명 |
|----|------|------|
| 30 | **Precision@30** | Top 30 중 실제 활성 약물 비율 |
| 31 | **NDCG@30** | 순위 품질 (상위에 좋은 약물일수록 높음) |
| 32 | **Top-30 overlap (across seeds)** | seed 변경 시 Top 30 겹침률 |

---

## 2. 15개 모델 목록 (v1/v2/v3)

### ML (8개)
1. **LightGBM**
2. **LightGBM DART**
3. **XGBoost**
4. **CatBoost**
5. **RandomForest**
6. **ExtraTrees**
7. **Stacking (Ridge)**
8. **RSF** (METABRIC 전용)

### DL (5개)
9. **ResidualMLP**
10. **FlatMLP**
11. **TabNet**
12. **FT-Transformer**
13. **Cross-Attention**

### Graph (2개)
14. **GraphSAGE** (drug-split)
15. **GAT** (drug-split)

---

## 3. 측정 현황 매트릭스

### ✅ 전체 모델 공통 측정 (14개 지표)

| 지표 | 모든 15개 모델 측정 여부 |
|------|------------------------|
| Train Spearman | ✅ |
| OOF Spearman (5CV) | ✅ |
| Gap (Train - OOF) | ✅ |
| Train RMSE | ✅ |
| OOF RMSE | ✅ |
| Holdout Spearman | ✅ (v3) |
| Holdout RMSE | ✅ (v3) |
| GroupKFold Spearman | ✅ (v3 - 6개 주요 모델) |
| Unseen Drug Spearman | ✅ (v3 - 6개 주요 모델) |
| Scaffold Spearman | ✅ (v3 - 6개 주요 모델) |
| Multi-seed mean±std | ✅ (v3 - 6개 주요 모델) |
| Top-30 overlap | ✅ (v3 - 6개 주요 모델) |
| Precision@30 | ✅ (v3) |
| NDCG@30 | ✅ (v3) |

### ⚠️ 일부 모델만 측정 (6개 주요 모델)

**v3에서 6단계 평가를 거친 모델 (6개):**
- CatBoost
- DART
- FlatMLP
- LightGBM
- CrossAttention
- FT-Transformer

**측정된 추가 지표 (6개 모델만):**
- GroupKFold Spearman
- Unseen Drug Spearman
- Scaffold Spearman
- Multi-seed Spearman (5 seeds)
- Top-30 overlap (Jaccard)
- Diversity (모델 간 예측 상관)

### ❌ 측정되지 않은 지표 (18개)

**v3 프로토콜에 명시되었으나 실제 대시보드에 없는 지표:**
1. Kendall tau
2. Pearson
3. R² (Train/OOF/Holdout)
4. MAE (Train/OOF/Holdout)
5. MedianAE
6. P95 absolute error
7. Train/Val Ratio
8. Fold별 Spearman std
9. Recall@30
10. MAP (Mean Average Precision)
11. EF@30 (Enrichment Factor)
12. Top-k overlap (across splits)

**Graph 모델 특화 지표 (측정 여부 불명확):**
- P@20 (GraphSAGE 전용)
- C-index (RSF 전용)

---

## 4. 모델별 측정 지표 매트릭스

### 🔵 Tier 1: 완전 평가 (6개 모델)

| 모델 | 기본 성능 (8) | 과적합 (5) | 일반화 (12) | 앙상블 (4) | 랭킹 (7) | **총 측정** |
|------|---------------|------------|-------------|-----------|---------|-----------|
| CatBoost | ✅ | ✅ | ✅ | ✅ | ✅ | **~20/32** |
| DART | ✅ | ✅ | ✅ | ✅ | ✅ | **~20/32** |
| FlatMLP | ✅ | ✅ | ✅ | ✅ | ✅ | **~20/32** |
| LightGBM | ✅ | ✅ | ✅ | ⚠️ | ✅ | **~18/32** |
| CrossAttention | ✅ | ✅ | ✅ | ⚠️ | ✅ | **~18/32** |
| FT-Transformer | ✅ | ✅ | ✅ | ❌ | ✅ | **~16/32** |

### 🟡 Tier 2: 기본 평가 (7개 모델)

| 모델 | 기본 성능 (8) | 과적합 (5) | 일반화 (12) | 앙상블 (4) | 랭킹 (7) | **총 측정** |
|------|---------------|------------|-------------|-----------|---------|-----------|
| XGBoost | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| RandomForest | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| ExtraTrees | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| Stacking | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| ResidualMLP | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| TabNet | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |
| GAT | ✅ | ✅ | ❌ | ❌ | ⚠️ | **~10/32** |

### 🟢 Tier 3: 특수 평가 (2개 모델)

| 모델 | 기본 성능 (8) | 과적합 (5) | 일반화 (12) | 앙상블 (4) | 랭킹 (7) | **총 측정** |
|------|---------------|------------|-------------|-----------|---------|-----------|
| RSF | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | **~6/32** |
| GraphSAGE | ⚠️ | ⚠️ | ⚠️ | ❌ | ⚠️ | **~12/32** |

---

## 5. 결론 및 권장사항

### ✅ 잘된 점
1. **핵심 6개 모델**은 거의 모든 중요 지표를 측정 (~20/32)
2. **6단계 평가 체계**로 과적합/일반화를 철저히 검증
3. **Gap 해석 가이드**로 각 단계별 의미를 명확히 정의

### ⚠️ 개선 필요
1. **나머지 9개 모델**은 일반화/앙상블 지표 미측정 (~10/32)
2. **18개 지표**는 프로토콜에 명시되었으나 실제 미측정
   - Kendall tau, Pearson, R², MAE 계열
   - MedianAE, P95 error
   - MAP, EF@30, Recall@30
3. **측정 지표 문서화** 부족 (어떤 모델에 어떤 지표가 측정되었는지 명시 필요)

### 📋 권장 조치
1. **우선순위 1**: 핵심 6개 모델의 누락 지표 보완 (Kendall, Pearson, MAE 등)
2. **우선순위 2**: 나머지 9개 모델의 일반화 평가 (GroupKFold, Unseen Drug 등)
3. **우선순위 3**: 모델별 지표 측정 현황 CSV 생성
   - `model_metrics_coverage.csv` (15 rows × 32 columns, ✅/❌ 표시)

### 📊 현재 측정률
- **Tier 1 (6개 모델)**: 평균 **62.5%** (20/32)
- **Tier 2 (7개 모델)**: 평균 **31.3%** (10/32)
- **Tier 3 (2개 모델)**: 평균 **28.1%** (9/32)
- **전체 평균**: 약 **40.6%** (13/32)

---

**다음 단계:**
1. 누락 지표 측정 스크립트 작성
2. 전체 15개 모델 × 32개 지표 완전 매트릭스 생성
3. 대시보드에 지표 커버리지 시각화 추가
