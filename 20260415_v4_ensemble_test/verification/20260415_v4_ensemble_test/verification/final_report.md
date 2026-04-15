# Step 4.5-A 최종 검증 보고서

**검증 일시:** 2026-04-15
**프로토콜:** v4.0
**검증 대상:** FlatMLP (model_10) vs CrossAttention (model_13)

---

## 📊 핵심 결과 요약

### 1. 예측값 상관 분석

| 지표 | 값 | 프로토콜 기준 | 판정 |
|------|-----|--------------|------|
| Pearson correlation | **0.9895** | - | 매우 높음 |
| Spearman correlation | **0.9848** | ≥ 0.98 → Case 2 | ✅ **Case 2 해당** |
| Max absolute diff | 1.1210 | - | 차이 존재 |
| Mean absolute diff | 0.2777 | - | 평균 0.28 차이 |
| Top-30 Jaccard | **0.3953** | 0.2~0.6 목표 | ⚠️ 낮은 편 |
| Top-50 Jaccard | **0.5385** | - | 보통 |

**해석:**
- Spearman 0.9848 → 순위가 거의 동일 (구조적 중복)
- 하지만 v3 보고 "1.000"보다는 낮음 (완전 동일은 아님)
- Top-30 overlap 40% → 상위 약물 중 절반 정도만 겹침

---

### 2. 파일 및 Weight 검증

#### OOF Prediction 파일:
| 항목 | FlatMLP | CrossAttention | 비교 |
|------|---------|----------------|------|
| 파일명 | model_10_oof.npy | model_13_oof.npy | ✅ 분리됨 |
| 파일 크기 | 40,864 bytes | 40,864 bytes | ⚠️ 동일 (정상) |
| 수정 시간 | 2026-04-14 00:40:40 | 2026-04-14 00:41:10 | ✅ 30초 차이 |
| Shape | (5092,) | (5092,) | ✅ 동일 row 수 |

#### Weight 파일:
| 항목 | FlatMLP | CrossAttention | 비교 |
|------|---------|----------------|------|
| 파일명 | model_10_model.pt | model_13_model.pt | ✅ 분리됨 |
| **파일 크기** | **5.7 MB** | **5.7 MB** | ⚠️ **동일 (의심)** |
| 수정 시간 | 2026-04-14 00:40 | 2026-04-14 00:41 | ✅ 1분 차이 |

**⚠️ WARNING:**
- **Weight 파일 크기가 완전히 동일 (5.7 MB)**
- CrossAttention은 Attention layer가 있어서 FlatMLP보다 커야 정상
- 구조적으로 의심스러운 상황

---

### 3. JSON 메타데이터

#### FlatMLP (model_10):
```json
{
  "model": "FlatMLP",
  "device": "mps",
  "oof_spearman": 0.8458,
  "oof_rmse": 1.2006,
  "holdout_spearman": 0.8871,
  "holdout_rmse": 1.1069,
  "ensemble_pass": true
}
```

#### CrossAttention (model_13):
```json
{
  "model": "CrossAttention",
  "device": "mps",
  "oof_spearman": 0.8005,
  "oof_rmse": 1.3751,
  "holdout_spearman": 0.8593,
  "holdout_rmse": 1.4652,
  "ensemble_pass": true
}
```

**관찰:**
- OOF Spearman이 다름 (0.8458 vs 0.8005)
- 하지만 fold별 loss나 학습 curve 정보 없음
- Weight 파일 경로 정보 없음

---

## 🔍 버그 vs 구조적 중복 분석

### 버그 가능성: **중간**

| 체크 항목 | 상태 | 비고 |
|----------|------|------|
| 파일 경로 분리 | ✅ 정상 | model_10 vs model_13 |
| 파일 수정 시간 | ✅ 정상 | 30초~1분 차이 |
| JSON 메타데이터 | ✅ 다름 | OOF Spearman 다름 |
| **Weight 크기** | ⚠️ **의심** | **5.7MB로 동일 (비정상)** |
| 학습 로그 | ❓ 확인 불가 | JSON에 저장 안 됨 |
| Prediction 덮어쓰기 | ✅ 없음 | 파일 분리 확인 |

### 구조적 중복 가능성: **높음**

| 요인 | 상태 | 비고 |
|------|------|------|
| 같은 feature set | ✅ 동일 | 5,534개 전부 사용 |
| 같은 전처리 | ✅ 동일 | 같은 X_train.npy |
| 같은 학습 설정 | ✅ 유사 | seed=42, 5-fold CV |
| **순위 상관 0.98** | ⚠️ **문제** | **Diversity 부족** |
| Weight 크기 동일 | ⚠️ **의심** | 구조가 다른데 크기 동일 |

---

## 🎯 분기 판단

### 최종 판정: **Case 2 - 구조적 중복 가능성**

**근거:**
1. Spearman correlation **0.9848 ≥ 0.98** (프로토콜 기준 충족)
2. Weight 파일 크기가 동일 (의심스러움)
3. 같은 feature set 사용으로 인한 구조적 유사성
4. Top-30 overlap 40% (완전 중복은 아니지만 높음)

**하지만 주의:**
- 완전 동일(1.000)은 아님
- 절대값 차이 존재 (mean 0.28)
- 두 모델이 실제로 다르게 학습되었을 가능성

---

## 📋 다음 단계: Step 4.5-B 분리 실험

### 권장 전략: Feature Subset 분리 (전략 1)

**FlatMLP:**
- 현재 유지: 5,534개 feature 전부 사용
- 역할: Dense pattern 학습

**CrossAttention:**
- **Feature Subset으로 제한:**
  - Drug 관련만: Morgan FP + LINCS + Target + Pathway + Drug desc
  - 예상 개수: ~1,112개
- 역할: "관계 학습" 전문화

**목표:**
- Prediction correlation < 0.95
- Top-30 overlap: 0.2~0.6
- 개별 OOF Spearman 유지 또는 향상

---

## 🔧 추가 조사 필요 사항

### 우선순위 1: Weight 파일 크기 동일 원인
- [ ] model_10_model.pt와 model_13_model.pt를 로드해서 구조 비교
- [ ] Layer 수, Parameter 수 확인
- [ ] 실제로 다른 모델인지 검증

### 우선순위 2: 학습 과정 재확인
- [ ] retrain_gpu_models.py 실행 로그 확인
- [ ] 두 모델이 실제로 별도로 학습되었는지
- [ ] Early stopping epoch이 동일했는지

### 우선순위 3 (선택): 재학습 테스트
- [ ] 다른 seed로 재학습 시 상관 변화 확인
- [ ] Feature subset 일부만 사용해서 재학습

---

## 📊 프로토콜 v3 vs v4 비교

| 항목 | v3 보고 | v4 검증 결과 | 차이 |
|------|---------|-------------|------|
| FlatMLP-CrossAttn 상관 | 1.000 | **0.9848** | ▼ 0.015 |
| 판정 | 완전 중복 | 구조적 중복 | 약간 완화 |
| Top-30 overlap | (미확인) | 40% | - |

**해석:**
- v3 "1.000"은 과장되었을 가능성
- 하지만 0.9848도 여전히 Diversity 부족
- **분리 실험은 여전히 필요**

---

## ✅ QC 체크리스트

### Step 4.5-A 완료 항목:

- [x] FlatMLP OOF prediction 파일 경로 확인
- [x] CrossAttention OOF prediction 파일 경로 확인
- [x] 두 파일이 다른 파일인지 확인 (경로·크기·수정일시)
- [x] row alignment 확인 (5,092 samples 동일)
- [x] 6개 비교 지표 측정 완료
  - [x] Pearson correlation: 0.9895
  - [x] Spearman correlation: 0.9848
  - [x] Max absolute diff: 1.12
  - [x] Mean absolute diff: 0.28
  - [x] Top-30 Jaccard: 0.40
  - [x] Top-50 Jaccard: 0.54
- [x] 학습 로그 확인 시도 (JSON에 저장 안 됨)
- [x] Weight 파일 분리 확인
- [x] Weight 파일 크기 비교 (⚠️ 동일 - 의심)
- [x] 분기 판단 결과 기록: **Case 2**
- [x] 다음 단계 결정: **Step 4.5-B 분리 실험**

---

## 📁 결과 파일

```
20260415_v4_ensemble_test/verification/
├── verify_overlap.py              # 검증 스크립트
├── verification_results.json       # 수치 결과
├── verification_summary.md         # 요약 보고서
└── final_report.md                 # 이 문서
```

---

## 🎯 최종 결론

1. **FlatMLP과 CrossAttention의 예측 상관 0.9848**
   - "완전 동일"은 아니지만 "충분히 다름"도 아님
   - Diversity 개선 필요

2. **Weight 파일 크기가 동일 (5.7 MB)**
   - 의심스러운 상황
   - 추가 조사 필요

3. **분기 판단: Case 2 - 구조적 중복**
   - Step 4.5-B 분리 실험 진행
   - Feature Subset 전략 추천

4. **Diversity 목표: < 0.90**
   - 현재 0.9848 → 목표 0.90 미만
   - 분리 실험으로 달성 가능

---

**검증 완료 일시:** 2026-04-15
**다음 단계:** Step 4.5-B Feature Subset 분리 실험
**책임자:** Claude Code v4.0
