# 32개 지표 × 15개 모델 매트릭스 완성

**생성일:** 2026-04-14
**파일:** model_metrics_32x15_matrix.csv

---

## ✅ 완료 사항

### 1. 32개 지표 전체 목록 작성
- `metrics_32_complete_list.md` 생성
- 8 + 5 + 12 + 4 + 7 = 36개 (실제 측정 기준)

### 2. 15개 모델 × 36개 지표 매트릭스 생성
- `model_metrics_32x15_matrix.csv` 생성
- 크기: 15 rows × 36 columns = 540 cells
- 측정된 값: 201 / 540 = **37.2%**

### 3. 실제 값 채움
- ✅ CatBoost: 26개 지표 측정
- ✅ DART: 25개 지표 측정
- ✅ FlatMLP: 25개 지표 측정
- ✅ LightGBM: 24개 지표 측정
- ✅ CrossAttention: 24개 지표 측정
- ✅ FT-Transformer: 24개 지표 측정
- ⚠️ XGBoost: 7개 지표 측정
- ⚠️ RandomForest: 7개 지표 측정
- ⚠️ ExtraTrees: 7개 지표 측정
- ⚠️ Stacking: 7개 지표 측정
- ⚠️ ResidualMLP: 7개 지표 측정
- ⚠️ TabNet: 7개 지표 측정
- ⚠️ RSF: 2개 지표 측정
- ⚠️ GraphSAGE: 8개 지표 측정
- ⚠️ GAT: 3개 지표 측정

---

## 📊 측정 현황

### Tier 1 (완전 평가 6개) - 평균 24.7개/36개 (68.6%)
1. CatBoost
2. DART
3. FlatMLP
4. LightGBM
5. CrossAttention
6. FT-Transformer

### Tier 2 (기본 평가 7개) - 평균 7개/36개 (19.4%)
7. XGBoost
8. RandomForest
9. ExtraTrees
10. Stacking
11. ResidualMLP
12. TabNet

### Tier 3 (특수 평가 2개) - 평균 5.5개/36개 (15.3%)
13. RSF (METABRIC 전용)
14. GraphSAGE (Scaffold 특화)
15. GAT (FAIL)

---

## 📋 지표별 측정률

### ✅ 100% 측정 (15/15 모델)
- OOF Spearman
- OOF RMSE

### ⭐ 80%+ 측정 (12+/15 모델)
- Train Spearman (13/15)
- Holdout Spearman (13/15)
- Train RMSE (13/15)
- Holdout RMSE (13/15)
- Gap (13/15)

### ⚠️ 40% 측정 (6/15 모델)
- GroupKFold Spearman
- Unseen Drug Spearman
- Scaffold Spearman
- Multi-seed mean/std
- Top-30 Overlap
- NDCG@30

### ❌ 0% 측정 (미구현)
- GroupKFold RMSE
- Unseen Drug RMSE
- Scaffold RMSE
- Pearson
- Kendall tau
- Recall@30
- MAP
- EF@30
- MRR

---

## 🎯 다음 단계 (선택사항)

### 우선순위 1: Tier 2 모델 일반화 평가
- XGBoost, Stacking, ResidualMLP, TabNet
- GroupKFold, Unseen Drug, Scaffold 측정
- 예상 시간: ~2시간

### 우선순위 2: 누락 지표 보완
- Pearson, Kendall tau 계산 (10분)
- RMSE 계열 보완 (20분)

### 우선순위 3: 랭킹 지표 완성
- Recall@30, MAP, EF@30, MRR
- 예상 시간: ~30분

---

## 📁 생성된 파일

1. `model_metrics_32x15_matrix.csv` - 전체 매트릭스
2. `metrics_32_complete_list.md` - 36개 지표 상세 설명
3. `metrics_matrix_summary.md` - 이 문서

**CSV 위치:**
```
/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol/model_metrics_32x15_matrix.csv
```

**측정률: 37.2% (201/540 cells)**
