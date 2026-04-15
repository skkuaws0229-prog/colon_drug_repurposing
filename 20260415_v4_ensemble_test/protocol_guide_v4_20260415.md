# Drug Discovery Pipeline Protocol Guide v4.0

**프로젝트:** 유방암(BRCA) 약물 재창출 파이프라인
**버전:** v4.0
**작성일:** 20260415
**기반:** v3.1 (20260414)
**환경:** iMac 24, Apple M4, 16GB RAM, MPS
**마감:** 5/8

---

## 변경 이력

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| v1.0 | 20260408 | 초기 프로토콜 (7개 모델, Step 1~7) |
| v2.0 | 20260410 | MultiModalFusionNet 추가, Step 8 멀티모달 허들 |
| v3.0 | 20260414 | Step 3-2.5 매칭 품질 검증, Step 3.5 Feature Selection, 6단계 평가 체계, 32개 지표, 15개 모델 |
| v3.1 | 20260414 | 앙상블 A(CatBoost+DART+FlatMLP) 확정, CatBoost 단독 채택, Step 8 제거 |
| **v4.0** | **20260415** | **앙상블 조합 변경(CatBoost+FlatMLP+CrossAttention), Step 4.5-A 동일예측 원인 검증 추가, Step 4.5-B 분리 실험+튜닝 추가, Diversity 개선** |

---

## v4.0 핵심 변경 사항 (v3.1 대비)

### 변경된 것
1. **앙상블 조합:** CatBoost+DART+FlatMLP → **CatBoost+FlatMLP+CrossAttention**
   - DART 제외: CatBoost와 예측 상관 0.990 (다양성 부족)
   - CrossAttention 추가: Unseen Drug에서 최고 성능(0.335), Attention 구조로 Tree와 차별화
2. **하이퍼파라미터 튜닝:** v3까지 기본값(default)만 사용 → **v4에서 튜닝 적용**
3. **Diversity 개선 전략:** Feature subset 분리 검토

### 유지하는 것 (v3.1 그대로)
- Step 1~4: 환경 설정, 데이터 준비, FE, 모델 학습 결과 **재사용**
- features_slim.parquet (6,366행 × 5,534컬럼) 그대로 사용
- 15개 모델 OOF 예측값 그대로 사용
- Step 6 METABRIC 외부 검증 방법
- Step 7 ADMET Gate

### 재실행 범위
- **Step 5부터 새로 시작** (앙상블 → METABRIC → ADMET)
- Step 4의 OOF 예측값, 6단계 평가 결과는 기존 것 활용
- 튜닝 후 재학습 시 Step 4 일부 재실행 가능

---

## 전체 파이프라인 흐름

```
✅ Step 1. 환경 설정                              — v3 결과 재사용
✅ Step 2. 전처리 데이터 준비                      — v3 결과 재사용
✅ Step 3. FE 실행                                — v3 결과 재사용
✅ Step 3-2.5 매칭 품질 검증                       — v3 결과 재사용
✅ Step 3.5 Feature Selection                     — v3 결과 재사용
✅ Step 4. 모델 학습 + 6단계 평가                  — v3 결과 재사용
🔄 Step 4.5-A 동일예측 원인 검증 [v4 신규 · 최우선] — FlatMLP vs CrossAttention 비교
🔄 Step 4.5-B 분리 실험 + 튜닝 [v4 신규]          — 결과에 따라 분리 후 Optuna 튜닝
🔄 Step 5. 앙상블 (CatBoost+FlatMLP+CrossAttention) — 새로 실행
🔄 Step 6. METABRIC 외부 검증 (A+B+C)             — 새로 실행
🔄 Step 7. ADMET Gate                             — 새로 실행
🔄 Step 7+. KG/API 검증·설명 자동화                — 새로 실행
```

---

## Step 4 — 기존 결과 요약 (v3.1 확정)

### v4 앙상블 대상 3개 모델 — v3 6단계 평가 결과

#### CatBoost (역할: 안정성)

| 평가단계 | Spearman | RMSE | 비고 |
|----------|----------|------|------|
| 1. Random 5CV | 0.862 | 1.259 | Train 0.936, Gap 0.074, Fold std 0.001 |
| 2. Holdout | 0.831 | 1.312 | OOF 대비 -0.031 |
| 3. GroupKFold (drug) | 0.559 | 2.306 | OOF 대비 -0.303 |
| 4. Unseen Drug | 0.353 | N/A | OOF 대비 -0.509 |
| 5. Scaffold Split | 0.358 | N/A | OOF 대비 -0.504 |
| 6. Multi-seed (5회) | 0.870±0.001 | N/A | Top-30 Overlap 0.57 (최고) |

#### FlatMLP (역할: 패턴 학습)

| 평가단계 | Spearman | RMSE | 비고 |
|----------|----------|------|------|
| 1. Random 5CV | 0.828 | 1.312 | Train 0.852, Gap 0.024, Fold std 0.005 |
| 2. Holdout | 0.806 | 1.345 | OOF 대비 -0.022 |
| 3. GroupKFold (drug) | 0.539 | 2.272 | OOF 대비 -0.289 |
| 4. Unseen Drug | 0.316 | N/A | OOF 대비 -0.512 |
| 5. Scaffold Split | 0.313 | N/A | OOF 대비 -0.515 |
| 6. Multi-seed (5회) | 0.827±0.005 | N/A | Top-30 Overlap 0.27 |

#### CrossAttention (역할: 확장성 · 새 약물 일반화)

| 평가단계 | Spearman | RMSE | 비고 |
|----------|----------|------|------|
| 1. Random 5CV | 0.824 | 1.318 | Train 0.853, Gap 0.029, Fold std 0.005 |
| 2. Holdout | 0.801 | 1.352 | OOF 대비 -0.023 |
| 3. GroupKFold (drug) | 0.542 | 2.348 | OOF 대비 -0.282 (3개 중 하락 최소) |
| 4. Unseen Drug | 0.335 | N/A | OOF 대비 -0.489 (3개 중 최고) |
| 5. Scaffold Split | 0.320 | N/A | OOF 대비 -0.504 |
| 6. Multi-seed (5회) | 0.827±0.005 | N/A | Top-30 Overlap 0.27 |

### v3 앙상블 결과 (참고 기준값)

| 항목 | v3 앙상블 A (3개) | v3 CatBoost 단독 | v1 앙상블 (6개) |
|------|-------------------|------------------|-----------------|
| OOF Spearman | 0.8668 | 0.8704 | 0.8055 |
| OOF RMSE | 1.146 | — | 1.3008 |
| Gap | — | 0.074 | 0.0004 |
| METABRIC Top15 | 12/15 일치 | 12/15 일치 | — |
| Diversity (평균 상관) | 0.962 (높음) | — | — |

---

## Step 4.5-A — 동일예측 원인 검증 [v4 신규 · 최우선]

### 배경
v3에서 FlatMLP과 CrossAttention의 예측 상관이 1.000(완전 중복)으로 나타남.
두 모델은 구조가 다르므로(MLP vs Attention), 완전 동일 예측은 비정상적.
앙상블 설계 전에 원인을 먼저 규명해야 함.

### 4.5-A-1. 검증 항목

```
1. OOF prediction 직접 비교
   - FlatMLP vs CrossAttention OOF prediction 파일 로드
   - row alignment (sample_id, canonical_drug_id 기준) 확인 후 비교
   - 측정 지표:
     · Pearson correlation
     · Spearman correlation
     · max absolute difference
     · mean absolute difference
     · Top-30 overlap (Jaccard)
     · Top-50 overlap (Jaccard)

2. 파이프라인 오류 점검
   - prediction 저장 경로가 모델별로 분리되어 있는지
   - inference 출력 경로가 겹치는지
   - evaluation 입력 경로에서 같은 파일을 읽고 있지 않은지
   - 덮어쓰기, 경로 충돌 여부 확인

3. 학습 설정 비교
   - 같은 seed 사용 여부
   - 같은 split 사용 여부
   - early stopping 기준 동일 여부
   - 전처리 산출물 공유 여부
   - 모델 가중치(weight) 파일이 실제로 다른지
```

### 4.5-A-2. 실행

```bash
# Claude Code에 전달할 지시
python verify_prediction_overlap.py \
  --pred_a step4_results/flatmlp_oof_predictions.parquet \
  --pred_b step4_results/crossattention_oof_predictions.parquet \
  --output 20260415_v4_ensemble_test/verification/

# 출력 내용:
# 1. Pearson / Spearman / max_diff / mean_diff / top30_overlap / top50_overlap
# 2. 파일 경로 · 크기 · 수정일시 비교
# 3. 학습 로그 경로 비교
```

### 4.5-A-3. 분기 판단

```
Case 1: 파일/평가 오류 발견
  → 수정 후 CrossAttention 재평가
  → 재평가 결과로 correlation 재측정
  → 결과에 따라 Step 4.5-B 진행 여부 결정

Case 2: 진짜 모델 출력이 거의 동일 (corr ≥ 0.98)
  → 구조적 중복 확인
  → Step 4.5-B 경량 분리 실험 진행

Case 3: 실제로는 다름 (corr < 0.95)
  → 이전 평가 오류였음
  → 분리 실험 불필요, 바로 Step 4.5-B 튜닝으로 진행
```

### 4.5-A-4. QC 체크

```
[ ] FlatMLP OOF prediction 파일 경로 확인
[ ] CrossAttention OOF prediction 파일 경로 확인
[ ] 두 파일이 다른 파일인지 확인 (경로 · 크기 · 수정일시)
[ ] row alignment 확인 (sample_id · canonical_drug_id 일치)
[ ] 6개 비교 지표 측정 완료
[ ] 학습 로그 · 모델 weight 파일 분리 확인
[ ] 분기 판단 결과 기록
[ ] 분기 판단에 따른 다음 단계 결정
```

---

## Step 4.5-B — 분리 실험 + 튜닝 [v4 신규]

### 4.5-B-1. 목적
- Step 4.5-A 결과에 따라 FlatMLP과 CrossAttention의 예측 중복 해소
- 중복 해소 후 3개 모델 Optuna 튜닝
- 목표: Diversity (평균 상관) < 0.90, 개별 성능 유지 또는 향상

### 4.5-B-2. 경량 분리 실험 (구조적 중복 확인 시)

> Step 4.5-A에서 Case 2 (corr ≥ 0.98)인 경우에만 실행.
> Case 1 또는 Case 3이면 이 단계를 건너뛰고 튜닝으로 직행.

**분리 전략 (우선순위 순):**

```
전략 1: Feature Subset 분리 (가장 추천)
  - FlatMLP: 현재 feature 유지 (5,534개 전체)
    → dense pattern 학습
  - CrossAttention: 입력 feature 일부만 사용
    → 예: Drug 관련(Morgan FP + LINCS + Target + Pathway + Drug desc) = 1,112개
    → 또는 Gene expression에서 importance 상위 subset만
    → "관계 학습" 전문화

전략 2: Loss 분리 (전략 1로 부족할 때)
  - FlatMLP: MSE (regression loss)
  - CrossAttention: Rank loss / pairwise loss
  → 출력 분포 자체를 다르게 만듦

전략 3: Input Noise Injection (quick check용)
  - CrossAttention 입력에 N(0, 0.01) 노이즈 추가
  → 근본 해결은 아니지만 빠른 확인용
```

**분리 실험 후 확인 지표:**

```
목표:
  prediction correlation < 0.95
  Top-30 overlap: 0.2~0.6 범위

측정:
  - FlatMLP vs CrossAttention Pearson/Spearman
  - Top-30/50 overlap
  - 개별 OOF Spearman (분리 전 대비 하락폭)
```

### 4.5-B-3. Optuna 튜닝

> 분리 실험 완료 후 (또는 Case 3으로 분리 불필요 시) 진행.

**튜닝 대상:**

| 모델 | 튜닝 방식 | 주요 파라미터 | 목표 |
|------|----------|-------------|------|
| CatBoost | Optuna (50~100 trials) | iterations, depth, learning_rate, l2_leaf_reg, subsample, colsample_bylevel | Gap ≤ 0.07 유지, Sp 향상 |
| FlatMLP | Optuna (50~100 trials) | hidden_dims, dropout, learning_rate, weight_decay, batch_size | Gap ≤ 0.03 유지 |
| CrossAttention | Optuna (50~100 trials) | n_heads, d_model, dropout, learning_rate, weight_decay | Unseen Drug Sp 향상 |

**튜닝 규칙:**

```
1. 평가 기준: OOF Spearman (5-fold CV, seed=42)
2. 과적합 제약: Gap ≤ 모델별 v3 Gap × 1.5
   - CatBoost: Gap ≤ 0.111
   - FlatMLP: Gap ≤ 0.036
   - CrossAttention: Gap ≤ 0.044
3. 기존 v3 결과 보존: 튜닝 결과는 20260415_v4_ensemble_test/tuning_results/ 에만 저장
4. 튜닝 전후 비교 필수: v3 기본값 vs v4 튜닝값
5. 튜닝 후 6단계 평가 재실행 (3개 모델만)
6. 튜닝 후 모델 간 예측 상관 재측정 (Diversity 확인)
```

### 4.5-B-4. 실행

```bash
# 분리 실험 (Case 2일 때만)
python separation/feature_subset_experiment.py \
  --fe_path features_slim.parquet \
  --label_path labels.parquet \
  --output 20260415_v4_ensemble_test/separation_results/

# 분리 후 correlation 재측정
python separation/measure_diversity.py \
  --pred_flatmlp separation_results/flatmlp_oof.parquet \
  --pred_crossattn separation_results/crossattn_oof.parquet \
  --output 20260415_v4_ensemble_test/separation_results/

# Optuna 튜닝 (분리 확인 후)
python tuning/tune_catboost.py \
  --fe_path features_slim.parquet \
  --label_path labels.parquet \
  --n_trials 100 \
  --output 20260415_v4_ensemble_test/tuning_results/

python tuning/tune_flatmlp.py \
  --fe_path features_slim.parquet \
  --label_path labels.parquet \
  --n_trials 100 \
  --output 20260415_v4_ensemble_test/tuning_results/

python tuning/tune_crossattention.py \
  --fe_path features_slim.parquet \
  --label_path labels.parquet \
  --n_trials 100 \
  --output 20260415_v4_ensemble_test/tuning_results/
```

### 4.5-B-5. QC 체크

```
[ ] (Case 2) 분리 실험 완료 · correlation < 0.95 확인
[ ] (Case 2) 분리 후 개별 Sp 하락폭 허용 범위 확인
[ ] CatBoost 튜닝 완료 · v3 대비 Sp 변화 기록
[ ] FlatMLP 튜닝 완료 · v3 대비 Sp 변화 기록
[ ] CrossAttention 튜닝 완료 · v3 대비 Sp 변화 기록
[ ] 3개 모델 Gap 제약 조건 충족 확인
[ ] 튜닝 후 6단계 평가 재실행
[ ] 모델 간 예측 상관 재측정 (Diversity < 0.90 확인)
[ ] v3 기본값 결과 보존 확인
```

---

## Step 5 — 앙상블 (v4: CatBoost + FlatMLP + CrossAttention)

### 5-1. 앙상블 구조

```
[입력] features_slim.parquet (6,366행 × 5,534컬럼)
        ↓
[3개 모델 예측]
CatBoost (안정성) + FlatMLP (패턴) + CrossAttention (확장성)
각 모델 OOF 예측값 사용 (튜닝 후 재학습 버전)
        ↓
[가중치 계산 — 3가지 방식 비교]
① Spearman 비례 가중치
② Equal weight (1/3씩)
③ Optuna 최적 가중치
        ↓
[가중 평균 → 최종 IC50 예측값]
        ↓
[Top 30 추출 → 카테고리 분류]
        ↓
[METABRIC 검증 → Top 15 선별]
```

### 5-2. v3 대비 변경점

| 항목 | v3 앙상블 A | v4 앙상블 |
|------|-----------|----------|
| 모델 구성 | CatBoost + DART + FlatMLP | CatBoost + FlatMLP + CrossAttention |
| DART → CrossAttention 이유 | CatBoost-DART 상관 0.990 | CrossAttention은 Attention 구조로 Tree와 차별화 |
| 가중치 방식 | Spearman 비례만 | 3가지 비교 (Spearman/Equal/Optuna) |
| 튜닝 | 미적용 | Optuna 튜닝 후 적용 |
| Diversity 목표 | 0.962 (너무 높음) | < 0.90 (이상적: 0.5~0.8) |

### 5-3. Diversity 모니터링

```
앙상블 실행 전 반드시 확인:
1. 3개 모델 OOF 예측값 간 Pearson 상관 행렬
2. 평균 상관 < 0.90 이면 진행
3. 평균 상관 ≥ 0.95 이면 Feature subset 분리 적용 후 재학습

v3 참고값 (문제였던 수치):
- CatBoost-DART: 0.990
- CatBoost-FlatMLP: 0.950
- DART-FlatMLP: 0.947
- 평균: 0.962

v3 참고값 (FlatMLP-CrossAttention):
- FlatMLP-CrossAttention: 1.000 (완전 중복)
→ 이 문제가 튜닝 후에도 지속되면 Feature subset 분리 필수
```

### 5-4. QC 기준

```
✅ 앙상블 Spearman > CatBoost 단독 (0.8704) — 핵심 목표
✅ 앙상블 Spearman > v3 앙상블 A (0.8668) — 최소 목표
✅ Gap ≈ 0 (과적합 없음)
✅ Diversity (평균 상관) < 0.90
✅ Top 30 추출 완료
✅ Top-30 Overlap (seed 안정성) 확인
✅ 약물 랭킹 지표: P@30, R@30, NDCG@30, EF@30, MAP
```

### 5-5. QC 체크

```
[ ] Diversity (모델 간 상관) 측정
[ ] 3가지 가중치 방식 비교 완료
[ ] 최적 앙상블 > CatBoost 단독 확인
[ ] Gap 확인
[ ] Top 30 추출
[ ] 약물 랭킹 지표 기록
[ ] v3 앙상블 A 대비 비교 완료
[ ] S3 저장 완료
```

---

## Step 6 — METABRIC 외부 검증 (A+B+C)

### v3.1과 동일. v4 앙상블 결과로 재실행.

| 방법 | 입력 | 평가 지표 | v3 결과 (참고) |
|------|------|----------|--------------|
| A — IC50 proxy | METABRIC FE + v4 앙상블 예측 | Spearman | v3: Top15 12/15 일치 |
| B — Survival binary | METABRIC OS/RFS + RSF 모델 | C-index · AUROC | v3: C-index 0.821 |
| C — GraphSAGE P@20 | drug-drug 유사도 그래프 | P@20 | v3: P@20 0.6875 |

### QC 체크

```
[ ] Method A·B·C 모두 완료
[ ] v3 결과 대비 변화 기록
[ ] Top 15 약물 목록 출력
[ ] v3 Top 15와 overlap 비교
[ ] S3 저장 완료
```

---

## Step 7 — ADMET Gate (ML 자동화 · 3단계 필터링)

### v3.1과 동일. v4 앙상블 Top 15로 재실행.

### 필터링 3단계

```
Tier 1 Hard Fail → 즉시 탈락
- hERG > 0.7
- PAINS > 0
- Lipinski 위반 > 2

Tier 2 Soft Flag → 검토 후 판단
- hERG 0.5~0.7
- DILI · Ames · CYP3A4 · PPB · Caco2

Tier 3 Context → 항암제 특성상 완화 적용
- F(oral) · t_half · Carcinogenicity
```

### QC 체크

```
[ ] 22개 ADMET assay 스크리닝 완료
[ ] Tier 1/2/3 분류 완료
[ ] CYP3A4 억제제/기질 분리 확인
[ ] v3 ADMET 결과 대비 변화 기록
[ ] S3 저장 완료
```

---

## Step 7+ — KG/API 검증·설명 자동화

### scaleup_biso 연동 (v3.1과 동일)

ADMET 통과 약물에 대해:
- FAERS 부작용 조회
- ClinicalTrials 임상시험 현황
- HIRA 약가/급여 정보
- PubMed 관련 논문

---

## 평가 지표 체계 (32개)

### 예측 성능 (8개)
Spearman, Kendall tau, Pearson, R², RMSE, MAE, MedianAE, P95 absolute error

### 과적합 진단 (5개)
Train Spearman, OOF Spearman, Gap, Train/Val Ratio, Fold별 Spearman std

### 일반화 (6종 Split)
Random 5CV, Holdout, GroupKFold(drug), Unseen Drug, Scaffold Split, Multi-seed(5 seeds)

### 앙상블 품질 (4개)
앙상블 > Best 여부, 앙상블 Gap, 가중치 분포, Diversity(모델 간 상관)

### 약물 랭킹 (9개)
P@k, R@k, NDCG@k, MAP, EF@k, Top-k Overlap(seeds), Top-k Overlap(splits), 동일 계열 중복률, Target coverage

---

## 데이터 원칙

```
1. 실제 데이터 = curated_date/ 만 사용
2. v3 Step 4까지의 결과물(OOF 예측값, 6단계 평가) 재사용
3. 튜닝/앙상블 결과는 20260415_v4_ensemble_test/ 에만 저장
4. 기존 v3 결과 파일 수정 금지
5. proxy 데이터 사용 시 반드시 사용자 확인
```

---

## 폴더 구조

```
20260415_v4_ensemble_test/
├── protocol_guide_v4_20260415.md     ← 이 문서
├── tuning_results/                   ← Step 4.5 튜닝 결과
│   ├── catboost_tuning.json
│   ├── flatmlp_tuning.json
│   └── crossattention_tuning.json
├── ensemble_results/                 ← Step 5 앙상블 결과
│   ├── ensemble_v4_results.json
│   ├── diversity_matrix.json
│   └── top30_drugs.csv
├── metabric_results/                 ← Step 6 검증 결과
├── admet_results/                    ← Step 7 ADMET 결과
└── dashboards/                       ← 대시보드 파일
```

---

## 실행 순서 요약

```
1. Step 4.5-A: FlatMLP vs CrossAttention 동일예측 원인 검증
   - OOF prediction 직접 비교 (Pearson/Spearman/max diff/mean diff/Top-k overlap)
   - 파일 경로 · 저장 오류 점검
   - 학습 설정 비교 (seed/split/early stopping)

2. 분기 판단:
   - Case 1 (파일 오류) → 수정 후 재평가 → 3번으로
   - Case 2 (구조적 중복, corr ≥ 0.98) → Step 4.5-B 경량 분리 실험 → 3번으로
   - Case 3 (실제로 다름, corr < 0.95) → 바로 3번으로

3. Step 4.5-B: (필요시) 분리 실험 + Optuna 튜닝
   - 분리 후 correlation < 0.95 확인
   - 3개 모델 Optuna 튜닝 (각 50~100 trials)
   - 튜닝 후 6단계 평가 재실행
   - Diversity (평균 상관) < 0.90 확인

4. Step 5: 앙상블 3가지 가중치 비교
   - 앙상블 > CatBoost 단독(0.8704) 확인

5. Step 6: METABRIC 재검증
6. Step 7: ADMET 재실행
7. Step 7+: KG/API 검증
8. 대시보드 업데이트 + GitHub push
```
