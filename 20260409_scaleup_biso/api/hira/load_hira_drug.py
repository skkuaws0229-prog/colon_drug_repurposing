#!/usr/bin/env python3
"""
HIRA 약물 보험 정보 수집 → Neo4j Drug 노드 속성 업데이트

엔드포인트: http://apis.data.go.kr/B551182/msInsu/getNIitemInfoList01
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

ENDPOINT = "http://apis.data.go.kr/B551182/msInsu/getNIitemInfoList01"

DRUG_NAMES = [
    "Docetaxel", "Paclitaxel", "Vinorelbine", "Vinblastine",
    "Epirubicin", "Bortezomib", "SN-38", "Dinaciclib",
    "Rapamycin", "Dactinomycin", "Staurosporine",
    "Camptothecin", "Luminespib",
]

# 한글 검색명 매핑
DRUG_NAME_KR = {
    "Docetaxel": "도세탁셀",
    "Paclitaxel": "파클리탁셀",
    "Vinorelbine": "비노렐빈",
    "Vinblastine": "빈블라스틴",
    "Epirubicin": "에피루비신",
    "Bortezomib": "보르테조밉",
    "Rapamycin": "라파마이신",
    "Dactinomycin": "닥티노마이신",
    "Camptothecin": "캄프토테신",
}


def load_api_key() -> str:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"API 키 파일 없음: {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("HIRA_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise ValueError("HIRA_API_KEY가 .env에 없습니다.")


def fetch_drug_info(api_key: str, item_name: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "serviceKey": api_key,
        "type": "json",
        "numOfRows": "10",
        "itemName": item_name,
    })
    url = f"{ENDPOINT}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        return [{"error": str(e)}]

    body = data.get("response", {}).get("body", {})
    items = body.get("items", {})
    if isinstance(items, dict):
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        return item_list
    return []


def load_to_neo4j(drug_name: str, items: list[dict]):
    from dotenv import load_dotenv
    from neo4j import GraphDatabase
    load_dotenv(PROJECT_ROOT / ".env")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    db = os.getenv("NEO4J_DATABASE")

    with driver.session(database=db) as session:
        if items:
            item = items[0]
            session.run(
                """
                MATCH (d:Drug {name: $name})
                SET d.hira_item_name = $hira_name,
                    d.insurance_type = $ins_type,
                    d.unit_price = $price,
                    d.hira_updated = date()
                """,
                name=drug_name,
                hira_name=item.get("itemName", ""),
                ins_type=item.get("insuType", item.get("insTypNm", "")),
                price=item.get("unitPrice", item.get("mdcGrdCd", "")),
            )
    driver.close()


def main():
    print("=" * 60)
    print("HIRA 약물 보험정보 수집")
    print(f"엔드포인트: {ENDPOINT}")
    print("=" * 60)

    api_key = load_api_key()
    print(f"API 키: {api_key[:15]}...")

    success = 0
    fail = 0
    no_data = 0
    results = {}

    for i, drug in enumerate(DRUG_NAMES, 1):
        search_terms = [drug]
        if drug in DRUG_NAME_KR:
            search_terms.append(DRUG_NAME_KR[drug])

        print(f"\n[{i}/{len(DRUG_NAMES)}] {drug}")
        found_items = []

        for term in search_terms:
            items = fetch_drug_info(api_key, term)
            if items and "error" in items[0]:
                print(f"  [{term}] ERROR: {items[0]['error']}")
                fail += 1
                break
            elif items:
                print(f"  [{term}] {len(items)}건 발견")
                found_items.extend(items)
            else:
                print(f"  [{term}] 결과 없음")

        if found_items:
            results[drug] = found_items
            success += 1
            item = found_items[0]
            print(f"  → {item.get('itemName', 'N/A')[:50]}")
            try:
                load_to_neo4j(drug, found_items)
                print(f"  → Neo4j 업데이트 완료")
            except Exception as e:
                print(f"  → Neo4j 에러: {e}")
        elif not any("error" in (items[0] if items else {}) for _ in [0]):
            no_data += 1

    # JSON 저장
    out_path = "hira_drug_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    print("\n" + "=" * 60)
    print(f"완료: 성공 {success} / 실패 {fail} / 데이터없음 {no_data} / 총 {len(DRUG_NAMES)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
