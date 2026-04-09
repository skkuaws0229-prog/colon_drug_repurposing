#!/usr/bin/env python3
"""
HIRA 병원 정보 수집 → Neo4j Hospital 노드 업데이트

엔드포인트: http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList
dgsbjtCd=140 (유방외과)
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

ENDPOINT = "http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"


def load_api_key() -> str:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"API 키 파일 없음: {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("HIRA_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise ValueError("HIRA_API_KEY가 .env에 없습니다.")


def fetch_hospitals(api_key: str, page: int = 1, num_rows: int = 50) -> tuple[list, int]:
    params = urllib.parse.urlencode({
        "serviceKey": api_key,
        "dgsbjtCd": "140",
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


def load_to_neo4j(hospitals: list[dict]):
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
    load_dotenv(PROJECT_ROOT / ".env")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    db = os.getenv("NEO4J_DATABASE")

    with driver.session(database=db) as session:
        for h in hospitals:
            session.run(
                """
                MERGE (h:Hospital {name: $name})
                SET h.address = $addr,
                    h.phone = $phone,
                    h.url = $url,
                    h.region = $region,
                    h.category = $category,
                    h.hira_code = $code,
                    h.hira_source = 'HIRA_hospInfo'
                WITH h
                MATCH (d:Disease {code: 'BRCA'})
                MERGE (h)-[:TREATS_DISEASE]->(d)
                """,
                name=h.get("yadmNm", ""),
                addr=h.get("addr", ""),
                phone=h.get("telno", ""),
                url=h.get("hospUrl", ""),
                region=h.get("sidoCdNm", ""),
                category=h.get("clCdNm", ""),
                code=h.get("ykiho", ""),
            )
    driver.close()


def main():
    print("=" * 60)
    print("HIRA 병원 정보 수집 (유방외과 dgsbjtCd=140)")
    print(f"엔드포인트: {ENDPOINT}")
    print("=" * 60)

    api_key = load_api_key()
    print(f"API 키: {api_key[:15]}...")

    all_hospitals = []
    page = 1

    while True:
        items, total = fetch_hospitals(api_key, page)
        if not items:
            if total == 0 and page == 1:
                print("  결과 없음 (500 에러 또는 데이터 없음)")
            break
        all_hospitals.extend(items)
        print(f"  page {page}: {len(items)}건 (누적 {len(all_hospitals)}/{total})")
        if len(all_hospitals) >= total:
            break
        page += 1

    if all_hospitals:
        # JSON 저장
        out_path = "hira_hospital_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_hospitals, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")

        # Neo4j 적재
        print("\n[Neo4j 적재]")
        try:
            load_to_neo4j(all_hospitals)
            print(f"  Neo4j 적재 완료: {len(all_hospitals)}건")
        except Exception as e:
            print(f"  Neo4j 에러: {e}")

    print("\n" + "=" * 60)
    print(f"완료: {len(all_hospitals)}건 병원")
    print("=" * 60)


if __name__ == "__main__":
    main()
