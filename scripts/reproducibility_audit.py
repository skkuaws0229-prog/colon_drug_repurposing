#!/usr/bin/env python
"""Generate reproducibility audit reports and artifact manifests.

The script is intentionally read-only for project inputs. It writes only:
- reports/repo_artifact_audit.csv
- reports/repo_artifact_audit.md
- manifests/artifact_manifest.csv
- manifests/checksums.sha256
- manifests/excluded_artifacts.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MANIFESTS = ROOT / "manifests"
REPORTS.mkdir(exist_ok=True)
MANIFESTS.mkdir(exist_ok=True)

MIB = 1024 * 1024
SMALL_LIMIT = 20 * MIB
TEXT_SCAN_LIMIT = 50 * MIB

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".nextflow",
    "work",
    "tmp",
    ".tmp_pydeps",
    ".npm-cache",
    "catboost_info",
}
TEMP_DIR_NAMES = {"tmp", "logs", "runs", "outputs", "downloads", "data_cache", ".npm-cache", ".tmp_pydeps"}
SECRET_DIR_NAMES = {"secrets", "keys"}
NESTED_PUBLISH_DIRS = {"drug_repurposing_publish"}

CODE_EXT = {".py", ".ps1", ".sql", ".sh", ".ts", ".tsx", ".js", ".css", ".html", ".cypher", ".nf", ".cmd"}
CONFIG_EXT = {".yaml", ".yml", ".toml", ".json", ".config", ".ini", ".example"}
DOC_EXT = {".md", ".txt"}
SMALL_RESULT_EXT = {".csv", ".json", ".log", ".npy"}
S3_RELEASE_EXT = {
    ".pt",
    ".pth",
    ".ckpt",
    ".pkl",
    ".joblib",
    ".parquet",
    ".h5",
    ".hdf5",
    ".zip",
    ".tar",
    ".gz",
    ".dump",
    ".db",
    ".sqlite",
    ".sqlite3",
}
SECRET_EXT = {".pem", ".key", ".p12", ".pfx", ".crt"}
RAW_DATA_EXT = {".fastq", ".fq", ".bam", ".sam", ".vcf", ".gct", ".gctx", ".tsv"}

SECRET_PATTERNS = [
    ("AWS_ACCESS_KEY_ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("OPENAI_API_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GENERIC_TOKEN", re.compile(r"(?i)\b(token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*['\"]?[^'\"\s]{8,}")),
    ("SECRET_ASSIGNMENT", re.compile(r"(?i)\b(secret|password|passwd|pwd)\b\s*[:=]\s*['\"]?[^'\"\s]{6,}")),
    ("DATABASE_URL", re.compile(r"(?i)\bDATABASE_URL\b\s*[:=]\s*['\"]?[^'\"\s]+")),
    ("POSTGRES_URI", re.compile(r"(?i)postgres(?:ql)?://[^\s'\"]+")),
    ("NEO4J_URI", re.compile(r"(?i)neo4j(?:\+s)?://[^\s'\"]+|bolt(?:\+s)?://[^\s'\"]+")),
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
S3_PATTERN = re.compile(r"s3://[^\s\)\]\}\'\"<>]+")
DATE_PATTERN = re.compile(r"(20\d{6})")
DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "PAAD", "PDAC", "HNSC", "STAD", "LUNG", "COLON", "RA", "PAH", "IPF", "PSORIASIS"]


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def get_tracked_files() -> set[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True, encoding="utf-8", errors="ignore")
        return set(out.splitlines())
    except Exception:
        return set()


def sha256_file(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except Exception:
        return "HASH_ERROR"


def probably_text(path: Path, size: int, ext: str) -> bool:
    if ext in CODE_EXT | CONFIG_EXT | DOC_EXT | {".csv", ".tsv", ".log", ".json", ".svg"}:
        return True
    if size > TEXT_SCAN_LIMIT:
        return False
    try:
        sample = path.open("rb").read(8192)
        if b"\x00" in sample:
            return False
        sample.decode("utf-8", errors="strict")
        return True
    except Exception:
        return False


def scan_text(path: Path, rp: str, size: int, ext: str, parts: set[str]) -> tuple[list[dict], list[dict], str]:
    name = path.name.lower()
    if ext in SECRET_EXT or name == ".env" or ".env" in name:
        return [{"relative_path": rp, "line": 0, "type": "SECRET_FILE_PATTERN"}], [], "FINDING:1"
    if parts & (EXCLUDE_DIR_NAMES | TEMP_DIR_NAMES | NESTED_PUBLISH_DIRS):
        return [], [], "SKIPPED_EXCLUDED_PATH"
    if not probably_text(path, size, ext):
        return [], [], "NOT_SCANNED_BINARY"
    if size > TEXT_SCAN_LIMIT:
        return [], [], "SKIPPED_LARGE_TEXT"

    findings: list[dict] = []
    s3_refs: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line_no, line in enumerate(handle, 1):
                for kind, pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append({"relative_path": rp, "line": line_no, "type": kind})
                for match in S3_PATTERN.findall(line):
                    s3_refs.append({"relative_path": rp, "line": line_no, "uri": match.rstrip(".,;`)]}")})
    except Exception:
        return [], [], "SCAN_ERROR"
    return findings, s3_refs, f"FINDING:{len(findings)}" if findings else "SCANNED"


def classify(rp: str, ext: str, size: int, secret_status: str, parts: set[str], name: str) -> tuple[str, str, str]:
    if secret_status.startswith("FINDING"):
        return "git_exclude", "exclude_from_git", "secret pattern detected; keep out of public Git"
    if ext in SECRET_EXT or name == ".env" or ".env" in name:
        return "git_exclude", "exclude_from_git", "secret/config credential file pattern"
    if parts & SECRET_DIR_NAMES:
        return "git_exclude", "exclude_from_git", "path is under secrets/keys directory"
    if parts & NESTED_PUBLISH_DIRS:
        return "git_exclude", "exclude_from_git", "nested publish clone; do not include inside reproducibility repo"
    if parts & EXCLUDE_DIR_NAMES:
        return "git_exclude", "exclude_from_git", "cache/runtime/dependency directory"
    if ext in S3_RELEASE_EXT:
        return "s3_or_release", "externalize_artifact", "large/model/data artifact extension"
    if ext in RAW_DATA_EXT:
        return "s3_or_release", "externalize_artifact", "raw or tabular data artifact"
    if size > SMALL_LIMIT:
        return "s3_or_release", "externalize_artifact", "file exceeds 20 MiB threshold"
    if ext in CODE_EXT | CONFIG_EXT | DOC_EXT:
        return "github", "include_in_git", "source/config/documentation file"
    if ext in SMALL_RESULT_EXT and size <= SMALL_LIMIT:
        if parts & TEMP_DIR_NAMES:
            return "git_exclude", "exclude_from_git", "temporary/cache result path"
        return "github", "include_in_git", "small public result artifact under 20 MiB"
    if ext == ".tfevents":
        return "s3_or_release", "externalize_artifact", "training telemetry artifact"
    return "review", "human_review", "file type or provenance needs human decision"


def infer_disease(rp: str) -> str:
    upper = rp.upper()
    for disease in DISEASES:
        if disease in upper:
            return "COAD" if disease == "COLON" else disease
    return ""


def infer_version(rp: str) -> str:
    match = DATE_PATTERN.search(rp)
    return match.group(1) if match else ""


def infer_artifact_type(ext: str, rp: str) -> str:
    lower = rp.lower()
    if ext in {".pt", ".pth", ".ckpt", ".pkl", ".joblib", ".h5", ".hdf5"}:
        return "model_artifact"
    if ext in {".parquet", ".csv", ".tsv", ".npy", ".npz", ".json"}:
        if any(token in lower for token in ["result", "report", "summary", "validation", "candidate", "admet", "metabric"]):
            return "result_artifact"
        return "data_artifact"
    if ext in {".log", ".tfevents"}:
        return "run_log"
    if ext in {".md", ".pdf", ".docx", ".html"}:
        return "documentation_artifact"
    if ext in CODE_EXT:
        return "source_code"
    if ext in CONFIG_EXT:
        return "configuration"
    return "other"


def collect_files() -> list[tuple[Path, str, int, str]]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            stat = path.stat()
            files.append((path, relpath(path), stat.st_size, path.suffix.lower()))
        except Exception:
            continue
    return files


def main() -> int:
    tracked = get_tracked_files()
    files = collect_files()
    rows: list[dict] = []
    checksums: list[str] = []
    secret_findings: list[dict] = []
    s3_refs: list[dict] = []
    s3_by_basename: defaultdict[str, set[str]] = defaultdict(set)
    s3_by_rel: defaultdict[str, set[str]] = defaultdict(set)

    for index, (path, rp, size, ext) in enumerate(files, 1):
        parts = set(Path(rp).parts)
        digest = sha256_file(path)
        findings, refs, scan_status = scan_text(path, rp, size, ext, parts)
        secret_findings.extend(findings)
        for ref in refs:
            s3_refs.append(ref)
            s3_by_basename[Path(ref["uri"]).name].add(ref["uri"])
            s3_by_rel[rp].add(ref["uri"])

        storage, action, reason = classify(rp, ext, size, scan_status, parts, path.name.lower())
        rows.append(
            {
                "relative_path": rp,
                "extension": ext,
                "size_bytes": size,
                "git_tracked": "YES" if rp in tracked else "NO",
                "sha256": digest,
                "secret_scan_status": scan_status,
                "recommended_storage": storage,
                "recommended_action": action,
                "reason": reason,
            }
        )
        checksums.append(f"{digest}  {rp}")
        if index % 5000 == 0:
            print(f"processed {index}/{len(files)}", flush=True)

    def resolve_uri(rp: str) -> tuple[str, str]:
        if len(s3_by_rel.get(rp, set())) == 1:
            return "s3", next(iter(s3_by_rel[rp]))
        basename = Path(rp).name
        if len(s3_by_basename.get(basename, set())) == 1:
            return "s3", next(iter(s3_by_basename[basename]))
        return "UNRESOLVED", ""

    manifest_rows = []
    excluded_rows = []
    for index, row in enumerate(rows, 1):
        location, uri = resolve_uri(row["relative_path"])
        if row["recommended_storage"] == "github":
            location, uri, public_status = "github", "", "PUBLIC_CANDIDATE"
        elif row["recommended_storage"] == "s3_or_release":
            public_status = "REQUIRES_S3_ACCESS" if uri else "UNRESOLVED"
        elif row["recommended_storage"] == "git_exclude":
            public_status = "EXCLUDED"
        else:
            public_status = "NEEDS_REVIEW" if uri else "UNRESOLVED"

        manifest = {
            "artifact_id": f"artifact-{index:06d}",
            "relative_path": row["relative_path"],
            "artifact_type": infer_artifact_type(row["extension"], row["relative_path"]),
            "disease": infer_disease(row["relative_path"]),
            "version": infer_version(row["relative_path"]),
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
            "storage_location": location,
            "storage_uri": uri,
            "required_for": "public-demo" if row["recommended_storage"] == "github" else "full-reproduction",
            "public_status": public_status,
            "generation_script": "",
            "reason": row["reason"],
        }
        manifest_rows.append(manifest)
        if row["recommended_storage"] != "github":
            excluded_rows.append(manifest)

    audit_csv = REPORTS / "repo_artifact_audit.csv"
    with audit_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest_fields = [
        "artifact_id",
        "relative_path",
        "artifact_type",
        "disease",
        "version",
        "size_bytes",
        "sha256",
        "storage_location",
        "storage_uri",
        "required_for",
        "public_status",
        "generation_script",
        "reason",
    ]
    with (MANIFESTS / "artifact_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(manifest_rows)
    with (MANIFESTS / "excluded_artifacts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(excluded_rows)
    (MANIFESTS / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    by_storage = Counter(row["recommended_storage"] for row in rows)
    by_action = Counter(row["recommended_action"] for row in rows)
    by_secret_type = Counter(item["type"] for item in secret_findings)
    unresolved = sum(1 for row in manifest_rows if row["public_status"] == "UNRESOLVED")

    md = [
        "# Repository Artifact Audit\n",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}\n",
        f"Project root: `{ROOT}`\n",
        "## Summary\n",
        f"- Files scanned: {len(rows)}",
        f"- Git tracked files detected: {sum(1 for row in rows if row['git_tracked'] == 'YES')}",
        f"- Secret findings: {len(secret_findings)}",
        f"- S3 URI references found in text files: {len(s3_refs)}",
        f"- Manifest unresolved URI rows: {unresolved}\n",
        "## Recommended Storage\n",
    ]
    md.extend(f"- {key}: {value}" for key, value in by_storage.most_common())
    md.append("\n## Recommended Actions\n")
    md.extend(f"- {key}: {value}" for key, value in by_action.most_common())
    md.append("\n## Secret Scan Findings by Type\n")
    md.extend((f"- {key}: {value}" for key, value in by_secret_type.most_common()) or ["- None detected"])
    md.append("\n## Secret Finding Locations\n")
    if secret_findings:
        md.extend(["Raw secret values are intentionally omitted.\n", "| relative_path | line | type |", "| --- | ---: | --- |"])
        for finding in secret_findings[:500]:
            md.append(f"| `{finding['relative_path']}` | {finding['line']} | {finding['type']} |")
        if len(secret_findings) > 500:
            md.append(f"\nOnly first 500 findings shown. Full count: {len(secret_findings)}.")
    else:
        md.append("No secret findings detected by fallback scanner.")
    md.extend(["\n## Largest Files\n", "| relative_path | size_bytes | recommended_storage | reason |", "| --- | ---: | --- | --- |"])
    for row in sorted(rows, key=lambda item: int(item["size_bytes"]), reverse=True)[:30]:
        md.append(f"| `{row['relative_path']}` | {row['size_bytes']} | {row['recommended_storage']} | {row['reason']} |")
    md.extend(
        [
            "\n## Notes\n",
            "- `gitleaks` was not available; Python fallback scanner was used.",
            "- S3 URIs are recorded only when exact `s3://...` strings were found in existing text files.",
            "- UNRESOLVED means no verified URI was found locally; no placeholder URI was generated.",
        ]
    )
    (REPORTS / "repo_artifact_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "files_scanned": len(rows),
                "recommended_storage": dict(by_storage),
                "recommended_action": dict(by_action),
                "secret_findings": len(secret_findings),
                "s3_uri_references": len(s3_refs),
                "unresolved_uri_rows": unresolved,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
