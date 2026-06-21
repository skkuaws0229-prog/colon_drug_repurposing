#!/usr/bin/env python
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import fsspec
import pandas as pd


def read_table(uri: str, columns: list[str] | None = None) -> pd.DataFrame:
    if uri.lower().endswith(".parquet"):
        return pd.read_parquet(uri, columns=columns)
    if uri.lower().endswith(".csv"):
        if columns:
            return pd.read_csv(uri, usecols=columns)
        return pd.read_csv(uri)
    raise ValueError(f"Unsupported mappings format: {uri}. Use .parquet or .csv")


def ensure_prefix(uri_prefix: str) -> str:
    return uri_prefix if uri_prefix.endswith("/") else f"{uri_prefix}/"


def write_text(uri: str, content: str) -> None:
    if uri.startswith("s3://"):
        with fsspec.open(uri, mode="w") as fh:
            fh.write(content)
        return

    path = Path(uri)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def to_json_serializable(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def summarize_group(df: pd.DataFrame, group_col: str) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for key, part in df.groupby(group_col, dropna=False):
        total = len(part)
        matched = int((part["match_type"] != "no_match").sum())
        rate = float(matched / total) if total else 0.0
        level = "ok"
        if rate < 0.6:
            level = "strong_warning"
        elif rate < 0.8:
            level = "warning"

        grouped[str(key)] = {
            "total": total,
            "mapped": matched,
            "mapping_rate": round(rate, 4),
            "status": level,
        }
    return grouped


def build_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Ontology Mapping QC Report",
        "",
        f"- Generated at (UTC): {report['generated_at_utc']}",
        f"- Total rows: {report['summary']['total_rows']}",
        f"- Mapped rows: {report['summary']['mapped_rows']}",
        f"- Overall mapping rate: {report['summary']['overall_mapping_rate']:.4f}",
        "",
        "## Alerts",
    ]

    if report["alerts"]:
        for alert in report["alerts"]:
            lines.append(f"- {alert}")
    else:
        lines.append("- No warnings triggered.")

    lines.append("")
    lines.append("## Mapping Rate by Entity Type")
    lines.append("")
    lines.append("| Entity Type | Total | Mapped | Mapping Rate | Status |")
    lines.append("|---|---:|---:|---:|---|")
    for entity_type, stats in report["by_entity_type"].items():
        lines.append(
            f"| {entity_type} | {stats['total']} | {stats['mapped']} | {stats['mapping_rate']:.4f} | {stats['status']} |"
        )

    lines.append("")
    lines.append("## Mapping Rate by Source Dataset")
    lines.append("")
    lines.append("| Source Dataset | Total | Mapped | Mapping Rate | Status |")
    lines.append("|---|---:|---:|---:|---|")
    for dataset, stats in report["by_source_dataset"].items():
        lines.append(
            f"| {dataset} | {stats['total']} | {stats['mapped']} | {stats['mapping_rate']:.4f} | {stats['status']} |"
        )

    lines.append("")
    lines.append("## Confidence Distribution")
    lines.append("")
    for k, v in report["mapping_confidence_distribution"].items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("## Match Type Distribution")
    lines.append("")
    for k, v in report["match_type_distribution"].items():
        lines.append(f"- {k}: {v}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ontology entity mapping quality")
    parser.add_argument("--mappings-s3-uri", required=True, help="Input mappings parquet/csv (local or s3://)")
    parser.add_argument("--output-s3-prefix", required=True, help="Output folder/prefix for qc reports")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        required_cols = [
            "source_dataset",
            "raw_entity_type",
            "mapping_confidence",
            "match_type",
        ]
        df = read_table(args.mappings_s3_uri, columns=required_cols)
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Mappings file is missing columns: {sorted(missing)}")

        total_rows = len(df)
        if total_rows == 0:
            raise ValueError("Mappings file is empty. Cannot generate QC report.")

        matched = int((df["match_type"] != "no_match").sum())
        overall_mapping_rate = matched / total_rows

        by_entity_type = summarize_group(df, "raw_entity_type")
        by_source_dataset = summarize_group(df, "source_dataset")

        confidence_dist = df["mapping_confidence"].fillna("null").value_counts(dropna=False).to_dict()
        match_dist = df["match_type"].fillna("null").value_counts(dropna=False).to_dict()

        alerts = []
        if overall_mapping_rate < 0.6:
            alerts.append(
                f"STRONG WARNING: overall mapping_rate={overall_mapping_rate:.4f} is below 0.60"
            )
        elif overall_mapping_rate < 0.8:
            alerts.append(f"WARNING: overall mapping_rate={overall_mapping_rate:.4f} is below 0.80")

        for entity_type, stats in by_entity_type.items():
            if stats["mapping_rate"] < 0.6:
                alerts.append(
                    f"STRONG WARNING: entity_type={entity_type} mapping_rate={stats['mapping_rate']:.4f}"
                )
            elif stats["mapping_rate"] < 0.8:
                alerts.append(f"WARNING: entity_type={entity_type} mapping_rate={stats['mapping_rate']:.4f}")

        for dataset, stats in by_source_dataset.items():
            if stats["mapping_rate"] < 0.6:
                alerts.append(
                    f"STRONG WARNING: source_dataset={dataset} mapping_rate={stats['mapping_rate']:.4f}"
                )
            elif stats["mapping_rate"] < 0.8:
                alerts.append(f"WARNING: source_dataset={dataset} mapping_rate={stats['mapping_rate']:.4f}")

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_rows": total_rows,
                "mapped_rows": matched,
                "overall_mapping_rate": round(overall_mapping_rate, 4),
            },
            "by_entity_type": by_entity_type,
            "by_source_dataset": by_source_dataset,
            "mapping_confidence_distribution": confidence_dist,
            "match_type_distribution": match_dist,
            "alerts": alerts,
        }

        md = build_markdown(report)
        prefix = ensure_prefix(args.output_s3_prefix)
        json_uri = f"{prefix}ontology_mapping_qc.json"
        md_uri = f"{prefix}ontology_mapping_qc.md"

        write_text(json_uri, to_json_serializable(report))
        write_text(md_uri, md)

        print(f"[ok] Wrote QC JSON: {json_uri}")
        print(f"[ok] Wrote QC Markdown: {md_uri}")
        print(f"[info] Overall mapping rate: {overall_mapping_rate:.4f}")
        if alerts:
            print(f"[warn] Alerts: {len(alerts)}")
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
