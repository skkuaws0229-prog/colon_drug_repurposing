from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.core.disease_aliases import normalize_disease
from api.db.neo4j import get_graph_ui_basic_by_disease
from api.db.postgres import get_ui_graph_candidate_fallback_by_disease

router = APIRouter(prefix="/api/graph", tags=["graph"])

ALLOWED_GROUPS = {"Disease", "CandidateDrug", "Gene", "Pathway", "Target", "Protein"}
ALLOWED_REL_TYPES = {
    "HAS_CANDIDATE",
    "HAS_TARGET",
    "TARGETS_GENE",
    "BINDS_PROTEIN",
    "ENCODES",
    "PARTICIPATES_IN",
    "ASSOCIATED_WITH",
}


def _ui_basic_contract(
    *,
    canonical: str,
    requested_disease: str,
    nodes: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_nodes = nodes if isinstance(nodes, list) else []
    safe_links = links if isinstance(links, list) else []
    safe_edges = [deepcopy(link) for link in safe_links]
    return {
        "disease": canonical,
        "requested_disease": requested_disease,
        "normalized_disease": canonical,
        "nodes": safe_nodes,
        "links": safe_links,
        "edges": safe_edges,
        "count": {"nodes": len(safe_nodes), "edges": len(safe_edges)},
        "warnings": warnings if isinstance(warnings, list) else [],
        "diagnostics": diagnostics if isinstance(diagnostics, dict) else {},
    }


def _build_pg_candidate_fallback_payload(canonical: str, requested_disease: str, warnings: list[str]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {
        "neo4j_status": "unavailable",
        "postgres_candidate_status": "not_attempted",
        "used_postgres_candidate_fallback": False,
    }
    try:
        pg = get_ui_graph_candidate_fallback_by_disease(canonical, limit=250)
        diagnostics["postgres_candidate_status"] = "ok"
        diagnostics["postgres_candidate_source_table"] = pg.get("source_table")
        items = pg.get("items", [])
        if not isinstance(items, list):
            items = []

        nodes_by_id: dict[str, dict[str, Any]] = {
            canonical: {"id": canonical, "label": canonical, "type": "Disease"}
        }
        links_by_key: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            drug_name = item.get("drug_name")
            if not str(drug_name or "").strip():
                payload = item.get("payload")
                if isinstance(payload, dict):
                    for key in ("drug_name", "drug_name_norm", "drug", "name", "compound_name"):
                        value = payload.get(key)
                        if str(value or "").strip():
                            drug_name = value
                            break
            if not str(drug_name or "").strip():
                continue

            drug_text = str(drug_name).strip()
            drug_id = f"{canonical}:DRUG:{drug_text}"
            source_table = item.get("source_table")
            node: dict[str, Any] = {
                "id": drug_id,
                "label": drug_text,
                "type": "CandidateDrug",
                "source_table": source_table,
            }
            for field in ("rank", "score", "confidence_grade"):
                value = item.get(field)
                if value is not None:
                    node[field] = value
            nodes_by_id[drug_id] = node
            links_by_key[f"{canonical}|HAS_CANDIDATE|{drug_id}"] = {
                "source": canonical,
                "target": drug_id,
                "type": "HAS_CANDIDATE",
            }

        nodes = list(nodes_by_id.values())
        links = list(links_by_key.values())
        diagnostics["postgres_candidate_count"] = max(0, len(nodes) - 1)
        if links:
            diagnostics["used_postgres_candidate_fallback"] = True
            warnings.append("GRAPH_FALLBACK_FROM_POSTGRES_CANDIDATES")
        else:
            diagnostics["postgres_candidate_status"] = "empty"
            warnings.append("NO_GRAPH_DATA")
    except Exception as exc:
        diagnostics["postgres_candidate_status"] = "unavailable"
        warnings.append(f"PostgreSQL candidate fallback unavailable: {exc.__class__.__name__}: {str(exc).strip()}")
        warnings.append("NO_GRAPH_DATA")

    return _ui_basic_contract(
        canonical=canonical,
        requested_disease=requested_disease,
        nodes=nodes,
        links=links,
        warnings=warnings,
        diagnostics=diagnostics,
    )


def _sanitize_ui_basic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    nodes = payload.get("nodes", [])
    links = payload.get("links", [])

    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(links, list):
        links = []

    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        group = str(node.get("group") or node.get("label") or "").strip()
        if not node_id or group not in ALLOWED_GROUPS:
            continue
        if node_id not in node_by_id:
            node_by_id[node_id] = node

    allowed_node_ids = set(node_by_id.keys())

    dedup_link_keys: set[str] = set()
    filtered_links: list[dict[str, Any]] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        source = str(link.get("source", "")).strip()
        target = str(link.get("target", "")).strip()
        rel_type = str(link.get("type", "")).strip()
        if not source or not target or not rel_type:
            continue
        if rel_type not in ALLOWED_REL_TYPES:
            continue
        if source not in allowed_node_ids or target not in allowed_node_ids:
            continue

        key = f"{source}|{rel_type}|{target}"
        if key in dedup_link_keys:
            continue
        dedup_link_keys.add(key)
        filtered_links.append(link)

    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics["projection_groups"] = sorted(ALLOWED_GROUPS)
    diagnostics["projection_relationship_types"] = sorted(ALLOWED_REL_TYPES)

    canonical = str(payload.get("normalized_disease") or payload.get("disease") or "").strip()
    requested_disease = str(payload.get("requested_disease") or canonical).strip()
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    return _ui_basic_contract(
        canonical=canonical,
        requested_disease=requested_disease,
        nodes=list(node_by_id.values()),
        links=filtered_links,
        warnings=warnings,
        diagnostics=diagnostics,
    )


@router.get("/{disease}/ui-basic")
def get_graph_ui_basic(disease: str, include_postgres: bool = Query(default=False)) -> dict[str, Any]:
    requested_disease = disease
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        raw_payload = get_graph_ui_basic_by_disease(canonical, include_postgres=include_postgres, requested_disease=requested_disease)
    except Exception as exc:
        warning = f"Neo4j projection unavailable: {exc.__class__.__name__}: {str(exc).strip()}".strip()
        return _build_pg_candidate_fallback_payload(canonical, requested_disease, [warning])

    return _sanitize_ui_basic_payload(raw_payload)
