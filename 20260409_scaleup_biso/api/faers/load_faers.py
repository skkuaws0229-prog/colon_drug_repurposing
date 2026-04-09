"""
FDA FAERS 부작용 데이터 수집 → Neo4j 적재

엔드포인트: https://api.fda.gov/drug/event.json
키 불필요 (1000건/일 제한)
"""

import os
import time
from pathlib import Path

import requests
from neo4j import GraphDatabase
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

FAERS_URL = "https://api.fda.gov/drug/event.json"


def get_pipeline_drugs(driver) -> list[str]:
    with driver.session(database=DATABASE) as session:
        result = session.run(
            'MATCH (d:Drug) WHERE d.disease_code = "BRCA" '
            "RETURN d.name AS name ORDER BY d.rank"
        ).data()
    return [r["name"] for r in result]


def fetch_side_effects(drug_name: str, limit: int = 10) -> list[dict] | None:
    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": limit,
    }
    try:
        resp = requests.get(FAERS_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"    ✗ API 에러: {e}")
        return None


def load_to_neo4j(driver, drug_name: str, side_effects: list[dict]):
    with driver.session(database=DATABASE) as session:
        for rank, se in enumerate(side_effects, 1):
            session.run(
                """
                MERGE (s:SideEffect {name: $name})
                SET s.meddra_term = $name
                WITH s
                MATCH (d:Drug {name: $drug_name})
                MERGE (d)-[r:HAS_SIDE_EFFECT]->(s)
                SET r.count          = $count,
                    r.frequency_rank = $rank
                """,
                name=se["term"],
                drug_name=drug_name,
                count=se["count"],
                rank=rank,
            )


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    drugs = get_pipeline_drugs(driver)
    print(f"대상 약물: {len(drugs)}개\n")

    total_se = 0
    total_edges = 0

    for i, drug in enumerate(drugs, 1):
        print(f"  [{i}/{len(drugs)}] {drug} ... ", end="", flush=True)

        results = fetch_side_effects(drug)
        if results is None:
            print("건너뜀")
        elif len(results) == 0:
            print("부작용 데이터 없음")
        else:
            load_to_neo4j(driver, drug, results)
            total_se += len(results)
            total_edges += len(results)
            print(f"✓ {len(results)}개 부작용")

        if i < len(drugs):
            time.sleep(1)

    # 통계
    with driver.session(database=DATABASE) as session:
        se_cnt = session.run("MATCH (s:SideEffect) RETURN count(s) AS cnt").single()["cnt"]
        edge_cnt = session.run("MATCH ()-[r:HAS_SIDE_EFFECT]->() RETURN count(r) AS cnt").single()["cnt"]

    print(f"\n{'='*50}")
    print(f"  FAERS 적재 완료")
    print(f"{'='*50}")
    print(f"  SideEffect 노드: {se_cnt}개")
    print(f"  HAS_SIDE_EFFECT 엣지: {edge_cnt}개")

    driver.close()


if __name__ == "__main__":
    main()
