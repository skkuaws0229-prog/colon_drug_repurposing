from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from neo4j.exceptions import AuthError, ClientError

from api.db import SQLAlchemyError, fetch_all, fetch_one
from api.neo4j_client import Neo4jError, ServiceUnavailable, run_query
from api.schemas.brca import ADMETDetail, AgentContext, CandidateDetail, CandidateSummary, KGDetail, ValidationDetail


router = APIRouter()
logger = logging.getLogger(__name__)

DISEASE = "BRCA"
RUN_ID = "BRCA_RELEASE_V1"


def _pg_fetch_one(query: str, params: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        return fetch_one(query, params)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"PostgreSQL unavailable: {exc.__class__.__name__}") from exc


def _pg_fetch_all(query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        return fetch_all(query, params)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"PostgreSQL unavailable: {exc.__class__.__name__}") from exc


def _neo4j_query(query: str, params: Dict[str, Any], stage: str = "unknown") -> List[Dict[str, Any]]:
    try:
        logger.info("Neo4j query start stage=%s", stage)
        return run_query(query, params)
    except (ServiceUnavailable, AuthError) as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {exc.__class__.__name__}") from exc
    except ClientError as exc:
        logger.exception(
            "Neo4j ClientError at stage=%s message=%s query=%s params=%s",
            stage,
            str(exc),
            query,
            params,
        )
        raise HTTPException(status_code=500, detail="Neo4j query error") from exc
    except Neo4jError as exc:
        logger.exception("Neo4j query error at stage=%s: %s", stage, exc)
        raise HTTPException(status_code=500, detail="Neo4j query error") from exc


def _get_candidate_or_404(drug_id: str) -> Dict[str, Any]:
    candidate = _pg_fetch_one(
        """
        SELECT
          disease,
          run_id,
          source_s3_uri,
          drug_id,
          drug_name,
          rank,
          score AS drug_level_score,
          payload,
          payload->>'canonical_smiles' AS canonical_smiles,
          payload->>'confidence_grade' AS confidence_grade
        FROM drug_candidate_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC
        LIMIT 1
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    if not candidate:
        raise HTTPException(status_code=404, detail=f"drug_id not found: {drug_id}")
    return candidate


def _get_kg_context(drug_id: str, drug_name: str | None = None) -> Dict[str, Any]:
    logger.info("BRCA KG lookup drug_id=%s drug_name=%s", drug_id, drug_name)
    logger.info("BRCA KG query stage=minimal_kg_lookup")
    rows = _neo4j_query(
        """
        MATCH (d:Drug)
        WHERE d.drug_id = $drug_id
        OPTIONAL MATCH (d)-[:TARGETS]->(g:Gene)
        OPTIONAL MATCH (g)-[:INVOLVED_IN]->(p:Pathway)
        RETURN
          d.drug_id AS drug_id,
          d.name AS drug_name,
          collect(DISTINCT coalesce(g.symbol, g.name)) AS genes,
          collect(DISTINCT p.name) AS pathways
        LIMIT 1
        """,
        {"drug_id": drug_id},
        stage="minimal_kg_lookup",
    )
    if not rows:
        return {
            "drug_id": drug_id,
            "drug_name": drug_name,
            "disease": DISEASE,
            "candidate_relationship": None,
            "genes": [],
            "pathways": [],
            "admet": None,
            "validation": [],
            "warnings": ["No matching Drug node in Neo4j."],
        }

    row = rows[0]
    genes = [item for item in (row.get("genes") or []) if item is not None]
    pathways = [item for item in (row.get("pathways") or []) if item is not None]

    return {
        "drug_id": row.get("drug_id") or drug_id,
        "drug_name": row.get("drug_name") or drug_name,
        "disease": DISEASE,
        "candidate_relationship": None,
        "genes": genes,
        "pathways": pathways,
        "admet": None,
        "validation": [],
        "warnings": [],
        # TODO: Add CANDIDATE_FOR relationship fields after minimal KG query is stable.
        # TODO: Add HAS_ADMET and VALIDATED_BY relationship details in a follow-up query.
    }


@router.get("/candidates", response_model=List[CandidateSummary])
def get_candidates() -> List[CandidateSummary]:
    rows = _pg_fetch_all(
        """
        WITH final15 AS (
          SELECT DISTINCT drug_id, TRUE AS final15
          FROM final_candidate_result
          WHERE disease = :disease
            AND run_id = :run_id
        ),
        val AS (
          SELECT drug_id, MAX(validation_score) AS validation_score
          FROM external_validation_result
          WHERE disease = :disease
            AND run_id = :run_id
          GROUP BY drug_id
        )
        SELECT
          c.rank,
          c.drug_id,
          c.drug_name,
          c.payload->>'canonical_smiles' AS canonical_smiles,
          c.score AS drug_level_score,
          c.payload->>'confidence_grade' AS confidence_grade,
          COALESCE(f.final15, FALSE) AS final15,
          a.admet_verdict AS admet_verdict,
          v.validation_score
        FROM drug_candidate_result c
        LEFT JOIN final15 f
          ON f.drug_id = c.drug_id
        LEFT JOIN LATERAL (
          SELECT admet_verdict
          FROM admet_result ar
          WHERE ar.disease = c.disease
            AND ar.run_id = c.run_id
            AND ar.drug_id = c.drug_id
          ORDER BY ar.rank ASC
          LIMIT 1
        ) a ON TRUE
        LEFT JOIN val v
          ON v.drug_id = c.drug_id
        WHERE c.disease = :disease
          AND c.run_id = :run_id
        ORDER BY c.rank ASC, c.drug_name ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID},
    )
    return [CandidateSummary(**row) for row in rows]


@router.get("/candidates/{drug_id}", response_model=CandidateDetail)
def get_candidate_detail(drug_id: str) -> CandidateDetail:
    candidate = _get_candidate_or_404(drug_id)
    tiers = _pg_fetch_all(
        """
        SELECT rank, tier, score, payload, source_s3_uri
        FROM drug_candidate_tier
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC, tier ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    finals = _pg_fetch_all(
        """
        SELECT rank, final_verdict, payload, source_s3_uri
        FROM final_candidate_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    source_rows = _pg_fetch_all(
        """
        SELECT DISTINCT source_s3_uri
        FROM (
          SELECT source_s3_uri FROM drug_candidate_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM drug_candidate_tier WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM final_candidate_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM admet_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM external_validation_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM metabric_method_score WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
        ) s
        WHERE source_s3_uri IS NOT NULL
          AND source_s3_uri <> ''
        ORDER BY source_s3_uri
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    return CandidateDetail(
        candidate=candidate,
        tiers=tiers,
        final_candidates=finals,
        source_s3_uris=[row["source_s3_uri"] for row in source_rows],
    )


@router.get("/candidates/{drug_id}/admet", response_model=ADMETDetail)
def get_candidate_admet(drug_id: str) -> ADMETDetail:
    _get_candidate_or_404(drug_id)
    rows = _pg_fetch_all(
        """
        SELECT rank, admet_verdict, hard_fail, score, payload, source_s3_uri
        FROM admet_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    return ADMETDetail(drug_id=drug_id, admet_results=rows)


@router.get("/candidates/{drug_id}/validation", response_model=ValidationDetail)
def get_candidate_validation(drug_id: str) -> ValidationDetail:
    _get_candidate_or_404(drug_id)
    validation_rows = _pg_fetch_all(
        """
        SELECT validation_source, rank, validation_score, payload, source_s3_uri
        FROM external_validation_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY validation_source ASC, rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    method_rows = _pg_fetch_all(
        """
        SELECT method, rank, score, payload, source_s3_uri
        FROM metabric_method_score
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY method ASC, rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    return ValidationDetail(
        drug_id=drug_id,
        validation_results=validation_rows,
        metabric_method_scores=method_rows,
    )


@router.get("/candidates/{drug_id}/kg", response_model=KGDetail)
def get_candidate_kg(drug_id: str) -> KGDetail:
    candidate = _get_candidate_or_404(drug_id)
    kg = _get_kg_context(drug_id, candidate.get("drug_name"))
    return KGDetail(**kg)


@router.get("/agent-context/{drug_id}", response_model=AgentContext)
def get_agent_context(drug_id: str) -> AgentContext:
    candidate = _get_candidate_or_404(drug_id)
    tiers = _pg_fetch_all(
        """
        SELECT rank, tier, score, payload, source_s3_uri
        FROM drug_candidate_tier
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC, tier ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    finals = _pg_fetch_all(
        """
        SELECT rank, final_verdict, payload, source_s3_uri
        FROM final_candidate_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    admet_rows = _pg_fetch_all(
        """
        SELECT rank, admet_verdict, hard_fail, score, payload, source_s3_uri
        FROM admet_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    validation_rows = _pg_fetch_all(
        """
        SELECT validation_source, rank, validation_score, payload, source_s3_uri
        FROM external_validation_result
        WHERE disease = :disease
          AND run_id = :run_id
          AND drug_id = :drug_id
        ORDER BY validation_source ASC, rank ASC
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )
    metrics = _pg_fetch_all(
        """
        SELECT model, metric, metric_value, source_s3_uri
        FROM model_metric
        WHERE disease = :disease
          AND run_id = :run_id
        ORDER BY model ASC, metric ASC
        LIMIT 200
        """,
        {"disease": DISEASE, "run_id": RUN_ID},
    )
    kg = _get_kg_context(drug_id, candidate.get("drug_name"))

    source_rows = _pg_fetch_all(
        """
        SELECT DISTINCT source_s3_uri
        FROM (
          SELECT source_s3_uri FROM drug_candidate_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM drug_candidate_tier WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM final_candidate_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM admet_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM external_validation_result WHERE disease=:disease AND run_id=:run_id AND drug_id=:drug_id
          UNION ALL
          SELECT source_s3_uri FROM source_artifact WHERE disease=:disease AND run_id=:run_id
          UNION ALL
          SELECT source_s3_uri FROM run_manifest WHERE disease=:disease AND run_id=:run_id
        ) s
        WHERE source_s3_uri IS NOT NULL
          AND source_s3_uri <> ''
        ORDER BY source_s3_uri
        """,
        {"disease": DISEASE, "run_id": RUN_ID, "drug_id": drug_id},
    )

    warnings: List[str] = []
    if not tiers:
        warnings.append("No tier rationale rows found in drug_candidate_tier.")
    if not finals:
        warnings.append("Drug is not present in final_candidate_result (final15 may be false).")
    if not admet_rows:
        warnings.append("No ADMET rows found for this drug.")
    if not validation_rows:
        warnings.append("No external validation rows found for this drug.")
    if not kg.get("genes"):
        warnings.append("No target genes found in Neo4j for this drug.")
    if not kg.get("pathways"):
        warnings.append("No pathways found in Neo4j for this drug.")

    return AgentContext(
        drug_id=drug_id,
        candidate_ranking=candidate,
        tier_rationale=tiers,
        final15_status={"is_final15": bool(finals), "rows": finals},
        admet_result=admet_rows,
        external_validation_result=validation_rows,
        model_metric_summary=metrics,
        neo4j_context=kg,
        source_s3_uri_list=[row["source_s3_uri"] for row in source_rows],
        warnings_caveats=warnings,
    )
