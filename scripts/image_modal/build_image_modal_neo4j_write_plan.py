#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_TABLE = "image_modal_asset"
TARGET_GRAPH = "Neo4j"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build dry-run Neo4j HAS_IMAGE_MODAL write-plan from PostgreSQL image_modal_asset."
    )
    p.add_argument("--disease", default="BRCA")
    p.add_argument(
        "--out-json",
        default="outputs/config_validation/brca_image_modal_neo4j_write_plan_preview.json",
    )
    p.add_argument(
        "--out-md",
        default="docs/brca_image_modal_neo4j_write_plan_preview.md",
    )
    p.add_argument(
        "--project-root",
        default=None,
        help="Optional project root for resolving relative output paths. Defaults to current working directory.",
    )
    p.add_argument("--db-host", default="localhost")
    p.add_argument("--db-port", default=5432, type=int)
    p.add_argument("--db-name", default="Drug")
    p.add_argument("--db-user", default="Drug")
    return p.parse_args()


def resolve_under_root(path_like: str, root: Path) -> Path:
    p = Path(path_like)
    return p if p.is_absolute() else (root / p)


def read_candidates(
    disease_code: str,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
) -> list[dict[str, Any]]:
    if not os.getenv("PGPASSWORD") and not os.getenv("PGPASSFILE"):
        raise SystemExit("PGPASSWORD or PGPASSFILE is required for PostgreSQL read.")

    import psycopg2  # type: ignore

    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
    )
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT disease_code, s3_uri, file_name, file_ext, inferred_asset_type, size_bytes, load_status
                FROM image_modal_asset
                WHERE disease_code = %s
                  AND inferred_asset_type = 'image'
                  AND load_status = 'REGISTERED'
                ORDER BY file_name
                """,
                (disease_code,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    candidates: list[dict[str, Any]] = []
    for r in rows:
        candidates.append(
            {
                "disease_code": r[0],
                "s3_uri": r[1],
                "file_name": r[2],
                "file_ext": r[3],
                "inferred_asset_type": r[4],
                "size_bytes": int(r[5]) if r[5] is not None else None,
                "load_status": r[6],
                "modality": "image",
                "source": "postgres.image_modal_asset",
            }
        )
    return candidates


def build_report(disease_code: str, candidates: list[dict[str, Any]], project_root: Path) -> dict[str, Any]:
    planned_nodes: list[dict[str, Any]] = [
        {
            "label": "Disease",
            "code": disease_code,
            "name": disease_code,
            "created_by": "image_modal_loader",
        }
    ]
    for c in candidates:
        planned_nodes.append(
            {
                "label": "ImageModalAsset",
                "s3_uri": c["s3_uri"],
                "file_name": c["file_name"],
                "file_ext": c["file_ext"],
                "inferred_asset_type": c["inferred_asset_type"],
                "modality": "image",
                "size_bytes": c["size_bytes"],
                "load_status": c["load_status"],
                "source": "postgres.image_modal_asset",
            }
        )

    planned_relationships: list[dict[str, Any]] = []
    for c in candidates:
        planned_relationships.append(
            {
                "from": {"label": "Disease", "code": disease_code},
                "type": "HAS_IMAGE_MODAL",
                "to": {"label": "ImageModalAsset", "s3_uri": c["s3_uri"]},
                "preview": f"{disease_code} - HAS_IMAGE_MODAL -> {c['file_name']}",
            }
        )

    cypher_template = """MERGE (d:Disease {code: $disease_code})
ON CREATE SET
  d.name = $disease_code,
  d.created_by = 'image_modal_loader'

MERGE (img:ImageModalAsset {s3_uri: $s3_uri})
SET
  img.file_name = $file_name,
  img.file_ext = $file_ext,
  img.inferred_asset_type = $inferred_asset_type,
  img.modality = 'image',
  img.size_bytes = $size_bytes,
  img.load_status = $load_status,
  img.source = 'postgres.image_modal_asset',
  img.updated_at = datetime()

MERGE (d)-[:HAS_IMAGE_MODAL]->(img)"""

    overall_status = "PASS" if len(candidates) == 3 else "FAIL"
    return {
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "disease_code": disease_code,
        "source_table": SOURCE_TABLE,
        "target_graph": TARGET_GRAPH,
        "execute_neo4j": False,
        "candidate_count": len(candidates),
        "planned_node_count": len(planned_nodes),
        "planned_relationship_count": len(planned_relationships),
        "planned_nodes": planned_nodes,
        "planned_relationships": planned_relationships,
        "cypher_templates": [
            {
                "name": "disease_image_modal_merge",
                "template": cypher_template,
            }
        ],
        "guardrail_confirmation": {
            "Neo4j write was not performed.": True,
            "PostgreSQL write was not performed.": True,
            "PostgreSQL was read only.": True,
            "S3 object download was not performed.": True,
            "Image binary was not processed.": True,
            "Agentic AI image interpretation was not performed.": True,
        },
        "overall_status": overall_status,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# BRCA Image Modal Neo4j Write-Plan Preview (Dry-Run)")
    lines.append("")
    lines.append(f"- project_root: `{report['project_root']}`")
    lines.append(f"- disease_code: {report['disease_code']}")
    lines.append(f"- source_table: {report['source_table']}")
    lines.append(f"- target_graph: {report['target_graph']}")
    lines.append(f"- execute_neo4j: {str(report['execute_neo4j']).lower()}")
    lines.append(f"- candidate_count: {report['candidate_count']}")
    lines.append(f"- planned_node_count: {report['planned_node_count']}")
    lines.append(f"- planned_relationship_count: {report['planned_relationship_count']}")
    lines.append(f"- overall_status: {report['overall_status']}")
    lines.append("")
    lines.append("## Planned Relationships")
    for rel in report["planned_relationships"]:
        lines.append(f"- {rel['preview']}")
    if not report["planned_relationships"]:
        lines.append("- none")
    lines.append("")
    lines.append("## Cypher Template")
    lines.append("```cypher")
    lines.append(report["cypher_templates"][0]["template"])
    lines.append("```")
    lines.append("")
    lines.append("## Guardrail Confirmation")
    for k in report["guardrail_confirmation"].keys():
        lines.append(f"- {k}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    disease = str(args.disease).upper().strip()
    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
    out_json = resolve_under_root(args.out_json, project_root)
    out_md = resolve_under_root(args.out_md, project_root)

    candidates = read_candidates(
        disease_code=disease,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
    )
    report = build_report(disease, candidates, project_root)
    write_json(out_json, report)
    write_markdown(out_md, report)

    print(f"project_root={report['project_root']}")
    print(f"postgres_read_success=true")
    print(f"candidate_count={report['candidate_count']}")
    print(f"planned_node_count={report['planned_node_count']}")
    print(f"planned_relationship_count={report['planned_relationship_count']}")
    print(f"execute_neo4j={str(report['execute_neo4j']).lower()}")
    print(f"overall_status={report['overall_status']}")
    print(f"out_json={out_json}")
    print(f"out_md={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
