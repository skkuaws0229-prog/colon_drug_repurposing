#!/usr/bin/env python3
"""
Step 4.5-A: FlatMLP vs CrossAttention 동일예측 원인 검증
"""
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import jaccard_score
from pathlib import Path
from datetime import datetime

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/verification"
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Step 4.5-A: FlatMLP vs CrossAttention 동일예측 원인 검증")
print("=" * 80)

# ============================================================================
# 1. OOF prediction 파일 경로 확인
# ============================================================================
print("\n[1] OOF prediction 파일 경로 확인")
print("-" * 80)

flatmlp_oof = step4_dir / "model_10_oof.npy"
crossattn_oof = step4_dir / "model_13_oof.npy"

print(f"FlatMLP OOF:        {flatmlp_oof}")
print(f"CrossAttention OOF: {crossattn_oof}")
print(f"\nFlatMLP exists:        {flatmlp_oof.exists()}")
print(f"CrossAttention exists: {crossattn_oof.exists()}")

# 파일 메타데이터
if flatmlp_oof.exists() and crossattn_oof.exists():
    flatmlp_stat = flatmlp_oof.stat()
    crossattn_stat = crossattn_oof.stat()

    print(f"\nFlatMLP size:        {flatmlp_stat.st_size:,} bytes")
    print(f"CrossAttention size: {crossattn_stat.st_size:,} bytes")
    print(f"\nFlatMLP modified:        {datetime.fromtimestamp(flatmlp_stat.st_mtime)}")
    print(f"CrossAttention modified: {datetime.fromtimestamp(crossattn_stat.st_mtime)}")

# ============================================================================
# 2. 데이터 로드 및 기본 정보
# ============================================================================
print("\n[2] 데이터 로드 및 기본 정보")
print("-" * 80)

pred_flatmlp = np.load(flatmlp_oof)
pred_crossattn = np.load(crossattn_oof)

print(f"FlatMLP shape:        {pred_flatmlp.shape}")
print(f"CrossAttention shape: {pred_crossattn.shape}")
print(f"\nFlatMLP dtype:        {pred_flatmlp.dtype}")
print(f"CrossAttention dtype: {pred_crossattn.dtype}")

# ============================================================================
# 3. 데이터 정렬 확인 (동일 인덱스 가정)
# ============================================================================
print("\n[3] row alignment 확인 (같은 순서로 저장되었다고 가정)")
print("-" * 80)
print(f"두 예측값의 길이가 같은가? {len(pred_flatmlp) == len(pred_crossattn)}")
print(f"Row 수: {len(pred_flatmlp)}")

# ============================================================================
# 4. 6개 비교 지표 계산
# ============================================================================
print("\n[4] 6개 비교 지표 계산")
print("-" * 80)

# Pearson correlation
pearson_corr, pearson_pval = pearsonr(pred_flatmlp, pred_crossattn)
print(f"Pearson correlation:    {pearson_corr:.6f} (p-value: {pearson_pval:.2e})")

# Spearman correlation
spearman_corr, spearman_pval = spearmanr(pred_flatmlp, pred_crossattn)
print(f"Spearman correlation:   {spearman_corr:.6f} (p-value: {spearman_pval:.2e})")

# Max/Mean absolute difference
abs_diff = np.abs(pred_flatmlp - pred_crossattn)
max_diff = np.max(abs_diff)
mean_diff = np.mean(abs_diff)
print(f"Max absolute diff:      {max_diff:.6f}")
print(f"Mean absolute diff:     {mean_diff:.6f}")

# Top-30 overlap (Jaccard)
top30_flatmlp = set(np.argsort(pred_flatmlp)[:30])
top30_crossattn = set(np.argsort(pred_crossattn)[:30])
jaccard_30 = len(top30_flatmlp & top30_crossattn) / len(top30_flatmlp | top30_crossattn)
print(f"Top-30 Jaccard overlap: {jaccard_30:.4f} ({len(top30_flatmlp & top30_crossattn)}/30 일치)")

# Top-50 overlap (Jaccard)
top50_flatmlp = set(np.argsort(pred_flatmlp)[:50])
top50_crossattn = set(np.argsort(pred_crossattn)[:50])
jaccard_50 = len(top50_flatmlp & top50_crossattn) / len(top50_flatmlp | top50_crossattn)
print(f"Top-50 Jaccard overlap: {jaccard_50:.4f} ({len(top50_flatmlp & top50_crossattn)}/50 일치)")

# ============================================================================
# 5. 파이프라인 경로 점검
# ============================================================================
print("\n[5] 파이프라인 경로 점검")
print("-" * 80)

# JSON 파일 확인
flatmlp_json = step4_dir / "model_10_flatmlp.json"
crossattn_json = step4_dir / "model_13_crossattention.json"

print(f"FlatMLP JSON:        {flatmlp_json.exists()} - {flatmlp_json}")
print(f"CrossAttention JSON: {crossattn_json.exists()} - {crossattn_json}")

if flatmlp_json.exists():
    with open(flatmlp_json) as f:
        flatmlp_meta = json.load(f)
    print(f"\nFlatMLP OOF 경로 (from JSON): {flatmlp_meta.get('oof_predictions_path', 'N/A')}")

if crossattn_json.exists():
    with open(crossattn_json) as f:
        crossattn_meta = json.load(f)
    print(f"CrossAttention OOF 경로 (from JSON): {crossattn_meta.get('oof_predictions_path', 'N/A')}")

# ============================================================================
# 6. 학습 로그 비교 (loss curve)
# ============================================================================
print("\n[6] 학습 로그 비교 (loss curve)")
print("-" * 80)

if flatmlp_json.exists() and crossattn_json.exists():
    flatmlp_loss = flatmlp_meta.get('fold_train_losses', [])
    crossattn_loss = crossattn_meta.get('fold_train_losses', [])

    print(f"FlatMLP fold train losses available:     {len(flatmlp_loss) > 0}")
    print(f"CrossAttention fold train losses available: {len(crossattn_loss) > 0}")

    if len(flatmlp_loss) > 0 and len(crossattn_loss) > 0:
        # Fold 0 첫 5 epoch 비교
        flatmlp_fold0 = flatmlp_loss[0][:5] if len(flatmlp_loss[0]) >= 5 else flatmlp_loss[0]
        crossattn_fold0 = crossattn_loss[0][:5] if len(crossattn_loss[0]) >= 5 else crossattn_loss[0]

        print(f"\nFlatMLP Fold 0 first 5 epochs:        {flatmlp_fold0}")
        print(f"CrossAttention Fold 0 first 5 epochs: {crossattn_fold0}")

        if flatmlp_fold0 == crossattn_fold0:
            print("⚠️  WARNING: 학습 loss가 완전히 동일함 - 같은 학습을 공유한 것으로 의심")
        else:
            print("✅ OK: 학습 loss가 다름 - 별도로 학습됨")

# ============================================================================
# 7. Weight 파일 비교
# ============================================================================
print("\n[7] Weight 파일 비교")
print("-" * 80)

# .pt 파일 찾기
flatmlp_weights = list(step4_dir.glob("model_10_flatmlp_fold*.pt"))
crossattn_weights = list(step4_dir.glob("model_13_crossattention_fold*.pt"))

print(f"FlatMLP weight 파일 수:        {len(flatmlp_weights)}")
print(f"CrossAttention weight 파일 수: {len(crossattn_weights)}")

if len(flatmlp_weights) > 0 and len(crossattn_weights) > 0:
    # Fold 0 비교
    flatmlp_w0 = flatmlp_weights[0]
    crossattn_w0 = crossattn_weights[0]

    flatmlp_w0_stat = flatmlp_w0.stat()
    crossattn_w0_stat = crossattn_w0.stat()

    print(f"\nFlatMLP fold 0 weight:")
    print(f"  Path: {flatmlp_w0.name}")
    print(f"  Size: {flatmlp_w0_stat.st_size:,} bytes")
    print(f"  Modified: {datetime.fromtimestamp(flatmlp_w0_stat.st_mtime)}")

    print(f"\nCrossAttention fold 0 weight:")
    print(f"  Path: {crossattn_w0.name}")
    print(f"  Size: {crossattn_w0_stat.st_size:,} bytes")
    print(f"  Modified: {datetime.fromtimestamp(crossattn_w0_stat.st_mtime)}")

    if flatmlp_w0_stat.st_size == crossattn_w0_stat.st_size:
        print("\n⚠️  WARNING: Weight 파일 크기가 동일함 - 구조적으로 의심스러움")
        print("   CrossAttention은 Attention layer가 있어서 FlatMLP보다 커야 정상")
    else:
        print(f"\n✅ OK: Weight 파일 크기가 다름 (차이: {abs(flatmlp_w0_stat.st_size - crossattn_w0_stat.st_size):,} bytes)")

# ============================================================================
# 8. 결과 요약 및 분기 판단
# ============================================================================
print("\n[8] 결과 요약 및 분기 판단")
print("=" * 80)

results = {
    "파일 메타데이터": {
        "flatmlp_path": str(flatmlp_oof),
        "crossattn_path": str(crossattn_oof),
        "flatmlp_size_bytes": flatmlp_stat.st_size if flatmlp_oof.exists() else None,
        "crossattn_size_bytes": crossattn_stat.st_size if crossattn_oof.exists() else None,
        "파일_크기_동일": flatmlp_stat.st_size == crossattn_stat.st_size if flatmlp_oof.exists() and crossattn_oof.exists() else None,
    },
    "예측값 비교": {
        "pearson_corr": float(pearson_corr),
        "spearman_corr": float(spearman_corr),
        "max_abs_diff": float(max_diff),
        "mean_abs_diff": float(mean_diff),
        "top30_jaccard": float(jaccard_30),
        "top50_jaccard": float(jaccard_50),
    },
    "학습 로그": {
        "flatmlp_loss_available": len(flatmlp_loss) > 0 if flatmlp_json.exists() else False,
        "crossattn_loss_available": len(crossattn_loss) > 0 if crossattn_json.exists() else False,
    },
    "Weight 파일": {
        "flatmlp_weight_count": len(flatmlp_weights),
        "crossattn_weight_count": len(crossattn_weights),
        "flatmlp_fold0_size": flatmlp_w0_stat.st_size if len(flatmlp_weights) > 0 else None,
        "crossattn_fold0_size": crossattn_w0_stat.st_size if len(crossattn_weights) > 0 else None,
        "weight_크기_동일": flatmlp_w0_stat.st_size == crossattn_w0_stat.st_size if len(flatmlp_weights) > 0 and len(crossattn_weights) > 0 else None,
    }
}

# 분기 판단
print("\n분기 판단:")
print("-" * 80)

if spearman_corr >= 0.98:
    case = "Case 2"
    diagnosis = "구조적 중복 가능성"
    action = "Step 4.5-B 경량 분리 실험 진행"
    print(f"✅ {case}: {diagnosis}")
    print(f"   Spearman correlation {spearman_corr:.6f} ≥ 0.98")
    print(f"   → {action}")
elif spearman_corr < 0.95:
    case = "Case 3"
    diagnosis = "실제로 다름"
    action = "분리 실험 불필요, 바로 Step 4.5-B 튜닝으로 진행"
    print(f"✅ {case}: {diagnosis}")
    print(f"   Spearman correlation {spearman_corr:.6f} < 0.95")
    print(f"   → {action}")
else:
    case = "Case 1"
    diagnosis = "파일/평가 오류 가능성"
    action = "수정 후 CrossAttention 재평가"
    print(f"⚠️  {case}: {diagnosis}")
    print(f"   Spearman correlation {spearman_corr:.6f} (0.95 ~ 0.98)")
    print(f"   → {action}")

results["분기 판단"] = {
    "case": case,
    "diagnosis": diagnosis,
    "action": action,
    "spearman_corr": float(spearman_corr)
}

# 저장
output_json = output_dir / "verification_results.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n결과 저장: {output_json}")

# 요약 테이블
print("\n" + "=" * 80)
print("요약 테이블")
print("=" * 80)
print(f"{'지표':<30} {'값':<20} {'판단':<30}")
print("-" * 80)
print(f"{'Pearson correlation':<30} {pearson_corr:<20.6f} {'완전 동일' if pearson_corr > 0.999 else '높은 상관' if pearson_corr > 0.95 else '보통':<30}")
print(f"{'Spearman correlation':<30} {spearman_corr:<20.6f} {'완전 동일' if spearman_corr > 0.999 else '높은 상관' if spearman_corr > 0.95 else '보통':<30}")
print(f"{'Max absolute diff':<30} {max_diff:<20.6f} {'거의 0' if max_diff < 0.001 else '작음' if max_diff < 0.1 else '큼':<30}")
print(f"{'Mean absolute diff':<30} {mean_diff:<20.6f} {'거의 0' if mean_diff < 0.001 else '작음' if mean_diff < 0.1 else '큼':<30}")
print(f"{'Top-30 Jaccard':<30} {jaccard_30:<20.4f} {'완전 일치' if jaccard_30 > 0.95 else '높은 overlap' if jaccard_30 > 0.7 else '보통':<30}")
print(f"{'Top-50 Jaccard':<30} {jaccard_50:<20.4f} {'완전 일치' if jaccard_50 > 0.95 else '높은 overlap' if jaccard_50 > 0.7 else '보통':<30}")
print("=" * 80)

print(f"\n분기: {case} - {diagnosis}")
print(f"다음 단계: {action}")
print("\n검증 완료!")
