#!/usr/bin/env python3
"""Run one graph model from train_graph_models.py and append/update JSON results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import train_graph_models as m


MODEL_CONFIG = {
    "14_GraphSAGE": (m.GraphSAGEModel, {"hidden": 256, "out_dim": 128, "dropout": 0.3}),
    "15_GAT": (m.GATModel, {"hidden": 256, "out_dim": 128, "heads": 4, "dropout": 0.3}),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one graph model and append results.")
    p.add_argument("--model", required=True, choices=sorted(MODEL_CONFIG.keys()))
    p.add_argument("--features-uri", required=True)
    p.add_argument("--pair-features-uri", required=True)
    p.add_argument("--labels-uri", required=True)
    p.add_argument("--out-json", default="models/graph_results/graph_results.json")
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

    X, y, y_bin, sample_ids, drug_ids = m.load_data()

    cls, kwargs = MODEL_CONFIG[args.model]
    result = m.run_graph_cv(args.model, cls, dict(kwargs), X, y, y_bin, sample_ids, drug_ids)

    all_results = [r for r in _load_existing(out_path) if r.get("model") != args.model]
    all_results.append(result)
    all_results = sorted(all_results, key=lambda d: str(d.get("model", "")))
    out_path.write_text(json.dumps(all_results, indent=2, default=_convert), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
