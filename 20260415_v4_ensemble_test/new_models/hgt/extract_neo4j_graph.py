#!/usr/bin/env python3
"""
Neo4j KG에서 HGT용 그래프 데이터 추출

우선순위:
1. Neo4j Cypher로 직접 추출
2. 로컬 export 파일 활용
3. FastAPI 엔드포인트 사용
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from neo4j import GraphDatabase

# ============================================================================
# Neo4j 연결 설정
# ============================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

output_dir = Path(__file__).parent
base_dir = Path("/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260408_pre_project_biso_myprotocol")

print("=" * 80)
print("Neo4j KG 데이터 추출")
print("=" * 80)

# ============================================================================
# Step 1: Neo4j 연결 확인
# ============================================================================
print("\n[Step 1] Neo4j 연결 확인")
print("-" * 80)

if not NEO4J_PASSWORD:
    print("❌ NEO4J_PASSWORD 환경변수 없음")
    print("\n대체 방법:")
    print("1. .env 파일 확인")
    print("2. 로컬 export 파일 사용")

    # .env 파일 확인
    env_file = base_dir / "20260409_scaleup_biso/.env"
    if env_file.exists():
        print(f"\n.env 파일 발견: {env_file}")
        print("비밀번호 로드 중...")
        from dotenv import load_dotenv
        load_dotenv(env_file)
        NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
        if NEO4J_PASSWORD:
            print("✓ 비밀번호 로드 성공")
        else:
            print("❌ .env에 NEO4J_PASSWORD 없음")
            exit(1)
    else:
        print(f"\n.env 파일 없음: {env_file}")
        exit(1)

print(f"\nNeo4j URI: {NEO4J_URI}")
print(f"Neo4j User: {NEO4J_USER}")
print(f"Neo4j Database: {NEO4J_DATABASE}")

# ============================================================================
# Step 2: Neo4j 연결 및 통계 확인
# ============================================================================
print("\n[Step 2] Neo4j 연결 및 통계")
print("-" * 80)

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("✓ Neo4j 연결 성공!")

    with driver.session(database=NEO4J_DATABASE) as session:
        # 노드 통계
        print("\n노드 통계:")
        result = session.run("MATCH (n) RETURN labels(n) as label, count(n) as count")
        node_stats = {}
        total_nodes = 0
        for record in result:
            label = record["label"][0] if record["label"] else "Unknown"
            count = record["count"]
            node_stats[label] = count
            total_nodes += count
            print(f"  {label:20s}: {count:>10,}")

        print(f"  {'Total':20s}: {total_nodes:>10,}")

        # 엣지 통계
        print("\n엣지 통계:")
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        edge_stats = {}
        total_edges = 0
        for record in result:
            edge_type = record["type"]
            count = record["count"]
            edge_stats[edge_type] = count
            total_edges += count
            print(f"  {edge_type:20s}: {count:>10,}")

        print(f"  {'Total':20s}: {total_edges:>10,}")

except Exception as e:
    print(f"❌ Neo4j 연결 실패: {e}")
    print("\n로컬 export 파일 확인 중...")
    # TODO: 로컬 파일 사용 로직
    exit(1)

# ============================================================================
# Step 3: Drug-Target 관계 추출
# ============================================================================
print("\n[Step 3] Drug-Target 관계 추출")
print("-" * 80)

with driver.session(database=NEO4J_DATABASE) as session:
    query = """
    MATCH (d:Drug)-[r:TARGETS]->(t:Target)
    RETURN d.name as drug_name,
           d.chembl_id as drug_chembl_id,
           t.name as target_name,
           t.gene_name as target_gene,
           t.uniprot_id as target_uniprot
    LIMIT 10000
    """

    result = session.run(query)
    drug_target_edges = []

    for record in result:
        drug_target_edges.append({
            "drug_name": record["drug_name"],
            "drug_chembl_id": record["drug_chembl_id"],
            "target_name": record["target_name"],
            "target_gene": record["target_gene"],
            "target_uniprot": record["target_uniprot"]
        })

    print(f"Drug-Target edges: {len(drug_target_edges):,}")

    # 저장
    drug_target_file = output_dir / "neo4j_drug_target_edges.json"
    with open(drug_target_file, "w") as f:
        json.dump(drug_target_edges, f, indent=2)
    print(f"✓ 저장: {drug_target_file}")

# ============================================================================
# Step 4: Target-Pathway 관계 추출
# ============================================================================
print("\n[Step 4] Target-Pathway 관계 추출")
print("-" * 80)

with driver.session(database=NEO4J_DATABASE) as session:
    query = """
    MATCH (t:Target)-[r:IN_PATHWAY]->(p:Pathway)
    RETURN t.gene_name as target_gene,
           p.pathway_id as pathway_id,
           p.name as pathway_name
    LIMIT 10000
    """

    result = session.run(query)
    target_pathway_edges = []

    for record in result:
        target_pathway_edges.append({
            "target_gene": record["target_gene"],
            "pathway_id": record["pathway_id"],
            "pathway_name": record["pathway_name"]
        })

    print(f"Target-Pathway edges: {len(target_pathway_edges):,}")

    # 저장
    target_pathway_file = output_dir / "neo4j_target_pathway_edges.json"
    with open(target_pathway_file, "w") as f:
        json.dump(target_pathway_edges, f, indent=2)
    print(f"✓ 저장: {target_pathway_file}")

# ============================================================================
# Step 5: Drug-Disease 관계 추출
# ============================================================================
print("\n[Step 5] Drug-Disease 관계 추출")
print("-" * 80)

with driver.session(database=NEO4J_DATABASE) as session:
    query = """
    MATCH (d:Drug)-[r:TREATS]->(dis:Disease)
    RETURN d.name as drug_name,
           d.chembl_id as drug_chembl_id,
           dis.name as disease_name,
           dis.code as disease_code
    LIMIT 10000
    """

    result = session.run(query)
    drug_disease_edges = []

    for record in result:
        drug_disease_edges.append({
            "drug_name": record["drug_name"],
            "drug_chembl_id": record["drug_chembl_id"],
            "disease_name": record["disease_name"],
            "disease_code": record["disease_code"]
        })

    print(f"Drug-Disease edges: {len(drug_disease_edges):,}")

    # 저장
    drug_disease_file = output_dir / "neo4j_drug_disease_edges.json"
    with open(drug_disease_file, "w") as f:
        json.dump(drug_disease_edges, f, indent=2)
    print(f"✓ 저장: {drug_disease_file}")

# ============================================================================
# Step 6: 전체 노드 목록 추출
# ============================================================================
print("\n[Step 6] 전체 노드 목록 추출")
print("-" * 80)

all_nodes = {}

with driver.session(database=NEO4J_DATABASE) as session:
    # Drug nodes
    result = session.run("MATCH (d:Drug) RETURN d.name as name, d.chembl_id as chembl_id LIMIT 10000")
    all_nodes["Drug"] = [{"name": r["name"], "chembl_id": r["chembl_id"]} for r in result]
    print(f"Drug nodes: {len(all_nodes['Drug']):,}")

    # Target nodes
    result = session.run("MATCH (t:Target) RETURN t.name as name, t.gene_name as gene_name, t.uniprot_id as uniprot_id LIMIT 10000")
    all_nodes["Target"] = [{"name": r["name"], "gene_name": r["gene_name"], "uniprot_id": r["uniprot_id"]} for r in result]
    print(f"Target nodes: {len(all_nodes['Target']):,}")

    # Pathway nodes
    result = session.run("MATCH (p:Pathway) RETURN p.pathway_id as pathway_id, p.name as name LIMIT 10000")
    all_nodes["Pathway"] = [{"pathway_id": r["pathway_id"], "name": r["name"]} for r in result]
    print(f"Pathway nodes: {len(all_nodes['Pathway']):,}")

    # Disease nodes
    result = session.run("MATCH (d:Disease) RETURN d.name as name, d.code as code LIMIT 10000")
    all_nodes["Disease"] = [{"name": r["name"], "code": r["code"]} for r in result]
    print(f"Disease nodes: {len(all_nodes['Disease']):,}")

# 저장
nodes_file = output_dir / "neo4j_all_nodes.json"
with open(nodes_file, "w") as f:
    json.dump(all_nodes, f, indent=2)
print(f"\n✓ 저장: {nodes_file}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("추출 완료!")
print("=" * 80)

summary = {
    "neo4j_stats": {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_types": node_stats,
        "edge_types": edge_stats
    },
    "extracted_data": {
        "drug_target_edges": len(drug_target_edges),
        "target_pathway_edges": len(target_pathway_edges),
        "drug_disease_edges": len(drug_disease_edges),
        "nodes": {k: len(v) for k, v in all_nodes.items()}
    },
    "output_files": [
        str(drug_target_file),
        str(target_pathway_file),
        str(drug_disease_file),
        str(nodes_file)
    ]
}

summary_file = output_dir / "neo4j_extraction_summary.json"
with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✓ Summary: {summary_file}")

driver.close()
print("\nNeo4j 연결 종료")
