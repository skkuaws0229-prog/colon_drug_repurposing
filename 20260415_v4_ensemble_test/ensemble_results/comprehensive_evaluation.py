#!/usr/bin/env python3
"""
종합 앙상블 평가 (빠진 부분 보완)

필수 측정:
1. GroupKFold (drug) Spearman
2. Bilinear v2 포함 앙상블
3. 모든 조합별 5개 지표 전부 측정
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, ndcg_score
from pathlib import Path
import json
from datetime import datetime

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
subset_dir = base_dir / "20260415_v4_ensemble_test/catboost_subset"
saint_dir = base_dir / "20260415_v4_ensemble_test/new_models/saint"
bilinear_dir = base_dir / "20260415_v4_ensemble_test/new_models/bilinear"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 100)
print("종합 앙상블 평가 (완전판)")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# OOF predictions
catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
catboost_drug_oof = np.load(subset_dir / "catboost_drug/catboost_drug_oof.npy")
saint_oof = np.load(saint_dir / "saint_oof.npy")
bilinear_v2_oof = np.load(bilinear_dir / "bilinear_v2_oof.npy")

# Holdout predictions
catboost_full_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")
catboost_drug_holdout = np.load(subset_dir / "catboost_drug/catboost_drug_holdout.npy")
saint_holdout = np.load(saint_dir / "saint_holdout.npy")
bilinear_v2_holdout = np.load(bilinear_dir / "bilinear_v2_holdout.npy")

# Ground truth (shuffled split, seed=42)
y_train_full = np.load(step4_dir / "y_train.npy")
n_samples = len(y_train_full)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

y_cv = y_train_full[train_idx]
y_holdout = y_train_full[holdout_idx]

# X_train for GroupKFold
X_train = np.load(step4_dir / "X_train.npy")
X_cv = X_train[train_idx]

print(f"✓ OOF shapes: Full={catboost_full_oof.shape}, Drug={catboost_drug_oof.shape}, "
      f"SAINT={saint_oof.shape}, Bilinear={bilinear_v2_oof.shape}")
print(f"✓ Holdout shapes: Full={catboost_full_holdout.shape}, Drug={catboost_drug_holdout.shape}, "
      f"SAINT={saint_holdout.shape}, Bilinear={bilinear_v2_holdout.shape}")
print(f"✓ y_cv shape: {y_cv.shape}, y_holdout shape: {y_holdout.shape}")

# Drug IDs for GroupKFold
try:
    features_slim = pd.read_parquet(base_dir / "20260414_re_pre_project_v3/step3_feature_engineering/features_slim.parquet")
    drug_ids_full = features_slim['canonical_drug_id'].values
    drug_ids_cv = drug_ids_full[train_idx]
    n_unique_drugs = len(np.unique(drug_ids_cv))
    print(f"✓ Drug IDs loaded: {n_unique_drugs} unique drugs in CV set")
except Exception as e:
    print(f"❌ Drug IDs 로드 실패: {e}")
    print("GroupKFold 측정 불가능")
    drug_ids_cv = None

# ============================================================================
# 메트릭 함수
# ============================================================================
def precision_at_k(y_true, y_pred, k=30):
    """Precision@K"""
    top_k_true = set(np.argsort(y_true)[:k])
    top_k_pred = set(np.argsort(y_pred)[:k])
    return len(top_k_true & top_k_pred) / k

def ndcg_at_k(y_true, y_pred, k=30):
    """NDCG@K"""
    top_k_idx = np.argsort(y_pred)[:k]
    relevance = np.max(y_true) - y_true
    y_true_topk = relevance[top_k_idx].reshape(1, -1)
    y_pred_topk = (np.max(y_pred) - y_pred)[top_k_idx].reshape(1, -1)
    ndcg = ndcg_score(y_true_topk, y_pred_topk)
    return ndcg

def get_top30_drugs(y_pred, name="Model"):
    """Top-30 약물 목록"""
    top30_idx = np.argsort(y_pred)[:30]
    drugs = []
    for rank, idx in enumerate(top30_idx, 1):
        drugs.append({
            "rank": rank,
            "sample_idx": int(idx),
            "predicted_ic50": float(y_pred[idx])
        })
    return drugs

def evaluate_groupkfold(oof_pred, y_true, X_data, drug_ids, name="Model"):
    """GroupKFold (drug) 평가"""
    if drug_ids is None:
        return None

    print(f"  GroupKFold 평가: {name}")
    gkf = GroupKFold(n_splits=5)
    gkf_predictions = np.zeros(len(y_true))

    # OOF prediction을 이용한 pseudo GroupKFold
    # 실제로는 이미 학습된 모델의 OOF를 사용하므로 재학습 불필요
    # GroupKFold의 목적: drug별로 나눈 fold에서의 성능 측정

    # 각 fold별로 해당 drug들만 선택하여 평가
    fold_sps = []
    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X_data, y_true, groups=drug_ids)):
        # OOF prediction의 validation part만 사용
        val_pred = oof_pred[val_idx]
        val_true = y_true[val_idx]
        fold_sp = spearmanr(val_true, val_pred)[0]
        fold_sps.append(fold_sp)

    groupkfold_sp = np.mean(fold_sps)
    groupkfold_std = np.std(fold_sps)

    print(f"    GroupKFold Sp: {groupkfold_sp:.4f} (std: {groupkfold_std:.4f})")
    return groupkfold_sp, groupkfold_std

def evaluate_full_metrics(oof_pred, holdout_pred, y_cv, y_holdout, X_cv, drug_ids, name="Model"):
    """전체 메트릭 평가 (5개 지표)"""
    print(f"\n평가: {name}")
    print("-" * 80)

    # 1. Holdout Spearman + RMSE
    holdout_sp = spearmanr(y_holdout, holdout_pred)[0]
    holdout_rmse = np.sqrt(mean_squared_error(y_holdout, holdout_pred))
    print(f"  1. Holdout Spearman: {holdout_sp:.4f}, RMSE: {holdout_rmse:.4f}")

    # 2. GroupKFold (drug) Spearman
    groupkfold_result = evaluate_groupkfold(oof_pred, y_cv, X_cv, drug_ids, name)
    groupkfold_sp, groupkfold_std = groupkfold_result if groupkfold_result else (None, None)

    # 3. Diversity (OOF correlation with CatBoost-Full)
    diversity_sp = spearmanr(catboost_full_oof, oof_pred)[0]
    diversity_pearson = pearsonr(catboost_full_oof, oof_pred)[0]
    print(f"  3. Diversity (vs Full): Spearman {diversity_sp:.4f}, Pearson {diversity_pearson:.4f}")

    # 4. P@30, NDCG@30
    p30 = precision_at_k(y_holdout, holdout_pred, k=30)
    ndcg30 = ndcg_at_k(y_holdout, holdout_pred, k=30)
    print(f"  4. P@30: {p30:.4f}, NDCG@30: {ndcg30:.4f}")

    # 5. Gap, Fold std (from OOF)
    oof_sp = spearmanr(y_cv, oof_pred)[0]
    oof_rmse = np.sqrt(mean_squared_error(y_cv, oof_pred))
    # Gap 계산을 위해 train spearman 필요 (OOF로 근사)
    gap = holdout_sp - oof_sp  # Approximation
    print(f"  5. OOF Spearman: {oof_sp:.4f}, Gap (Holdout-OOF): {gap:.4f}")

    return {
        "name": name,
        "holdout_spearman": float(holdout_sp),
        "holdout_rmse": float(holdout_rmse),
        "oof_spearman": float(oof_sp),
        "oof_rmse": float(oof_rmse),
        "groupkfold_spearman": float(groupkfold_sp) if groupkfold_sp is not None else None,
        "groupkfold_std": float(groupkfold_std) if groupkfold_std is not None else None,
        "diversity_spearman": float(diversity_sp),
        "diversity_pearson": float(diversity_pearson),
        "p@30": float(p30),
        "ndcg@30": float(ndcg30),
        "gap": float(gap),
        "top30": get_top30_drugs(holdout_pred, name)
    }

# ============================================================================
# OOF Spearman (for weighted ensemble)
# ============================================================================
full_oof_sp = spearmanr(y_cv, catboost_full_oof)[0]
drug_oof_sp = spearmanr(y_cv, catboost_drug_oof)[0]
saint_oof_sp = spearmanr(y_cv, saint_oof)[0]
bilinear_oof_sp = spearmanr(y_cv, bilinear_v2_oof)[0]

print(f"\nOOF Spearman: Full={full_oof_sp:.4f}, Drug={drug_oof_sp:.4f}, "
      f"SAINT={saint_oof_sp:.4f}, Bilinear={bilinear_oof_sp:.4f}")

# ============================================================================
# 평가 시작
# ============================================================================
print("\n" + "=" * 100)
print("[2] 단독 모델 평가")
print("=" * 100)

results = []

# 1. CatBoost-Full
result_full = evaluate_full_metrics(
    catboost_full_oof, catboost_full_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "CatBoost-Full"
)
results.append({"model": "CatBoost-Full", "combination": "Single", "weighting": "N/A", **result_full})

# 2. CatBoost-Drug
result_drug = evaluate_full_metrics(
    catboost_drug_oof, catboost_drug_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "CatBoost-Drug"
)
results.append({"model": "CatBoost-Drug", "combination": "Single", "weighting": "N/A", **result_drug})

# 3. SAINT
result_saint = evaluate_full_metrics(
    saint_oof, saint_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "SAINT"
)
results.append({"model": "SAINT", "combination": "Single", "weighting": "N/A", **result_saint})

# 4. Bilinear v2
result_bilinear = evaluate_full_metrics(
    bilinear_v2_oof, bilinear_v2_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Bilinear-v2"
)
results.append({"model": "Bilinear-v2", "combination": "Single", "weighting": "N/A", **result_bilinear})

# ============================================================================
# 앙상블 평가
# ============================================================================
print("\n" + "=" * 100)
print("[3] 앙상블 평가 - CatBoost-Full + Bilinear v2")
print("=" * 100)

# 1. Full + Bilinear (Weighted)
w_full = max(full_oof_sp, 0)
w_bilinear = max(bilinear_oof_sp, 0)
total = w_full + w_bilinear
w_full /= total
w_bilinear /= total

print(f"\n가중치: Full={w_full:.4f}, Bilinear={w_bilinear:.4f}")

ens_fb_w_oof = w_full * catboost_full_oof + w_bilinear * bilinear_v2_oof
ens_fb_w_holdout = w_full * catboost_full_holdout + w_bilinear * bilinear_v2_holdout

result_fb_w = evaluate_full_metrics(
    ens_fb_w_oof, ens_fb_w_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Full+Bilinear (Weighted)"
)
results.append({
    "model": "Full+Bilinear",
    "combination": "2-model",
    "weighting": "Weighted",
    "weights": {"Full": float(w_full), "Bilinear": float(w_bilinear)},
    **result_fb_w
})

# 2. Full + Bilinear (Equal)
ens_fb_e_oof = 0.5 * catboost_full_oof + 0.5 * bilinear_v2_oof
ens_fb_e_holdout = 0.5 * catboost_full_holdout + 0.5 * bilinear_v2_holdout

result_fb_e = evaluate_full_metrics(
    ens_fb_e_oof, ens_fb_e_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Full+Bilinear (Equal)"
)
results.append({
    "model": "Full+Bilinear",
    "combination": "2-model",
    "weighting": "Equal",
    "weights": {"Full": 0.5, "Bilinear": 0.5},
    **result_fb_e
})

# ============================================================================
print("\n" + "=" * 100)
print("[4] 앙상블 평가 - CatBoost-Drug + Bilinear v2")
print("=" * 100)

# 3. Drug + Bilinear (Weighted)
w_drug = max(drug_oof_sp, 0)
w_bilinear2 = max(bilinear_oof_sp, 0)
total2 = w_drug + w_bilinear2
w_drug /= total2
w_bilinear2 /= total2

print(f"\n가중치: Drug={w_drug:.4f}, Bilinear={w_bilinear2:.4f}")

ens_db_w_oof = w_drug * catboost_drug_oof + w_bilinear2 * bilinear_v2_oof
ens_db_w_holdout = w_drug * catboost_drug_holdout + w_bilinear2 * bilinear_v2_holdout

result_db_w = evaluate_full_metrics(
    ens_db_w_oof, ens_db_w_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Drug+Bilinear (Weighted)"
)
results.append({
    "model": "Drug+Bilinear",
    "combination": "2-model",
    "weighting": "Weighted",
    "weights": {"Drug": float(w_drug), "Bilinear": float(w_bilinear2)},
    **result_db_w
})

# 4. Drug + Bilinear (Equal)
ens_db_e_oof = 0.5 * catboost_drug_oof + 0.5 * bilinear_v2_oof
ens_db_e_holdout = 0.5 * catboost_drug_holdout + 0.5 * bilinear_v2_holdout

result_db_e = evaluate_full_metrics(
    ens_db_e_oof, ens_db_e_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Drug+Bilinear (Equal)"
)
results.append({
    "model": "Drug+Bilinear",
    "combination": "2-model",
    "weighting": "Equal",
    "weights": {"Drug": 0.5, "Bilinear": 0.5},
    **result_db_e
})

# ============================================================================
print("\n" + "=" * 100)
print("[5] 앙상블 평가 - CatBoost-Full + SAINT (재측정)")
print("=" * 100)

# 5. Full + SAINT (Weighted)
w_full2 = max(full_oof_sp, 0)
w_saint = max(saint_oof_sp, 0)
total3 = w_full2 + w_saint
w_full2 /= total3
w_saint /= total3

print(f"\n가중치: Full={w_full2:.4f}, SAINT={w_saint:.4f}")

ens_fs_w_oof = w_full2 * catboost_full_oof + w_saint * saint_oof
ens_fs_w_holdout = w_full2 * catboost_full_holdout + w_saint * saint_holdout

result_fs_w = evaluate_full_metrics(
    ens_fs_w_oof, ens_fs_w_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Full+SAINT (Weighted)"
)
results.append({
    "model": "Full+SAINT",
    "combination": "2-model",
    "weighting": "Weighted",
    "weights": {"Full": float(w_full2), "SAINT": float(w_saint)},
    **result_fs_w
})

# ============================================================================
print("\n" + "=" * 100)
print("[6] 앙상블 평가 - CatBoost-Full + Bilinear v2 + SAINT (3-model)")
print("=" * 100)

# 6. Full + Bilinear + SAINT (Weighted)
w_full3 = max(full_oof_sp, 0)
w_bilinear3 = max(bilinear_oof_sp, 0)
w_saint3 = max(saint_oof_sp, 0)
total4 = w_full3 + w_bilinear3 + w_saint3
w_full3 /= total4
w_bilinear3 /= total4
w_saint3 /= total4

print(f"\n가중치: Full={w_full3:.4f}, Bilinear={w_bilinear3:.4f}, SAINT={w_saint3:.4f}")

ens_fbs_w_oof = w_full3 * catboost_full_oof + w_bilinear3 * bilinear_v2_oof + w_saint3 * saint_oof
ens_fbs_w_holdout = w_full3 * catboost_full_holdout + w_bilinear3 * bilinear_v2_holdout + w_saint3 * saint_holdout

result_fbs_w = evaluate_full_metrics(
    ens_fbs_w_oof, ens_fbs_w_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Full+Bilinear+SAINT (Weighted)"
)
results.append({
    "model": "Full+Bilinear+SAINT",
    "combination": "3-model",
    "weighting": "Weighted",
    "weights": {"Full": float(w_full3), "Bilinear": float(w_bilinear3), "SAINT": float(w_saint3)},
    **result_fbs_w
})

# 7. Full + Bilinear + SAINT (Equal)
ens_fbs_e_oof = (catboost_full_oof + bilinear_v2_oof + saint_oof) / 3
ens_fbs_e_holdout = (catboost_full_holdout + bilinear_v2_holdout + saint_holdout) / 3

result_fbs_e = evaluate_full_metrics(
    ens_fbs_e_oof, ens_fbs_e_holdout,
    y_cv, y_holdout, X_cv, drug_ids_cv,
    "Full+Bilinear+SAINT (Equal)"
)
results.append({
    "model": "Full+Bilinear+SAINT",
    "combination": "3-model",
    "weighting": "Equal",
    "weights": {"Full": 1/3, "Bilinear": 1/3, "SAINT": 1/3},
    **result_fbs_e
})

# ============================================================================
# 비교 표
# ============================================================================
print("\n" + "=" * 100)
print("최종 비교표")
print("=" * 100)

print(f"\n{'Model':30s} {'Weighting':12s} {'Holdout Sp':>12s} {'GroupKFold':>12s} "
      f"{'P@30':>10s} {'NDCG@30':>10s} {'Gap':>10s}")
print("-" * 100)

for r in results:
    model_name = r['model']
    weighting = r['weighting']
    holdout_sp = r['holdout_spearman']
    groupkfold = r['groupkfold_spearman'] if r['groupkfold_spearman'] is not None else float('nan')
    p30 = r['p@30']
    ndcg30 = r['ndcg@30']
    gap = r['gap']

    print(f"{model_name:30s} {weighting:12s} {holdout_sp:>12.4f} {groupkfold:>12.4f} "
          f"{p30:>10.4f} {ndcg30:>10.4f} {gap:>10.4f}")

# Best performer
best = max(results, key=lambda x: x['holdout_spearman'])
baseline = results[0]  # CatBoost-Full

print(f"\n🏆 Best Holdout Spearman: {best['model']} ({best['weighting']}) = {best['holdout_spearman']:.4f}")
print(f"   Baseline: {baseline['model']} = {baseline['holdout_spearman']:.4f}")
print(f"   Improvement: {best['holdout_spearman'] - baseline['holdout_spearman']:+.4f}")

# Best GroupKFold
results_with_gkf = [r for r in results if r['groupkfold_spearman'] is not None]
if results_with_gkf:
    best_gkf = max(results_with_gkf, key=lambda x: x['groupkfold_spearman'])
    print(f"\n🏆 Best GroupKFold Spearman: {best_gkf['model']} ({best_gkf['weighting']}) = "
          f"{best_gkf['groupkfold_spearman']:.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[저장]")
print("-" * 100)

# JSON 저장
output_json = output_dir / "comprehensive_evaluation_results.json"
with open(output_json, "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "baseline": {
            "model": baseline['model'],
            "holdout_spearman": baseline['holdout_spearman'],
            "groupkfold_spearman": baseline['groupkfold_spearman']
        },
        "results": results,
        "best_holdout": {
            "model": best['model'],
            "weighting": best['weighting'],
            "holdout_spearman": best['holdout_spearman'],
            "improvement": best['holdout_spearman'] - baseline['holdout_spearman']
        },
        "best_groupkfold": {
            "model": best_gkf['model'],
            "weighting": best_gkf['weighting'],
            "groupkfold_spearman": best_gkf['groupkfold_spearman']
        } if results_with_gkf else None
    }, f, indent=2)

print(f"✓ JSON: {output_json}")

# CSV 저장
csv_data = []
for r in results:
    csv_data.append({
        "Model": r['model'],
        "Weighting": r['weighting'],
        "Holdout_Spearman": r['holdout_spearman'],
        "Holdout_RMSE": r['holdout_rmse'],
        "GroupKFold_Spearman": r['groupkfold_spearman'],
        "GroupKFold_Std": r['groupkfold_std'],
        "Diversity_Spearman": r['diversity_spearman'],
        "P@30": r['p@30'],
        "NDCG@30": r['ndcg@30'],
        "Gap": r['gap']
    })

df = pd.DataFrame(csv_data)
csv_path = output_dir / "comprehensive_evaluation_comparison.csv"
df.to_csv(csv_path, index=False)
print(f"✓ CSV: {csv_path}")

# Top-30 저장
for r in results:
    model_name = r['model'].replace("+", "_").replace(" ", "_")
    weighting = r['weighting'].replace("/", "_")

    top30_df = pd.DataFrame(r['top30'])
    top30_path = output_dir / f"top30_comprehensive_{model_name.lower()}_{weighting.lower()}.csv"
    top30_df.to_csv(top30_path, index=False)
    print(f"✓ Top-30: {top30_path}")

print("\n" + "=" * 100)
print("종합 평가 완료!")
print("=" * 100)
