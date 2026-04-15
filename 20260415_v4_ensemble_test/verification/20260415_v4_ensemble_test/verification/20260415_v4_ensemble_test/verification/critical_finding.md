# 🚨 중대 발견: CrossAttention의 정체

**검증 일시:** 2026-04-15
**발견자:** Weight Architecture Check

---

## 핵심 발견

### **"CrossAttention"이라는 이름만 있고, 실제로는 단순 MLP!**

---

## 1. Weight 파일 분석 결과

| 항목 | FlatMLP (model_10) | CrossAttention (model_13) | 비교 |
|------|-------------------|---------------------------|------|
| **Total Parameters** | **1,481,729** | **1,481,729** | ⚠️ **완전 동일** |
| **Layer 구조** | Linear → Linear → Linear | Linear → Linear → Linear | ⚠️ **동일** |
| **Attention Layer** | ❌ 없음 (정상) | ❌ **없음 (비정상!)** | 🚨 **문제!** |
| State dict keys | net.0, net.3, net.6 | fc1, fc2, out | 이름만 다름 |

### State Dict 세부:

**FlatMLP:**
```
net.0.weight: [256, 5529]  ← input → hidden
net.0.bias:   [256]
net.3.weight: [256, 256]   ← hidden → hidden
net.3.bias:   [256]
net.6.weight: [1, 256]     ← hidden → output
net.6.bias:   [1]
```

**CrossAttention:**
```
fc1.weight: [256, 5529]    ← input → hidden
fc1.bias:   [256]
fc2.weight: [256, 256]     ← hidden → hidden
fc2.bias:   [256]
out.weight: [1, 256]       ← hidden → output
out.bias:   [1]
```

**→ 완전히 동일한 shape!**

---

## 2. 소스 코드 확인

### CrossAttentionMLP 클래스 (retrain_gpu_models.py:121-135)

```python
class CrossAttentionMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()

    def forward(self, x):
        x1 = self.relu(self.fc1(x))
        x1 = self.dropout(x1)
        x2 = self.relu(self.fc2(x1))
        x2 = self.dropout(x2)
        return self.out(x2).squeeze()
```

**분석:**
- ❌ **Attention layer 전혀 없음!**
- ❌ **MultiheadAttention 없음!**
- ❌ **Query/Key/Value 없음!**
- ✅ 단순한 2-layer MLP

### FlatMLP 클래스 (retrain_gpu_models.py:69-83)

```python
class FlatMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze()
```

**분석:**
- ✅ 2-layer MLP (정직한 이름)
- ✅ Sequential 사용 vs 명시적 forward

---

## 3. 두 모델의 실질적 차이

| 항목 | FlatMLP | CrossAttentionMLP | 차이점 |
|------|---------|-------------------|--------|
| **구조** | 2-layer MLP | 2-layer MLP | 동일 |
| **Layer 수** | 3 (fc1, fc2, out) | 3 (fc1, fc2, out) | 동일 |
| **Hidden dim** | 256 | 256 | 동일 |
| **Activation** | ReLU | ReLU | 동일 |
| **Dropout** | 0.3 | 0.3 | 동일 |
| **구현 방식** | Sequential | 명시적 forward | **유일한 차이** |
| **Residual** | ❌ | ❌ | 동일 |
| **Attention** | ❌ | ❌ | **둘 다 없음!** |

### 유일한 차이: 구현 스타일

**FlatMLP:**
```python
self.net = nn.Sequential(
    nn.Linear(...), nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(...), nn.ReLU(), nn.Dropout(0.3),
    nn.Linear(...)
)
```

**CrossAttentionMLP:**
```python
x1 = self.relu(self.fc1(x))
x1 = self.dropout(x1)
x2 = self.relu(self.fc2(x1))
x2 = self.dropout(x2)
return self.out(x2)
```

→ **본질적으로 동일한 연산!**

---

## 4. 예측 상관 0.9848의 원인

### 근본 원인: **구조적으로 거의 동일한 모델**

```
동일 요소:
✓ 같은 input features (5,529개)
✓ 같은 hidden dimension (256)
✓ 같은 layer 수 (3)
✓ 같은 activation (ReLU)
✓ 같은 dropout (0.3)
✓ 같은 loss (MSE)
✓ 같은 optimizer (Adam)
✓ 같은 learning rate (0.001)
✓ 같은 epochs (100)
✓ 같은 random seed (42)
✓ 같은 5-fold CV split

차이 요소:
✗ 구현 스타일만 다름 (Sequential vs 명시적)
```

### 결과:
- **두 모델이 거의 같은 함수를 학습함**
- **예측값이 매우 유사함 (Spearman 0.9848)**
- **Top-30 overlap 40%**

---

## 5. 프로토콜 v3 vs 실제

| 항목 | 프로토콜 v3 기대 | 실제 |
|------|----------------|------|
| CrossAttention 구조 | Attention layer 있음 | **Attention 없음!** |
| 역할 | 확장성 · 새 약물 일반화 | 단순 MLP |
| FlatMLP와 차이 | Attention vs MLP | **구현 스타일만 다름** |
| Diversity | 다른 구조로 다양성 | **거의 동일** |
| Unseen Drug 최고 성능 | 0.335 (3개 중 최고) | 우연일 가능성 |

---

## 6. 버그 vs 설계 오류

### 판정: **설계 오류 (Code Naming Error)**

**버그 아님:**
- [x] 학습은 정상적으로 실행됨
- [x] 두 모델이 별도로 학습됨
- [x] Weight 파일이 분리되어 저장됨
- [x] 예측값이 약간 다름 (0.9848, 완전 동일 아님)

**설계 오류:**
- [x] **CrossAttentionMLP 클래스에 Attention이 없음**
- [x] **이름만 "CrossAttention"이고 실제로는 MLP**
- [x] **FlatMLP와 구조적으로 거의 동일**
- [x] **앙상블 Diversity를 제공하지 못함**

---

## 7. v3 앙상블 재평가

### v3 앙상블 A: CatBoost + DART + FlatMLP
- CatBoost-DART 상관: 0.990 (높음)
- CatBoost-FlatMLP 상관: 0.950 (높음)
- **Diversity 평균: 0.962 (너무 높음)**

### v4 계획: CatBoost + FlatMLP + CrossAttention
- **문제: CrossAttention이 사실상 FlatMLP와 동일**
- **예상 결과: Diversity 개선 실패**

---

## 8. 올바른 CrossAttention 구조 예시

### 진짜 CrossAttention이어야 할 구조:

```python
class RealCrossAttention(nn.Module):
    def __init__(self, input_dim, hidden_dim=256, n_heads=4):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)

        # ✅ Attention layer 추가
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=n_heads,
            dropout=0.3,
            batch_first=True
        )

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.3)
        self.relu = nn.ReLU()

    def forward(self, x):
        # Input projection
        x1 = self.relu(self.fc1(x))  # [batch, hidden]
        x1 = self.dropout(x1)

        # Self-attention
        x1_attn = x1.unsqueeze(1)  # [batch, 1, hidden]
        attn_out, _ = self.attention(x1_attn, x1_attn, x1_attn)
        attn_out = attn_out.squeeze(1)  # [batch, hidden]

        # Residual connection
        x2 = x1 + attn_out

        # Output
        x3 = self.relu(self.fc2(x2))
        x3 = self.dropout(x3)
        return self.out(x3).squeeze()
```

---

## 9. 다음 단계 재설정

### 원래 계획 (Step 4.5-B):
- Feature Subset 분리 실험
- Optuna 튜닝

### **새로운 계획:**

#### Option 1: CrossAttention 재구현 (추천)
1. **진짜 Attention layer가 있는 CrossAttention 구현**
2. 재학습 (같은 5-fold CV, seed=42)
3. 예측 상관 재측정 (목표: < 0.95)
4. Diversity 확인 (목표: < 0.90)

#### Option 2: 다른 모델로 교체
1. CrossAttention 대신 다른 모델 사용:
   - ResidualMLP (model_09)
   - FTTransformer (model_12)
   - GraphSAGE (model_14)
   - GAT (model_15)
2. 기존 v3 결과 활용
3. Diversity 재측정

#### Option 3: Feature Subset 분리 (임시 방편)
1. 현재 CrossAttentionMLP 유지
2. Feature subset으로 차별화
3. **하지만 근본 해결은 아님**

---

## 10. 권장 사항

### ✅ 권장: **Option 1 (CrossAttention 재구현)**

**이유:**
1. 프로토콜 v4의 의도 구현 (Attention 구조)
2. Diversity 실질적 개선
3. Unseen Drug 성능 향상 가능성
4. 학술적 정직성

**구현 계획:**
1. 위 "RealCrossAttention" 클래스 구현
2. retrain_gpu_models.py에서 CrossAttentionMLP 교체
3. model_13 재학습
4. 6단계 평가 재실행
5. Diversity 0.9848 → 목표 < 0.90

**예상 소요 시간:**
- 구현: 30분
- 재학습: 1-2시간 (MPS)
- 평가: 30분
- **총 2-3시간**

---

## 11. 최종 결론

### 🚨 **CrossAttention은 이름만 있고 실제로는 FlatMLP의 변종**

**증거:**
1. ✅ Attention layer 전혀 없음 (소스 코드 확인)
2. ✅ 파라미터 수 1,481,729로 동일
3. ✅ 구조 동일 (2-layer MLP)
4. ✅ 예측 상관 0.9848 (매우 높음)
5. ✅ Weight shape 완전 동일

**판정:**
- **버그 아님, 설계/명명 오류**
- **앙상블 Diversity를 제공하지 못함**
- **재구현 필요**

**다음 단계:**
→ **CrossAttention을 진짜 Attention layer가 있는 모델로 재구현**

---

**검증 완료 일시:** 2026-04-15
**파일 위치:** `20260415_v4_ensemble_test/verification/`
**담당:** Claude Code v4.0
