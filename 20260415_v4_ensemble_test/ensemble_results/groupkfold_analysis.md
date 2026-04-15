# GroupKFold 측정 방식 차이 분석

## 📊 v3 vs v4 결과 비교

| Metric | v3 CatBoost | v4 CatBoost | 차이 |
|--------|------------|------------|------|
| **Random 5-CV OOF** | 0.8624 | 0.8624 | 동일 |
| **GroupKFold Sp** | **0.4909** | **0.8583** | **+0.3674** |
| **Drop from Random** | -43% | -0.5% | **42.5%p 차이** |

---

## 🚨 **핵심 발견: 측정 방식이 완전히 다름!**

### v3 방식 (CORRECT ✅)
```python
# v3: GroupKFold로 모델을 재학습
for fold in GroupKFold(5):
    model = CatBoost()
    model.fit(X_train, y_train)  # Unseen drugs로 학습
    val_pred = model.predict(X_val)  # 완전히 다른 약물로 평가
```

**특징**:
- 각 fold마다 **새로 학습**
- Train에 없는 약물을 Val에서 예측 (진정한 unseen drug 테스트)
- 결과: **0.862 → 0.491 (-43%)**
- 판정: "SEVERE overfitting" (unseen drug에 약함)

---

### v4 방식 (WRONG ❌)
```python
# v4: 기존 OOF predictions를 GroupKFold로 재분할
oof_predictions = load("catboost_oof.npy")  # 이미 random split으로 학습됨
for fold in GroupKFold(5):
    val_pred = oof_predictions[val_idx]  # 그냥 기존 예측 사용
```

**문제점**:
- 모델은 **random split으로 학습됨** (모든 약물이 train에 포함)
- GroupKFold은 단지 predictions를 재분할할 뿐
- Val에 있는 약물도 이미 train에서 봤음 ❌
- 결과: **0.862 → 0.858 (-0.5%)** (너무 높음, 현실적이지 않음)

---

## 💡 왜 v4가 잘못되었나?

### v4 OOF 생성 방식 (random 5-CV)
```
전체 6366 샘플 → shuffle → 80/20 split
CV 5092 샘플 → random 5-fold CV
각 fold: 약물 A, B, C, D, E가 모두 train에 포함됨
```

### v4 GroupKFold "측정" (잘못됨)
```
OOF predictions (이미 모든 약물로 학습됨)
→ GroupKFold로 재분할
→ Fold 1 val: 약물 A, B (이미 train에서 봤음!)
→ Spearman 0.86 (당연히 높음)
```

### 올바른 GroupKFold (v3)
```
전체 6366 샘플
→ GroupKFold 5-fold (약물 기준 분할)
→ Fold 1: train에 약물 C,D,E만, val에 약물 A,B
→ 모델을 새로 학습 (약물 C,D,E만 사용)
→ 약물 A,B 예측 (처음 보는 약물!)
→ Spearman 0.56 (unseen drug이라 낮음)
```

---

## 🎯 올바른 측정 방법

### ✅ 해야 할 것
1. **v3처럼 GroupKFold로 모델 재학습**
2. 각 fold마다 unseen drugs로 평가
3. 진정한 drug generalization 측정

### ❌ 하지 말아야 할 것
- 기존 OOF predictions를 GroupKFold로 재분할 (v4 방식)
- 이미 학습된 예측을 재평가 (의미 없음)

---

## 📈 v3 실제 결과 (step2_groupkfold_04_results.json)

```json
{
  "random_5cv_spearman": 0.8624,
  "spearman_mean": 0.4909,
  "drop_from_random": 0.3691,
  "overfitting_verdict": "SEVERE"
}
```

**Fold별 Spearman**:
- Fold 1: 0.5630
- Fold 2: 0.4323
- Fold 3: 0.4078
- Fold 4: 0.5086
- Fold 5: 0.5427
- **평균: 0.4909**

---

## 🔧 v4 수정 필요

**현재 v4 결과 (0.8583)는 무효!**

올바른 측정을 위해:
1. CatBoost-Full을 GroupKFold로 **재학습**
2. CatBoost-Drug를 GroupKFold로 **재학습**
3. Bilinear v2를 GroupKFold로 **재학습**
4. Drug+Bilinear 앙상블을 GroupKFold로 **재학습**

**예상 결과**:
- CatBoost-Full: ~0.49 (v3와 유사)
- CatBoost-Drug: ? (측정 필요)
- Bilinear v2: ? (Drug/Gene 분리가 유리할 수도)
- Drug+Bilinear: ? (핵심 질문!)

---

## ⏱️ 추정 시간

각 모델 GroupKFold 재학습:
- CatBoost-Full: ~15분 (5 folds × 3분)
- CatBoost-Drug: ~10분
- Bilinear v2: ~40분 (5 folds × 8분, 200 epochs)
- Total: ~1시간

---

## 🎯 결론

**v4 GroupKFold 측정은 잘못되었음** ❌
- 측정 방식: 기존 OOF 재분할 (의미 없음)
- 결과 0.8583: 너무 높음 (unseen drug 테스트가 아님)

**올바른 방법**: v3처럼 GroupKFold로 재학습 필요 ✅
- 각 fold에서 unseen drugs로 평가
- 예상 결과: 0.49~0.56 (v3와 유사)
- 시간: ~1시간

**핵심 질문 재설정**:
- Drug+Bilinear가 GroupKFold 재학습에서도 CatBoost-Full (0.49)보다 나은가?
- Bilinear의 Drug/Gene 분리 학습이 unseen drug에 유리한가?
