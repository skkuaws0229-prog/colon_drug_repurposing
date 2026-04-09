#!/usr/bin/env python3
"""
Reactome API → Pathway 데이터 수집 + Neo4j 적재
엔드포인트: https://reactome.org/ContentService/
키 불필요 · 무료

사용법:
  python load_reactome.py              # 수집만 (JSON 저장)
  python load_reactome.py --neo4j      # 수집 + Neo4j 적재
"""
import argparse
import json
import time
import urllib.request
import urllib.parse

REACTOME_BASE = "https://reactome.org/ContentService"

# 유방암 관련 주요 단백질 (UniProt ID) - Pathway 추가 수집용
BRCA_PROTEINS = {
    "P38398": "BRCA1",
    "P51587": "BRCA2",
    "P04637": "TP53",
    "P38936": "CDKN1A (p21)",
    "Q07817": "BCL2L1 (BCL-XL)",
}

# 파이프라인 15개 약물 타겟 관련 경로 키워드
TARGET_PATHWAYS = [
    "R-HSA-3214858",   # Chromatin modifying enzymes (HDAC)
    "R-HSA-109581",    # Apoptosis
    "R-HSA-8953897",   # Cellular responses to stress
    "R-HSA-69278",     # Cell Cycle
    "R-HSA-1640170",   # Cell Cycle, Mitotic
    "R-HSA-73857",     # RNA Polymerase transcription
    "R-HSA-2500257",   # DNA replication (TOP1)
    "R-HSA-5357801",   # Programmed Cell Death
    "R-HSA-199418",    # Negative regulators of cell death (BIRC5)
    "R-HSA-2262749",   # Cellular response to stress
]


def fetch_json(url: str) -> dict | list | None:
    """GET request → JSON parse, 실패 시 None."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def fetch_pathway_detail(pathway_id: str) -> dict | None:
    """Reactome ContentService에서 pathway 상세 정보 조회."""
    url = f"{REACTOME_BASE}/data/query/{urllib.parse.quote(pathway_id)}"
    return fetch_json(url)


def fetch_protein_pathways(uniprot_id: str) -> list[dict]:
    """특정 단백질(UniProt ID) 관련 Reactome 경로 조회."""
    # UniProt → Reactome pathway 매핑 엔드포인트
    url = f"{REACTOME_BASE}/data/mapping/UniProt/{uniprot_id}/pathways"
    data = fetch_json(url)
    if not data or not isinstance(data, list):
        return []
    return data


def parse_pathway(data: dict) -> dict:
    """Reactome 응답에서 필요한 필드 추출."""
    summation_list = data.get("summation", [])
    description = summation_list[0].get("text", "") if summation_list else ""
    return {
        "reactome_id": data.get("stId", ""),
        "display_name": data.get("displayName", ""),
        "species": data.get("speciesName", "Homo sapiens"),
        "description": description[:500],
    }


def load_to_neo4j(pathways: list[dict], brca_pathways: list[dict]):
    """Neo4j에 적재."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[ERROR] neo4j 패키지가 설치되지 않았습니다.")
        return

    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("  Neo4j 연결 성공")

    with driver.session() as session:
        # 기존 Pathway 업데이트
        for pw in pathways:
            session.run(
                """
                MATCH (p:Pathway {pathway_id: $pathway_id})
                SET p.reactome_id = $reactome_id,
                    p.description = $description,
                    p.species = $species
                """,
                pathway_id=pw["reactome_id"],
                reactome_id=pw["reactome_id"],
                description=pw["description"],
                species=pw["species"],
            )

        # BRCA 관련 Pathway 추가
        for pw in brca_pathways:
            session.run(
                """
                MERGE (p:Pathway {pathway_id: $reactome_id})
                ON CREATE SET p.name = $name,
                              p.reactome_id = $reactome_id,
                              p.description = $description,
                              p.species = $species,
                              p.source = $source
                ON MATCH SET  p.reactome_id = $reactome_id,
                              p.description = $description,
                              p.species = $species
                """,
                reactome_id=pw["reactome_id"],
                name=pw["display_name"],
                description=pw["description"],
                species=pw["species"],
                source=pw.get("source", "Reactome"),
            )

    driver.close()
    print(f"  Neo4j 적재 완료: {len(pathways)} 업데이트 + {len(brca_pathways)} BRCA 경로")


def main():
    parser = argparse.ArgumentParser(description="Reactome API → Pathway 수집")
    parser.add_argument("--neo4j", action="store_true", help="Neo4j에 적재")
    args = parser.parse_args()

    print("=" * 60)
    print("Reactome API → Pathway 데이터 수집")
    print("=" * 60)

    # ── 1단계: 약물 타겟 관련 주요 Pathway 상세 조회 ──
    print(f"\n[1/2] 약물 타겟 관련 Pathway {len(TARGET_PATHWAYS)}개 조회...")
    target_results = []
    for pid in TARGET_PATHWAYS:
        data = fetch_pathway_detail(pid)
        if data:
            pw = parse_pathway(data)
            target_results.append(pw)
            print(f"  ✓ {pw['reactome_id']}: {pw['display_name']}")
        else:
            print(f"  ✗ {pid}: 조회 실패")
        time.sleep(1)

    print(f"  → {len(target_results)}/{len(TARGET_PATHWAYS)}개 수집 완료")

    # ── 2단계: BRCA 관련 단백질 경로 수집 ──
    print(f"\n[2/2] BRCA 관련 단백질 경로 조회 ({len(BRCA_PROTEINS)}개)...")
    brca_results = []
    seen_ids = set()
    for uniprot_id, gene_name in BRCA_PROTEINS.items():
        print(f"  {gene_name} ({uniprot_id})...")
        pathways = fetch_protein_pathways(uniprot_id)
        count = 0
        for pw_data in pathways:
            pw = parse_pathway(pw_data)
            pw["source"] = f"Reactome_{gene_name}"
            if pw["reactome_id"] not in seen_ids:
                seen_ids.add(pw["reactome_id"])
                brca_results.append(pw)
                count += 1
        print(f"    → {count}개 (중복 제외)")
        time.sleep(1)

    print(f"  → BRCA 관련 총 {len(brca_results)}개 고유 경로")

    # ── JSON 저장 ──
    output = {
        "target_pathways": target_results,
        "brca_pathways": brca_results,
        "stats": {
            "target_pathway_count": len(target_results),
            "brca_pathway_count": len(brca_results),
            "brca_proteins_queried": list(BRCA_PROTEINS.keys()),
        },
    }
    out_path = "reactome_pathways_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    # ── Neo4j 적재 (옵션) ──
    if args.neo4j:
        print("\n[Neo4j 적재]")
        load_to_neo4j(target_results, brca_results)

    # ── 통계 ──
    print("\n" + "=" * 60)
    print("완료 통계:")
    print(f"  약물 타겟 Pathway: {len(target_results)}개")
    print(f"  BRCA 관련 Pathway: {len(brca_results)}개")
    print(f"  총 수집: {len(target_results) + len(brca_results)}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
