#!/usr/bin/env python3
"""
Weight 파일 아키텍처 추가 확인
model_10_model.pt vs model_13_model.pt
"""
import torch
import json
from pathlib import Path

# 경로 설정
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")
step4_dir = base_dir / "20260414_re_pre_project_v3/step4_results"
output_dir = base_dir / "20260415_v4_ensemble_test/verification"

print("=" * 80)
print("Weight 파일 아키텍처 검증")
print("=" * 80)

# ============================================================================
# 1. Weight 파일 로드 및 아키텍처 확인
# ============================================================================
print("\n[1] Weight 파일 로드 및 state_dict keys 확인")
print("-" * 80)

flatmlp_weight = step4_dir / "model_10_model.pt"
crossattn_weight = step4_dir / "model_13_model.pt"

print(f"FlatMLP weight:        {flatmlp_weight}")
print(f"CrossAttention weight: {crossattn_weight}")

# FlatMLP 로드
print("\n▶ FlatMLP (model_10):")
try:
    flatmlp_state = torch.load(flatmlp_weight, map_location='cpu')
    flatmlp_keys = list(flatmlp_state.keys())
    print(f"  Total keys: {len(flatmlp_keys)}")
    print(f"  Keys:")
    for key in flatmlp_keys:
        shape = flatmlp_state[key].shape if hasattr(flatmlp_state[key], 'shape') else 'N/A'
        print(f"    - {key}: {shape}")
except Exception as e:
    print(f"  ❌ Error loading FlatMLP: {e}")
    flatmlp_state = None
    flatmlp_keys = []

# CrossAttention 로드
print("\n▶ CrossAttention (model_13):")
try:
    crossattn_state = torch.load(crossattn_weight, map_location='cpu')
    crossattn_keys = list(crossattn_state.keys())
    print(f"  Total keys: {len(crossattn_keys)}")
    print(f"  Keys:")
    for key in crossattn_keys:
        shape = crossattn_state[key].shape if hasattr(crossattn_state[key], 'shape') else 'N/A'
        print(f"    - {key}: {shape}")
except Exception as e:
    print(f"  ❌ Error loading CrossAttention: {e}")
    crossattn_state = None
    crossattn_keys = []

# ============================================================================
# 2. 파라미터 수 비교
# ============================================================================
print("\n[2] 파라미터 수 비교")
print("-" * 80)

def count_parameters(state_dict):
    """Count total parameters in state dict"""
    total = 0
    for key, param in state_dict.items():
        if hasattr(param, 'numel'):
            total += param.numel()
    return total

if flatmlp_state is not None:
    flatmlp_params = count_parameters(flatmlp_state)
    print(f"FlatMLP total parameters:        {flatmlp_params:,}")
else:
    flatmlp_params = 0

if crossattn_state is not None:
    crossattn_params = count_parameters(crossattn_state)
    print(f"CrossAttention total parameters: {crossattn_params:,}")
else:
    crossattn_params = 0

if flatmlp_params > 0 and crossattn_params > 0:
    diff = abs(flatmlp_params - crossattn_params)
    print(f"\nParameter difference: {diff:,}")
    if flatmlp_params == crossattn_params:
        print("⚠️  WARNING: 파라미터 수가 완전히 동일! (비정상)")
    elif crossattn_params > flatmlp_params:
        print(f"✅ OK: CrossAttention이 더 큼 (+{diff:,} params)")
    else:
        print(f"⚠️  WARNING: FlatMLP가 더 큼 (+{diff:,} params, 비정상)")

# ============================================================================
# 3. Layer 타입 분석
# ============================================================================
print("\n[3] Layer 타입 분석")
print("-" * 80)

def analyze_layer_types(keys, model_name):
    """Analyze layer types from state dict keys"""
    print(f"\n▶ {model_name}:")

    layer_types = {
        'Linear': 0,
        'Attention': 0,
        'MultiheadAttention': 0,
        'Conv': 0,
        'BatchNorm': 0,
        'Dropout': 0,
        'Embedding': 0,
        'Other': 0
    }

    unique_prefixes = set()

    for key in keys:
        # Extract layer prefix (before .weight or .bias)
        parts = key.split('.')
        if len(parts) >= 2:
            prefix = '.'.join(parts[:-1])
            unique_prefixes.add(prefix)

        # Count layer types
        if 'linear' in key.lower() or 'fc' in key.lower():
            layer_types['Linear'] += 1
        elif 'attention' in key.lower() or 'attn' in key.lower():
            if 'multihead' in key.lower():
                layer_types['MultiheadAttention'] += 1
            else:
                layer_types['Attention'] += 1
        elif 'conv' in key.lower():
            layer_types['Conv'] += 1
        elif 'bn' in key.lower() or 'batchnorm' in key.lower():
            layer_types['BatchNorm'] += 1
        elif 'dropout' in key.lower():
            layer_types['Dropout'] += 1
        elif 'embed' in key.lower():
            layer_types['Embedding'] += 1
        else:
            if not key.endswith('.weight') and not key.endswith('.bias'):
                layer_types['Other'] += 1

    print(f"  Layer type counts:")
    for layer_type, count in layer_types.items():
        if count > 0:
            print(f"    - {layer_type}: {count}")

    print(f"\n  Unique layer prefixes ({len(unique_prefixes)}):")
    for prefix in sorted(unique_prefixes):
        print(f"    - {prefix}")

    return layer_types, unique_prefixes

if flatmlp_keys:
    flatmlp_layers, flatmlp_prefixes = analyze_layer_types(flatmlp_keys, "FlatMLP")
else:
    flatmlp_layers, flatmlp_prefixes = {}, set()

if crossattn_keys:
    crossattn_layers, crossattn_prefixes = analyze_layer_types(crossattn_keys, "CrossAttention")
else:
    crossattn_layers, crossattn_prefixes = {}, set()

# ============================================================================
# 4. 아키텍처 비교 판정
# ============================================================================
print("\n[4] 아키텍처 비교 판정")
print("=" * 80)

# Keys 비교
if flatmlp_keys and crossattn_keys:
    keys_identical = (set(flatmlp_keys) == set(crossattn_keys))
    print(f"State dict keys 동일? {keys_identical}")

    if keys_identical:
        print("⚠️  CRITICAL WARNING: state_dict keys가 완전히 동일!")
        print("   → 두 모델이 같은 아키텍처일 가능성")
        print("   → 또는 한쪽 weight가 다른 쪽을 덮어쓴 것일 가능성")
    else:
        # Key 차이 확인
        only_flatmlp = set(flatmlp_keys) - set(crossattn_keys)
        only_crossattn = set(crossattn_keys) - set(flatmlp_keys)

        if only_flatmlp:
            print(f"\nFlatMLP에만 있는 keys ({len(only_flatmlp)}):")
            for key in sorted(only_flatmlp)[:10]:  # 처음 10개만
                print(f"  - {key}")
            if len(only_flatmlp) > 10:
                print(f"  ... and {len(only_flatmlp) - 10} more")

        if only_crossattn:
            print(f"\nCrossAttention에만 있는 keys ({len(only_crossattn)}):")
            for key in sorted(only_crossattn)[:10]:
                print(f"  - {key}")
            if len(only_crossattn) > 10:
                print(f"  ... and {len(only_crossattn) - 10} more")

# Attention layer 확인
print("\n아키텍처 기대:")
print("  FlatMLP:        Linear layer만 (Attention layer 없어야 함)")
print("  CrossAttention: Attention layer 있어야 함")

print("\n실제 확인:")
flatmlp_has_attn = flatmlp_layers.get('Attention', 0) + flatmlp_layers.get('MultiheadAttention', 0) > 0
crossattn_has_attn = crossattn_layers.get('Attention', 0) + crossattn_layers.get('MultiheadAttention', 0) > 0

print(f"  FlatMLP has Attention:        {flatmlp_has_attn}")
print(f"  CrossAttention has Attention: {crossattn_has_attn}")

if flatmlp_has_attn:
    print("\n⚠️  WARNING: FlatMLP에 Attention layer가 있음! (비정상)")

if not crossattn_has_attn:
    print("\n⚠️  WARNING: CrossAttention에 Attention layer가 없음! (비정상)")

# ============================================================================
# 5. 결과 저장
# ============================================================================
results = {
    "weight_files": {
        "flatmlp": {
            "path": str(flatmlp_weight),
            "file_size_bytes": flatmlp_weight.stat().st_size if flatmlp_weight.exists() else None,
            "total_keys": len(flatmlp_keys),
            "total_parameters": flatmlp_params,
            "state_dict_keys": flatmlp_keys,
            "layer_types": flatmlp_layers,
            "has_attention": flatmlp_has_attn
        },
        "crossattention": {
            "path": str(crossattn_weight),
            "file_size_bytes": crossattn_weight.stat().st_size if crossattn_weight.exists() else None,
            "total_keys": len(crossattn_keys),
            "total_parameters": crossattn_params,
            "state_dict_keys": crossattn_keys,
            "layer_types": crossattn_layers,
            "has_attention": crossattn_has_attn
        }
    },
    "comparison": {
        "keys_identical": keys_identical if flatmlp_keys and crossattn_keys else None,
        "params_identical": flatmlp_params == crossattn_params if flatmlp_params > 0 and crossattn_params > 0 else None,
        "param_difference": abs(flatmlp_params - crossattn_params) if flatmlp_params > 0 and crossattn_params > 0 else None
    },
    "판정": {}
}

# 판정
if keys_identical:
    results["판정"]["아키텍처"] = "⚠️ 완전 동일 (비정상)"
    results["판정"]["원인_추정"] = "같은 모델이거나 덮어쓰기 발생"
elif flatmlp_params == crossattn_params and flatmlp_params > 0:
    results["판정"]["아키텍처"] = "⚠️ 파라미터 수 동일 (의심)"
    results["판정"]["원인_추정"] = "우연히 같은 크기이거나 구조적 유사"
elif not crossattn_has_attn:
    results["판정"]["아키텍처"] = "⚠️ CrossAttention에 Attention 없음 (비정상)"
    results["판정"]["원인_추정"] = "잘못된 모델이 저장됨"
elif flatmlp_has_attn:
    results["판정"]["아키텍처"] = "⚠️ FlatMLP에 Attention 있음 (비정상)"
    results["판정"]["원인_추정"] = "잘못된 모델이 저장됨"
else:
    results["판정"]["아키텍처"] = "✅ 다른 구조 (정상)"
    results["판정"]["원인_추정"] = "예측 상관 0.98은 구조적 중복"

output_json = output_dir / "weight_architecture_check.json"
with open(output_json, "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n결과 저장: {output_json}")
print("\n검증 완료!")
