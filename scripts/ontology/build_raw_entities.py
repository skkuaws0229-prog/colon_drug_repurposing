#!/usr/bin/env python
import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import boto3
import pandas as pd
import pyarrow.parquet as pq
from pyarrow import fs


ENTITY_TYPES = ("drug", "disease", "gene", "target", "cell_line", "sample")

ENTITY_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "cell_line": [
        re.compile(r"cell[_-]?line", re.IGNORECASE),
        re.compile(r"cellline", re.IGNORECASE),
        re.compile(r"depmap", re.IGNORECASE),
        re.compile(r"ccle", re.IGNORECASE),
    ],
    "target": [
        re.compile(r"\btarget\b", re.IGNORECASE),
        re.compile(r"protein[_-]?target", re.IGNORECASE),
        re.compile(r"target[_-]?gene", re.IGNORECASE),
    ],
    "gene": [
        re.compile(r"\bgene(s)?\b", re.IGNORECASE),
        re.compile(r"symbol", re.IGNORECASE),
        re.compile(r"hgnc", re.IGNORECASE),
        re.compile(r"ensembl", re.IGNORECASE),
        re.compile(r"entrez", re.IGNORECASE),
    ],
    "drug": [
        re.compile(r"\bdrug(s)?\b", re.IGNORECASE),
        re.compile(r"compound", re.IGNORECASE),
        re.compile(r"pert", re.IGNORECASE),
        re.compile(r"chembl", re.IGNORECASE),
        re.compile(r"drugbank", re.IGNORECASE),
        re.compile(r"smiles", re.IGNORECASE),
        re.compile(r"inchi", re.IGNORECASE),
    ],
    "disease": [
        re.compile(r"disease", re.IGNORECASE),
        re.compile(r"indication", re.IGNORECASE),
        re.compile(r"cancer", re.IGNORECASE),
        re.compile(r"tumou?r", re.IGNORECASE),
        re.compile(r"histology", re.IGNORECASE),
        re.compile(r"subtype", re.IGNORECASE),
    ],
    "sample": [
        re.compile(r"sample", re.IGNORECASE),
        re.compile(r"patient", re.IGNORECASE),
        re.compile(r"specimen", re.IGNORECASE),
        re.compile(r"barcode", re.IGNORECASE),
        re.compile(r"aliquot", re.IGNORECASE),
    ],
}


@dataclass(frozen=True)
class DetectedColumn:
    entity_type: str
    source_column: str


def parse_s3_uri(s3_uri: str) -> Tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got: {s3_uri}")
    body = s3_uri[5:]
    bucket, _, key = body.partition("/")
    if not bucket:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return bucket, key


def list_parquet_uris(prefix_uri: str, max_files: Optional[int]) -> List[str]:
    bucket, prefix = parse_s3_uri(prefix_uri)
    client = boto3.client("s3")
    paginator = client.get_paginator("list_objects_v2")

    uris: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.lower().endswith(".parquet"):
                uris.append(f"s3://{bucket}/{key}")
                if max_files and len(uris) >= max_files:
                    return uris
    return uris


def detect_entity_columns(columns: Sequence[str]) -> List[DetectedColumn]:
    detected: List[DetectedColumn] = []
    for col in columns:
        selected_type: Optional[str] = None
        for entity_type in ENTITY_TYPES:
            patterns = ENTITY_PATTERNS[entity_type]
            if any(p.search(col) for p in patterns):
                selected_type = entity_type
                break
        if selected_type:
            detected.append(DetectedColumn(entity_type=selected_type, source_column=col))
    return detected


def normalize_value(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple)):
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:  # noqa: BLE001
            text = str(value)
    else:
        text = str(value).strip()
    text = text.strip()
    if not text:
        return None
    if text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return None
    return text


def extract_unique_rows_for_column(
    s3_uri: str,
    source_column: str,
    entity_type: str,
) -> Iterable[Tuple[str, str, str, str]]:
    df = pd.read_parquet(s3_uri, columns=[source_column], engine="pyarrow")
    series = df[source_column]
    seen_values: set[str] = set()
    for raw in series:
        normalized = normalize_value(raw)
        if normalized is None:
            continue
        if normalized in seen_values:
            continue
        seen_values.add(normalized)
        yield (normalized, entity_type, source_column, s3_uri)


def read_parquet_columns_with_pyarrow(s3_uri: str, pa_fs: fs.S3FileSystem) -> List[str]:
    bucket, key = parse_s3_uri(s3_uri)
    schema = pq.read_schema(f"{bucket}/{key}", filesystem=pa_fs)
    return list(schema.names)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build raw entity catalog from S3 parquet files")
    parser.add_argument(
        "--input-s3-prefix",
        default="s3://say2-4team/",
        help="S3 prefix to scan for parquet files",
    )
    parser.add_argument(
        "--output-s3-uri",
        default="s3://say2-4team/entities/raw_entities.parquet",
        help="Output parquet URI",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on number of parquet files to scan",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        parquet_uris = list_parquet_uris(args.input_s3_prefix, args.max_files)
        if not parquet_uris:
            raise ValueError(f"No parquet files found under {args.input_s3_prefix}")

        pa_fs = fs.S3FileSystem()
        dedup_rows: set[Tuple[str, str, str, str]] = set()
        scanned_files = 0
        detected_columns_count = 0

        for s3_uri in parquet_uris:
            scanned_files += 1
            columns = read_parquet_columns_with_pyarrow(s3_uri, pa_fs)
            detected_columns = detect_entity_columns(columns)
            if not detected_columns:
                continue

            for detected in detected_columns:
                detected_columns_count += 1
                for row in extract_unique_rows_for_column(
                    s3_uri=s3_uri,
                    source_column=detected.source_column,
                    entity_type=detected.entity_type,
                ):
                    dedup_rows.add(row)

        if not dedup_rows:
            raise ValueError("No entity values detected from scanned parquet files.")

        out_df = pd.DataFrame(
            sorted(dedup_rows),
            columns=["raw_value", "entity_type", "source_column", "source_s3_uri"],
        )

        # Compatibility columns so output can be used directly by map_raw_entities.py.
        type_alias = {"target": "gene", "sample": "cell_line"}
        out_df["raw_entity_name"] = out_df["raw_value"]
        out_df["raw_entity_type"] = out_df["entity_type"].map(lambda x: type_alias.get(x, x))
        out_df["source_dataset"] = out_df["source_s3_uri"]

        out_df.to_parquet(args.output_s3_uri, index=False, engine="pyarrow")

        print(f"[ok] Wrote raw entities: {args.output_s3_uri}")
        print(f"[info] scanned_parquet_files={scanned_files}")
        print(f"[info] detected_columns={detected_columns_count}")
        print(f"[info] unique_rows={len(out_df)}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
