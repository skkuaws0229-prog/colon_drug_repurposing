from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import app

CASES = ["BRAC", "COAD", "COLON", "LUAD", "STAD", "HNSC", "LIHC", "PAAD", "LIVER"]
EXPECTED_NORMALIZED = {
    "BRAC": "BRCA",
    "COAD": "COAD",
    "COLON": "COAD",
    "LUAD": "LUAD",
    "STAD": "STAD",
    "HNSC": "HNSC",
    "LIHC": "LIHC",
    "PAAD": "PAAD",
    "LIVER": "LIHC",
}
ALLOWED_NODE_TYPES = {"Disease", "CandidateDrug", "Gene", "Pathway", "Target", "Protein"}


def _route_registered(path: str) -> bool:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path:
            return True
    return False


def _keys_exist(payload: dict[str, Any]) -> dict[str, bool]:
    required = [
        "disease",
        "requested_disease",
        "normalized_disease",
        "view",
        "source",
        "nodes",
        "links",
        "edges",
        "count",
        "legend",
        "warnings",
        "diagnostics",
    ]
    return {key: key in payload for key in required}


def _contains_text(payload: Any, token: str) -> bool:
    return token.upper() in json.dumps(payload, ensure_ascii=False).upper()


def _validate_case(alias: str, payload: dict[str, Any]) -> dict[str, Any]:
    expected = EXPECTED_NORMALIZED[alias]
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    links = payload.get("links") if isinstance(payload.get("links"), list) else []
    edges = payload.get("edges") if isinstance(payload.get("edges"), list) else []
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    keys_present = _keys_exist(payload)

    count = payload.get("count") if isinstance(payload.get("count"), dict) else {}
    count_ok = count.get("nodes") == len(nodes) and count.get("edges") == len(edges)
    links_edges_identical = links == edges
    no_pg_fallback_warning = all("GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES" not in str(w) for w in warnings)

    normalized_ok = (
        str(payload.get("disease", "")) == expected
        and str(payload.get("normalized_disease", "")) == expected
        and str(payload.get("requested_disease", "")) == alias
    )
    view_source_ok = str(payload.get("view", "")) == "obsidian" and str(payload.get("source", "")) == "neo4j"

    auth_related_signals = [
        str(w) for w in warnings if "auth" in str(w).lower() or "authentication" in str(w).lower()
    ]
    auth_warning_contract_ok = True
    if auth_related_signals:
        auth_warning_contract_ok = "NEO4J_AUTH_FAILED" in [str(w) for w in warnings]

    node_types = {
        str(node.get("type", "")).strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("type", "")).strip()
    }
    node_types_allowed = node_types.issubset(ALLOWED_NODE_TYPES)
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}

    disease_drug_row_count = int(diagnostics.get("disease_drug_row_count") or 0)
    drug_gene_row_count = int(diagnostics.get("drug_gene_row_count") or 0)

    candidate_node_count = sum(1 for n in nodes if isinstance(n, dict) and str(n.get("type", "")).strip() == "CandidateDrug")
    gene_node_count = sum(1 for n in nodes if isinstance(n, dict) and str(n.get("type", "")).strip() == "Gene")
    node_type_by_id = {
        str(node.get("id", "")).strip(): str(node.get("type", "")).strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("id", "")).strip()
    }
    candidate_gene_edge_count = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source_id = str(edge.get("source", "")).strip()
        target_id = str(edge.get("target", "")).strip()
        edge_type = str(edge.get("type", "")).strip()
        source_type = node_type_by_id.get(source_id, "")
        target_type = node_type_by_id.get(target_id, "")
        if (
            ((source_type == "CandidateDrug" and target_type == "Gene") or (source_type == "Gene" and target_type == "CandidateDrug"))
            and edge_type in {"TARGETS_GENE", "HAS_TARGET", "ASSOCIATED_WITH"}
        ):
            candidate_gene_edge_count += 1

    candidate_presence_ok = True
    if disease_drug_row_count > 0:
        candidate_presence_ok = candidate_node_count > 0

    gene_presence_ok = True
    candidate_gene_edge_ok = True
    if drug_gene_row_count > 0:
        gene_presence_ok = gene_node_count > 0
        candidate_gene_edge_ok = candidate_gene_edge_count > 0

    cross_contamination_ok = True
    contamination_notes: list[str] = []
    if alias == "COLON":
        if _contains_text(payload, "LIHC"):
            cross_contamination_ok = False
            contamination_notes.append("COLON response contains LIHC token")
    if alias == "LIVER":
        if _contains_text(payload, "COAD") or _contains_text(payload, "COLON"):
            cross_contamination_ok = False
            contamination_notes.append("LIVER response contains COAD/COLON token")

    return {
        "alias": alias,
        "expected_normalized_disease": expected,
        "actual": {
            "disease": payload.get("disease"),
            "requested_disease": payload.get("requested_disease"),
            "normalized_disease": payload.get("normalized_disease"),
            "view": payload.get("view"),
            "source": payload.get("source"),
        },
        "counts": {
            "nodes": len(nodes),
            "links": len(links),
            "edges": len(edges),
            "node_types": sorted(node_types),
            "candidate_nodes": candidate_node_count,
            "gene_nodes": gene_node_count,
            "candidate_gene_edges": candidate_gene_edge_count,
            "neo4j_disease_drug_rows": disease_drug_row_count,
            "neo4j_drug_gene_rows": drug_gene_row_count,
        },
        "checks": {
            "required_keys_present": all(keys_present.values()),
            "view_source_ok": view_source_ok,
            "requested_disease_preserved": str(payload.get("requested_disease", "")) == alias,
            "normalized_disease_ok": normalized_ok,
            "count_consistent": count_ok,
            "links_edges_identical": links_edges_identical,
            "no_postgres_fallback_warning": no_pg_fallback_warning,
            "auth_warning_contract_ok": auth_warning_contract_ok,
            "node_types_allowed": node_types_allowed,
            "candidate_nodes_present_when_evidence_exists": candidate_presence_ok,
            "gene_nodes_present_when_evidence_exists": gene_presence_ok,
            "candidate_gene_edge_present_when_evidence_exists": candidate_gene_edge_ok,
            "cross_disease_contamination_ok": cross_contamination_ok,
        },
        "warnings": warnings,
        "details": {
            "required_keys": keys_present,
            "contamination_notes": contamination_notes,
            "auth_related_signals": auth_related_signals,
            "diagnostics": diagnostics,
        },
    }


def run() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_app": "api.main:app",
        "route_checks": {
            "/api/graph/{disease}/obsidian": _route_registered("/api/graph/{disease}/obsidian"),
        },
        "cases": [],
        "summary": {},
    }

    with TestClient(app) as client:
        for alias in CASES:
            path = f"/api/graph/{alias}/obsidian"
            response = client.get(path)
            try:
                body = response.json() if response.content else {}
            except Exception:
                body = {}
            case_result = _validate_case(alias, body if isinstance(body, dict) else {})
            case_result["path"] = path
            case_result["http_status"] = response.status_code
            payload["cases"].append(case_result)

    total = len(payload["cases"])
    pass_count = 0
    for case in payload["cases"]:
        checks = case.get("checks", {})
        if checks and all(bool(v) for v in checks.values()):
            pass_count += 1
    payload["summary"] = {
        "total_cases": total,
        "all_checks_pass_cases": pass_count,
        "failed_cases": total - pass_count,
    }
    return payload


def write_markdown(payload: dict[str, Any], out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Neo4j Obsidian KG UI Validation")
    lines.append("")
    lines.append(f"- Generated (UTC): {payload.get('generated_at_utc')}")
    lines.append(f"- Target app: `{payload.get('target_app')}`")
    lines.append("")
    lines.append("## Route Checks")
    lines.append("")
    for path, ok in (payload.get("route_checks") or {}).items():
        lines.append(f"- `{path}`: `{ok}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = payload.get("summary") or {}
    lines.append(f"- Total cases: {summary.get('total_cases')}")
    lines.append(f"- All-check pass cases: {summary.get('all_checks_pass_cases')}")
    lines.append(f"- Failed cases: {summary.get('failed_cases')}")
    lines.append("")
    lines.append("## Per-Case")
    lines.append("")
    for case in payload.get("cases", []):
        lines.append(f"### {case.get('alias')}")
        lines.append("")
        lines.append(f"- Path: `{case.get('path')}`")
        lines.append(f"- HTTP: `{case.get('http_status')}`")
        lines.append(f"- Expected normalized disease: `{case.get('expected_normalized_disease')}`")
        lines.append(f"- Actual: `{case.get('actual')}`")
        lines.append(f"- Counts: `{case.get('counts')}`")
        lines.append(f"- Checks: `{case.get('checks')}`")
        lines.append(f"- Warnings: `{case.get('warnings')}`")
        notes = (case.get("details") or {}).get("contamination_notes") or []
        if notes:
            lines.append(f"- Contamination notes: `{notes}`")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    result = run()
    json_path = Path("outputs/config_validation/neo4j_obsidian_kg_ui_validation.json")
    md_path = Path("docs/neo4j_obsidian_kg_ui_validation.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(result, md_path)
    print(str(json_path))
    print(str(md_path))


if __name__ == "__main__":
    main()
