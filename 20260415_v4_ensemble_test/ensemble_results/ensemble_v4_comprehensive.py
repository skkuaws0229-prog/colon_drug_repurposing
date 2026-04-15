#!/usr/bin/env python3
"""
Step 5 앙상블 — v4 Comprehensive Analysis
CatBoost + FlatMLP + Real CrossAttention
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_absolute_error, median_absolute_error, r2_score
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
crossattn_dir = base_dir / "20260415_v4_ensemble_test/crossattn_reimpl"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

print("=" * 100)
print("Step 5 앙상블 — v4 Comprehensive Analysis")
print("=" * 100)

# ============================================================================
# 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

# OOF predictions
catboost_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
flatmlp_oof = np.load(step4_dir / "model_10_oof.npy")
crossattn_oof = np.load(crossattn_dir / "real_crossattention_oof.npy")

# Holdout predictions
catboost_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")
flatmlp_holdout = np.load(step4_dir / "model_10_holdout.npy")
crossattn_holdout = np.load(crossattn_dir / "real_crossattention_holdout.npy")

# True labels (from X_train, y_train split)
y_train_full = np.load(step4_dir / "y_train.npy")

# Train/Holdout split (같은 방식으로)
n_samples = len(y_train_full)
n_train = int(n_samples * 0.8)
indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

y_cv = y_train_full[train_idx]
y_holdout = y_train_full[holdout_idx]

print(f"CatBoost OOF shape:     {catboost_oof.shape}")
print(f"FlatMLP OOF shape:      {flatmlp_oof.shape}")
print(f"CrossAttention OOF shape: {crossattn_oof.shape}")
print(f"y_cv shape:             {y_cv.shape}")
print(f"\nHoldout samples:        {len(y_holdout)}")

# Drug names 로드 (features_slim.parquet에서)
fe_path = base_dir / "20260414_re_pre_project_v3/features_slim.parquet"
df = pd.read_parquet(fe_path)

# CV indices에 해당하는 drug names
df_cv = df.iloc[train_idx].reset_index(drop=True)
df_holdout = df.iloc[holdout_idx].reset_index(drop=True)

# ============================================================================
# Diversity 분석
# ============================================================================
print("\n[2] Diversity 분석 (3개 모델 간 예측 상관)")
print("-" * 100)

models_oof = {
    'CatBoost': catboost_oof,
    'FlatMLP': flatmlp_oof,
    'CrossAttention': crossattn_oof
}

diversity_matrix = {}
for name1, pred1 in models_oof.items():
    diversity_matrix[name1] = {}
    for name2, pred2 in models_oof.items():
        if name1 == name2:
            diversity_matrix[name1][name2] = 1.0
        else:
            corr = pearsonr(pred1, pred2)[0]
            diversity_matrix[name1][name2] = float(corr)

# 평균 상관 (대각선 제외)
off_diag = []
for i, (name1, pred1) in enumerate(models_oof.items()):
    for j, (name2, pred2) in enumerate(models_oof.items()):
        if i < j:
            off_diag.append(diversity_matrix[name1][name2])

avg_corr = np.mean(off_diag)

print(f"\nPearson 상관 행렬:")
print(f"{'':20s} {'CatBoost':>12s} {'FlatMLP':>12s} {'CrossAttn':>12s}")
for name1 in models_oof.keys():
    values = [diversity_matrix[name1][name2] for name2 in models_oof.keys()]
    print(f"{name1:20s} {values[0]:>12.4f} {values[1]:>12.4f} {values[2]:>12.4f}")

print(f"\n평균 상관 (off-diagonal): {avg_corr:.4f}")

if avg_corr < 0.90:
    diversity_verdict = f"✅ 우수 (< 0.90)"
elif avg_corr < 0.95:
    diversity_verdict = f"⚠️  보통 (0.90 ~ 0.95)"
else:
    diversity_verdict = f"❌ 부족 (≥ 0.95)"

print(f"Diversity 판정: {diversity_verdict}")

# ============================================================================
# 개별 모델 OOF 성능
# ============================================================================
print("\n[3] 개별 모델 OOF 성능")
print("-" * 100)

individual_oof_metrics = {}

for name, pred in models_oof.items():
    sp = spearmanr(y_cv, pred)[0]
    rmse = np.sqrt(np.mean((y_cv - pred) ** 2))
    individual_oof_metrics[name] = {
        'spearman': float(sp),
        'rmse': float(rmse)
    }
    print(f"{name:20s}: Spearman={sp:.4f}, RMSE={rmse:.4f}")

# ============================================================================
# 앙상블 함수
# ============================================================================
def ensemble_predictions(preds_dict, weights=None, method='weighted'):
    """
    앙상블 예측 계산

    Args:
        preds_dict: {model_name: predictions}
        weights: {model_name: weight} or None
        method: 'weighted' or 'equal'
    """
    model_names = list(preds_dict.keys())

    if method == 'equal' or weights is None:
        # Equal weight
        weights = {name: 1.0 / len(model_names) for name in model_names}

    # Weighted average
    ensemble = np.zeros_like(list(preds_dict.values())[0])
    for name, pred in preds_dict.items():
        ensemble += weights[name] * pred

    return ensemble, weights

def calculate_metrics(y_true, y_pred):
    """전체 메트릭 계산"""
    return {
        'spearman': float(spearmanr(y_true, y_pred)[0]),
        'kendall_tau': float(kendalltau(y_true, y_pred)[0]),
        'pearson': float(pearsonr(y_true, y_pred)[0]),
        'r2': float(r2_score(y_true, y_pred)),
        'rmse': float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        'mae': float(mean_absolute_error(y_true, y_pred)),
        'median_ae': float(median_absolute_error(y_true, y_pred)),
        'p95_error': float(np.percentile(np.abs(y_true - y_pred), 95))
    }

def calculate_ranking_metrics(y_true, y_pred, k=30):
    """
    Ranking metrics 계산
    P@k, R@k, NDCG@k, EF@k, MAP
    """
    # Top-k indices
    top_k_pred = np.argsort(y_pred)[:k]
    top_k_true = np.argsort(y_true)[:k]

    # Precision@k
    precision = len(set(top_k_pred) & set(top_k_true)) / k

    # Recall@k (전체 중 몇 개 찾았는지)
    total_relevant = k  # assume top-k as relevant
    recall = len(set(top_k_pred) & set(top_k_true)) / total_relevant

    # NDCG@k
    # DCG
    dcg = 0.0
    for i, idx in enumerate(top_k_pred):
        if idx in top_k_true:
            rank = i + 1
            dcg += 1.0 / np.log2(rank + 1)

    # IDCG
    idcg = sum(1.0 / np.log2(i + 2) for i in range(k))

    ndcg = dcg / idcg if idcg > 0 else 0.0

    # Enrichment Factor@k
    # EF = (hits / k) / (total_actives / total_compounds)
    # Assume top-k as actives
    ef = precision / (k / len(y_true))

    # MAP (Mean Average Precision)
    ap_sum = 0.0
    hits = 0
    for i, idx in enumerate(top_k_pred):
        if idx in top_k_true:
            hits += 1
            ap_sum += hits / (i + 1)
    map_score = ap_sum / k if k > 0 else 0.0

    return {
        f'P@{k}': float(precision),
        f'R@{k}': float(recall),
        f'NDCG@{k}': float(ndcg),
        f'EF@{k}': float(ef),
        'MAP': float(map_score)
    }

def get_top_k_drugs(y_pred, df, k=30):
    """
    Top-k 약물 목록 (rank, drug name, score)
    """
    top_k_idx = np.argsort(y_pred)[:k]

    results = []
    for rank, idx in enumerate(top_k_idx, 1):
        drug_name = df.iloc[idx]['canonical_drug_id'] if 'canonical_drug_id' in df.columns else f"drug_{idx}"
        score = y_pred[idx]
        results.append({
            'rank': rank,
            'drug_name': drug_name,
            'predicted_ic50': float(score)
        })

    return results

# ============================================================================
# 앙상블 조합별 평가
# ============================================================================
print("\n[4] 앙상블 조합별 평가")
print("-" * 100)

# 조합 정의
combinations = {
    '1. CatBoost': ['CatBoost'],
    '2. CatBoost+FlatMLP': ['CatBoost', 'FlatMLP'],
    '3. CatBoost+FlatMLP+CrossAttn': ['CatBoost', 'FlatMLP', 'CrossAttention']
}

# OOF Spearman 기반 가중치 계산
oof_spearman_weights = {}
for name in models_oof.keys():
    sp = individual_oof_metrics[name]['spearman']
    oof_spearman_weights[name] = sp

# 정규화
total_sp = sum(oof_spearman_weights.values())
oof_spearman_weights = {k: v / total_sp for k, v in oof_spearman_weights.items()}

print(f"\nOOF Spearman 기반 가중치:")
for name, weight in oof_spearman_weights.items():
    print(f"  {name:20s}: {weight:.4f}")

# 결과 저장
all_results = {}

for comb_name, model_list in combinations.items():
    print(f"\n{comb_name}")
    print("-" * 100)

    # OOF predictions
    oof_preds = {name: models_oof[name] for name in model_list}

    # Holdout predictions
    holdout_preds = {
        'CatBoost': catboost_holdout,
        'FlatMLP': flatmlp_holdout,
        'CrossAttention': crossattn_holdout
    }
    holdout_preds = {name: holdout_preds[name] for name in model_list}

    # Weighted 가중치 (subset만)
    weighted_weights = {name: oof_spearman_weights[name] for name in model_list}
    # 재정규화
    total_w = sum(weighted_weights.values())
    weighted_weights = {k: v / total_w for k, v in weighted_weights.items()}

    # 두 가지 방법
    methods = {
        'weighted': weighted_weights,
        'equal': None
    }

    comb_results = {}

    for method_name, weights in methods.items():
        print(f"\n  [{method_name.upper()}]")

        # OOF ensemble
        oof_ensemble, final_weights = ensemble_predictions(oof_preds, weights, method_name)

        # Holdout ensemble
        holdout_ensemble, _ = ensemble_predictions(holdout_preds, weights, method_name)

        # OOF metrics
        oof_metrics = calculate_metrics(y_cv, oof_ensemble)
        oof_ranking = calculate_ranking_metrics(y_cv, oof_ensemble, k=30)

        # Holdout metrics
        holdout_metrics = calculate_metrics(y_holdout, holdout_ensemble)
        holdout_ranking = calculate_ranking_metrics(y_holdout, holdout_ensemble, k=30)

        # Top-30/50 약물 목록
        top30_drugs = get_top_k_drugs(oof_ensemble, df_cv, k=30)
        top50_drugs = get_top_k_drugs(oof_ensemble, df_cv, k=50)

        # 출력
        print(f"    가중치: {final_weights}")
        print(f"    OOF  Spearman: {oof_metrics['spearman']:.4f}, RMSE: {oof_metrics['rmse']:.4f}")
        print(f"    Hold Spearman: {holdout_metrics['spearman']:.4f}, RMSE: {holdout_metrics['rmse']:.4f}")
        print(f"    OOF  P@30: {oof_ranking['P@30']:.4f}, NDCG@30: {oof_ranking['NDCG@30']:.4f}")
        print(f"    Hold P@30: {holdout_ranking['P@30']:.4f}, NDCG@30: {holdout_ranking['NDCG@30']:.4f}")

        # 저장
        comb_results[method_name] = {
            'weights': final_weights,
            'oof_metrics': oof_metrics,
            'oof_ranking': oof_ranking,
            'holdout_metrics': holdout_metrics,
            'holdout_ranking': holdout_ranking,
            'top30_drugs': top30_drugs,
            'top50_drugs': top50_drugs
        }

    all_results[comb_name] = comb_results

# ============================================================================
# 조합 간 비교
# ============================================================================
print("\n[5] 조합 간 비교")
print("-" * 100)

# Holdout Spearman 기준 비교
print("\nHoldout Spearman 비교 (Weighted):")
print(f"{'Combination':40s} {'Holdout Sp':>12s} {'Holdout RMSE':>12s} {'P@30':>8s} {'NDCG@30':>8s}")
print("-" * 100)

for comb_name in combinations.keys():
    res = all_results[comb_name]['weighted']
    print(f"{comb_name:40s} "
          f"{res['holdout_metrics']['spearman']:>12.4f} "
          f"{res['holdout_metrics']['rmse']:>12.4f} "
          f"{res['holdout_ranking']['P@30']:>8.4f} "
          f"{res['holdout_ranking']['NDCG@30']:>8.4f}")

# 개선율 계산
catboost_sp = all_results['1. CatBoost']['weighted']['holdout_metrics']['spearman']
two_model_sp = all_results['2. CatBoost+FlatMLP']['weighted']['holdout_metrics']['spearman']
three_model_sp = all_results['3. CatBoost+FlatMLP+CrossAttn']['weighted']['holdout_metrics']['spearman']

improvement_2_vs_1 = two_model_sp - catboost_sp
improvement_3_vs_2 = three_model_sp - two_model_sp
improvement_3_vs_1 = three_model_sp - catboost_sp

print(f"\n개선율:")
print(f"  2-model vs CatBoost: {improvement_2_vs_1:+.4f} ({improvement_2_vs_1/catboost_sp*100:+.2f}%)")
print(f"  3-model vs 2-model:  {improvement_3_vs_2:+.4f} ({improvement_3_vs_2/two_model_sp*100:+.2f}%)")
print(f"  3-model vs CatBoost: {improvement_3_vs_1:+.4f} ({improvement_3_vs_1/catboost_sp*100:+.2f}%)")

# Top-30 overlap 비교
print("\n\nTop-30 Overlap (Jaccard, Weighted):")
for i, comb1 in enumerate(combinations.keys()):
    for j, comb2 in enumerate(combinations.keys()):
        if i < j:
            top30_1 = set([d['drug_name'] for d in all_results[comb1]['weighted']['top30_drugs']])
            top30_2 = set([d['drug_name'] for d in all_results[comb2]['weighted']['top30_drugs']])
            jaccard = len(top30_1 & top30_2) / len(top30_1 | top30_2)
            overlap = len(top30_1 & top30_2)
            print(f"  {comb1:40s} vs {comb2:40s}: {jaccard:.4f} ({overlap}/30)")

# ============================================================================
# 최종 선택
# ============================================================================
print("\n[6] 최종 선택 기준")
print("=" * 100)

print("\n판단 기준:")
print("1. Holdout Spearman (일반화 성능)")
print("2. Holdout RMSE (예측 정확도)")
print("3. Top-30 quality (P@30, NDCG@30)")
print("4. 3-model이 2-model 대비 실제 이득")

# 판정
if improvement_3_vs_2 > 0:
    verdict_3vs2 = f"✅ 3-model이 우수 (+{improvement_3_vs_2:.4f})"
elif improvement_3_vs_2 > -0.001:
    verdict_3vs2 = f"⚠️  거의 동등 ({improvement_3_vs_2:+.4f})"
else:
    verdict_3vs2 = f"❌ 2-model이 우수 ({improvement_3_vs_2:+.4f})"

print(f"\n3-model vs 2-model 판정: {verdict_3vs2}")

# Holdout 기준 최고 성능
best_comb = max(combinations.keys(),
                key=lambda x: all_results[x]['weighted']['holdout_metrics']['spearman'])

best_sp = all_results[best_comb]['weighted']['holdout_metrics']['spearman']
best_rmse = all_results[best_comb]['weighted']['holdout_metrics']['rmse']
best_p30 = all_results[best_comb]['weighted']['holdout_ranking']['P@30']
best_ndcg30 = all_results[best_comb]['weighted']['holdout_ranking']['NDCG@30']

print(f"\n최고 성능 (Holdout Spearman 기준):")
print(f"  조합: {best_comb}")
print(f"  Holdout Spearman: {best_sp:.4f}")
print(f"  Holdout RMSE:     {best_rmse:.4f}")
print(f"  P@30:             {best_p30:.4f}")
print(f"  NDCG@30:          {best_ndcg30:.4f}")

# ============================================================================
# 저장
# ============================================================================
print("\n[7] 결과 저장")
print("-" * 100)

# JSON 저장
output_json = output_dir / "ensemble_v4_comprehensive_results.json"
save_data = {
    "diversity": {
        "correlation_matrix": diversity_matrix,
        "average_correlation": float(avg_corr),
        "verdict": diversity_verdict
    },
    "individual_oof_metrics": individual_oof_metrics,
    "oof_spearman_weights": oof_spearman_weights,
    "combinations": all_results,
    "comparison": {
        "holdout_spearman": {
            comb: all_results[comb]['weighted']['holdout_metrics']['spearman']
            for comb in combinations.keys()
        },
        "improvement_2_vs_1": float(improvement_2_vs_1),
        "improvement_3_vs_2": float(improvement_3_vs_2),
        "improvement_3_vs_1": float(improvement_3_vs_1)
    },
    "final_selection": {
        "best_combination": best_comb,
        "holdout_spearman": float(best_sp),
        "holdout_rmse": float(best_rmse),
        "p@30": float(best_p30),
        "ndcg@30": float(best_ndcg30),
        "verdict_3vs2": verdict_3vs2
    }
}

with open(output_json, "w") as f:
    json.dump(save_data, f, indent=2)

print(f"✓ JSON: {output_json}")

# Top-30/50 CSV 저장
for comb_name in combinations.keys():
    safe_name = comb_name.replace(' ', '_').replace('+', '_')

    # Top-30
    top30_df = pd.DataFrame(all_results[comb_name]['weighted']['top30_drugs'])
    top30_csv = output_dir / f"top30_{safe_name}_weighted.csv"
    top30_df.to_csv(top30_csv, index=False)

    # Top-50
    top50_df = pd.DataFrame(all_results[comb_name]['weighted']['top50_drugs'])
    top50_csv = output_dir / f"top50_{safe_name}_weighted.csv"
    top50_df.to_csv(top50_csv, index=False)

print(f"✓ Top-30/50 CSV 저장 완료")

# Summary 저장
summary_path = output_dir / "ensemble_v4_summary.txt"
with open(summary_path, "w") as f:
    f.write("=" * 100 + "\n")
    f.write("Step 5 앙상블 v4 — Summary\n")
    f.write("=" * 100 + "\n\n")

    f.write("Diversity:\n")
    f.write(f"  평균 상관: {avg_corr:.4f}\n")
    f.write(f"  판정: {diversity_verdict}\n\n")

    f.write("Holdout Spearman (Weighted):\n")
    for comb_name in combinations.keys():
        sp = all_results[comb_name]['weighted']['holdout_metrics']['spearman']
        f.write(f"  {comb_name:40s}: {sp:.4f}\n")

    f.write(f"\n개선율:\n")
    f.write(f"  2-model vs CatBoost: {improvement_2_vs_1:+.4f}\n")
    f.write(f"  3-model vs 2-model:  {improvement_3_vs_2:+.4f}\n")
    f.write(f"  3-model vs CatBoost: {improvement_3_vs_1:+.4f}\n")

    f.write(f"\n최종 선택: {best_comb}\n")
    f.write(f"  Holdout Spearman: {best_sp:.4f}\n")
    f.write(f"  판정: {verdict_3vs2}\n")

print(f"✓ Summary: {summary_path}")

print("\n" + "=" * 100)
print("앙상블 분석 완료!")
print("=" * 100)
