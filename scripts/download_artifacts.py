#!/usr/bin/env python
"""Download artifacts declared in manifests/artifact_manifest.csv.

Default behavior is dry-run. Real downloads require --no-dry-run and a verified
storage_uri. Missing or UNRESOLVED URIs are reported but never invented.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "artifact_manifest.csv"
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


def load_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def selected_rows(rows: list[dict], profile: str, disease: str | None) -> list[dict]:
    selected = []
    for row in rows:
        if disease and row.get("disease", "").upper() != disease.upper():
            continue
        if profile == "public-demo" and row.get("required_for") != "public-demo":
            continue
        selected.append(row)
    return selected


def download_s3_with_boto3(uri: str, destination: Path) -> bool:
    try:
        import boto3  # type: ignore
    except Exception:
        return False
    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(bucket, key, str(destination))
    return True


def download_s3_with_aws_cli(uri: str, destination: Path) -> bool:
    aws = shutil.which("aws")
    if not aws:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call([aws, "s3", "cp", uri, str(destination)])
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--profile", choices=["public-demo", "full-reproduction"], default="public-demo")
    parser.add_argument("--disease")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--no-dry-run", action="store_true", help="Perform downloads. Default is dry-run.")
    parser.add_argument("--output-root", default=str(ROOT))
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_root = Path(args.output_root)
    dry_run = not args.no_dry_run
    rows = selected_rows(load_manifest(manifest_path), args.profile, args.disease)

    unresolved = 0
    downloaded = 0
    checked = 0
    mismatched = 0
    local_github = 0

    for row in rows:
        rel = row["relative_path"]
        uri = row.get("storage_uri", "")
        status = row.get("public_status", "")
        destination = output_root / rel
        if row.get("storage_location") == "github":
            local_github += 1
            continue
        if not uri or row.get("storage_location") == "UNRESOLVED" or status == "UNRESOLVED":
            unresolved += 1
            print(f"UNRESOLVED {rel}")
            continue
        if not uri.startswith("s3://"):
            print(f"SKIP_NON_S3 {rel} {uri}")
            continue
        if dry_run:
            print(f"DRY_RUN download {uri} -> {destination}")
            continue
        if not download_s3_with_boto3(uri, destination):
            if not download_s3_with_aws_cli(uri, destination):
                print(f"ERROR no boto3 or aws cli available for {uri}", file=sys.stderr)
                return 2
        downloaded += 1
        if args.verify:
            checked += 1
            actual = sha256_file(destination)
            if actual.lower() != row.get("sha256", "").lower():
                mismatched += 1
                print(f"MISMATCH {rel}")
            else:
                print(f"OK {rel}")

    print(f"summary selected={len(rows)} local_github={local_github} dry_run={dry_run} downloaded={downloaded} unresolved={unresolved} checked={checked} mismatched={mismatched}")
    return 1 if mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
