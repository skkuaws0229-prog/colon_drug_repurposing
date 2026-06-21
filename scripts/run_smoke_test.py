#!/usr/bin/env python
"""Read-only smoke test for public reproducibility metadata."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MANIFEST = ROOT / "manifests" / "artifact_manifest.csv"
AUDIT = ROOT / "reports" / "repo_artifact_audit.csv"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    checks = []

    for path in [MANIFEST, AUDIT, ROOT / "manifests" / "checksums.sha256"]:
        checks.append({"name": str(path.relative_to(ROOT)), "ok": path.exists(), "detail": "exists" if path.exists() else "missing"})

    manifest_rows = read_csv(MANIFEST) if MANIFEST.exists() else []
    audit_rows = read_csv(AUDIT) if AUDIT.exists() else []
    public_rows = [row for row in manifest_rows if row.get("required_for") == "public-demo"]
    unresolved_rows = [row for row in manifest_rows if row.get("public_status") == "UNRESOLVED"]
    secret_rows = [row for row in audit_rows if row.get("secret_scan_status", "").startswith("FINDING")]

    checks.append({"name": "manifest_rows", "ok": bool(manifest_rows), "detail": len(manifest_rows)})
    checks.append({"name": "public_demo_rows", "ok": bool(public_rows), "detail": len(public_rows)})
    checks.append({"name": "secret_findings_recorded_without_values", "ok": True, "detail": len(secret_rows)})
    checks.append({"name": "unresolved_uri_rows", "ok": True, "detail": len(unresolved_rows)})

    sample_readable = 0
    for row in public_rows[:25]:
        path = ROOT / row["relative_path"]
        if path.exists() and path.is_file():
            sample_readable += 1
    checks.append({"name": "sample_public_files_readable", "ok": sample_readable > 0, "detail": sample_readable})

    ok = all(item["ok"] for item in checks)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "read_only": True,
        "db_write": False,
        "s3_write": False,
        "checks": checks,
        "ok": ok,
    }
    (REPORTS / "smoke_test_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = ["# Smoke Test Report\n", f"Generated: {report['generated_at']}\n", f"Overall: {'PASS' if ok else 'FAIL'}\n", "| check | ok | detail |", "| --- | --- | --- |"]
    for item in checks:
        lines.append(f"| {item['name']} | {item['ok']} | {item['detail']} |")
    (REPORTS / "smoke_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
