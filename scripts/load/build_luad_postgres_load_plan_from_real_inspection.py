#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_HINTS = {
    "final_candidate_result": [["drug_id", "drug_name", "drug", "compound_name"], ["rank", "final_rank", "score"]],
    "drug_candidate_result": [["drug_id", "drug_name", "drug", "compound_name"], ["rank", "score"]],
    "drug_candidate_tier": [["drug_id", "drug_name", "drug", "compound_name"], ["tier", "candidate_tier", "drug_tier"]],
    "admet_result": [["drug_id", "drug_name", "drug", "compound_name"], ["admet", "tox", "safety", "assay", "hard_fail"]],
    "external_validation_result": [["validation", "dataset", "source", "metabric", "geo", "cptac", "cosmic", "prism"], ["drug_id", "drug_name", "drug", "compound_name", "rank", "score"]],
    "model_metric": [["model"], ["metric", "metric_value", "score"]],
    "model_metric_detailed": [["model"], ["split", "fold", "metric", "metric_value"]],
    "ensemble_metric": [["ensemble", "metric", "metric_value", "score"]],
    "source_artifact": [["source", "artifact", "manifest", "uri", "path"]],
    "load_audit": [["status", "table_name", "row_count", "message"]],
    "run_manifest": [["run_id", "manifest", "source_s3_uri"]],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build LUAD PostgreSQL load plan from real S3 file inspection output.")
    p.add_argument("--project-root", default="")
    p.add_argument("--inspection-json", required=True)
    return p.parse_args()


def has_project_markers(path: Path) -> bool:
    return (path / "scripts").is_dir() and (path / "docs").is_dir() and (path / "outputs").is_dir()


def find_project_root() -> Path:
    cwd = Path.cwd()
    if has_project_markers(cwd):
        return cwd
    script_root = Path(__file__).resolve().parents[2]
    if has_project_markers(script_root):
        return script_root
    return script_root


def resolve_project_root(arg_root: str) -> Path:
    if safe_str(arg_root):
        p = Path(arg_root)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve()
    return find_project_root().resolve()


def resolve_path(project_root: Path, path_arg: str) -> Path:
    p = Path(path_arg)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def parser_strategy(extension: str) -> str:
    ext = extension.lower()
    if ext in {".csv", ".tsv", ".csv.gz", ".tsv.gz"}:
        return "tabular"
    if ext == ".json":
        return "json"
    if ext == ".jsonl":
        return "jsonl"
    if ext == ".parquet":
        return "parquet"
    if ext in {".md", ".txt"}:
        return "text"
    return "unknown"


def required_found_and_missing(target_table: str, cols: list[str]) -> tuple[list[str], list[str]]:
    hints = REQUIRED_HINTS.get(target_table, [])
    lowered = {safe_str(c).lower() for c in cols}
    found: list[str] = []
    missing: list[str] = []
    for group in hints:
        hit = [g for g in group if g.lower() in lowered]
        if hit:
            found.extend(hit)
        else:
            missing.append(" OR ".join(group))
    # unique stable
    found_unique: list[str] = []
    for f in found:
        if f not in found_unique:
            found_unique.append(f)
    return found_unique, missing


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.project_root)
    inspect_json_path = resolve_path(project_root, args.inspection_json)

    payload = json.loads(inspect_json_path.read_text(encoding="utf-8"))
    disease = safe_str(payload.get("disease", "LUAD")).upper()
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    approved_rows = [r for r in rows if safe_str(r.get("decision")) == "APPROVED_FOR_POSTGRES_LOAD"]

    plan_rows: list[dict[str, Any]] = []
    for r in approved_rows:
        table = safe_str(r.get("proposed_target_table"))
        role = safe_str(r.get("proposed_role"))
        cols = r.get("columns_or_keys", [])
        if not isinstance(cols, list):
            cols = []
        found, missing = required_found_and_missing(table, [safe_str(c) for c in cols])
        plan_rows.append(
            {
                "disease": disease,
                "source_s3_uri": safe_str(r.get("s3_uri")),
                "target_table": table,
                "proposed_role": role,
                "parser_strategy": parser_strategy(safe_str(r.get("extension"))),
                "required_columns_found": found,
                "missing_columns": missing,
                "confidence": safe_str(r.get("confidence")),
                "reason": safe_str(r.get("reason")),
                "filename": safe_str(r.get("filename")),
                "size_bytes": r.get("size_bytes", 0),
            }
        )

    status = "PASS" if len(plan_rows) > 0 else "PASS_WITH_WARNINGS"
    out_json = project_root / "outputs" / "config_validation" / "luad_postgres_load_plan_from_real_inspection.json"
    out_md = project_root / "docs" / "luad_postgres_load_plan_from_real_inspection.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_payload = {
        "generated_at": now_iso(),
        "status": status,
        "disease": disease,
        "project_root": str(project_root),
        "inspection_json": str(inspect_json_path),
        "approved_artifact_count": len(plan_rows),
        "plan_rows": plan_rows,
        "notes": [
            "Only APPROVED_FOR_POSTGRES_LOAD artifacts are included.",
            "NEEDS_REVIEW/DO_NOT_LOAD_EXCLUDED/NOT_COMPACT_RESULT/BLOCKED are excluded.",
        ],
    }
    out_json.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# LUAD PostgreSQL Load Plan From Real Inspection",
        "",
        f"- generated_at: `{out_payload['generated_at']}`",
        f"- disease: `{disease}`",
        f"- approved_artifact_count: `{len(plan_rows)}`",
        f"- status: `{status}`",
        "",
        "| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in plan_rows:
        lines.append(
            f"| {safe_str(r.get('source_s3_uri'))} | {safe_str(r.get('target_table'))} | {safe_str(r.get('proposed_role'))} | {safe_str(r.get('parser_strategy'))} | {', '.join(r.get('required_columns_found', []))} | {', '.join(r.get('missing_columns', []))} | {safe_str(r.get('confidence'))} | {safe_str(r.get('reason'))} |"
        )
    if not plan_rows:
        lines.append("| (none) |  |  |  |  |  |  |  |")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"disease={disease}")
    print(f"approved_artifact_count={len(plan_rows)}")
    print(f"status={status}")
    print(f"json_output={out_json}")
    print(f"markdown_output={out_md}")


if __name__ == "__main__":
    main()

