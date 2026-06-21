from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import app

GRAPH_ALIASES = ["BRAC", "BRCA", "COLON", "COAD", "CRC", "LIHC", "LIVER"]
CANON_EXPECTED = {
    "BRAC": "BRCA",
    "BRCA": "BRCA",
    "COLON": "COAD",
    "COAD": "COAD",
    "CRC": "COAD",
    "LIHC": "LIHC",
    "LIVER": "LIHC",
}
COAD_ALIAS_GROUP = {"COLON", "COAD", "CRC"}
LIHC_ALIAS_GROUP = {"LIHC", "LIVER"}


def _route_registered(path: str) -> bool:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path:
            return True
    return False


def _candidate_count_from_graph_nodes(nodes: list[dict[str, Any]]) -> int:
    c = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("type", "")).strip() == "CandidateDrug":
            c += 1
    return c


def _contains_any_text(value: Any, tokens: list[str]) -> bool:
    text = json.dumps(value, ensure_ascii=False).upper()
    return any(token.upper() in text for token in tokens)


def _validate_contract(payload: dict[str, Any]) -> dict[str, Any]:
    keys = ["disease", "requested_disease", "normalized_disease", "nodes", "links", "edges", "count", "warnings"]
    present = {k: (k in payload) for k in keys}
    count_obj = payload.get("count") if isinstance(payload.get("count"), dict) else {}
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    edges = payload.get("edges") if isinstance(payload.get("edges"), list) else []
    links = payload.get("links") if isinstance(payload.get("links"), list) else []
    count_ok = (
        isinstance(count_obj, dict)
        and count_obj.get("nodes") == len(nodes)
        and count_obj.get("edges") == len(edges)
        and len(edges) == len(links)
    )
    return {
        "keys_present": present,
        "count_consistent": count_ok,
    }


def _validate_no_fabricated_evidence_nodes(payload: dict[str, Any]) -> dict[str, Any]:
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    edges = payload.get("edges") if isinstance(payload.get("edges"), list) else []

    incident_by_node: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        s = str(edge.get("source", "")).strip()
        t = str(edge.get("target", "")).strip()
        if s:
            incident_by_node[s] = incident_by_node.get(s, 0) + 1
        if t:
            incident_by_node[t] = incident_by_node.get(t, 0) + 1

    bad_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ntype = str(node.get("type", "")).strip()
        if ntype not in {"Gene", "Pathway", "Target", "Protein"}:
            continue
        node_id = str(node.get("id", "")).strip()
        source = ""
        props = node.get("properties")
        if isinstance(props, dict):
            source = str(props.get("source", "")).strip().lower()
        has_incident = incident_by_node.get(node_id, 0) > 0
        has_real_source = source in {"neo4j", "postgres"}
        if not has_incident or not has_real_source:
            bad_nodes.append({"id": node_id, "type": ntype, "source": source, "incident_edges": incident_by_node.get(node_id, 0)})

    return {
        "ok": len(bad_nodes) == 0,
        "bad_nodes": bad_nodes,
    }


def run() -> dict[str, Any]:
    results: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_app": "api.main:app",
        "route_checks": {
            "/api/graph/{disease}/ui-basic": _route_registered("/api/graph/{disease}/ui-basic"),
            "/api/diseases/{disease}/candidates": _route_registered("/api/diseases/{disease}/candidates"),
            "/api/diseases/{disease}/final-candidates": _route_registered("/api/diseases/{disease}/final-candidates"),
            "/api/docking/{disease}/gene-pdb": _route_registered("/api/docking/{disease}/gene-pdb"),
            "/api/docking/{disease}/gene-pdb/{gene}": _route_registered("/api/docking/{disease}/gene-pdb/{gene}"),
            "/api/assistant/{disease}/ask": _route_registered("/api/assistant/{disease}/ask"),
        },
        "graph_tests": [],
        "summary": {},
    }

    with TestClient(app) as client:
        for alias in GRAPH_ALIASES:
            graph_path = f"/api/graph/{alias}/ui-basic"
            final_path = f"/api/diseases/{alias}/final-candidates"

            graph_resp = client.get(graph_path)
            final_resp = client.get(final_path)

            graph_payload: dict[str, Any]
            final_payload: dict[str, Any]
            try:
                graph_payload = graph_resp.json() if graph_resp.content else {}
            except Exception:
                graph_payload = {}
            try:
                final_payload = final_resp.json() if final_resp.content else {}
            except Exception:
                final_payload = {}

            nodes = graph_payload.get("nodes") if isinstance(graph_payload.get("nodes"), list) else []
            candidate_count = _candidate_count_from_graph_nodes(nodes)
            final_count = int(final_payload.get("count") or 0) if isinstance(final_payload, dict) else 0

            expected = CANON_EXPECTED[alias]
            normalized_actual = str(graph_payload.get("normalized_disease", ""))
            disease_actual = str(graph_payload.get("disease", ""))

            contamination_ok = True
            contamination_notes: list[str] = []
            if alias in COAD_ALIAS_GROUP:
                bad_tokens = ["LIHC", "LIVER", "HCC", "HEPATOCELLULAR"]
                if _contains_any_text(graph_payload, bad_tokens):
                    contamination_ok = False
                    contamination_notes.append("COAD-family response contains LIHC-family tokens")
            if alias in LIHC_ALIAS_GROUP:
                bad_tokens = ["COLON", "COAD", "CRC", "COLORECTAL"]
                if _contains_any_text(graph_payload, bad_tokens):
                    contamination_ok = False
                    contamination_notes.append("LIHC-family response contains COAD-family tokens")

            contract = _validate_contract(graph_payload)
            fabricated_check = _validate_no_fabricated_evidence_nodes(graph_payload)

            candidate_multiplicity_ok = True
            if final_count > 1:
                candidate_multiplicity_ok = candidate_count > 1

            results["graph_tests"].append(
                {
                    "alias": alias,
                    "graph_path": graph_path,
                    "final_candidates_path": final_path,
                    "http_status": {
                        "graph": graph_resp.status_code,
                        "final_candidates": final_resp.status_code,
                    },
                    "expected_normalized": expected,
                    "actual": {
                        "disease": disease_actual,
                        "normalized_disease": normalized_actual,
                        "requested_disease": graph_payload.get("requested_disease"),
                    },
                    "counts": {
                        "graph_nodes": len(nodes),
                        "graph_edges": len(graph_payload.get("edges", []) if isinstance(graph_payload.get("edges"), list) else []),
                        "candidate_drug_nodes": candidate_count,
                        "final_candidates_count": final_count,
                    },
                    "checks": {
                        "normalized_matches_expected": (normalized_actual == expected and disease_actual == expected),
                        "response_contract_ok": all(contract["keys_present"].values()) and contract["count_consistent"],
                        "cross_disease_contamination_ok": contamination_ok,
                        "candidate_multiplicity_ok": candidate_multiplicity_ok,
                        "no_fabricated_evidence_nodes": fabricated_check["ok"],
                    },
                    "warnings": graph_payload.get("warnings", []) if isinstance(graph_payload.get("warnings"), list) else [],
                    "details": {
                        "contract": contract,
                        "contamination_notes": contamination_notes,
                        "fabricated_evidence_node_issues": fabricated_check["bad_nodes"],
                    },
                }
            )

    tests = results["graph_tests"]
    total = len(tests)
    all_pass = 0
    for t in tests:
        checks = t.get("checks", {})
        if checks and all(bool(v) for v in checks.values()):
            all_pass += 1

    results["summary"] = {
        "total_cases": total,
        "all_checks_pass_cases": all_pass,
        "failed_cases": total - all_pass,
    }
    return results


def write_md(payload: dict[str, Any], out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Multi-Disease UI Graph Enriched Validation")
    lines.append("")
    lines.append(f"- Generated (UTC): {payload.get('generated_at_utc')}")
    lines.append(f"- Target app: `{payload.get('target_app')}`")
    lines.append("")
    lines.append("## Route Checks")
    lines.append("")
    for route_path, ok in (payload.get("route_checks") or {}).items():
        lines.append(f"- `{route_path}`: `{ok}`")
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

    for case in payload.get("graph_tests", []):
        lines.append(f"### {case.get('alias')}")
        lines.append("")
        lines.append(f"- Graph status: `{(case.get('http_status') or {}).get('graph')}`")
        lines.append(f"- Final-candidates status: `{(case.get('http_status') or {}).get('final_candidates')}`")
        lines.append(f"- Expected normalized: `{case.get('expected_normalized')}`")
        actual = case.get("actual") or {}
        lines.append(
            f"- Actual disease/requested/normalized: `{actual.get('disease')}` / `{actual.get('requested_disease')}` / `{actual.get('normalized_disease')}`"
        )
        counts = case.get("counts") or {}
        lines.append(
            f"- Counts (nodes/edges/candidate_nodes/final_candidates): `{counts.get('graph_nodes')}` / `{counts.get('graph_edges')}` / `{counts.get('candidate_drug_nodes')}` / `{counts.get('final_candidates_count')}`"
        )
        checks = case.get("checks") or {}
        lines.append(f"- Checks: `{checks}`")
        notes = ((case.get("details") or {}).get("contamination_notes") or [])
        if notes:
            lines.append(f"- Contamination notes: {notes}")
        lines.append(f"- Warnings: {case.get('warnings')}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    payload = run()
    json_path = Path("outputs/config_validation/multi_disease_ui_graph_enriched_validation.json")
    md_path = Path("docs/multi_disease_ui_graph_enriched_validation.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(payload, md_path)
    print(str(json_path))
    print(str(md_path))


if __name__ == "__main__":
    main()
