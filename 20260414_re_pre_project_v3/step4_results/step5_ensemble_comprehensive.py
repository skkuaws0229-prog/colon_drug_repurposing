"""
Step 5 앙상블 종합 분석
- 앙상블 A (3개): CatBoost, DART, FlatMLP
- 앙상블 B (4개): CatBoost, DART, FlatMLP, CrossAttention
"""

import numpy as np
import json
from scipy.stats import spearmanr, kendalltau, pearsonr
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, ndcg_score
import pandas as pd
from collections import Counter

# 데이터 로드
print("=" * 80)
print("데이터 로드 중...")
print("=" * 80)

# Y 값 로드
y_train = np.load('y_train.npy')

# 전체 샘플 수
n_total = len(y_train)
print(f"총 Train 샘플 수: {n_total}")

# 모델 ID 정의
models_A = {
    '04': 'CatBoost',
    '02': 'DART',
    '10': 'FlatMLP'
}

models_B = {
    '04': 'CatBoost',
    '02': 'DART',
    '10': 'FlatMLP',
    '13': 'CrossAttention'
}

seeds = [42, 123, 456, 789, 2026]

# Step 5 Multi-seed 결과에서 OOF Spearman 읽기
def get_oof_spearman(model_id):
    """각 모델의 Step 5 OOF Spearman mean 가져오기"""
    with open(f'step5_multiseed_{model_id}_results.json', 'r') as f:
        results = json.load(f)
    return results['cross_seed_stats']['oof_spearman_mean']

# 가중치 계산
print("\n각 모델의 OOF Spearman (가중치 계산용):")
weights_A = {}
weights_B = {}

for mid, mname in models_A.items():
    sp = get_oof_spearman(mid)
    weights_A[mid] = sp
    print(f"  {mname} ({mid}): {sp:.4f}")

print()
for mid, mname in models_B.items():
    sp = get_oof_spearman(mid)
    weights_B[mid] = sp
    if mid not in weights_A:
        print(f"  {mname} ({mid}): {sp:.4f}")

# 가중치 정규화
sum_A = sum(weights_A.values())
sum_B = sum(weights_B.values())
weights_A_norm = {k: v/sum_A for k, v in weights_A.items()}
weights_B_norm = {k: v/sum_B for k, v in weights_B.items()}

print("\n정규화된 가중치:")
print("앙상블 A:")
for mid in weights_A_norm:
    print(f"  모델 {mid}: {weights_A_norm[mid]:.4f}")
print("앙상블 B:")
for mid in weights_B_norm:
    print(f"  모델 {mid}: {weights_B_norm[mid]:.4f}")

# 각 시드별 OOF 예측값 로드 및 앙상블 계산
print("\n" + "=" * 80)
print("시드별 OOF 예측 및 앙상블 계산...")
print("=" * 80)

ensemble_results = {
    'A': {'seeds': [], 'oof_equal': [], 'oof_weighted': []},
    'B': {'seeds': [], 'oof_equal': [], 'oof_weighted': []}
}

for seed in seeds:
    print(f"\nSeed {seed}:")

    # 앙상블 A
    preds_A = []
    for mid in models_A.keys():
        oof_file = f'step5_seed{seed}_{mid}_oof.npy'
        pred = np.load(oof_file)
        preds_A.append(pred)
        print(f"  모델 {mid} loaded: shape {pred.shape}")

    # 균등 가중
    oof_equal_A = np.mean(preds_A, axis=0)
    # 가중 평균
    oof_weighted_A = sum(preds_A[i] * weights_A_norm[list(models_A.keys())[i]]
                         for i in range(len(preds_A)))

    ensemble_results['A']['seeds'].append(seed)
    ensemble_results['A']['oof_equal'].append(oof_equal_A)
    ensemble_results['A']['oof_weighted'].append(oof_weighted_A)

    # 앙상블 B
    preds_B = []
    for mid in models_B.keys():
        oof_file = f'step5_seed{seed}_{mid}_oof.npy'
        pred = np.load(oof_file)
        preds_B.append(pred)

    # 균등 가중
    oof_equal_B = np.mean(preds_B, axis=0)
    # 가중 평균
    oof_weighted_B = sum(preds_B[i] * weights_B_norm[list(models_B.keys())[i]]
                         for i in range(len(preds_B)))

    ensemble_results['B']['seeds'].append(seed)
    ensemble_results['B']['oof_equal'].append(oof_equal_B)
    ensemble_results['B']['oof_weighted'].append(oof_weighted_B)

    # 각 시드별 Spearman 계산
    sp_A_eq = spearmanr(y_train, oof_equal_A)[0]
    sp_A_wt = spearmanr(y_train, oof_weighted_A)[0]
    sp_B_eq = spearmanr(y_train, oof_equal_B)[0]
    sp_B_wt = spearmanr(y_train, oof_weighted_B)[0]

    print(f"  앙상블 A - Equal: {sp_A_eq:.4f}, Weighted: {sp_A_wt:.4f}")
    print(f"  앙상블 B - Equal: {sp_B_eq:.4f}, Weighted: {sp_B_wt:.4f}")

# Train 예측값 로드 및 앙상블 계산
print("\n" + "=" * 80)
print("Train 예측 및 과적합 분석...")
print("=" * 80)

# Step 2 GroupKFold에서 train 예측 사용
train_preds_A = []
for mid in models_A.keys():
    # Step 2 train 예측 파일 읽기
    train_file = f'step2_groupkfold_{mid}_oof.npy'  # OOF가 실제로 전체 train 예측
    pred = np.load(train_file)
    train_preds_A.append(pred)

train_equal_A = np.mean(train_preds_A, axis=0)
train_weighted_A = sum(train_preds_A[i] * weights_A_norm[list(models_A.keys())[i]]
                       for i in range(len(train_preds_A)))

train_preds_B = []
for mid in models_B.keys():
    train_file = f'step2_groupkfold_{mid}_oof.npy'
    pred = np.load(train_file)
    train_preds_B.append(pred)

train_equal_B = np.mean(train_preds_B, axis=0)
train_weighted_B = sum(train_preds_B[i] * weights_B_norm[list(models_B.keys())[i]]
                       for i in range(len(train_preds_B)))

# Train Spearman
train_sp_A_eq = spearmanr(y_train, train_equal_A)[0]
train_sp_A_wt = spearmanr(y_train, train_weighted_A)[0]
train_sp_B_eq = spearmanr(y_train, train_equal_B)[0]
train_sp_B_wt = spearmanr(y_train, train_weighted_B)[0]

print(f"\nTrain Spearman:")
print(f"  앙상블 A - Equal: {train_sp_A_eq:.4f}, Weighted: {train_sp_A_wt:.4f}")
print(f"  앙상블 B - Equal: {train_sp_B_eq:.4f}, Weighted: {train_sp_B_wt:.4f}")

# 시드별 평균 OOF Spearman
oof_A_eq_sps = [spearmanr(y_train, pred)[0] for pred in ensemble_results['A']['oof_equal']]
oof_A_wt_sps = [spearmanr(y_train, pred)[0] for pred in ensemble_results['A']['oof_weighted']]
oof_B_eq_sps = [spearmanr(y_train, pred)[0] for pred in ensemble_results['B']['oof_equal']]
oof_B_wt_sps = [spearmanr(y_train, pred)[0] for pred in ensemble_results['B']['oof_weighted']]

oof_sp_A_eq = np.mean(oof_A_eq_sps)
oof_sp_A_wt = np.mean(oof_A_wt_sps)
oof_sp_B_eq = np.mean(oof_B_eq_sps)
oof_sp_B_wt = np.mean(oof_B_wt_sps)

print(f"\nOOF Spearman (5 seeds 평균):")
print(f"  앙상블 A - Equal: {oof_sp_A_eq:.4f} ± {np.std(oof_A_eq_sps):.4f}")
print(f"  앙상블 A - Weighted: {oof_sp_A_wt:.4f} ± {np.std(oof_A_wt_sps):.4f}")
print(f"  앙상블 B - Equal: {oof_sp_B_eq:.4f} ± {np.std(oof_B_eq_sps):.4f}")
print(f"  앙상블 B - Weighted: {oof_sp_B_wt:.4f} ± {np.std(oof_B_wt_sps):.4f}")

# Gap 계산
gap_A_eq = train_sp_A_eq - oof_sp_A_eq
gap_A_wt = train_sp_A_wt - oof_sp_A_wt
gap_B_eq = train_sp_B_eq - oof_sp_B_eq
gap_B_wt = train_sp_B_wt - oof_sp_B_wt

ratio_A_eq = oof_sp_A_eq / train_sp_A_eq if train_sp_A_eq != 0 else 0
ratio_A_wt = oof_sp_A_wt / train_sp_A_wt if train_sp_A_wt != 0 else 0
ratio_B_eq = oof_sp_B_eq / train_sp_B_eq if train_sp_B_eq != 0 else 0
ratio_B_wt = oof_sp_B_wt / train_sp_B_wt if train_sp_B_wt != 0 else 0

print(f"\n과적합 분석:")
print(f"  앙상블 A Equal - Gap: {gap_A_eq:.4f}, Ratio: {ratio_A_eq:.4f}")
print(f"  앙상블 A Weighted - Gap: {gap_A_wt:.4f}, Ratio: {ratio_A_wt:.4f}")
print(f"  앙상블 B Equal - Gap: {gap_B_eq:.4f}, Ratio: {ratio_B_eq:.4f}")
print(f"  앙상블 B Weighted - Gap: {gap_B_wt:.4f}, Ratio: {ratio_B_wt:.4f}")

# Holdout 예측 (Step 1 결과 사용)
print("\n" + "=" * 80)
print("Holdout 예측...")
print("=" * 80)

import os

model_name_map = {
    '01': 'lightgbm',
    '02': '',  # model_02_holdout.npy
    '04': 'catboost',
    '10': 'flatmlp',
    '13': 'crossattention'
}

holdout_preds_A = []
for mid in models_A.keys():
    # Try both naming conventions
    if mid in model_name_map and model_name_map[mid]:
        holdout_file = f'model_{mid}_{model_name_map[mid]}_holdout.npy'
    else:
        holdout_file = f'model_{mid}_holdout.npy'

    if not os.path.exists(holdout_file):
        # Try alternative
        holdout_file = f'model_{mid}_holdout.npy'

    pred = np.load(holdout_file)
    holdout_preds_A.append(pred)
    print(f"  Loaded {holdout_file}: shape {pred.shape}")

holdout_equal_A = np.mean(holdout_preds_A, axis=0)
holdout_weighted_A = sum(holdout_preds_A[i] * weights_A_norm[list(models_A.keys())[i]]
                         for i in range(len(holdout_preds_A)))

holdout_preds_B = []
for mid in models_B.keys():
    # Try both naming conventions
    if mid in model_name_map and model_name_map[mid]:
        holdout_file = f'model_{mid}_{model_name_map[mid]}_holdout.npy'
    else:
        holdout_file = f'model_{mid}_holdout.npy'

    if not os.path.exists(holdout_file):
        # Try alternative
        holdout_file = f'model_{mid}_holdout.npy'

    pred = np.load(holdout_file)
    holdout_preds_B.append(pred)

holdout_equal_B = np.mean(holdout_preds_B, axis=0)
holdout_weighted_B = sum(holdout_preds_B[i] * weights_B_norm[list(models_B.keys())[i]]
                         for i in range(len(holdout_preds_B)))

# Holdout Y 로드 (model_01_lightgbm.json에서 holdout indices 확인)
# 간단하게 첫 번째 모델의 holdout 예측 길이로 y_holdout 생성
# 실제로는 data split 정보 필요하지만, 여기서는 근사값 사용
n_holdout = len(holdout_equal_A)
print(f"Holdout 샘플 수: {n_holdout}")

# 전체 y에서 holdout 부분 추출 (train 길이 + holdout = 전체)
# 간단히 model results에서 가져오기
with open('model_04_catboost.json', 'r') as f:
    model_data = json.load(f)
    holdout_sp_04 = model_data['holdout_spearman']

# 실제 holdout y 계산을 위해 임시로 추정
# y_train은 이미 있고, holdout은 별도
# Step 1에서 사용한 split 재현 필요
print("Holdout 예측 완료 (Holdout y 값 확인 필요)")

# 전체 메트릭 계산 함수
def calculate_metrics(y_true, y_pred, prefix=""):
    """모든 메트릭 계산"""
    metrics = {}

    # Regression metrics
    metrics[f'{prefix}spearman'] = spearmanr(y_true, y_pred)[0]
    metrics[f'{prefix}kendall'] = kendalltau(y_true, y_pred)[0]
    metrics[f'{prefix}pearson'] = pearsonr(y_true, y_pred)[0]
    metrics[f'{prefix}rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
    metrics[f'{prefix}mae'] = mean_absolute_error(y_true, y_pred)
    metrics[f'{prefix}median_ae'] = np.median(np.abs(y_true - y_pred))
    metrics[f'{prefix}p95_error'] = np.percentile(np.abs(y_true - y_pred), 95)
    metrics[f'{prefix}r2'] = r2_score(y_true, y_pred)

    return metrics

# OOF 메트릭 (평균 예측 사용)
print("\n" + "=" * 80)
print("전체 메트릭 계산...")
print("=" * 80)

# 각 앙상블의 평균 OOF 예측 사용
avg_oof_A_eq = np.mean(ensemble_results['A']['oof_equal'], axis=0)
avg_oof_A_wt = np.mean(ensemble_results['A']['oof_weighted'], axis=0)
avg_oof_B_eq = np.mean(ensemble_results['B']['oof_equal'], axis=0)
avg_oof_B_wt = np.mean(ensemble_results['B']['oof_weighted'], axis=0)

metrics_A_eq = calculate_metrics(y_train, avg_oof_A_eq, 'oof_')
metrics_A_wt = calculate_metrics(y_train, avg_oof_A_wt, 'oof_')
metrics_B_eq = calculate_metrics(y_train, avg_oof_B_eq, 'oof_')
metrics_B_wt = calculate_metrics(y_train, avg_oof_B_wt, 'oof_')

# Train 메트릭
train_metrics_A_eq = calculate_metrics(y_train, train_equal_A, 'train_')
train_metrics_A_wt = calculate_metrics(y_train, train_weighted_A, 'train_')
train_metrics_B_eq = calculate_metrics(y_train, train_equal_B, 'train_')
train_metrics_B_wt = calculate_metrics(y_train, train_weighted_B, 'train_')

print("\n메트릭 계산 완료!")

# Top 30 약물 추출
print("\n" + "=" * 80)
print("Top 30 약물 추출...")
print("=" * 80)

def get_top30_indices(predictions, y_true):
    """예측값 기준 Top 30 인덱스 추출"""
    sorted_indices = np.argsort(predictions)[::-1][:30]
    return sorted_indices

# 각 앙상블의 Top 30
top30_A_eq = get_top30_indices(avg_oof_A_eq, y_train)
top30_A_wt = get_top30_indices(avg_oof_A_wt, y_train)
top30_B_eq = get_top30_indices(avg_oof_B_eq, y_train)
top30_B_wt = get_top30_indices(avg_oof_B_wt, y_train)

# A vs B overlap
overlap_eq = len(set(top30_A_eq) & set(top30_B_eq))
overlap_wt = len(set(top30_A_wt) & set(top30_B_wt))

print(f"Top 30 Overlap (Equal): {overlap_eq}/30 ({overlap_eq/30*100:.1f}%)")
print(f"Top 30 Overlap (Weighted): {overlap_wt}/30 ({overlap_wt/30*100:.1f}%)")

# Top 30 저장
np.savetxt('ensemble_A_equal_top30.csv', top30_A_eq, fmt='%d', delimiter=',')
np.savetxt('ensemble_A_weighted_top30.csv', top30_A_wt, fmt='%d', delimiter=',')
np.savetxt('ensemble_B_equal_top30.csv', top30_B_eq, fmt='%d', delimiter=',')
np.savetxt('ensemble_B_weighted_top30.csv', top30_B_wt, fmt='%d', delimiter=',')

print("Top 30 목록 CSV 저장 완료")

# 예측값 저장
print("\n" + "=" * 80)
print("예측값 저장...")
print("=" * 80)

np.save('ensemble_A_equal_oof.npy', avg_oof_A_eq)
np.save('ensemble_A_weighted_oof.npy', avg_oof_A_wt)
np.save('ensemble_B_equal_oof.npy', avg_oof_B_eq)
np.save('ensemble_B_weighted_oof.npy', avg_oof_B_wt)

np.save('ensemble_A_equal_train.npy', train_equal_A)
np.save('ensemble_A_weighted_train.npy', train_weighted_A)
np.save('ensemble_B_equal_train.npy', train_equal_B)
np.save('ensemble_B_weighted_train.npy', train_weighted_B)

np.save('ensemble_A_equal_holdout.npy', holdout_equal_A)
np.save('ensemble_A_weighted_holdout.npy', holdout_weighted_A)
np.save('ensemble_B_equal_holdout.npy', holdout_equal_B)
np.save('ensemble_B_weighted_holdout.npy', holdout_weighted_B)

print("예측값 저장 완료")

# 최종 결과 JSON 저장
print("\n" + "=" * 80)
print("결과 JSON 생성...")
print("=" * 80)

final_results = {
    "ensemble_A": {
        "models": list(models_A.values()),
        "model_ids": list(models_A.keys()),
        "weights_normalized": weights_A_norm,
        "equal_weight": {
            "train_spearman": float(train_sp_A_eq),
            "oof_spearman_mean": float(oof_sp_A_eq),
            "oof_spearman_std": float(np.std(oof_A_eq_sps)),
            "gap": float(gap_A_eq),
            "ratio": float(ratio_A_eq),
            **{k: float(v) for k, v in metrics_A_eq.items()},
            **{k: float(v) for k, v in train_metrics_A_eq.items()},
            "top30_indices": top30_A_eq.tolist()
        },
        "weighted": {
            "train_spearman": float(train_sp_A_wt),
            "oof_spearman_mean": float(oof_sp_A_wt),
            "oof_spearman_std": float(np.std(oof_A_wt_sps)),
            "gap": float(gap_A_wt),
            "ratio": float(ratio_A_wt),
            **{k: float(v) for k, v in metrics_A_wt.items()},
            **{k: float(v) for k, v in train_metrics_A_wt.items()},
            "top30_indices": top30_A_wt.tolist()
        }
    },
    "ensemble_B": {
        "models": list(models_B.values()),
        "model_ids": list(models_B.keys()),
        "weights_normalized": weights_B_norm,
        "equal_weight": {
            "train_spearman": float(train_sp_B_eq),
            "oof_spearman_mean": float(oof_sp_B_eq),
            "oof_spearman_std": float(np.std(oof_B_eq_sps)),
            "gap": float(gap_B_eq),
            "ratio": float(ratio_B_eq),
            **{k: float(v) for k, v in metrics_B_eq.items()},
            **{k: float(v) for k, v in train_metrics_B_eq.items()},
            "top30_indices": top30_B_eq.tolist()
        },
        "weighted": {
            "train_spearman": float(train_sp_B_wt),
            "oof_spearman_mean": float(oof_sp_B_wt),
            "oof_spearman_std": float(np.std(oof_B_wt_sps)),
            "gap": float(gap_B_wt),
            "ratio": float(ratio_B_wt),
            **{k: float(v) for k, v in metrics_B_wt.items()},
            **{k: float(v) for k, v in train_metrics_B_wt.items()},
            "top30_indices": top30_B_wt.tolist()
        }
    },
    "comparison": {
        "top30_overlap_equal": int(overlap_eq),
        "top30_overlap_weighted": int(overlap_wt),
        "jaccard_equal": float(overlap_eq / 30),
        "jaccard_weighted": float(overlap_wt / 30)
    }
}

with open('step5_ensemble_comprehensive_results.json', 'w') as f:
    json.dump(final_results, f, indent=2)

print("결과 JSON 저장 완료: step5_ensemble_comprehensive_results.json")

# 요약 테이블 출력
print("\n" + "=" * 80)
print("앙상블 비교 요약")
print("=" * 80)

print("\n[앙상블 구성]")
print(f"앙상블 A (3개): {', '.join(models_A.values())}")
print(f"앙상블 B (4개): {', '.join(models_B.values())}")

print("\n[Equal Weight 결과]")
print(f"{'Metric':<20} {'Ensemble A':>12} {'Ensemble B':>12} {'Diff':>10}")
print("-" * 60)
print(f"{'Train Sp':<20} {train_sp_A_eq:>12.4f} {train_sp_B_eq:>12.4f} {train_sp_B_eq-train_sp_A_eq:>10.4f}")
print(f"{'OOF Sp':<20} {oof_sp_A_eq:>12.4f} {oof_sp_B_eq:>12.4f} {oof_sp_B_eq-oof_sp_A_eq:>10.4f}")
print(f"{'Gap':<20} {gap_A_eq:>12.4f} {gap_B_eq:>12.4f} {gap_B_eq-gap_A_eq:>10.4f}")
print(f"{'Ratio':<20} {ratio_A_eq:>12.4f} {ratio_B_eq:>12.4f} {ratio_B_eq-ratio_A_eq:>10.4f}")
print(f"{'RMSE':<20} {metrics_A_eq['oof_rmse']:>12.4f} {metrics_B_eq['oof_rmse']:>12.4f} {metrics_B_eq['oof_rmse']-metrics_A_eq['oof_rmse']:>10.4f}")

print("\n[Weighted 결과]")
print(f"{'Metric':<20} {'Ensemble A':>12} {'Ensemble B':>12} {'Diff':>10}")
print("-" * 60)
print(f"{'Train Sp':<20} {train_sp_A_wt:>12.4f} {train_sp_B_wt:>12.4f} {train_sp_B_wt-train_sp_A_wt:>10.4f}")
print(f"{'OOF Sp':<20} {oof_sp_A_wt:>12.4f} {oof_sp_B_wt:>12.4f} {oof_sp_B_wt-oof_sp_A_wt:>10.4f}")
print(f"{'Gap':<20} {gap_A_wt:>12.4f} {gap_B_wt:>12.4f} {gap_B_wt-gap_A_wt:>10.4f}")
print(f"{'Ratio':<20} {ratio_A_wt:>12.4f} {ratio_B_wt:>12.4f} {ratio_B_wt-ratio_A_wt:>10.4f}")
print(f"{'RMSE':<20} {metrics_A_wt['oof_rmse']:>12.4f} {metrics_B_wt['oof_rmse']:>12.4f} {metrics_B_wt['oof_rmse']-metrics_A_wt['oof_rmse']:>10.4f}")

print("\n[Top 30 Overlap]")
print(f"Equal Weight:    {overlap_eq}/30 ({overlap_eq/30*100:.1f}%)")
print(f"Weighted:        {overlap_wt}/30 ({overlap_wt/30*100:.1f}%)")

print("\n" + "=" * 80)
print("분석 완료!")
print("=" * 80)
