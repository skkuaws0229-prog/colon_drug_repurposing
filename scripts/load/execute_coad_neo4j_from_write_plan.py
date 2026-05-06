#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BLOCKED_DECISIONS = {
    "NEEDS_REVIEW",
    "DO_NOT_LOAD_EXCLUDED",
    "BLOCKED",
    "MISSING",
    "LOCAL_SYNC_NEEDED",
}
NO_ADMET_BLOCK_TABLES = {"final_candidate_result", "admet_result", "run_manifest"}
APPROVED_ROLE_TABLE_PAIRS = {
    ("candidate_tiered", "drug_candidate_tier"),
    ("final_after_admet", "final_candidate_result"),
    ("external_validation_top30", "external_validation_result"),
    ("admet_top30", "admet_result"),
}
NON_COMPACT_TOKENS = [
    "/raw/",
    "/curated/",
    "/reference/",
    "/glue/",
    "/temp/",
    "/debug/",
    "/intermediate/",
    "/full/",
    "_raw",
    "_curated",
    "_reference",
    "_glue",
    "_temp",
    "_debug",
    "_intermediate",
]
DRUG_KEY_CANDIDATES = [
    "drug_id",
    "drug_name",
    "drug",
    "compound_id",
    "compound_name",
    "chembl_id",
    "drug_chembl_id",
    "name",
]
DRUG_KEY_EXTENDED = DRUG_KEY_CANDIDATES + ["canonical_drug_id", "DRUG_NAME", "drug_name_norm"]
S3_PREFIX_KEY = "20260408_new_pre_project_biso/202604_Final_data/Colon/"


@dataclass
class RuntimePaths:
    project_root: Path
    output_dir: Path
    docs_dir: Path
    local_coad_dir: Path
    plan_json: Path
    plan_md: Path
    stage4_summary_md: Path
    postgres_execute_json: Path
    execute_report_json: Path
    execute_report_md: Path
    validation_report_json: Path
    validation_report_md: Path


@dataclass
class PlanItem:
    role: str
    target_table: str
    source_file: str
    source_s3_uri: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_project_markers(path: Path) -> bool:
    return (path / "scripts").is_dir() and (path / "docs").is_dir() and (path / "outputs").is_dir()


def find_project_root() -> Path:
    cwd = Path.cwd()
    if has_project_markers(cwd):
        return cwd
    script_root = Path(__file__).resolve().parents[2]
    if has_project_markers(script_root):
        return script_root
    return cwd


def runtime_paths(project_root: Path) -> RuntimePaths:
    output_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    return RuntimePaths(
        project_root=project_root,
        output_dir=output_dir,
        docs_dir=docs_dir,
        local_coad_dir=project_root / "data_cache" / "final_data" / "COAD",
        plan_json=output_dir / "coad_neo4j_write_plan_preview.json",
        plan_md=docs_dir / "coad_neo4j_write_plan_preview.md",
        stage4_summary_md=docs_dir / "coad_stage4_postgres_neo4j_pre_execute_summary.md",
        postgres_execute_json=output_dir / "coad_postgres_execute_report.json",
        execute_report_json=output_dir / "coad_neo4j_execute_report.json",
        execute_report_md=docs_dir / "coad_neo4j_execute_report.md",
        validation_report_json=output_dir / "coad_neo4j_validation_report.json",
        validation_report_md=docs_dir / "coad_neo4j_validation_report.md",
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Execute COAD Neo4j load from approved write-plan.")
    p.add_argument("--project-root", default="")
    p.add_argument("--disease", default="COAD")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    p.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    p.add_argument("--neo4j-password-env", default="NEO4J_PASSWORD")
    p.add_argument("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    return p.parse_args()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def upper(v: Any) -> str:
    return safe_str(v).upper()


def normalize_name(v: str) -> str:
    return " ".join(v.strip().lower().split())


def parse_number(v: str) -> int | float | str:
    s = safe_str(v)
    if not s:
        return s
    if re.fullmatch(r"[+-]?\d+", s):
        try:
            return int(s)
        except Exception:
            return s
    if re.fullmatch(r"[+-]?\d*\.\d+(e[+-]?\d+)?", s.lower()) or re.fullmatch(r"[+-]?\d+e[+-]?\d+", s.lower()):
        try:
            return float(s)
        except Exception:
            return s
    return s


def bool_from_text(v: str) -> bool | None:
    s = safe_str(v).lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None


def sanitize_key(k: str) -> str:
    out = re.sub(r"[^0-9A-Za-z_]", "_", k.strip().lower())
    out = re.sub(r"_+", "_", out).strip("_")
    if not out:
        out = "field"
    if out[0].isdigit():
        out = f"f_{out}"
    return out[:80]


def scalar_value(v: Any) -> Any:
    s = safe_str(v)
    if s == "":
        return None
    b = bool_from_text(s)
    if b is not None:
        return b
    n = parse_number(s)
    if isinstance(n, str):
        if len(n) > 4000:
            return n[:4000]
    return n


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16", "cp949"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise ValueError(f"failed to parse json: {path}")


def extract_plan_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("plan_rows")
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def load_env_local(paths: RuntimePaths) -> None:
    env_path = paths.project_root / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


def print_summary(
    *,
    paths: RuntimePaths,
    overall_status: str,
    execute_report: dict[str, Any] | None = None,
    validation_report: dict[str, Any] | None = None,
) -> None:
    print(f"project_root={paths.project_root}")
    print(f"execute_report={paths.execute_report_json}")
    print(f"validation_report={paths.validation_report_json}")
    print(f"execute_markdown={paths.execute_report_md}")
    print(f"validation_markdown={paths.validation_report_md}")
    if execute_report is not None:
        print(f"execute_performed={str(execute_report.get('execute_performed', False)).lower()}")
        print(f"loaded_rows_by_role={json.dumps(execute_report.get('loaded_rows_by_role', {}), ensure_ascii=False)}")
        print(f"skipped_rows_by_role={json.dumps(execute_report.get('skipped_rows_by_role', {}), ensure_ascii=False)}")
        print(f"node_counts={json.dumps(execute_report.get('node_counts', {}), ensure_ascii=False)}")
        print(f"relationship_counts={json.dumps(execute_report.get('relationship_counts', {}), ensure_ascii=False)}")
    if validation_report is not None:
        print(f"skipped_rows={len(validation_report.get('skipped_rows', []))}")
    print(f"overall_status={overall_status}")


def write_reports(paths: RuntimePaths, execute_report: dict[str, Any], validation_report: dict[str, Any]) -> None:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.docs_dir.mkdir(parents=True, exist_ok=True)

    paths.execute_report_json.write_text(json.dumps(execute_report, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.validation_report_json.write_text(json.dumps(validation_report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_exec = [
        "# COAD Neo4j Execute Report",
        "",
        f"- generated_at: {execute_report.get('generated_at')}",
        f"- disease: {execute_report.get('disease')}",
        f"- execute_requested: {str(execute_report.get('execute_requested')).lower()}",
        f"- execute_performed: {str(execute_report.get('execute_performed')).lower()}",
        f"- overall_status: {execute_report.get('overall_status')}",
        f"- reason: {execute_report.get('reason', '')}",
        "",
        "## Loaded Rows By Role",
    ]
    for k, v in execute_report.get("loaded_rows_by_role", {}).items():
        md_exec.append(f"- {k}: {v}")
    md_exec.extend(["", "## Skipped Rows By Role"])
    for k, v in execute_report.get("skipped_rows_by_role", {}).items():
        md_exec.append(f"- {k}: {v}")
    md_exec.extend(["", "## Source Artifacts Used"])
    for x in execute_report.get("source_artifacts_used", []):
        md_exec.append(f"- {x}")
    md_exec.extend(["", "## Skipped Rows"])
    for s in execute_report.get("skipped_rows", []):
        md_exec.append(f"- role={s.get('role')} source_file={s.get('source_file')} row_index={s.get('row_index')} reason={s.get('reason')}")
    paths.execute_report_md.write_text("\n".join(md_exec) + "\n", encoding="utf-8")

    md_val = [
        "# COAD Neo4j Validation Report",
        "",
        f"- generated_at: {validation_report.get('generated_at')}",
        f"- disease: {validation_report.get('disease')}",
        f"- execute_requested: {str(validation_report.get('execute_requested')).lower()}",
        f"- execute_performed: {str(validation_report.get('execute_performed')).lower()}",
        f"- overall_status: {validation_report.get('overall_status')}",
        "",
        "## Node Counts",
    ]
    for k, v in validation_report.get("node_counts", {}).items():
        md_val.append(f"- {k}: {v}")
    md_val.extend(["", "## Relationship Counts"])
    for k, v in validation_report.get("relationship_counts", {}).items():
        md_val.append(f"- {k}: {v}")
    md_val.extend(["", "## Guardrail Checks"])
    for k, v in validation_report.get("guardrail_checks", {}).items():
        md_val.append(f"- {k}: {v}")
    md_val.extend(["", "## Source Artifacts Used"])
    for x in validation_report.get("source_artifacts_used", []):
        md_val.append(f"- {x}")
    md_val.extend(["", "## Skipped Rows"])
    for s in validation_report.get("skipped_rows", []):
        md_val.append(f"- role={s.get('role')} source_file={s.get('source_file')} row_index={s.get('row_index')} reason={s.get('reason')}")
    paths.validation_report_md.write_text("\n".join(md_val) + "\n", encoding="utf-8")


def failure_report(
    *,
    paths: RuntimePaths,
    reason: str,
    guardrail_checks: dict[str, Any],
    source_artifacts_used: list[str] | None = None,
    skipped_rows: list[dict[str, Any]] | None = None,
    loaded_rows_by_role: dict[str, int] | None = None,
    skipped_rows_by_role: dict[str, int] | None = None,
    error_detail: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    execute_report = {
        "generated_at": now_iso(),
        "disease": "COAD",
        "execute_requested": True,
        "execute_performed": False,
        "reason": reason,
        "error_detail": error_detail,
        "guardrail_checks": guardrail_checks,
        "source_artifacts_used": source_artifacts_used or [],
        "node_counts": {},
        "relationship_counts": {},
        "loaded_rows_by_role": loaded_rows_by_role or {},
        "skipped_rows_by_role": skipped_rows_by_role or {},
        "skipped_rows": skipped_rows or [],
        "overall_status": "FAIL",
    }
    validation_report = {
        "generated_at": now_iso(),
        "disease": "COAD",
        "execute_requested": True,
        "execute_performed": False,
        "reason": reason,
        "error_detail": error_detail,
        "guardrail_checks": guardrail_checks,
        "source_artifacts_used": source_artifacts_used or [],
        "node_counts": {},
        "relationship_counts": {},
        "loaded_rows_by_role": loaded_rows_by_role or {},
        "skipped_rows_by_role": skipped_rows_by_role or {},
        "skipped_rows": skipped_rows or [],
        "overall_status": "FAIL",
    }
    write_reports(paths, execute_report, validation_report)
    return execute_report, validation_report


def is_non_compact(path_or_uri: str) -> bool:
    t = safe_str(path_or_uri).lower().replace("\\", "/")
    return any(tok in t for tok in NON_COMPACT_TOKENS)


def to_plan_item(row: dict[str, Any]) -> PlanItem:
    return PlanItem(
        role=safe_str(row.get("source_file_role")),
        target_table=safe_str(row.get("target_table")),
        source_file=safe_str(row.get("source_file")),
        source_s3_uri=safe_str(row.get("source_s3_uri")),
    )


def resolve_local_path(paths: RuntimePaths, item: PlanItem) -> Path:
    key = item.source_s3_uri.replace("s3://say2-4team/", "", 1)
    if S3_PREFIX_KEY in key:
        rel = key.split(S3_PREFIX_KEY, 1)[1].replace("/", os.sep)
        p = paths.local_coad_dir / rel
        if p.exists():
            return p
    p2 = paths.local_coad_dir / item.source_file
    if p2.exists():
        return p2
    matches = list(paths.local_coad_dir.rglob(item.source_file))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return matches[0]
    raise FileNotFoundError(f"local source file not found for role={item.role}, file={item.source_file}")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def detect_drug_key(row: dict[str, Any]) -> tuple[str, str, str]:
    # Returns (drug_key, drug_id, drug_name) using allowed key aliases only.
    normalized: dict[str, Any] = {sanitize_key(str(k)): v for k, v in row.items()}
    drug_id = ""
    drug_name = ""

    id_aliases = {"drug_id", "compound_id", "chembl_id", "drug_chembl_id"}
    name_aliases = {"drug_name", "drug", "compound_name", "name"}
    for alias in id_aliases:
        if alias in normalized and safe_str(normalized[alias]):
            drug_id = safe_str(normalized[alias])
            break
    for alias in name_aliases:
        if alias in normalized and safe_str(normalized[alias]):
            drug_name = safe_str(normalized[alias])
            break

    if not drug_id and not drug_name:
        return "", "", ""
    if drug_id:
        return f"id:{drug_id}", drug_id, drug_name
    return f"name:{normalize_name(drug_name)}", drug_id, drug_name


def row_props(row: dict[str, Any], *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for k, v in row.items():
        key = sanitize_key(k)
        val = scalar_value(v)
        if val is None:
            continue
        props[key] = val
    if extra:
        for k, v in extra.items():
            val = scalar_value(v)
            if val is None:
                continue
            props[sanitize_key(k)] = val
    return props


def prepare_guardrail_checks(
    plan_payload: dict[str, Any],
    postgres_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "postgres_status_in_plan": upper(plan_payload.get("postgres_status")),
        "postgres_status_in_execute_report": upper(postgres_payload.get("status")),
        "neo4j_status_in_plan": upper(plan_payload.get("neo4j_status")),
        "blocked_decisions_rejected": True,
        "no_admet_guardrail": True,
        "approved_roles_only": True,
        "non_compact_artifacts_blocked": True,
    }


def validate_guardrails(
    *,
    paths: RuntimePaths,
    plan_payload: dict[str, Any],
    postgres_payload: dict[str, Any],
    plan_md_text: str,
    stage4_md_text: str,
    plan_items: list[PlanItem],
    guardrail_checks: dict[str, Any],
) -> tuple[bool, str]:
    if upper(plan_payload.get("postgres_status")) != "POSTGRES_LOADED" or upper(postgres_payload.get("status")) != "POSTGRES_LOADED":
        return False, "POSTGRES_STATUS_NOT_LOADED"
    if upper(plan_payload.get("neo4j_status")) != "REACHABLE":
        return False, "NEO4J_NOT_REACHABLE_IN_PREVIEW"
    if "PostgreSQL status: `POSTGRES_LOADED`" not in plan_md_text or "COAD PostgreSQL is complete" not in stage4_md_text:
        return False, "CROSSCHECK_REPORT_MISMATCH"
    if len(plan_items) != 4:
        return False, "APPROVED_PLAN_ROW_COUNT_NOT_4"

    rows = extract_plan_rows(plan_payload)
    for r in rows:
        if upper(r.get("decision")) in BLOCKED_DECISIONS or upper(r.get("status")) in BLOCKED_DECISIONS:
            return False, "BLOCKED_DECISION_FOUND_IN_PLAN"

    role_pairs = {(p.role, p.target_table) for p in plan_items}
    if role_pairs != APPROVED_ROLE_TABLE_PAIRS:
        return False, "PLAN_ROWS_NOT_EXACT_APPROVED_SET"

    for item in plan_items:
        if "no_admet" in item.source_file.lower() and item.target_table in NO_ADMET_BLOCK_TABLES:
            return False, "NO_ADMET_GUARDRAIL_VIOLATION"
        if is_non_compact(item.source_s3_uri) or is_non_compact(item.source_file):
            return False, "NON_COMPACT_ARTIFACT_IN_PLAN"

    return True, ""


def run() -> int:
    args = parse_args()
    project_root = Path(args.project_root) if safe_str(args.project_root) else find_project_root()
    if not project_root.is_absolute():
        project_root = Path.cwd() / project_root
    paths = runtime_paths(project_root)
    load_env_local(paths)

    disease = upper(args.disease)
    if disease != "COAD":
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="ONLY_COAD_SUPPORTED",
            guardrail_checks={},
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    required_files = [paths.plan_json, paths.plan_md, paths.stage4_summary_md, paths.postgres_execute_json]
    for p in required_files:
        if not p.exists():
            execute_report, validation_report = failure_report(
                paths=paths,
                reason=f"REQUIRED_FILE_MISSING: {p}",
                guardrail_checks={},
            )
            print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
            return 2

    plan_payload = read_json(paths.plan_json)
    postgres_payload = read_json(paths.postgres_execute_json)
    plan_md_text = paths.plan_md.read_text(encoding="utf-8", errors="replace")
    stage4_md_text = paths.stage4_summary_md.read_text(encoding="utf-8", errors="replace")
    plan_items = [to_plan_item(r) for r in extract_plan_rows(plan_payload)]
    guardrail_checks = prepare_guardrail_checks(plan_payload, postgres_payload)

    ok, reason = validate_guardrails(
        paths=paths,
        plan_payload=plan_payload,
        postgres_payload=postgres_payload,
        plan_md_text=plan_md_text,
        stage4_md_text=stage4_md_text,
        plan_items=plan_items,
        guardrail_checks=guardrail_checks,
    )
    if not ok:
        execute_report, validation_report = failure_report(paths=paths, reason=reason, guardrail_checks=guardrail_checks)
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    if not args.execute:
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="EXECUTE_FLAG_NOT_SET",
            guardrail_checks=guardrail_checks,
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    password = os.getenv(args.neo4j_password_env, "")
    if not password:
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="NEO4J_PASSWORD_MISSING",
            guardrail_checks={**guardrail_checks, "neo4j_password_present": False},
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception:
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="NEO4J_DRIVER_NOT_AVAILABLE",
            guardrail_checks={**guardrail_checks, "neo4j_driver_available": False},
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    run_id = f"COAD_NEO4J_EXECUTE_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    source_artifacts_used: list[str] = []
    skipped_rows: list[dict[str, Any]] = []
    loaded_rows_by_role: dict[str, int] = {r: 0 for r, _ in APPROVED_ROLE_TABLE_PAIRS}
    skipped_rows_by_role: dict[str, int] = {r: 0 for r, _ in APPROVED_ROLE_TABLE_PAIRS}

    staged: list[dict[str, Any]] = []
    for item in plan_items:
        try:
            local_path = resolve_local_path(paths, item)
        except FileNotFoundError as exc:
            execute_report, validation_report = failure_report(
                paths=paths,
                reason="SOURCE_FILE_MISSING",
                guardrail_checks=guardrail_checks,
                source_artifacts_used=source_artifacts_used,
                skipped_rows=skipped_rows,
                loaded_rows_by_role=loaded_rows_by_role,
                skipped_rows_by_role=skipped_rows_by_role,
                error_detail=str(exc),
            )
            print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
            return 2
        source_artifacts_used.append(f"{item.role} | {item.target_table} | {local_path}")
        rows = read_csv_rows(local_path)
        for idx, row in enumerate(rows, start=1):
            drug_key, drug_id, drug_name = detect_drug_key(row)
            if item.role in {"candidate_tiered", "final_after_admet"} and not drug_key:
                skipped_rows.append(
                    {
                        "role": item.role,
                        "source_file": item.source_file,
                        "row_index": idx,
                        "reason": "MISSING_DRUG_KEY",
                    }
                )
                skipped_rows_by_role[item.role] += 1
                continue
            if not drug_key:
                skipped_rows.append(
                    {
                        "role": item.role,
                        "source_file": item.source_file,
                        "row_index": idx,
                        "reason": "MISSING_DRUG_KEY",
                    }
                )
                skipped_rows_by_role[item.role] += 1
            staged.append(
                {
                    "item": item,
                    "source_path": str(local_path),
                    "row_index": idx,
                    "row": row,
                    "drug_key": drug_key,
                    "drug_id": drug_id,
                    "drug_name": drug_name,
                }
            )

    if not staged:
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="NO_WRITABLE_ROWS_AFTER_VALIDATION",
            guardrail_checks=guardrail_checks,
            source_artifacts_used=source_artifacts_used,
            skipped_rows=skipped_rows,
            loaded_rows_by_role=loaded_rows_by_role,
            skipped_rows_by_role=skipped_rows_by_role,
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    def tx_write(tx: Any) -> None:
        ts = now_iso()
        tx.run(
            """
            MERGE (d:Disease {code:$code})
            SET d.name=$name, d.updated_at=$updated_at
            """,
            code="COAD",
            name="Colon adenocarcinoma",
            updated_at=ts,
        )
        tx.run("MERGE (r:Run {run_id:$run_id}) SET r.disease=$disease, r.updated_at=$updated_at", run_id=run_id, disease="COAD", updated_at=ts)

        for item in plan_items:
            local_path = resolve_local_path(paths, item)
            tx.run(
                """
                MERGE (s:SourceArtifact {path:$path})
                SET s.role=$role, s.target_table=$target_table, s.file_name=$file_name, s.updated_at=$updated_at
                WITH s
                MATCH (r:Run {run_id:$run_id})
                MERGE (r)-[:DERIVED_FROM_SOURCE]->(s)
                """,
                path=str(local_path),
                role=item.role,
                target_table=item.target_table,
                file_name=item.source_file,
                updated_at=ts,
                run_id=run_id,
            )

        for rec in staged:
            item: PlanItem = rec["item"]
            row = rec["row"]
            source_path = rec["source_path"]
            row_index = rec["row_index"]
            drug_key = rec["drug_key"]
            drug_id = rec["drug_id"]
            drug_name = rec["drug_name"]

            if item.role == "candidate_tiered":
                props = row_props(row, extra={"row_index": row_index, "source_file": item.source_file, "role": item.role})
                tx.run(
                    """
                    MATCH (d:Disease {code:$disease})
                    MATCH (r:Run {run_id:$run_id})
                    MATCH (s:SourceArtifact {path:$source_path})
                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                    SET c += $props, c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                        c.updated_at=$updated_at
                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                    MERGE (c)-[:DERIVED_FROM_SOURCE]->(s)
                    MERGE (r)-[:PRODUCED_BY_RUN]->(c)
                    """,
                    disease="COAD",
                    run_id=run_id,
                    source_path=source_path,
                    drug_key=drug_key,
                    drug_id=drug_id,
                    drug_name=drug_name,
                    props=props,
                    updated_at=now_iso(),
                )
                loaded_rows_by_role[item.role] += 1
                continue

            if item.role == "final_after_admet":
                evidence_key = f"COAD|{item.source_file}|{row_index}|{drug_key}"
                props = row_props(row, extra={"row_index": row_index, "source_file": item.source_file, "role": item.role})
                tx.run(
                    """
                    MATCH (d:Disease {code:$disease})
                    MATCH (r:Run {run_id:$run_id})
                    MATCH (s:SourceArtifact {path:$source_path})
                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                    SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                        c.updated_at=$updated_at
                    MERGE (a:AdmetEvidence {disease:$disease, evidence_key:$evidence_key})
                    SET a += $props, a.updated_at=$updated_at
                    MERGE (c)-[:HAS_ADMET_PROFILE]->(a)
                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                    MERGE (a)-[:DERIVED_FROM_SOURCE]->(s)
                    MERGE (r)-[:PRODUCED_BY_RUN]->(a)
                    """,
                    disease="COAD",
                    run_id=run_id,
                    source_path=source_path,
                    drug_key=drug_key,
                    drug_id=drug_id,
                    drug_name=drug_name,
                    evidence_key=evidence_key,
                    props=props,
                    updated_at=now_iso(),
                )
                loaded_rows_by_role[item.role] += 1
                continue

            if item.role == "external_validation_top30":
                evidence_key = f"COAD|{item.source_file}|{row_index}|{drug_key or 'no_drug_key'}"
                props = row_props(row, extra={"row_index": row_index, "source_file": item.source_file, "role": item.role})
                tx.run(
                    """
                    MATCH (d:Disease {code:$disease})
                    MATCH (r:Run {run_id:$run_id})
                    MATCH (s:SourceArtifact {path:$source_path})
                    MERGE (e:ExternalValidationEvidence {disease:$disease, evidence_key:$evidence_key})
                    SET e += $props, e.updated_at=$updated_at
                    MERGE (e)-[:VALIDATED_BY_EXTERNAL_DATA]->(d)
                    MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                    MERGE (r)-[:PRODUCED_BY_RUN]->(e)
                    """,
                    disease="COAD",
                    run_id=run_id,
                    source_path=source_path,
                    evidence_key=evidence_key,
                    props=props,
                    updated_at=now_iso(),
                )
                if drug_key:
                    tx.run(
                        """
                        MATCH (d:Disease {code:$disease})
                        MATCH (s:SourceArtifact {path:$source_path})
                        MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                        SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                            c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                            c.updated_at=$updated_at
                        MERGE (c)-[:CANDIDATE_FOR]->(d)
                        MERGE (c)-[:DERIVED_FROM_SOURCE]->(s)
                        """,
                        disease="COAD",
                        source_path=source_path,
                        drug_key=drug_key,
                        drug_id=drug_id,
                        drug_name=drug_name,
                        updated_at=now_iso(),
                    )
                loaded_rows_by_role[item.role] += 1
                continue

            if item.role == "admet_top30":
                evidence_key = f"COAD|{item.source_file}|{row_index}|{drug_key or 'no_drug_key'}"
                props = row_props(row, extra={"row_index": row_index, "source_file": item.source_file, "role": item.role})
                tx.run(
                    """
                    MATCH (r:Run {run_id:$run_id})
                    MATCH (s:SourceArtifact {path:$source_path})
                    MERGE (a:AdmetEvidence {disease:$disease, evidence_key:$evidence_key})
                    SET a += $props, a.updated_at=$updated_at
                    MERGE (a)-[:DERIVED_FROM_SOURCE]->(s)
                    MERGE (r)-[:PRODUCED_BY_RUN]->(a)
                    """,
                    disease="COAD",
                    run_id=run_id,
                    source_path=source_path,
                    evidence_key=evidence_key,
                    props=props,
                    updated_at=now_iso(),
                )
                if drug_key:
                    tx.run(
                        """
                        MATCH (d:Disease {code:$disease})
                        MATCH (s:SourceArtifact {path:$source_path})
                        MATCH (a:AdmetEvidence {disease:$disease, evidence_key:$evidence_key})
                        MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                        SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                            c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                            c.updated_at=$updated_at
                        MERGE (c)-[:HAS_ADMET_PROFILE]->(a)
                        MERGE (c)-[:CANDIDATE_FOR]->(d)
                        MERGE (c)-[:DERIVED_FROM_SOURCE]->(s)
                        """,
                        disease="COAD",
                        source_path=source_path,
                        evidence_key=evidence_key,
                        drug_key=drug_key,
                        drug_id=drug_id,
                        drug_name=drug_name,
                        updated_at=now_iso(),
                    )
                loaded_rows_by_role[item.role] += 1

    node_counts: dict[str, int] = {}
    relationship_counts: dict[str, int] = {}

    try:
        from neo4j import GraphDatabase  # type: ignore

        driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, password))
        with driver.session(database=args.neo4j_database) as session:
            session.execute_write(tx_write)
            node_counts["Disease_COAD"] = int(session.run("MATCH (d:Disease {code:'COAD'}) RETURN count(d) AS c").single()["c"])
            node_counts["DrugCandidate_for_COAD"] = int(
                session.run("MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'}) RETURN count(c) AS c").single()["c"]
            )
            relationship_counts["HAS_ADMET_PROFILE"] = int(
                session.run("MATCH (:DrugCandidate)-[:HAS_ADMET_PROFILE]->(:AdmetEvidence) RETURN count(*) AS c").single()["c"]
            )
            relationship_counts["VALIDATED_BY_EXTERNAL_DATA"] = int(
                session.run("MATCH (:ExternalValidationEvidence)-[:VALIDATED_BY_EXTERNAL_DATA]->(:Disease {code:'COAD'}) RETURN count(*) AS c").single()["c"]
            )
            node_counts["SourceArtifact"] = int(session.run("MATCH (:SourceArtifact) RETURN count(*) AS c").single()["c"])
            node_counts["Run"] = int(session.run("MATCH (:Run) RETURN count(*) AS c").single()["c"])
        driver.close()
    except Exception as exc:  # noqa: BLE001
        execute_report, validation_report = failure_report(
            paths=paths,
            reason="NEO4J_WRITE_FAILED",
            guardrail_checks=guardrail_checks,
            source_artifacts_used=source_artifacts_used,
            skipped_rows=skipped_rows,
            loaded_rows_by_role=loaded_rows_by_role,
            skipped_rows_by_role=skipped_rows_by_role,
            error_detail=str(exc),
        )
        print_summary(paths=paths, overall_status="FAIL", execute_report=execute_report, validation_report=validation_report)
        return 2

    required_nonzero = [
        node_counts.get("Disease_COAD", 0),
        node_counts.get("DrugCandidate_for_COAD", 0),
        relationship_counts.get("HAS_ADMET_PROFILE", 0),
        relationship_counts.get("VALIDATED_BY_EXTERNAL_DATA", 0),
        node_counts.get("SourceArtifact", 0),
        node_counts.get("Run", 0),
    ]
    if any(v <= 0 for v in required_nonzero):
        overall_status = "FAIL"
    elif len(skipped_rows) > 0:
        overall_status = "PASS_WITH_WARNINGS"
    else:
        overall_status = "PASS"

    execute_report = {
        "generated_at": now_iso(),
        "disease": "COAD",
        "execute_requested": True,
        "execute_performed": True,
        "reason": "",
        "guardrail_checks": guardrail_checks,
        "source_artifacts_used": source_artifacts_used,
        "node_counts": node_counts,
        "relationship_counts": relationship_counts,
        "loaded_rows_by_role": loaded_rows_by_role,
        "skipped_rows_by_role": skipped_rows_by_role,
        "skipped_rows": skipped_rows,
        "overall_status": overall_status,
    }
    validation_report = {
        "generated_at": now_iso(),
        "disease": "COAD",
        "execute_requested": True,
        "execute_performed": True,
        "guardrail_checks": guardrail_checks,
        "source_artifacts_used": source_artifacts_used,
        "node_counts": node_counts,
        "relationship_counts": relationship_counts,
        "loaded_rows_by_role": loaded_rows_by_role,
        "skipped_rows_by_role": skipped_rows_by_role,
        "skipped_rows": skipped_rows,
        "overall_status": overall_status,
    }
    write_reports(paths, execute_report, validation_report)
    print_summary(paths=paths, overall_status=overall_status, execute_report=execute_report, validation_report=validation_report)
    return 0 if overall_status in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(run())
