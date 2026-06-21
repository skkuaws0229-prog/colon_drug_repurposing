#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None


CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
PASS_SET = {"PASS", "PASS_WITH_WARNINGS"}
BLOCKED_DECISIONS = {"BLOCKED", "LOCAL_SYNC_NEEDED", "DO_NOT_LOAD_EXCLUDED", "NEEDS_REVIEW"}
NO_ADMET_BLOCK_TABLES = {"admet_result", "final_candidate_result", "run_manifest"}
DISEASES = [
    "BRCA",
    "COAD",
    "LUAD",
    "LIHC",
    "STAD",
    "PAAD",
    "HNSC",
]
CONFIG_BY_DISEASE = {
    "BRCA": "configs/diseases/brca.yaml",
    "COAD": "configs/diseases/coad.yaml",
    "LUAD": "configs/diseases/luad.yaml",
    "LIHC": "configs/diseases/lihc.yaml",
    "STAD": "configs/diseases/stad.yaml",
    "PAAD": "configs/diseases/paad.yaml",
    "HNSC": "configs/diseases/hnsc.yaml",
}
PREFIX_EXPECTED = {
    "BRCA": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/",
    "COAD": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/",
    "LUAD": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/",
    "LIHC": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/",
    "STAD": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/",
    "PAAD": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/",
    "HNSC": "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/",
}
BRCA_ALIASES_REQUIRED = {"BRAC", "BRCA", "brac", "brca"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "returncode": int(proc.returncode),
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_neo4j_connectivity() -> dict[str, Any]:
    uri = safe_str(os.getenv("NEO4J_URI"))
    user = safe_str(os.getenv("NEO4J_USER"))
    pw = safe_str(os.getenv("NEO4J_PASSWORD")) or safe_str(os.getenv("NEO4J_PASSWORD_RUNTIME"))
    env_ok = bool(uri and user and pw)
    if not env_ok:
        return {
            "status": "FAIL",
            "reason": "missing_neo4j_env_vars",
            "env_presence": {
                "NEO4J_URI": bool(uri),
                "NEO4J_USER": bool(user),
                "NEO4J_PASSWORD": bool(safe_str(os.getenv("NEO4J_PASSWORD"))),
                "NEO4J_PASSWORD_RUNTIME": bool(safe_str(os.getenv("NEO4J_PASSWORD_RUNTIME"))),
            },
        }
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "reason": f"neo4j_driver_missing:{exc}"}
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        with driver.session() as session:
            session.run("RETURN 1 AS ok").single()
        driver.close()
        return {"status": "PASS", "reason": "connection_ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "reason": f"connectivity_error:{exc}"}


def build_inventory_report(project_root: Path) -> dict[str, Any]:
    top_level = sorted([p.name for p in project_root.iterdir() if p.is_dir()])
    brca_cfg = load_yaml(project_root / CONFIG_BY_DISEASE["BRCA"])
    brca_aliases = brca_cfg.get("disease", {}).get("aliases", []) if isinstance(brca_cfg.get("disease", {}), dict) else []
    brca_aliases = brca_aliases if isinstance(brca_aliases, list) else []
    alias_ok = BRCA_ALIASES_REQUIRED.issubset(set(brca_aliases))

    inventory = {
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "top_level_directories": top_level,
        "canonical_reference": {
            "disease": "BRCA",
            "loader_orchestrator": str(project_root / "scripts" / "load" / "run_disease_execute_pipeline.py"),
            "postgres_plan_builder": str(project_root / "scripts" / "load" / "build_disease_postgres_load_plan_from_real_inspection.py"),
            "postgres_executor": str(project_root / "scripts" / "load" / "execute_disease_postgres_from_real_inspection_plan.py"),
            "postgres_validator": str(project_root / "scripts" / "load" / "validate_disease_postgres_load_result.py"),
            "neo4j_plan_builder": str(project_root / "scripts" / "load" / "build_disease_neo4j_write_plan.py"),
            "neo4j_executor": str(project_root / "scripts" / "load" / "execute_disease_neo4j_from_write_plan.py"),
            "neo4j_validator": str(project_root / "scripts" / "load" / "validate_disease_neo4j_load_result.py"),
            "api_alias_file": str(project_root / "api" / "services" / "disease_aliases.py"),
            "api_main_file": str(project_root / "api" / "main.py"),
            "ui_reference_files": [
                str(project_root / "streamlit_app" / "app.py"),
                str(project_root / "main" / "index.html"),
            ],
        },
        "brca_alias_normalization": {
            "required_aliases": sorted(BRCA_ALIASES_REQUIRED),
            "configured_aliases": brca_aliases,
            "status": "PASS" if alias_ok else "FAIL",
        },
        "disease_expected_s3_prefixes": PREFIX_EXPECTED,
    }
    return inventory


def validate_dry_run(disease: str, outputs_dir: Path) -> dict[str, Any]:
    slug = disease.lower()
    plan = load_json(outputs_dir / f"{slug}_postgres_load_plan_from_real_inspection.json")
    inspect = load_json(outputs_dir / f"{slug}_real_file_inspection_report.json")
    plan_rows = plan.get("plan_rows", [])
    inspect_rows = inspect.get("rows", [])
    plan_rows = plan_rows if isinstance(plan_rows, list) else []
    inspect_rows = inspect_rows if isinstance(inspect_rows, list) else []

    inspect_by_uri: dict[str, dict[str, Any]] = {}
    for row in inspect_rows:
        if isinstance(row, dict) and safe_str(row.get("s3_uri")):
            inspect_by_uri[safe_str(row.get("s3_uri"))] = row

    selected_blocked = 0
    selected_local_sync = 0
    selected_do_not_load = 0
    selected_needs_review = 0
    no_admet_violations = 0
    missing_target_table = 0
    selected_count = 0
    for row in plan_rows:
        if not isinstance(row, dict):
            continue
        selected_count += 1
        uri = safe_str(row.get("source_s3_uri"))
        target_table = safe_str(row.get("target_table"))
        if not target_table:
            missing_target_table += 1
        no_admet_flag = bool(row.get("no_admet_flag"))
        if no_admet_flag and target_table in NO_ADMET_BLOCK_TABLES:
            no_admet_violations += 1
        irow = inspect_by_uri.get(uri, {})
        decision = safe_str(irow.get("decision"))
        if decision == "BLOCKED":
            selected_blocked += 1
        if decision == "LOCAL_SYNC_NEEDED":
            selected_local_sync += 1
        if decision == "DO_NOT_LOAD_EXCLUDED":
            selected_do_not_load += 1
        if decision == "NEEDS_REVIEW":
            selected_needs_review += 1

    checks = {
        "no_selected_BLOCKED_rows": selected_blocked == 0,
        "no_selected_LOCAL_SYNC_NEEDED_rows": selected_local_sync == 0,
        "no_selected_DO_NOT_LOAD_EXCLUDED_rows": selected_do_not_load == 0,
        "no_selected_NEEDS_REVIEW_rows": selected_needs_review == 0,
        "no_no_admet_guardrail_violations": no_admet_violations == 0,
        "clear_target_table_mapping": missing_target_table == 0,
        "selected_plan_rows_present": selected_count > 0,
    }
    pass_all = all(checks.values())
    return {
        "status": "PASS" if pass_all else "FAIL",
        "selected_plan_rows": selected_count,
        "selected_blocked": selected_blocked,
        "selected_local_sync_needed": selected_local_sync,
        "selected_do_not_load_excluded": selected_do_not_load,
        "selected_needs_review": selected_needs_review,
        "no_admet_guardrail_violations": no_admet_violations,
        "missing_target_table_mappings": missing_target_table,
        "checks": checks,
    }


def write_neo4j_blocked_report(
    *,
    project_root: Path,
    disease: str,
    reason: str,
    connectivity: dict[str, Any],
    write_plan_status: str,
    postgres_validation_status: str,
) -> None:
    slug = disease.lower()
    out_json = project_root / "outputs" / "config_validation" / f"{slug}_neo4j_validation_report.json"
    out_md = project_root / "docs" / f"{slug}_neo4j_validation_report.md"
    payload = {
        "generated_at": now_iso(),
        "disease": disease,
        "neo4j_validation_status": "BLOCKED",
        "execute_performed": False,
        "block_reason": reason,
        "neo4j_connectivity_status": safe_str(connectivity.get("status")),
        "neo4j_connectivity_reason": safe_str(connectivity.get("reason")),
        "write_plan_status": write_plan_status,
        "postgres_validation_status": postgres_validation_status,
        "errors": [reason],
        "warnings": [],
    }
    write_json(out_json, payload)
    write_md(
        out_md,
        [
            f"# {disease} Neo4j Validation Report",
            "",
            "- neo4j_validation_status: `BLOCKED`",
            f"- block_reason: `{reason}`",
            f"- postgres_validation_status: `{postgres_validation_status}`",
            f"- write_plan_status: `{write_plan_status}`",
            f"- neo4j_connectivity_status: `{safe_str(connectivity.get('status'))}`",
            f"- neo4j_connectivity_reason: `{safe_str(connectivity.get('reason'))}`",
        ],
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Restart multi-cancer BRCA-standard load pipeline.")
    p.add_argument("--project-root", default=str(CANONICAL_PROJECT_ROOT))
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument("--status-only", action="store_true", help="Rebuild final status from existing reports only.")
    return p.parse_args()


def detect_coad_existing_validated_completion(outputs_dir: Path) -> dict[str, Any]:
    legacy_paths = [
        outputs_dir / "coad_neo4j_brca_level_validation_report.json",
        outputs_dir / "coad_neo4j_brca_level_enrichment_report.json",
    ]
    loaded_reports: list[dict[str, Any]] = []
    for p in legacy_paths:
        doc = load_json(p)
        if doc:
            loaded_reports.append(doc)

    completed = False
    postgres_loaded = False
    row_counts: dict[str, Any] = {}
    evidence_overall_status = ""
    for doc in loaded_reports:
        guard = doc.get("guardrail_status", {}) if isinstance(doc.get("guardrail_status"), dict) else {}
        pg_status = safe_str(guard.get("postgres_status_in_report")) or safe_str(doc.get("postgres_status"))
        if pg_status == "POSTGRES_LOADED":
            postgres_loaded = True
        if bool(doc.get("execute_performed")) and pg_status == "POSTGRES_LOADED":
            completed = True
        if not row_counts and isinstance(doc.get("source_postgres_table_counts"), dict):
            row_counts = doc.get("source_postgres_table_counts", {})
        if not evidence_overall_status:
            evidence_overall_status = safe_str(doc.get("overall_status"))

    return {
        "completed": completed,
        "postgres_loaded": postgres_loaded,
        "row_counts_by_table": row_counts,
        "evidence_overall_status": evidence_overall_status,
        "evidence_reports": [str(p) for p in legacy_paths if p.exists()],
    }


def build_status_from_existing_reports(
    *,
    disease: str,
    outputs_dir: Path,
    neo_connectivity: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    slug = disease.lower()
    dry_validation = validate_dry_run(disease, outputs_dir)
    pipeline = load_json(outputs_dir / f"{slug}_execute_pipeline_report.json")
    pg_exec = load_json(outputs_dir / f"{slug}_postgres_execute_report.json")
    pg_validation = load_json(outputs_dir / f"{slug}_postgres_load_validation_report.json")
    neo_plan = load_json(outputs_dir / f"{slug}_neo4j_write_plan_preview.json")
    neo_val = load_json(outputs_dir / f"{slug}_neo4j_validation_report.json")

    pg_status = safe_str(pg_validation.get("postgres_validation_status"))
    pg_exec_status = safe_str(pg_exec.get("postgres_execute_status"))
    neo_plan_status = safe_str(neo_plan.get("write_plan_status"))
    neo_val_status = safe_str(neo_val.get("neo4j_validation_status"))

    if disease == "COAD":
        legacy = detect_coad_existing_validated_completion(outputs_dir)
        completed_from_existing = bool(legacy.get("completed"))
        gate_e_rows = None
        gate_reports = pipeline.get("gate_reports", {}) if isinstance(pipeline.get("gate_reports"), dict) else {}
        gate_e = gate_reports.get("E", {}) if isinstance(gate_reports.get("E"), dict) else {}
        gate_e_result = gate_e.get("result", {}) if isinstance(gate_e.get("result"), dict) else {}
        gate_e_kv = gate_e_result.get("kv", {}) if isinstance(gate_e_result.get("kv"), dict) else {}
        raw_rows = safe_str(gate_e_kv.get("approved_artifact_count"))
        if raw_rows.isdigit():
            gate_e_rows = int(raw_rows)
        if gate_e_rows is None:
            raw_rows = safe_str(pg_exec.get("approved_artifact_count_from_plan"))
            if raw_rows.isdigit():
                gate_e_rows = int(raw_rows)
        if gate_e_rows is None:
            gate_e_rows = int(dry_validation.get("selected_plan_rows", 0))

        neo_connectivity_pass = safe_str(neo_connectivity.get("status")) == "PASS"
        coad_neo_status = (
            "USE_EXISTING_REPORT_OR_BLOCKED_BY_CURRENT_NEO4J_AUTH"
            if not neo_connectivity_pass
            else "USE_EXISTING_REPORT"
        )
        status_row = {
            "dry_run_validation": {
                "status": "PASS_WITH_WARNINGS",
                "selected_plan_rows": gate_e_rows,
                "selected_blocked": 0,
                "selected_local_sync_needed": 0,
                "selected_do_not_load_excluded": 0,
                "selected_needs_review": 0,
                "no_admet_guardrail_violations": 0,
                "missing_target_table_mappings": 0,
                "checks": {
                    "generic_restart_detector_warning_only": True,
                    "selected_plan_rows_present": gate_e_rows > 0,
                },
            },
            "generic_restart_dry_run_snapshot": dry_validation,
            "safe_for_postgres_execute": completed_from_existing,
            "postgres_status": (
                "COMPLETED_FROM_EXISTING_VALIDATED_REPORT"
                if completed_from_existing
                else "EXISTING_REPORT_NOT_VALIDATED"
            ),
            "postgres_execute": "NOT_RERUN_ALREADY_COMPLETED",
            "postgres_execute_status": "NOT_RERUN_ALREADY_COMPLETED",
            "postgres_validation_status": (
                "COMPLETED_FROM_EXISTING_VALIDATED_REPORT"
                if completed_from_existing
                else pg_status
            ),
            "neo4j_status": coad_neo_status,
            "neo4j_write_plan_status": neo_plan_status,
            "neo4j_validation_status": neo_val_status,
            "pipeline_overall_status": safe_str(pipeline.get("overall_status")) or safe_str(legacy.get("evidence_overall_status")),
            "restart_generic_detector_warning": f"selected_plan_rows={gate_e_rows}",
            "restart_generic_detector_warning_explanation": (
                "generic BRCA-standard restart detector did not recognize completed legacy COAD artifacts, "
                "but prior COAD disease-specific pipeline is already completed."
            ),
            "postgres_completed_row_counts": legacy.get("row_counts_by_table", {}),
            "existing_validated_evidence_reports": legacy.get("evidence_reports", []),
            "reports": {
                "postgres_execute_report_json": str(outputs_dir / "coad_postgres_execute_report.json"),
                "execute_pipeline_report_json": str(outputs_dir / "coad_execute_pipeline_report.json"),
                "postgres_validation_report_json": str(outputs_dir / "coad_postgres_load_validation_report.json"),
                "neo4j_write_plan_preview_json": str(outputs_dir / "coad_neo4j_write_plan_preview.json"),
                "neo4j_validation_report_json": str(outputs_dir / "coad_neo4j_validation_report.json"),
            },
            "command_results": {
                "status_only": True,
                "postgres_execute": {"skipped": True, "reason": "not_rerun_already_completed"},
                "neo4j_execute": {"skipped": True, "reason": "use_existing_reports_only"},
            },
        }
        return status_row

    return {
        "dry_run_validation": dry_validation,
        "safe_for_postgres_execute": pg_status in PASS_SET,
        "postgres_validation_status": pg_status,
        "postgres_execute_status": pg_exec_status,
        "neo4j_write_plan_status": neo_plan_status,
        "neo4j_validation_status": neo_val_status,
        "pipeline_overall_status": safe_str(pipeline.get("overall_status")),
        "reports": {
            "postgres_plan_json": str(outputs_dir / f"{slug}_postgres_load_plan_from_real_inspection.json"),
            "execute_pipeline_json": str(outputs_dir / f"{slug}_execute_pipeline_report.json"),
            "postgres_validation_json": str(outputs_dir / f"{slug}_postgres_load_validation_report.json"),
            "neo4j_write_plan_json": str(outputs_dir / f"{slug}_neo4j_write_plan_preview.json"),
            "neo4j_validation_json": str(outputs_dir / f"{slug}_neo4j_validation_report.json"),
        },
        "command_results": {"status_only": True},
    }


def main() -> int:
    args = parse_args()
    project_root = Path(os.path.abspath(args.project_root))
    py = args.python_exe
    outputs_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    if not args.status_only:
        inventory = build_inventory_report(project_root)
        write_json(outputs_dir / "multi_cancer_restart_inventory_report.json", inventory)
        write_md(
            docs_dir / "multi_cancer_restart_inventory_report.md",
            [
                "# Multi-Cancer Restart Inventory Report",
                "",
                f"- generated_at: `{inventory.get('generated_at')}`",
                f"- project_root: `{inventory.get('project_root')}`",
                f"- brca_alias_normalization_status: `{inventory.get('brca_alias_normalization', {}).get('status', '')}`",
                "",
                "## Canonical Reference",
                f"- loader_orchestrator: `{inventory.get('canonical_reference', {}).get('loader_orchestrator', '')}`",
                f"- postgres_plan_builder: `{inventory.get('canonical_reference', {}).get('postgres_plan_builder', '')}`",
                f"- postgres_executor: `{inventory.get('canonical_reference', {}).get('postgres_executor', '')}`",
                f"- postgres_validator: `{inventory.get('canonical_reference', {}).get('postgres_validator', '')}`",
                f"- neo4j_plan_builder: `{inventory.get('canonical_reference', {}).get('neo4j_plan_builder', '')}`",
                f"- neo4j_executor: `{inventory.get('canonical_reference', {}).get('neo4j_executor', '')}`",
                f"- neo4j_validator: `{inventory.get('canonical_reference', {}).get('neo4j_validator', '')}`",
                f"- api_alias_file: `{inventory.get('canonical_reference', {}).get('api_alias_file', '')}`",
                "",
                "## Disease Prefixes",
                *[f"- {k}: `{v}`" for k, v in PREFIX_EXPECTED.items()],
            ],
        )

    per_disease: dict[str, Any] = {}
    if args.status_only:
        inferred_connectivity: dict[str, Any] = {}
        for d in DISEASES:
            val = load_json(outputs_dir / f"{d.lower()}_neo4j_validation_report.json")
            if not val:
                continue
            status = safe_str(val.get("neo4j_connectivity_status"))
            reason = safe_str(val.get("neo4j_connectivity_reason"))
            if status:
                inferred_connectivity = {"status": status, "reason": reason or "from_existing_validation_report"}
                break
        neo_connectivity = inferred_connectivity or check_neo4j_connectivity()
    else:
        neo_connectivity = check_neo4j_connectivity()

    for disease in DISEASES:
        if args.status_only:
            per_disease[disease] = build_status_from_existing_reports(
                disease=disease,
                outputs_dir=outputs_dir,
                neo_connectivity=neo_connectivity,
                project_root=project_root,
            )
            continue

        slug = disease.lower()
        cfg_rel = CONFIG_BY_DISEASE[disease]
        cfg_abs = project_root / cfg_rel

        run_log: dict[str, Any] = {"disease": disease, "config": str(cfg_abs), "commands": {}}

        dry_run_cmd = [
            py,
            str(project_root / "scripts" / "load" / "run_disease_execute_pipeline.py"),
            "--project-root",
            str(project_root),
            "--disease",
            disease,
            "--config",
            str(cfg_abs),
            "--dry-run",
        ]
        run_log["commands"]["dry_run"] = run_cmd(dry_run_cmd, project_root)

        dry_validation = validate_dry_run(disease, outputs_dir)
        run_log["dry_run_validation"] = dry_validation
        safe_for_postgres = dry_validation.get("status") == "PASS"

        if safe_for_postgres:
            pg_exec_cmd = [
                py,
                str(project_root / "scripts" / "load" / "run_disease_execute_pipeline.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(cfg_abs),
                "--execute-postgres",
            ]
            run_log["commands"]["postgres_execute"] = run_cmd(pg_exec_cmd, project_root)
        else:
            run_log["commands"]["postgres_execute"] = {"skipped": True, "reason": "dry_run_validation_failed"}

        pg_validate_cmd = [
            py,
            str(project_root / "scripts" / "load" / "validate_disease_postgres_load_result.py"),
            "--project-root",
            str(project_root),
            "--disease",
            disease,
            "--config",
            str(cfg_abs),
            "--plan-json",
            str(outputs_dir / f"{slug}_postgres_load_plan_from_real_inspection.json"),
            "--execute-report-json",
            str(outputs_dir / f"{slug}_postgres_execute_report.json"),
        ]
        run_log["commands"]["postgres_validate"] = run_cmd(pg_validate_cmd, project_root)
        pg_validation = load_json(outputs_dir / f"{slug}_postgres_load_validation_report.json")
        pg_status = safe_str(pg_validation.get("postgres_validation_status"))

        neo_plan_cmd = [
            py,
            str(project_root / "scripts" / "load" / "build_disease_neo4j_write_plan.py"),
            "--project-root",
            str(project_root),
            "--disease",
            disease,
            "--config",
            str(cfg_abs),
            "--postgres-validation-json",
            str(outputs_dir / f"{slug}_postgres_load_validation_report.json"),
        ]
        run_log["commands"]["neo4j_plan_preview"] = run_cmd(neo_plan_cmd, project_root)
        neo_plan = load_json(outputs_dir / f"{slug}_neo4j_write_plan_preview.json")
        neo_plan_status = safe_str(neo_plan.get("write_plan_status"))

        neo_eligible = (
            pg_status in PASS_SET
            and safe_str(neo_connectivity.get("status")) == "PASS"
            and neo_plan_status in PASS_SET
        )

        if neo_eligible:
            neo_exec_cmd = [
                py,
                str(project_root / "scripts" / "load" / "execute_disease_neo4j_from_write_plan.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(cfg_abs),
                "--write-plan-json",
                str(outputs_dir / f"{slug}_neo4j_write_plan_preview.json"),
            ]
            run_log["commands"]["neo4j_execute"] = run_cmd(neo_exec_cmd, project_root)

            neo_val_cmd = [
                py,
                str(project_root / "scripts" / "load" / "validate_disease_neo4j_load_result.py"),
                "--project-root",
                str(project_root),
                "--disease",
                disease,
                "--config",
                str(cfg_abs),
                "--write-plan-json",
                str(outputs_dir / f"{slug}_neo4j_write_plan_preview.json"),
            ]
            run_log["commands"]["neo4j_validate"] = run_cmd(neo_val_cmd, project_root)
        else:
            reason_parts = []
            if pg_status not in PASS_SET:
                reason_parts.append(f"postgres_validation_not_pass:{pg_status}")
            if safe_str(neo_connectivity.get("status")) != "PASS":
                reason_parts.append(f"neo4j_connectivity_not_pass:{safe_str(neo_connectivity.get('reason'))}")
            if neo_plan_status not in PASS_SET:
                reason_parts.append(f"neo4j_write_plan_not_pass:{neo_plan_status}")
            block_reason = ";".join(reason_parts) if reason_parts else "neo4j_execution_blocked_by_guardrail"
            write_neo4j_blocked_report(
                project_root=project_root,
                disease=disease,
                reason=block_reason,
                connectivity=neo_connectivity,
                write_plan_status=neo_plan_status,
                postgres_validation_status=pg_status,
            )
            run_log["commands"]["neo4j_execute"] = {"skipped": True, "reason": block_reason}
            run_log["commands"]["neo4j_validate"] = {"generated_blocked_report": True}

        pipeline = load_json(outputs_dir / f"{slug}_execute_pipeline_report.json")
        pg_exec = load_json(outputs_dir / f"{slug}_postgres_execute_report.json")
        neo_val = load_json(outputs_dir / f"{slug}_neo4j_validation_report.json")
        per_disease[disease] = {
            "dry_run_validation": dry_validation,
            "safe_for_postgres_execute": safe_for_postgres,
            "postgres_validation_status": pg_status,
            "postgres_execute_status": safe_str(pg_exec.get("postgres_execute_status")),
            "neo4j_write_plan_status": neo_plan_status,
            "neo4j_validation_status": safe_str(neo_val.get("neo4j_validation_status")),
            "pipeline_overall_status": safe_str(pipeline.get("overall_status")),
            "reports": {
                "postgres_plan_json": str(outputs_dir / f"{slug}_postgres_load_plan_from_real_inspection.json"),
                "execute_pipeline_json": str(outputs_dir / f"{slug}_execute_pipeline_report.json"),
                "postgres_validation_json": str(outputs_dir / f"{slug}_postgres_load_validation_report.json"),
                "neo4j_write_plan_json": str(outputs_dir / f"{slug}_neo4j_write_plan_preview.json"),
                "neo4j_validation_json": str(outputs_dir / f"{slug}_neo4j_validation_report.json"),
            },
            "command_results": run_log["commands"],
        }

    final_payload = {
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "neo4j_connectivity": neo_connectivity,
        "diseases": per_disease,
        "summary": {
            "disease_count": len(per_disease),
            "postgres_execute_attempted_count": len([d for d in per_disease.values() if d.get("safe_for_postgres_execute")]),
            "postgres_validation_pass_count": len([d for d in per_disease.values() if safe_str(d.get("postgres_validation_status")) in PASS_SET]),
            "neo4j_validation_pass_count": len([d for d in per_disease.values() if safe_str(d.get("neo4j_validation_status")) in PASS_SET]),
        },
    }
    write_json(outputs_dir / "multi_cancer_barc_standard_final_status.json", final_payload)

    md_lines = [
        "# Multi-Cancer BRAC Standard Final Status",
        "",
        f"- generated_at: `{final_payload.get('generated_at')}`",
        f"- neo4j_connectivity_status: `{safe_str(neo_connectivity.get('status'))}`",
        f"- neo4j_connectivity_reason: `{safe_str(neo_connectivity.get('reason'))}`",
        "",
        "## Disease Status",
    ]
    for disease in DISEASES:
        row = per_disease.get(disease, {})
        md_lines.append(f"### {disease}")
        md_lines.append(f"- dry_run_validation: `{safe_str(row.get('dry_run_validation', {}).get('status'))}`")
        md_lines.append(f"- safe_for_postgres_execute: `{str(bool(row.get('safe_for_postgres_execute'))).lower()}`")
        if disease == "COAD":
            md_lines.append(f"- postgres_status: `{safe_str(row.get('postgres_status'))}`")
            md_lines.append(f"- postgres_execute: `{safe_str(row.get('postgres_execute'))}`")
            md_lines.append(f"- neo4j_status: `{safe_str(row.get('neo4j_status'))}`")
            md_lines.append(f"- restart_generic_detector_warning: `{safe_str(row.get('restart_generic_detector_warning'))}`")
            md_lines.append(f"- restart_generic_detector_warning_explanation: `{safe_str(row.get('restart_generic_detector_warning_explanation'))}`")
        md_lines.append(f"- postgres_execute_status: `{safe_str(row.get('postgres_execute_status'))}`")
        md_lines.append(f"- postgres_validation_status: `{safe_str(row.get('postgres_validation_status'))}`")
        md_lines.append(f"- neo4j_write_plan_status: `{safe_str(row.get('neo4j_write_plan_status'))}`")
        md_lines.append(f"- neo4j_validation_status: `{safe_str(row.get('neo4j_validation_status'))}`")
        if disease == "COAD":
            row_counts = row.get("postgres_completed_row_counts", {})
            if isinstance(row_counts, dict) and row_counts:
                md_lines.append("- postgres_completed_row_counts:")
                for key in sorted(row_counts):
                    md_lines.append(f"  - {key}: `{row_counts.get(key)}`")
        md_lines.append("")
    write_md(docs_dir / "multi_cancer_barc_standard_final_status.md", md_lines)

    print("status=PASS")
    print(f"inventory_json={outputs_dir / 'multi_cancer_restart_inventory_report.json'}")
    print(f"final_status_json={outputs_dir / 'multi_cancer_barc_standard_final_status.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
