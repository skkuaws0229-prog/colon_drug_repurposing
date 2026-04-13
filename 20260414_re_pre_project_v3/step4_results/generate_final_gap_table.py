#!/usr/bin/env python3
"""
전체 15개 모델 Gap 테이블 생성
"""
import json
import glob

models = []
for i in range(1, 16):
    json_files = glob.glob(f"model_{i:02d}.json") + glob.glob(f"model_{i:02d}_*.json")
    json_files = [f for f in json_files if not f.endswith('_old.json')]

    if not json_files:
        continue

    # Use the shortest filename (likely the new one without suffix)
    json_file = min(json_files, key=len)

    with open(json_file) as f:
        data = json.load(f)

    model_name = data.get("model", "Unknown")
    train_sp = data.get("train_spearman", None)
    oof_sp = data.get("oof_spearman", None)
    gap = data.get("gap", None)
    ratio = data.get("ratio", None)
    verdict = data.get("verdict", None)
    fold_std = data.get("fold_std", None)
    ensemble_pass = data.get("ensemble_pass", False)

    if train_sp is None and gap is not None and oof_sp is not None:
        train_sp = oof_sp + gap

    models.append({
        "id": i,
        "name": model_name,
        "train_sp": train_sp,
        "oof_sp": oof_sp,
        "gap": gap,
        "ratio": ratio,
        "fold_std": fold_std,
        "verdict": verdict,
        "ensemble_pass": ensemble_pass
    })

# Sort by model ID
models.sort(key=lambda x: x["id"])

print("="*120)
print("전체 15개 모델 Train Spearman & Gap 최종 테이블")
print("="*120)
print()
print(f"{'#':<4} {'모델명':<30} {'Train Sp':>12} {'OOF Sp':>12} {'Gap':>10} {'Ratio':>10} {'Fold Std':>12} {'판정':>12} {'앙상블':>8}")
print("-"*120)

for m in models:
    train_sp_str = f"{m['train_sp']:.4f}" if m['train_sp'] is not None else "N/A"
    oof_sp_str = f"{m['oof_sp']:.4f}" if m['oof_sp'] is not None else "N/A"
    gap_str = f"{m['gap']:.4f}" if m['gap'] is not None else "N/A"
    ratio_str = f"{m['ratio']:.4f}" if m['ratio'] is not None else "N/A"
    fold_std_str = f"{m['fold_std']:.4f}" if m['fold_std'] is not None else "N/A"
    verdict_str = m['verdict'] if m['verdict'] else "N/A"
    ensemble_str = "✅ PASS" if m['ensemble_pass'] else "❌ FAIL"

    print(f"{m['id']:<4} {m['name']:<30} {train_sp_str:>12} {oof_sp_str:>12} {gap_str:>10} {ratio_str:>10} {fold_std_str:>12} {verdict_str:>12} {ensemble_str:>8}")

print("="*120)

# Count by verdict
verdicts = [m['verdict'] for m in models if m['verdict']]
print(f"\n판정 요약:")
print(f"  NORMAL: {verdicts.count('NORMAL')}개")
print(f"  WARNING: {verdicts.count('WARNING')}개")
print(f"  OVERFITTING: {verdicts.count('OVERFITTING')}개")
print(f"  SEVERE: {verdicts.count('SEVERE')}개")
print(f"  N/A: {15 - len(verdicts)}개")

# Count ensemble pass
pass_count = sum(1 for m in models if m['ensemble_pass'])
print(f"\n앙상블 통과: {pass_count}/15개")
print("="*120)
