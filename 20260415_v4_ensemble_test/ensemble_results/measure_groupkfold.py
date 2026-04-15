#!/usr/bin/env python3
"""
GroupKFold (by drug) 평가 - v4 앙상블용

v3 결과와 비교:
- CatBoost-Full v3 GroupKFold: 0.559

v4 측정 대상:
1. CatBoost-Full 단독
2. CatBoost-Drug 단독
3. Drug + Bilinear v2 (Weighted) ← 핵심!
4. Bilinear v2 단독

핵심 질문:
Bilinear의 Drug/Gene 분리 학습이 unseen drug 일반화에 더 나은가?
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold
import json

print("=" * 100)
print("GroupKFold (by drug) 평가")
print("=" * 100)

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
v4_dir = base_dir / "20260415_v4_ensemble_test"
catboost_dir = v4_dir / "catboost_subset"
bilinear_dir = v4_dir / "new_models/bilinear"
output_dir = v4_dir / "ensemble_results"

# ============================================================================
# 1. Drug IDs 로드 (features_slim.parquet)
# ============================================================================
print("\n[1] Drug IDs 로드")
print("-" * 100)

features_df = pd.read_parquet(base_dir / "20260414_re_pre_project_v3/features_slim.parquet")
drug_ids_full = features_df['canonical_drug_id'].values
print(f"✓ features_slim.parquet 로드 완료")
print(f"  Total samples: {len(drug_ids_full)}")
print(f"  Unique drugs: {len(np.unique(drug_ids_full))}")

# ============================================================================
# 2. v4 Shuffle 재현 (seed=42, 80/20 split)
# ============================================================================
print("\n[2] v4 Shuffle 재현 (seed=42)")
print("-" * 100)

n_samples = len(drug_ids_full)
n_train = int(n_samples * 0.8)

indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

# CV용 drug_ids (5092 samples)
drug_ids_cv = drug_ids_full[train_idx]
print(f"✓ CV samples: {len(drug_ids_cv)}")
print(f"  Unique drugs in CV: {len(np.unique(drug_ids_cv))}")

# ============================================================================
# 3. OOF Predictions 로드
# ============================================================================
print("\n[3] OOF Predictions 로드")
print("-" * 100)

# CatBoost-Full
catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
print(f"✓ CatBoost-Full OOF: {catboost_full_oof.shape}")

# CatBoost-Drug
catboost_drug_oof = np.load(catboost_dir / "catboost_drug/catboost_drug_oof.npy")
print(f"✓ CatBoost-Drug OOF: {catboost_drug_oof.shape}")

# Bilinear v2
bilinear_oof = np.load(bilinear_dir / "bilinear_v2_oof.npy")
print(f"✓ Bilinear-v2 OOF: {bilinear_oof.shape}")

# Ground truth
y_train_full = np.load(step4_dir / "y_train.npy")
y_cv = y_train_full[train_idx]
print(f"✓ y_cv: {y_cv.shape}")

# ============================================================================
# 4. Ensemble 계산
# ============================================================================
print("\n[4] Ensemble 계산")
print("-" * 100)

# Drug + Bilinear (Weighted: 51%/49% from comprehensive_evaluation)
drug_oof_sp = spearmanr(y_cv, catboost_drug_oof)[0]
bilinear_oof_sp = spearmanr(y_cv, bilinear_oof)[0]

w_drug = max(drug_oof_sp, 0)
w_bilinear = max(bilinear_oof_sp, 0)
total = w_drug + w_bilinear

w_drug /= total
w_bilinear /= total

drug_bilinear_oof = w_drug * catboost_drug_oof + w_bilinear * bilinear_oof

print(f"Drug + Bilinear (Weighted) 가중치:")
print(f"  Drug: {w_drug:.4f}")
print(f"  Bilinear: {w_bilinear:.4f}")
print(f"  OOF Spearman: {spearmanr(y_cv, drug_bilinear_oof)[0]:.4f}")

# ============================================================================
# 5. GroupKFold 평가 함수
# ============================================================================

def evaluate_groupkfold(oof_pred, y_true, drug_ids, name="Model"):
    """
    GroupKFold 평가

    OOF predictions는 이미 전체 CV set에 대해 계산되어 있으므로,
    GroupKFold로 split하고 해당 validation set의 predictions만 사용.
    """
    print(f"\n[GroupKFold] {name}")
    print("-" * 100)

    gkf = GroupKFold(n_splits=5)
    fold_sps = []
    fold_rmses = []

    # GroupKFold은 drug_ids를 기준으로 split (unseen drug 평가)
    for fold_idx, (_, val_idx) in enumerate(gkf.split(oof_pred, y_true, groups=drug_ids), 1):
        val_true = y_true[val_idx]
        val_pred = oof_pred[val_idx]

        fold_sp = spearmanr(val_true, val_pred)[0]
        fold_rmse = np.sqrt(np.mean((val_true - val_pred) ** 2))

        fold_sps.append(fold_sp)
        fold_rmses.append(fold_rmse)

        print(f"  Fold {fold_idx}/5: Spearman={fold_sp:.4f}, RMSE={fold_rmse:.4f}, Drugs={len(np.unique(drug_ids[val_idx]))}")

    mean_sp = np.mean(fold_sps)
    std_sp = np.std(fold_sps)
    mean_rmse = np.mean(fold_rmses)

    print(f"\n  평균 Spearman: {mean_sp:.4f} ± {std_sp:.4f}")
    print(f"  평균 RMSE: {mean_rmse:.4f}")

    return {
        'mean_spearman': float(mean_sp),
        'std_spearman': float(std_sp),
        'mean_rmse': float(mean_rmse),
        'fold_spearman': [float(x) for x in fold_sps],
        'fold_rmse': [float(x) for x in fold_rmses]
    }

# ============================================================================
# 6. 4개 모델 평가
# ============================================================================
print("\n" + "=" * 100)
print("GroupKFold 평가 시작")
print("=" * 100)

results = {}

# 1. CatBoost-Full
results['CatBoost-Full'] = evaluate_groupkfold(
    catboost_full_oof, y_cv, drug_ids_cv,
    name="CatBoost-Full (v3 baseline: 0.559)"
)

# 2. CatBoost-Drug
results['CatBoost-Drug'] = evaluate_groupkfold(
    catboost_drug_oof, y_cv, drug_ids_cv,
    name="CatBoost-Drug"
)

# 3. Bilinear v2
results['Bilinear-v2'] = evaluate_groupkfold(
    bilinear_oof, y_cv, drug_ids_cv,
    name="Bilinear-v2 (Drug/Gene 분리 학습)"
)

# 4. Drug + Bilinear (Weighted) ← 핵심!
results['Drug+Bilinear (Weighted)'] = evaluate_groupkfold(
    drug_bilinear_oof, y_cv, drug_ids_cv,
    name="Drug + Bilinear (Weighted) ⭐️ 핵심!"
)

# ============================================================================
# 7. 결과 요약
# ============================================================================
print("\n" + "=" * 100)
print("GroupKFold 결과 요약")
print("=" * 100)

print("\n| Model | GroupKFold Sp (Mean ± Std) | RMSE | vs v3 Full |")
print("|-------|---------------------------|------|------------|")

v3_baseline = 0.559

for name, res in results.items():
    mean_sp = res['mean_spearman']
    std_sp = res['std_spearman']
    mean_rmse = res['mean_rmse']
    diff = mean_sp - v3_baseline

    marker = ""
    if name == "Drug+Bilinear (Weighted)":
        marker = " 🏆" if diff > 0 else " ⚠️"

    print(f"| {name:<28} | {mean_sp:.4f} ± {std_sp:.4f} | {mean_rmse:.4f} | {diff:+.4f}{marker} |")

# ============================================================================
# 8. 핵심 질문 답변
# ============================================================================
print("\n" + "=" * 100)
print("핵심 질문 답변")
print("=" * 100)

drug_bilinear_sp = results['Drug+Bilinear (Weighted)']['mean_spearman']
catboost_full_sp = results['CatBoost-Full']['mean_spearman']
bilinear_sp = results['Bilinear-v2']['mean_spearman']
drug_sp = results['CatBoost-Drug']['mean_spearman']

print(f"\n❓ Drug+Bilinear 앙상블이 GroupKFold에서도 CatBoost-Full(0.559)보다 좋은가?")

if drug_bilinear_sp > v3_baseline:
    print(f"✅ YES! Drug+Bilinear = {drug_bilinear_sp:.4f} > v3 Full = {v3_baseline:.4f}")
    print(f"   개선폭: +{drug_bilinear_sp - v3_baseline:.4f}")
    print(f"   → Unseen drug 일반화도 향상됨!")
else:
    print(f"❌ NO. Drug+Bilinear = {drug_bilinear_sp:.4f} < v3 Full = {v3_baseline:.4f}")
    print(f"   하락폭: {drug_bilinear_sp - v3_baseline:.4f}")
    print(f"   → Unseen drug 일반화는 v3 대비 악화")

print(f"\n❓ v4 CatBoost-Full vs v3 CatBoost-Full (GroupKFold)?")
print(f"   v4: {catboost_full_sp:.4f}")
print(f"   v3: {v3_baseline:.4f}")
print(f"   차이: {catboost_full_sp - v3_baseline:+.4f}")

print(f"\n❓ Bilinear의 Drug/Gene 분리 학습이 unseen drug에 더 나은가?")
print(f"   Bilinear 단독: {bilinear_sp:.4f}")
print(f"   Drug 단독: {drug_sp:.4f}")
if bilinear_sp > drug_sp:
    print(f"   ✅ YES! Bilinear이 {bilinear_sp - drug_sp:+.4f} 더 좋음")
    print(f"   → Drug/Gene 분리가 unseen drug 일반화에 효과적!")
else:
    print(f"   ❌ NO. Bilinear이 {bilinear_sp - drug_sp:.4f} 더 낮음")
    print(f"   → Drug/Gene 분리의 장점이 크지 않음")

# ============================================================================
# 9. 저장
# ============================================================================
print("\n" + "=" * 100)
print("결과 저장")
print("=" * 100)

output = {
    "evaluation_type": "GroupKFold (by canonical_drug_id)",
    "n_splits": 5,
    "cv_samples": len(drug_ids_cv),
    "unique_drugs": len(np.unique(drug_ids_cv)),
    "v3_baseline": {
        "model": "CatBoost-Full",
        "groupkfold_spearman": v3_baseline
    },
    "v4_results": results,
    "weights": {
        "drug": float(w_drug),
        "bilinear": float(w_bilinear)
    },
    "key_findings": {
        "drug_bilinear_better_than_v3": drug_bilinear_sp > v3_baseline,
        "drug_bilinear_vs_v3": float(drug_bilinear_sp - v3_baseline),
        "bilinear_better_than_drug": bilinear_sp > drug_sp,
        "bilinear_vs_drug": float(bilinear_sp - drug_sp)
    }
}

output_path = output_dir / "groupkfold_results.json"
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"✓ JSON: {output_path}")

# CSV 요약표
summary_df = pd.DataFrame([
    {
        'Model': name,
        'GroupKFold_Spearman': res['mean_spearman'],
        'Std': res['std_spearman'],
        'RMSE': res['mean_rmse'],
        'vs_v3_Full': res['mean_spearman'] - v3_baseline
    }
    for name, res in results.items()
])

csv_path = output_dir / "groupkfold_comparison.csv"
summary_df.to_csv(csv_path, index=False)
print(f"✓ CSV: {csv_path}")

print("\n" + "=" * 100)
print("GroupKFold 평가 완료!")
print("=" * 100)
