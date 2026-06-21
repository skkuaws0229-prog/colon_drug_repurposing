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


CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
BLOCKED_DECISIONS = {"NEEDS_REVIEW", "DO_NOT_LOAD_EXCLUDED", "BLOCKED", "MISSING", "LOCAL_SYNC_NEEDED"}

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


def normalize_path_for_compare(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve())))


def normalize_path_no_resolve(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path))))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build disease Neo4j write-plan preview from validated PostgreSQL results.")
    p.add_argument("--project-root", required=True)
    p.add_argument("--disease", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--postgres-validation-json", required=True)
    return p.parse_args()


def resolve_path(project_root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return Path(os.path.abspath(str(p)))
    return Path(os.path.abspath(str(project_root / p)))


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("config root must be mapping")
    return payload


def main() -> None:
    args = parse_args()
    requested_root = Path(args.project_root)
    if not requested_root.is_absolute():
        requested_root = Path.cwd() / requested_root

    expected_root = normalize_path_no_resolve(CANONICAL_PROJECT_ROOT)
    resolved_root = normalize_path_no_resolve(requested_root)
    one_drive_detected = (
        "onedrive" in resolved_root.lower()
        or r"\users\hjy10\onedrive" in resolved_root.lower()
    )
    project_root_match = (resolved_root == expected_root) and (not one_drive_detected)
    root_status = "PASS" if project_root_match else ("BLOCKED_ONEDRIVE_PROJECT_ROOT" if one_drive_detected else "BLOCKED_WRONG_PROJECT_ROOT")
    one_drive_output_blocked = True

    project_root = CANONICAL_PROJECT_ROOT
    outputs_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    disease = safe_str(args.disease).upper()
    out_json = outputs_dir / f"{disease.lower()}_neo4j_write_plan_preview.json"
    out_md = docs_dir / f"{disease.lower()}_neo4j_write_plan_preview.md"

    cfg_path = resolve_path(project_root, args.config)
    val_json_path = resolve_path(project_root, args.postgres_validation_json)
    pg_exec_json_path = outputs_dir / f"{disease.lower()}_postgres_execute_report.json"

    failures: list[str] = []
    warnings: list[str] = []

    if not project_root_match:
        failures.append("BLOCKED_WRONG_PROJECT_ROOT")

    cfg = load_yaml(cfg_path)
    cfg_disease = safe_str(cfg.get("disease", {}).get("code", "")).upper()
    if cfg_disease and cfg_disease != disease:
        failures.append(f"disease_mismatch_config:{cfg_disease}")

    if not val_json_path.exists():
        failures.append(f"missing_postgres_validation_report:{val_json_path}")
        val = {}
    else:
        val = json.loads(val_json_path.read_text(encoding="utf-8"))

    if not pg_exec_json_path.exists():
        failures.append(f"missing_postgres_execute_report:{pg_exec_json_path}")
        pg_exec = {}
    else:
        pg_exec = json.loads(pg_exec_json_path.read_text(encoding="utf-8"))

    pg_status = safe_str(val.get("postgres_validation_status"))
    if pg_status not in {"PASS", "PASS_WITH_WARNINGS"}:
        failures.append(f"postgres_validation_not_pass:{pg_status}")

    guard = val.get("guardrail_checks", {})
    excluded_viol = int(guard.get("excluded_artifact_load_violations", 0) or 0) if isinstance(guard, dict) else 0
    no_admet_viol = int(guard.get("no_admet_violations", 0) or 0) if isinstance(guard, dict) else 0
    if excluded_viol > 0:
        failures.append("excluded_artifact_load_violations_detected")
    if no_admet_viol > 0:
        failures.append("no_admet_violations_detected")
    if val.get("loaded_sources_not_in_approved_plan"):
        failures.append("loaded_sources_not_in_approved_plan")

    row_counts = val.get("row_counts_by_table", {}) if isinstance(val, dict) else {}
    if not isinstance(row_counts, dict):
        row_counts = {}
    tier_rows = int(row_counts.get("drug_candidate_tier", 0) or 0)
    final_rows = int(row_counts.get("final_candidate_result", 0) or 0)
    admet_rows = int(row_counts.get("admet_result", 0) or 0)
    ext_rows = int(row_counts.get("external_validation_result", 0) or 0)
    model_rows = int(row_counts.get("model_metric", 0) or 0)
    model_detail_rows = int(row_counts.get("model_metric_detailed", 0) or 0)
    ens_rows = int(row_counts.get("ensemble_metric", 0) or 0)
    src_rows = int(row_counts.get("source_artifact", 0) or 0)
    audit_rows = int(row_counts.get("load_audit", 0) or 0)
    run_rows = int(row_counts.get("run_manifest", 0) or 0)

    node_counts = {k: 0 for k in NODE_KEYS}
    rel_counts = {k: 0 for k in REL_KEYS}

    if tier_rows > 0:
        node_counts["Disease"] = 1
        node_counts["DrugCandidate"] = tier_rows
        node_counts["CandidateScore"] = tier_rows
        node_counts["TierEvidence"] = tier_rows
        rel_counts["CANDIDATE_FOR"] = tier_rows
        rel_counts["HAS_CANDIDATE_SCORE"] = tier_rows
        rel_counts["HAS_TIER"] = tier_rows

    if final_rows > 0:
        node_counts["FinalCandidateEvidence"] = final_rows
        rel_counts["SELECTED_AS_FINAL"] = final_rows
    else:
        warnings.append("no_real_data_for_FinalCandidateEvidence")

    if admet_rows > 0:
        node_counts["AdmetEvidence"] = admet_rows
        rel_counts["HAS_ADMET_PROFILE"] = admet_rows
    else:
        warnings.append("no_real_data_for_AdmetEvidence")

    if ext_rows > 0:
        node_counts["ExternalValidationEvidence"] = ext_rows
        rel_counts["VALIDATED_BY_EXTERNAL_DATA"] = ext_rows
        rel_counts["HAS_EXTERNAL_VALIDATION"] = ext_rows
    else:
        warnings.append("no_real_data_for_ExternalValidationEvidence")

    if model_rows > 0:
        node_counts["ModelEvidence"] = model_rows
        rel_counts["SUPPORTED_BY_MODEL"] = model_rows
    else:
        warnings.append("no_real_data_for_ModelEvidence")

    if model_detail_rows > 0:
        node_counts["ModelDetailEvidence"] = model_detail_rows
        rel_counts["HAS_DETAILED_MODEL_METRIC"] = model_detail_rows
    else:
        warnings.append("no_real_data_for_ModelDetailEvidence")

    if ens_rows > 0:
        node_counts["EnsembleEvidence"] = ens_rows
        rel_counts["SUPPORTED_BY_ENSEMBLE"] = ens_rows
    else:
        warnings.append("no_real_data_for_EnsembleEvidence")

    if src_rows > 0:
        node_counts["SourceArtifact"] = src_rows
    if audit_rows > 0:
        node_counts["LoadAuditEvidence"] = audit_rows
    else:
        warnings.append("no_real_data_for_LoadAuditEvidence")
    if run_rows > 0:
        node_counts["Run"] = run_rows
    else:
        warnings.append("no_real_data_for_Run")

    loaded_artifacts = []
    for r in pg_exec.get("artifact_results", []) if isinstance(pg_exec, dict) else []:
        if not isinstance(r, dict):
            continue
        if safe_str(r.get("status")) != "LOADED":
            continue
        loaded_artifacts.append(
            {
                "source_s3_uri": safe_str(r.get("source_s3_uri")),
                "target_table": safe_str(r.get("target_table")),
                "proposed_role": safe_str(r.get("proposed_role")),
                "decision": "APPROVED_FOR_POSTGRES_LOAD",
            }
        )

    for a in loaded_artifacts:
        if safe_str(a.get("decision")) in BLOCKED_DECISIONS:
            failures.append("blocked_decision_artifact_included")
            break
        s3 = safe_str(a.get("source_s3_uri")).lower()
        tgt = safe_str(a.get("target_table"))
        if "no_admet" in s3 and tgt in {"final_candidate_result", "admet_result", "run_manifest"}:
            failures.append("no_admet_guardrail_violation_in_source")
            break

    rel_counts["DERIVED_FROM_SOURCE"] = (
        node_counts["CandidateScore"]
        + node_counts["TierEvidence"]
        + node_counts["FinalCandidateEvidence"]
        + node_counts["AdmetEvidence"]
        + node_counts["ExternalValidationEvidence"]
        + node_counts["ModelEvidence"]
        + node_counts["ModelDetailEvidence"]
        + node_counts["EnsembleEvidence"]
    )
    rel_counts["PRODUCED_EVIDENCE"] = (
        node_counts["CandidateScore"]
        + node_counts["TierEvidence"]
        + node_counts["FinalCandidateEvidence"]
        + node_counts["AdmetEvidence"]
        + node_counts["ExternalValidationEvidence"]
        + node_counts["ModelEvidence"]
        + node_counts["ModelDetailEvidence"]
        + node_counts["EnsembleEvidence"]
    )
    rel_counts["AUDITS_LOAD_FOR"] = 1 if tier_rows > 0 else 0

    total_nodes = sum(node_counts.values())
    total_rels = sum(rel_counts.values())
    if total_nodes <= 0 or total_rels <= 0:
        failures.append("no_real_graph_data_planned")

    status = "PASS"
    if failures:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"

    payload = {
        "generated_at": now_iso(),
        "disease": disease,
        "requested_project_root_arg": safe_str(args.project_root),
        "cwd": str(Path.cwd()),
        "expected_project_root": expected_root,
        "resolved_project_root": resolved_root,
        "project_root_match": project_root_match,
        "resolved_docs_dir": str(docs_dir),
        "resolved_outputs_dir": str(outputs_dir),
        "one_drive_output_blocked": one_drive_output_blocked,
        "output_path_guardrail_status": root_status,
        "postgres_validation_status": pg_status,
        "write_plan_status": status,
        "postgres_validation_json": str(val_json_path),
        "postgres_execute_json": str(pg_exec_json_path),
        "approved_artifact_count_from_plan": int(pg_exec.get("approved_artifact_count_from_plan", pg_exec.get("approved_artifact_count", 0)) or 0),
        "loaded_artifact_count": int(pg_exec.get("loaded_artifact_count", 0) or 0),
        "guardrail_checks": {
            "excluded_artifact_load_violations": excluded_viol,
            "no_admet_violations": no_admet_viol,
            "loaded_sources_not_in_approved_plan_count": len(val.get("loaded_sources_not_in_approved_plan", []) if isinstance(val, dict) else []),
        },
        "loaded_artifacts": loaded_artifacts,
        "planned_node_counts": node_counts,
        "planned_relationship_counts": rel_counts,
        "total_planned_nodes": total_nodes,
        "total_planned_relationships": total_rels,
        "failures": failures,
        "warnings": warnings,
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {disease} Neo4j Write Plan Preview",
        "",
        f"- write_plan_status: `{status}`",
        f"- postgres_validation_status: `{pg_status}`",
        f"- project_root_match: `{str(project_root_match).lower()}`",
        f"- output_path_guardrail_status: `{root_status}`",
        f"- total_planned_nodes: `{total_nodes}`",
        f"- total_planned_relationships: `{total_rels}`",
        "",
        "## Planned Node Counts",
    ]
    for k in NODE_KEYS:
        lines.append(f"- {k}: {int(node_counts.get(k, 0) or 0)}")
    lines.extend(["", "## Planned Relationship Counts"])
    for k in REL_KEYS:
        lines.append(f"- {k}: {int(rel_counts.get(k, 0) or 0)}")
    lines.extend(["", "## Failures"])
    if failures:
        lines.extend([f"- {x}" for x in failures])
    else:
        lines.append("- (none)")
    lines.extend(["", "## Warnings"])
    if warnings:
        lines.extend([f"- {x}" for x in warnings])
    else:
        lines.append("- (none)")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"disease={disease}")
    print(f"write_plan_status={status}")
    print(f"total_planned_nodes={total_nodes}")
    print(f"total_planned_relationships={total_rels}")
    print(f"json_output={out_json}")
    print(f"markdown_output={out_md}")


if __name__ == "__main__":
    main()
