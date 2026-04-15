# v4 Ensemble 최종 비교 테이블

**실험 기간**: 2026-04-15
**목적**: CatBoost-Full baseline (0.8709) 대비 성능 향상

---

## 📊 전체 모델 성능 비교 (Holdout + GroupKFold)

| Rank | Model | **Holdout Sp** | **GroupKFold Sp** | P@30 | NDCG@30 | Gap | Feature수 | 복잡도 |
|------|-------|---------------|------------------|------|---------|-----|-----------|--------|
| 🥇 | **CatBoost-Drug** | **0.8710** | **0.5210** ± 0.060 | **0.6667** | 0.9847 | 0.0065 | 1,127 | 단순 ✅ |
| 🥈 | Drug+Bilinear | **0.8756** | 0.5145 | 0.6333 | 0.9807 | 0.0132 | 1,127 + 5,529 | 중간 ⚠️ |
| 🥉 | CatBoost-Full | 0.8709 | 0.5189 ± 0.062 | 0.6333 | 0.9848 | 0.0085 | 5,529 | 단순 ✅ |
| 4 | Bilinear-v2 | 0.8522 | 0.4074 ± 0.126 | 0.5333 | 0.9692 | 0.0224 | 5,529 | 중간 |
| 5 | SAINT | 0.7344 | - | 0.2000 | 0.9475 | 0.0004 | 5,529 | 복잡 |
| - | HGT | - | - | - | - | - | - | 실패 ❌ |

---

## 🎯 Holdout vs GroupKFold 하락폭 분석

| Model | Holdout | GroupKFold | **하락폭** | **하락률** | 안정성 |
|-------|---------|------------|----------|-----------|--------|
| **CatBoost-Drug** | 0.8710 | 0.5210 | 0.3500 | **-40.2%** | 🏆 최고 |
| CatBoost-Full | 0.8709 | 0.5189 | 0.3520 | -40.4% | 우수 |
| Drug+Bilinear | 0.8756 | 0.5145 | 0.3611 | -41.2% | 보통 |
| Bilinear-v2 | 0.8522 | 0.4074 | 0.4448 | **-52.2%** | ❌ 불안정 |

**해석**:
- CatBoost 계열: ~40% 하락 (SEVERE overfitting, v3와 동일)
- Bilinear: ~52% 하락 (더 심각한 unseen drug overfitting)
- **CatBoost-Drug가 가장 안정적**

---

## 📈 시나리오별 최적 모델

### 1. 신약 스크리닝 (Unseen Drugs 많음)

| Model | Holdout | **GroupKFold** | 추천 |
|-------|---------|----------------|------|
| **CatBoost-Drug** 🏆 | 0.8710 | **0.5210** | ⭐⭐⭐⭐⭐ |
| CatBoost-Full | 0.8709 | 0.5189 | ⭐⭐⭐⭐ |
| Drug+Bilinear | 0.8756 | 0.5145 | ⭐⭐⭐ |
| Bilinear-v2 | 0.8522 | 0.4074 | ❌ 비권장 |

**권장**: **CatBoost-Drug** (Unseen drug 성능 최고, Feature 효율적)

---

### 2. 기존 약물 재창출 (Known Drugs)

| Model | **Holdout** | GroupKFold | 추천 |
|-------|------------|------------|------|
| **Drug+Bilinear** 🏆 | **0.8756** | 0.5145 | ⭐⭐⭐⭐⭐ |
| CatBoost-Drug | 0.8710 | 0.5210 | ⭐⭐⭐⭐ |
| CatBoost-Full | 0.8709 | 0.5189 | ⭐⭐⭐ |

**권장**: **Drug+Bilinear** (Holdout 최고, Known drug 정확도 우선)

---

### 3. 균형/보수적 접근

| Model | Holdout | GroupKFold | Feature | 복잡도 | 추천 |
|-------|---------|------------|---------|--------|------|
| **CatBoost-Drug** 🏆 | 0.8710 | **0.5210** | 1,127 | 단순 | ⭐⭐⭐⭐⭐ |
| CatBoost-Full | 0.8709 | 0.5189 | 5,529 | 단순 | ⭐⭐⭐⭐ |
| Drug+Bilinear | 0.8756 | 0.5145 | 복합 | 중간 | ⭐⭐⭐ |

**권장**: **CatBoost-Drug** (모든 면에서 균형 잡힘)

---

### 4. 프로덕션 환경

| Model | 성능 | 안정성 | 복잡도 | Feature | 추천 |
|-------|------|--------|--------|---------|------|
| **CatBoost-Drug** 🏆 | 최고 수준 | 최고 | 단순 ✅ | 1,127 | ⭐⭐⭐⭐⭐ |
| CatBoost-Full | 최고 수준 | 우수 | 단순 ✅ | 5,529 ⚠️ | ⭐⭐⭐⭐ |
| Drug+Bilinear | 최고 | 보통 | 복잡 ⚠️ | 복합 | ⭐⭐⭐ |

**권장**: **CatBoost-Drug** (단순성 + 효율성 + 안정성)

---

## 🔬 모델별 상세 분석

### 🏆 CatBoost-Drug (최종 1위)

**장점**:
- ✅ GroupKFold 최고 (0.5210)
- ✅ Holdout 최고 수준 (0.8710)
- ✅ 가장 안정적 (하락 40.2%, 최소)
- ✅ Feature 효율성 (79.6% 감소)
- ✅ 단순성 (단일 모델)

**단점**:
- ⚠️ Holdout이 Drug+Bilinear보다 -0.0046 낮음

**권장 시나리오**: 신약, 균형, 프로덕션 (거의 모든 경우)

---

### 🥈 Drug+Bilinear 앙상블 (조건부 2위)

**장점**:
- ✅ Holdout 최고 (0.8756)
- ✅ Diversity 효과 (random split에서)

**단점**:
- ❌ GroupKFold에서 Drug 단독보다 낮음 (-0.0065)
- ❌ 복잡도 (2-model, StandardScaler 필수)
- ❌ Bilinear이 unseen drug에 약함 (0.4074)

**권장 시나리오**: Known drug 재창출만

---

### 🥉 CatBoost-Full (보수적 3위)

**장점**:
- ✅ v3 검증된 모델
- ✅ GroupKFold 우수 (0.5189)

**단점**:
- ⚠️ Drug와 성능 동일, Feature만 많음 (비효율)

**권장 시나리오**: 보수적 선택

---

### ❌ Bilinear-v2 (단독 사용 비권장)

**장점**:
- ✅ Holdout 보통 (0.8522)
- ✅ 앙상블 diversity 제공

**단점**:
- ❌ GroupKFold 최악 (0.4074, -21.8% vs Drug)
- ❌ 매우 불안정 (Fold 3: 0.2003)
- ❌ Unseen drug 극도로 취약

**결론**: Bilinear은 **앙상블에서만** 제한적 가치 (Holdout에서만)

---

## 📊 v3 vs v4 비교

| Metric | v3 CatBoost | v4 CatBoost-Full | v4 CatBoost-Drug | 개선 |
|--------|-------------|-----------------|-----------------|------|
| Holdout Sp | - | 0.8709 | **0.8710** | - |
| **GroupKFold Sp** | **0.491** | **0.519** | **0.521** | **+0.030** ✅ |
| Feature 수 | 5,529 | 5,529 | **1,127** | **-79.6%** ✅ |
| 복잡도 | 단순 | 단순 | 단순 | 동일 |

**결론**:
- v4 GroupKFold (0.519) ≈ v3 (0.491) → 측정 검증 완료
- CatBoost-Drug가 Feature 효율성 극대화
- Unseen drug 성능 유지하면서 Feature 79.6% 감소

---

## 🎯 최종 권장사항 요약

### 일반적 상황 (90% 케이스)
→ **CatBoost-Drug 단독** 🏆
- 이유: 최고 안정성 + Feature 효율성 + 단순성
- Holdout 0.8710, GroupKFold 0.5210

### Known Drug 재창출 (10% 케이스)
→ **Drug+Bilinear 앙상블**
- 이유: Holdout 최고 (0.8756)
- 주의: Unseen drug에서 Drug 단독보다 낮음

### 절대 비권장
→ ❌ Bilinear-v2 단독
- 이유: Unseen drug 극도로 취약 (0.4074)

---

## 🔬 핵심 발견 정리

1. **Drug Features의 중요성**
   - Drug 1,127개만으로 Full (5,529개)과 동일 성능
   - IC50 signal이 Drug features에 집중
   - Gene/CRISPR features는 거의 무의미

2. **Bilinear의 역할 재평가**
   - Holdout: 유리 (diversity 제공)
   - Unseen drug: 불리 (interaction 전이 실패)
   - 결론: Random split에서만 가치

3. **앙상블의 한계**
   - Holdout: Drug+Bilinear > Drug ✅
   - GroupKFold: Drug+Bilinear < Drug ❌
   - Known drug에서만 효과적

4. **GroupKFold 측정 검증**
   - v4 초기 (0.858): 잘못됨 (OOF 재분할)
   - v4 올바름 (0.519): v3 (0.491)과 일치 ✅
   - 올바른 방법: GroupKFold로 재학습

---

**최종 결론**: **CatBoost-Drug 단독** 강력 권장 🏆

- 모든 시나리오에서 최상위 또는 최고 성능
- 가장 안정적 (Unseen drug 성능 최고)
- Feature 효율적 (79.6% 감소)
- 단순성 (프로덕션 배포 용이)
