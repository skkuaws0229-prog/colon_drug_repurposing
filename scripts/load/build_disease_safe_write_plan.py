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


DECISIONS = [
    "LOAD_CANDIDATE",
    "NEEDS_REVIEW",
    "DO_NOT_LOAD_EXCLUDED",
    "BLOCKED",
    "MISSING",
    "LOCAL_SYNC_NEEDED",
    "NOT_COMPACT_RESULT",
    "UNCLASSIFIED_REVIEW",
]
IMAGE_MODAL_TOKENS = [
    "image",
    "images",
    "img",
    "imaging",
    "image_modal",
    "imagemodal",
    "multimodal_image",
    "pathology",
    "histology",
    "wsi",
    "whole_slide",
    "slide_images",
    "svs",
    "tissue_image",
]
CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
PROJECT_ROOT_MARKERS = ["configs", "scripts", "backend", "outputs", "docs", "pyproject.toml", "requirements.txt"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build disease safe write-plan preview only (read-only).")
    p.add_argument("--disease", required=True)
    p.add_argument("--project-root", default="")
    p.add_argument("--config", required=True)
    return p.parse_args()


def resolve_project_root(project_root_arg: str) -> Path:
    if not safe_str(project_root_arg):
        raise SystemExit("MISSING_PROJECT_ROOT_ARG")
    p = Path(project_root_arg)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def normalize_path_for_compare(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve())))


def normalize_path_no_resolve(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path))))


def marker_score(path: Path) -> int:
    score = 0
    for marker in PROJECT_ROOT_MARKERS:
        if (path / marker).exists():
            score += 1
    return score


def iter_ancestors_inclusive(path: Path) -> list[Path]:
    p = path.resolve()
    if p.is_file():
        p = p.parent
    out = [p]
    out.extend(p.parents)
    return out


def detect_project_root(project_root_arg: str) -> tuple[Path, str]:
    arg_root = safe_str(project_root_arg)
    if arg_root:
        p = Path(arg_root)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve(), "project_root_arg"

    env_root = safe_str(os.getenv("PROJECT_ROOT", ""))
    if env_root:
        p = Path(env_root)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve(), "project_root_env"

    starts = [Path.cwd(), Path(__file__).resolve().parents[2]]
    best_path = None
    best_score = -1
    for start in starts:
        for cand in iter_ancestors_inclusive(start):
            score = marker_score(cand)
            if score > best_score:
                best_score = score
                best_path = cand
            if score == len(PROJECT_ROOT_MARKERS):
                return cand.resolve(), "marker_detection_full"
    if best_path is not None and best_score > 0:
        return best_path.resolve(), "marker_detection_best_effort"
    return Path.cwd().resolve(), "cwd_fallback"


def output_root_guardrail_status_flexible(project_root: Path) -> str:
    resolved = normalize_path_no_resolve(project_root)
    if (
        "onedrive" in resolved.lower()
        or r"\users\hjy10\onedrive" in resolved.lower()
        or r"\문서\new project 2" in resolved.lower()
    ):
        return "BLOCKED_ONEDRIVE_PROJECT_ROOT"
    return "PASS"


def output_root_guardrail_status(project_root_arg: str) -> str:
    requested_path = Path(project_root_arg)
    if not requested_path.is_absolute():
        requested_path = Path.cwd() / requested_path
    expected = normalize_path_no_resolve(CANONICAL_PROJECT_ROOT)
    resolved = normalize_path_no_resolve(requested_path)
    if (
        "onedrive" in resolved.lower()
        or r"\문서\new project 2" in resolved.lower()
        or r"\users\hjy10\onedrive" in resolved.lower()
    ):
        return "BLOCKED_ONEDRIVE_PROJECT_ROOT"
    if resolved != expected:
        return "BLOCKED_WRONG_PROJECT_ROOT"
    return "PASS"


def resolve_config_path(project_root: Path, config_arg: str) -> Path:
    cp = Path(config_arg)
    if cp.is_absolute():
        return cp
    return project_root / cp


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    if not isinstance(payload, dict):
        raise ValueError("YAML root must be a mapping")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be a mapping")
    return payload


def contains_token(path_text: str, tokens: list[str]) -> bool:
    text = path_text.lower().replace("\\", "/")
    return any(t.lower() in text for t in tokens)


def match_role(path_text: str, artifact_roles: list[dict[str, Any]]) -> tuple[str, str]:
    lower_path = path_text.lower()
    for role in artifact_roles:
        role_name = safe_str(role.get("role"))
        target_table = safe_str(role.get("target_table"))
        include_kw = [safe_str(x).lower() for x in role.get("include_keywords", []) if safe_str(x)]
        exclude_kw = [safe_str(x).lower() for x in role.get("exclude_keywords", []) if safe_str(x)]
        if not role_name or not target_table or not include_kw:
            continue
        if not all(k in lower_path for k in include_kw):
            continue
        if any(k in lower_path for k in exclude_kw):
            continue
        return role_name, target_table
    return "", ""


def main() -> int:
    args = parse_args()
    disease = safe_str(args.disease).upper()
    project_root, project_root_source = detect_project_root(args.project_root)
    status = output_root_guardrail_status_flexible(project_root)
    if status != "PASS":
        raise SystemExit(status)
    output_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = resolve_config_path(project_root, args.config)
    recon_json = output_dir / f"{disease.lower()}_s3_inventory_dry_run_reconciliation_report.json"
    json_out = output_dir / f"{disease.lower()}_safe_write_plan_preview.json"
    md_out = docs_dir / f"{disease.lower()}_safe_write_plan_preview.md"

    failures: list[str] = []
    warnings: list[str] = []
    plan_rows: list[dict[str, Any]] = []
    safe_load_candidate_rows: list[dict[str, Any]] = []
    image_examples: list[str] = []
    image_excluded_count = 0
    no_admet_guardrail_violation_count = 0
    resolved_s3_prefix = ""
    resolved_local_cache = ""

    cfg_path_text = str(cfg_path).lower().replace("/", "\\")
    if "onedrive" in cfg_path_text and "new project 2" in cfg_path_text:
        failures.append("resolved_config_path_onedrive_not_allowed")

    if not cfg_path.exists():
        failures.append(f"config_not_found:{cfg_path}")
        cfg = {}
    else:
        try:
            cfg = load_yaml(cfg_path)
            paths = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
            resolved_s3_prefix = safe_str(paths.get("s3_prefix")) if isinstance(paths, dict) else ""
            lc = safe_str(paths.get("local_cache")) if isinstance(paths, dict) else ""
            resolved_local_cache = str((project_root / lc) if lc and not Path(lc).is_absolute() else Path(lc)) if lc else ""
        except Exception as exc:  # noqa: BLE001
            failures.append(f"config_parse_error:{exc}")
            cfg = {}

    if not recon_json.exists():
        failures.append(f"reconciliation_report_missing:{recon_json}")
        recon = {}
    else:
        try:
            recon = load_json(recon_json)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"reconciliation_parse_error:{exc}")
            recon = {}

    artifact_roles = cfg.get("artifact_roles", []) if isinstance(cfg, dict) else []
    blocked_tables = cfg.get("no_admet_guardrail", {}).get("blocked_target_tables", []) if isinstance(cfg, dict) else []
    blocked_table_set = {safe_str(x) for x in blocked_tables}
    s3_rows = recon.get("s3_rows", []) if isinstance(recon, dict) else []
    if not isinstance(s3_rows, list):
        s3_rows = []
    if disease == "LUAD" and "/LUNG/" in resolved_s3_prefix.replace("\\", "/").upper():
        warnings.append("luad_uses_lung_s3_prefix_alias")

    compact_before_role = int(recon.get("compact_result_candidate_count_before_role_filter", 0) or 0) if isinstance(recon, dict) else 0

    for row in s3_rows:
        if not isinstance(row, dict):
            continue
        s3_uri = safe_str(row.get("s3_uri"))
        expected_local = safe_str(row.get("expected_local_path"))
        filename = safe_str(row.get("filename"))
        path_text = safe_str(row.get("s3_key") or s3_uri)
        merged_path_text = f"{path_text} {expected_local}"
        recon_decision = safe_str(row.get("decision")).upper()
        recon_reason = safe_str(row.get("reason"))
        classification = safe_str(row.get("classification"))

        source_role = ""
        target_table = ""
        decision = recon_decision if recon_decision in DECISIONS else "UNCLASSIFIED_REVIEW"
        reason = recon_reason or "reconciliation_reason_missing"

        if contains_token(merged_path_text, IMAGE_MODAL_TOKENS) and disease == "LUAD":
            decision = "DO_NOT_LOAD_EXCLUDED"
            reason = "image_modal_excluded_for_current_stage"
            image_excluded_count += 1
            if len(image_examples) < 20:
                image_examples.append(s3_uri or path_text)

        # role matching for compact candidate paths only
        if decision in {"LOAD_CANDIDATE", "LOCAL_SYNC_NEEDED", "NEEDS_REVIEW"}:
            source_role, target_table = match_role(merged_path_text + " " + filename, artifact_roles if isinstance(artifact_roles, list) else [])
            if not source_role and decision == "LOAD_CANDIDATE":
                decision = "NEEDS_REVIEW"
                reason = "role_mapping_uncertain_for_load_candidate"
            elif not source_role and decision == "LOCAL_SYNC_NEEDED":
                decision = "NEEDS_REVIEW"
                reason = "role_mapping_uncertain_for_local_sync_candidate"
            elif source_role:
                if "no_admet" in merged_path_text.lower() and target_table in blocked_table_set:
                    decision = "BLOCKED"
                    reason = "no_admet_guardrail_blocked_target_table"
                    no_admet_guardrail_violation_count += 1
                elif decision == "NEEDS_REVIEW":
                    reason = "promising_compact_artifact_role_matched_but_requires_review"
                else:
                    reason = "matched_artifact_role_pattern"

        plan_rows.append(
            {
                "disease": disease,
                "source_file_role": source_role,
                "target_table": target_table,
                "source_file": filename,
                "source_s3_uri": s3_uri,
                "expected_local_path": expected_local,
                "classification": classification,
                "decision": decision,
                "reason": reason,
            }
        )
        if decision == "LOAD_CANDIDATE":
            safe_load_candidate_rows.append(
                {
                    "disease": disease,
                    "source_file_role": source_role,
                    "target_table": target_table,
                    "source_file": filename,
                    "source_s3_uri": s3_uri,
                    "expected_local_path": expected_local,
                    "decision": decision,
                    "reason": reason,
                }
            )

    role_matched_candidate_count = len([r for r in plan_rows if safe_str(r.get("source_file_role"))])
    counts = {
        "classified_files": len(plan_rows),
        "load_candidates": len([r for r in plan_rows if r.get("decision") == "LOAD_CANDIDATE"]),
        "needs_review": len([r for r in plan_rows if r.get("decision") == "NEEDS_REVIEW"]),
        "do_not_load_excluded": len([r for r in plan_rows if r.get("decision") == "DO_NOT_LOAD_EXCLUDED"]),
        "local_sync_needed": len([r for r in plan_rows if r.get("decision") == "LOCAL_SYNC_NEEDED"]),
        "missing": len([r for r in plan_rows if r.get("decision") == "MISSING"]),
        "blocked": len([r for r in plan_rows if r.get("decision") == "BLOCKED"]),
        "not_compact_result": len([r for r in plan_rows if r.get("decision") == "NOT_COMPACT_RESULT"]),
        "unclassified_review": len([r for r in plan_rows if r.get("decision") == "UNCLASSIFIED_REVIEW"]),
        "no_admet_guardrail_violation_count": no_admet_guardrail_violation_count,
    }

    if failures:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    payload = {
        "generated_at": now_iso(),
        "disease": disease,
        "project_root": str(project_root),
        "detected_project_root": str(project_root),
        "project_root_source": project_root_source,
        "project_root_env": safe_str(os.getenv("PROJECT_ROOT", "")),
        "requested_project_root_arg": safe_str(args.project_root),
        "output_root_guardrail_status": status,
        "resolved_config_path": str(cfg_path),
        "resolved_s3_prefix": resolved_s3_prefix,
        "resolved_local_cache": resolved_local_cache,
        "safe_write_plan_status": status,
        "failures": failures,
        "warnings": warnings,
        "counts": counts,
        "compact_result_candidate_count_before_role_filter": compact_before_role,
        "role_matched_candidate_count": role_matched_candidate_count,
        "image_modal_excluded_count": image_excluded_count,
        "image_modal_excluded_examples_first_20": image_examples,
        "no_admet_guardrail_violation_count": no_admet_guardrail_violation_count,
        "safe_load_candidate_rows": safe_load_candidate_rows,
        "plan_rows": plan_rows,
        "statement": "LUAD image/image-modal folders were excluded from the current PostgreSQL/Neo4j loading workflow."
        if disease == "LUAD"
        else "",
        "postgres_execute": "not run",
        "neo4j_execute": "not run",
    }
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# {disease} Safe Write Plan Preview",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- disease: {disease}",
        f"- project_root: {project_root}",
        f"- resolved_config_path: {cfg_path}",
        f"- resolved_s3_prefix: {resolved_s3_prefix}",
        f"- resolved_local_cache: {resolved_local_cache}",
        f"- safe_write_plan_status: {status}",
        f"- classified_files: {counts['classified_files']}",
        f"- load_candidates: {counts['load_candidates']}",
        f"- needs_review: {counts['needs_review']}",
        f"- do_not_load_excluded: {counts['do_not_load_excluded']}",
        f"- local_sync_needed: {counts['local_sync_needed']}",
        f"- missing: {counts['missing']}",
        f"- blocked: {counts['blocked']}",
        f"- NOT_COMPACT_RESULT: {counts['not_compact_result']}",
        f"- UNCLASSIFIED_REVIEW: {counts['unclassified_review']}",
        f"- no_admet_guardrail_violation_count: {no_admet_guardrail_violation_count}",
        f"- compact_result_candidate_count_before_role_filter: {compact_before_role}",
        f"- role_matched_candidate_count: {role_matched_candidate_count}",
        f"- PostgreSQL execute: not run",
        f"- Neo4j execute: not run",
        "",
        f"- image_modal_excluded_count: {image_excluded_count}",
        "",
        "## Image Modal Excluded Examples (first 20)",
    ]
    for p in image_examples:
        md.append(f"- {p}")
    if disease == "LUAD":
        md.extend(
            [
                "",
                'LUAD image/image-modal folders were excluded from the current PostgreSQL/Neo4j loading workflow.',
                "",
                "Future note: Image-modal data may be handled later by a separate multimodal/vector pipeline, but it is out of scope for this LUAD compact result artifact loading workflow.",
            ]
        )
    md.extend(["", "## Failures"])
    for f in failures:
        md.append(f"- {f}")
    md.extend(["", "## Warnings"])
    for w in warnings:
        md.append(f"- {w}")
    md_out.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"disease={disease}")
    print("dry_run=true")
    print("config_status=PASS")
    print("inventory_status=PASS")
    print(f"safe_write_plan_status={status}")
    print(f"classified_files={counts['classified_files']}")
    print(f"load_candidates={counts['load_candidates']}")
    print(f"needs_review={counts['needs_review']}")
    print(f"do_not_load_excluded={counts['do_not_load_excluded']}")
    print(f"local_sync_needed={counts['local_sync_needed']}")
    print(f"missing={counts['missing']}")
    print(f"blocked={counts['blocked']}")
    print(f"json_output={json_out}")
    print(f"markdown_output={md_out}")
    return 0 if status in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
