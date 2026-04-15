# Step 4.5-A 검증 결과 요약

**검증 일시:** 2026-04-15
**대상 모델:** FlatMLP (model_10) vs CrossAttention (model_13)
**데이터:** OOF predictions (5,092 samples)

---

## 1. 파일 메타데이터 비교

| 항목 | FlatMLP | CrossAttention |
|------|---------|----------------|
| **파일 경로** | model_10_oof.npy | model_13_oof.npy |
| **파일 크기** | 40,864 bytes | 40,864 bytes |
| **수정 일시** | 2026-04-14 00:40:40 | 2026-04-14 00:41:10 |
| **Shape** | (5092,) | (5092,) |
| **Dtype** | float64 | float64 |

**관찰:**
- 두 파일 크기가 정확히 동일 (40,864 bytes)
- 수정 시간이 30초 차이로 매우 근접
- 같은 row 수이므로 파일 크기 동일은 정상

---

## 2. 예측값 비교 지표 (6개)

| 지표 | 값 | 해석 |
|------|-----|------|
| **Pearson correlation** | 0.9895 | 매우 높은 선형 상관 |
| **Spearman correlation** | **0.9848** | **매우 높은 순위 상관 (≥ 0.98)** |
| **Max absolute diff** | 1.1210 | 예측값 차이는 존재 |
| **Mean absolute diff** | 0.2777 | 평균적으로 0.28 차이 |
| **Top-30 Jaccard** | 0.3953 | 17/30 일치 (57%) |
| **Top-50 Jaccard** | 0.5385 | 35/50 일치 (70%) |

**핵심 발견:**
1. **순위 상관 0.9848** → 두 모델이 예측하는 약물 순위가 거의 동일
2. **절대값 차이는 존재** → 완전히 동일한 예측값은 아님
3. **Top-30 overlap 57%** → 상위 약물 중 절반 이상 겹침

---

## 3. 프로토콜 기준과 비교

### 프로토콜 v4.0 기준:
- v3에서 FlatMLP-CrossAttention 상관 **1.000** (완전 중복) 보고됨
- 이번 검증 결과: Spearman **0.9848**

### 차이점:
- **완전 동일(1.000)은 아님**
- 하지만 **0.9848은 여전히 매우 높음** (Diversity 부족)
- v3 문제였던 CatBoost-DART (0.990)보다는 낮지만 여전히 문제

---

## 4. 학습 로그 및 Weight 파일 검증

### JSON 메타데이터:
```json
FlatMLP (model_10):
{
  "oof_spearman": 0.8458,
  "holdout_spearman": 0.8871,
  "oof_rmse": 1.2006,
  "holdout_rmse": 1.1069
}

CrossAttention (model_13):
{
  "oof_spearman": 0.8005,
  "holdout_spearman": 0.8593,
  "oof_rmse": 1.3751,
  "holdout_rmse": 1.4652
}
```

**관찰:**
- 두 모델의 OOF Spearman이 다름 (0.8458 vs 0.8005)
- 하지만 이 값은 검증 스크립트에서 계산한 예측값의 상관과는 다른 지표
- JSON에 fold별 loss나 weight 경로 정보 없음

### Weight 파일:
- step4_results/에 .pt 파일 27개 존재
- FlatMLP/CrossAttention 특정 weight 파일 확인 필요

---

## 5. 분기 판단: **Case 2 - 구조적 중복 가능성**

### 판단 근거:
- Spearman correlation **0.9848 ≥ 0.98**
- 프로토콜 기준 Case 2에 해당

### 다음 단계:
**→ Step 4.5-B 경량 분리 실험 진행**

---

## 6. 버그 가능성 vs 구조적 중복 가능성

### 버그 가능성: **낮음**
- [x] 두 파일이 물리적으로 다름 (수정 시간 30초 차이)
- [x] 파일 경로가 분리되어 있음
- [x] JSON 메타데이터가 다름 (OOF Spearman 0.8458 vs 0.8005)
- [ ] 학습 로그 확인 불가 (JSON에 저장 안 됨)
- [ ] Weight 파일 크기 비교 필요

### 구조적 중복 가능성: **높음**
- [x] 예측값 순위 상관 0.9848 (매우 높음)
- [x] Top-30 overlap 57%
- [x] 두 모델 모두 같은 feature set 사용 (5,534개)
- [x] 같은 전처리 파이프라인 사용
- [?] 학습 설정이 유사할 가능성

---

## 7. 권장 사항

### 즉시 실행:
1. **Step 4.5-B 분리 실험** 진행
   - 전략 1: Feature Subset 분리 (추천)
   - CrossAttention에 Drug 관련 feature만 사용 (1,112개)
   - 목표: correlation < 0.95, Top-30 overlap < 0.6

2. Weight 파일 크기 확인
   - CrossAttention이 Attention layer로 인해 더 커야 정상

### 장기 개선:
3. 학습 로그 저장 체계 개선
   - Fold별 loss curve 저장
   - Early stopping epoch 기록
   - Weight 파일 경로 명시

---

## 8. 결론

**FlatMLP과 CrossAttention의 예측 상관 0.9848은:**
- "완전 동일(1.000)"은 아니지만
- "충분히 다름(<0.95)"도 아님
- **Diversity 개선이 필요한 수준**

**→ Step 4.5-B 분리 실험을 통해 상관을 0.95 미만으로 낮춰야 함**

---

**검증 완료 일시:** 2026-04-15
**결과 저장 위치:** `20260415_v4_ensemble_test/verification/verification_results.json`
