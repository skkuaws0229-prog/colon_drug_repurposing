from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.neo4j_client import run_query
from api.services.neo4j_graph_service import get_external_validation_for_disease, get_graph_summary, get_model_evidence
from api.services.disease_aliases import get_disease_aliases
from api.services.postgres_service import get_candidate_detail, normalize_disease


INTENTS = (
    "candidate_explanation",
    "admet_evidence",
    "external_validation",
    "model_evidence",
    "source_trace",
    "graph_summary",
)

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


def detect_intent(question: str) -> str:
    text = (question or "").strip().lower()
    if any(token in text for token in ("admet", "tox", "safety", "pk", "absorption")):
        return "admet_evidence"
    if any(token in text for token in ("external", "metabric", "validation", "cohort")):
        return "external_validation"
    if any(token in text for token in ("model", "metric", "auc", "ensemble")):
        return "model_evidence"
    if any(token in text for token in ("source", "trace", "provenance", "artifact", "run")):
        return "source_trace"
    if any(token in text for token in ("graph", "network", "node", "relationship", "summary")):
        return "graph_summary"
    return "candidate_explanation"


def _candidate_query_context(disease: str, drug_key: str) -> List[Dict[str, Any]]:
    disease_aliases = get_disease_aliases(disease)
    disease_tokens = sorted({item.lower() for item in disease_aliases if item.strip()})
    return run_query(
        """
        MATCH (d:Disease)
        WHERE coalesce(d.name, '') IN $disease_aliases
           OR coalesce(d.code, '') IN $disease_aliases
           OR coalesce(d.disease, '') IN $disease_aliases
           OR coalesce(d.disease_code, '') IN $disease_aliases
           OR coalesce(d.id, '') IN $disease_aliases
        WITH d
        MATCH (c:DrugCandidate)-[:CANDIDATE_FOR]->(d)
        WHERE c.drug_key = $drug_key OR toLower(coalesce(c.drug_name,'')) CONTAINS toLower($drug_key)
        OPTIONAL MATCH (c)-[:HAS_CANDIDATE_SCORE]->(score:CandidateScore)
        OPTIONAL MATCH (c)-[:SELECTED_AS_FINAL]->(final:FinalCandidateEvidence)
        OPTIONAL MATCH (c)-[:HAS_ADMET_PROFILE]->(admet:AdmetEvidence)
        OPTIONAL MATCH (c)-[:HAS_EXTERNAL_VALIDATION]->(ext:ExternalValidationEvidence)
        OPTIONAL MATCH (c)-[:DERIVED_FROM_SOURCE]->(src:SourceArtifact)
        RETURN c, score, final, admet, ext, src
        LIMIT 100
        """,
        {"disease": disease, "drug_key": drug_key, "disease_aliases": disease_aliases, "disease_tokens": disease_tokens},
    )


def _candidate_property_context(disease: str, drug_key: str) -> List[Dict[str, Any]]:
    disease_aliases = get_disease_aliases(disease)
    disease_tokens = sorted({item.lower() for item in disease_aliases if item.strip()})
    return run_query(
        f"""
        MATCH (c)
        WHERE (c:DrugCandidate OR c:Drug) AND ({CANDIDATE_PROPERTY_FALLBACK})
          AND (c.drug_key = $drug_key OR toLower(coalesce(c.drug_name,'')) CONTAINS toLower($drug_key))
        RETURN c
        LIMIT 100
        """,
        {"disease": disease, "drug_key": drug_key, "disease_aliases": disease_aliases, "disease_tokens": disease_tokens},
    )


def answer_question(
    disease: str,
    question: str,
    drug_key: Optional[str] = None,
    mode: str = "graph_context",
) -> Dict[str, Any]:
    normalized = normalize_disease(disease)
    intent = detect_intent(question)
    warnings: List[str] = []
    evidence: List[Dict[str, Any]] = []
    context_counts: Dict[str, int] = {}

    if mode != "graph_context":
        warnings.append("Unsupported mode; graph_context was used.")

    drug_lookup = (drug_key or "").strip()

    if intent in {"candidate_explanation", "admet_evidence", "external_validation", "source_trace"} and not drug_lookup:
        warnings.append("No drug_key was provided; disease-level context was used where possible.")

    if intent == "graph_summary":
        graph_summary = get_graph_summary(normalized)
        context_counts = {
            "node_types": len(graph_summary.get("node_counts", {})),
            "relationship_types": len(graph_summary.get("relationship_counts", {})),
        }
        evidence.append({"source": "neo4j", "kind": "graph_summary", "payload": graph_summary})
        answer = (
            f"Graph summary for {normalized}: "
            f"{graph_summary.get('node_counts', {}).get('DrugCandidate', 0)} DrugCandidate nodes and "
            f"{graph_summary.get('relationship_counts', {}).get('CANDIDATE_FOR', 0)} CANDIDATE_FOR edges."
        )
        warnings.extend(graph_summary.get("known_warnings", []))
    elif intent == "model_evidence":
        model_nodes = get_model_evidence()
        context_counts = {"model_related_nodes": len(model_nodes)}
        evidence.append({"source": "neo4j", "kind": "model_evidence", "rows": model_nodes})
        if model_nodes:
            answer = f"Found {len(model_nodes)} model-related Neo4j evidence nodes."
        else:
            answer = "No model evidence was found in Neo4j."
            warnings.append("No ModelEvidence/ModelDetailEvidence context found.")
    elif intent == "external_validation" and not drug_lookup:
        ext_nodes = get_external_validation_for_disease(normalized)
        context_counts = {"external_validation_nodes": len(ext_nodes)}
        evidence.append({"source": "neo4j", "kind": "external_validation_disease_level", "rows": ext_nodes})
        if ext_nodes:
            answer = f"Found {len(ext_nodes)} disease-level external validation evidence nodes."
        else:
            answer = "No disease-level external validation evidence was found."
            warnings.append("No ExternalValidationEvidence context found for disease.")
    else:
        detail = get_candidate_detail(normalized, drug_lookup) if drug_lookup else {"candidate_rows": []}
        neo_rows = _candidate_query_context(normalized, drug_lookup) if drug_lookup else []
        if drug_lookup and not neo_rows:
            neo_rows = _candidate_property_context(normalized, drug_lookup)

        context_counts = {
            "candidate_rows": len(detail.get("candidate_rows", [])),
            "tier_rows": len(detail.get("tier_rows", [])),
            "final_candidate_rows": len(detail.get("final_candidate_evidence", [])),
            "admet_rows": len(detail.get("admet_rows", [])),
            "external_validation_rows": len(detail.get("external_validation_rows", [])),
            "neo4j_context_rows": len(neo_rows),
            "source_artifact_rows": len(detail.get("source_artifact_rows", [])),
        }
        evidence.append({"source": "postgres", "kind": "candidate_detail", "payload": detail})
        evidence.append({"source": "neo4j", "kind": "candidate_graph_context", "rows": neo_rows})

        if intent == "admet_evidence":
            count = context_counts["admet_rows"]
            answer = (
                f"Found {count} ADMET evidence row(s) for {drug_lookup}."
                if count
                else "ADMET evidence is unavailable for this query."
            )
            if count == 0:
                warnings.append("No ADMET rows found in PostgreSQL for this drug.")
            if context_counts["neo4j_context_rows"] == 0:
                warnings.append("Neo4j ADMET relationship evidence is unavailable for this drug.")
        elif intent == "external_validation":
            count = context_counts["external_validation_rows"]
            answer = (
                f"Found {count} external validation row(s) for {drug_lookup}."
                if count
                else "External validation evidence is unavailable for this query."
            )
            if count == 0:
                warnings.append("No external validation rows found in PostgreSQL for this drug.")
            if context_counts["neo4j_context_rows"] == 0:
                warnings.append("Neo4j external validation relationship evidence is unavailable for this drug.")
        elif intent == "source_trace":
            count = context_counts["source_artifact_rows"]
            answer = (
                f"Found {count} source artifact row(s) linked to {drug_lookup}."
                if count
                else "No source trace rows were found for this drug."
            )
            if count == 0:
                warnings.append("No source artifact rows matched this drug key.")
        else:
            if context_counts["candidate_rows"] > 0 or context_counts["neo4j_context_rows"] > 0:
                answer = (
                    f"Candidate context found for {drug_lookup}: "
                    f"{context_counts['candidate_rows']} PostgreSQL candidate row(s), "
                    f"{context_counts['neo4j_context_rows']} Neo4j context row(s)."
                )
            else:
                answer = "Evidence is unavailable for the requested drug in PostgreSQL and Neo4j."
                warnings.append("No candidate context found.")

    return {
        "disease": normalized,
        "intent": intent,
        "answer": answer,
        "evidence": evidence,
        "warnings": warnings,
        "context_counts": context_counts,
    }

