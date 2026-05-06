#!/usr/bin/env python
"""Validate BRCA Neo4j KG and write a JSON report."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from neo4j import GraphDatabase


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("brca_kg_check")

DISEASE = "BRCA"
RUN_ID = "BRCA_RELEASE_V1"
REPORT_PATH = Path("outputs/kg_validation/brca_kg_validation_report.json")

DEFAULT_NEO4J = {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "1234",
    "NEO4J_DATABASE": "neo4j",
}

LABELS = [
    "Disease",
    "Run",
    "Drug",
    "CandidateResult",
    "FinalCandidate",
    "ADMETResult",
    "ValidationResult",
    "Gene",
    "Pathway",
    "Model",
    "Metric",
    "SourceArtifact",
]

REL_TYPES = [
    "CANDIDATE_FOR",
    "HAS_RANKING",
    "SELECTED_AS_FINAL",
    "HAS_ADMET",
    "VALIDATED_BY",
    "TARGETS",
    "ASSOCIATED_WITH",
    "INVOLVED_IN",
    "HAS_METRIC",
    "PRODUCED",
    "USED_SOURCE",
]


def env(name: str) -> str:
    return os.getenv(name, DEFAULT_NEO4J[name])


def neo4j_conf() -> Dict[str, str]:
    return {
        "uri": env("NEO4J_URI"),
        "user": env("NEO4J_USER"),
        "password": env("NEO4J_PASSWORD"),
        "database": env("NEO4J_DATABASE"),
    }


def records_to_dicts(result: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for record in result:
        out.append(dict(record))
    return out


def count_labels(session: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for label in LABELS:
        res = session.run(f"MATCH (n:{label}) RETURN count(n) AS n")
        out[label] = int(res.single()["n"])
    return out


def count_relationships(session: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for rel in REL_TYPES:
        res = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS n")
        out[rel] = int(res.single()["n"])
    return out


def main() -> int:
    conf = neo4j_conf()
    LOGGER.info("Neo4j target: uri=%s database=%s user=%s", conf["uri"], conf["database"], conf["user"])
    LOGGER.info("Validation scope: disease=%s run_id=%s", DISEASE, RUN_ID)

    driver = GraphDatabase.driver(conf["uri"], auth=(conf["user"], conf["password"]))
    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disease": DISEASE,
        "run_id": RUN_ID,
    }

    try:
        with driver.session(database=conf["database"]) as session:
            label_counts = count_labels(session)
            rel_counts = count_relationships(session)
            report["node_counts_by_label"] = label_counts
            report["relationship_counts_by_type"] = rel_counts

            LOGGER.info("Node counts by label:")
            for label, n in label_counts.items():
                LOGGER.info(" - %s: %s", label, n)

            LOGGER.info("Relationship counts by type:")
            for rel, n in rel_counts.items():
                LOGGER.info(" - %s: %s", rel, n)

            top30 = session.run(
                """
                MATCH (d:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                WHERE r.run_id=$run_id
                RETURN d.drug_id AS drug_id, d.name AS drug_name, r.rank AS rank, r.score AS score
                ORDER BY rank ASC, drug_name ASC
                LIMIT 30
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["top30_brca_candidate_drugs"] = records_to_dicts(top30)

            final15 = session.run(
                """
                MATCH (d:Drug)-[:SELECTED_AS_FINAL]->(f:FinalCandidate {disease:$disease, run_id:$run_id})
                RETURN d.drug_id AS drug_id, d.name AS drug_name, f.rank AS rank, f.final_verdict AS final_verdict
                ORDER BY rank ASC, drug_name ASC
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["final15_candidates"] = records_to_dicts(final15)

            no_admet = session.run(
                """
                MATCH (d:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                WHERE r.run_id=$run_id
                  AND NOT (d)-[:HAS_ADMET]->(:ADMETResult {disease:$disease, run_id:$run_id})
                RETURN d.drug_id AS drug_id, d.name AS drug_name, r.rank AS rank
                ORDER BY rank ASC, drug_name ASC
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["candidate_drugs_without_admet"] = records_to_dicts(no_admet)

            no_validation = session.run(
                """
                MATCH (d:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                WHERE r.run_id=$run_id
                OPTIONAL MATCH (d)-[:VALIDATED_BY]->(v:ValidationResult {disease:$disease, run_id:$run_id})
                WITH d, r, collect(toLower(coalesce(v.validation_source, ""))) AS sources
                WHERE NONE(src IN sources WHERE src CONTAINS "metabric")
                RETURN d.drug_id AS drug_id, d.name AS drug_name, r.rank AS rank
                ORDER BY rank ASC, drug_name ASC
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["candidate_drugs_without_metabric_validation"] = records_to_dicts(no_validation)

            with_genes = session.run(
                """
                MATCH (d:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                WHERE r.run_id=$run_id
                MATCH (d)-[:TARGETS]->(g:Gene)
                RETURN d.drug_id AS drug_id, d.name AS drug_name, count(DISTINCT g) AS gene_count
                ORDER BY gene_count DESC, drug_name ASC
                LIMIT 50
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["drugs_with_target_genes"] = records_to_dicts(with_genes)

            with_pathways = session.run(
                """
                MATCH (d:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                WHERE r.run_id=$run_id
                MATCH (d)-[:TARGETS]->(:Gene)-[:INVOLVED_IN]->(p:Pathway)
                RETURN d.drug_id AS drug_id, d.name AS drug_name, count(DISTINCT p) AS pathway_count
                ORDER BY pathway_count DESC, drug_name ASC
                LIMIT 50
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["drugs_with_pathways"] = records_to_dicts(with_pathways)

            hard_fail = session.run(
                """
                MATCH (d:Drug)-[:HAS_ADMET]->(a:ADMETResult {disease:$disease, run_id:$run_id})
                WHERE a.hard_fail = true
                RETURN d.drug_id AS drug_id, d.name AS drug_name, a.rank AS rank, a.verdict AS verdict
                ORDER BY rank ASC, drug_name ASC
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["drugs_with_hard_fail_admet"] = records_to_dicts(hard_fail)

            top_validation = session.run(
                """
                MATCH (d:Drug)-[:VALIDATED_BY]->(v:ValidationResult {disease:$disease, run_id:$run_id})
                RETURN d.drug_id AS drug_id, d.name AS drug_name, max(v.validation_score) AS top_validation_score
                ORDER BY top_validation_score DESC, drug_name ASC
                LIMIT 30
                """,
                disease=DISEASE,
                run_id=RUN_ID,
            )
            report["top_validation_score_drugs"] = records_to_dicts(top_validation)

            check_drug_count = int(
                session.run("MATCH (d:Drug) RETURN count(d) AS n").single()["n"]
            )
            check_candidate_rel = int(
                session.run(
                    """
                    MATCH (:Drug)-[r:CANDIDATE_FOR]->(:Disease {name:$disease})
                    WHERE r.run_id=$run_id
                    RETURN count(r) AS n
                    """,
                    disease=DISEASE,
                    run_id=RUN_ID,
                ).single()["n"]
            )
            check_has_admet_rel = int(
                session.run(
                    """
                    MATCH (:Drug)-[r:HAS_ADMET]->(:ADMETResult {disease:$disease, run_id:$run_id})
                    RETURN count(r) AS n
                    """,
                    disease=DISEASE,
                    run_id=RUN_ID,
                ).single()["n"]
            )
            check_validated_by_rel = int(
                session.run(
                    """
                    MATCH (:Drug)-[r:VALIDATED_BY]->(:ValidationResult {disease:$disease, run_id:$run_id})
                    RETURN count(r) AS n
                    """,
                    disease=DISEASE,
                    run_id=RUN_ID,
                ).single()["n"]
            )

            report["critical_checks"] = {
                "drug_count": check_drug_count,
                "candidate_for_rel_count": check_candidate_rel,
                "has_admet_rel_count": check_has_admet_rel,
                "validated_by_rel_count": check_validated_by_rel,
            }
    except Exception as exc:
        LOGGER.error("Neo4j validation failed: %s", exc)
        return 1
    finally:
        driver.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Saved KG validation report: %s", REPORT_PATH)

    checks = report["critical_checks"]
    if checks["drug_count"] == 0:
        LOGGER.error("Drug count is 0")
        return 2
    if checks["candidate_for_rel_count"] == 0:
        LOGGER.error("CANDIDATE_FOR relationship count is 0")
        return 2
    if checks["has_admet_rel_count"] == 0:
        LOGGER.error("HAS_ADMET relationship count is 0")
        return 2
    if checks["validated_by_rel_count"] == 0:
        LOGGER.error("VALIDATED_BY relationship count is 0")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
