#!/usr/bin/env python3
"""
HIRA 비급여 진료비 정보 수집 → Neo4j 적재

엔드포인트: http://apis.data.go.kr/B551182/nonePaymentDiagInfoService/getNonePaymentDiagInfoList
itemNm=유방 (유방암 관련 비급여)
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / "config" / ".env"

ENDPOINT = "http://apis.data.go.kr/B551182/nonePaymentDiagInfoService/getNonePaymentDiagInfoList"


def load_api_key() -> str:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"API 키 파일 없음: {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("HIRA_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise ValueError("HIRA_API_KEY가 .env에 없습니다.")


def fetch_nopay(api_key: str, page: int = 1, num_rows: int = 50) -> tuple[list, int]:
    params = urllib.parse.urlencode({
        "serviceKey": api_key,
        "itemNm": "유방",
        "type": "json",
        "numOfRows": str(num_rows),
        "pageNo": str(page),
    })
    url = f"{ENDPOINT}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [ERROR] page {page}: {e}")
        return [], 0

    body = data.get("response", {}).get("body", {})
    total = int(body.get("totalCount", 0))
    items = body.get("items", {})
    if isinstance(items, dict):
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        return item_list, total
    return [], total


def load_to_neo4j(items: list[dict]):
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
    load_dotenv(PROJECT_ROOT / ".env")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    db = os.getenv("NEO4J_DATABASE")

    with driver.session(database=db) as session:
        for item in items:
            hosp_name = item.get("yadmNm", "")
            if not hosp_name:
                continue
            session.run(
                """
                MERGE (h:Hospital {name: $name})
                SET h.nopay_item = coalesce(h.nopay_item, []) + [$item_name],
                    h.hira_nopay_source = 'HIRA_nonePayment'
                """,
                name=hosp_name,
                item_name=item.get("itemNm", ""),
            )
    driver.close()


def main():
    print("=" * 60)
    print("HIRA 비급여 진료비 수집 (유방 관련)")
    print(f"엔드포인트: {ENDPOINT}")
    print("=" * 60)

    api_key = load_api_key()
    print(f"API 키: {api_key[:15]}...")

    all_items = []
    page = 1

    while True:
        items, total = fetch_nopay(api_key, page)
        if not items:
            if total == 0 and page == 1:
                print("  결과 없음 (500 에러 또는 데이터 없음)")
            break
        all_items.extend(items)
        print(f"  page {page}: {len(items)}건 (누적 {len(all_items)}/{total})")
        if len(all_items) >= total:
            break
        page += 1

    if all_items:
        out_path = "hira_nopay_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")

        print("\n[Neo4j 적재]")
        try:
            load_to_neo4j(all_items)
            print(f"  Neo4j 적재 완료: {len(all_items)}건")
        except Exception as e:
            print(f"  Neo4j 에러: {e}")

    print("\n" + "=" * 60)
    print(f"완료: {len(all_items)}건 비급여")
    print("=" * 60)


if __name__ == "__main__":
    main()
