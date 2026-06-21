from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

import boto3  # type: ignore
from neo4j.exceptions import Neo4jError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db.neo4j import get_neo4j_driver


DISEASE_CODE = "COAD"
SOURCE_NAME = "S3_COAD_IMAGE_MODAL_DEEP_EDGE"
S3_URIS = [
    "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/0.Image_modal_COAD/step_im4b/coad_top30_drug_cluster_hypotheses.csv",
    "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/0.Image_modal_COAD/step_im4c/coad_final_drug_cluster_recommendations.csv",
    "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/0.Image_modal_COAD/step_im4c/coad_top30_4tier_classification.csv",
]
REL_DISEASE_CANDIDATE = ("HAS_CANDIDATE", "CANDIDATE_FOR", "SELECTED_AS_FINAL")
OUTPUT_JSON = Path("outputs/config_validation/coad_s3_deep_edge_load_report.json")
OUTPUT_MD = Path("docs/coad_s3_deep_edge_load_report.md")

DRUG_COL_CANDIDATES = ("drug_name", "DRUG_NAME", "drug_name_display")
TARGET_COL_CANDIDATES = ("target", "TARGET")
PATHWAY_COL_CANDIDATES = ("target_pathway", "TARGET_PATHWAY")

# Broad mechanism-like terms that must not be treated as Gene symbols.
NON_GENE_TARGET_TERMS = {
    "MICROTUBULE STABILISER",
    "MICROTUBULE DESTABILISER",
    "RNA POLYMERASE",
    "OTHER",
    "MITOSIS",
    "DNA REPLICATION",
}


@dataclass(frozen=True)
class EvidenceEdge:
    disease: str
    source_file: str
    drug_name: str
    candidate_key: str
    target_raw: str
    target_norm: str
    target_kind: str  # gene | target
    pathway_raw: str
    pathway_norm: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"invalid_s3_uri:{uri}")
    bucket, key = uri[5:].split("/", 1)
    return bucket, key


def _read_s3_text(s3: Any, s3_uri: str) -> str:
    bucket, key = _parse_s3_uri(s3_uri)
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8-sig", errors="replace")


def _read_rows_from_s3_csv(s3: Any, s3_uri: str) -> list[dict[str, Any]]:
    text = _read_s3_text(s3, s3_uri)
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _norm_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_key(value: Any) -> str:
    text = str(value or "").strip().upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def _split_values(value: Any) -> list[str]:
    raw = _norm_space(value)
    if not raw:
        return []
    tokens = re.split(r"[;,|/]+", raw)
    out: list[str] = []
    for token in tokens:
        norm = _norm_space(token)
        if not norm:
            continue
        if norm.upper() in {"NA", "N/A", "NONE", "NULL", "UNKNOWN", "NAN", "-"}:
            continue
        out.append(norm)
    return out


def _first_present(row: dict[str, Any], candidates: tuple[str, ...]) -> tuple[str | None, str]:
    for key in candidates:
        if key in row and _norm_space(row.get(key)):
            return key, _norm_space(row.get(key))
    return None, ""


def _is_gene_like_symbol(token: str) -> bool:
    value = _norm_space(token)
    if not value:
        return False
    upper = value.upper()
    if upper in NON_GENE_TARGET_TERMS:
        return False
    if " " in upper:
        return False
    if len(upper) < 2 or len(upper) > 20:
        return False
    # HGNC-like: uppercase letters/digits with optional dashes.
    if not re.fullmatch(r"[A-Z][A-Z0-9-]*", upper):
        return False
    # Generic non-symbol phrases should not pass even if uppercased.
    if upper in {"PATHWAY", "TARGET", "GENE", "PROTEIN", "SIGNALING"}:
        return False
    return True


def _build_evidence_edges() -> tuple[list[EvidenceEdge], dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "rows_scanned": 0,
        "rows_with_drug": 0,
        "rows_with_target": 0,
        "rows_with_pathway": 0,
        "rows_skipped_missing_drug": 0,
        "rows_skipped_missing_target": 0,
        "input_files": [],
    }
    dedupe_keys: set[tuple[str, str, str, str, str]] = set()
    edges: list[EvidenceEdge] = []
    s3 = boto3.client("s3")

    for s3_uri in S3_URIS:
        file_diag: dict[str, Any] = {
            "source_file": s3_uri,
            "rows_scanned": 0,
            "rows_with_drug": 0,
            "rows_with_target": 0,
            "rows_with_pathway": 0,
            "edges_planned": 0,
            "dedup_dropped": 0,
            "detected_columns": [],
            "used_columns": {"drug": None, "target": None, "pathway": None},
            "error": None,
        }
        try:
            rows = _read_rows_from_s3_csv(s3, s3_uri)
            file_diag["rows_scanned"] = len(rows)
            file_diag["detected_columns"] = sorted({k for row in rows for k in row.keys()})
            for row in rows:
                diagnostics["rows_scanned"] += 1
                drug_col, drug_value = _first_present(row, DRUG_COL_CANDIDATES)
                target_col, target_value = _first_present(row, TARGET_COL_CANDIDATES)
                pathway_col, pathway_value = _first_present(row, PATHWAY_COL_CANDIDATES)
                if file_diag["used_columns"]["drug"] is None and drug_col:
                    file_diag["used_columns"]["drug"] = drug_col
                if file_diag["used_columns"]["target"] is None and target_col:
                    file_diag["used_columns"]["target"] = target_col
                if file_diag["used_columns"]["pathway"] is None and pathway_col:
                    file_diag["used_columns"]["pathway"] = pathway_col

                if not drug_value:
                    diagnostics["rows_skipped_missing_drug"] += 1
                    continue
                diagnostics["rows_with_drug"] += 1
                file_diag["rows_with_drug"] += 1

                targets = _split_values(target_value)
                if not targets:
                    diagnostics["rows_skipped_missing_target"] += 1
                    continue
                diagnostics["rows_with_target"] += 1
                file_diag["rows_with_target"] += 1

                pathways = _split_values(pathway_value)
                if pathways:
                    diagnostics["rows_with_pathway"] += 1
                    file_diag["rows_with_pathway"] += 1
                else:
                    pathways = [""]

                candidate_key = _norm_key(drug_value)
                for target_token in targets:
                    target_norm = _norm_space(target_token).upper()
                    target_kind = "gene" if _is_gene_like_symbol(target_norm) else "target"
                    for pathway_token in pathways:
                        pathway_norm = _norm_space(pathway_token).upper()
                        dedupe_key = (DISEASE_CODE, candidate_key, target_norm, pathway_norm, s3_uri)
                        if dedupe_key in dedupe_keys:
                            file_diag["dedup_dropped"] += 1
                            continue
                        dedupe_keys.add(dedupe_key)
                        edges.append(
                            EvidenceEdge(
                                disease=DISEASE_CODE,
                                source_file=s3_uri,
                                drug_name=drug_value,
                                candidate_key=candidate_key,
                                target_raw=target_token,
                                target_norm=target_norm,
                                target_kind=target_kind,
                                pathway_raw=pathway_token,
                                pathway_norm=pathway_norm,
                            )
                        )
                        file_diag["edges_planned"] += 1
        except Exception as exc:
            file_diag["error"] = f"{exc.__class__.__name__}: {str(exc)}"
        diagnostics["input_files"].append(file_diag)

    return edges, diagnostics


def _load_to_neo4j(evidence_edges: list[EvidenceEdge], execute: bool) -> dict[str, Any]:
    report: dict[str, Any] = {
        "candidate_drug_count": 0,
        "candidate_keys_matched": 0,
        "candidate_keys_unmatched": 0,
        "planned_candidate_gene_edges": 0,
        "planned_candidate_target_edges": 0,
        "planned_gene_pathway_edges": 0,
        "planned_target_pathway_edges": 0,
        "merged_candidate_gene_edges": 0,
        "merged_candidate_target_edges": 0,
        "merged_gene_pathway_edges": 0,
        "merged_target_pathway_edges": 0,
        "skipped_rows": {
            "missing_drug_name": 0,
            "no_matching_candidatedrug_node": 0,
            "no_gene_evidence": 0,
            "gene_value_empty": 0,
            "gene_node_missing": 0,
            "dry_run_only": 0,
        },
        "errors": [],
    }
    if not evidence_edges:
        return report

    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            rows = list(
                session.run(
                    """
                    MATCH (d:Disease)-[r]-(c)
                    WHERE toUpper(coalesce(d.code, d.name, d.disease, d.label, '')) = $disease
                      AND type(r) IN $rels
                      AND any(l IN labels(c) WHERE l IN ['CandidateDrug', 'DrugCandidate', 'Drug', 'Candidate', 'FinalCandidate'])
                    RETURN DISTINCT elementId(c) AS element_id,
                                    coalesce(c.drug_name_norm, c.drug_name, c.name, c.drug, c.compound_name, c.drug_key, c.drug_id, c.id) AS key_text
                    """,
                    disease=DISEASE_CODE,
                    rels=list(REL_DISEASE_CANDIDATE),
                    timeout=20,
                )
            )
            candidate_key_map: dict[str, list[str]] = {}
            for row in rows:
                element_id = str(row.get("element_id") or "").strip()
                key = _norm_key(row.get("key_text"))
                if element_id and key:
                    candidate_key_map.setdefault(key, []).append(element_id)
            report["candidate_drug_count"] = len(rows)

            gene_symbols_needed = sorted({e.target_norm for e in evidence_edges if e.target_kind == "gene"})
            existing_gene_symbols: set[str] = set()
            if gene_symbols_needed:
                gene_rows = list(
                    session.run(
                        """
                        UNWIND $symbols AS symbol
                        MATCH (g:Gene)
                        WHERE toUpper(coalesce(g.symbol, '')) = symbol
                        RETURN DISTINCT toUpper(coalesce(g.symbol, '')) AS symbol
                        """,
                        symbols=gene_symbols_needed,
                        timeout=20,
                    )
                )
                existing_gene_symbols = {str(r.get("symbol") or "").upper() for r in gene_rows}

            cand_gene_payload: list[dict[str, Any]] = []
            cand_target_payload: list[dict[str, Any]] = []
            gene_pathway_payload: list[dict[str, Any]] = []
            target_pathway_payload: list[dict[str, Any]] = []

            matched_keys: set[str] = set()
            unmatched_keys: set[str] = set()

            for edge in evidence_edges:
                if not edge.candidate_key:
                    report["skipped_rows"]["missing_drug_name"] += 1
                    continue
                candidate_element_ids = candidate_key_map.get(edge.candidate_key, [])
                if not candidate_element_ids:
                    report["skipped_rows"]["no_matching_candidatedrug_node"] += 1
                    unmatched_keys.add(edge.candidate_key)
                    continue
                matched_keys.add(edge.candidate_key)

                if edge.target_kind == "gene":
                    if not edge.target_norm:
                        report["skipped_rows"]["gene_value_empty"] += 1
                        continue
                    if edge.target_norm not in existing_gene_symbols:
                        report["skipped_rows"]["gene_node_missing"] += 1
                        continue
                    for element_id in candidate_element_ids:
                        cand_gene_payload.append(
                            {
                                "candidate_element_id": element_id,
                                "disease": edge.disease,
                                "source": SOURCE_NAME,
                                "source_file": edge.source_file,
                                "drug_name": edge.drug_name,
                                "target_raw": edge.target_raw,
                                "target_norm": edge.target_norm,
                                "pathway_raw": edge.pathway_raw,
                            }
                        )
                    if edge.pathway_norm:
                        gene_pathway_payload.append(
                            {
                                "disease": edge.disease,
                                "source": SOURCE_NAME,
                                "source_file": edge.source_file,
                                "drug_name": edge.drug_name,
                                "target_raw": edge.target_raw,
                                "target_norm": edge.target_norm,
                                "pathway_raw": edge.pathway_raw,
                                "pathway_norm": edge.pathway_norm,
                            }
                        )
                else:
                    for element_id in candidate_element_ids:
                        cand_target_payload.append(
                            {
                                "candidate_element_id": element_id,
                                "disease": edge.disease,
                                "source": SOURCE_NAME,
                                "source_file": edge.source_file,
                                "drug_name": edge.drug_name,
                                "target_raw": edge.target_raw,
                                "target_norm": edge.target_norm,
                                "pathway_raw": edge.pathway_raw,
                            }
                        )
                    if edge.pathway_norm:
                        target_pathway_payload.append(
                            {
                                "disease": edge.disease,
                                "source": SOURCE_NAME,
                                "source_file": edge.source_file,
                                "drug_name": edge.drug_name,
                                "target_raw": edge.target_raw,
                                "target_norm": edge.target_norm,
                                "pathway_raw": edge.pathway_raw,
                                "pathway_norm": edge.pathway_norm,
                            }
                        )

            # Explicit counter required by diagnostics schema; we classify non-gene targets separately.
            report["skipped_rows"]["no_gene_evidence"] = len(cand_target_payload)

            # Deduplicate planned merge payloads exactly by relationship evidence identity.
            def _unique_rows(rows_in: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
                seen: set[tuple[Any, ...]] = set()
                out: list[dict[str, Any]] = []
                for item in rows_in:
                    k = tuple(item.get(key) for key in keys)
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append(item)
                return out

            cand_gene_payload = _unique_rows(
                cand_gene_payload,
                ("candidate_element_id", "target_norm", "source_file", "pathway_raw", "drug_name", "target_raw"),
            )
            cand_target_payload = _unique_rows(
                cand_target_payload,
                ("candidate_element_id", "target_norm", "source_file", "pathway_raw", "drug_name", "target_raw"),
            )
            gene_pathway_payload = _unique_rows(
                gene_pathway_payload,
                ("target_norm", "pathway_norm", "source_file", "drug_name", "target_raw", "pathway_raw"),
            )
            target_pathway_payload = _unique_rows(
                target_pathway_payload,
                ("target_norm", "pathway_norm", "source_file", "drug_name", "target_raw", "pathway_raw"),
            )

            report["candidate_keys_matched"] = len(matched_keys)
            report["candidate_keys_unmatched"] = len(unmatched_keys)
            report["planned_candidate_gene_edges"] = len(cand_gene_payload)
            report["planned_candidate_target_edges"] = len(cand_target_payload)
            report["planned_gene_pathway_edges"] = len(gene_pathway_payload)
            report["planned_target_pathway_edges"] = len(target_pathway_payload)

            if not execute:
                report["skipped_rows"]["dry_run_only"] = (
                    report["planned_candidate_gene_edges"]
                    + report["planned_candidate_target_edges"]
                    + report["planned_gene_pathway_edges"]
                    + report["planned_target_pathway_edges"]
                )
                return report

            if cand_gene_payload:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (c) WHERE elementId(c) = row.candidate_element_id
                    MATCH (g:Gene) WHERE toUpper(coalesce(g.symbol, '')) = row.target_norm
                    MERGE (c)-[r:TARGETS {
                        disease: row.disease,
                        source: row.source,
                        source_file: row.source_file,
                        drug_name: row.drug_name,
                        target_raw: row.target_raw,
                        pathway_raw: row.pathway_raw
                    }]->(g)
                      ON CREATE SET r.created_at = datetime()
                    SET r.updated_at = datetime()
                    """,
                    rows=cand_gene_payload,
                    timeout=90,
                )
                report["merged_candidate_gene_edges"] = len(cand_gene_payload)

            if cand_target_payload:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (c) WHERE elementId(c) = row.candidate_element_id
                    MERGE (t:Target {name: row.target_norm})
                      ON CREATE SET t.created_at = datetime()
                    SET t.updated_at = datetime()
                    MERGE (c)-[r:HAS_TARGET {
                        disease: row.disease,
                        source: row.source,
                        source_file: row.source_file,
                        drug_name: row.drug_name,
                        target_raw: row.target_raw,
                        pathway_raw: row.pathway_raw
                    }]->(t)
                      ON CREATE SET r.created_at = datetime()
                    SET r.updated_at = datetime()
                    """,
                    rows=cand_target_payload,
                    timeout=90,
                )
                report["merged_candidate_target_edges"] = len(cand_target_payload)

            if gene_pathway_payload:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (g:Gene) WHERE toUpper(coalesce(g.symbol, '')) = row.target_norm
                    MERGE (p:Pathway {name: row.pathway_norm})
                      ON CREATE SET p.created_at = datetime()
                    SET p.updated_at = datetime()
                    MERGE (g)-[r:INVOLVED_IN {
                        disease: row.disease,
                        source: row.source,
                        source_file: row.source_file,
                        drug_name: row.drug_name,
                        target_raw: row.target_raw,
                        pathway_raw: row.pathway_raw
                    }]->(p)
                      ON CREATE SET r.created_at = datetime()
                    SET r.updated_at = datetime()
                    """,
                    rows=gene_pathway_payload,
                    timeout=90,
                )
                report["merged_gene_pathway_edges"] = len(gene_pathway_payload)

            if target_pathway_payload:
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (t:Target {name: row.target_norm})
                      ON CREATE SET t.created_at = datetime()
                    SET t.updated_at = datetime()
                    MERGE (p:Pathway {name: row.pathway_norm})
                      ON CREATE SET p.created_at = datetime()
                    SET p.updated_at = datetime()
                    MERGE (t)-[r:ASSOCIATED_WITH {
                        disease: row.disease,
                        source: row.source,
                        source_file: row.source_file,
                        drug_name: row.drug_name,
                        target_raw: row.target_raw,
                        pathway_raw: row.pathway_raw
                    }]->(p)
                      ON CREATE SET r.created_at = datetime()
                    SET r.updated_at = datetime()
                    """,
                    rows=target_pathway_payload,
                    timeout=90,
                )
                report["merged_target_pathway_edges"] = len(target_pathway_payload)
    except Neo4jError as exc:
        report["errors"].append(f"Neo4jError: {exc.__class__.__name__}: {str(exc)}")
    except Exception as exc:
        report["errors"].append(f"Error: {exc.__class__.__name__}: {str(exc)}")
    return report


def _validate_obsidian_via_http() -> dict[str, Any]:
    out: dict[str, Any] = {
        "path": "http://127.0.0.1:8000/api/graph/COAD/obsidian",
        "http_status": None,
        "checks": {},
        "counts": {},
        "diagnostics": {},
        "error": None,
    }
    try:
        req = urlrequest.Request(out["path"], method="GET")
        with urlrequest.urlopen(req, timeout=20) as resp:
            out["http_status"] = int(resp.status)
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
        edges = payload.get("edges") if isinstance(payload.get("edges"), list) else []
        diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}

        node_types = [str(n.get("type", "")) for n in nodes if isinstance(n, dict)]
        out["counts"] = {
            "candidate_nodes": sum(1 for t in node_types if t == "CandidateDrug"),
            "gene_nodes": sum(1 for t in node_types if t == "Gene"),
            "target_nodes": sum(1 for t in node_types if t == "Target"),
            "pathway_nodes": sum(1 for t in node_types if t == "Pathway"),
            "total_edges": len(edges),
        }
        out["diagnostics"] = diagnostics

        candidate_gene_edge_count = int(diagnostics.get("candidate_gene_edge_count") or 0)
        target_pathway_edge_count = int(diagnostics.get("target_pathway_edge_count") or 0)
        gene_pathway_edge_count = int(diagnostics.get("gene_pathway_edge_count") or 0)
        out["checks"] = {
            "candidate_nodes_positive": int(out["counts"]["candidate_nodes"]) > 0,
            "gene_nodes_positive_when_possible": int(out["counts"]["gene_nodes"]) > 0,
            "target_nodes_positive_when_possible": int(out["counts"]["target_nodes"]) > 0,
            "pathway_nodes_positive": int(out["counts"]["pathway_nodes"]) > 0,
            "candidate_gene_edge_count_positive": candidate_gene_edge_count > 0,
            "target_or_pathway_edges_positive": (target_pathway_edge_count > 0) or (gene_pathway_edge_count > 0),
        }
    except urlerror.URLError as exc:
        out["error"] = f"URLError: {str(exc)}"
    except Exception as exc:
        out["error"] = f"{exc.__class__.__name__}: {str(exc)}"
    return out


def run(execute: bool, validate_obsidian: bool) -> dict[str, Any]:
    evidence_edges, s3_diag = _build_evidence_edges()
    load_diag = _load_to_neo4j(evidence_edges=evidence_edges, execute=execute)
    report: dict[str, Any] = {
        "generated_at_utc": _utc_now(),
        "mode": "execute" if execute else "dry-run",
        "disease": DISEASE_CODE,
        "source": SOURCE_NAME,
        "source_files": S3_URIS,
        "input_diagnostics": s3_diag,
        "evidence_edge_rows": len(evidence_edges),
        "gene_like_target_rows": sum(1 for e in evidence_edges if e.target_kind == "gene"),
        "mechanism_like_target_rows": sum(1 for e in evidence_edges if e.target_kind == "target"),
        "neo4j_load_diagnostics": load_diag,
        "obsidian_validation": {},
    }
    if validate_obsidian:
        report["obsidian_validation"] = _validate_obsidian_via_http()
    return report


def _write_markdown(report: dict[str, Any], out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# COAD S3 Deep Edge Load Report")
    lines.append("")
    lines.append(f"- Generated (UTC): {report.get('generated_at_utc')}")
    lines.append(f"- Mode: `{report.get('mode')}`")
    lines.append(f"- Disease: `{report.get('disease')}`")
    lines.append(f"- Source: `{report.get('source')}`")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    for s3_uri in report.get("source_files", []):
        lines.append(f"- `{s3_uri}`")
    lines.append("")
    lines.append("## Input Diagnostics")
    lines.append("")
    lines.append(f"- Summary: `{report.get('input_diagnostics')}`")
    lines.append("")
    lines.append("## Neo4j Load Diagnostics")
    lines.append("")
    lines.append(f"- Summary: `{report.get('neo4j_load_diagnostics')}`")
    lines.append("")
    obs = report.get("obsidian_validation") or {}
    if obs:
        lines.append("## Obsidian Validation")
        lines.append("")
        lines.append(f"- HTTP: `{obs.get('http_status')}`")
        lines.append(f"- Counts: `{obs.get('counts')}`")
        lines.append(f"- Diagnostics: `{obs.get('diagnostics')}`")
        lines.append(f"- Checks: `{obs.get('checks')}`")
        if obs.get("error"):
            lines.append(f"- Error: `{obs.get('error')}`")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load COAD S3 deep evidence-backed edges into Neo4j without fabricating links.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Inspect inputs and report planned merges only (default).")
    mode.add_argument("--execute", action="store_true", help="Execute Neo4j MERGE writes.")
    parser.add_argument("--validate-obsidian", action="store_true", help="Validate /api/graph/COAD/obsidian via HTTP after run.")
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON, help=f"Output JSON path (default: {OUTPUT_JSON})")
    parser.add_argument("--output-md", type=Path, default=OUTPUT_MD, help=f"Output markdown path (default: {OUTPUT_MD})")
    args = parser.parse_args()

    execute = bool(args.execute)
    report = run(execute=execute, validate_obsidian=bool(args.validate_obsidian))

    json_path = Path(args.output_json)
    md_path = Path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(report, md_path)
    print(str(json_path))
    print(str(md_path))


if __name__ == "__main__":
    main()
