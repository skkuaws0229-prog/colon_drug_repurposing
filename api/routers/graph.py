from __future__ import annotations

from copy import deepcopy
from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from api.core.disease_aliases import normalize_disease
from api.db.neo4j import (
    get_graph_data_by_disease,
    get_graph_obsidian_by_disease,
    get_graph_summary_by_disease,
    get_graph_ui_basic_by_disease,
)
from api.db.postgres import get_ui_graph_candidate_fallback_by_disease


router = APIRouter(prefix="/api", tags=["graph"])


def _ui_basic_contract(
    *,
    canonical: str,
    requested_disease: str,
    nodes: list[dict[str, object]] | None = None,
    links: list[dict[str, object]] | None = None,
    warnings: list[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> dict[str, object]:
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


def _build_pg_candidate_fallback_payload(
    canonical: str,
    requested_disease: str,
    warnings: list[str],
    neo4j_status: str = "unavailable",
) -> dict[str, object]:
    nodes: list[dict[str, object]] = []
    links: list[dict[str, object]] = []
    diagnostics: dict[str, object] = {
        "neo4j_status": neo4j_status,
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

        nodes_by_id: dict[str, dict[str, object]] = {
            canonical: {"id": canonical, "label": canonical, "type": "Disease"}
        }
        links_by_key: dict[str, dict[str, object]] = {}
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
            node: dict[str, object] = {
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


@router.get("/graph/{disease}")
def get_disease_graph(disease: str, limit: int = Query(default=800, ge=1, le=5000)) -> dict[str, object]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return get_graph_data_by_disease(canonical, limit=limit)
    except Exception as exc:
        return {
            "disease": canonical,
            "nodes": [],
            "edges": [],
            "summary": {"node_count": 0, "edge_count": 0},
            "warnings": [f"Neo4j unavailable: {exc.__class__.__name__}"],
        }


@router.get("/graph/{disease}/summary")
def get_disease_graph_summary(disease: str) -> dict[str, object]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return get_graph_summary_by_disease(canonical)
    except Exception as exc:
        return {
            "disease": canonical,
            "node_counts": {},
            "relationship_counts": {},
            "status": "PASS_WITH_WARNINGS",
            "warnings": [f"Neo4j unavailable: {exc.__class__.__name__}"],
        }


@router.get("/graph/{disease}/ui-basic")
def get_disease_graph_ui_basic(
    disease: str,
    include_postgres: bool = Query(default=False),
    source: Literal["auto", "neo4j", "fallback"] = Query(default="auto"),
    view: Literal["core", "full"] = Query(default="core"),
    max_nodes: int = Query(default=200, ge=1, le=2000),
    max_links: int = Query(default=300, ge=1, le=5000),
) -> dict[str, object]:
    requested_disease = disease
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if source == "fallback":
        return _build_pg_candidate_fallback_payload(canonical, requested_disease, [], neo4j_status="skipped")

    try:
        payload = get_graph_ui_basic_by_disease(
            canonical,
            include_postgres=include_postgres,
            requested_disease=requested_disease,
            source=source,
            view=view,
            max_nodes=max_nodes,
            max_links=max_links,
        )
        if not isinstance(payload, dict):
            payload = {}
        nodes = payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []
        links = payload.get("links", []) if isinstance(payload.get("links"), list) else []
        warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
        diagnostics = payload.get("diagnostics", {}) if isinstance(payload.get("diagnostics"), dict) else {}
        return _ui_basic_contract(
            canonical=canonical,
            requested_disease=requested_disease,
            nodes=nodes,
            links=links,
            warnings=warnings,
            diagnostics=diagnostics,
        )
    except Exception as exc:
        warning = f"Neo4j projection unavailable: {exc.__class__.__name__}: {str(exc).strip()}".strip()
        if source == "neo4j":
            return _ui_basic_contract(
                canonical=canonical,
                requested_disease=requested_disease,
                nodes=[],
                links=[],
                warnings=[warning],
                diagnostics={"source_mode": source, "neo4j_status": "unavailable"},
            )
        return _build_pg_candidate_fallback_payload(canonical, requested_disease, [warning])


@router.get("/graph/{disease}/obsidian")
def get_disease_graph_obsidian(disease: str) -> dict[str, object]:
    requested_disease = disease
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        payload = get_graph_obsidian_by_disease(canonical, requested_disease=requested_disease, limit=500)
    except Exception as exc:
        payload = {
            "disease": canonical,
            "requested_disease": requested_disease,
            "normalized_disease": canonical,
            "view": "obsidian",
            "source": "neo4j",
            "nodes": [],
            "links": [],
            "edges": [],
            "count": {"nodes": 0, "edges": 0},
            "legend": ["Disease", "Candidate Drug", "Gene", "Pathway", "Target", "Protein"],
            "warnings": [f"Neo4j obsidian route unavailable: {exc.__class__.__name__}"],
            "diagnostics": {"neo4j_status": "unavailable", "source": "neo4j"},
        }
    if not isinstance(payload, dict):
        payload = {}
    nodes = payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []
    links = payload.get("links", []) if isinstance(payload.get("links"), list) else []
    edges = payload.get("edges", []) if isinstance(payload.get("edges"), list) else []
    if len(edges) != len(links):
        edges = [deepcopy(link) for link in links]
    count = {"nodes": len(nodes), "edges": len(edges)}
    return {
        "disease": canonical,
        "requested_disease": requested_disease,
        "normalized_disease": canonical,
        "view": "obsidian",
        "source": "neo4j",
        "nodes": nodes,
        "links": links,
        "edges": edges,
        "count": count,
        "legend": payload.get("legend")
        if isinstance(payload.get("legend"), list)
        else ["Disease", "Candidate Drug", "Gene", "Pathway", "Target", "Protein"],
        "warnings": payload.get("warnings") if isinstance(payload.get("warnings"), list) else [],
        "diagnostics": payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {},
    }
