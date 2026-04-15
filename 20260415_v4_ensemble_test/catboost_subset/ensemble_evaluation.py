#!/usr/bin/env python3
"""
CatBoost Feature Subset 앙상블 평가

조합:
1. CatBoost-Full 단독 (baseline)
2. CatBoost-Full + CatBoost-Gene (2-model)
3. CatBoost-Full + CatBoost-Drug (2-model)
4. CatBoost-Full + CatBoost-Gene + CatBoost-Drug (3-model)

각 조합별 Weighted + Equal 가중치
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
subset_dir = base_dir / "20260415_v4_ensemble_test/catboost_subset"
output_dir = subset_dir / "ensemble"

print("=" * 100)
print("CatBoost Feature Subset 앙상블 평가")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# OOF
catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
catboost_gene_oof = np.load(subset_dir / "catboost_gene/catboost_gene_oof.npy")
catboost_drug_oof = np.load(subset_dir / "catboost_drug/catboost_drug_oof.npy")

# Holdout
catboost_full_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")
catboost_gene_holdout = np.load(subset_dir / "catboost_gene/catboost_gene_holdout.npy")
catboost_drug_holdout = np.load(subset_dir / "catboost_drug/catboost_drug_holdout.npy")

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

print(f"y_cv shape: {y_cv.shape}")
print(f"y_holdout shape: {y_holdout.shape}")

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
    true_ranking = np.argsort(np.argsort(y_true))
    pred_ranking = np.argsort(np.argsort(y_pred))
    top_k_idx = np.argsort(y_pred)[:k]
    relevance = np.max(y_true) - y_true
    y_true_topk = relevance[top_k_idx].reshape(1, -1)
    y_pred_topk = (np.max(y_pred) - y_pred)[top_k_idx].reshape(1, -1)
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

# ============================================================================
# 앙상블 조합 평가
# ============================================================================
print("\n[2] 앙상블 조합 평가")
print("-" * 100)

results = []

# OOF Spearman (for weighted ensemble)
full_oof_sp = spearmanr(y_cv, catboost_full_oof)[0]
gene_oof_sp = spearmanr(y_cv, catboost_gene_oof)[0]
drug_oof_sp = spearmanr(y_cv, catboost_drug_oof)[0]

print(f"OOF Spearman: Full={full_oof_sp:.4f}, Gene={gene_oof_sp:.4f}, Drug={drug_oof_sp:.4f}")

# 1. CatBoost-Full 단독 (baseline)
print("\n1. CatBoost-Full 단독 (baseline)")
full_oof_metrics = evaluate_predictions(y_cv, catboost_full_oof, "Full_OOF")
full_holdout_metrics = evaluate_predictions(y_holdout, catboost_full_holdout, "Full_Holdout")

print(f"  OOF Spearman:     {full_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {full_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full",
    "models": ["CatBoost-Full"],
    "weighting": "N/A",
    "weights": {"Full": 1.0},
    "oof_metrics": full_oof_metrics,
    "holdout_metrics": full_holdout_metrics,
    "top30_oof": get_top30_drugs(catboost_full_oof, "Full_OOF"),
    "top30_holdout": get_top30_drugs(catboost_full_holdout, "Full_Holdout")
})

# 2. Full + Gene (Weighted)
print("\n2. CatBoost-Full + CatBoost-Gene (Weighted)")
w_full = max(full_oof_sp, 0)
w_gene = max(gene_oof_sp, 0)
total = w_full + w_gene
w_full /= total
w_gene /= total

print(f"  가중치: Full={w_full:.4f}, Gene={w_gene:.4f}")

ensemble_fg_w_oof = w_full * catboost_full_oof + w_gene * catboost_gene_oof
ensemble_fg_w_holdout = w_full * catboost_full_holdout + w_gene * catboost_gene_holdout

fg_w_oof_metrics = evaluate_predictions(y_cv, ensemble_fg_w_oof, "Full+Gene_Weighted_OOF")
fg_w_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fg_w_holdout, "Full+Gene_Weighted_Holdout")

print(f"  OOF Spearman:     {fg_w_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fg_w_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Gene",
    "models": ["CatBoost-Full", "CatBoost-Gene"],
    "weighting": "Weighted",
    "weights": {"Full": float(w_full), "Gene": float(w_gene)},
    "oof_metrics": fg_w_oof_metrics,
    "holdout_metrics": fg_w_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fg_w_oof),
    "top30_holdout": get_top30_drugs(ensemble_fg_w_holdout)
})

# 3. Full + Gene (Equal)
print("\n3. CatBoost-Full + CatBoost-Gene (Equal)")
ensemble_fg_e_oof = 0.5 * catboost_full_oof + 0.5 * catboost_gene_oof
ensemble_fg_e_holdout = 0.5 * catboost_full_holdout + 0.5 * catboost_gene_holdout

fg_e_oof_metrics = evaluate_predictions(y_cv, ensemble_fg_e_oof, "Full+Gene_Equal_OOF")
fg_e_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fg_e_holdout, "Full+Gene_Equal_Holdout")

print(f"  OOF Spearman:     {fg_e_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fg_e_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Gene",
    "models": ["CatBoost-Full", "CatBoost-Gene"],
    "weighting": "Equal",
    "weights": {"Full": 0.5, "Gene": 0.5},
    "oof_metrics": fg_e_oof_metrics,
    "holdout_metrics": fg_e_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fg_e_oof),
    "top30_holdout": get_top30_drugs(ensemble_fg_e_holdout)
})

# 4. Full + Drug (Weighted)
print("\n4. CatBoost-Full + CatBoost-Drug (Weighted)")
w_full2 = max(full_oof_sp, 0)
w_drug = max(drug_oof_sp, 0)
total2 = w_full2 + w_drug
w_full2 /= total2
w_drug /= total2

print(f"  가중치: Full={w_full2:.4f}, Drug={w_drug:.4f}")

ensemble_fd_w_oof = w_full2 * catboost_full_oof + w_drug * catboost_drug_oof
ensemble_fd_w_holdout = w_full2 * catboost_full_holdout + w_drug * catboost_drug_holdout

fd_w_oof_metrics = evaluate_predictions(y_cv, ensemble_fd_w_oof, "Full+Drug_Weighted_OOF")
fd_w_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fd_w_holdout, "Full+Drug_Weighted_Holdout")

print(f"  OOF Spearman:     {fd_w_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fd_w_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Drug",
    "models": ["CatBoost-Full", "CatBoost-Drug"],
    "weighting": "Weighted",
    "weights": {"Full": float(w_full2), "Drug": float(w_drug)},
    "oof_metrics": fd_w_oof_metrics,
    "holdout_metrics": fd_w_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fd_w_oof),
    "top30_holdout": get_top30_drugs(ensemble_fd_w_holdout)
})

# 5. Full + Drug (Equal)
print("\n5. CatBoost-Full + CatBoost-Drug (Equal)")
ensemble_fd_e_oof = 0.5 * catboost_full_oof + 0.5 * catboost_drug_oof
ensemble_fd_e_holdout = 0.5 * catboost_full_holdout + 0.5 * catboost_drug_holdout

fd_e_oof_metrics = evaluate_predictions(y_cv, ensemble_fd_e_oof, "Full+Drug_Equal_OOF")
fd_e_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fd_e_holdout, "Full+Drug_Equal_Holdout")

print(f"  OOF Spearman:     {fd_e_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fd_e_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Drug",
    "models": ["CatBoost-Full", "CatBoost-Drug"],
    "weighting": "Equal",
    "weights": {"Full": 0.5, "Drug": 0.5},
    "oof_metrics": fd_e_oof_metrics,
    "holdout_metrics": fd_e_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fd_e_oof),
    "top30_holdout": get_top30_drugs(ensemble_fd_e_holdout)
})

# 6. Full + Gene + Drug (Weighted)
print("\n6. CatBoost-Full + CatBoost-Gene + CatBoost-Drug (Weighted)")
w_full3 = max(full_oof_sp, 0)
w_gene3 = max(gene_oof_sp, 0)
w_drug3 = max(drug_oof_sp, 0)
total3 = w_full3 + w_gene3 + w_drug3
w_full3 /= total3
w_gene3 /= total3
w_drug3 /= total3

print(f"  가중치: Full={w_full3:.4f}, Gene={w_gene3:.4f}, Drug={w_drug3:.4f}")

ensemble_fgd_w_oof = w_full3 * catboost_full_oof + w_gene3 * catboost_gene_oof + w_drug3 * catboost_drug_oof
ensemble_fgd_w_holdout = w_full3 * catboost_full_holdout + w_gene3 * catboost_gene_holdout + w_drug3 * catboost_drug_holdout

fgd_w_oof_metrics = evaluate_predictions(y_cv, ensemble_fgd_w_oof, "Full+Gene+Drug_Weighted_OOF")
fgd_w_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fgd_w_holdout, "Full+Gene+Drug_Weighted_Holdout")

print(f"  OOF Spearman:     {fgd_w_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fgd_w_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Gene+Drug",
    "models": ["CatBoost-Full", "CatBoost-Gene", "CatBoost-Drug"],
    "weighting": "Weighted",
    "weights": {"Full": float(w_full3), "Gene": float(w_gene3), "Drug": float(w_drug3)},
    "oof_metrics": fgd_w_oof_metrics,
    "holdout_metrics": fgd_w_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fgd_w_oof),
    "top30_holdout": get_top30_drugs(ensemble_fgd_w_holdout)
})

# 7. Full + Gene + Drug (Equal)
print("\n7. CatBoost-Full + CatBoost-Gene + CatBoost-Drug (Equal)")
ensemble_fgd_e_oof = (catboost_full_oof + catboost_gene_oof + catboost_drug_oof) / 3
ensemble_fgd_e_holdout = (catboost_full_holdout + catboost_gene_holdout + catboost_drug_holdout) / 3

fgd_e_oof_metrics = evaluate_predictions(y_cv, ensemble_fgd_e_oof, "Full+Gene+Drug_Equal_OOF")
fgd_e_holdout_metrics = evaluate_predictions(y_holdout, ensemble_fgd_e_holdout, "Full+Gene+Drug_Equal_Holdout")

print(f"  OOF Spearman:     {fgd_e_oof_metrics['spearman']:.4f}")
print(f"  Holdout Spearman: {fgd_e_holdout_metrics['spearman']:.4f}")

results.append({
    "combination": "Full+Gene+Drug",
    "models": ["CatBoost-Full", "CatBoost-Gene", "CatBoost-Drug"],
    "weighting": "Equal",
    "weights": {"Full": 1/3, "Gene": 1/3, "Drug": 1/3},
    "oof_metrics": fgd_e_oof_metrics,
    "holdout_metrics": fgd_e_holdout_metrics,
    "top30_oof": get_top30_drugs(ensemble_fgd_e_oof),
    "top30_holdout": get_top30_drugs(ensemble_fgd_e_holdout)
})

# ============================================================================
# 비교 표
# ============================================================================
print("\n" + "=" * 100)
print("성능 비교표")
print("=" * 100)

print("\n[OOF Performance]")
print(f"{'Combination':25s} {'Weighting':15s} {'Spearman':>12s} {'RMSE':>12s} {'P@30':>12s} {'NDCG@30':>12s}")
print("-" * 90)
for r in results:
    print(f"{r['combination']:25s} {r['weighting']:15s} "
          f"{r['oof_metrics']['spearman']:>12.4f} {r['oof_metrics']['rmse']:>12.4f} "
          f"{r['oof_metrics']['p@30']:>12.4f} {r['oof_metrics']['ndcg@30']:>12.4f}")

print("\n[Holdout Performance]")
print(f"{'Combination':25s} {'Weighting':15s} {'Spearman':>12s} {'RMSE':>12s} {'P@30':>12s} {'NDCG@30':>12s}")
print("-" * 90)
for r in results:
    print(f"{r['combination']:25s} {r['weighting']:15s} "
          f"{r['holdout_metrics']['spearman']:>12.4f} {r['holdout_metrics']['rmse']:>12.4f} "
          f"{r['holdout_metrics']['p@30']:>12.4f} {r['holdout_metrics']['ndcg@30']:>12.4f}")

# Best performer
best_holdout = max(results, key=lambda x: x['holdout_metrics']['spearman'])
print(f"\n🏆 Best Holdout Spearman: {best_holdout['combination']} ({best_holdout['weighting']}) = "
      f"{best_holdout['holdout_metrics']['spearman']:.4f}")

baseline = results[0]['holdout_metrics']['spearman']
best_value = best_holdout['holdout_metrics']['spearman']
improvement = best_value - baseline

if best_value > baseline:
    print(f"✅ 개선: +{improvement:.4f}")
else:
    print(f"❌ 악화: {improvement:.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[3] 저장")
print("-" * 100)

output_dir.mkdir(parents=True, exist_ok=True)

# ablation_results.json (필수!)
ablation_json = output_dir / "ablation_results.json"
with open(ablation_json, "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "baseline": {"model": "CatBoost-Full", "holdout_spearman": baseline},
        "results": results,
        "best": {
            "combination": best_holdout['combination'],
            "weighting": best_holdout['weighting'],
            "holdout_spearman": best_value,
            "improvement": float(improvement)
        }
    }, f, indent=2)

print(f"✓ JSON: {ablation_json}")

# Top-30 CSV
for r in results:
    comb_name = r['combination'].replace("+", "_")
    weight_name = r['weighting'].replace("/", "_")

    # Holdout Top-30
    top30_df = pd.DataFrame(r['top30_holdout'])
    top30_path = output_dir / f"top30_{comb_name.lower()}_{weight_name.lower()}.csv"
    top30_df.to_csv(top30_path, index=False)
    print(f"✓ Top-30: {top30_path}")

print("\n" + "=" * 100)
print("Phase 3/3 완료: 앙상블 평가 완료")
print("=" * 100)
