#!/usr/bin/env python3
"""
CatBoost Feature Subset 앙상블 실험

학습:
- CatBoost-Gene: Gene block만 4,402개
- CatBoost-Drug: Drug block만 1,127개

기존 CatBoost-Full (v3) OOF 재사용
"""
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import KFold, GroupKFold
from sklearn.metrics import mean_squared_error
from scipy.stats import spearmanr
from catboost import CatBoostRegressor
import json
from datetime import datetime

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_base = base_dir / "20260415_v4_ensemble_test/catboost_subset"

print("=" * 100)
print("CatBoost Feature Subset 앙상블 실험")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# Feature indices
drug_indices = np.load(crossattn_dir / "drug_feature_indices.npy")
gene_indices = np.load(crossattn_dir / "gene_feature_indices.npy")

print(f"Drug features: {len(drug_indices)}")
print(f"Gene features: {len(gene_indices)}")

# X_train, y_train
X_train = np.load(step4_dir / "X_train.npy")
y_train = np.load(step4_dir / "y_train.npy")

print(f"X_train shape: {X_train.shape}")
print(f"y_train shape: {y_train.shape}")

# Train/Holdout split (v3와 동일: seed=42, shuffled 80/20)
n_samples = len(y_train)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

X_cv = X_train[train_idx]
y_cv = y_train[train_idx]
X_holdout = X_train[holdout_idx]
y_holdout = y_train[holdout_idx]

print(f"CV samples: {len(X_cv)}")
print(f"Holdout samples: {len(X_holdout)}")

# Drug IDs for GroupKFold (if available)
try:
    features_slim = pd.read_parquet(step4_dir / "features_slim.parquet")
    drug_ids = features_slim['canonical_drug_id'].values[train_idx]
    print(f"Drug IDs loaded for GroupKFold: {len(np.unique(drug_ids))} unique drugs")
except Exception as e:
    print(f"Warning: Could not load drug IDs: {e}")
    drug_ids = None

# ============================================================================
# 학습 함수
# ============================================================================
def train_catboost_subset(X_subset, y_subset, feature_name, feature_indices, X_holdout_subset, y_holdout_subset):
    """
    CatBoost 학습 (feature subset)

    Args:
        X_subset: CV 데이터 (feature subset)
        y_subset: CV labels
        feature_name: 'Gene' or 'Drug'
        feature_indices: Feature indices
        X_holdout_subset: Holdout 데이터
        y_holdout_subset: Holdout labels
    """
    print(f"\n{'='*100}")
    print(f"CatBoost-{feature_name} 학습 시작")
    print(f"{'='*100}")

    output_dir = output_base / f"catboost_{feature_name.lower()}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nFeature 수: {X_subset.shape[1]}")
    print(f"CV 샘플 수: {len(X_subset)}")
    print(f"Holdout 샘플 수: {len(X_holdout_subset)}")

    # CatBoost 하이퍼파라미터 (v3와 동일)
    params = {
        'iterations': 1000,
        'learning_rate': 0.05,
        'depth': 6,
        'loss_function': 'RMSE',
        'verbose': False,
        'random_seed': 42,
        'thread_count': -1
    }

    # 5-fold CV
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_predictions = np.zeros(len(y_subset))
    train_predictions = np.zeros(len(y_subset))
    fold_train_sps = []
    fold_oof_sps = []
    fold_models = []

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_subset), 1):
        print(f"\nFold {fold_idx}/5:")

        X_tr, X_val = X_subset[tr_idx], X_subset[val_idx]
        y_tr, y_val = y_subset[tr_idx], y_subset[val_idx]

        # 모델 학습
        model = CatBoostRegressor(**params)
        model.fit(X_tr, y_tr, eval_set=(X_val, y_val), early_stopping_rounds=50, verbose=False)

        # 예측
        train_pred = model.predict(X_tr)
        val_pred = model.predict(X_val)

        train_predictions[tr_idx] = train_pred
        oof_predictions[val_idx] = val_pred

        train_sp = spearmanr(y_tr, train_pred)[0]
        val_sp = spearmanr(y_val, val_pred)[0]

        fold_train_sps.append(train_sp)
        fold_oof_sps.append(val_sp)
        fold_models.append(model)

        print(f"  Train Sp: {train_sp:.4f}, OOF Sp: {val_sp:.4f}")

    # 전체 메트릭
    train_sp = np.mean(fold_train_sps)
    oof_sp = spearmanr(y_subset, oof_predictions)[0]
    oof_rmse = np.sqrt(mean_squared_error(y_subset, oof_predictions))
    gap = train_sp - oof_sp
    fold_std = np.std(fold_oof_sps)
    train_val_ratio = train_sp / oof_sp if oof_sp != 0 else 0

    # 과적합 판정
    if gap < 0.05:
        overfitting_verdict = "없음"
    elif gap < 0.10:
        overfitting_verdict = "허용"
    else:
        overfitting_verdict = "주의"

    print(f"\n전체 메트릭:")
    print(f"  Train Spearman: {train_sp:.4f}")
    print(f"  OOF Spearman:   {oof_sp:.4f}")
    print(f"  OOF RMSE:       {oof_rmse:.4f}")
    print(f"  Gap:            {gap:.4f}")
    print(f"  Fold Std:       {fold_std:.4f}")
    print(f"  Train/Val Ratio: {train_val_ratio:.4f}")
    print(f"  과적합 판정:    {overfitting_verdict}")

    # Final model (전체 CV 데이터로)
    print(f"\nFinal model 학습...")
    final_model = CatBoostRegressor(**params)
    final_model.fit(X_subset, y_subset, verbose=False)

    # Holdout 예측
    holdout_pred = final_model.predict(X_holdout_subset)
    holdout_sp = spearmanr(y_holdout_subset, holdout_pred)[0]
    holdout_rmse = np.sqrt(mean_squared_error(y_holdout_subset, holdout_pred))

    print(f"  Holdout Spearman: {holdout_sp:.4f}")
    print(f"  Holdout RMSE:     {holdout_rmse:.4f}")

    # GroupKFold (if drug_ids available)
    groupkfold_sp = None
    if drug_ids is not None:
        print(f"\nGroupKFold (by drug) 평가...")
        gkf = GroupKFold(n_splits=5)
        gkf_predictions = np.zeros(len(y_subset))

        for tr_idx, val_idx in gkf.split(X_subset, y_subset, groups=drug_ids):
            X_tr, X_val = X_subset[tr_idx], X_subset[val_idx]
            y_tr, y_val = y_subset[tr_idx], y_subset[val_idx]

            model_gkf = CatBoostRegressor(**params)
            model_gkf.fit(X_tr, y_tr, verbose=False)
            gkf_predictions[val_idx] = model_gkf.predict(X_val)

        groupkfold_sp = spearmanr(y_subset, gkf_predictions)[0]
        print(f"  GroupKFold Spearman: {groupkfold_sp:.4f}")

    # Unseen Drug 평가 (holdout에서 random 50% drug 제외)
    print(f"\nUnseen Drug 평가...")
    unique_holdout_drugs = np.unique(features_slim['canonical_drug_id'].values[holdout_idx]) if drug_ids is not None else None

    if unique_holdout_drugs is not None and len(unique_holdout_drugs) > 10:
        np.random.seed(42)
        n_unseen = len(unique_holdout_drugs) // 2
        unseen_drugs = np.random.choice(unique_holdout_drugs, size=n_unseen, replace=False)

        holdout_drug_ids = features_slim['canonical_drug_id'].values[holdout_idx]
        unseen_mask = np.isin(holdout_drug_ids, unseen_drugs)

        X_unseen = X_holdout_subset[unseen_mask]
        y_unseen = y_holdout_subset[unseen_mask]

        unseen_pred = final_model.predict(X_unseen)
        unseen_sp = spearmanr(y_unseen, unseen_pred)[0]
        print(f"  Unseen Drug Spearman: {unseen_sp:.4f} ({unseen_mask.sum()}/{len(y_holdout_subset)} samples)")
    else:
        unseen_sp = None
        print(f"  Unseen Drug: Not available (insufficient drug diversity)")

    # ========================================================================
    # 저장
    # ========================================================================
    print(f"\n결과 저장...")

    # 1. Model
    model_path = output_dir / f"catboost_{feature_name.lower()}_model.pkl"
    final_model.save_model(str(model_path))
    print(f"  ✓ Model: {model_path}")

    # 2. OOF predictions (필수!)
    oof_path = output_dir / f"catboost_{feature_name.lower()}_oof.npy"
    np.save(oof_path, oof_predictions)
    print(f"  ✓ OOF: {oof_path} (shape: {oof_predictions.shape})")

    # 3. Holdout predictions (필수!)
    holdout_path = output_dir / f"catboost_{feature_name.lower()}_holdout.npy"
    np.save(holdout_path, holdout_pred)
    print(f"  ✓ Holdout: {holdout_path} (shape: {holdout_pred.shape})")

    # 4. Results (필수!)
    results = {
        "model": f"CatBoost-{feature_name}",
        "timestamp": datetime.now().isoformat(),
        "n_features": X_subset.shape[1],
        "feature_indices": feature_indices.tolist(),
        "hyperparameters": params,
        "metrics": {
            "train_spearman": float(train_sp),
            "oof_spearman": float(oof_sp),
            "oof_rmse": float(oof_rmse),
            "holdout_spearman": float(holdout_sp),
            "holdout_rmse": float(holdout_rmse),
            "gap": float(gap),
            "fold_std": float(fold_std),
            "train_val_ratio": float(train_val_ratio),
            "groupkfold_spearman": float(groupkfold_sp) if groupkfold_sp is not None else None,
            "unseen_drug_spearman": float(unseen_sp) if unseen_sp is not None else None,
            "overfitting_verdict": overfitting_verdict
        },
        "fold_metrics": {
            "fold_train_sps": [float(x) for x in fold_train_sps],
            "fold_oof_sps": [float(x) for x in fold_oof_sps]
        }
    }

    results_path = output_dir / f"catboost_{feature_name.lower()}_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Results: {results_path}")

    print(f"\nCatBoost-{feature_name} 학습 완료!")
    return results

# ============================================================================
# CatBoost-Gene 학습
# ============================================================================
X_cv_gene = X_cv[:, gene_indices]
X_holdout_gene = X_holdout[:, gene_indices]

gene_results = train_catboost_subset(
    X_cv_gene, y_cv, "Gene", gene_indices,
    X_holdout_gene, y_holdout
)

# ============================================================================
# CatBoost-Drug 학습
# ============================================================================
X_cv_drug = X_cv[:, drug_indices]
X_holdout_drug = X_holdout[:, drug_indices]

drug_results = train_catboost_subset(
    X_cv_drug, y_cv, "Drug", drug_indices,
    X_holdout_drug, y_holdout
)

# ============================================================================
# 요약
# ============================================================================
print("\n" + "=" * 100)
print("학습 완료! 단독 성능 비교")
print("=" * 100)

# 비교 테이블
print(f"\n{'Model':20s} {'Feature수':>12s} {'OOF Sp':>10s} {'Train Sp':>10s} {'Gap':>8s} "
      f"{'판정':>8s} {'Holdout Sp':>12s} {'GroupKFold':>12s} {'Unseen Drug':>12s} {'Fold Std':>10s}")
print("-" * 130)

# CatBoost-Full (from v3)
print(f"{'CatBoost-Full':20s} {5529:>12d} {0.8624:>10.4f} {0.9364:>10.4f} {0.074:>8.3f} "
      f"{'허용':>8s} {0.8709:>12.4f} {'N/A':>12s} {'N/A':>12s} {0.0288:>10.4f}")

# CatBoost-Gene
print(f"{'CatBoost-Gene':20s} {gene_results['n_features']:>12d} "
      f"{gene_results['metrics']['oof_spearman']:>10.4f} "
      f"{gene_results['metrics']['train_spearman']:>10.4f} "
      f"{gene_results['metrics']['gap']:>8.3f} "
      f"{gene_results['metrics']['overfitting_verdict']:>8s} "
      f"{gene_results['metrics']['holdout_spearman']:>12.4f} "
      f"{gene_results['metrics']['groupkfold_spearman'] if gene_results['metrics']['groupkfold_spearman'] else 'N/A':>12s} "
      f"{gene_results['metrics']['unseen_drug_spearman'] if gene_results['metrics']['unseen_drug_spearman'] else 'N/A':>12s} "
      f"{gene_results['metrics']['fold_std']:>10.4f}")

# CatBoost-Drug
print(f"{'CatBoost-Drug':20s} {drug_results['n_features']:>12d} "
      f"{drug_results['metrics']['oof_spearman']:>10.4f} "
      f"{drug_results['metrics']['train_spearman']:>10.4f} "
      f"{drug_results['metrics']['gap']:>8.3f} "
      f"{drug_results['metrics']['overfitting_verdict']:>8s} "
      f"{drug_results['metrics']['holdout_spearman']:>12.4f} "
      f"{drug_results['metrics']['groupkfold_spearman'] if drug_results['metrics']['groupkfold_spearman'] else 'N/A':>12s} "
      f"{drug_results['metrics']['unseen_drug_spearman'] if drug_results['metrics']['unseen_drug_spearman'] else 'N/A':>12s} "
      f"{drug_results['metrics']['fold_std']:>10.4f}")

print("\n" + "=" * 100)
print("Phase 1/3 완료: CatBoost-Gene, CatBoost-Drug 학습 완료")
print("=" * 100)
