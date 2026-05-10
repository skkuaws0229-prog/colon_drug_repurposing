#!/usr/bin/env python
"""Load BRCA Neo4j KG from PostgreSQL tables (source of truth)."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote_plus

from neo4j import GraphDatabase
from sqlalchemy import create_engine, text


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger("brca_kg_loader")

DISEASE = "BRCA"
RUN_ID = "BRCA_RELEASE_V1"
REPORT_PATH = Path("outputs/kg_validation/brca_kg_load_report.json")

DEFAULT_POSTGRES = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "Drug",
    "POSTGRES_USER": "Drug",
    "POSTGRES_PASSWORD": "1234",
}

DEFAULT_NEO4J = {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "1234",
    "NEO4J_DATABASE": "neo4j",
}

LABELS_TO_COUNT = [
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

RELS_TO_COUNT = [
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


def env(name: str, defaults: Dict[str, str]) -> str:
    return os.getenv(name, defaults[name])


def postgres_url() -> str:
    user = env("POSTGRES_USER", DEFAULT_POSTGRES)
    password = quote_plus(env("POSTGRES_PASSWORD", DEFAULT_POSTGRES))
    host = env("POSTGRES_HOST", DEFAULT_POSTGRES)
    port = env("POSTGRES_PORT", DEFAULT_POSTGRES)
    db = env("POSTGRES_DB", DEFAULT_POSTGRES)
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def neo4j_conf() -> Dict[str, str]:
    return {
        "uri": env("NEO4J_URI", DEFAULT_NEO4J),
        "user": env("NEO4J_USER", DEFAULT_NEO4J),
        "password": env("NEO4J_PASSWORD", DEFAULT_NEO4J),
        "database": env("NEO4J_DATABASE", DEFAULT_NEO4J),
    }


def as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def first_nonempty(record: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key not in record:
            continue
        value = record[key]
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value == "":
            continue
        return value
    return default


def split_multi(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    text_value = str(value).strip()
    if not text_value:
        return []
    parts = [p.strip() for p in re.split(r"[,\n;|/]+", text_value) if p.strip()]
    out: List[str] = []
    for part in parts:
        if part not in out:
            out.append(part)
    return out


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "t", "yes", "y", "pass", "passed"}:
        return True
    if text_value in {"0", "false", "f", "no", "n", "fail", "failed"}:
        return False
    return None


def table_columns(conn: Any, table_name: str) -> List[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            ORDER BY ordinal_position
            """
        ),
        {"table_name": table_name},
    ).mappings()
    return [r["column_name"] for r in rows]


def fetch_rows(conn: Any, table_name: str, wanted_columns: List[str]) -> List[Dict[str, Any]]:
    cols = table_columns(conn, table_name)
    if "disease" not in cols or "run_id" not in cols:
        LOGGER.warning("Skipping table %s: disease/run_id columns missing", table_name)
        return []

    selected = [col for col in wanted_columns if col in cols]
    if "payload" in cols and "payload" not in selected:
        selected.append("payload")
    if not selected:
        LOGGER.warning("Skipping table %s: no requested columns present", table_name)
        return []

    sql = text(
        f"""
        SELECT {", ".join(selected)}
        FROM {table_name}
        WHERE disease = :disease
          AND run_id = :run_id
        """
    )
    rows = conn.execute(sql, {"disease": DISEASE, "run_id": RUN_ID}).mappings().all()
    return [dict(row) for row in rows]


def create_constraints(session: Any) -> None:
    constraints = [
        ("disease_name_unique", "Disease", "name"),
        ("run_id_unique", "Run", "run_id"),
        ("drug_id_unique", "Drug", "drug_id"),
        ("candidate_key_unique", "CandidateResult", "candidate_key"),
        ("final_key_unique", "FinalCandidate", "final_key"),
        ("admet_key_unique", "ADMETResult", "admet_key"),
        ("validation_key_unique", "ValidationResult", "validation_key"),
        ("gene_symbol_unique", "Gene", "symbol"),
        ("pathway_name_unique", "Pathway", "name"),
        ("model_key_unique", "Model", "model_key"),
        ("metric_key_unique", "Metric", "metric_key"),
        ("source_key_unique", "SourceArtifact", "source_key"),
    ]
    for name, label, prop in constraints:
        session.run(
            f"""
            CREATE CONSTRAINT {name} IF NOT EXISTS
            FOR (n:{label})
            REQUIRE n.{prop} IS UNIQUE
            """
        )


def merge_base_graph(session: Any) -> None:
    session.run(
        """
        MERGE (d:Disease {name:$disease})
        ON CREATE SET d.display_name='Breast Cancer', d.created_at=datetime()
        SET d.display_name='Breast Cancer', d.updated_at=datetime()
        """,
        disease=DISEASE,
    )
    session.run(
        """
        MERGE (r:Run {run_id:$run_id})
        ON CREATE SET r.created_at=datetime()
        SET r.disease=$disease, r.updated_at=datetime()
        """,
        run_id=RUN_ID,
        disease=DISEASE,
    )


def load_candidates(session: Any, rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        payload = as_dict(row.get("payload"))
        drug_id = str(row.get("drug_id") or "").strip()
        if not drug_id:
            continue
        drug_name = str(row.get("drug_name") or "").strip()
        rank = row.get("rank")
        score = to_float(row.get("score"))
        source_s3_uri = str(row.get("source_s3_uri") or "")
        canonical_smiles = first_nonempty(payload, ["canonical_smiles", "smiles"], None)
        confidence_grade = first_nonempty(payload, ["confidence_grade"], None)
        candidate_key = f"{RUN_ID}|{source_s3_uri}|{drug_id}|{rank}"

        session.run(
            """
            MATCH (dis:Disease {name:$disease})
            MATCH (run:Run {run_id:$run_id})
            MERGE (d:Drug {drug_id:$drug_id})
            ON CREATE SET d.created_at=datetime()
            SET d.name=coalesce($drug_name, d.name),
                d.canonical_smiles=coalesce($canonical_smiles, d.canonical_smiles),
                d.updated_at=datetime()
            MERGE (cr:CandidateResult {candidate_key:$candidate_key})
            ON CREATE SET cr.created_at=datetime()
            SET cr.disease=$disease,
                cr.run_id=$run_id,
                cr.source_s3_uri=$source_s3_uri,
                cr.rank=$rank,
                cr.score=$score,
                cr.confidence_grade=$confidence_grade,
                cr.updated_at=datetime()
            MERGE (d)-[r:CANDIDATE_FOR {run_id:$run_id}]->(dis)
            SET r.rank=$rank,
                r.score=$score,
                r.confidence_grade=$confidence_grade
            MERGE (d)-[:HAS_RANKING]->(cr)
            MERGE (run)-[:PRODUCED]->(cr)
            """,
            disease=DISEASE,
            run_id=RUN_ID,
            drug_id=drug_id,
            drug_name=drug_name or None,
            canonical_smiles=canonical_smiles,
            source_s3_uri=source_s3_uri,
            rank=rank,
            score=score,
            confidence_grade=confidence_grade,
            candidate_key=candidate_key,
        )
        count += 1
    return count


def load_final_candidates(session: Any, rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        drug_id = str(row.get("drug_id") or "").strip()
        if not drug_id:
            continue
        drug_name = str(row.get("drug_name") or "").strip()
        rank = row.get("rank")
        source_s3_uri = str(row.get("source_s3_uri") or "")
        final_verdict = row.get("final_verdict")
        final_key = f"{RUN_ID}|{source_s3_uri}|{drug_id}|{rank}"

        session.run(
            """
            MERGE (d:Drug {drug_id:$drug_id})
            ON CREATE SET d.created_at=datetime()
            SET d.name=coalesce($drug_name, d.name), d.updated_at=datetime()
            MERGE (f:FinalCandidate {final_key:$final_key})
            ON CREATE SET f.created_at=datetime()
            SET f.disease=$disease,
                f.run_id=$run_id,
                f.rank=$rank,
                f.final_verdict=$final_verdict,
                f.source_s3_uri=$source_s3_uri,
                f.updated_at=datetime()
            MERGE (d)-[:SELECTED_AS_FINAL]->(f)
            """,
            drug_id=drug_id,
            drug_name=drug_name or None,
            final_key=final_key,
            disease=DISEASE,
            run_id=RUN_ID,
            rank=rank,
            final_verdict=final_verdict,
            source_s3_uri=source_s3_uri,
        )
        count += 1
    return count


def load_admet(session: Any, rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        payload = as_dict(row.get("payload"))
        drug_id = str(row.get("drug_id") or "").strip()
        if not drug_id:
            continue
        drug_name = str(row.get("drug_name") or "").strip()
        rank = row.get("rank")
        source_s3_uri = str(row.get("source_s3_uri") or "")
        admet_key = f"{RUN_ID}|{source_s3_uri}|{drug_id}|{rank}"

        verdict = first_nonempty({"v": row.get("admet_verdict")}, ["v"], None)
        safety_score = first_nonempty(payload, ["safety_score", "score"], row.get("score"))
        hard_fail = to_bool(row.get("hard_fail"))
        hard_fail_reasons = first_nonempty(payload, ["hard_fail_reasons", "flags"], None)
        herg_value = first_nonempty(payload, ["herg_value", "herg_risk"], None)
        ames_value = first_nonempty(payload, ["ames_value", "ames_risk"], None)
        dili_value = first_nonempty(payload, ["dili_value", "dili_risk"], None)
        lipinski_violations = first_nonempty(payload, ["lipinski_violations"], None)

        session.run(
            """
            MERGE (d:Drug {drug_id:$drug_id})
            ON CREATE SET d.created_at=datetime()
            SET d.name=coalesce($drug_name, d.name), d.updated_at=datetime()
            MERGE (a:ADMETResult {admet_key:$admet_key})
            ON CREATE SET a.created_at=datetime()
            SET a.disease=$disease,
                a.run_id=$run_id,
                a.rank=$rank,
                a.source_s3_uri=$source_s3_uri,
                a.verdict=$verdict,
                a.safety_score=$safety_score,
                a.hard_fail=$hard_fail,
                a.hard_fail_reasons=$hard_fail_reasons,
                a.herg_value=$herg_value,
                a.ames_value=$ames_value,
                a.dili_value=$dili_value,
                a.lipinski_violations=$lipinski_violations,
                a.updated_at=datetime()
            MERGE (d)-[:HAS_ADMET]->(a)
            """,
            drug_id=drug_id,
            drug_name=drug_name or None,
            admet_key=admet_key,
            disease=DISEASE,
            run_id=RUN_ID,
            rank=rank,
            source_s3_uri=source_s3_uri,
            verdict=verdict,
            safety_score=to_float(safety_score),
            hard_fail=hard_fail,
            hard_fail_reasons=str(hard_fail_reasons) if hard_fail_reasons is not None else None,
            herg_value=to_float(herg_value),
            ames_value=to_float(ames_value),
            dili_value=to_float(dili_value),
            lipinski_violations=to_float(lipinski_violations),
        )
        count += 1
    return count


def load_validations_and_biology(session: Any, rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        payload = as_dict(row.get("payload"))
        drug_id = str(row.get("drug_id") or "").strip()
        if not drug_id:
            continue
        drug_name = str(row.get("drug_name") or "").strip()
        rank = row.get("rank")
        source_s3_uri = str(row.get("source_s3_uri") or "")
        validation_source = str(row.get("validation_source") or "")
        validation_key = f"{RUN_ID}|{source_s3_uri}|{validation_source}|{drug_id}|{rank}"

        validation_score = first_nonempty(payload, ["validation_score"], row.get("validation_score"))
        target_expressed = first_nonempty(payload, ["target_expressed"], None)
        brca_pathway = first_nonempty(payload, ["brca_pathway"], None)
        survival_sig = first_nonempty(payload, ["survival_sig"], None)
        survival_p = first_nonempty(payload, ["survival_p"], None)
        known_brca = first_nonempty(payload, ["known_brca"], None)

        session.run(
            """
            MATCH (dis:Disease {name:$disease})
            MERGE (d:Drug {drug_id:$drug_id})
            ON CREATE SET d.created_at=datetime()
            SET d.name=coalesce($drug_name, d.name), d.updated_at=datetime()
            MERGE (v:ValidationResult {validation_key:$validation_key})
            ON CREATE SET v.created_at=datetime()
            SET v.disease=$disease,
                v.run_id=$run_id,
                v.rank=$rank,
                v.source_s3_uri=$source_s3_uri,
                v.validation_source=$validation_source,
                v.validation_score=$validation_score,
                v.target_expressed=$target_expressed,
                v.brca_pathway=$brca_pathway,
                v.survival_sig=$survival_sig,
                v.survival_p=$survival_p,
                v.known_brca=$known_brca,
                v.updated_at=datetime()
            MERGE (d)-[:VALIDATED_BY]->(v)
            MERGE (d)-[:CANDIDATE_FOR {run_id:$run_id}]->(dis)
            """,
            disease=DISEASE,
            run_id=RUN_ID,
            drug_id=drug_id,
            drug_name=drug_name or None,
            validation_key=validation_key,
            rank=rank,
            source_s3_uri=source_s3_uri,
            validation_source=validation_source,
            validation_score=to_float(validation_score),
            target_expressed=to_float(target_expressed),
            brca_pathway=to_float(brca_pathway),
            survival_sig=to_float(survival_sig),
            survival_p=to_float(survival_p),
            known_brca=to_float(known_brca),
        )

        gene_values = split_multi(first_nonempty(payload, ["target_gene", "gene", "target"], None))
        pathway_values = split_multi(first_nonempty(payload, ["pathway", "pathway_name"], None))

        for gene_symbol in gene_values:
            session.run(
                """
                MATCH (d:Drug {drug_id:$drug_id})
                MATCH (dis:Disease {name:$disease})
                MERGE (g:Gene {symbol:$symbol})
                ON CREATE SET g.created_at=datetime()
                SET g.updated_at=datetime()
                MERGE (d)-[:TARGETS]->(g)
                MERGE (g)-[:ASSOCIATED_WITH]->(dis)
                """,
                drug_id=drug_id,
                disease=DISEASE,
                symbol=gene_symbol,
            )
            for pathway_name in pathway_values:
                session.run(
                    """
                    MATCH (g:Gene {symbol:$symbol})
                    MERGE (p:Pathway {name:$pathway_name})
                    ON CREATE SET p.created_at=datetime()
                    SET p.updated_at=datetime()
                    MERGE (g)-[:INVOLVED_IN]->(p)
                    """,
                    symbol=gene_symbol,
                    pathway_name=pathway_name,
                )

        count += 1
    return count


def load_models_and_metrics(session: Any, rows: List[Dict[str, Any]], source_table: str) -> int:
    count = 0
    for row in rows:
        model_name = str(row.get("model") or "").strip()
        metric_name = str(row.get("metric") or "").strip()
        if not model_name or not metric_name:
            continue

        phase = str(row.get("phase") or "")
        family = str(row.get("family") or "")
        split = str(row.get("split") or "")
        source_model_dir = str(row.get("source_model_dir") or "")
        metric_value = to_float(row.get("metric_value"))

        model_key = f"{RUN_ID}|{phase}|{family}|{model_name}|{source_model_dir}"
        metric_key = f"{model_key}|{split}|{metric_name}|{source_table}"

        session.run(
            """
            MERGE (m:Model {model_key:$model_key})
            ON CREATE SET m.created_at=datetime()
            SET m.disease=$disease,
                m.run_id=$run_id,
                m.phase=$phase,
                m.family=$family,
                m.model=$model,
                m.source_model_dir=$source_model_dir,
                m.updated_at=datetime()
            MERGE (mt:Metric {metric_key:$metric_key})
            ON CREATE SET mt.created_at=datetime()
            SET mt.disease=$disease,
                mt.run_id=$run_id,
                mt.phase=$phase,
                mt.family=$family,
                mt.model=$model,
                mt.metric=$metric,
                mt.metric_value=$metric_value,
                mt.source_model_dir=$source_model_dir,
                mt.split=$split,
                mt.source_table=$source_table,
                mt.updated_at=datetime()
            MERGE (m)-[:HAS_METRIC]->(mt)
            """,
            model_key=model_key,
            metric_key=metric_key,
            disease=DISEASE,
            run_id=RUN_ID,
            phase=phase,
            family=family,
            model=model_name,
            metric=metric_name,
            metric_value=metric_value,
            source_model_dir=source_model_dir,
            split=split,
            source_table=source_table,
        )
        count += 1
    return count


def load_source_artifacts(session: Any, rows: List[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        source_s3_uri = str(row.get("source_s3_uri") or "")
        artifact_name = str(row.get("artifact_name") or "")
        artifact_uri = str(row.get("artifact_uri") or "")
        source_key = f"{RUN_ID}|{source_s3_uri}|{artifact_name}|{artifact_uri}"
        payload = as_dict(row.get("payload"))
        artifact_type = row.get("artifact_type")
        artifact_hash = row.get("artifact_hash")

        session.run(
            """
            MATCH (run:Run {run_id:$run_id})
            MERGE (s:SourceArtifact {source_key:$source_key})
            ON CREATE SET s.created_at=datetime()
            SET s.disease=$disease,
                s.run_id=$run_id,
                s.source_s3_uri=$source_s3_uri,
                s.artifact_name=$artifact_name,
                s.artifact_uri=$artifact_uri,
                s.artifact_type=$artifact_type,
                s.artifact_hash=$artifact_hash,
                s.payload_json=$payload_json,
                s.updated_at=datetime()
            MERGE (run)-[:USED_SOURCE]->(s)
            """,
            run_id=RUN_ID,
            disease=DISEASE,
            source_key=source_key,
            source_s3_uri=source_s3_uri,
            artifact_name=artifact_name,
            artifact_uri=artifact_uri,
            artifact_type=artifact_type,
            artifact_hash=artifact_hash,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
        )
        count += 1
    return count


def count_labels(session: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for label in LABELS_TO_COUNT:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS n")
        out[label] = int(result.single()["n"])
    return out


def count_relationships(session: Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for rel_type in RELS_TO_COUNT:
        result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS n")
        out[rel_type] = int(result.single()["n"])
    return out


def main() -> int:
    pg_engine = create_engine(postgres_url(), future=True)
    n4j = neo4j_conf()

    LOGGER.info("PostgreSQL target: host=%s port=%s db=%s user=%s", env("POSTGRES_HOST", DEFAULT_POSTGRES), env("POSTGRES_PORT", DEFAULT_POSTGRES), env("POSTGRES_DB", DEFAULT_POSTGRES), env("POSTGRES_USER", DEFAULT_POSTGRES))
    LOGGER.info("Neo4j target: uri=%s database=%s user=%s", n4j["uri"], n4j["database"], n4j["user"])
    LOGGER.info("KG scope: disease=%s run_id=%s (PostgreSQL only)", DISEASE, RUN_ID)

    try:
        with pg_engine.connect() as pg_conn:
            candidates = fetch_rows(
                pg_conn,
                "drug_candidate_result",
                ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank", "score", "payload"],
            )
            finals = fetch_rows(
                pg_conn,
                "final_candidate_result",
                ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank", "final_verdict", "payload"],
            )
            admet = fetch_rows(
                pg_conn,
                "admet_result",
                ["disease", "run_id", "source_s3_uri", "drug_id", "drug_name", "rank", "admet_verdict", "hard_fail", "score", "payload"],
            )
            validations = fetch_rows(
                pg_conn,
                "external_validation_result",
                ["disease", "run_id", "source_s3_uri", "validation_source", "drug_id", "drug_name", "rank", "validation_score", "payload"],
            )
            model_metric = fetch_rows(
                pg_conn,
                "model_metric",
                ["disease", "run_id", "source_s3_uri", "phase", "family", "model", "metric", "metric_value", "source_model_dir", "payload"],
            )
            model_metric_detailed = fetch_rows(
                pg_conn,
                "model_metric_detailed",
                ["disease", "run_id", "source_s3_uri", "phase", "family", "model", "split", "metric", "metric_value", "source_model_dir", "payload"],
            )
            source_artifacts = fetch_rows(
                pg_conn,
                "source_artifact",
                ["disease", "run_id", "source_s3_uri", "artifact_name", "artifact_type", "artifact_uri", "artifact_hash", "payload"],
            )
    except Exception as exc:
        LOGGER.error("Failed to read PostgreSQL data: %s", exc)
        return 1

    counters = {
        "candidate_rows": len(candidates),
        "final_rows": len(finals),
        "admet_rows": len(admet),
        "validation_rows": len(validations),
        "model_metric_rows": len(model_metric),
        "model_metric_detailed_rows": len(model_metric_detailed),
        "source_artifact_rows": len(source_artifacts),
    }

    driver = GraphDatabase.driver(n4j["uri"], auth=(n4j["user"], n4j["password"]))
    try:
        with driver.session(database=n4j["database"]) as session:
            create_constraints(session)
            merge_base_graph(session)

            loaded = {
                "candidates_loaded": load_candidates(session, candidates),
                "final_loaded": load_final_candidates(session, finals),
                "admet_loaded": load_admet(session, admet),
                "validation_loaded": load_validations_and_biology(session, validations),
                "model_metric_loaded": load_models_and_metrics(session, model_metric, "model_metric"),
                "model_metric_detailed_loaded": load_models_and_metrics(session, model_metric_detailed, "model_metric_detailed"),
                "source_artifact_loaded": load_source_artifacts(session, source_artifacts),
            }

            node_counts = count_labels(session)
            rel_counts = count_relationships(session)
    except Exception as exc:
        LOGGER.error("Failed to write Neo4j graph: %s", exc)
        return 1
    finally:
        driver.close()

    LOGGER.info("Node counts:")
    for label, count in node_counts.items():
        LOGGER.info(" - %s: %s", label, count)

    LOGGER.info("Relationship counts:")
    for rel_type, count in rel_counts.items():
        LOGGER.info(" - %s: %s", rel_type, count)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disease": DISEASE,
        "run_id": RUN_ID,
        "postgres_rows": counters,
        "loaded_rows": loaded,
        "node_counts": node_counts,
        "relationship_counts": rel_counts,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Saved KG load report: %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
