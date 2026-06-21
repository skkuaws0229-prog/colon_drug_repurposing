#!/usr/bin/env python3
"""Run one ML model from train_ml_models.py and append/update JSON results.

Usage example:
  python models/run_ml_single.py --model 1_LightGBM \
    --features-uri runs/20260418_crc_v1/features/features.parquet \
    --pair-features-uri runs/20260418_crc_v1/pair_features/pair_features_newfe_v2.parquet \
    --labels-uri runs/20260418_crc_v1/features/labels.parquet \
    --out-json models/ml_results/ml_results.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import train_ml_models as m


MODEL_MAP = {
    "1_LightGBM": m.lgbm_model,
    "2_LightGBM_DART": m.lgbm_dart_model,
    "3_XGBoost": m.xgboost_model,
    "4_CatBoost": m.catboost_model,
    "5_RandomForest": m.rf_model,
    "6_ExtraTrees": m.extratrees_model,
    "7_Stacking_Ridge": m.stacking_model,
    "8_RSF": m.rsf_model,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run single ML model and persist results JSON.")
    p.add_argument("--model", required=True, choices=sorted(MODEL_MAP.keys()))
    p.add_argument("--features-uri", required=True)
    p.add_argument("--pair-features-uri", required=True)
    p.add_argument("--labels-uri", required=True)
    p.add_argument("--out-json", default="models/ml_results/ml_results.json")
    return p.parse_args()


def _convert(obj):
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
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

    # Override input paths in module.
    m.FEATURES_URI = args.features_uri
    m.PAIR_FEATURES_URI = args.pair_features_uri
    m.LABELS_URI = args.labels_uri

    X, y_reg, y_bin, feat_names, sample_ids, drug_ids = m.load_data()
    cv_splits = m.get_cv_splits(X, sample_ids, drug_ids)
    fn = MODEL_MAP[args.model]

    started = time.time()
    result = m.run_cv(args.model, fn, X, y_reg, y_bin, feat_names, cv_splits)
    result["elapsed_sec"] = time.time() - started

    # Keep RSF extra metrics aligned with main() behavior.
    if args.model == "8_RSF":
        c_indices, aurocs = [], []
        for fold_idx, (train_idx, val_idx) in enumerate(cv_splits):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y_reg[train_idx], y_reg[val_idx]
            model, _, _ = m.rsf_model(X_tr, y_tr, X_val, y_val, fold_idx, feat_names)
            extra = m.rsf_extra_metrics(model, X_tr, y_tr, X_val, y_val, fold_idx)
            c_indices.append(extra["c_index"])
            aurocs.append(extra["auroc"])
        result["c_index_mean"] = np.mean(c_indices)
        result["c_index_std"] = np.std(c_indices)
        result["auroc_mean"] = np.nanmean(aurocs)
        result["auroc_std"] = np.nanstd(aurocs)

    all_results = [r for r in _load_existing(out_path) if r.get("model") != args.model]
    all_results.append(result)
    all_results = sorted(all_results, key=lambda d: str(d.get("model", "")))
    out_path.write_text(json.dumps(all_results, indent=2, default=_convert), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
