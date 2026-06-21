#!/usr/bin/env python
"""Verify local artifact existence, size, and SHA-256 from manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "artifact_manifest.csv"
SELF_GENERATED_METADATA = {
    "reports/repo_artifact_audit.csv",
    "reports/repo_artifact_audit.md",
    "reports/smoke_test_report.md",
    "reports/smoke_test_report.json",
    "manifests/artifact_manifest.csv",
    "manifests/checksums.sha256",
    "manifests/excluded_artifacts.csv",
}
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--profile", choices=["public-demo", "full-reproduction"], default="public-demo")
    parser.add_argument("--disease")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()

    root = Path(args.root)
    with Path(args.manifest).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    results = []
    for row in rows:
        if args.disease and row.get("disease", "").upper() != args.disease.upper():
            continue
        if args.profile == "public-demo" and row.get("required_for") != "public-demo":
            continue
        if row["relative_path"] in SELF_GENERATED_METADATA:
            results.append({"relative_path": row["relative_path"], "status": "SKIPPED_SELF_METADATA", "expected_size": int(row["size_bytes"] or 0)})
            continue
        path = root / row["relative_path"]
        item = {"relative_path": row["relative_path"], "status": "OK", "expected_size": int(row["size_bytes"] or 0)}
        if not path.exists():
            item["status"] = "MISSING"
        else:
            actual_size = path.stat().st_size
            item["actual_size"] = actual_size
            if actual_size != item["expected_size"]:
                item["status"] = "SIZE_MISMATCH"
            else:
                actual_sha = sha256_file(path)
                item["actual_sha256"] = actual_sha
                if actual_sha.lower() != row.get("sha256", "").lower():
                    item["status"] = "SHA256_MISMATCH"
        results.append(item)

    counts = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(json.dumps({"checked": len(results), "counts": counts}, indent=2))
    for item in results:
        if item["status"] != "OK":
            print(f"{item['status']} {item['relative_path']}")
    return 0 if set(counts) <= {"OK", "SKIPPED_SELF_METADATA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
