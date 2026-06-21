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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def normalize_path_for_compare(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve())))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate disease Neo4j load result.")
    p.add_argument("--project-root", required=True)
    p.add_argument("--disease", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--write-plan-json", required=True)
    p.add_argument("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    return p.parse_args()


def resolve_path(project_root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p.resolve()
    return (project_root / p).resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("config root must be mapping")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json root must be mapping")
    return payload


def choose_password() -> str:
    p1 = safe_str(os.getenv("NEO4J_PASSWORD"))
    if p1:
        return p1
    return safe_str(os.getenv("NEO4J_PASSWORD_RUNTIME"))


def main() -> None:
    args = parse_args()
    disease = safe_str(args.disease).upper()
    requested_root = Path(args.project_root)
    if not requested_root.is_absolute():
        requested_root = Path.cwd() / requested_root

    expected_root = normalize_path_for_compare(CANONICAL_PROJECT_ROOT)
    resolved_root = normalize_path_for_compare(requested_root)
    project_root_match = resolved_root == expected_root
    root_status = "PASS" if project_root_match else "BLOCKED_WRONG_PROJECT_ROOT"
    one_drive_output_blocked = "onedrive" in resolved_root.lower()

    project_root = CANONICAL_PROJECT_ROOT
    outputs_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    out_json = outputs_dir / f"{disease.lower()}_neo4j_validation_report.json"
    out_md = docs_dir / f"{disease.lower()}_neo4j_validation_report.md"

    _ = load_yaml(resolve_path(project_root, args.config))
    write_plan = load_json(resolve_path(project_root, args.write_plan_json))
    exec_report_path = outputs_dir / f"{disease.lower()}_neo4j_execute_report.json"

    errors: list[str] = []
    warnings: list[str] = []
    if not project_root_match:
        errors.append("BLOCKED_WRONG_PROJECT_ROOT")
    if not exec_report_path.exists():
        errors.append(f"missing_neo4j_execute_report:{exec_report_path}")
        exec_report = {}
    else:
        exec_report = load_json(exec_report_path)

    execute_performed = bool(exec_report.get("execute_performed"))
    if not execute_performed:
        errors.append("neo4j_execute_not_performed")

    neo4j_uri = safe_str(os.getenv("NEO4J_URI"))
    neo4j_user = safe_str(os.getenv("NEO4J_USER"))
    neo4j_password = choose_password()
    neo4j_env_presence = {
        "NEO4J_URI": bool(neo4j_uri),
        "NEO4J_USER": bool(neo4j_user),
        "NEO4J_PASSWORD": bool(safe_str(os.getenv("NEO4J_PASSWORD"))),
        "NEO4J_PASSWORD_RUNTIME": bool(safe_str(os.getenv("NEO4J_PASSWORD_RUNTIME"))),
    }
    if (not neo4j_uri) or (not neo4j_user) or (not neo4j_password):
        errors.append("missing_runtime_neo4j_env_vars")

    node_counts = {k: 0 for k in write_plan.get("planned_node_counts", {}).keys()} if isinstance(write_plan.get("planned_node_counts"), dict) else {}
    rel_counts = {k: 0 for k in write_plan.get("planned_relationship_counts", {}).keys()} if isinstance(write_plan.get("planned_relationship_counts"), dict) else {}
    cross_disease_mismatch_count = 0
    duplicate_risk_count = 0

    if not errors:
        try:
            from neo4j import GraphDatabase  # type: ignore

            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            run_id = safe_str(exec_report.get("run_id"))
            with driver.session(database=args.neo4j_database) as session:
                node_counts["Disease"] = int(
                    session.run("MATCH (d:Disease {code:$d}) RETURN count(d) AS c", d=disease).single()["c"]
                )
                node_counts["DrugCandidate"] = int(
                    session.run("MATCH (n:DrugCandidate {disease:$d}) RETURN count(n) AS c", d=disease).single()["c"]
                )
                node_counts["CandidateScore"] = int(
                    session.run("MATCH (n:CandidateScore {disease:$d}) RETURN count(n) AS c", d=disease).single()["c"]
                )
                node_counts["TierEvidence"] = int(
                    session.run("MATCH (n:TierEvidence {disease:$d}) RETURN count(n) AS c", d=disease).single()["c"]
                )
                node_counts["SourceArtifact"] = int(
                    session.run("MATCH (n:SourceArtifact) RETURN count(n) AS c").single()["c"]
                )
                node_counts["Run"] = int(session.run("MATCH (n:Run {run_id:$r}) RETURN count(n) AS c", r=run_id).single()["c"]) if run_id else 0

                rel_counts["CANDIDATE_FOR"] = int(
                    session.run(
                        "MATCH (:DrugCandidate {disease:$d})-[r:CANDIDATE_FOR]->(:Disease {code:$d}) RETURN count(r) AS c",
                        d=disease,
                    ).single()["c"]
                )
                rel_counts["HAS_CANDIDATE_SCORE"] = int(
                    session.run(
                        "MATCH (:DrugCandidate {disease:$d})-[r:HAS_CANDIDATE_SCORE]->(:CandidateScore {disease:$d}) RETURN count(r) AS c",
                        d=disease,
                    ).single()["c"]
                )
                rel_counts["HAS_TIER"] = int(
                    session.run(
                        "MATCH (:DrugCandidate {disease:$d})-[r:HAS_TIER]->(:TierEvidence {disease:$d}) RETURN count(r) AS c",
                        d=disease,
                    ).single()["c"]
                )
                rel_counts["DERIVED_FROM_SOURCE"] = int(
                    session.run("MATCH ()-[r:DERIVED_FROM_SOURCE]->(:SourceArtifact) RETURN count(r) AS c").single()["c"]
                )
                rel_counts["PRODUCED_EVIDENCE"] = int(
                    session.run(
                        "MATCH (:Run {run_id:$r})-[rel:PRODUCED_EVIDENCE]->() RETURN count(rel) AS c",
                        r=run_id,
                    ).single()["c"]
                ) if run_id else 0
                rel_counts["AUDITS_LOAD_FOR"] = int(
                    session.run(
                        "MATCH (:Run {run_id:$r})-[rel:AUDITS_LOAD_FOR]->(:Disease {code:$d}) RETURN count(rel) AS c",
                        r=run_id,
                        d=disease,
                    ).single()["c"]
                ) if run_id else 0

                cross_disease_mismatch_count = int(
                    session.run(
                        "MATCH (:Run {run_id:$r})-[:PRODUCED_EVIDENCE]->(n) "
                        "WHERE coalesce(n.disease, '') <> $d RETURN count(n) AS c",
                        r=run_id,
                        d=disease,
                    ).single()["c"]
                ) if run_id else 0

                duplicate_risk_count = int(
                    session.run(
                        "MATCH (:Run {run_id:$r})-[:PRODUCED_EVIDENCE]->(n:CandidateScore {disease:$d}) "
                        "WITH n.evidence_key AS k, count(*) AS c WHERE c > 1 RETURN count(k) AS c",
                        r=run_id,
                        d=disease,
                    ).single()["c"]
                ) if run_id else 0
            driver.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"neo4j_validation_query_error:{exc}")

    if node_counts.get("Disease", 0) <= 0:
        errors.append("missing_Disease")
    if node_counts.get("DrugCandidate", 0) <= 0:
        errors.append("missing_DrugCandidate")
    if cross_disease_mismatch_count > 0:
        errors.append("cross_disease_write_detected")
    if duplicate_risk_count > 0:
        warnings.append("potential_duplicate_evidence_keys_detected")

    status = "PASS"
    if errors:
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
        "write_plan_json": str(resolve_path(project_root, args.write_plan_json)),
        "execute_report_json": str(exec_report_path),
        "neo4j_env_presence": neo4j_env_presence,
        "execute_performed": execute_performed,
        "neo4j_validation_status": status,
        "node_counts": node_counts,
        "relationship_counts": rel_counts,
        "guardrail_checks": {
            "cross_disease_mismatch_count": cross_disease_mismatch_count,
            "duplicate_risk_count": duplicate_risk_count,
        },
        "warnings": warnings,
        "errors": errors,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {disease} Neo4j Validation Report",
        "",
        f"- neo4j_validation_status: `{status}`",
        f"- execute_performed: `{str(execute_performed).lower()}`",
        f"- output_path_guardrail_status: `{root_status}`",
        "",
        "## Node Counts",
    ]
    for k, v in node_counts.items():
        lines.append(f"- {k}: {int(v or 0)}")
    lines.extend(["", "## Relationship Counts"])
    for k, v in rel_counts.items():
        lines.append(f"- {k}: {int(v or 0)}")
    lines.extend(["", "## Guardrail Checks"])
    lines.append(f"- cross_disease_mismatch_count: {cross_disease_mismatch_count}")
    lines.append(f"- duplicate_risk_count: {duplicate_risk_count}")
    lines.extend(["", "## Errors"])
    if errors:
        lines.extend([f"- {x}" for x in errors])
    else:
        lines.append("- (none)")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"disease={disease}")
    print(f"neo4j_validation_status={status}")
    print(f"json_output={out_json}")
    print(f"markdown_output={out_md}")


if __name__ == "__main__":
    main()
