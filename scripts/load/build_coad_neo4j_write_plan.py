#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "config_validation"
DOCS_DIR = PROJECT_ROOT / "docs"

BLOCKED_DECISIONS = {
    "NEEDS_REVIEW",
    "DO_NOT_LOAD_EXCLUDED",
    "BLOCKED",
    "MISSING",
    "LOCAL_SYNC_NEEDED",
}

NO_ADMET_BLOCK_TABLES = {"final_candidate_result", "admet_result", "run_manifest"}

MIN_NODE_LABELS = [
    "Disease",
    "DrugCandidate",
    "ModelEvidence",
    "ExternalValidationEvidence",
    "AdmetEvidence",
    "Run",
    "SourceArtifact",
]

MIN_REL_TYPES = [
    "CANDIDATE_FOR",
    "SUPPORTED_BY_MODEL",
    "VALIDATED_BY_EXTERNAL_DATA",
    "HAS_ADMET_PROFILE",
    "PRODUCED_BY_RUN",
    "DERIVED_FROM_SOURCE",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build read-only COAD Neo4j write-plan preview.")
    p.add_argument("--disease", default="COAD")
    p.add_argument("--postgres-report", default="coad_postgres_execute_report.json")
    p.add_argument("--safe-plan-preview", default="coad_safe_write_plan_preview.json")
    p.add_argument("--json-output", default="coad_neo4j_write_plan_preview.json")
    p.add_argument("--markdown-output", default="coad_neo4j_write_plan_preview.md")
    return p.parse_args()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def upper_or_empty(v: Any) -> str:
    return safe_str(v).upper()


def basename(pathish: str) -> str:
    s = safe_str(pathish).replace("\\", "/")
    return s.rsplit("/", 1)[-1] if s else ""


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    last_exc: Exception | None = None
    for enc in ("utf-8", "utf-8-sig", "utf-16", "cp949"):
        try:
            return json.loads(raw.decode(enc))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise ValueError(f"failed to parse {path}: {last_exc}")


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("rows", "items", "plan", "plans", "artifact_results", "artifacts"):
        v = payload.get(key)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def first_non_empty(row: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in row and safe_str(row.get(k)):
            return row.get(k)
    return None


def detect_neo4j_status() -> str:
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception:  # noqa: BLE001
        return "DRIVER_NOT_AVAILABLE"

    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)
        try:
            driver.verify_connectivity()
        finally:
            driver.close()
        return "REACHABLE"
    except Exception as exc:  # noqa: BLE001
        msg = safe_str(exc).lower()
        if any(t in msg for t in ("auth", "authentication", "unauthorized", "credentials")):
            return "REACHABLE"
        try:
            with socket.create_connection(("localhost", 7687), timeout=2):
                return "REACHABLE"
        except Exception:  # noqa: BLE001
            return "NOT_REACHABLE"


def get_postgres_status(payload: Any) -> str:
    if isinstance(payload, dict):
        for k in ("final_status", "status", "postgres_status"):
            v = upper_or_empty(payload.get(k))
            if v:
                return v
        summary = payload.get("summary")
        if isinstance(summary, dict):
            for k in ("final_status", "status", "postgres_status"):
                v = upper_or_empty(summary.get(k))
                if v:
                    return v
    return "UNKNOWN"


def classify_graph_shapes(role: str, table: str) -> tuple[list[str], list[str]]:
    r = role.lower()
    t = table.lower()
    labels = {"Disease", "Run", "SourceArtifact"}
    rels = {"PRODUCED_BY_RUN", "DERIVED_FROM_SOURCE"}

    if "candidate" in r or t in {"drug_candidate_result", "drug_candidate_tier", "final_candidate_result"}:
        labels.add("DrugCandidate")
        rels.add("CANDIDATE_FOR")
    if "model" in r or "ensemble" in r or t in {"model_metric", "model_metric_detailed", "ensemble_metric"}:
        labels.add("ModelEvidence")
        rels.add("SUPPORTED_BY_MODEL")
    if "external_validation" in r or t == "external_validation_result":
        labels.add("ExternalValidationEvidence")
        rels.add("VALIDATED_BY_EXTERNAL_DATA")
    if "admet" in r or t == "admet_result":
        labels.add("AdmetEvidence")
        rels.add("HAS_ADMET_PROFILE")
    return sorted(labels), sorted(rels)


def is_non_compact(text: str) -> bool:
    t = safe_str(text).lower().replace("\\", "/")
    banned = [
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
    return any(x in t for x in banned)


def build_artifact_index(pg_payload: Any) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in extract_rows(pg_payload):
        source_uri = safe_str(first_non_empty(row, ["selected_s3_uri", "source_s3_uri", "source_uri", "s3_uri"]))
        source_file = safe_str(first_non_empty(row, ["selected_file", "source_file", "file_name", "file"]))
        target_table = safe_str(first_non_empty(row, ["destination_table", "target_table", "target_table_candidate", "table"]))
        status = upper_or_empty(first_non_empty(row, ["status", "decision", "load_status"]))
        row_count = row.get("row_count")
        normalized = {
            "source_uri": source_uri,
            "source_file": source_file or basename(source_uri),
            "target_table": target_table,
            "status": status,
            "row_count": row_count,
        }
        for key in (source_uri, normalized["source_file"], basename(source_uri)):
            if key:
                idx[key] = normalized
    return idx


def build_plan_rows(safe_payload: Any, artifact_index: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = extract_rows(safe_payload)
    plan_rows: list[dict[str, Any]] = []
    counts = {
        "source_rows": len(rows),
        "excluded_blocked_decision": 0,
        "excluded_no_admet_guardrail": 0,
        "excluded_non_compact": 0,
        "excluded_not_approved": 0,
        "included": 0,
    }

    for row in rows:
        decision = upper_or_empty(first_non_empty(row, ["decision", "load_decision", "execution_decision"]))
        status = upper_or_empty(first_non_empty(row, ["status", "load_status"]))
        if decision in BLOCKED_DECISIONS or status in BLOCKED_DECISIONS:
            counts["excluded_blocked_decision"] += 1
            continue

        source_uri = safe_str(first_non_empty(row, ["source_s3_uri", "selected_s3_uri", "source_uri", "s3_uri"]))
        source_file = safe_str(first_non_empty(row, ["selected_file", "source_file", "file_name", "file"]))
        role = safe_str(first_non_empty(row, ["source_file_role", "role", "source_role"]))
        target_table = safe_str(first_non_empty(row, ["target_table", "destination_table", "target_table_candidate", "table"]))
        source_hint = source_uri or source_file

        if "no_admet" in source_hint.lower() and target_table.lower() in NO_ADMET_BLOCK_TABLES:
            counts["excluded_no_admet_guardrail"] += 1
            continue
        if is_non_compact(source_hint):
            counts["excluded_non_compact"] += 1
            continue

        matched = None
        for key in (source_uri, source_file, basename(source_uri)):
            if key and key in artifact_index:
                matched = artifact_index[key]
                break
        if not matched:
            counts["excluded_not_approved"] += 1
            continue
        approved = upper_or_empty(matched.get("status"))
        if approved and approved not in {"LOADED", "APPROVED", "SUCCESS", "POSTGRES_LOADED"}:
            counts["excluded_not_approved"] += 1
            continue

        labels, rels = classify_graph_shapes(role=role, table=target_table or safe_str(matched.get("target_table")))
        plan_rows.append(
            {
                "source_file_role": role,
                "source_file": source_file or safe_str(matched.get("source_file")),
                "source_s3_uri": source_uri or safe_str(matched.get("source_uri")),
                "target_table": target_table or safe_str(matched.get("target_table")),
                "postgres_artifact_status": approved or "UNKNOWN",
                "postgres_artifact_row_count": matched.get("row_count"),
                "planned_node_labels": labels,
                "planned_relationship_types": rels,
                "aggregation_level": "artifact_role_table",
                "notes": "Aggregated preview only; no row-level graph data fabricated.",
            }
        )
        counts["included"] += 1

    return plan_rows, counts


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def plan_markdown_table(rows: list[dict[str, Any]]) -> str:
    head = [
        "| source_file_role | target_table | source_file | postgres_artifact_status | postgres_artifact_row_count | planned_node_labels | planned_relationship_types |",
        "|---|---|---|---|---:|---|---|",
    ]
    if not rows:
        head.append("| (none) | (none) | (none) | (none) | 0 | (none) | (none) |")
        return "\n".join(head)
    for r in rows:
        head.append(
            "| "
            + " | ".join(
                [
                    safe_str(r.get("source_file_role")) or "(none)",
                    safe_str(r.get("target_table")) or "(none)",
                    safe_str(r.get("source_file")) or "(none)",
                    safe_str(r.get("postgres_artifact_status")) or "UNKNOWN",
                    str(r.get("postgres_artifact_row_count") if r.get("postgres_artifact_row_count") is not None else 0),
                    ", ".join(r.get("planned_node_labels", [])) or "(none)",
                    ", ".join(r.get("planned_relationship_types", [])) or "(none)",
                ]
            )
            + " |"
        )
    return "\n".join(head)


def write_markdown(
    path: Path,
    *,
    generated_at: str,
    postgres_status: str,
    neo4j_status: str,
    blocked_decisions: list[str],
    no_admet_guardrail: dict[str, Any],
    planned_node_labels: list[str],
    planned_relationship_types: list[str],
    plan_rows: list[dict[str, Any]],
    input_reports: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# COAD Neo4j Write-Plan Preview (Read-Only)",
        "",
        f"- timestamp: `{generated_at}`",
        f"- PostgreSQL status: `{postgres_status}`",
        f"- Neo4j status: `{neo4j_status}`",
        '- Neo4j execute was not run.',
        "",
        "## Planned Node Labels",
    ]
    lines.extend([f"- `{x}`" for x in planned_node_labels])
    lines.append("")
    lines.append("## Planned Relationship Types")
    lines.extend([f"- `{x}`" for x in planned_relationship_types])
    lines.append("")
    lines.append("## Plan Rows")
    lines.append(plan_markdown_table(plan_rows))
    lines.append("")
    lines.append("## Blocked Decisions")
    lines.extend([f"- `{x}`" for x in blocked_decisions])
    lines.append("")
    lines.append("## no_admet Guardrail")
    lines.append(f"- blocked_tables: `{', '.join(no_admet_guardrail.get('blocked_tables', []))}`")
    lines.append(f"- excluded_rows: `{no_admet_guardrail.get('excluded_rows', 0)}`")
    lines.append("")
    lines.append("## Source Input Reports")
    for k, v in input_reports.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    disease = safe_str(args.disease).upper() or "COAD"

    postgres_report = OUTPUT_DIR / args.postgres_report
    safe_plan_preview = OUTPUT_DIR / args.safe_plan_preview
    json_output = OUTPUT_DIR / args.json_output
    markdown_output = DOCS_DIR / args.markdown_output

    if not postgres_report.exists():
        raise FileNotFoundError(f"missing input: {postgres_report}")
    if not safe_plan_preview.exists():
        raise FileNotFoundError(f"missing input: {safe_plan_preview}")

    postgres_payload = load_json(postgres_report)
    safe_payload = load_json(safe_plan_preview)
    postgres_status = get_postgres_status(postgres_payload)
    if postgres_status != "POSTGRES_LOADED":
        raise RuntimeError(f"postgres_status must be POSTGRES_LOADED, got {postgres_status}")

    neo4j_status = detect_neo4j_status()
    artifact_index = build_artifact_index(postgres_payload)
    plan_rows, counts = build_plan_rows(safe_payload=safe_payload, artifact_index=artifact_index)

    planned_node_labels = sorted(set(MIN_NODE_LABELS).union(*(set(r.get("planned_node_labels", [])) for r in plan_rows)))
    planned_relationship_types = sorted(
        set(MIN_REL_TYPES).union(*(set(r.get("planned_relationship_types", [])) for r in plan_rows))
    )

    payload = {
        "disease": disease,
        "generated_at": now_iso(),
        "execute": False,
        "postgres_status": postgres_status,
        "neo4j_status": neo4j_status,
        "input_reports": {
            "postgres_execute_report": str(postgres_report),
            "safe_write_plan_preview": str(safe_plan_preview),
        },
        "blocked_decisions": sorted(BLOCKED_DECISIONS),
        "no_admet_guardrail": {
            "blocked_tables": sorted(NO_ADMET_BLOCK_TABLES),
            "excluded_rows": counts["excluded_no_admet_guardrail"],
        },
        "planned_node_labels": planned_node_labels,
        "planned_relationship_types": planned_relationship_types,
        "plan_rows": plan_rows,
        "summary": {
            "safe_preview_source_rows": counts["source_rows"],
            "neo4j_plan_rows": len(plan_rows),
            "excluded_blocked_decision": counts["excluded_blocked_decision"],
            "excluded_no_admet_guardrail": counts["excluded_no_admet_guardrail"],
            "excluded_non_compact": counts["excluded_non_compact"],
            "excluded_not_approved": counts["excluded_not_approved"],
            "notes": [
                "Read-only preview only.",
                "Neo4j execute was not run.",
                "PostgreSQL execute was not run.",
                "Plan rows are aggregated by artifact/role/table.",
            ],
        },
    }

    write_json(json_output, payload)
    write_markdown(
        markdown_output,
        generated_at=payload["generated_at"],
        postgres_status=postgres_status,
        neo4j_status=neo4j_status,
        blocked_decisions=payload["blocked_decisions"],
        no_admet_guardrail=payload["no_admet_guardrail"],
        planned_node_labels=planned_node_labels,
        planned_relationship_types=planned_relationship_types,
        plan_rows=plan_rows,
        input_reports=payload["input_reports"],
    )

    print(f"disease={disease}")
    print(f"postgres_status={postgres_status}")
    print(f"neo4j_status={neo4j_status}")
    print(f"neo4j_plan_rows={len(plan_rows)}")
    print("execute=false")
    print(f"json_output={json_output}")
    print(f"markdown_output={markdown_output}")


if __name__ == "__main__":
    main()
