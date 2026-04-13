#!/usr/bin/env python3
"""
국립암센터 공공데이터 API → 유방암 통계 수집 + Neo4j 적재

승인된 API:
  1. 유방암_라이브러리_집계정보
     엔드포인트: http://apis.data.go.kr/B551172/brst/patientNumber
     파라미터: serviceKey, pageNo, numOfRows
     데이터: 연도별/병원별/연령별 환자 수

  2. 유방암 협력병기 조사 (엔드포인트 미확인 → 추후 추가)
  3. 유방암 검진 수검률 (엔드포인트 미확인 → 추후 추가)

사용법:
  python load_ncis_brca.py              # 수집만 (JSON 저장)
  python load_ncis_brca.py --neo4j      # 수집 + Neo4j 적재
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

# API 설정
BRST_ENDPOINT = "http://apis.data.go.kr/B551172/brst/patientNumber"
ENV_PATH = Path(__file__).resolve().parent.parent.parent / "config" / ".env"


def load_api_key() -> str:
    """config/.env에서 API 키 로드."""
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"API 키 파일 없음: {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("HIRA_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise ValueError("HIRA_API_KEY가 .env에 없습니다.")


def fetch_all_brst(api_key: str) -> list[dict]:
    """유방암 라이브러리 전체 데이터 수집 (페이지네이션)."""
    all_items = []
    page = 1
    while True:
        params = urllib.parse.urlencode({
            "serviceKey": api_key,
            "pageNo": str(page),
            "numOfRows": "100",
        })
        url = f"{BRST_ENDPOINT}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"  [ERROR] page {page}: {e}")
            break

        items = data.get("items", [])
        if not items:
            break
        all_items.extend(items)
        total = data.get("totalCount", 0)
        print(f"  page {page}: {len(items)}건 (누적 {len(all_items)}/{total})")

        if len(all_items) >= total:
            break
        page += 1

    return all_items


def aggregate_stats(items: list[dict]) -> dict:
    """연도별/병원별 통계 집계."""
    year_patients = defaultdict(int)
    year_center = defaultdict(lambda: defaultdict(int))
    centers = set()

    for item in items:
        yr = item.get("critYr", "")
        center = item.get("centerNm", "")
        cnt = int(item.get("ptCntNmvl", 0))
        year_patients[yr] += cnt
        year_center[yr][center] += cnt
        centers.add(center)

    return {
        "annual_patients": dict(sorted(year_patients.items())),
        "centers": sorted(centers),
        "center_count": len(centers),
        "year_count": len(year_patients),
        "total_records": len(items),
        "total_patients": sum(year_patients.values()),
        "year_center_detail": {
            yr: dict(sorted(cs.items()))
            for yr, cs in sorted(year_center.items())
        },
    }


def load_to_neo4j(stats: dict):
    """Neo4j Disease(BRCA) 노드에 통계 속성 업데이트."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[ERROR] neo4j 패키지가 설치되지 않았습니다.")
        return

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("  Neo4j 연결 성공")

    with driver.session() as session:
        # Disease 노드 MERGE + 속성 업데이트
        session.run(
            """
            MERGE (d:Disease {disease_code: 'BRCA'})
            ON CREATE SET d.name = '유방암 (Breast Cancer)',
                          d.name_en = 'Breast Cancer',
                          d.name_kr = '유방암'
            SET d.brca_annual_patients = $annual_patients,
                d.brca_total_patients = $total_patients,
                d.brca_center_count = $center_count,
                d.ncis_updated = date()
            """,
            annual_patients=json.dumps(stats["annual_patients"], ensure_ascii=False),
            total_patients=stats["total_patients"],
            center_count=stats["center_count"],
        )

        # 병원별 노드 생성 + 엣지
        for center in stats["centers"]:
            session.run(
                """
                MERGE (h:Hospital {name: $name})
                ON CREATE SET h.source = 'NCIS'
                WITH h
                MATCH (d:Disease {disease_code: 'BRCA'})
                MERGE (h)-[:TREATS]->(d)
                """,
                name=center,
            )

    driver.close()
    print(f"  Neo4j 적재 완료: Disease(BRCA) 속성 + {stats['center_count']}개 Hospital 노드")


def main():
    parser = argparse.ArgumentParser(description="국립암센터 유방암 통계 수집")
    parser.add_argument("--neo4j", action="store_true", help="Neo4j에 적재")
    args = parser.parse_args()

    print("=" * 60)
    print("국립암센터 공공데이터 → 유방암 통계 수집")
    print("=" * 60)

    # API 키 로드
    api_key = load_api_key()
    print(f"API 키: {api_key[:15]}...")

    # ── 1. 유방암 라이브러리 집계정보 ──
    print(f"\n[1/3] 유방암_라이브러리_집계정보")
    print(f"  엔드포인트: {BRST_ENDPOINT}")
    items = fetch_all_brst(api_key)
    print(f"  → {len(items)}건 수집")

    stats = aggregate_stats(items)
    print(f"\n  === 연도별 유방암 환자 수 ===")
    for yr, cnt in stats["annual_patients"].items():
        print(f"  {yr}: {cnt:,}명")
    print(f"  총합: {stats['total_patients']:,}명")
    print(f"  참여 병원: {stats['center_count']}개")

    # ── 2. 유방암 협력병기 조사 (미확인) ──
    print(f"\n[2/3] 유방암_협력병기_조사")
    print("  [SKIP] 엔드포인트 URL 미확인 (500 에러)")
    print("  → data.go.kr 마이페이지에서 오퍼레이션명 확인 필요")

    # ── 3. 유방암 검진 수검률 (미확인) ──
    print(f"\n[3/3] 유방암_검진_수검률")
    print("  [SKIP] 엔드포인트 URL 미확인 (500 에러)")
    print("  → data.go.kr 마이페이지에서 오퍼레이션명 확인 필요")

    # ── JSON 저장 ──
    output = {
        "brst_patient_stats": stats,
        "raw_items_count": len(items),
        "skipped_apis": [
            "BreastCancerCoperationService (엔드포인트 미확인)",
            "getExaminationRateBreastCancer (엔드포인트 미확인)",
        ],
    }
    out_path = "ncis_brca_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    # ── Neo4j 적재 ──
    if args.neo4j:
        print("\n[Neo4j 적재]")
        load_to_neo4j(stats)

    # ── 통계 ──
    print("\n" + "=" * 60)
    print("완료 통계:")
    print(f"  유방암 라이브러리: {len(items)}건 (2002-2021)")
    print(f"  연도별 환자 수: {stats['year_count']}년")
    print(f"  총 환자 수: {stats['total_patients']:,}명")
    print(f"  참여 병원: {stats['center_count']}개")
    print(f"  협력병기: SKIP (엔드포인트 미확인)")
    print(f"  검진수검률: SKIP (엔드포인트 미확인)")
    print("=" * 60)


if __name__ == "__main__":
    main()
