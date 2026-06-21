#!/usr/bin/env python
"""Validate S3-first feature engineering outputs without full data downloads."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
import pandas as pd
import pyarrow.parquet as pq
import s3fs


REQUIRED_FILES = [
    "features.parquet",
    "labels.parquet",
    "preprocessing_stats.json",
    "feature_selection_log.json",
    "features_slim.parquet",
]

OPTIONAL_FILES = [
    "feature_manifest.json",
    "feature_qc_report.json",
    "leakage_check_report.json",
    "schema_report.json",
]

LEAKAGE_KEYWORDS = [
    "ic50",
    "ln_ic50",
    "auc",
    "z_score",
    "response",
    "sensitive",
    "label",
    "target",
    "y_log_ic50",
    "raw_ic50",
    "raw_auc",
    "prediction",
    "pred",
    "score",
]


def normalize_s3_prefix(uri: str) -> str:
    if not uri.startswith("s3://"):
        raise ValueError("--s3-fe-output must start with s3://")
    return uri.rstrip("/") + "/"


def split_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def head_s3_object(s3_client: Any, uri: str) -> dict[str, Any]:
    bucket, key = split_s3_uri(uri)
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
    except s3_client.exceptions.NoSuchKey:
        return {"exists": False, "size_bytes": None}
    except Exception as exc:
        code = getattr(getattr(exc, "response", None), "get", lambda *_: {})("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return {"exists": False, "size_bytes": None}
        raise
    return {
        "exists": True,
        "size_bytes": int(response.get("ContentLength", 0)),
        "last_modified": response.get("LastModified").isoformat()
        if response.get("LastModified")
        else None,
    }


def parquet_metadata(fs: s3fs.S3FileSystem, uri: str) -> dict[str, Any]:
    with fs.open(uri, "rb") as handle:
        parquet_file = pq.ParquetFile(handle)
        schema_names = list(parquet_file.schema_arrow.names)
        metadata = parquet_file.metadata
        return {
            "parquet_file": parquet_file,
            "row_count": metadata.num_rows,
            "column_count": len(schema_names),
            "columns": schema_names,
            "metadata": metadata,
            "num_row_groups": metadata.num_row_groups,
        }


def duplicate_columns(columns: list[str]) -> list[str]:
    counts = Counter(columns)
    return sorted([name for name, count in counts.items() if count > 1])


def leakage_columns(columns: list[str]) -> list[dict[str, str]]:
    pattern_by_keyword = {
        keyword: re.compile(re.escape(keyword), flags=re.IGNORECASE) for keyword in LEAKAGE_KEYWORDS
    }
    matches: list[dict[str, str]] = []
    for column in columns:
        for keyword, pattern in pattern_by_keyword.items():
            if pattern.search(column):
                matches.append({"column": column, "keyword": keyword})
                break
    return matches


def _clean_stat_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def column_stats_from_footer(parquet_info: dict[str, Any], null_threshold: float) -> dict[str, Any]:
    metadata = parquet_info["metadata"]
    columns = parquet_info["columns"]
    total_rows = int(parquet_info["row_count"])
    high_null_columns: list[dict[str, Any]] = []
    all_null_columns: list[dict[str, Any]] = []
    constant_columns: list[dict[str, Any]] = []
    stats_unavailable: list[str] = []

    for col_idx, column in enumerate(columns):
        null_count = 0
        has_null_counts = True
        has_minmax = True
        non_null_values = 0
        min_value = None
        max_value = None

        for rg_idx in range(metadata.num_row_groups):
            rg = metadata.row_group(rg_idx)
            col_meta = rg.column(col_idx)
            stats = col_meta.statistics
            if stats is None:
                has_null_counts = False
                has_minmax = False
                break

            if stats.null_count is None:
                has_null_counts = False
            else:
                null_count += int(stats.null_count)

            if not stats.has_min_max:
                has_minmax = False
            else:
                rg_min = _clean_stat_value(stats.min)
                rg_max = _clean_stat_value(stats.max)
                if rg_min is not None and rg_max is not None:
                    min_value = rg_min if min_value is None or rg_min < min_value else min_value
                    max_value = rg_max if max_value is None or rg_max > max_value else max_value

            if stats.null_count is not None:
                non_null_values += int(rg.num_rows) - int(stats.null_count)

        if not has_null_counts:
            stats_unavailable.append(column)
            continue

        null_ratio = null_count / total_rows if total_rows else 1.0
        if null_ratio >= null_threshold:
            high_null_columns.append(
                {"column": column, "null_ratio": round(null_ratio, 6), "null_count": null_count}
            )
        if total_rows > 0 and null_count == total_rows:
            all_null_columns.append(
                {"column": column, "null_ratio": 1.0, "null_count": null_count}
            )

        if has_minmax and non_null_values > 0 and min_value == max_value:
            constant_columns.append({"column": column, "value": repr(min_value)})

    return {
        "high_null_columns": high_null_columns,
        "all_null_columns": all_null_columns,
        "constant_columns": constant_columns,
        "stats_unavailable_columns": stats_unavailable,
    }


def sample_parquet(
    fs: s3fs.S3FileSystem,
    uri: str,
    columns: list[str],
    sample_rows: int,
) -> pd.DataFrame:
    if not columns or sample_rows <= 0:
        return pd.DataFrame()
    with fs.open(uri, "rb") as handle:
        parquet_file = pq.ParquetFile(handle)
        batches = []
        rows_seen = 0
        for batch in parquet_file.iter_batches(
            batch_size=min(sample_rows, 8192),
            columns=columns,
            use_threads=True,
        ):
            if rows_seen >= sample_rows:
                break
            take_rows = min(batch.num_rows, sample_rows - rows_seen)
            batches.append(batch.slice(0, take_rows))
            rows_seen += take_rows
        if not batches:
            return pd.DataFrame(columns=columns)
        return pd.concat([batch.to_pandas() for batch in batches], ignore_index=True)


def sample_stats_for_unavailable(
    fs: s3fs.S3FileSystem,
    uri: str,
    columns: list[str],
    sample_rows: int,
    null_threshold: float,
) -> dict[str, Any]:
    if not columns:
        return {"sample_high_null_columns": [], "sample_constant_columns": []}
    sample = sample_parquet(fs, uri, columns, sample_rows)
    sample_high_null: list[dict[str, Any]] = []
    sample_constant: list[dict[str, Any]] = []
    for column in sample.columns:
        null_ratio = float(sample[column].isna().mean()) if len(sample) else 1.0
        if null_ratio >= null_threshold:
            sample_high_null.append(
                {"column": column, "sample_null_ratio": round(null_ratio, 6), "sample_rows": len(sample)}
            )
        non_null = sample[column].dropna()
        if len(non_null) > 0 and non_null.nunique(dropna=True) == 1:
            sample_constant.append(
                {"column": column, "sample_value": repr(non_null.iloc[0]), "sample_rows": len(sample)}
            )
    return {
        "sample_high_null_columns": sample_high_null,
        "sample_constant_columns": sample_constant,
    }


def validate_parquet(
    fs: s3fs.S3FileSystem,
    uri: str,
    null_threshold: float,
    sample_rows: int,
    check_stats: bool,
) -> dict[str, Any]:
    info = parquet_metadata(fs, uri)
    result = {
        "row_count": info["row_count"],
        "column_count": info["column_count"],
        "num_row_groups": info["num_row_groups"],
        "columns": info["columns"],
        "columns_preview": info["columns"][:30],
        "duplicate_columns": duplicate_columns(info["columns"]),
    }
    if check_stats:
        footer_stats = column_stats_from_footer(info, null_threshold)
        sampled_stats = sample_stats_for_unavailable(
            fs,
            uri,
            footer_stats["stats_unavailable_columns"][:200],
            sample_rows,
            null_threshold,
        )
        result.update(footer_stats)
        result.update(sampled_stats)
    return result


def status_line(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def render_markdown(summary: dict[str, Any]) -> str:
    checks = summary["checks"]
    files = summary["files"]
    parquet = summary["parquet"]
    failures = summary["failures"]

    lines = [
        f"# FE Validation Summary",
        "",
        f"- Result: **{summary['result']}**",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- S3 FE output: `{summary['s3_fe_output']}`",
        "",
        "## Checks",
    ]
    for name, payload in checks.items():
        lines.append(f"- {name}: **{status_line(payload['pass'])}** - {payload['detail']}")

    lines.extend(["", "## Files"])
    for name, payload in files.items():
        size = payload.get("size_bytes")
        size_text = "missing" if size is None else f"{size} bytes"
        required = "required" if name in REQUIRED_FILES else "optional"
        lines.append(f"- `{name}` ({required}): exists={payload['exists']}, size={size_text}")

    lines.extend(["", "## Parquet Metadata"])
    for name in ["features.parquet", "labels.parquet", "features_slim.parquet"]:
        payload = parquet.get(name)
        if not payload:
            continue
        lines.append(
            f"- `{name}`: rows={payload.get('row_count')}, columns={payload.get('column_count')}, "
            f"row_groups={payload.get('num_row_groups')}"
        )

    if failures:
        lines.extend(["", "## Failures"])
        for failure in failures:
            lines.append(f"- {failure}")

    leakage = summary["problem_columns"].get("leakage_columns", {})
    all_null = summary["problem_columns"].get("all_null_columns", {})
    duplicate = summary["problem_columns"].get("duplicate_columns", {})
    constant = summary["problem_columns"].get("constant_columns", {})
    high_null = summary["problem_columns"].get("high_null_columns", {})

    lines.extend(["", "## Problem Columns"])
    lines.append(f"- Leakage columns: `{json.dumps(leakage, ensure_ascii=False)}`")
    lines.append(f"- Duplicate columns: `{json.dumps(duplicate, ensure_ascii=False)}`")
    lines.append(f"- All-null feature columns: `{json.dumps(all_null, ensure_ascii=False)}`")
    lines.append(f"- Constant columns: `{json.dumps(constant, ensure_ascii=False)}`")
    lines.append(f"- High-null columns: `{json.dumps(high_null, ensure_ascii=False)}`")
    lines.append("")
    return "\n".join(lines)


def write_text_s3(fs: s3fs.S3FileSystem, uri: str, content: str) -> None:
    with fs.open(uri, "w", encoding="utf-8") as handle:
        handle.write(content)


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    s3_prefix = normalize_s3_prefix(args.s3_fe_output)
    fs = s3fs.S3FileSystem(anon=False)
    s3_client = boto3.client("s3")

    files: dict[str, dict[str, Any]] = {}
    for filename in REQUIRED_FILES + OPTIONAL_FILES:
        uri = s3_prefix + filename
        files[filename] = head_s3_object(s3_client, uri)
        files[filename]["uri"] = uri

    parquet: dict[str, dict[str, Any]] = {}
    problem_columns = {
        "leakage_columns": {},
        "duplicate_columns": {},
        "all_null_columns": {},
        "constant_columns": {},
        "high_null_columns": {},
    }

    for filename in ["features.parquet", "labels.parquet", "features_slim.parquet"]:
        file_info = files[filename]
        if not file_info["exists"] or file_info.get("size_bytes", 0) == 0:
            continue
        try:
            check_stats = filename in {"features.parquet", "features_slim.parquet"}
            parquet[filename] = validate_parquet(
                fs,
                file_info["uri"],
                null_threshold=args.null_threshold,
                sample_rows=args.sample_rows,
                check_stats=check_stats,
            )
        except Exception as exc:
            parquet[filename] = {"error": repr(exc)}

    for filename in ["features.parquet", "features_slim.parquet"]:
        payload = parquet.get(filename, {})
        if "columns" in payload:
            problem_columns["leakage_columns"][filename] = leakage_columns(payload["columns"])
        if payload.get("duplicate_columns"):
            problem_columns["duplicate_columns"][filename] = payload["duplicate_columns"]
        if payload.get("all_null_columns"):
            problem_columns["all_null_columns"][filename] = payload["all_null_columns"]
        if payload.get("constant_columns"):
            problem_columns["constant_columns"][filename] = payload["constant_columns"]
        if payload.get("high_null_columns"):
            problem_columns["high_null_columns"][filename] = payload["high_null_columns"]

    labels_payload = parquet.get("labels.parquet", {})
    if labels_payload.get("duplicate_columns"):
        problem_columns["duplicate_columns"]["labels.parquet"] = labels_payload["duplicate_columns"]

    failures: list[str] = []
    checks: dict[str, dict[str, Any]] = {}

    missing_required = [name for name in REQUIRED_FILES if not files[name]["exists"]]
    checks["required_files_exist"] = {
        "pass": not missing_required,
        "detail": "all required files found" if not missing_required else f"missing: {missing_required}",
    }
    if missing_required:
        failures.append(f"Missing required files: {missing_required}")

    zero_byte_required = [
        name for name in REQUIRED_FILES if files[name]["exists"] and files[name].get("size_bytes", 0) == 0
    ]
    checks["required_files_non_empty"] = {
        "pass": not zero_byte_required,
        "detail": "all required files are non-empty"
        if not zero_byte_required
        else f"zero-byte files: {zero_byte_required}",
    }
    if zero_byte_required:
        failures.append(f"Zero-byte required files: {zero_byte_required}")

    parquet_errors = {name: payload["error"] for name, payload in parquet.items() if "error" in payload}
    checks["parquet_metadata_readable"] = {
        "pass": not parquet_errors,
        "detail": "parquet metadata readable" if not parquet_errors else str(parquet_errors),
    }
    if parquet_errors:
        failures.append(f"Parquet metadata read failed: {parquet_errors}")

    feature_rows = parquet.get("features.parquet", {}).get("row_count")
    label_rows = parquet.get("labels.parquet", {}).get("row_count")
    rows_match = feature_rows is not None and label_rows is not None and feature_rows == label_rows
    checks["features_labels_row_count_match"] = {
        "pass": rows_match,
        "detail": f"features rows={feature_rows}, labels rows={label_rows}",
    }
    if not rows_match:
        failures.append(f"features/labels row mismatch: features={feature_rows}, labels={label_rows}")

    slim_exists = files["features_slim.parquet"]["exists"]
    checks["features_slim_exists"] = {
        "pass": slim_exists,
        "detail": "features_slim.parquet found" if slim_exists else "features_slim.parquet missing",
    }
    if not slim_exists:
        failures.append("features_slim.parquet is missing")

    feature_cols = parquet.get("features.parquet", {}).get("column_count")
    slim_cols = parquet.get("features_slim.parquet", {}).get("column_count")
    slim_smaller = feature_cols is not None and slim_cols is not None and slim_cols < feature_cols
    checks["features_slim_has_fewer_columns"] = {
        "pass": slim_smaller,
        "detail": f"features columns={feature_cols}, features_slim columns={slim_cols}",
    }
    if not slim_smaller:
        failures.append(
            f"features_slim column count is not smaller than features: features={feature_cols}, slim={slim_cols}"
        )

    leakage_failures = {
        name: cols for name, cols in problem_columns["leakage_columns"].items() if cols
    }
    checks["no_feature_leakage_keywords"] = {
        "pass": not leakage_failures,
        "detail": "no leakage keyword columns in features/features_slim"
        if not leakage_failures
        else str(leakage_failures),
    }
    if leakage_failures:
        failures.append(f"Leakage keyword columns found: {leakage_failures}")

    duplicate_failures = {
        name: cols for name, cols in problem_columns["duplicate_columns"].items() if cols
    }
    checks["no_duplicate_columns"] = {
        "pass": not duplicate_failures,
        "detail": "no duplicate columns" if not duplicate_failures else str(duplicate_failures),
    }
    if duplicate_failures:
        failures.append(f"Duplicate columns found: {duplicate_failures}")

    all_null_failures = {
        name: cols for name, cols in problem_columns["all_null_columns"].items() if cols
    }
    checks["no_all_null_feature_columns"] = {
        "pass": not all_null_failures,
        "detail": "no all-null feature columns" if not all_null_failures else str(all_null_failures),
    }
    if all_null_failures:
        failures.append(f"All-null feature columns found: {all_null_failures}")

    checks["feature_manifest_exists"] = {
        "pass": files["feature_manifest.json"]["exists"],
        "detail": "feature_manifest.json found"
        if files["feature_manifest.json"]["exists"]
        else "feature_manifest.json missing (optional, recorded for QC)",
    }

    pass_required_checks = [
        "required_files_exist",
        "required_files_non_empty",
        "parquet_metadata_readable",
        "features_labels_row_count_match",
        "features_slim_exists",
        "features_slim_has_fewer_columns",
        "no_feature_leakage_keywords",
        "no_duplicate_columns",
        "no_all_null_feature_columns",
    ]
    result = "PASS" if all(checks[name]["pass"] for name in pass_required_checks) else "FAIL"

    return {
        "result": result,
        "generated_at_utc": utc_now_iso(),
        "s3_fe_output": s3_prefix,
        "null_threshold": args.null_threshold,
        "sample_rows_for_missing_stats": args.sample_rows,
        "required_files": REQUIRED_FILES,
        "optional_files": OPTIONAL_FILES,
        "leakage_keywords": LEAKAGE_KEYWORDS,
        "files": files,
        "parquet": parquet,
        "problem_columns": problem_columns,
        "checks": checks,
        "failures": failures,
    }


def save_reports(summary: dict[str, Any], local_report_dir: str, s3_prefix: str) -> None:
    report_dir = Path(local_report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    json_text = json.dumps(summary, ensure_ascii=False, indent=2, default=str)
    md_text = render_markdown(summary)

    (report_dir / "fe_validation_summary.json").write_text(json_text + "\n", encoding="utf-8")
    (report_dir / "fe_validation_summary.md").write_text(md_text, encoding="utf-8")

    fs = s3fs.S3FileSystem(anon=False)
    write_text_s3(fs, s3_prefix + "fe_validation_summary.json", json_text + "\n")
    write_text_s3(fs, s3_prefix + "fe_validation_summary.md", md_text)


def print_console_result(summary: dict[str, Any]) -> None:
    print(f"FE VALIDATION RESULT: {summary['result']}")
    if summary["result"] == "PASS":
        return

    print("\nFailed conditions:")
    for failure in summary["failures"]:
        print(f"- {failure}")

    missing = [
        name for name in REQUIRED_FILES if not summary["files"].get(name, {}).get("exists")
    ]
    if missing:
        print("\nMissing files:")
        for name in missing:
            print(f"- {name}")

    problem_columns = summary["problem_columns"]
    has_problem_columns = any(problem_columns[key] for key in problem_columns)
    if has_problem_columns:
        print("\nProblem columns:")
        for category, payload in problem_columns.items():
            if payload:
                print(f"- {category}: {json.dumps(payload, ensure_ascii=False)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate FE output artifacts in S3 without downloading full datasets."
    )
    parser.add_argument("--s3-fe-output", required=True, help="S3 prefix ending in fe_output/")
    parser.add_argument(
        "--local-report-dir",
        default="reports/",
        help="Local directory for fe_validation_summary.json/md",
    )
    parser.add_argument(
        "--null-threshold",
        type=float,
        default=0.95,
        help="Columns with null ratio >= this value are listed as high-null.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=5000,
        help="Maximum rows sampled only for columns whose Parquet footer lacks statistics.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    s3_prefix = normalize_s3_prefix(args.s3_fe_output)
    summary = build_summary(args)
    save_reports(summary, args.local_report_dir, s3_prefix)
    print_console_result(summary)
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
