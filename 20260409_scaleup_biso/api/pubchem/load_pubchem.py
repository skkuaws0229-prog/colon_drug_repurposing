"""
PubChem API → Drug 노드 속성 보강

엔드포인트: https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name
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

PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"


def get_pipeline_drugs(driver) -> list[str]:
    with driver.session(database=DATABASE) as session:
        return [
            r["name"]
            for r in session.run(
                'MATCH (d:Drug) WHERE d.disease_code = "BRCA" '
                "RETURN d.name AS name ORDER BY d.rank"
            ).data()
        ]


def fetch_pubchem(drug_name: str) -> dict | None:
    url = (
        f"{PUBCHEM_URL}/{drug_name}/property/"
        "MolecularFormula,MolecularWeight,IUPACName,InChIKey/JSON"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if not props:
            return None

        p = props[0]
        return {
            "pubchem_cid": p.get("CID"),
            "molecular_formula": p.get("MolecularFormula"),
            "molecular_weight": p.get("MolecularWeight"),
            "iupac_name": p.get("IUPACName"),
            "inchikey": p.get("InChIKey"),
        }
    except Exception as e:
        print(f"에러: {e}")
        return None


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    drugs = get_pipeline_drugs(driver)
    print(f"대상 약물: {len(drugs)}개\n")

    updated = 0
    for i, drug in enumerate(drugs, 1):
        print(f"  [{i}/{len(drugs)}] {drug} ... ", end="", flush=True)

        info = fetch_pubchem(drug)
        if not info:
            print("데이터 없음")
        else:
            with driver.session(database=DATABASE) as session:
                session.run(
                    """
                    MATCH (d:Drug {name: $name})
                    SET d.pubchem_cid        = $pubchem_cid,
                        d.molecular_formula  = $molecular_formula,
                        d.iupac_name         = $iupac_name,
                        d.inchikey           = $inchikey
                    """,
                    name=drug,
                    **info,
                )
            updated += 1
            print(f"✓ CID={info['pubchem_cid']} ({info['molecular_formula']})")

        if i < len(drugs):
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"  PubChem API 완료: {updated}/{len(drugs)} Drug 업데이트")
    print(f"{'='*50}")

    driver.close()


if __name__ == "__main__":
    main()
