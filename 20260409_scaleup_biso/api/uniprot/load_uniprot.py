"""
UniProt API → Target 노드 속성 보강

엔드포인트: https://rest.uniprot.org/uniprotkb/search
키 불필요 · 무료
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

UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/search"


def get_target_genes(driver, limit: int = 500) -> list[str]:
    with driver.session(database=DATABASE) as session:
        return [
            r["gs"]
            for r in session.run(
                "MATCH (t:Target) WHERE t.gene_symbol IS NOT NULL "
                f"RETURN t.gene_symbol AS gs LIMIT {limit}"
            ).data()
        ]


def fetch_uniprot(gene_symbol: str) -> dict | None:
    params = {
        "query": f"gene:{gene_symbol} AND organism_id:9606",
        "fields": "accession,gene_names,protein_name,cc_function,keyword",
        "format": "json",
        "size": 1,
    }
    try:
        resp = requests.get(UNIPROT_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        entry = results[0]

        # accession
        uniprot_id = entry.get("primaryAccession", "")

        # protein name
        protein_desc = entry.get("proteinDescription", {})
        rec_name = protein_desc.get("recommendedName", {})
        full_name = rec_name.get("fullName", {}).get("value", "")

        # function
        comments = entry.get("comments", [])
        function_text = ""
        for c in comments:
            if c.get("commentType") == "FUNCTION":
                texts = c.get("texts", [])
                if texts:
                    function_text = texts[0].get("value", "")
                break

        # keywords
        kw_list = entry.get("keywords", [])
        keywords = [k.get("name", "") for k in kw_list[:10]]

        return {
            "uniprot_id": uniprot_id,
            "protein_full_name": full_name,
            "function": function_text[:500] if function_text else None,
            "keywords": keywords if keywords else None,
        }
    except Exception as e:
        print(f"에러: {e}")
        return None


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    genes = get_target_genes(driver, limit=500)
    print(f"대상 Target: {len(genes)}개 (gene_symbol 있는 것)\n")

    updated = 0
    failed = 0
    for i, gene in enumerate(genes, 1):
        if i % 50 == 1 or i <= 5:
            print(f"  [{i}/{len(genes)}] {gene} ... ", end="", flush=True)

        info = fetch_uniprot(gene)
        if not info:
            failed += 1
            if i % 50 == 1 or i <= 5:
                print("없음")
        else:
            with driver.session(database=DATABASE) as session:
                session.run(
                    """
                    MATCH (t:Target {gene_symbol: $gene_symbol})
                    SET t.uniprot_id        = $uniprot_id,
                        t.protein_full_name = $protein_full_name,
                        t.function          = $function,
                        t.keywords          = $keywords
                    """,
                    gene_symbol=gene,
                    **info,
                )
            updated += 1
            if i % 50 == 1 or i <= 5:
                print(f"✓ {info['uniprot_id']} ({info['protein_full_name'][:40]})")

        if i < len(genes):
            time.sleep(0.5)

        # 진행률 (50개마다)
        if i % 50 == 0:
            print(f"    ... {i}/{len(genes)} 완료 ({updated} 성공, {failed} 실패)")

    print(f"\n{'='*50}")
    print(f"  UniProt API 완료: {updated}/{len(genes)} Target 업데이트")
    print(f"  실패: {failed}개")
    print(f"{'='*50}")

    # 전체 통계
    with driver.session(database=DATABASE) as session:
        nodes = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label"
        ).data()
        edges = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY type"
        ).data()

    total_n = sum(n["cnt"] for n in nodes)
    total_e = sum(e["cnt"] for e in edges)

    print(f"\n{'='*50}")
    print(f"  Neo4j 전체 통계")
    print(f"{'='*50}")
    print(f"\n  노드 ({total_n:,}개):")
    for n in nodes:
        print(f"    :{n['label']:20s} {n['cnt']:>10,}개")
    print(f"\n  엣지 ({total_e:,}개):")
    for e in edges:
        print(f"    -[:{e['type']:20s}]-> {e['cnt']:>10,}개")

    driver.close()


if __name__ == "__main__":
    main()
