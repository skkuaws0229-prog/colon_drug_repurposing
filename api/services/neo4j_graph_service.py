from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

from api.neo4j_client import run_query
from api.services.disease_aliases import get_disease_aliases
from api.services.postgres_service import normalize_disease


BREAST_RELATIONSHIP_WARNING = "BRCA (alias BRAC) candidate nodes exist, but evidence relationships are not connected in Neo4j."

DISEASE_MATCH = """
    d.name IN $disease_aliases
 OR d.code IN $disease_aliases
 OR d.disease IN $disease_aliases
 OR d.disease_code IN $disease_aliases
 OR d.id IN $disease_aliases
"""

CANDIDATE_PROPERTY_FALLBACK = """
    c.disease IN $disease_aliases
 OR c.disease_code IN $disease_aliases
 OR c.cancer_type IN $disease_aliases
 OR c.project IN $disease_aliases
 OR any(tok IN $disease_tokens WHERE toLower(coalesce(c.name, '')) CONTAINS tok)
 OR any(tok IN $disease_tokens WHERE toLower(coalesce(c.drug_name, '')) CONTAINS tok)
 OR any(tok IN $disease_tokens WHERE toLower(coalesce(c.drug_key, '')) CONTAINS tok)
 OR any(tok IN $disease_tokens WHERE toLower(coalesce(c.indication, '')) CONTAINS tok)
 OR any(tok IN $disease_tokens WHERE toLower(coalesce(c.description, '')) CONTAINS tok)
"""


def _to_primitive(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_to_primitive(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_primitive(v) for k, v in value.items()}
    if hasattr(value, "items"):
        try:
            return {str(k): _to_primitive(v) for k, v in dict(value.items()).items()}
        except Exception:
            pass
    return str(value)


def _node_payload(node: Any) -> Dict[str, Any]:
    element_id = str(getattr(node, "element_id", "")) if node is not None else ""
    labels = list(getattr(node, "labels", [])) if node is not None else []
    properties = _to_primitive(dict(node.items()) if hasattr(node, "items") else {})
    node_type = labels[0] if labels else "Node"
    node_id = (
        properties.get("drug_key")
        or properties.get("drug_id")
        or properties.get("evidence_key")
        or properties.get("model_key")
        or properties.get("code")
        or properties.get("id")
        or element_id
    )
    label = (
        properties.get("drug_name")
        or properties.get("name")
        or properties.get("code")
        or properties.get("evidence_key")
        or node_id
    )
    return {
        "id": str(node_id),
        "label": str(label),
        "type": node_type,
        "group": node_type,
        "properties": properties,
        "_element_id": element_id,
    }


def _rel_payload(rel: Any, source: Any, target: Any) -> Dict[str, Any]:
    rel_type = str(getattr(rel, "type", "RELATED_TO"))
    rel_props = _to_primitive(dict(rel.items()) if hasattr(rel, "items") else {})
    return {
        "source": source,
        "target": target,
        "type": rel_type,
        "properties": rel_props,
    }


def _collect_graph_rows(rows: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    nodes_by_element: Dict[str, Dict[str, Any]] = {}
    links_seen: Set[Tuple[str, str, str]] = set()
    links: List[Dict[str, Any]] = []

    for row in rows:
        for value in row.values():
            if value is None:
                continue
            if hasattr(value, "labels"):
                node = _node_payload(value)
                nodes_by_element[node["_element_id"]] = node

        for value in row.values():
            if value is None or not hasattr(value, "type"):
                continue
            start_element = str(getattr(value.start_node, "element_id", ""))
            end_element = str(getattr(value.end_node, "element_id", ""))
            if not start_element or not end_element:
                continue
            start_node = nodes_by_element.get(start_element)
            end_node = nodes_by_element.get(end_element)
            if not start_node or not end_node:
                continue
            key = (start_node["id"], end_node["id"], str(getattr(value, "type", "")))
            if key in links_seen:
                continue
            links_seen.add(key)
            links.append(_rel_payload(value, start_node["id"], end_node["id"]))

    nodes = []
    for node in nodes_by_element.values():
        clean = dict(node)
        clean.pop("_element_id", None)
        nodes.append(clean)
    return nodes, links


def _disease_query_params(disease: str) -> Dict[str, Any]:
    aliases = get_disease_aliases(disease)
    tokens = sorted({a.lower() for a in aliases if a.strip()})
    return {"disease": disease, "disease_aliases": aliases, "disease_tokens": tokens}


def _count_value(query: str, params: Dict[str, Any]) -> int:
    rows = run_query(query, params)
    if not rows:
        return 0
    return int(rows[0].get("c") or 0)


def _candidate_count_via_relationships(params: Dict[str, Any]) -> int:
    return _count_value(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        RETURN count(DISTINCT c) AS c
        """,
        params,
    )


def _candidate_count_via_properties(params: Dict[str, Any]) -> int:
    return _count_value(
        f"""
        MATCH (c)
        WHERE (c:DrugCandidate OR c:Drug) AND ({CANDIDATE_PROPERTY_FALLBACK})
        RETURN count(DISTINCT c) AS c
        """,
        params,
    )


def _count_distinct_node(query: str, params: Dict[str, Any]) -> int:
    return _count_value(query, params)


def _count_relationship(query: str, params: Dict[str, Any]) -> int:
    return _count_value(query, params)


def get_graph_summary(disease: str) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    params = _disease_query_params(normalized)

    node_counts: Dict[str, int] = {}
    relationship_counts: Dict[str, int] = {}

    node_counts["Disease"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        RETURN count(DISTINCT d) AS c
        """,
        params,
    )

    relationship_candidate_count = _candidate_count_via_relationships(params)
    property_candidate_count = _candidate_count_via_properties(params)
    node_counts["DrugCandidate"] = max(relationship_candidate_count, property_candidate_count)

    node_counts["CandidateScore"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:HAS_CANDIDATE_SCORE]->(score:CandidateScore)
        RETURN count(DISTINCT score) AS c
        """,
        params,
    )
    node_counts["TierEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:HAS_TIER]->(tier:TierEvidence)
        RETURN count(DISTINCT tier) AS c
        """,
        params,
    )
    node_counts["FinalCandidateEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:SELECTED_AS_FINAL]->(final:FinalCandidateEvidence)
        RETURN count(DISTINCT final) AS c
        """,
        params,
    )
    node_counts["AdmetEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:HAS_ADMET_PROFILE]->(admet:AdmetEvidence)
        RETURN count(DISTINCT admet) AS c
        """,
        params,
    )
    node_counts["ExternalValidationEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        OPTIONAL MATCH (e:ExternalValidationEvidence)-[:VALIDATED_BY_EXTERNAL_DATA]->(d)
        RETURN count(DISTINCT e) AS c
        """,
        params,
    )
    node_counts["ModelEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_MODEL]->(m:ModelEvidence)
        RETURN count(DISTINCT m) AS c
        """,
        params,
    )
    node_counts["ModelDetailEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[:SUPPORTED_BY_MODEL]->(m:ModelEvidence)
        OPTIONAL MATCH (m)-[:HAS_DETAILED_MODEL_METRIC]->(detail:ModelDetailEvidence)
        RETURN count(DISTINCT detail) AS c
        """,
        params,
    )
    node_counts["EnsembleEvidence"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_ENSEMBLE]->(ens:EnsembleEvidence)
        RETURN count(DISTINCT ens) AS c
        """,
        params,
    )
    node_counts["SourceArtifact"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        OPTIONAL MATCH (c)-[:DERIVED_FROM_SOURCE]->(src:SourceArtifact)
        RETURN count(DISTINCT src) AS c
        """,
        params,
    )
    node_counts["Run"] = _count_distinct_node(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        OPTIONAL MATCH (run:Run)-[:PRODUCED_EVIDENCE]->(:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        RETURN count(DISTINCT run) AS c
        """,
        params,
    )

    relationship_counts["CANDIDATE_FOR"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (:DrugCandidate)-[r:CANDIDATE_FOR]->(d)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["HAS_CANDIDATE_SCORE"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:HAS_CANDIDATE_SCORE]->(:CandidateScore)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["HAS_TIER"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:HAS_TIER]->(:TierEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["SELECTED_AS_FINAL"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:SELECTED_AS_FINAL]->(:FinalCandidateEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["HAS_ADMET_PROFILE"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:HAS_ADMET_PROFILE]->(:AdmetEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["VALIDATED_BY_EXTERNAL_DATA"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (:ExternalValidationEvidence)-[r:VALIDATED_BY_EXTERNAL_DATA]->(d)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["HAS_EXTERNAL_VALIDATION"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:HAS_EXTERNAL_VALIDATION]->(:ExternalValidationEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["SUPPORTED_BY_MODEL"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:SUPPORTED_BY_MODEL]->(:ModelEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["HAS_DETAILED_MODEL_METRIC"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[:SUPPORTED_BY_MODEL]->(m:ModelEvidence)
        MATCH (m)-[r:HAS_DETAILED_MODEL_METRIC]->(:ModelDetailEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["SUPPORTED_BY_ENSEMBLE"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:SUPPORTED_BY_ENSEMBLE]->(:EnsembleEvidence)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["DERIVED_FROM_SOURCE"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        MATCH (c)-[r:DERIVED_FROM_SOURCE]->(:SourceArtifact)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["PRODUCED_EVIDENCE"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (run:Run)-[r:PRODUCED_EVIDENCE]->(:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        RETURN count(r) AS c
        """,
        params,
    )
    relationship_counts["AUDITS_LOAD_FOR"] = _count_relationship(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        MATCH (:LoadAuditEvidence)-[r:AUDITS_LOAD_FOR]->(d)
        RETURN count(r) AS c
        """,
        params,
    )

    warnings: List[str] = []
    if node_counts["Disease"] == 0:
        warnings.append(f"No Disease node was found for aliases of {normalized}.")
    if relationship_counts["HAS_TIER"] == 0:
        warnings.append("HAS_TIER relationship count is 0 (Tier evidence may be unavailable).")
    if normalized in {"BRCA", "BRAC"} and node_counts["DrugCandidate"] > 0 and relationship_counts["CANDIDATE_FOR"] == 0:
        warnings.append(BREAST_RELATIONSHIP_WARNING)

    if node_counts["Disease"] == 0 or node_counts["DrugCandidate"] == 0:
        graph_status = "FAIL"
    elif warnings:
        graph_status = "PASS_WITH_WARNINGS"
    else:
        graph_status = "PASS"

    return {
        "disease": normalized,
        "node_counts": node_counts,
        "relationship_counts": relationship_counts,
        "graph_status": graph_status,
        "known_warnings": warnings,
    }


def _fallback_candidate_rows(params: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
    return run_query(
        f"""
        MATCH (c)
        WHERE (c:DrugCandidate OR c:Drug) AND ({CANDIDATE_PROPERTY_FALLBACK})
        RETURN c
        ORDER BY coalesce(c.rank, 2147483647), c.drug_key, c.drug_name
        LIMIT $limit
        """,
        {**params, "limit": limit},
    )


def get_force_graph(disease: str, limit: int = 300, include_evidence: bool = True) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    params = _disease_query_params(normalized)
    limit_value = max(1, min(int(limit), 2000))

    base_rows = run_query(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        OPTIONAL MATCH (c:DrugCandidate)-[cf:CANDIDATE_FOR]->(d)
        WITH d, c, cf
        ORDER BY coalesce(c.rank, 2147483647), c.drug_key, c.drug_name
        LIMIT $limit
        RETURN d, c, cf
        """,
        {**params, "limit": limit_value},
    )

    rows = list(base_rows)
    if not rows or not any(row.get("cf") is not None for row in rows):
        rows.extend(_fallback_candidate_rows(params, limit_value))

    if include_evidence:
        evidence_rows = run_query(
            f"""
            MATCH (d:Disease)
            WHERE {DISEASE_MATCH}
            MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
            WITH c
            ORDER BY coalesce(c.rank, 2147483647), c.drug_key, c.drug_name
            LIMIT $limit
            OPTIONAL MATCH (c)-[r]->(n)
            WHERE type(r) IN [
              'HAS_CANDIDATE_SCORE',
              'HAS_TIER',
              'SELECTED_AS_FINAL',
              'HAS_ADMET_PROFILE',
              'HAS_EXTERNAL_VALIDATION',
              'SUPPORTED_BY_MODEL',
              'SUPPORTED_BY_ENSEMBLE',
              'DERIVED_FROM_SOURCE'
            ]
            RETURN c, r, n
            LIMIT $edge_limit
            """,
            {**params, "limit": limit_value, "edge_limit": max(limit_value * 20, 300)},
        )
        rows.extend(evidence_rows)

    nodes, links = _collect_graph_rows(rows)
    return {"disease": normalized, "nodes": nodes, "links": links}


def get_node_neighborhood(disease: str, node_id: str, limit: int = 200) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    params = _disease_query_params(normalized)
    limit_value = max(1, min(int(limit), 1000))
    rows = run_query(
        f"""
        MATCH (n)
        WHERE (
               elementId(n) = $node_id
               OR coalesce(n.drug_key, '') = $node_id
               OR coalesce(n.drug_id, '') = $node_id
               OR coalesce(n.evidence_key, '') = $node_id
               OR coalesce(n.model_key, '') = $node_id
               OR coalesce(n.code, '') = $node_id
               OR coalesce(n.id, '') = $node_id
        )
          AND (
               n.name IN $disease_aliases
               OR n.code IN $disease_aliases
               OR n.disease IN $disease_aliases
               OR n.disease_code IN $disease_aliases
               OR n.id IN $disease_aliases
               OR n:SourceArtifact
               OR n:Run
          )
        WITH n
        LIMIT 1
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, r, m
        LIMIT $limit
        """,
        {**params, "node_id": node_id, "limit": limit_value},
    )
    nodes, links = _collect_graph_rows(rows)
    center = nodes[0] if nodes else None
    return {"disease": normalized, "node_id": node_id, "center": center, "nodes": nodes, "links": links}


def get_drug_graph_context(disease: str, drug_key: str) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    params = _disease_query_params(normalized)
    rows = run_query(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        WITH d
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        WHERE c.drug_key = $drug_key OR toLower(coalesce(c.drug_name,'')) CONTAINS toLower($drug_key)
        OPTIONAL MATCH (c)-[:HAS_CANDIDATE_SCORE]->(score:CandidateScore)
        OPTIONAL MATCH (c)-[:SELECTED_AS_FINAL]->(final:FinalCandidateEvidence)
        OPTIONAL MATCH (c)-[:HAS_ADMET_PROFILE]->(admet:AdmetEvidence)
        OPTIONAL MATCH (c)-[:HAS_EXTERNAL_VALIDATION]->(ext:ExternalValidationEvidence)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_MODEL]->(model:ModelEvidence)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_ENSEMBLE]->(ens:EnsembleEvidence)
        OPTIONAL MATCH (c)-[:DERIVED_FROM_SOURCE]->(src:SourceArtifact)
        OPTIONAL MATCH (run:Run)-[:PRODUCED_EVIDENCE]->(c)
        RETURN c, score, final, admet, ext, model, ens, src, run
        LIMIT 100
        """,
        {**params, "drug_key": drug_key},
    )

    if not rows:
        rows = run_query(
            f"""
            MATCH (c)
            WHERE (c:DrugCandidate OR c:Drug) AND ({CANDIDATE_PROPERTY_FALLBACK})
              AND (c.drug_key = $drug_key OR toLower(coalesce(c.drug_name,'')) CONTAINS toLower($drug_key))
            RETURN c
            LIMIT 100
            """,
            {**params, "drug_key": drug_key},
        )

    label_map = {
        "DrugCandidate": "DrugCandidate",
        "CandidateScore": "CandidateScore",
        "FinalCandidateEvidence": "FinalCandidateEvidence",
        "AdmetEvidence": "AdmetEvidence",
        "ExternalValidationEvidence": "ExternalValidationEvidence",
        "ModelEvidence": "ModelEvidence",
        "EnsembleEvidence": "EnsembleEvidence",
        "SourceArtifact": "SourceArtifact",
        "Run": "Run",
    }
    payload: Dict[str, List[Dict[str, Any]]] = {value: [] for value in label_map.values()}
    seen: Dict[str, Set[str]] = {value: set() for value in label_map.values()}

    for row in rows:
        for value in row.values():
            if value is None or not hasattr(value, "labels"):
                continue
            node = _node_payload(value)
            mapped = label_map.get(node["type"])
            if not mapped:
                continue
            node_id = node["id"]
            if node_id in seen[mapped]:
                continue
            seen[mapped].add(node_id)
            clean = dict(node)
            clean.pop("_element_id", None)
            payload[mapped].append(clean)

    return {"disease": normalized, "drug_key": drug_key, **payload}


def get_external_validation_for_disease(disease: str) -> List[Dict[str, Any]]:
    normalized = normalize_disease(disease)
    params = _disease_query_params(normalized)
    rows = run_query(
        f"""
        MATCH (d:Disease)
        WHERE {DISEASE_MATCH}
        WITH d
        MATCH (e:ExternalValidationEvidence)-[:VALIDATED_BY_EXTERNAL_DATA]->(d)
        OPTIONAL MATCH (e)-[:DERIVED_FROM_SOURCE]->(src:SourceArtifact)
        RETURN e, src
        LIMIT 100
        """,
        params,
    )
    nodes, _ = _collect_graph_rows(rows)
    return nodes


def get_model_evidence() -> List[Dict[str, Any]]:
    rows = run_query(
        """
        MATCH (m:ModelEvidence)
        OPTIONAL MATCH (m)-[:HAS_DETAILED_MODEL_METRIC]->(detail:ModelDetailEvidence)
        OPTIONAL MATCH (m)-[:DERIVED_FROM_SOURCE]->(src:SourceArtifact)
        RETURN m, detail, src
        LIMIT 100
        """,
        {},
    )
    nodes, _ = _collect_graph_rows(rows)
    return nodes
