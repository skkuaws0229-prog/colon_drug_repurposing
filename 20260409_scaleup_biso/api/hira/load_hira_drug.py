"""
HIRA 약가·급여 정보 조회 → Neo4j Drug 노드 업데이트

엔드포인트: http://apis.data.go.kr/B551182/msInsu/getNIitemInfoList01
"""

import os
import time
import xml.etree.ElementTree as ET
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
API_KEY = os.getenv("HIRA_API_KEY") or os.getenv("PUBLIC_DATA_API_KEY")

BASE_URL = "http://apis.data.go.kr/B551182/msInsu/getNIitemInfoList01"


def get_pipeline_drugs(driver) -> list[str]:
    with driver.session(database=DATABASE) as session:
        return [
            r["name"]
            for r in session.run(
                'MATCH (d:Drug) WHERE d.disease_code = "BRCA" '
                "RETURN d.name AS name ORDER BY d.rank"
            ).data()
        ]


def parse_response(resp_text: str) -> list[dict]:
    """XML 또는 JSON 응답 파싱"""
    items = []
    # JSON 시도
    try:
        import json
        data = json.loads(resp_text)
        body = data.get("response", {}).get("body", {})
        item_list = body.get("items", {})
        if isinstance(item_list, dict):
            item_list = item_list.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        for item in item_list:
            items.append({
                "item_name": item.get("itemName", ""),
                "insurance_type": item.get("insrType", ""),
                "unit_price": item.get("unitPrice", ""),
                "component_name": item.get("cmpnName", ""),
            })
        return items
    except (json.JSONDecodeError, ValueError):
        pass

    # XML 시도
    try:
        root = ET.fromstring(resp_text)
        for item in root.iter("item"):
            items.append({
                "item_name": (item.findtext("itemName") or "").strip(),
                "insurance_type": (item.findtext("insrType") or "").strip(),
                "unit_price": (item.findtext("unitPrice") or "").strip(),
                "component_name": (item.findtext("cmpnName") or "").strip(),
            })
    except ET.ParseError:
        pass

    return items


def fetch_drug_price(drug_name: str) -> list[dict] | None:
    params = {
        "serviceKey": API_KEY,
        "itemName": drug_name,
        "type": "json",
        "numOfRows": 10,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        return parse_response(resp.text)
    except Exception as e:
        print(f"에러: {e}")
        return None


def main():
    if not API_KEY:
        print("HIRA_API_KEY 없음 → 즉시 중단")
        return

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    drugs = get_pipeline_drugs(driver)
    print(f"대상 약물: {len(drugs)}개\n")

    updated = 0
    for i, drug in enumerate(drugs, 1):
        print(f"  [{i}/{len(drugs)}] {drug} ... ", end="", flush=True)

        items = fetch_drug_price(drug)
        if not items:
            # 한글명으로도 시도하지 않음 (영문 약물명이라 HIRA에 없을 수 있음)
            print("데이터 없음")
            with driver.session(database=DATABASE) as session:
                session.run(
                    """
                    MATCH (d:Drug {name: $name})
                    SET d.insurance_type = '해당없음'
                    """,
                    name=drug,
                )
        else:
            item = items[0]
            with driver.session(database=DATABASE) as session:
                session.run(
                    """
                    MATCH (d:Drug {name: $name})
                    SET d.insurance_type = $insurance_type,
                        d.unit_price     = $unit_price,
                        d.hira_item_name = $hira_item_name
                    """,
                    name=drug,
                    insurance_type=item["insurance_type"] or "해당없음",
                    unit_price=item["unit_price"],
                    hira_item_name=item["item_name"],
                )
            updated += 1
            print(f"✓ {item['item_name'][:30]} ({item['insurance_type']}, {item['unit_price']}원)")

        if i < len(drugs):
            time.sleep(1)

    print(f"\n{'='*50}")
    print(f"  HIRA 약가 완료: {updated}/{len(drugs)} 업데이트")
    print(f"{'='*50}")

    driver.close()


if __name__ == "__main__":
    main()
