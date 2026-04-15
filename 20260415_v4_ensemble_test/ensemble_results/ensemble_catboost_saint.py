#!/usr/bin/env python3
"""
CatBoost + SAINT 앙상블 평가

비교:
1. CatBoost 단독
2. CatBoost + SAINT (Spearman 가중치)
3. CatBoost + SAINT (Equal 가중치)
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, ndcg_score
from pathlib import Path
import json
from datetime import datetime

base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
saint_dir = base_dir / "20260415_v4_ensemble_test/new_models/saint"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 100)
print("CatBoost + SAINT 앙상블 평가")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[데이터 로드]")
print("-" * 100)

# OOF predictions
catboost_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
saint_oof = np.load(saint_dir / "saint_oof.npy")

# Holdout predictions
catboost_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")
saint_holdout = np.load(saint_dir / "saint_holdout.npy")

# Ground truth (use shuffled split with seed=42, same as train_all_models.py)
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

print(f"CatBoost OOF shape:    {catboost_oof.shape}")
print(f"SAINT OOF shape:       {saint_oof.shape}")
print(f"CatBoost Holdout shape: {catboost_holdout.shape}")
print(f"SAINT Holdout shape:    {saint_holdout.shape}")
print(f"y_cv shape:            {y_cv.shape}")
print(f"y_holdout shape:       {y_holdout.shape}")

# ============================================================================
# 메트릭 함수
# ============================================================================
def precision_at_k(y_true, y_pred, k=30):
    """Precision@K: top-k 예측 중 실제 top-k와 겹치는 비율"""
    top_k_true = set(np.argsort(y_true)[:k])
    top_k_pred = set(np.argsort(y_pred)[:k])
    return len(top_k_true & top_k_pred) / k

def ndcg_at_k(y_true, y_pred, k=30):
    """NDCG@K"""
    # argsort로 ranking 생성
    true_ranking = np.argsort(np.argsort(y_true))  # 0이 최고
    pred_ranking = np.argsort(np.argsort(y_pred))

    # Top-k만 추출
    top_k_idx = np.argsort(y_pred)[:k]

    # Relevance scores (낮은 IC50 = 높은 relevance)
    # IC50가 낮을수록 좋으므로, max - value로 변환
    relevance = np.max(y_true) - y_true

    y_true_topk = relevance[top_k_idx].reshape(1, -1)
    y_pred_topk = (np.max(y_pred) - y_pred)[top_k_idx].reshape(1, -1)

    # NDCG 계산
    ndcg = ndcg_score(y_true_topk, y_pred_topk)
    return ndcg

def evaluate_predictions(y_true, y_pred, name="Model"):
    """예측 평가"""
    spearman = spearmanr(y_true, y_pred)[0]
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    p30 = precision_at_k(y_true, y_pred, k=30)
    ndcg30 = ndcg_at_k(y_true, y_pred, k=30)

    return {
        "name": name,
        "spearman": float(spearman),
        "rmse": float(rmse),
        "p@30": float(p30),
        "ndcg@30": float(ndcg30)
    }

def get_top30_drugs(y_pred, name="Model"):
    """Top-30 약물 목록 (인덱스 기준)"""
    top30_idx = np.argsort(y_pred)[:30]

    drugs = []
    for rank, idx in enumerate(top30_idx, 1):
        drugs.append({
            "rank": rank,
            "sample_idx": int(idx),
            "predicted_ic50": float(y_pred[idx])
        })

    return drugs

# ============================================================================
# 모델별 성능 평가
# ============================================================================
print("\n[모델별 성능 평가]")
print("-" * 100)

results = []

# 1. CatBoost 단독
print("\n1. CatBoost 단독")
catboost_oof_metrics = evaluate_predictions(y_cv, catboost_oof, "CatBoost (OOF)")
catboost_holdout_metrics = evaluate_predictions(y_holdout, catboost_holdout, "CatBoost (Holdout)")

print(f"  OOF Spearman:     {catboost_oof_metrics['spearman']:.4f}")
print(f"  OOF RMSE:         {catboost_oof_metrics['rmse']:.4f}")
print(f"  OOF P@30:         {catboost_oof_metrics['p@30']:.4f}")
print(f"  OOF NDCG@30:      {catboost_oof_metrics['ndcg@30']:.4f}")
print(f"  Holdout Spearman: {catboost_holdout_metrics['spearman']:.4f}")
print(f"  Holdout RMSE:     {catboost_holdout_metrics['rmse']:.4f}")
print(f"  Holdout P@30:     {catboost_holdout_metrics['p@30']:.4f}")
print(f"  Holdout NDCG@30:  {catboost_holdout_metrics['ndcg@30']:.4f}")

catboost_top30_oof = get_top30_drugs(catboost_oof, "CatBoost_OOF")
catboost_top30_holdout = get_top30_drugs(catboost_holdout, "CatBoost_Holdout")

results.append({
    "model": "CatBoost",
    "weighting": "N/A",
    "oof_metrics": catboost_oof_metrics,
    "holdout_metrics": catboost_holdout_metrics,
    "top30_oof": catboost_top30_oof,
    "top30_holdout": catboost_top30_holdout
})

# 2. CatBoost + SAINT (Spearman 가중치)
print("\n2. CatBoost + SAINT (Spearman 가중치)")

# OOF Spearman으로 가중치 계산
catboost_oof_sp = catboost_oof_metrics['spearman']
saint_oof_sp = spearmanr(y_cv, saint_oof)[0]

# 양수 정규화
w_catboost = max(catboost_oof_sp, 0)
w_saint = max(saint_oof_sp, 0)
total_weight = w_catboost + w_saint

if total_weight > 0:
    w_catboost /= total_weight
    w_saint /= total_weight
else:
    w_catboost = 0.5
    w_saint = 0.5

print(f"  가중치: CatBoost={w_catboost:.4f}, SAINT={w_saint:.4f}")

# 앙상블 예측
ensemble_spw_oof = w_catboost * catboost_oof + w_saint * saint_oof
ensemble_spw_holdout = w_catboost * catboost_holdout + w_saint * saint_holdout

ensemble_spw_oof_metrics = evaluate_predictions(y_cv, ensemble_spw_oof, "Ensemble_SpW (OOF)")
ensemble_spw_holdout_metrics = evaluate_predictions(y_holdout, ensemble_spw_holdout, "Ensemble_SpW (Holdout)")

print(f"  OOF Spearman:     {ensemble_spw_oof_metrics['spearman']:.4f}")
print(f"  OOF RMSE:         {ensemble_spw_oof_metrics['rmse']:.4f}")
print(f"  OOF P@30:         {ensemble_spw_oof_metrics['p@30']:.4f}")
print(f"  OOF NDCG@30:      {ensemble_spw_oof_metrics['ndcg@30']:.4f}")
print(f"  Holdout Spearman: {ensemble_spw_holdout_metrics['spearman']:.4f}")
print(f"  Holdout RMSE:     {ensemble_spw_holdout_metrics['rmse']:.4f}")
print(f"  Holdout P@30:     {ensemble_spw_holdout_metrics['p@30']:.4f}")
print(f"  Holdout NDCG@30:  {ensemble_spw_holdout_metrics['ndcg@30']:.4f}")

ensemble_spw_top30_oof = get_top30_drugs(ensemble_spw_oof, "Ensemble_SpW_OOF")
ensemble_spw_top30_holdout = get_top30_drugs(ensemble_spw_holdout, "Ensemble_SpW_Holdout")

results.append({
    "model": "CatBoost + SAINT",
    "weighting": "Spearman",
    "weights": {"catboost": float(w_catboost), "saint": float(w_saint)},
    "oof_metrics": ensemble_spw_oof_metrics,
    "holdout_metrics": ensemble_spw_holdout_metrics,
    "top30_oof": ensemble_spw_top30_oof,
    "top30_holdout": ensemble_spw_top30_holdout
})

# 3. CatBoost + SAINT (Equal 가중치)
print("\n3. CatBoost + SAINT (Equal 가중치)")

w_equal = 0.5
print(f"  가중치: CatBoost={w_equal:.4f}, SAINT={w_equal:.4f}")

ensemble_eq_oof = w_equal * catboost_oof + w_equal * saint_oof
ensemble_eq_holdout = w_equal * catboost_holdout + w_equal * saint_holdout

ensemble_eq_oof_metrics = evaluate_predictions(y_cv, ensemble_eq_oof, "Ensemble_Equal (OOF)")
ensemble_eq_holdout_metrics = evaluate_predictions(y_holdout, ensemble_eq_holdout, "Ensemble_Equal (Holdout)")

print(f"  OOF Spearman:     {ensemble_eq_oof_metrics['spearman']:.4f}")
print(f"  OOF RMSE:         {ensemble_eq_oof_metrics['rmse']:.4f}")
print(f"  OOF P@30:         {ensemble_eq_oof_metrics['p@30']:.4f}")
print(f"  OOF NDCG@30:      {ensemble_eq_oof_metrics['ndcg@30']:.4f}")
print(f"  Holdout Spearman: {ensemble_eq_holdout_metrics['spearman']:.4f}")
print(f"  Holdout RMSE:     {ensemble_eq_holdout_metrics['rmse']:.4f}")
print(f"  Holdout P@30:     {ensemble_eq_holdout_metrics['p@30']:.4f}")
print(f"  Holdout NDCG@30:  {ensemble_eq_holdout_metrics['ndcg@30']:.4f}")

ensemble_eq_top30_oof = get_top30_drugs(ensemble_eq_oof, "Ensemble_Equal_OOF")
ensemble_eq_top30_holdout = get_top30_drugs(ensemble_eq_holdout, "Ensemble_Equal_Holdout")

results.append({
    "model": "CatBoost + SAINT",
    "weighting": "Equal",
    "weights": {"catboost": float(w_equal), "saint": float(w_equal)},
    "oof_metrics": ensemble_eq_oof_metrics,
    "holdout_metrics": ensemble_eq_holdout_metrics,
    "top30_oof": ensemble_eq_top30_oof,
    "top30_holdout": ensemble_eq_top30_holdout
})

# ============================================================================
# 비교 표
# ============================================================================
print("\n" + "=" * 100)
print("성능 비교표")
print("=" * 100)

print("\n[OOF Performance]")
print(f"{'Model':30s} {'Weighting':15s} {'Spearman':>12s} {'RMSE':>12s} {'P@30':>12s} {'NDCG@30':>12s}")
print("-" * 100)
for r in results:
    model_name = r['model']
    weighting = r['weighting']
    metrics = r['oof_metrics']
    print(f"{model_name:30s} {weighting:15s} {metrics['spearman']:>12.4f} {metrics['rmse']:>12.4f} "
          f"{metrics['p@30']:>12.4f} {metrics['ndcg@30']:>12.4f}")

print("\n[Holdout Performance]")
print(f"{'Model':30s} {'Weighting':15s} {'Spearman':>12s} {'RMSE':>12s} {'P@30':>12s} {'NDCG@30':>12s}")
print("-" * 100)
for r in results:
    model_name = r['model']
    weighting = r['weighting']
    metrics = r['holdout_metrics']
    print(f"{model_name:30s} {weighting:15s} {metrics['spearman']:>12.4f} {metrics['rmse']:>12.4f} "
          f"{metrics['p@30']:>12.4f} {metrics['ndcg@30']:>12.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[저장]")
print("-" * 100)

# JSON 결과
output_json = output_dir / "ensemble_catboost_saint_results.json"
with open(output_json, "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "models": ["CatBoost", "SAINT"],
        "results": results,
        "summary": {
            "best_oof_spearman": max(r['oof_metrics']['spearman'] for r in results),
            "best_holdout_spearman": max(r['holdout_metrics']['spearman'] for r in results)
        }
    }, f, indent=2)

print(f"✓ JSON: {output_json}")

# CSV 비교표
comparison_data = []
for r in results:
    comparison_data.append({
        "Model": r['model'],
        "Weighting": r['weighting'],
        "OOF_Spearman": r['oof_metrics']['spearman'],
        "OOF_RMSE": r['oof_metrics']['rmse'],
        "OOF_P@30": r['oof_metrics']['p@30'],
        "OOF_NDCG@30": r['oof_metrics']['ndcg@30'],
        "Holdout_Spearman": r['holdout_metrics']['spearman'],
        "Holdout_RMSE": r['holdout_metrics']['rmse'],
        "Holdout_P@30": r['holdout_metrics']['p@30'],
        "Holdout_NDCG@30": r['holdout_metrics']['ndcg@30']
    })

df_comparison = pd.DataFrame(comparison_data)
csv_path = output_dir / "ensemble_catboost_saint_comparison.csv"
df_comparison.to_csv(csv_path, index=False)
print(f"✓ CSV: {csv_path}")

# Top-30 약물 목록 (각 조합별)
for r in results:
    model_name = r['model'].replace(" ", "_").replace("+", "")
    weighting = r['weighting'].replace("/", "_")  # Fix invalid filename chars

    # OOF Top-30
    top30_oof_df = pd.DataFrame(r['top30_oof'])
    top30_oof_path = output_dir / f"top30_{model_name}_{weighting}_oof.csv"
    top30_oof_df.to_csv(top30_oof_path, index=False)
    print(f"✓ Top-30 OOF: {top30_oof_path}")

    # Holdout Top-30
    top30_holdout_df = pd.DataFrame(r['top30_holdout'])
    top30_holdout_path = output_dir / f"top30_{model_name}_{weighting}_holdout.csv"
    top30_holdout_df.to_csv(top30_holdout_path, index=False)
    print(f"✓ Top-30 Holdout: {top30_holdout_path}")

print("\n" + "=" * 100)
print("앙상블 평가 완료!")
print("=" * 100)
