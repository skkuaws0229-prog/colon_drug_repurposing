#!/usr/bin/env python3
"""Run one DL model from train_dl_models.py and append/update JSON results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import train_dl_models as m


MODEL_CONFIG = {
    # Fast mode for interactive execution; can be re-run with larger epochs later.
    "9_ResidualMLP": (m.ResidualMLP, {"hidden": 512, "n_blocks": 3, "dropout": 0.3}, {"epochs": 20, "lr": 1e-3, "batch_size": 256}),
    "10_FlatMLP": (m.FlatMLP, {"layers": [1024, 512, 256], "dropout": 0.3}, {"epochs": 20, "lr": 1e-3, "batch_size": 256}),
    "11_TabNet": (m.TabNet, {"n_steps": 3, "hidden": 256, "dropout": 0.3}, {"epochs": 20, "lr": 1e-3, "batch_size": 256}),
    "12_FT_Transformer": (m.FTTransformer, {"d_model": 128, "nhead": 4, "n_layers": 2, "dropout": 0.2}, {"epochs": 20, "lr": 5e-4, "batch_size": 128}),
    "13_Cross_Attention": (m.CrossAttentionNet, {"sample_dim": 18311, "d_model": 128, "nhead": 4, "dropout": 0.2}, {"epochs": 20, "lr": 5e-4, "batch_size": 256}),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one DL model and append results.")
    p.add_argument("--model", required=True, choices=sorted(MODEL_CONFIG.keys()))
    p.add_argument("--features-uri", required=True)
    p.add_argument("--pair-features-uri", required=True)
    p.add_argument("--labels-uri", required=True)
    p.add_argument("--out-json", default="models/dl_results/dl_results.json")
    return p.parse_args()


def _convert(obj):
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    return obj


def _load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def main() -> None:
    args = parse_args()
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    m.FEATURES_URI = args.features_uri
    m.PAIR_FEATURES_URI = args.pair_features_uri
    m.LABELS_URI = args.labels_uri

    X, y, sample_ids, drug_ids = m.load_data()
    cv_splits = m.get_cv_splits(X, sample_ids, drug_ids)
    in_dim = X.shape[1]

    cls, kwargs, train_kwargs = MODEL_CONFIG[args.model]
    kwargs = dict(kwargs)
    kwargs["in_dim"] = in_dim
    result = m.run_dl_cv(args.model, cls, kwargs, X, y, cv_splits, **train_kwargs)

    all_results = [r for r in _load_existing(out_path) if r.get("model") != args.model]
    all_results.append(result)
    all_results = sorted(all_results, key=lambda d: str(d.get("model", "")))
    out_path.write_text(json.dumps(all_results, indent=2, default=_convert), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
