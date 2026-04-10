#!/usr/bin/env python3
"""
HIRA 비급여 진료비 정보 수집 → Neo4j 적재

엔드포인트: http://apis.data.go.kr/B551182/nonPaymentDamtInfoService/getNonPaymentItemHospDtlList
ykiho(암호화된 요양기호) 필수 → Neo4j Hospital 노드에서 조회
"""
import json
import os
import sys
import time
import requests
import xmltodict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / "config" / ".env"

ENDPOINT = "http://apis.data.go.kr/B551182/nonPaymentDamtInfoService/getNonPaymentItemHospDtlList"


def load_api_key() -> str:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"API 키 파일 없음: {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("HIRA_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise ValueError("HIRA_API_KEY가 .env에 없습니다.")


def get_neo4j_driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
    load_dotenv(PROJECT_ROOT / ".env")
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    return driver, os.getenv("NEO4J_DATABASE")


def fetch_hospital_ykihos(driver, db):
    """Neo4j에서 상급종합 Hospital의 hira_code(ykiho) 전체 조회."""
    with driver.session(database=db) as session:
        result = session.run(
            'MATCH (h:Hospital) WHERE h.hira_source = "HIRA_hospInfo" '
            'AND h.hira_code IS NOT NULL '
            'RETURN h.name AS name, h.hira_code AS ykiho'
        )
        return [(r["name"], r["ykiho"]) for r in result]


def fetch_nopay_items(api_key: str, ykiho: str, num_rows: int = 50) -> list[dict]:
    """한 병원의 비급여 항목 조회 (최대 num_rows건)."""
    params = {
        "serviceKey": api_key,
        "ykiho": ykiho,
        "numOfRows": str(num_rows),
        "pageNo": "1",
    }
    try:
        resp = requests.get(ENDPOINT, params=params, timeout=15)
        resp.raise_for_status()
        data = xmltodict.parse(resp.text)
    except Exception as e:
        return [{"error": str(e)}]

    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    if items is None or items == "":
        return []
    if isinstance(items, dict):
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        return item_list
    return []


def load_nopay_to_neo4j(driver, db, hosp_name: str, items: list[dict]):
    """비급여 항목을 Hospital 노드에 속성으로 추가."""
    with driver.session(database=db) as session:
        nopay_list = []
        for item in items:
            nopay_list.append({
                "code": item.get("npayCd", ""),
                "name": item.get("npayKorNm", ""),
                "hosp_name_item": item.get("yadmNpayCdNm", ""),
                "amount": item.get("curAmt", ""),
            })

        session.run(
            """
            MATCH (h:Hospital {name: $name})
            SET h.nopay_count = $count,
                h.nopay_items = $items_json,
                h.hira_nopay_source = 'HIRA_nonPayment'
            """,
            name=hosp_name,
            count=len(nopay_list),
            items_json=json.dumps(nopay_list, ensure_ascii=False),
        )


def main():
    print("=" * 60)
    print("HIRA 비급여 진료비 수집 (상급종합 병원별)")
    print(f"엔드포인트: {ENDPOINT}")
    print("=" * 60)

    api_key = load_api_key()
    print(f"API 키: {api_key[:15]}...")

    driver, db = get_neo4j_driver()
    hospitals = fetch_hospital_ykihos(driver, db)
    print(f"상급종합 병원: {len(hospitals)}건\n")

    success = 0
    fail = 0
    no_data = 0
    total_items = 0
    all_results = {}

    for i, (name, ykiho) in enumerate(hospitals, 1):
        items = fetch_nopay_items(api_key, ykiho)

        if items and "error" in items[0]:
            print(f"  [{i:2d}/{len(hospitals)}] {name:25s} → ERROR: {items[0]['error']}")
            fail += 1
        elif items:
            total_items += len(items)
            all_results[name] = items
            success += 1
            print(f"  [{i:2d}/{len(hospitals)}] {name:25s} → {len(items)}건")
            try:
                load_nopay_to_neo4j(driver, db, name, items)
            except Exception as e:
                print(f"    Neo4j 에러: {e}")
        else:
            no_data += 1
            print(f"  [{i:2d}/{len(hospitals)}] {name:25s} → 데이터 없음")

        time.sleep(0.3)  # API 과부하 방지

    driver.close()

    # JSON 저장
    out_path = "hira_nopay_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    print("\n" + "=" * 60)
    print(f"완료: 성공 {success} / 실패 {fail} / 데이터없음 {no_data} / 총 {len(hospitals)}병원")
    print(f"총 비급여 항목: {total_items}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
