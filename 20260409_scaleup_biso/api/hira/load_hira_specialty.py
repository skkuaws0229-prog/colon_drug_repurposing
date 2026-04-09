"""
HIRA 전문병원 정보 조회 → Neo4j Hospital 노드 보강

엔드포인트: http://apis.data.go.kr/B551182/spclHospInfoService01/getSpclHospInfoList01
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

BASE_URL = "http://apis.data.go.kr/B551182/spclHospInfoService01/getSpclHospInfoList01"


def parse_response(resp_text: str) -> list[dict]:
    items = []
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
                "doctor_count": item.get("drTotCnt", ""),
            })
        return items
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        root = ET.fromstring(resp_text)
        for item in root.iter("item"):
            items.append({
                "hospital_id": (item.findtext("ykiho") or "").strip(),
                "name": (item.findtext("yadmNm") or "").strip(),
                "address": (item.findtext("addr") or "").strip(),
                "phone": (item.findtext("telno") or "").strip(),
                "doctor_count": (item.findtext("drTotCnt") or "").strip(),
            })
    except ET.ParseError:
        pass

    return items


def main():
    if not API_KEY:
        print("HIRA_API_KEY 없음 → 즉시 중단")
        return

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    print("  전문병원 조회 ... ", end="", flush=True)
    params = {
        "serviceKey": API_KEY,
        "type": "json",
        "numOfRows": 100,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        items = parse_response(resp.text)
        print(f"{len(items)}개")
    except Exception as e:
        print(f"에러: {e}")
        items = []

    if not items:
        print("  데이터 없음 또는 API 응답 에러")
        print(f"  응답 미리보기: {resp.text[:300]}")
        driver.close()
        return

    # Neo4j 적재
    updated = 0
    with driver.session(database=DATABASE) as session:
        for h in items:
            if not h["hospital_id"]:
                continue
            session.run(
                """
                MERGE (hosp:Hospital {hospital_id: $hospital_id})
                SET hosp.name          = $name,
                    hosp.address       = $address,
                    hosp.phone         = $phone,
                    hosp.doctor_count  = $doctor_count,
                    hosp.is_specialty  = true
                """,
                hospital_id=h["hospital_id"],
                name=h["name"],
                address=h["address"],
                phone=h["phone"],
                doctor_count=h["doctor_count"],
            )
            updated += 1

        hosp_cnt = session.run(
            "MATCH (h:Hospital) WHERE h.is_specialty = true RETURN count(h) AS cnt"
        ).single()["cnt"]

    print(f"\n{'='*50}")
    print(f"  HIRA 전문병원 완료")
    print(f"{'='*50}")
    print(f"  전문병원 (is_specialty=true): {hosp_cnt}개")

    driver.close()


if __name__ == "__main__":
    main()
