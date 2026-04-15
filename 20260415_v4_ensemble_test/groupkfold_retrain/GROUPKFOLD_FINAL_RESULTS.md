# GroupKFold 재학습 최종 결과

**실험 날짜**: 2026-04-15
**방법**: GroupKFold (by canonical_drug_id) 5-fold 재학습 (올바른 방식)
**비교 대상**: v3 CatBoost GroupKFold = 0.491

---

## 📊 종합 결과

| Model | GroupKFold Sp | Std | RMSE | vs v3 | Holdout Sp | Holdout-GroupKFold Gap |
|-------|--------------|-----|------|-------|------------|------------------------|
| **CatBoost-Drug** 🏆 | **0.5210** | 0.0600 | 2.2646 | **+0.030** ✅ | 0.8710 | **-0.350 (-40.2%)** |
| CatBoost-Full | 0.5189 | 0.0619 | 2.2787 | +0.028 ✅ | 0.8709 | -0.352 (-40.4%) |
| Drug+Bilinear | 0.5145 | - | 2.3412 | +0.024 ✅ | 0.8756 | -0.361 (-41.2%) |
| Bilinear-v2 | 0.4074 | 0.1264 | 2.8968 | **-0.084** ❌ | 0.8522 | **-0.445 (-52.2%)** |

---

## 🔬 Fold별 상세 결과

### CatBoost-Full
| Fold | Train Drugs | Val Drugs | Val Spearman |
|------|------------|-----------|--------------|
| 1 | 196 | 47 | 0.5778 |
| 2 | 196 | 47 | 0.4804 |
| 3 | 192 | 51 | 0.4157 |
| 4 | 192 | 51 | 0.5672 |
| 5 | 196 | 47 | 0.5535 |
| **Mean** | - | - | **0.5189 ± 0.0619** |

### CatBoost-Drug
| Fold | Val Spearman |
|------|--------------|
| 1 | 0.5711 |
| 2 | 0.5041 |
| 3 | 0.4137 |
| 4 | 0.5799 |
| 5 | 0.5364 |
| **Mean** | **0.5210 ± 0.0600** |

### Bilinear v2
| Fold | Val Spearman |
|------|--------------|
| 1 | 0.5331 |
| 2 | 0.4821 |
| 3 | **0.2003** ⚠️ |
| 4 | 0.3226 |
| 5 | 0.4988 |
| **Mean** | **0.4074 ± 0.1264** |

**Fold 3 이상 저조**: Bilinear이 특정 unseen drug에 취약함

### Drug+Bilinear 앙상블
- **Weighted**: Drug 56.1% + Bilinear 43.9%
- **Spearman**: 0.5145
- **vs Drug 단독**: -0.0065 (악화)

---

## 💡 핵심 발견

### 1. ❌ Bilinear의 Drug/Gene 분리는 unseen drug에 불리

**가설**: Drug/Gene을 분리 학습하면 unseen drug 일반화가 더 좋을 것
**결과**: ❌ 완전히 반대

- Bilinear: 0.4074 (최악)
- CatBoost-Drug: 0.5210 (최고)
- **차이**: -0.1137 (21.8% 더 낮음)

**이유**:
- Bilinear은 Drug-Gene interaction을 학습하는데, unseen drug의 interaction은 예측 불가
- CatBoost은 drug features 자체를 학습하여 더 robust
- Fold 3에서 Bilinear 0.2003 (극단적 실패) → 특정 drug에 매우 취약

---

### 2. ❌ Drug+Bilinear 앙상블은 GroupKFold에서 개선되지 않음

**가설**: 앙상블이 unseen drug에서도 개선될 것
**결과**: ❌ 오히려 약간 악화

- Drug+Bilinear: 0.5145
- CatBoost-Drug: 0.5210
- **차이**: -0.0065

**이유**:
- Bilinear이 너무 약해서 (0.4074) Drug (0.5210)을 희석
- Weighted 앙상블도 Bilinear의 약점을 극복하지 못함
- Holdout에서는 diversity 효과가 있었지만, unseen drug에서는 무효

---

### 3. ✅ v4 잘못된 GroupKFold 측정 확인

**v4 잘못된 방식** (기존 OOF 재분할):
- CatBoost-Full: 0.8583
- 방법: Random 5-CV OOF를 GroupKFold로 재분할
- 문제: 모델이 모든 약물로 학습되어 unseen drug 테스트가 아님

**v4 올바른 방식** (GroupKFold 재학습):
- CatBoost-Full: 0.5189
- 방법: GroupKFold로 모델을 재학습 (각 fold마다 unseen drugs)
- **차이**: 0.8583 → 0.5189 = **-0.339 (-39.5%)**

**v3 결과**:
- CatBoost: 0.491

**결론**: v4 올바른 방식 (0.519)이 v3 (0.491)과 거의 일치 ✅

---

### 4. 📈 Holdout vs GroupKFold 차이

| Model | Holdout | GroupKFold | 하락폭 | 판정 |
|-------|---------|------------|-------|------|
| CatBoost-Drug | 0.8710 | 0.5210 | **-40.2%** | 가장 안정적 ✅ |
| CatBoost-Full | 0.8709 | 0.5189 | -40.4% | 안정적 |
| Drug+Bilinear | 0.8756 | 0.5145 | -41.2% | Holdout만 우수 |
| Bilinear-v2 | 0.8522 | 0.4074 | **-52.2%** | 매우 불안정 ❌ |

**해석**:
- CatBoost 계열: ~40% 하락 (SEVERE overfitting, v3와 동일)
- Bilinear: ~52% 하락 (더 심각한 overfitting)
- **CatBoost-Drug가 가장 안정적** (하락폭 최소)

---

## 🎯 최종 권고

### 🥇 **1순위: CatBoost-Drug 단독**

**채택 이유**:
- ✅ GroupKFold 최고 (0.5210)
- ✅ Holdout 최고 수준 (0.8710, 0.8709와 거의 동일)
- ✅ 가장 안정적 (Holdout-GroupKFold 차이 최소)
- ✅ Feature 효율성 (1,127개만 사용, 79.6% 감소)
- ✅ 단순성 (단일 모델, 배포 용이)

**적용 시나리오**:
- 신약 스크리닝 (unseen drugs 많음)
- 보수적/균형 잡힌 접근
- 프로덕션 환경

---

### 🥈 **2순위: Drug + Bilinear 앙상블**

**채택 이유**:
- ✅ Holdout 최고 (0.8756)
- ⚠️ GroupKFold 보통 (0.5145, Drug 단독보다 낮음)

**채택 조건**:
- Holdout 성능 우선 시 (known drugs)
- 앙상블 복잡도 허용 가능
- Unseen drug 성능 감소 감수

**적용 시나리오**:
- 기존 약물 재창출 (known drugs)
- Holdout 성능 극대화

---

### 🥉 **3순위: CatBoost-Full 단독**

**채택 이유**:
- ✅ v3 검증된 모델
- ⚠️ Drug 단독과 성능 동일, feature 불필요하게 많음

**채택 조건**:
- 보수적 선택 (v3 검증)
- 모든 feature 활용 원할 때

---

### ❌ **비권장: Bilinear v2 단독**

**이유**:
- ❌ GroupKFold 최악 (0.4074)
- ❌ Unseen drug에 매우 취약 (Fold 3: 0.2003)
- ❌ 높은 불안정성 (Std 0.1264)

**결론**: Bilinear은 **앙상블에서만** 제한적 가치 (Holdout에서만)

---

## 📝 추가 분석 필요

### GroupKFold 상관 분석
- CatBoost-Full vs Drug의 GroupKFold OOF 상관
- Bilinear vs CatBoost의 GroupKFold OOF 상관
- Diversity가 GroupKFold에서도 유지되는지 확인

### Fold 3 Bilinear 이상 저조 원인
- Fold 3의 특정 unseen drug 특성 분석
- 어떤 약물이 Bilinear 예측을 어렵게 하는가?
- Drug features와의 correlation 분석

---

## 🔬 실험 메타데이터

- **전체 샘플**: 6,366
- **Unique drugs**: 243
- **GroupKFold splits**: 5
- **평균 train drugs per fold**: ~195
- **평균 val drugs per fold**: ~48
- **Train/Val overlap**: 0 (모든 fold에서 확인됨 ✅)

---

## 📊 v3 vs v4 GroupKFold 비교

| Model | v3 | v4 (올바름) | 차이 |
|-------|-----|-------------|------|
| CatBoost-Full | 0.491 | 0.519 | +0.028 |
| CatBoost-Drug | - | **0.521** | - |
| Bilinear-v2 | - | 0.407 | - |
| Drug+Bilinear | - | 0.515 | - |

**결론**: v4와 v3 결과가 일치 (0.519 vs 0.491, ~5% 차이)

---

**최종 결론**: **CatBoost-Drug 단독** 사용 강력 권장 🏆
