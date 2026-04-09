"""
HIRA 비급여 진료비 정보 조회 → Neo4j Hospital 노드 보강

엔드포인트: http://apis.data.go.kr/B551182/nonePaymentDiagInfoService/getNonePaymentItemListInfoService
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

BASE_URL = "http://apis.data.go.kr/B551182/nonePaymentDiagInfoService/getNonePaymentItemListInfoService"


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
                "hospital_name": item.get("yadmNm", ""),
                "item_name": item.get("npayKorNm", "") or item.get("itemNm", ""),
                "cur_amount": item.get("curAmt", ""),
                "min_amount": item.get("minAmt", ""),
                "max_amount": item.get("maxAmt", ""),
            })
        return items
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        root = ET.fromstring(resp_text)
        for item in root.iter("item"):
            items.append({
                "hospital_id": (item.findtext("ykiho") or "").strip(),
                "hospital_name": (item.findtext("yadmNm") or "").strip(),
                "item_name": (item.findtext("npayKorNm") or item.findtext("itemNm") or "").strip(),
                "cur_amount": (item.findtext("curAmt") or "").strip(),
                "min_amount": (item.findtext("minAmt") or "").strip(),
                "max_amount": (item.findtext("maxAmt") or "").strip(),
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

    print("  유방 관련 비급여 항목 조회 ... ", end="", flush=True)
    params = {
        "serviceKey": API_KEY,
        "npayKorNm": "유방",
        "type": "json",
        "numOfRows": 50,
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
        if 'resp' in dir():
            print(f"  응답 미리보기: {resp.text[:300]}")

        # 다른 키워드로도 시도
        for keyword in ["항암", "Breast"]:
            time.sleep(1)
            print(f"\n  '{keyword}' 키워드로 재시도 ... ", end="", flush=True)
            params["npayKorNm"] = keyword
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                items = parse_response(resp.text)
                print(f"{len(items)}개")
                if items:
                    break
            except Exception as e:
                print(f"에러: {e}")

    if not items:
        print("\n  비급여 데이터 없음 → 건너뜀")
        driver.close()
        return

    # Neo4j 적재
    updated = 0
    with driver.session(database=DATABASE) as session:
        for item in items:
            if not item["hospital_id"]:
                continue
            session.run(
                """
                MERGE (hosp:Hospital {hospital_id: $hospital_id})
                SET hosp.name              = $hospital_name,
                    hosp.nopay_item        = $item_name,
                    hosp.nopay_cur_amount  = $cur_amount,
                    hosp.nopay_min_amount  = $min_amount,
                    hosp.nopay_max_amount  = $max_amount
                """,
                hospital_id=item["hospital_id"],
                hospital_name=item["hospital_name"],
                item_name=item["item_name"],
                cur_amount=item["cur_amount"],
                min_amount=item["min_amount"],
                max_amount=item["max_amount"],
            )
            updated += 1

    print(f"\n{'='*50}")
    print(f"  HIRA 비급여 완료: {updated}개 병원 업데이트")
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
