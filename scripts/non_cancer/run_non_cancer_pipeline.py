#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import step1_inspect_s3_content as step1


def safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", safe_str(text).strip()).strip("_").lower()
    return slug or "unknown_disease"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Non-cancer pipeline runner (step-based).")
    p.add_argument("--step", default="step1", choices=["step1"])
    p.add_argument("--disease-code", required=True)
    p.add_argument("--disease-type", default="non_cancer")
    p.add_argument("--s3-prefix", required=True)
    p.add_argument("--out-dir", default="outputs/config_validation")
    p.add_argument("--docs-dir", default="docs")
    return p.parse_args()


def run_step1(
    disease_code: str,
    disease_type: str,
    s3_prefix: str,
    out_dir: Path,
    docs_dir: Path,
) -> tuple[Path, Path, Path]:
    slug = slugify(disease_code)
    out_json = out_dir / f"{slug}_s3_content_inspection_report.json"
    out_md = docs_dir / f"{slug}_s3_content_inspection_report.md"
    out_csv = out_dir / f"{slug}_file_role_recommendation.csv"

    report = step1.run_inspection(
        s3_prefix=s3_prefix,
        disease_code=disease_code.upper(),
        disease_type=disease_type,
    )
    step1.write_json(out_json, report)
    step1.write_markdown(out_md, report)
    step1.write_csv(out_csv, report.get("objects", []))
    return out_json, out_md, out_csv


def main() -> None:
    args = parse_args()
    disease_code = safe_str(args.disease_code).upper()
    disease_type = safe_str(args.disease_type) or "non_cancer"
    out_dir = Path(args.out_dir)
    docs_dir = Path(args.docs_dir)

    if args.step == "step1":
        out_json, out_md, out_csv = run_step1(
            disease_code=disease_code,
            disease_type=disease_type,
            s3_prefix=args.s3_prefix,
            out_dir=out_dir,
            docs_dir=docs_dir,
        )
        print(f"step=step1")
        print(f"disease_code={disease_code}")
        print(f"out_json={out_json}")
        print(f"out_md={out_md}")
        print(f"out_csv={out_csv}")


if __name__ == "__main__":
    main()
