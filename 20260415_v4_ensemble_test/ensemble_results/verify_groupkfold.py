#!/usr/bin/env python3
"""
GroupKFold 측정 방식 검증

v3 vs v4 차이 확인:
- v3: OOF 0.862 → GroupKFold 0.559 (-35%)
- v4: OOF 0.871 → GroupKFold 0.858 (-1.3%)

검증 항목:
1. Group 기준이 canonical_drug_id인지 확인
2. Train/Val fold에 같은 drug_id가 섞여있는지 확인
3. Group 수(unique drug) 출력
4. v3 구현과 비교
"""
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold
import json

print("=" * 100)
print("GroupKFold 측정 방식 검증")
print("=" * 100)

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/ensemble_results"

# ============================================================================
# 1. 데이터 로드
# ============================================================================
print("\n[1] 데이터 로드")
print("-" * 100)

features_df = pd.read_parquet(base_dir / "20260414_re_pre_project_v3/features_slim.parquet")
drug_ids_full = features_df['canonical_drug_id'].values

print(f"✓ features_slim.parquet 로드")
print(f"  Total samples: {len(drug_ids_full)}")
print(f"  Unique drugs (전체): {len(np.unique(drug_ids_full))}")
print(f"  Unique drugs 목록 (처음 10개): {np.unique(drug_ids_full)[:10]}")

# v4 shuffle 재현
n_samples = len(drug_ids_full)
n_train = int(n_samples * 0.8)

indices = np.arange(n_samples)
np.random.seed(42)
np.random.shuffle(indices)

train_idx = indices[:n_train]
holdout_idx = indices[n_train:]

drug_ids_cv = drug_ids_full[train_idx]
drug_ids_holdout = drug_ids_full[holdout_idx]

print(f"\n✓ v4 Shuffle (seed=42)")
print(f"  CV samples: {len(drug_ids_cv)}")
print(f"  Unique drugs (CV): {len(np.unique(drug_ids_cv))}")
print(f"  Holdout samples: {len(drug_ids_holdout)}")
print(f"  Unique drugs (Holdout): {len(np.unique(drug_ids_holdout))}")

# OOF 로드
catboost_full_oof = np.load(step4_dir / "model_04_catboost_oof.npy")
y_train_full = np.load(step4_dir / "y_train.npy")
y_cv = y_train_full[train_idx]

print(f"\n✓ OOF predictions 로드")
print(f"  CatBoost-Full OOF shape: {catboost_full_oof.shape}")
print(f"  y_cv shape: {y_cv.shape}")
print(f"  OOF Spearman: {spearmanr(y_cv, catboost_full_oof)[0]:.4f}")

# ============================================================================
# 2. GroupKFold 검증 (Fold 1만 상세 확인)
# ============================================================================
print("\n" + "=" * 100)
print("[2] GroupKFold 검증 - Fold 1 상세 분석")
print("=" * 100)

gkf = GroupKFold(n_splits=5)

# Fold 1만 확인
for fold_idx, (train_fold_idx, val_fold_idx) in enumerate(gkf.split(catboost_full_oof, y_cv, groups=drug_ids_cv), 1):
    if fold_idx > 1:
        break  # Fold 1만 확인

    print(f"\n✅ Fold {fold_idx}/5:")
    print("-" * 100)

    # Train/Val 분리
    train_drugs = drug_ids_cv[train_fold_idx]
    val_drugs = drug_ids_cv[val_fold_idx]

    unique_train_drugs = set(train_drugs)
    unique_val_drugs = set(val_drugs)

    print(f"\n[Train Set]")
    print(f"  Samples: {len(train_fold_idx)}")
    print(f"  Unique drugs: {len(unique_train_drugs)}")
    print(f"  Drug IDs (처음 10개): {sorted(unique_train_drugs)[:10]}")

    print(f"\n[Val Set]")
    print(f"  Samples: {len(val_fold_idx)}")
    print(f"  Unique drugs: {len(unique_val_drugs)}")
    print(f"  Drug IDs (처음 10개): {sorted(unique_val_drugs)[:10]}")

    # 핵심 검증: Train/Val에 같은 drug_id가 있는지 확인
    overlap = unique_train_drugs & unique_val_drugs

    print(f"\n[중복 검증] ⚠️ 핵심!")
    print(f"  Train/Val 중복 약물 수: {len(overlap)}")

    if len(overlap) > 0:
        print(f"  ❌ 중복 발견! GroupKFold이 제대로 작동하지 않음!")
        print(f"  중복 약물 목록 (처음 20개): {sorted(overlap)[:20]}")
        print(f"\n  → 이것이 v4에서 GroupKFold 성능이 높은 이유!")
        print(f"  → Train에 있는 약물이 Val에도 있어서 일반화 테스트가 안 됨")
    else:
        print(f"  ✅ 중복 없음! GroupKFold이 제대로 작동함")
        print(f"  → Train과 Val이 완전히 다른 약물로 분리됨")
        print(f"  → Unseen drug 테스트가 제대로 됨")

    # 성능 확인
    val_true = y_cv[val_fold_idx]
    val_pred = catboost_full_oof[val_fold_idx]
    val_sp = spearmanr(val_true, val_pred)[0]

    print(f"\n[성능]")
    print(f"  Val Spearman: {val_sp:.4f}")

    # 약물별 평균 샘플 수
    from collections import Counter
    train_drug_counts = Counter(train_drugs)
    val_drug_counts = Counter(val_drugs)

    print(f"\n[약물별 샘플 분포]")
    print(f"  Train - 평균 샘플/약물: {np.mean(list(train_drug_counts.values())):.1f}")
    print(f"  Train - 최소/최대: {min(train_drug_counts.values())}/{max(train_drug_counts.values())}")
    print(f"  Val - 평균 샘플/약물: {np.mean(list(val_drug_counts.values())):.1f}")
    print(f"  Val - 최소/최대: {min(val_drug_counts.values())}/{max(val_drug_counts.values())}")

# ============================================================================
# 3. 전체 Fold 검증 (중복 확인)
# ============================================================================
print("\n" + "=" * 100)
print("[3] 전체 5-Fold 중복 검증")
print("=" * 100)

all_fold_results = []

for fold_idx, (train_fold_idx, val_fold_idx) in enumerate(gkf.split(catboost_full_oof, y_cv, groups=drug_ids_cv), 1):
    train_drugs = set(drug_ids_cv[train_fold_idx])
    val_drugs = set(drug_ids_cv[val_fold_idx])
    overlap = train_drugs & val_drugs

    val_true = y_cv[val_fold_idx]
    val_pred = catboost_full_oof[val_fold_idx]
    val_sp = spearmanr(val_true, val_pred)[0]

    all_fold_results.append({
        'fold': fold_idx,
        'train_samples': len(train_fold_idx),
        'val_samples': len(val_fold_idx),
        'train_drugs': len(train_drugs),
        'val_drugs': len(val_drugs),
        'overlap_drugs': len(overlap),
        'val_spearman': val_sp
    })

    status = "❌ 중복 있음" if len(overlap) > 0 else "✅ 중복 없음"
    print(f"Fold {fold_idx}: Train {len(train_drugs)}개, Val {len(val_drugs)}개, 중복 {len(overlap)}개 - {status} (Sp={val_sp:.4f})")

# ============================================================================
# 4. v3 코드와 비교
# ============================================================================
print("\n" + "=" * 100)
print("[4] v3 GroupKFold 구현 확인")
print("=" * 100)

v3_script_path = base_dir / "20260414_re_pre_project_v3/step4_results/extended_eval_step2_groupkfold.py"
if v3_script_path.exists():
    print(f"✓ v3 스크립트 발견: {v3_script_path}")
    print("\nv3 GroupKFold 핵심 코드:")
    print("-" * 100)

    with open(v3_script_path, 'r') as f:
        lines = f.readlines()
        # GroupKFold 관련 라인 찾기
        for i, line in enumerate(lines[80:95], 80):
            print(f"{i:3d}: {line.rstrip()}")

    print("-" * 100)
    print("\nv3와 v4 비교:")
    print(f"  v3: features_df = pd.read_parquet('../features_slim.parquet')")
    print(f"      drug_ids = features_df['canonical_drug_id'].values")
    print(f"      gkf.split(X, y, groups=drug_ids)")
    print(f"\n  v4: (동일)")
    print(f"      features_df = pd.read_parquet('features_slim.parquet')")
    print(f"      drug_ids_cv = features_df['canonical_drug_id'].values[train_idx]")
    print(f"      gkf.split(oof_pred, y_cv, groups=drug_ids_cv)")
    print(f"\n  차이점:")
    print(f"    - v3: 전체 6366 샘플 사용 (X, y, drug_ids)")
    print(f"    - v4: CV 5092 샘플만 사용 (shuffled train_idx)")
    print(f"    → 이 차이가 결과 차이를 만들 수 있음")

else:
    print(f"❌ v3 스크립트를 찾을 수 없음")

# ============================================================================
# 5. v3 방식으로 재측정 (전체 데이터 사용)
# ============================================================================
print("\n" + "=" * 100)
print("[5] v3 방식으로 재측정 (전체 6366 샘플 사용)")
print("=" * 100)

# v3처럼 전체 데이터로 측정
# 단, OOF는 CV 5092만 있으므로, 전체 예측을 만들어야 함
# 간단히 CV OOF + Holdout predictions 결합

# Holdout predictions 로드
catboost_full_holdout = np.load(step4_dir / "model_04_catboost_holdout.npy")

# 전체 predictions 재구성 (shuffle 복원)
full_predictions = np.zeros(n_samples)
full_predictions[train_idx] = catboost_full_oof
full_predictions[holdout_idx] = catboost_full_holdout

print(f"✓ 전체 predictions 재구성")
print(f"  Shape: {full_predictions.shape}")
print(f"  전체 Spearman: {spearmanr(y_train_full, full_predictions)[0]:.4f}")

# v3 방식 GroupKFold
print(f"\nv3 방식 GroupKFold (전체 {n_samples} 샘플):")
print("-" * 100)

gkf_v3 = GroupKFold(n_splits=5)
fold_sps_v3 = []

for fold_idx, (_, val_idx) in enumerate(gkf_v3.split(full_predictions, y_train_full, groups=drug_ids_full), 1):
    val_true = y_train_full[val_idx]
    val_pred = full_predictions[val_idx]
    val_sp = spearmanr(val_true, val_pred)[0]
    fold_sps_v3.append(val_sp)

    print(f"  Fold {fold_idx}/5: Spearman={val_sp:.4f}")

mean_sp_v3 = np.mean(fold_sps_v3)
print(f"\n  평균 Spearman (v3 방식): {mean_sp_v3:.4f}")

# ============================================================================
# 6. 결과 요약 및 저장
# ============================================================================
print("\n" + "=" * 100)
print("[6] 결과 요약")
print("=" * 100)

summary = {
    "verification": {
        "group_basis": "canonical_drug_id",
        "cv_samples": len(drug_ids_cv),
        "unique_drugs_cv": len(np.unique(drug_ids_cv)),
        "unique_drugs_full": len(np.unique(drug_ids_full)),
        "fold_overlap_check": all_fold_results
    },
    "v4_method": {
        "description": "CV 5092 샘플만 사용 (shuffled 80/20 split)",
        "mean_spearman": np.mean([r['val_spearman'] for r in all_fold_results]),
        "std_spearman": np.std([r['val_spearman'] for r in all_fold_results])
    },
    "v3_method": {
        "description": "전체 6366 샘플 사용",
        "mean_spearman": float(mean_sp_v3),
        "std_spearman": float(np.std(fold_sps_v3))
    },
    "comparison": {
        "v4_vs_v3_diff": np.mean([r['val_spearman'] for r in all_fold_results]) - mean_sp_v3,
        "overlap_found": any(r['overlap_drugs'] > 0 for r in all_fold_results)
    }
}

# 핵심 발견
print(f"\n🔍 핵심 발견:")
print(f"  1. Group 기준: canonical_drug_id ✅")
print(f"  2. Train/Val 중복: {summary['comparison']['overlap_found']}")
if summary['comparison']['overlap_found']:
    print(f"     ❌ 중복 발견! GroupKFold이 제대로 작동하지 않음")
else:
    print(f"     ✅ 중복 없음! GroupKFold이 제대로 작동함")

print(f"  3. v4 방식 (CV only): {summary['v4_method']['mean_spearman']:.4f}")
print(f"  4. v3 방식 (Full): {summary['v3_method']['mean_spearman']:.4f}")
print(f"  5. 차이: {summary['comparison']['v4_vs_v3_diff']:+.4f}")

print(f"\n💡 결론:")
if abs(summary['comparison']['v4_vs_v3_diff']) > 0.05:
    print(f"  측정 방식의 차이가 결과에 영향을 줌")
    print(f"  v3 방식 (전체 데이터) 사용 권장")
else:
    print(f"  v4와 v3 방식의 차이가 작음")
    print(f"  두 방식 모두 신뢰 가능")

# 저장
output_path = output_dir / "groupkfold_verification.json"
with open(output_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✓ 검증 결과 저장: {output_path}")

print("\n" + "=" * 100)
print("GroupKFold 검증 완료!")
print("=" * 100)
