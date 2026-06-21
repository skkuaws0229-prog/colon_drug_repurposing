#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
PASS_STATUSES = {"PASS", "PASS_WITH_WARNINGS"}
BLOCKED_STATUS = "BLOCKED"

DISEASE_CONFIG_MAP = {
    "LUAD": "configs/diseases/luad.yaml",
    "LIHC": "configs/diseases/lihc.yaml",
    "STAD": "configs/diseases/stad.yaml",
    "PAAD": "configs/diseases/paad.yaml",
    "HNSC": "configs/diseases/hnsc.yaml",
    "BRCA": "configs/diseases/brca.yaml",
    "COAD": "configs/diseases/coad.yaml",
}

NODE_KEYS = [
    "Disease",
    "DrugCandidate",
    "CandidateScore",
    "TierEvidence",
    "FinalCandidateEvidence",
    "AdmetEvidence",
    "ExternalValidationEvidence",
    "ModelEvidence",
    "ModelDetailEvidence",
    "EnsembleEvidence",
    "SourceArtifact",
    "LoadAuditEvidence",
    "Run",
]

REL_KEYS = [
    "CANDIDATE_FOR",
    "HAS_CANDIDATE_SCORE",
    "HAS_TIER",
    "SELECTED_AS_FINAL",
    "HAS_ADMET_PROFILE",
    "VALIDATED_BY_EXTERNAL_DATA",
    "HAS_EXTERNAL_VALIDATION",
    "SUPPORTED_BY_MODEL",
    "HAS_DETAILED_MODEL_METRIC",
    "SUPPORTED_BY_ENSEMBLE",
    "DERIVED_FROM_SOURCE",
    "PRODUCED_EVIDENCE",
    "AUDITS_LOAD_FOR",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parallel dry-run preflight for multi-cancer PG/Neo4j load planning.")
    p.add_argument("--project-root", default=str(CANONICAL_PROJECT_ROOT))
    p.add_argument("--diseases", default="LUAD,LIHC,STAD,PAAD,HNSC")
    p.add_argument("--workers", type=int, default=5)
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument("--dry-run", action="store_true", default=True)
    return p.parse_args()


def canonicalize_disease(disease: str) -> str:
    d = safe_str(disease).upper()
    if d == "BRAC":
        return "BRCA"
    return d


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def inspection_status(payload: dict[str, Any]) -> str:
    if not payload:
        return "FAIL"
    errors = payload.get("errors", [])
    if isinstance(errors, list) and errors:
        return "FAIL"
    approved = int(payload.get("approved_for_postgres_load_count", 0) or 0)
    remaining = int(payload.get("remaining_uninspected_count", 0) or 0)
    if approved > 0 and remaining == 0:
        return "PASS"
    if approved > 0:
        return "PASS_WITH_WARNINGS"
    return "PASS_WITH_WARNINGS"


def build_neo4j_preview_counts(plan_rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    node_counts = {k: 0 for k in NODE_KEYS}
    rel_counts = {k: 0 for k in REL_KEYS}

    for row in plan_rows:
        table = safe_str(row.get("target_table")).lower()
        if table in {"drug_candidate_result", "drug_candidate_tier"}:
            node_counts["DrugCandidate"] += 1
            node_counts["CandidateScore"] += 1
            node_counts["TierEvidence"] += 1
            rel_counts["CANDIDATE_FOR"] += 1
            rel_counts["HAS_CANDIDATE_SCORE"] += 1
            rel_counts["HAS_TIER"] += 1
        elif table == "final_candidate_result":
            node_counts["FinalCandidateEvidence"] += 1
            rel_counts["SELECTED_AS_FINAL"] += 1
        elif table in {"admet_result", "admet_summary"}:
            node_counts["AdmetEvidence"] += 1
            rel_counts["HAS_ADMET_PROFILE"] += 1
        elif table == "external_validation_result":
            node_counts["ExternalValidationEvidence"] += 1
            rel_counts["VALIDATED_BY_EXTERNAL_DATA"] += 1
            rel_counts["HAS_EXTERNAL_VALIDATION"] += 1
        elif table == "model_metric":
            node_counts["ModelEvidence"] += 1
            rel_counts["SUPPORTED_BY_MODEL"] += 1
        elif table == "model_metric_detailed":
            node_counts["ModelDetailEvidence"] += 1
            rel_counts["HAS_DETAILED_MODEL_METRIC"] += 1
        elif table == "ensemble_metric":
            node_counts["EnsembleEvidence"] += 1
            rel_counts["SUPPORTED_BY_ENSEMBLE"] += 1
        elif table == "source_artifact":
            node_counts["SourceArtifact"] += 1
        elif table == "load_audit":
            node_counts["LoadAuditEvidence"] += 1
        elif table == "run_manifest":
            node_counts["Run"] += 1

    if plan_rows:
        node_counts["Disease"] = 1
    if node_counts["LoadAuditEvidence"] > 0:
        rel_counts["AUDITS_LOAD_FOR"] = 1

    lineage_total = (
        node_counts["CandidateScore"]
        + node_counts["TierEvidence"]
        + node_counts["FinalCandidateEvidence"]
        + node_counts["AdmetEvidence"]
        + node_counts["ExternalValidationEvidence"]
        + node_counts["ModelEvidence"]
        + node_counts["ModelDetailEvidence"]
        + node_counts["EnsembleEvidence"]
    )
    rel_counts["DERIVED_FROM_SOURCE"] = lineage_total
    rel_counts["PRODUCED_EVIDENCE"] = lineage_total
    return node_counts, rel_counts


def summarize_disease(
    *,
    project_root: Path,
    python_exe: str,
    disease_input: str,
) -> dict[str, Any]:
    disease = canonicalize_disease(disease_input)
    if disease not in DISEASE_CONFIG_MAP:
        return {
            "disease": disease,
            "final_status": BLOCKED_STATUS,
            "errors": [f"unsupported_disease:{disease_input}"],
        }

    config_rel = DISEASE_CONFIG_MAP[disease]
    config_path = project_root / config_rel

    out_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    slug = disease.lower()
    yaml_json = out_dir / f"{slug}_disease_yaml_validation_report.json"
    recon_json = out_dir / f"{slug}_s3_inventory_dry_run_reconciliation_report.json"
    safe_json = out_dir / f"{slug}_safe_write_plan_preview.json"
    candidate_json = out_dir / f"{slug}_compact_result_candidate_discovery_report.json"
    inspect_json = out_dir / f"{slug}_real_file_inspection_report.json"
    inspect_md = docs_dir / f"{slug}_real_file_inspection_report.md"
    plan_json = out_dir / f"{slug}_postgres_load_plan_from_real_inspection.json"
    plan_md = docs_dir / f"{slug}_postgres_load_plan_from_real_inspection.md"

    stage_results: dict[str, Any] = {}
    commands = [
        (
            "yaml_validation",
            [
                python_exe,
                str(project_root / "scripts" / "load" / "validate_disease_yaml_config.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(config_path),
            ],
        ),
        (
            "inventory_reconcile",
            [
                python_exe,
                str(project_root / "scripts" / "load" / "reconcile_disease_s3_inventory_with_dry_run.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(config_path),
                "--dry-run",
            ],
        ),
        (
            "safe_write_plan",
            [
                python_exe,
                str(project_root / "scripts" / "load" / "build_disease_safe_write_plan.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(config_path),
            ],
        ),
        (
            "real_file_inspection",
            [
                python_exe,
                str(project_root / "scripts" / "load" / "inspect_disease_s3_files_for_postgres_load.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(config_path),
                "--candidate-json",
                str(candidate_json),
                "--decision-filter",
                "LOAD_CANDIDATE,LOCAL_SYNC_NEEDED,NEEDS_REVIEW",
                "--output-json",
                str(inspect_json),
                "--output-md",
                str(inspect_md),
            ],
        ),
        (
            "postgres_load_plan",
            [
                python_exe,
                str(project_root / "scripts" / "load" / "build_disease_postgres_load_plan_from_real_inspection.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(config_path),
                "--inspection-json",
                str(inspect_json),
            ],
        ),
    ]

    for name, cmd in commands:
        stage_results[name] = run_cmd(cmd, project_root)

    yaml_payload = load_json(yaml_json)
    recon_payload = load_json(recon_json)
    safe_payload = load_json(safe_json)
    inspect_payload = load_json(inspect_json)
    plan_payload = load_json(plan_json)
    cfg = load_yaml(config_path)

    plan_rows_raw = plan_payload.get("plan_rows", [])
    plan_rows = [x for x in plan_rows_raw if isinstance(x, dict)] if isinstance(plan_rows_raw, list) else []
    inspection_rows_raw = inspect_payload.get("rows", [])
    inspection_rows = [x for x in inspection_rows_raw if isinstance(x, dict)] if isinstance(inspection_rows_raw, list) else []
    recon_rows_raw = recon_payload.get("s3_rows", [])
    recon_rows = [x for x in recon_rows_raw if isinstance(x, dict)] if isinstance(recon_rows_raw, list) else []

    scanned_object_count = int(recon_payload.get("scanned_object_count", 0) or 0)
    excluded_object_count = int((recon_payload.get("decision_counts", {}) or {}).get("DO_NOT_LOAD_EXCLUDED", 0) or 0)
    blocked_from_inspection = [r for r in inspection_rows if safe_str(r.get("decision")) == "BLOCKED"]
    blocked_from_reconcile = [r for r in recon_rows if safe_str(r.get("decision")) == "BLOCKED"]
    blocked_uris = sorted(
        {
            safe_str(r.get("s3_uri"))
            for r in [*blocked_from_inspection, *blocked_from_reconcile]
            if safe_str(r.get("s3_uri"))
        }
    )
    blocked_files_count = len(blocked_uris)

    approved_postgres_load_candidates = len(plan_rows)
    needs_review_count = int(inspect_payload.get("needs_review_count", 0) or 0)

    target_postgres_tables = sorted({safe_str(r.get("target_table")) for r in plan_rows if safe_str(r.get("target_table"))})

    expected_roles = []
    artifact_roles = cfg.get("artifact_roles", [])
    if isinstance(artifact_roles, list):
        expected_roles = [safe_str(x.get("role")) for x in artifact_roles if isinstance(x, dict) and safe_str(x.get("role"))]
    actual_roles = sorted({safe_str(r.get("proposed_role")) for r in plan_rows if safe_str(r.get("proposed_role"))})
    missing_required_roles = [x for x in expected_roles if x not in actual_roles]

    columns_profiled_files = len([r for r in inspection_rows if isinstance(r.get("columns_or_keys"), list) and r.get("columns_or_keys")])

    node_counts, rel_counts = build_neo4j_preview_counts(plan_rows)

    config_status = safe_str(yaml_payload.get("config_status")) or ("PASS" if stage_results["yaml_validation"]["returncode"] == 0 else "FAIL")
    inventory_status = safe_str(recon_payload.get("inventory_status")) or ("PASS" if stage_results["inventory_reconcile"]["returncode"] == 0 else "FAIL")
    safe_write_status = safe_str(safe_payload.get("safe_write_plan_status")) or ("PASS" if stage_results["safe_write_plan"]["returncode"] == 0 else "FAIL")
    inspect_status = inspection_status(inspect_payload) if stage_results["real_file_inspection"]["returncode"] == 0 else "FAIL"
    postgres_plan_status = safe_str(plan_payload.get("status")) or ("PASS" if stage_results["postgres_load_plan"]["returncode"] == 0 else "FAIL")

    stage_failures = []
    for stage_name, stage_status in [
        ("yaml_validation", config_status),
        ("inventory_reconcile", inventory_status),
        ("safe_write_plan", safe_write_status),
        ("real_file_inspection", inspect_status),
        ("postgres_load_plan", postgres_plan_status),
    ]:
        if stage_status not in PASS_STATUSES:
            stage_failures.append(stage_name)

    if stage_failures or approved_postgres_load_candidates <= 0:
        final_status = BLOCKED_STATUS
    elif missing_required_roles or blocked_files_count > 0 or needs_review_count > 0:
        final_status = "PASS_WITH_WARNINGS"
    else:
        final_status = "PASS"

    report = {
        "generated_at": now_iso(),
        "disease": disease,
        "dry_run": True,
        "postgres_execute": "not run",
        "neo4j_execute": "not run",
        "config_path": str(config_path),
        "scanned_object_count": scanned_object_count,
        "excluded_object_count": excluded_object_count,
        "approved_postgres_load_candidates": approved_postgres_load_candidates,
        "blocked_files_count": blocked_files_count,
        "blocked_files_first_50": blocked_uris[:50],
        "missing_required_roles": missing_required_roles,
        "target_postgres_tables": target_postgres_tables,
        "columns_profiled_files": columns_profiled_files,
        "neo4j_plan": {
            "node_counts": node_counts,
            "relationship_counts": rel_counts,
            "total_nodes": int(sum(node_counts.values())),
            "total_relationships": int(sum(rel_counts.values())),
        },
        "stage_statuses": {
            "yaml_validation": config_status,
            "inventory_reconcile": inventory_status,
            "safe_write_plan": safe_write_status,
            "real_file_inspection": inspect_status,
            "postgres_load_plan": postgres_plan_status,
        },
        "stage_failures": stage_failures,
        "needs_review_count": needs_review_count,
        "warnings": [
            *[safe_str(x) for x in (yaml_payload.get("warnings", []) if isinstance(yaml_payload.get("warnings"), list) else [])],
            *[safe_str(x) for x in (recon_payload.get("warnings", []) if isinstance(recon_payload.get("warnings"), list) else [])],
            *[safe_str(x) for x in (safe_payload.get("warnings", []) if isinstance(safe_payload.get("warnings"), list) else [])],
        ],
        "final_status": final_status,
        "report_paths": {
            "yaml_validation_json": str(yaml_json),
            "inventory_reconcile_json": str(recon_json),
            "safe_write_plan_json": str(safe_json),
            "inspection_json": str(inspect_json),
            "inspection_md": str(inspect_md),
            "postgres_plan_json": str(plan_json),
            "postgres_plan_md": str(plan_md),
        },
        "stage_results": stage_results,
    }

    disease_json_out = out_dir / f"{slug}_parallel_preflight_report.json"
    disease_md_out = docs_dir / f"{slug}_parallel_preflight_report.md"
    disease_json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# {disease} Parallel Preflight Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- dry_run: `true`",
        "- postgres_execute: `not run`",
        "- neo4j_execute: `not run`",
        f"- scanned_object_count: `{scanned_object_count}`",
        f"- excluded_object_count: `{excluded_object_count}`",
        f"- approved_postgres_load_candidates: `{approved_postgres_load_candidates}`",
        f"- blocked_files_count: `{blocked_files_count}`",
        f"- missing_required_roles_count: `{len(missing_required_roles)}`",
        f"- target_postgres_tables_count: `{len(target_postgres_tables)}`",
        f"- columns_profiled_files: `{columns_profiled_files}`",
        f"- final_status: `{final_status}`",
        "",
        "## Stage Statuses",
    ]
    for k, v in report["stage_statuses"].items():
        md_lines.append(f"- {k}: `{v}`")
    md_lines.extend(["", "## Missing Required Roles"])
    if missing_required_roles:
        for role in missing_required_roles:
            md_lines.append(f"- {role}")
    else:
        md_lines.append("- (none)")
    md_lines.extend(["", "## Target PostgreSQL Tables"])
    if target_postgres_tables:
        for t in target_postgres_tables:
            md_lines.append(f"- {t}")
    else:
        md_lines.append("- (none)")
    md_lines.extend(["", "## Neo4j Plan Node Counts"])
    for k in NODE_KEYS:
        md_lines.append(f"- {k}: {int(node_counts.get(k, 0) or 0)}")
    md_lines.extend(["", "## Neo4j Plan Relationship Counts"])
    for k in REL_KEYS:
        md_lines.append(f"- {k}: {int(rel_counts.get(k, 0) or 0)}")
    md_lines.extend(["", "## Blocked Files (first 50)"])
    if blocked_uris:
        for uri in blocked_uris[:50]:
            md_lines.append(f"- {uri}")
    else:
        md_lines.append("- (none)")
    disease_md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    report["per_disease_json_report"] = str(disease_json_out)
    report["per_disease_md_report"] = str(disease_md_out)
    return report


def main() -> int:
    args = parse_args()
    requested_root = Path(args.project_root)
    if not requested_root.is_absolute():
        requested_root = Path.cwd() / requested_root
    expected = os.path.normcase(os.path.normpath(str(CANONICAL_PROJECT_ROOT)))
    resolved_no_resolve = os.path.normcase(os.path.normpath(str(requested_root)))
    if resolved_no_resolve != expected:
        raise SystemExit(f"BLOCKED_WRONG_PROJECT_ROOT:{resolved_no_resolve}")
    project_root = CANONICAL_PROJECT_ROOT

    diseases = [canonicalize_disease(x) for x in safe_str(args.diseases).split(",") if safe_str(x)]
    if not diseases:
        diseases = ["LUAD", "LIHC", "STAD", "PAAD", "HNSC"]

    results: list[dict[str, Any]] = []
    max_workers = max(1, min(int(args.workers or 1), len(diseases)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {
            pool.submit(
                summarize_disease,
                project_root=project_root,
                python_exe=args.python_exe,
                disease_input=disease,
            ): disease
            for disease in diseases
        }
        for fut in as_completed(fut_map):
            results.append(fut.result())

    order_index = {d: i for i, d in enumerate(diseases)}
    results.sort(key=lambda x: order_index.get(safe_str(x.get("disease")), 999))

    combined_status = "PASS"
    if any(safe_str(x.get("final_status")) == BLOCKED_STATUS for x in results):
        combined_status = BLOCKED_STATUS
    elif any(safe_str(x.get("final_status")) == "PASS_WITH_WARNINGS" for x in results):
        combined_status = "PASS_WITH_WARNINGS"

    combined = {
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "diseases": diseases,
        "dry_run": True,
        "postgres_execute": "not run",
        "neo4j_execute": "not run",
        "combined_status": combined_status,
        "summary_counts": {
            "scanned_object_count": int(sum(int(x.get("scanned_object_count", 0) or 0) for x in results)),
            "excluded_object_count": int(sum(int(x.get("excluded_object_count", 0) or 0) for x in results)),
            "approved_postgres_load_candidates": int(sum(int(x.get("approved_postgres_load_candidates", 0) or 0) for x in results)),
            "blocked_files_count": int(sum(int(x.get("blocked_files_count", 0) or 0) for x in results)),
            "missing_required_roles_count": int(sum(len(x.get("missing_required_roles", []) or []) for x in results)),
        },
        "per_disease": results,
    }

    out_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    combined_json = out_dir / "multi_cancer_parallel_preflight_report.json"
    combined_md = docs_dir / "multi_cancer_parallel_preflight_report.md"
    combined_json.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Multi-Cancer Parallel Preflight Report",
        "",
        f"- generated_at: `{combined['generated_at']}`",
        "- dry_run: `true`",
        "- postgres_execute: `not run`",
        "- neo4j_execute: `not run`",
        f"- combined_status: `{combined_status}`",
        "",
        "## Combined Summary",
        f"- scanned_object_count: `{combined['summary_counts']['scanned_object_count']}`",
        f"- excluded_object_count: `{combined['summary_counts']['excluded_object_count']}`",
        f"- approved_postgres_load_candidates: `{combined['summary_counts']['approved_postgres_load_candidates']}`",
        f"- blocked_files_count: `{combined['summary_counts']['blocked_files_count']}`",
        f"- missing_required_roles_count: `{combined['summary_counts']['missing_required_roles_count']}`",
        "",
        "## Per Disease Status",
        "",
        "| disease | scanned_object_count | excluded_object_count | approved_postgres_load_candidates | blocked_files_count | missing_required_roles | target_postgres_tables | neo4j_nodes | neo4j_relationships | final_status |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    safe_str(row.get("disease")),
                    str(int(row.get("scanned_object_count", 0) or 0)),
                    str(int(row.get("excluded_object_count", 0) or 0)),
                    str(int(row.get("approved_postgres_load_candidates", 0) or 0)),
                    str(int(row.get("blocked_files_count", 0) or 0)),
                    str(len(row.get("missing_required_roles", []) or [])),
                    ", ".join(row.get("target_postgres_tables", []) or []) or "(none)",
                    str(int((row.get("neo4j_plan", {}) or {}).get("total_nodes", 0) or 0)),
                    str(int((row.get("neo4j_plan", {}) or {}).get("total_relationships", 0) or 0)),
                    safe_str(row.get("final_status")),
                ]
            )
            + " |"
        )
    combined_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"diseases={','.join(diseases)}")
    print(f"combined_status={combined_status}")
    print(f"json_output={combined_json}")
    print(f"markdown_output={combined_md}")
    return 0 if combined_status in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
