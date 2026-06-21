#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"PyYAML is required: {exc}")


REQUIRED_HINTS = {
    "final_candidate_result": [["drug_id", "drug_name", "drug", "compound_name", "canonical_drug_id"], ["final_rank", "rank", "score"]],
    "drug_candidate_result": [["drug_id", "drug_name", "drug", "compound_name", "canonical_drug_id"], ["rank", "score"]],
    "drug_candidate_tier": [["drug_id", "drug_name", "drug", "compound_name", "canonical_drug_id"], ["tier", "candidate_tier", "drug_tier"]],
    "admet_result": [["drug_id", "drug_name", "drug", "compound_name", "canonical_drug_id"], ["admet", "tox", "safety", "assay", "hard_fail"]],
    "external_validation_result": [["validation", "dataset", "source", "metabric", "geo", "cptac", "cosmic", "prism"], ["drug_id", "drug_name", "drug", "compound_name", "canonical_drug_id", "rank", "score"]],
    "model_metric": [["model"], ["metric", "metric_value", "score"]],
    "model_metric_detailed": [["model"], ["split", "fold", "metric", "metric_value"]],
    "ensemble_metric": [["ensemble", "metric", "metric_value", "score"]],
    "source_artifact": [["source", "artifact", "manifest", "uri", "path"]],
    "load_audit": [["status", "table_name", "row_count", "message"]],
    "run_manifest": [["run_id", "manifest", "source_s3_uri"]],
}
CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
LIHC_IMAGE_MODAL_PATH_TOKENS = ("/0.image_modal_lihc/", "/image_modal/", "image_modal")
LIHC_STALE_OR_MISMATCH_PATH_TOKENS = (
    "/stad_results_",
    "/stad_scripts_snapshot/",
    "/generated/results/stad_",
    "/protocol_used_files/",
    "/reports/",
)
TABULAR_EXTENSIONS = {".csv", ".tsv", ".csv.gz", ".tsv.gz"}
EXTERNAL_VALIDATION_SOURCE_REQUIREMENT = "validation OR dataset OR source OR metabric OR geo OR cptac OR cosmic OR prism"
EXTERNAL_VALIDATION_REQUIRED_EVIDENCE_COLUMNS = {
    "prism_has_evidence",
    "geo_has_evidence",
    "cosmic_has_evidence",
    "cptac_has_evidence",
    "clinical_trials_has_evidence",
    "opentargets_has_evidence",
}
EXTERNAL_VALIDATION_SOURCE_PREFIXES = (
    "geo_",
    "cptac_",
    "cosmic_",
    "prism_",
    "clinical_trials_",
    "opentargets_",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build disease PostgreSQL load plan from real inspection output.")
    p.add_argument("--project-root", default="")
    p.add_argument("--disease", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--inspection-json", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--output-md", default="")
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
    if not safe_str(arg_root):
        raise SystemExit("MISSING_PROJECT_ROOT_ARG")
    p = Path(arg_root)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def resolve_path(project_root: Path, path_arg: str) -> Path:
    p = Path(path_arg)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def normalize_path_for_compare(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve())))


def normalize_path_no_resolve(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path))))


def output_root_guardrail_status(project_root: Path) -> str:
    resolved = normalize_path_no_resolve(project_root)
    if (
        "onedrive" in resolved.lower()
        or r"\users\hjy10\onedrive" in resolved.lower()
        or r"\문서\new project 2" in resolved.lower()
    ):
        return "BLOCKED_ONEDRIVE_PROJECT_ROOT"
    return "PASS"


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


def normalized_col_name(name: str) -> str:
    text = safe_str(name).lower()
    out_chars: list[str] = []
    for ch in text:
        if ch.isalnum():
            out_chars.append(ch)
        else:
            out_chars.append("_")
    normalized = "".join(out_chars).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def required_found_and_missing(target_table: str, cols: list[str]) -> tuple[list[str], list[str]]:
    hints = REQUIRED_HINTS.get(target_table, [])
    lowered = {safe_str(c).lower() for c in cols}
    found: list[str] = []
    missing: list[str] = []
    for group in hints:
        hits = [g for g in group if g.lower() in lowered]
        if hits:
            found.extend(hits)
        else:
            missing.append(" OR ".join(group))
    uniq: list[str] = []
    for f in found:
        if f not in uniq:
            uniq.append(f)
    return uniq, missing


def detect_external_validation_source_columns(cols: list[str]) -> list[str]:
    detected: list[str] = []
    for col in cols:
        norm = normalized_col_name(col)
        if norm in EXTERNAL_VALIDATION_REQUIRED_EVIDENCE_COLUMNS:
            detected.append(norm)
            continue
        if norm.endswith("_has_evidence") or norm.endswith("_status"):
            detected.append(norm)
            continue
        if any(norm.startswith(prefix) for prefix in EXTERNAL_VALIDATION_SOURCE_PREFIXES):
            detected.append(norm)
            continue
    uniq: list[str] = []
    for col in detected:
        if col not in uniq:
            uniq.append(col)
    return uniq


def apply_external_validation_top30_mapping_override(
    target_table: str,
    role: str,
    s3_uri: str,
    cols: list[str],
    found: list[str],
    missing: list[str],
) -> tuple[list[str], list[str], list[str], str]:
    if not (target_table == "external_validation_result" and role == "external_validation_top30"):
        return found, missing, [], "NOT_APPLICABLE"
    if path_has_any_token(s3_uri, LIHC_IMAGE_MODAL_PATH_TOKENS):
        return found, missing, [], "BLOCKED_IMAGE_PATH"

    detected_source_columns = detect_external_validation_source_columns(cols)
    if not detected_source_columns:
        return found, missing, [], "BLOCKED_NO_SOURCE_COLUMNS"

    has_required_evidence = any(col in EXTERNAL_VALIDATION_REQUIRED_EVIDENCE_COLUMNS for col in detected_source_columns)
    if not has_required_evidence:
        return found, missing, detected_source_columns, "BLOCKED_NO_REQUIRED_EVIDENCE_COLUMNS"

    patched_missing: list[str] = []
    for group in missing:
        if safe_str(group) == EXTERNAL_VALIDATION_SOURCE_REQUIREMENT:
            continue
        patched_missing.append(group)

    patched_found = list(found)
    for col in detected_source_columns:
        if col not in patched_found:
            patched_found.append(col)
    return patched_found, patched_missing, detected_source_columns, "ACCEPTED_EVIDENCE_SOURCE_COLUMNS"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be mapping")
    return data


def path_has_any_token(path_text: str, tokens: tuple[str, ...]) -> bool:
    low = safe_str(path_text).lower().replace("\\", "/")
    return any(tok in low for tok in tokens)


def should_include_lihc_needs_review_with_role_patch(row: dict[str, Any]) -> tuple[bool, str, str, str]:
    s3_uri = safe_str(row.get("s3_uri"))
    filename = safe_str(row.get("filename")).lower()
    extension = safe_str(row.get("extension")).lower()
    proposed_table = safe_str(row.get("proposed_target_table"))
    proposed_role = safe_str(row.get("proposed_role"))
    reason = safe_str(row.get("reason"))
    uri_low = s3_uri.lower().replace("\\", "/")

    if path_has_any_token(s3_uri, LIHC_IMAGE_MODAL_PATH_TOKENS):
        return False, "", "", "lihc_image_modal_excluded"
    if path_has_any_token(s3_uri, LIHC_STALE_OR_MISMATCH_PATH_TOKENS):
        return False, "", "", "lihc_stale_or_mismatched_path_excluded"
    if extension not in TABULAR_EXTENSIONS:
        return False, "", "", "lihc_non_tabular_excluded"
    if "lihc" not in uri_low:
        return False, "", "", "lihc_path_token_missing"

    if (
        proposed_table == "external_validation_result"
        and proposed_role == "external_validation_top30"
        and reason == "external_validation_like_columns_detected"
        and "external_validation" in uri_low
    ):
        return True, "external_validation_result", "external_validation_top30", "lihc_role_patch_external_validation"

    if (
        proposed_table == "external_validation_result"
        and proposed_role == "external_validation_top30"
        and reason == "external_validation_like_columns_detected"
        and "tiered" in filename
        and "generated/results/" in uri_low
    ):
        return True, "drug_candidate_tier", "candidate_tiered", "lihc_role_patch_candidate_tiered_from_filename"

    if (
        proposed_table == "drug_candidate_tier"
        and proposed_role == "candidate_tiered"
        and "tiered" in filename
    ):
        return True, "drug_candidate_tier", "candidate_tiered", "lihc_role_patch_candidate_tiered"

    return False, "", "", "lihc_role_patch_not_applicable"


def main() -> None:
    args = parse_args()
    disease = safe_str(args.disease).upper()
    project_root = resolve_project_root(args.project_root)
    root_guardrail_status = output_root_guardrail_status(project_root)
    if root_guardrail_status != "PASS":
        raise SystemExit(root_guardrail_status)
    config_path = resolve_path(project_root, args.config)
    inspect_json_path = resolve_path(project_root, args.inspection_json)
    out_json = (
        resolve_path(project_root, args.output_json)
        if safe_str(args.output_json)
        else project_root / "outputs" / "config_validation" / f"{disease.lower()}_postgres_load_plan_from_real_inspection.json"
    )
    out_md = (
        resolve_path(project_root, args.output_md)
        if safe_str(args.output_md)
        else project_root / "docs" / f"{disease.lower()}_postgres_load_plan_from_real_inspection.md"
    )
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    config = load_yaml(config_path)
    cfg_disease = safe_str(config.get("disease", {}).get("code", "")).upper()
    if cfg_disease and cfg_disease != disease:
        raise SystemExit(f"disease mismatch: arg={disease}, config={cfg_disease}")

    allowed_tables = set([safe_str(x) for x in config.get("postgres", {}).get("target_tables", []) if safe_str(x)])
    if not allowed_tables:
        allowed_tables = set(REQUIRED_HINTS.keys())

    payload = json.loads(inspect_json_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    plan_rows: list[dict[str, Any]] = []
    role_patch_newly_supported_count = 0
    for r in rows:
        decision = safe_str(r.get("decision"))
        table = safe_str(r.get("proposed_target_table"))
        role = safe_str(r.get("proposed_role"))
        include_from_role_patch = False
        role_patch_reason = ""

        if decision == "APPROVED_FOR_POSTGRES_LOAD":
            if disease == "LIHC":
                s3_uri = safe_str(r.get("s3_uri"))
                if path_has_any_token(s3_uri, LIHC_IMAGE_MODAL_PATH_TOKENS):
                    continue
                if path_has_any_token(s3_uri, LIHC_STALE_OR_MISMATCH_PATH_TOKENS):
                    continue
        elif disease == "LIHC" and decision == "NEEDS_REVIEW":
            include_from_role_patch, patched_table, patched_role, role_patch_reason = should_include_lihc_needs_review_with_role_patch(r)
            if not include_from_role_patch:
                continue
            table = patched_table
            role = patched_role
            role_patch_newly_supported_count += 1
        else:
            continue

        if table not in allowed_tables:
            continue
        cols = r.get("columns_or_keys", [])
        if not isinstance(cols, list):
            cols = []
        normalized_cols = [safe_str(c) for c in cols]
        found, missing = required_found_and_missing(table, normalized_cols)
        found, missing, ev_source_cols, ev_mapping_status = apply_external_validation_top30_mapping_override(
            target_table=table,
            role=role,
            s3_uri=safe_str(r.get("s3_uri")),
            cols=normalized_cols,
            found=found,
            missing=missing,
        )
        plan_rows.append(
            {
                "disease": disease,
                "source_s3_uri": safe_str(r.get("s3_uri")),
                "target_table": table,
                "proposed_role": role,
                "parser_strategy": parser_strategy(safe_str(r.get("extension"))),
                "required_columns_found": found,
                "missing_columns": missing,
                "missing_required_columns": missing,
                "external_validation_source_columns_detected": ev_source_cols,
                "external_validation_mapping_status": ev_mapping_status,
                "confidence": safe_str(r.get("confidence")),
                "reason": safe_str(r.get("reason")),
                "filename": safe_str(r.get("filename")),
                "size_bytes": int(r.get("size_bytes", 0) or 0),
                "no_admet_flag": bool(r.get("no_admet_flag")),
                "included_from_role_patch": include_from_role_patch,
                "role_patch_reason": role_patch_reason,
            }
        )

    plan_status = "PASS" if len(plan_rows) > 0 else "PASS_WITH_WARNINGS"
    out_payload = {
        "generated_at": now_iso(),
        "status": plan_status,
        "disease": disease,
        "project_root": str(project_root),
        "detected_project_root": str(project_root),
        "project_root_env": safe_str(os.getenv("PROJECT_ROOT", "")),
        "requested_project_root_arg": safe_str(args.project_root),
        "output_root_guardrail_status": root_guardrail_status,
        "config_path": str(config_path),
        "inspection_json": str(inspect_json_path),
        "approved_artifact_count": len(plan_rows),
        "role_patch_newly_supported_count": role_patch_newly_supported_count,
        "plan_rows": plan_rows,
        "notes": [
            "Only APPROVED_FOR_POSTGRES_LOAD artifacts are included.",
            "LIHC only: selected NEEDS_REVIEW rows may be promoted when BRCA-standard role mapping is safe and non-image.",
            "NEEDS_REVIEW/DO_NOT_LOAD_EXCLUDED/NOT_COMPACT_RESULT/BLOCKED are excluded.",
            "PostgreSQL execute: not run",
            "Neo4j execute: not run",
        ],
    }
    out_json.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {disease} PostgreSQL Load Plan From Real Inspection",
        "",
        f"- generated_at: `{out_payload['generated_at']}`",
        f"- disease: `{disease}`",
        f"- approved_artifact_count: `{len(plan_rows)}`",
        f"- status: `{plan_status}`",
        "- PostgreSQL execute: `not run`",
        "- Neo4j execute: `not run`",
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
    print(f"status={plan_status}")
    print(f"json_output={out_json}")
    print(f"markdown_output={out_md}")


if __name__ == "__main__":
    main()


