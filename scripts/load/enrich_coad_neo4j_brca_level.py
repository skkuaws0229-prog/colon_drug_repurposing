#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_TABLES = [
    "drug_candidate_result",
    "drug_candidate_tier",
    "final_candidate_result",
    "admet_result",
    "external_validation_result",
    "model_metric",
    "model_metric_detailed",
    "ensemble_metric",
    "source_artifact",
    "coad_load_audit",
]
CORE_REQUIRED_TABLES = [
    "drug_candidate_result",
    "drug_candidate_tier",
    "final_candidate_result",
    "admet_result",
    "external_validation_result",
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
    "candidate_name",
    "smiles",
]
TIER_RANK_CANDIDATES = [
    "tier",
    "candidate_tier",
    "drug_tier",
    "rank",
    "final_rank",
    "ensemble_rank",
    "recommendation_rank",
]
BLOCKED_DECISIONS = {
    "NEEDS_REVIEW",
    "DO_NOT_LOAD_EXCLUDED",
    "BLOCKED",
    "MISSING",
    "LOCAL_SYNC_NEEDED",
}
NO_ADMET_BLOCK_TABLES = {"admet_result", "final_candidate_result", "run_manifest"}
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def upper(v: Any) -> str:
    return safe_str(v).upper()


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="COAD BRCA-level Neo4j enrichment from PostgreSQL compact result tables.")
    p.add_argument("--disease", default="COAD")
    p.add_argument("--project-root", default="")
    p.add_argument("--pg-host", default=os.getenv("PGHOST", "localhost"))
    p.add_argument("--pg-port", type=int, default=int(os.getenv("PGPORT", "5432")))
    p.add_argument("--pg-database", default=os.getenv("PGDATABASE", "Drug"))
    p.add_argument("--pg-user", default=os.getenv("PGUSER", "Drug"))
    p.add_argument("--pg-password-env", default="PGPASSWORD")
    p.add_argument("--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    p.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    p.add_argument("--neo4j-password-env", default="NEO4J_PASSWORD")
    p.add_argument("--neo4j-database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    p.add_argument("--execute", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def load_env_local(project_root: Path) -> None:
    env_path = project_root / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16", "cp949"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise ValueError(f"failed_to_parse_json: {path}")


def normalize_key(k: str) -> str:
    out = re.sub(r"[^0-9A-Za-z_]", "_", k.strip().lower())
    out = re.sub(r"_+", "_", out).strip("_")
    if not out:
        return ""
    if out[0].isdigit():
        out = f"f_{out}"
    return out[:80]


def to_scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        if len(s) > 4000:
            return s[:4000]
        return s
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")[:4000]
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return safe_str(v)[:4000]
    return safe_str(v)[:4000]


def sanitized_props(row: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        nk = normalize_key(str(k))
        if not nk:
            continue
        sv = to_scalar(v)
        if sv is None:
            continue
        out[nk] = sv
    if extra:
        for k, v in extra.items():
            nk = normalize_key(str(k))
            if not nk:
                continue
            sv = to_scalar(v)
            if sv is None:
                continue
            out[nk] = sv
    return out


def row_hash(table: str, row: dict[str, Any]) -> str:
    payload = {k: to_scalar(v) for k, v in row.items()}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(f"{table}|{encoded}".encode("utf-8")).hexdigest()[:20]


def parse_payload_dict(row: dict[str, Any]) -> dict[str, Any]:
    if "payload" not in row:
        return {}
    payload = row.get("payload")
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        s = payload.strip()
        if not s:
            return {}
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return {}
    return {}


def merged_row_for_detection(row: dict[str, Any]) -> dict[str, Any]:
    merged = dict(row)
    payload_dict = parse_payload_dict(row)
    for k, v in payload_dict.items():
        nk = normalize_key(str(k))
        if not nk:
            continue
        if nk not in {normalize_key(str(x)) for x in merged.keys()}:
            merged[k] = v
    return merged


def detect_drug_key(row: dict[str, Any]) -> tuple[str, str, str]:
    lowered: dict[str, Any] = {normalize_key(str(k)): v for k, v in merged_row_for_detection(row).items()}
    for key in DRUG_KEY_CANDIDATES:
        nk = normalize_key(key)
        if nk in lowered and safe_str(lowered[nk]):
            val = safe_str(lowered[nk])
            if nk in {"drug_name", "drug", "compound_name", "name", "candidate_name"}:
                return f"name:{val.lower()}", "", val
            if nk == "smiles":
                return f"smiles:{val}", "", ""
            if nk in {"chembl_id", "drug_chembl_id"}:
                return f"chembl:{val}", val, ""
            return f"id:{val}", val, ""
    return "", "", ""


def detect_tier_rank_fields(row: dict[str, Any]) -> dict[str, Any]:
    lowered: dict[str, Any] = {normalize_key(str(k)): v for k, v in merged_row_for_detection(row).items()}
    out: dict[str, Any] = {}
    for key in TIER_RANK_CANDIDATES:
        nk = normalize_key(key)
        if nk in lowered and safe_str(lowered[nk]):
            out[nk] = lowered[nk]
    return out


def detect_model_key(row: dict[str, Any]) -> str:
    lowered: dict[str, Any] = {normalize_key(str(k)): v for k, v in row.items()}
    for k in ("model", "model_name", "algorithm", "learner", "estimator", "method"):
        nk = normalize_key(k)
        if nk in lowered and safe_str(lowered[nk]):
            return f"model:{safe_str(lowered[nk]).lower()}"
    return ""


def detect_source_path(row: dict[str, Any]) -> str:
    for k in (
        "source_s3_uri",
        "selected_s3_uri",
        "source_uri",
        "artifact_uri",
        "s3_uri",
        "source_path",
        "file_path",
        "selected_file",
        "source_file",
        "file_name",
    ):
        if k in row and safe_str(row.get(k)):
            return safe_str(row.get(k))
    lowered = {normalize_key(str(k)): v for k, v in row.items()}
    for k in ("source_s3_uri", "selected_s3_uri", "artifact_uri", "file_name", "source_file"):
        if k in lowered and safe_str(lowered.get(k)):
            return safe_str(lowered.get(k))
    return ""


def is_non_compact(text: str) -> bool:
    t = safe_str(text).lower().replace("\\", "/")
    return any(tok in t for tok in NON_COMPACT_TOKENS)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def get_postgres_connection(args: argparse.Namespace):
    password = os.getenv(args.pg_password_env, "")
    try:
        import psycopg  # type: ignore

        conn = psycopg.connect(
            host=args.pg_host,
            port=args.pg_port,
            dbname=args.pg_database,
            user=args.pg_user,
            password=password,
        )
        return conn, "psycopg"
    except Exception:
        pass

    import psycopg2  # type: ignore

    conn = psycopg2.connect(
        host=args.pg_host,
        port=args.pg_port,
        dbname=args.pg_database,
        user=args.pg_user,
        password=password,
    )
    return conn, "psycopg2"


def table_exists(cur: Any, table: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS(
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema='public' AND table_name=%s
        )
        """,
        (table,),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def table_columns(cur: Any, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def safe_table_name(table: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", table):
        raise ValueError(f"unsafe_table_name: {table}")
    return table


def fetch_table_rows(cur: Any, table: str, columns: list[str], disease: str) -> tuple[list[dict[str, Any]], int, str]:
    t = safe_table_name(table)
    has_disease = "disease" in columns
    if has_disease:
        cur.execute(f"SELECT * FROM {t} WHERE disease=%s", (disease,))
        reason = "disease_filtered"
    else:
        cur.execute(f"SELECT * FROM {t}")
        reason = "disease_column_not_found_full_table_read"
    fetched = cur.fetchall()
    desc = [d[0] for d in cur.description]
    rows = [dict(zip(desc, r)) for r in fetched]
    return rows, len(rows), reason


def check_neo4j_reachable(uri: str) -> tuple[bool, str]:
    try:
        host_port = uri.replace("bolt://", "").split("/")[0]
        host, port = host_port.split(":")
        with socket.create_connection((host, int(port)), timeout=3):
            return True, "reachable"
    except Exception as exc:
        return False, f"not_reachable: {exc}"


def extract_status(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "UNKNOWN"
    for key in ("final_status", "status", "overall_status", "postgres_status"):
        val = upper(payload.get(key))
        if val:
            return val
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in ("final_status", "status", "postgres_status"):
            val = upper(summary.get(key))
            if val:
                return val
    return "UNKNOWN"


def write_reports(
    enrich_json_path: Path,
    enrich_md_path: Path,
    val_json_path: Path,
    val_md_path: Path,
    enrich_report: dict[str, Any],
    validation_report: dict[str, Any],
) -> None:
    enrich_json_path.parent.mkdir(parents=True, exist_ok=True)
    enrich_md_path.parent.mkdir(parents=True, exist_ok=True)
    val_json_path.parent.mkdir(parents=True, exist_ok=True)
    val_md_path.parent.mkdir(parents=True, exist_ok=True)

    enrich_json_path.write_text(json.dumps(enrich_report, ensure_ascii=False, indent=2), encoding="utf-8")
    val_json_path.write_text(json.dumps(validation_report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# COAD Neo4j BRCA-Level Enrichment Report",
        "",
        f"- generated_at: {enrich_report.get('generated_at')}",
        f"- disease: {enrich_report.get('disease')}",
        f"- execute_requested: {str(enrich_report.get('execute_requested')).lower()}",
        f"- execute_performed: {str(enrich_report.get('execute_performed')).lower()}",
        f"- overall_status: {enrich_report.get('overall_status')}",
        "",
        "## Guardrails",
    ]
    for k, v in enrich_report.get("guardrail_status", {}).items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Source PostgreSQL Table Counts"])
    for k, v in enrich_report.get("source_postgres_table_counts", {}).items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Loaded Nodes By Type"])
    for k, v in enrich_report.get("loaded_nodes_by_type", {}).items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Loaded Relationships By Type"])
    for k, v in enrich_report.get("loaded_relationships_by_type", {}).items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Skipped Rows By Source Table"])
    for k, v in enrich_report.get("skipped_rows_by_source_table", {}).items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Skipped Rows"])
    for s in enrich_report.get("skipped_rows", [])[:200]:
        md.append(
            f"- table={s.get('source_table')} reason={s.get('reason')} row_hash={s.get('row_hash')} source={s.get('source_path')}"
        )
    md.extend(["", "## Failures"])
    for f in enrich_report.get("failures", []):
        md.append(f"- {f}")
    md.extend(["", "## Warnings"])
    for w in enrich_report.get("warnings", []):
        md.append(f"- {w}")
    md.extend(["", "## Table Columns By Source"])
    table_cols = enrich_report.get("table_columns_by_source", {})
    for t, cols in table_cols.items():
        md.append(f"- {t}: {', '.join(cols)}")
    md.extend(["", "## Validation Decision"])
    md.append(f"- {enrich_report.get('validation_decision_explanation', '')}")
    enrich_md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    md2 = [
        "# COAD Neo4j BRCA-Level Validation Report",
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
        md2.append(f"- {k}: {v}")
    md2.extend(["", "## Relationship Counts"])
    for k, v in validation_report.get("relationship_counts", {}).items():
        md2.append(f"- {k}: {v}")
    md2.extend(["", "## Guardrails"])
    for k, v in validation_report.get("guardrail_status", {}).items():
        md2.append(f"- {k}: {v}")
    val_md_path.write_text("\n".join(md2) + "\n", encoding="utf-8")


def run() -> int:
    args = parse_args()
    if safe_str(args.project_root):
        project_root = Path(args.project_root)
        if not project_root.is_absolute():
            project_root = Path.cwd() / project_root
    else:
        project_root = find_project_root()
    load_env_local(project_root)
    if args.neo4j_uri == "bolt://localhost:7687" and os.getenv("NEO4J_URI"):
        args.neo4j_uri = os.getenv("NEO4J_URI", args.neo4j_uri)
    if args.neo4j_user == "neo4j" and os.getenv("NEO4J_USER"):
        args.neo4j_user = os.getenv("NEO4J_USER", args.neo4j_user)
    if args.neo4j_database == "neo4j" and os.getenv("NEO4J_DATABASE"):
        args.neo4j_database = os.getenv("NEO4J_DATABASE", args.neo4j_database)
    if args.pg_host == "localhost" and os.getenv("PGHOST"):
        args.pg_host = os.getenv("PGHOST", args.pg_host)
    if args.pg_port == 5432 and os.getenv("PGPORT"):
        try:
            args.pg_port = int(os.getenv("PGPORT", "5432"))
        except Exception:
            pass
    if args.pg_database == "Drug" and os.getenv("PGDATABASE"):
        args.pg_database = os.getenv("PGDATABASE", args.pg_database)
    if args.pg_user == "Drug" and os.getenv("PGUSER"):
        args.pg_user = os.getenv("PGUSER", args.pg_user)

    disease = upper(args.disease)
    outputs_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    enrich_json_path = outputs_dir / "coad_neo4j_brca_level_enrichment_report.json"
    enrich_md_path = docs_dir / "coad_neo4j_brca_level_enrichment_report.md"
    val_json_path = outputs_dir / "coad_neo4j_brca_level_validation_report.json"
    val_md_path = docs_dir / "coad_neo4j_brca_level_validation_report.md"

    postgres_execute_json = outputs_dir / "coad_postgres_execute_report.json"
    neo4j_execute_json = outputs_dir / "coad_neo4j_execute_report.json"
    neo4j_validation_json = outputs_dir / "coad_neo4j_validation_report.json"

    guardrail_status: dict[str, Any] = {
        "postgres_write_disabled": True,
        "neo4j_merge_only": True,
        "disease_is_coad": disease == "COAD",
    }
    warnings: list[str] = []
    failures: list[str] = []
    source_postgres_table_counts: dict[str, Any] = {}
    skipped_rows: list[dict[str, Any]] = []
    skipped_rows_by_source_table: dict[str, int] = {t: 0 for t in REQUIRED_TABLES}
    loaded_nodes_by_type: dict[str, int] = {}
    loaded_relationships_by_type: dict[str, int] = {}
    source_artifacts_used: set[str] = set()
    loaded_rows_by_source_table: dict[str, int] = {t: 0 for t in REQUIRED_TABLES}
    tier_usable_row_count = 0
    tier_loaded_row_count = 0

    if disease != "COAD":
        failures.append("ONLY_COAD_SUPPORTED")

    for p in [postgres_execute_json, neo4j_execute_json, neo4j_validation_json]:
        if not p.exists():
            failures.append(f"REQUIRED_INPUT_MISSING: {p}")

    pg_status = "UNKNOWN"
    prev_neo4j_status = "UNKNOWN"
    prev_neo4j_execute_performed = False
    if not failures:
        pg_payload = read_json(postgres_execute_json)
        neo_exec_payload = read_json(neo4j_execute_json)
        _ = read_json(neo4j_validation_json)
        pg_status = extract_status(pg_payload)
        prev_neo4j_status = upper(neo_exec_payload.get("overall_status"))
        prev_neo4j_execute_performed = bool(neo_exec_payload.get("execute_performed"))
        guardrail_status["postgres_status_in_report"] = pg_status
        guardrail_status["neo4j_initial_execute_performed"] = prev_neo4j_execute_performed
        guardrail_status["neo4j_initial_status"] = prev_neo4j_status
        if pg_status != "POSTGRES_LOADED":
            failures.append("POSTGRES_STATUS_NOT_LOADED")
        if not prev_neo4j_execute_performed or prev_neo4j_status not in {"PASS", "PASS_WITH_WARNINGS"}:
            failures.append("INITIAL_NEO4J_EXECUTE_STATUS_NOT_OK")

    neo4j_reachable, neo4j_reachability_reason = check_neo4j_reachable(args.neo4j_uri)
    guardrail_status["neo4j_reachable"] = neo4j_reachable
    guardrail_status["neo4j_reachability_reason"] = neo4j_reachability_reason
    if not neo4j_reachable:
        failures.append("NEO4J_NOT_REACHABLE")

    config_path_candidates = [
        project_root / "configs" / "diseases" / "coad.yaml",
        project_root / "configs" / "diseases" / "colon.yaml",
    ]
    config_payload: dict[str, Any] = {}
    config_path_used = ""
    for cp in config_path_candidates:
        if cp.exists():
            config_payload = load_yaml(cp)
            if config_payload:
                config_path_used = str(cp)
                break
    guardrail_status["biology_config_path"] = config_path_used
    if not config_payload:
        warnings.append("BIOLOGY_CONFIG_NOT_FOUND")

    pg_rows: dict[str, list[dict[str, Any]]] = {}
    table_columns_map: dict[str, list[str]] = {}
    pg_count_details: dict[str, Any] = {}

    try:
        conn, pg_driver = get_postgres_connection(args)
        guardrail_status["postgres_driver"] = pg_driver
        conn.autocommit = True
        with conn.cursor() as cur:
            for table in REQUIRED_TABLES:
                exists = table_exists(cur, table)
                if not exists:
                    failures.append(f"POSTGRES_TABLE_MISSING:{table}")
                    continue
                cols = table_columns(cur, table)
                table_columns_map[table] = cols
                rows, count, count_reason = fetch_table_rows(cur, table, cols, disease)
                pg_rows[table] = rows
                source_postgres_table_counts[table] = count
                pg_count_details[table] = {
                    "count": count,
                    "count_reason": count_reason,
                    "columns": cols,
                }
    except Exception as exc:  # noqa: BLE001
        failures.append(f"POSTGRES_READ_FAILED:{exc}")

    for t in CORE_REQUIRED_TABLES:
        if source_postgres_table_counts.get(t, 0) <= 0:
            failures.append(f"CORE_TABLE_EMPTY:{t}")

    guardrail_status["blocked_decisions_rejected"] = True
    guardrail_status["no_admet_guardrail"] = True
    for table in ("admet_result", "final_candidate_result"):
        for row in pg_rows.get(table, []):
            sp = detect_source_path(row).lower()
            if "no_admet" in sp and table in NO_ADMET_BLOCK_TABLES:
                guardrail_status["no_admet_guardrail"] = False
                failures.append(f"NO_ADMET_GUARDRAIL_VIOLATION:{table}")
                break

    if failures:
        overall_status = "FAIL"
        execute_performed = False
    else:
        overall_status = "PASS"
        execute_performed = False

    def resolve_neo4j_password(env_name: str) -> str:
        primary = os.getenv(env_name, "")
        if primary:
            return primary
        for alt in ("NEO4J_PASSWORD", "NEO4J_PASSWORD_RUNTIME"):
            v = os.getenv(alt, "")
            if v:
                return v
        return ""

    # execute path
    if args.execute and not failures:
        password = resolve_neo4j_password(args.neo4j_password_env)
        if not password:
            failures.append("NEO4J_PASSWORD_MISSING")
        try:
            from neo4j import GraphDatabase  # type: ignore
        except Exception:
            failures.append("NEO4J_DRIVER_NOT_AVAILABLE")

        if not failures:
            run_id = f"COAD_NEO4J_BRCA_LEVEL_ENRICHMENT_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            ts = now_iso()
            try:
                driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, password))
                with driver.session(database=args.neo4j_database) as session:
                    session.run("RETURN 1 AS ok").single()

                    def merge_source_and_run(tx: Any, source_path: str, role: str, target_table: str, file_name: str) -> None:
                        tx.run(
                            """
                            MERGE (r:Run {run_id:$run_id})
                            SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                            WITH r
                            MERGE (s:SourceArtifact {path:$source_path})
                            SET s.role=$role, s.target_table=$target_table, s.file_name=$file_name, s.updated_at=$updated_at
                            MERGE (r)-[:DERIVED_FROM_SOURCE]->(s)
                            """,
                            run_id=run_id,
                            disease=disease,
                            source_path=source_path,
                            role=role,
                            target_table=target_table,
                            file_name=file_name,
                            updated_at=ts,
                        )

                    def write_table_rows(tx: Any, table: str, rows: list[dict[str, Any]]) -> None:
                        nonlocal tier_usable_row_count, tier_loaded_row_count
                        for row_idx, row in enumerate(rows, start=1):
                            r_hash = row_hash(table, row)
                            drug_key, drug_id, drug_name = detect_drug_key(row)
                            source_path = detect_source_path(row)
                            if source_path and is_non_compact(source_path):
                                skipped_rows.append(
                                    {"source_table": table, "reason": "NON_COMPACT_SOURCE_BLOCKED", "row_hash": r_hash, "source_path": source_path}
                                )
                                skipped_rows_by_source_table[table] += 1
                                continue
                            if source_path:
                                source_artifacts_used.add(source_path)
                                merge_source_and_run(tx, source_path, table, table, Path(source_path).name)

                            if table in {"drug_candidate_result", "drug_candidate_tier", "final_candidate_result"} and not drug_key:
                                skipped_rows.append(
                                    {
                                        "source_table": table,
                                        "reason": "MISSING_DRUG_KEY",
                                        "row_hash": r_hash,
                                        "source_path": source_path,
                                        "row_index": row_idx,
                                    }
                                )
                                skipped_rows_by_source_table[table] += 1
                                continue

                            if table == "admet_result" and not drug_key:
                                skipped_rows.append(
                                    {
                                        "source_table": table,
                                        "reason": "MISSING_DRUG_KEY",
                                        "row_hash": r_hash,
                                        "source_path": source_path,
                                        "row_index": row_idx,
                                    }
                                )
                                skipped_rows_by_source_table[table] += 1
                                continue

                            props = sanitized_props(row, {"disease": disease, "source_table": table, "row_hash": r_hash, "updated_at": ts})

                            if table == "drug_candidate_result":
                                evidence_key = f"COAD|candidate_score|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                    SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                        c.updated_at=$updated_at
                                    MERGE (e:CandidateScore {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                                    MERGE (c)-[:HAS_CANDIDATE_SCORE]->(e)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    drug_key=drug_key,
                                    drug_id=drug_id,
                                    drug_name=drug_name,
                                    evidence_key=evidence_key,
                                    props=props,
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:CandidateScore {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=evidence_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "drug_candidate_tier":
                                tier_rank_fields = detect_tier_rank_fields(row)
                                if not tier_rank_fields:
                                    skipped_rows.append(
                                        {
                                            "source_table": table,
                                            "reason": "MISSING_TIER_OR_RANK",
                                            "row_hash": r_hash,
                                            "source_path": source_path,
                                            "row_index": row_idx,
                                        }
                                    )
                                    skipped_rows_by_source_table[table] += 1
                                    continue
                                tier_usable_row_count += 1
                                evidence_key = f"COAD|tier|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                    SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                        c.updated_at=$updated_at
                                    MERGE (e:TierEvidence {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                                    MERGE (c)-[:HAS_TIER]->(e)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    drug_key=drug_key,
                                    drug_id=drug_id,
                                    drug_name=drug_name,
                                    evidence_key=evidence_key,
                                    props={**props, **sanitized_props(tier_rank_fields)},
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:TierEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=evidence_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                tier_loaded_row_count += 1
                                continue

                            if table == "final_candidate_result":
                                evidence_key = f"COAD|final|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                    SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                        c.updated_at=$updated_at
                                    MERGE (e:FinalCandidateEvidence {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                                    MERGE (c)-[:SELECTED_AS_FINAL]->(e)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    drug_key=drug_key,
                                    drug_id=drug_id,
                                    drug_name=drug_name,
                                    evidence_key=evidence_key,
                                    props=props,
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:FinalCandidateEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=evidence_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "admet_result":
                                evidence_key = f"COAD|admet|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                    SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                        c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                        c.updated_at=$updated_at
                                    MERGE (e:AdmetEvidence {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (c)-[:CANDIDATE_FOR]->(d)
                                    MERGE (c)-[:HAS_ADMET_PROFILE]->(e)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    drug_key=drug_key,
                                    drug_id=drug_id,
                                    drug_name=drug_name,
                                    evidence_key=evidence_key,
                                    props=props,
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:AdmetEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=evidence_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "external_validation_result":
                                evidence_key = f"COAD|external|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (e:ExternalValidationEvidence {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (e)-[:VALIDATED_BY_EXTERNAL_DATA]->(d)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    evidence_key=evidence_key,
                                    props=props,
                                )
                                if drug_key:
                                    tx.run(
                                        """
                                        MERGE (d:Disease {code:$disease})
                                        MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                        SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                            c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                            c.updated_at=$updated_at
                                        MATCH (e:ExternalValidationEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MERGE (c)-[:CANDIDATE_FOR]->(d)
                                        MERGE (c)-[:HAS_EXTERNAL_VALIDATION]->(e)
                                        """,
                                        disease=disease,
                                        drug_key=drug_key,
                                        drug_id=drug_id,
                                        drug_name=drug_name,
                                        evidence_key=evidence_key,
                                        updated_at=ts,
                                    )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:ExternalValidationEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=evidence_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "model_metric":
                                m_key = detect_model_key(row) or f"model_hash:{r_hash}"
                                evidence_key = f"COAD|model|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (m:ModelEvidence {disease:$disease, model_key:$model_key})
                                    SET m += $props, m.updated_at=$updated_at
                                    MERGE (m)-[:SUPPORTS_DISEASE_MODELING]->(d)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(m)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    model_key=m_key,
                                    props={**props, "model_key": m_key, "evidence_key": evidence_key},
                                )
                                if drug_key:
                                    tx.run(
                                        """
                                        MERGE (d:Disease {code:$disease})
                                        MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                        SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                            c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                            c.updated_at=$updated_at
                                        MATCH (m:ModelEvidence {disease:$disease, model_key:$model_key})
                                        MERGE (c)-[:CANDIDATE_FOR]->(d)
                                        MERGE (c)-[:SUPPORTED_BY_MODEL]->(m)
                                        """,
                                        disease=disease,
                                        drug_key=drug_key,
                                        drug_id=drug_id,
                                        drug_name=drug_name,
                                        model_key=m_key,
                                        updated_at=ts,
                                    )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (m:ModelEvidence {disease:$disease, model_key:$model_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (m)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        model_key=m_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "model_metric_detailed":
                                m_key = detect_model_key(row) or f"model_hash:{r_hash}"
                                detail_key = f"COAD|model_detail|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (m:ModelEvidence {disease:$disease, model_key:$model_key})
                                    SET m.updated_at=$updated_at
                                    MERGE (e:ModelDetailEvidence {disease:$disease, detail_key:$detail_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (m)-[:HAS_DETAILED_MODEL_METRIC]->(e)
                                    MERGE (m)-[:SUPPORTS_DISEASE_MODELING]->(d)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    model_key=m_key,
                                    detail_key=detail_key,
                                    props={**props, "model_key": m_key},
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:ModelDetailEvidence {disease:$disease, detail_key:$detail_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        detail_key=detail_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "ensemble_metric":
                                e_key = f"COAD|ensemble|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (e:EnsembleEvidence {disease:$disease, evidence_key:$evidence_key})
                                    SET e += $props, e.updated_at=$updated_at
                                    MERGE (e)-[:SUPPORTS_ENSEMBLE_RANKING]->(d)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(e)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    evidence_key=e_key,
                                    props=props,
                                )
                                if drug_key:
                                    tx.run(
                                        """
                                        MERGE (d:Disease {code:$disease})
                                        MERGE (c:DrugCandidate {disease:$disease, drug_key:$drug_key})
                                        SET c.drug_id=CASE WHEN $drug_id<>'' THEN $drug_id ELSE c.drug_id END,
                                            c.drug_name=CASE WHEN $drug_name<>'' THEN $drug_name ELSE c.drug_name END,
                                            c.updated_at=$updated_at
                                        MATCH (e:EnsembleEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MERGE (c)-[:CANDIDATE_FOR]->(d)
                                        MERGE (c)-[:SUPPORTED_BY_ENSEMBLE]->(e)
                                        """,
                                        disease=disease,
                                        drug_key=drug_key,
                                        drug_id=drug_id,
                                        drug_name=drug_name,
                                        evidence_key=e_key,
                                        updated_at=ts,
                                    )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (e:EnsembleEvidence {disease:$disease, evidence_key:$evidence_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (e)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        evidence_key=e_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "source_artifact":
                                sp = source_path or f"source_artifact::{r_hash}"
                                if is_non_compact(sp):
                                    skipped_rows.append(
                                        {"source_table": table, "reason": "NON_COMPACT_SOURCE_BLOCKED", "row_hash": r_hash, "source_path": sp}
                                    )
                                    skipped_rows_by_source_table[table] += 1
                                    continue
                                source_artifacts_used.add(sp)
                                merge_source_and_run(tx, sp, table, table, Path(sp).name)
                                loaded_rows_by_source_table[table] += 1
                                continue

                            if table == "coad_load_audit":
                                audit_key = f"COAD|audit|{r_hash}"
                                tx.run(
                                    """
                                    MERGE (d:Disease {code:$disease})
                                    SET d.name='Colon adenocarcinoma', d.updated_at=$updated_at
                                    MERGE (r:Run {run_id:$run_id})
                                    SET r.disease=$disease, r.stage='neo4j_brca_level_enrichment', r.updated_at=$updated_at
                                    MERGE (a:LoadAuditEvidence {disease:$disease, audit_key:$audit_key})
                                    SET a += $props, a.updated_at=$updated_at
                                    MERGE (a)-[:AUDITS_LOAD_FOR]->(d)
                                    MERGE (r)-[:PRODUCED_EVIDENCE]->(a)
                                    """,
                                    disease=disease,
                                    updated_at=ts,
                                    run_id=run_id,
                                    audit_key=audit_key,
                                    props=props,
                                )
                                if source_path:
                                    tx.run(
                                        """
                                        MATCH (a:LoadAuditEvidence {disease:$disease, audit_key:$audit_key})
                                        MATCH (s:SourceArtifact {path:$source_path})
                                        MERGE (a)-[:DERIVED_FROM_SOURCE]->(s)
                                        """,
                                        disease=disease,
                                        audit_key=audit_key,
                                        source_path=source_path,
                                    )
                                loaded_rows_by_source_table[table] += 1
                                continue

                    with session.begin_transaction() as tx:
                        tx.run(
                            """
                            MERGE (d:Disease {code:$code})
                            SET d.name=$name, d.updated_at=$updated_at
                            """,
                            code=disease,
                            name="Colon adenocarcinoma",
                            updated_at=ts,
                        )

                        if config_payload:
                            bio = config_payload.get("biology")
                            if isinstance(bio, dict):
                                genes = bio.get("marker_genes")
                                if not isinstance(genes, list):
                                    genes = bio.get("driver_genes")
                                subtypes = bio.get("subtypes")
                                if not isinstance(subtypes, list):
                                    subtypes = bio.get("molecular_subtypes")
                                if isinstance(genes, list):
                                    for g in genes:
                                        gs = safe_str(g)
                                        if not gs:
                                            continue
                                        tx.run(
                                            """
                                            MATCH (d:Disease {code:$code})
                                            MERGE (g:Gene {symbol:$symbol})
                                            MERGE (d)-[:HAS_DRIVER_GENE]->(g)
                                            """,
                                            code=disease,
                                            symbol=gs,
                                        )
                                if isinstance(subtypes, list):
                                    for st in subtypes:
                                        ss = safe_str(st)
                                        if not ss:
                                            continue
                                        tx.run(
                                            """
                                            MATCH (d:Disease {code:$code})
                                            MERGE (m:MolecularSubtype {name:$name})
                                            MERGE (d)-[:HAS_MOLECULAR_SUBTYPE]->(m)
                                            """,
                                            code=disease,
                                            name=ss,
                                        )

                        for table in REQUIRED_TABLES:
                            write_table_rows(tx, table, pg_rows.get(table, []))
                        tx.commit()

                    # Validation queries after write
                    node_queries = {
                        "Disease_COAD": "MATCH (d:Disease {code:$disease}) RETURN count(d) AS c",
                        "DrugCandidate_for_COAD": "MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:$disease}) RETURN count(c) AS c",
                        "CandidateScore": "MATCH (:CandidateScore {disease:$disease}) RETURN count(*) AS c",
                        "TierEvidence": "MATCH (:TierEvidence {disease:$disease}) RETURN count(*) AS c",
                        "FinalCandidateEvidence": "MATCH (:FinalCandidateEvidence {disease:$disease}) RETURN count(*) AS c",
                        "AdmetEvidence": "MATCH (:AdmetEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ExternalValidationEvidence": "MATCH (:ExternalValidationEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ModelEvidence": "MATCH (:ModelEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ModelDetailEvidence": "MATCH (:ModelDetailEvidence {disease:$disease}) RETURN count(*) AS c",
                        "EnsembleEvidence": "MATCH (:EnsembleEvidence {disease:$disease}) RETURN count(*) AS c",
                        "SourceArtifact": "MATCH (:SourceArtifact) RETURN count(*) AS c",
                        "LoadAuditEvidence": "MATCH (:LoadAuditEvidence {disease:$disease}) RETURN count(*) AS c",
                        "Run": "MATCH (:Run {disease:$disease}) RETURN count(*) AS c",
                    }
                    rel_queries = {
                        "CANDIDATE_FOR": "MATCH (:DrugCandidate)-[r:CANDIDATE_FOR]->(:Disease {code:$disease}) RETURN count(r) AS c",
                        "HAS_CANDIDATE_SCORE": "MATCH (:DrugCandidate)-[r:HAS_CANDIDATE_SCORE]->(:CandidateScore {disease:$disease}) RETURN count(r) AS c",
                        "HAS_TIER": "MATCH (:DrugCandidate)-[r:HAS_TIER]->(:TierEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SELECTED_AS_FINAL": "MATCH (:DrugCandidate)-[r:SELECTED_AS_FINAL]->(:FinalCandidateEvidence {disease:$disease}) RETURN count(r) AS c",
                        "HAS_ADMET_PROFILE": "MATCH (:DrugCandidate)-[r:HAS_ADMET_PROFILE]->(:AdmetEvidence {disease:$disease}) RETURN count(r) AS c",
                        "VALIDATED_BY_EXTERNAL_DATA": "MATCH (:ExternalValidationEvidence {disease:$disease})-[r:VALIDATED_BY_EXTERNAL_DATA]->(:Disease {code:$disease}) RETURN count(r) AS c",
                        "HAS_EXTERNAL_VALIDATION": "MATCH (:DrugCandidate)-[r:HAS_EXTERNAL_VALIDATION]->(:ExternalValidationEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SUPPORTED_BY_MODEL": "MATCH (:DrugCandidate)-[r:SUPPORTED_BY_MODEL]->(:ModelEvidence {disease:$disease}) RETURN count(r) AS c",
                        "HAS_DETAILED_MODEL_METRIC": "MATCH (:ModelEvidence {disease:$disease})-[r:HAS_DETAILED_MODEL_METRIC]->(:ModelDetailEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SUPPORTED_BY_ENSEMBLE": "MATCH (:DrugCandidate)-[r:SUPPORTED_BY_ENSEMBLE]->(:EnsembleEvidence {disease:$disease}) RETURN count(r) AS c",
                        "DERIVED_FROM_SOURCE": "MATCH ()-[r:DERIVED_FROM_SOURCE]->(:SourceArtifact) RETURN count(r) AS c",
                        "PRODUCED_EVIDENCE": "MATCH (:Run {disease:$disease})-[r:PRODUCED_EVIDENCE]->() RETURN count(r) AS c",
                        "AUDITS_LOAD_FOR": "MATCH (:LoadAuditEvidence {disease:$disease})-[r:AUDITS_LOAD_FOR]->(:Disease {code:$disease}) RETURN count(r) AS c",
                    }
                    for k, q in node_queries.items():
                        loaded_nodes_by_type[k] = int(session.run(q, disease=disease).single()["c"])
                    for k, q in rel_queries.items():
                        loaded_relationships_by_type[k] = int(session.run(q, disease=disease).single()["c"])
                driver.close()
                execute_performed = True
            except Exception as exc:  # noqa: BLE001
                failures.append(f"NEO4J_EXECUTE_FAILED:{exc}")
                execute_performed = False

    validation_decision_explanation = ""
    if failures:
        overall_status = "FAIL"
        validation_decision_explanation = "hard_failures_present"
    else:
        if args.execute:
            disease_ok = loaded_nodes_by_type.get("Disease_COAD", 0) >= 1
            drug_ok = loaded_nodes_by_type.get("DrugCandidate_for_COAD", 0) > 0
            source_ok = loaded_nodes_by_type.get("SourceArtifact", 0) > 0
            run_ok = loaded_nodes_by_type.get("Run", 0) > 0
            core_categories = [
                "CandidateScore",
                "FinalCandidateEvidence",
                "AdmetEvidence",
                "ExternalValidationEvidence",
                "ModelEvidence",
                "EnsembleEvidence",
                "LoadAuditEvidence",
            ]
            core_nonzero = sum(1 for k in core_categories if loaded_nodes_by_type.get(k, 0) > 0)
            if not (disease_ok and drug_ok and source_ok and run_ok and core_nonzero >= 3):
                failures.append(
                    "REQUIRED_VALIDATION_COUNTS_NOT_MET"
                    f"(disease_ok={disease_ok},drug_ok={drug_ok},source_ok={source_ok},run_ok={run_ok},core_nonzero={core_nonzero})"
                )

            tier_total = source_postgres_table_counts.get("drug_candidate_tier", 0)
            tier_missing_key = len(
                [s for s in skipped_rows if s.get("source_table") == "drug_candidate_tier" and s.get("reason") == "MISSING_DRUG_KEY"]
            )
            tier_missing_rank = len(
                [s for s in skipped_rows if s.get("source_table") == "drug_candidate_tier" and s.get("reason") == "MISSING_TIER_OR_RANK"]
            )
            tier_loaded = loaded_nodes_by_type.get("TierEvidence", 0)
            if tier_total > 0 and tier_usable_row_count > 0 and tier_loaded <= 0:
                failures.append(
                    "TIER_EVIDENCE_ZERO_WITH_USABLE_ROWS"
                    f"(tier_total={tier_total},tier_usable={tier_usable_row_count},tier_loaded={tier_loaded})"
                )
            elif tier_total > 0 and tier_usable_row_count == 0:
                warnings.append(
                    "TIER_ROWS_NOT_USABLE"
                    f"(tier_total={tier_total},missing_drug_key={tier_missing_key},missing_tier_or_rank={tier_missing_rank})"
                )

            if loaded_relationships_by_type.get("HAS_EXTERNAL_VALIDATION", 0) == 0 and loaded_nodes_by_type.get(
                "ExternalValidationEvidence", 0
            ) > 0:
                warnings.append("HAS_EXTERNAL_VALIDATION_ZERO_OPTIONAL_DRUG_LEVEL")
            if loaded_relationships_by_type.get("SUPPORTED_BY_MODEL", 0) == 0 and loaded_nodes_by_type.get("ModelEvidence", 0) > 0:
                warnings.append("SUPPORTED_BY_MODEL_ZERO_OPTIONAL_DRUG_LEVEL")
            if loaded_relationships_by_type.get("SUPPORTED_BY_ENSEMBLE", 0) == 0 and loaded_nodes_by_type.get("EnsembleEvidence", 0) > 0:
                warnings.append("SUPPORTED_BY_ENSEMBLE_ZERO_OPTIONAL_DRUG_LEVEL")

            if failures:
                overall_status = "FAIL"
                validation_decision_explanation = "required_checks_failed"
            elif warnings:
                overall_status = "PASS_WITH_WARNINGS"
                validation_decision_explanation = "core_evidence_loaded_optional_relationship_warnings_present"
            else:
                overall_status = "PASS"
                validation_decision_explanation = "core_evidence_loaded_all_required_checks_passed"
        else:
            overall_status = "PASS_WITH_WARNINGS" if warnings else "PASS"
            validation_decision_explanation = (
                "dry_run_with_warnings" if warnings else "dry_run_core_checks_ready_without_warnings"
            )

    # dry-run validation queries (read only) if no execute and reachable+auth available
    if not args.execute and neo4j_reachable:
        password = resolve_neo4j_password(args.neo4j_password_env)
        if password:
            try:
                from neo4j import GraphDatabase  # type: ignore

                driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, password))
                with driver.session(database=args.neo4j_database) as session:
                    node_queries = {
                        "Disease_COAD": "MATCH (d:Disease {code:$disease}) RETURN count(d) AS c",
                        "DrugCandidate_for_COAD": "MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:$disease}) RETURN count(c) AS c",
                        "CandidateScore": "MATCH (:CandidateScore {disease:$disease}) RETURN count(*) AS c",
                        "TierEvidence": "MATCH (:TierEvidence {disease:$disease}) RETURN count(*) AS c",
                        "FinalCandidateEvidence": "MATCH (:FinalCandidateEvidence {disease:$disease}) RETURN count(*) AS c",
                        "AdmetEvidence": "MATCH (:AdmetEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ExternalValidationEvidence": "MATCH (:ExternalValidationEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ModelEvidence": "MATCH (:ModelEvidence {disease:$disease}) RETURN count(*) AS c",
                        "ModelDetailEvidence": "MATCH (:ModelDetailEvidence {disease:$disease}) RETURN count(*) AS c",
                        "EnsembleEvidence": "MATCH (:EnsembleEvidence {disease:$disease}) RETURN count(*) AS c",
                        "SourceArtifact": "MATCH (:SourceArtifact) RETURN count(*) AS c",
                        "LoadAuditEvidence": "MATCH (:LoadAuditEvidence {disease:$disease}) RETURN count(*) AS c",
                        "Run": "MATCH (:Run {disease:$disease}) RETURN count(*) AS c",
                    }
                    rel_queries = {
                        "CANDIDATE_FOR": "MATCH (:DrugCandidate)-[r:CANDIDATE_FOR]->(:Disease {code:$disease}) RETURN count(r) AS c",
                        "HAS_CANDIDATE_SCORE": "MATCH (:DrugCandidate)-[r:HAS_CANDIDATE_SCORE]->(:CandidateScore {disease:$disease}) RETURN count(r) AS c",
                        "HAS_TIER": "MATCH (:DrugCandidate)-[r:HAS_TIER]->(:TierEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SELECTED_AS_FINAL": "MATCH (:DrugCandidate)-[r:SELECTED_AS_FINAL]->(:FinalCandidateEvidence {disease:$disease}) RETURN count(r) AS c",
                        "HAS_ADMET_PROFILE": "MATCH (:DrugCandidate)-[r:HAS_ADMET_PROFILE]->(:AdmetEvidence {disease:$disease}) RETURN count(r) AS c",
                        "VALIDATED_BY_EXTERNAL_DATA": "MATCH (:ExternalValidationEvidence {disease:$disease})-[r:VALIDATED_BY_EXTERNAL_DATA]->(:Disease {code:$disease}) RETURN count(r) AS c",
                        "HAS_EXTERNAL_VALIDATION": "MATCH (:DrugCandidate)-[r:HAS_EXTERNAL_VALIDATION]->(:ExternalValidationEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SUPPORTED_BY_MODEL": "MATCH (:DrugCandidate)-[r:SUPPORTED_BY_MODEL]->(:ModelEvidence {disease:$disease}) RETURN count(r) AS c",
                        "HAS_DETAILED_MODEL_METRIC": "MATCH (:ModelEvidence {disease:$disease})-[r:HAS_DETAILED_MODEL_METRIC]->(:ModelDetailEvidence {disease:$disease}) RETURN count(r) AS c",
                        "SUPPORTED_BY_ENSEMBLE": "MATCH (:DrugCandidate)-[r:SUPPORTED_BY_ENSEMBLE]->(:EnsembleEvidence {disease:$disease}) RETURN count(r) AS c",
                        "DERIVED_FROM_SOURCE": "MATCH ()-[r:DERIVED_FROM_SOURCE]->(:SourceArtifact) RETURN count(r) AS c",
                        "PRODUCED_EVIDENCE": "MATCH (:Run {disease:$disease})-[r:PRODUCED_EVIDENCE]->() RETURN count(r) AS c",
                        "AUDITS_LOAD_FOR": "MATCH (:LoadAuditEvidence {disease:$disease})-[r:AUDITS_LOAD_FOR]->(:Disease {code:$disease}) RETURN count(r) AS c",
                    }
                    for k, q in node_queries.items():
                        loaded_nodes_by_type[k] = int(session.run(q, disease=disease).single()["c"])
                    for k, q in rel_queries.items():
                        loaded_relationships_by_type[k] = int(session.run(q, disease=disease).single()["c"])
                driver.close()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"NEO4J_READ_VALIDATION_FAILED:{exc}")
        else:
            warnings.append("NEO4J_PASSWORD_MISSING_FOR_DRYRUN_VALIDATION")

    enrich_report = {
        "generated_at": now_iso(),
        "disease": disease,
        "execute_requested": bool(args.execute),
        "execute_performed": execute_performed,
        "postgres_status": pg_status,
        "source_postgres_table_counts": source_postgres_table_counts,
        "source_postgres_table_count_details": pg_count_details,
        "table_columns_by_source": table_columns_map,
        "loaded_nodes_by_type": loaded_nodes_by_type,
        "loaded_relationships_by_type": loaded_relationships_by_type,
        "loaded_rows_by_source_table": loaded_rows_by_source_table,
        "skipped_rows_by_source_table": skipped_rows_by_source_table,
        "skipped_rows": skipped_rows,
        "skipped_rows_examples_first_30": skipped_rows[:30],
        "skipped_rows_by_reason": {
            k: len([s for s in skipped_rows if s.get("reason") == k])
            for k in sorted({safe_str(s.get("reason")) for s in skipped_rows})
        },
        "source_artifacts_used": sorted(source_artifacts_used),
        "guardrail_status": guardrail_status,
        "no_admet_check": guardrail_status.get("no_admet_guardrail", False),
        "tier_analysis": {
            "tier_total_rows": source_postgres_table_counts.get("drug_candidate_tier", 0),
            "tier_usable_rows": tier_usable_row_count,
            "tier_loaded_rows": tier_loaded_row_count,
        },
        "failures": failures,
        "warnings": warnings,
        "blockers": failures,
        "validation_decision_explanation": validation_decision_explanation,
        "overall_status": overall_status,
    }

    validation_report = {
        "generated_at": now_iso(),
        "disease": disease,
        "execute_requested": bool(args.execute),
        "execute_performed": execute_performed,
        "node_counts": loaded_nodes_by_type,
        "relationship_counts": loaded_relationships_by_type,
        "source_postgres_table_counts": source_postgres_table_counts,
        "table_columns_by_source": table_columns_map,
        "guardrail_status": guardrail_status,
        "source_artifacts_used": sorted(source_artifacts_used),
        "skipped_rows": skipped_rows,
        "skipped_rows_examples_first_30": skipped_rows[:30],
        "skipped_rows_by_source_table": skipped_rows_by_source_table,
        "skipped_rows_by_reason": enrich_report.get("skipped_rows_by_reason", {}),
        "failures": failures,
        "warnings": warnings,
        "blockers": failures,
        "validation_decision_explanation": validation_decision_explanation,
        "overall_status": overall_status,
    }

    write_reports(enrich_json_path, enrich_md_path, val_json_path, val_md_path, enrich_report, validation_report)

    print(f"disease={disease}")
    print(f"execute_requested={str(bool(args.execute)).lower()}")
    print(f"execute_performed={str(execute_performed).lower()}")
    print(f"postgres_status={pg_status}")
    print(f"neo4j_reachable={str(neo4j_reachable).lower()}")
    print(f"loaded_nodes_by_type={json.dumps(loaded_nodes_by_type, ensure_ascii=False)}")
    print(f"loaded_relationships_by_type={json.dumps(loaded_relationships_by_type, ensure_ascii=False)}")
    print(
        f"skipped_rows_by_reason={json.dumps(enrich_report.get('skipped_rows_by_reason', {}), ensure_ascii=False)}"
    )
    print(f"overall_status={overall_status}")
    print(f"enrichment_report_json={enrich_json_path}")
    print(f"enrichment_report_md={enrich_md_path}")
    print(f"validation_report_json={val_json_path}")
    print(f"validation_report_md={val_md_path}")

    if overall_status == "FAIL":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
