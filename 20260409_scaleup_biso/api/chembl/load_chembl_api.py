"""
ChEMBL API → Drug 노드 속성 보강

엔드포인트: https://www.ebi.ac.uk/chembl/api/data/molecule
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

CHEMBL_URL = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"


def get_pipeline_drugs(driver) -> list[str]:
    with driver.session(database=DATABASE) as session:
        return [
            r["name"]
            for r in session.run(
                'MATCH (d:Drug) WHERE d.disease_code = "BRCA" '
                "RETURN d.name AS name ORDER BY d.rank"
            ).data()
        ]


def fetch_chembl(drug_name: str) -> dict | None:
    try:
        resp = requests.get(
            CHEMBL_URL,
            params={"pref_name": drug_name.upper(), "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        molecules = data.get("molecules", [])
        if not molecules:
            return None

        mol = molecules[0]
        props = mol.get("molecule_properties") or {}
        structs = mol.get("molecule_structures") or {}

        return {
            "chembl_id": mol.get("molecule_chembl_id"),
            "molecule_type": mol.get("molecule_type"),
            "max_phase": mol.get("max_phase"),
            "oral": mol.get("oral"),
            "smiles": structs.get("canonical_smiles"),
            "mol_weight": props.get("mw_freebase"),
            "alogp": props.get("alogp"),
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

        info = fetch_chembl(drug)
        if not info:
            print("데이터 없음")
        else:
            with driver.session(database=DATABASE) as session:
                session.run(
                    """
                    MATCH (d:Drug {name: $name})
                    SET d.chembl_id      = $chembl_id,
                        d.molecule_type  = $molecule_type,
                        d.max_phase      = $max_phase,
                        d.oral           = $oral,
                        d.smiles         = $smiles,
                        d.mol_weight     = $mol_weight,
                        d.alogp          = $alogp
                    """,
                    name=drug,
                    **info,
                )
            updated += 1
            print(f"✓ {info['chembl_id']} (phase={info['max_phase']})")

        if i < len(drugs):
            time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"  ChEMBL API 완료: {updated}/{len(drugs)} Drug 업데이트")
    print(f"{'='*50}")

    driver.close()


if __name__ == "__main__":
    main()
