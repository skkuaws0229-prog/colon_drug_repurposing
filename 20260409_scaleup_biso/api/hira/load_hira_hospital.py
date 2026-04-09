"""
HIRA 병원정보 조회 → Neo4j Hospital 노드 생성

엔드포인트: http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList
"""

import os
import time
import json
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

BASE_URL = "http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"


def parse_response(resp_text: str) -> list[dict]:
    items = []
    # JSON
    try:
        data = json.loads(resp_text)
        body = data.get("response", {}).get("body", {})
        item_list = body.get("items", {})
        if isinstance(item_list, dict):
            item_list = item_list.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        for item in item_list:
            items.append({
                "hospital_id": item.get("ykiho", ""),
                "name": item.get("yadmNm", ""),
                "address": item.get("addr", ""),
                "phone": item.get("telno", ""),
                "url": item.get("hospUrl", ""),
                "region": item.get("sidoCdNm", ""),
                "district": item.get("sgguCdNm", ""),
                "category": item.get("clCdNm", ""),
            })
        return items
    except (json.JSONDecodeError, ValueError):
        pass

    # XML
    try:
        root = ET.fromstring(resp_text)
        for item in root.iter("item"):
            items.append({
                "hospital_id": (item.findtext("ykiho") or "").strip(),
                "name": (item.findtext("yadmNm") or "").strip(),
                "address": (item.findtext("addr") or "").strip(),
                "phone": (item.findtext("telno") or "").strip(),
                "url": (item.findtext("hospUrl") or "").strip(),
                "region": (item.findtext("sidoCdNm") or "").strip(),
                "district": (item.findtext("sgguCdNm") or "").strip(),
                "category": (item.findtext("clCdNm") or "").strip(),
            })
    except ET.ParseError:
        pass

    return items


def fetch_hospitals(num_rows: int = 50, **extra_params) -> list[dict]:
    params = {
        "serviceKey": API_KEY,
        "numOfRows": num_rows,
    }
    params.update(extra_params)
    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        return parse_response(resp.text)
    except Exception as e:
        print(f"    에러: {e}")
        return []


def main():
    if not API_KEY:
        print("HIRA_API_KEY 없음 → 즉시 중단")
        return

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    all_hospitals = {}

    # 1. 상급종합병원 (clCd=11) - XML 응답
    print("  상급종합병원 (clCd=11) 조회 ... ", end="", flush=True)
    h1 = fetch_hospitals(50, clCd="11")
    print(f"{len(h1)}개")
    for h in h1:
        if h["hospital_id"]:
            h["specialty"] = "상급종합병원"
            all_hospitals[h["hospital_id"]] = h

    time.sleep(1)

    # 2. 종합병원 (clCd=01)
    print("  종합병원 (clCd=01) 조회 ... ", end="", flush=True)
    h2 = fetch_hospitals(50, clCd="01")
    print(f"{len(h2)}개")
    for h in h2:
        if h["hospital_id"]:
            h["specialty"] = "종합병원"
            if h["hospital_id"] not in all_hospitals:
                all_hospitals[h["hospital_id"]] = h

    print(f"\n  고유 병원: {len(all_hospitals)}개")

    # Neo4j 적재
    with driver.session(database=DATABASE) as session:
        for hid, h in all_hospitals.items():
            session.run(
                """
                MERGE (hosp:Hospital {hospital_id: $hospital_id})
                SET hosp.name      = $name,
                    hosp.address   = $address,
                    hosp.phone     = $phone,
                    hosp.url       = $url,
                    hosp.region    = $region,
                    hosp.district  = $district,
                    hosp.category  = $category,
                    hosp.specialty = $specialty
                WITH hosp
                MATCH (dis:Disease {code: 'BRCA'})
                MERGE (hosp)-[:TREATS_DISEASE]->(dis)
                """,
                hospital_id=h["hospital_id"],
                name=h["name"],
                address=h["address"],
                phone=h["phone"],
                url=h["url"],
                region=h["region"],
                district=h["district"],
                category=h["category"],
                specialty=h["specialty"],
            )

        hosp_cnt = session.run("MATCH (h:Hospital) RETURN count(h) AS cnt").single()["cnt"]
        edge_cnt = session.run("MATCH ()-[r:TREATS_DISEASE]->() RETURN count(r) AS cnt").single()["cnt"]

    print(f"\n{'='*50}")
    print(f"  HIRA 병원 완료")
    print(f"{'='*50}")
    print(f"  Hospital 노드: {hosp_cnt}개")
    print(f"  TREATS_DISEASE 엣지: {edge_cnt}개")

    driver.close()


if __name__ == "__main__":
    main()
