#!/usr/bin/env python3
"""
Drug Repurposing KG — FastAPI 서버

포트: 8000
CORS 전체 허용
Neo4j Aura + PubMed + 국립암센터 API 통합
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── 프로젝트 루트를 sys.path에 추가 (llm 모듈 import용) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from llm.ncis_content import get_ncis_info  # noqa: E402
from llm.llm_module import search_news, get_lifestyle_guide, search_celebrity_cases  # noqa: E402

# ── .env 로드 ──
load_dotenv(PROJECT_ROOT / ".env")

# ── Neo4j 설정 (Aura 클라우드) ──
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

_driver = None


def get_driver():
    """Neo4j 드라이버 싱글턴."""
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _driver.verify_connectivity()
    return _driver


def neo4j_query(cypher: str, **params) -> list[dict]:
    """Cypher 쿼리 실행 → list[dict] 반환."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


def make_response(data: Any, source: str = "neo4j") -> dict:
    """공통 응답 형식."""
    return {
        "status": "success",
        "data": data,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── FastAPI 앱 ──
app = FastAPI(
    title="Drug Repurposing KG API",
    description="유방암 약물 재창출 지식그래프 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 파이프라인 15개 약물 ──
PIPELINE_DRUGS = [
    "Romidepsin", "Sepantronium bromide", "Dactinomycin", "Staurosporine",
    "Vinblastine", "Bortezomib", "SN-38", "Docetaxel", "Vinorelbine",
    "Dinaciclib", "Paclitaxel", "Rapamycin", "Camptothecin", "Luminespib",
    "Epirubicin",
]


# ── 1. 약물 정보 ──
@app.get("/api/drug/{drug_name}")
def get_drug(drug_name: str):
    """Drug 노드 조회."""
    rows = neo4j_query(
        "MATCH (d:Drug {name: $name}) RETURN d",
        name=drug_name,
    )
    if not rows:
        raise HTTPException(404, f"Drug '{drug_name}' not found")
    node = dict(rows[0]["d"])
    return make_response(node)


# ── 2. 약물 타겟 ──
@app.get("/api/drug/{drug_name}/targets")
def get_drug_targets(drug_name: str):
    """Drug → Target 관계 조회."""
    rows = neo4j_query(
        """
        MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)
        RETURN t.gene_symbol AS gene_symbol,
               t.protein_name AS protein_name,
               t.uniprot_id AS uniprot_id,
               t.function AS function
        """,
        name=drug_name,
    )
    return make_response(rows)


# ── 3. 약물 부작용 ──
@app.get("/api/drug/{drug_name}/side_effects")
def get_drug_side_effects(drug_name: str):
    """Drug → SideEffect 관계 조회."""
    rows = neo4j_query(
        """
        MATCH (d:Drug {name: $name})-[:HAS_SIDE_EFFECT]->(s:SideEffect)
        RETURN s.name AS name,
               s.meddra_term AS meddra_term
        """,
        name=drug_name,
    )
    return make_response(rows)


# ── 4. 약물 임상시험 ──
@app.get("/api/drug/{drug_name}/trials")
def get_drug_trials(drug_name: str):
    """Drug → Trial 관계 조회."""
    rows = neo4j_query(
        """
        MATCH (d:Drug {name: $name})-[:IN_TRIAL]->(t:Trial)
        RETURN t.nct_id AS nct_id,
               t.title AS title,
               t.phase AS phase,
               t.status AS status,
               t.sponsor AS sponsor,
               t.start_date AS start_date,
               t.completion_date AS completion_date
        """,
        name=drug_name,
    )
    return make_response(rows)


# ── 5. 약물 Pathway ──
@app.get("/api/drug/{drug_name}/pathways")
def get_drug_pathways(drug_name: str):
    """Drug → Target → Pathway 경로 조회."""
    rows = neo4j_query(
        """
        MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)-[:IN_PATHWAY]->(p:Pathway)
        RETURN DISTINCT p.pathway_id AS pathway_id,
               p.name AS name,
               p.collection AS collection
        """,
        name=drug_name,
    )
    return make_response(rows)


# ── 6. 전체 약물 목록 ──
@app.get("/api/drugs")
def get_drugs(
    status: str | None = None,
    pipeline: bool = Query(default=False, description="파이프라인 15개 약물만"),
    limit: int = Query(default=100, le=20000),
):
    """Drug 목록 조회 (brca_status 필터, pipeline 필터 가능)."""
    where_clauses = []
    params: dict = {}

    if pipeline:
        where_clauses.append("d.name IN $drug_list")
        params["drug_list"] = PIPELINE_DRUGS

    if status:
        where_clauses.append("d.brca_status = $status")
        params["status"] = status

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = neo4j_query(
        f"""
        MATCH (d:Drug)
        {where}
        RETURN d.name AS name,
               d.brca_status AS brca_status,
               d.overall_score AS overall_score,
               d.safety_score AS safety_score,
               d.ic50 AS ic50,
               d.max_phase AS max_phase,
               d.target AS target,
               d.rank AS rank
        ORDER BY d.overall_score DESC
        LIMIT $limit
        """,
        limit=limit,
        **params,
    )
    return make_response(rows)


# ── 7. 병원 목록 ──
@app.get("/api/hospitals")
def get_hospitals(
    region: str | None = None,
    specialty: str | None = Query(default=None, description="상급종합병원 등"),
):
    """Hospital 노드 목록."""
    where_clauses = []
    params: dict = {}

    if region:
        where_clauses.append("h.region = $region")
        params["region"] = region

    if specialty:
        where_clauses.append("h.specialty CONTAINS $specialty")
        params["specialty"] = specialty

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = neo4j_query(
        f"""
        MATCH (h:Hospital)
        {where}
        RETURN h.name AS name,
               h.address AS address,
               h.phone AS phone,
               h.url AS url,
               h.region AS region,
               h.specialty AS specialty,
               h.category AS category,
               h.district AS district
        ORDER BY h.name
        """,
        **params,
    )
    return make_response(rows)


# ── 8. 질환 정보 ──
@app.get("/api/disease/{disease_code}")
def get_disease(disease_code: str):
    """Disease 노드 조회."""
    rows = neo4j_query(
        "MATCH (d:Disease {code: $code}) RETURN d",
        code=disease_code,
    )
    if not rows:
        raise HTTPException(404, f"Disease '{disease_code}' not found")
    node = dict(rows[0]["d"])
    return make_response(node)


# ── 9. PubMed 실시간 검색 ──
@app.get("/api/pubmed")
def search_pubmed(query: str, max_results: int = Query(default=5, le=20)):
    """PubMed eutils API 실시간 호출."""
    search_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
            "sort": "relevance",
        })
    )
    try:
        with urllib.request.urlopen(search_url, timeout=10) as resp:
            search_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(502, f"PubMed search failed: {e}")

    id_list = search_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return make_response([], source="pubmed")

    fetch_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
        })
    )
    try:
        with urllib.request.urlopen(fetch_url, timeout=10) as resp:
            fetch_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(502, f"PubMed fetch failed: {e}")

    articles = []
    result = fetch_data.get("result", {})
    for pmid in id_list:
        art = result.get(pmid, {})
        authors = [a.get("name", "") for a in art.get("authors", [])]
        articles.append({
            "pmid": pmid,
            "title": art.get("title", ""),
            "authors": authors[:5],
            "journal": art.get("fulljournalname", ""),
            "pub_date": art.get("pubdate", ""),
        })

    return make_response(articles, source="pubmed")


# ── 10. 국립암센터 유방암 정보 ──
@app.get("/api/ncis/{category}")
def get_ncis(category: str, term: str | None = None):
    """국립암센터 API 호출 (brca/prevention/guide/term)."""
    valid = {"brca", "prevention", "guide", "term"}
    if category not in valid:
        raise HTTPException(400, f"Invalid category. Use: {', '.join(valid)}")

    kwargs = {}
    if category == "term":
        kwargs["term"] = term or "유방암"

    data = get_ncis_info(category, **kwargs)
    return make_response(data, source="ncis")


# ── 11. KG 현황 ──
@app.get("/api/stats")
def get_stats():
    """Neo4j 전체 노드/엣지 통계."""
    node_rows = neo4j_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
    )
    rel_rows = neo4j_query(
        "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
    )

    total_nodes = sum(r["count"] for r in node_rows)
    total_rels = sum(r["count"] for r in rel_rows)

    return make_response({
        "nodes": {r["label"]: r["count"] for r in node_rows},
        "edges": {r["type"]: r["count"] for r in rel_rows},
        "total_nodes": total_nodes,
        "total_edges": total_rels,
    })


# ── 12. 채팅 질의 ──
class ChatRequest(BaseModel):
    query: str
    user_type: str = "patient"  # patient / researcher


def _extract_drug_from_query(query: str) -> str | None:
    """쿼리에서 약물명 추출."""
    q_lower = query.lower()
    for drug in PIPELINE_DRUGS:
        if drug.lower() in q_lower:
            return drug
    return None


def _classify_intent(query: str) -> str:
    """쿼리 의도 분류."""
    q_lower = query.lower()
    if any(kw in q_lower for kw in ["부작용", "side effect", "adverse", "독성", "toxicity"]):
        return "side_effects"
    if any(kw in q_lower for kw in ["임상", "trial", "clinical", "kct", "nct"]):
        return "trials"
    if any(kw in q_lower for kw in ["타겟", "target", "표적", "작용기전"]):
        return "targets"
    if any(kw in q_lower for kw in ["pathway", "경로", "신호전달"]):
        return "pathways"
    if any(kw in q_lower for kw in ["병원", "hospital", "의료기관"]):
        return "hospitals"
    if any(kw in q_lower for kw in ["통계", "환자수", "발생률", "유병률"]):
        return "disease_stats"
    if any(kw in q_lower for kw in ["예방", "검진", "screening"]):
        return "prevention"
    if any(kw in q_lower for kw in ["용어", "사전", "뜻", "정의"]):
        return "term"
    if any(kw in q_lower for kw in ["뉴스", "news", "기사", "최신", "소식"]):
        return "news"
    if any(kw in q_lower for kw in ["음식", "식단", "운동", "수면", "스트레스", "생활", "추천",
                                     "먹을", "식사", "영양", "잠", "불면", "심리", "마음"]):
        return "lifestyle"
    if any(kw in q_lower for kw in ["유명인", "celebrity", "사례", "연예인", "스타"]):
        return "celebrity"
    return "drug_info"


@app.post("/api/chat")
def chat(req: ChatRequest):
    """채팅 질의 처리 — 쿼리 분석 → Neo4j/API 조회 → 응답."""
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "query is empty")

    drug_name = _extract_drug_from_query(query)
    intent = _classify_intent(query)
    source = "neo4j"
    data = {}
    answer = ""

    if intent == "side_effects" and drug_name:
        rows = neo4j_query(
            """
            MATCH (d:Drug {name: $name})-[:HAS_SIDE_EFFECT]->(s:SideEffect)
            RETURN s.name AS name, s.meddra_term AS meddra_term
            """,
            name=drug_name,
        )
        data = {"drug": drug_name, "side_effects": rows}
        if rows:
            effects = ", ".join(r["name"] for r in rows[:5])
            answer = f"{drug_name}의 주요 부작용: {effects}"
        else:
            answer = f"{drug_name}의 부작용 데이터가 아직 없습니다."

    elif intent == "trials" and drug_name:
        rows = neo4j_query(
            """
            MATCH (d:Drug {name: $name})-[:IN_TRIAL]->(t:Trial)
            RETURN t.nct_id AS nct_id, t.title AS title,
                   t.phase AS phase, t.status AS status,
                   t.sponsor AS sponsor
            """,
            name=drug_name,
        )
        data = {"drug": drug_name, "trials": rows}
        answer = f"{drug_name} 관련 임상시험: {len(rows)}건" if rows else f"{drug_name} 관련 임상시험 데이터가 없습니다."

    elif intent == "targets" and drug_name:
        rows = neo4j_query(
            """
            MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)
            RETURN t.gene_symbol AS gene, t.protein_name AS protein
            """,
            name=drug_name,
        )
        data = {"drug": drug_name, "targets": rows}
        if rows:
            genes = ", ".join(r["gene"] for r in rows if r["gene"])
            answer = f"{drug_name}의 타겟: {genes}"
        else:
            answer = f"{drug_name}의 타겟 데이터가 아직 없습니다."

    elif intent == "pathways" and drug_name:
        rows = neo4j_query(
            """
            MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)-[:IN_PATHWAY]->(p:Pathway)
            RETURN DISTINCT p.pathway_id AS id, p.name AS name
            """,
            name=drug_name,
        )
        data = {"drug": drug_name, "pathways": rows}
        answer = f"{drug_name} 관련 Pathway: {len(rows)}개" if rows else f"{drug_name}의 Pathway 데이터가 없습니다."

    elif intent == "hospitals":
        rows = neo4j_query(
            """
            MATCH (h:Hospital)
            RETURN h.name AS name, h.region AS region,
                   h.specialty AS specialty, h.phone AS phone
            ORDER BY h.name LIMIT 20
            """
        )
        data = {"hospitals": rows}
        names = ", ".join(r["name"] for r in rows[:5])
        answer = f"유방암 치료 병원: {names} 등 총 {len(rows)}개"

    elif intent == "disease_stats":
        rows = neo4j_query(
            "MATCH (d:Disease {code: 'BRCA'}) RETURN d"
        )
        if rows:
            node = dict(rows[0]["d"])
            data = node
            total = node.get("brca_total_patients", node.get("total_patients", "N/A"))
            if isinstance(total, (int, float)):
                answer = f"유방암 누적 환자 수: {total:,}명 (NCIS)"
            else:
                answer = f"유방암 정보: {node.get('name', 'BRCA')}"
        else:
            answer = "질환 통계 데이터가 없습니다."

    elif intent == "prevention":
        source = "ncis"
        data = get_ncis_info("prevention")
        count = len(data)
        answer = f"유방암 예방/검진 정보: {count}개 항목 (국립암센터)"

    elif intent == "term":
        source = "ncis"
        term = query.replace("용어", "").replace("사전", "").replace("뜻", "").replace("정의", "").strip()
        if not term:
            term = "유방암"
        data = get_ncis_info("term", term=term)
        answer = f"'{term}' 검색 결과: {len(data)}개 용어"

    elif intent == "news":
        source = "news"
        news_query = query.replace("뉴스", "").replace("최신", "").replace("소식", "").strip()
        if not news_query or len(news_query) < 2:
            news_query = "유방암"
        news = search_news(news_query, max_results=5)
        data = {"news": news, "query": news_query}
        if news and "error" not in news[0]:
            titles = " / ".join(n["title"][:40] for n in news[:3])
            answer = f"'{news_query}' 최신 뉴스 {len(news)}건: {titles}"
        else:
            answer = "뉴스 검색에 실패했습니다."

    elif intent == "lifestyle":
        source = "guide"
        guide = get_lifestyle_guide(query)
        data = guide
        topic = guide.get("topic", "")
        recs = guide.get("recommendations", [])
        if recs and topic:
            top3 = " / ".join(recs[:3])
            answer = f"유방암 환자 {topic} 가이드: {top3}"
        else:
            answer = "생활 가이드를 찾을 수 없습니다. 지원 주제: 음식, 운동, 수면, 스트레스"

    elif intent == "celebrity":
        source = "guide"
        cases = search_celebrity_cases()
        data = {"cases": cases}
        names = ", ".join(c["name"] for c in cases[:3])
        answer = f"유방암 치료 유명인 사례 {len(cases)}건: {names} 등"

    elif drug_name:
        rows = neo4j_query(
            "MATCH (d:Drug {name: $name}) RETURN d",
            name=drug_name,
        )
        if rows:
            node = dict(rows[0]["d"])
            data = node
            answer = (
                f"{drug_name} 정보: IC50={node.get('ic50', 'N/A')}, "
                f"상태={node.get('brca_status', 'N/A')}, "
                f"안전성={node.get('safety_score', 'N/A')}, "
                f"종합점수={node.get('overall_score', 'N/A')}"
            )
        else:
            answer = f"{drug_name} 약물 정보가 KG에 없습니다."
            data = {"drug": drug_name}

    else:
        answer = "죄송합니다. 약물명이나 질환, 병원 등 구체적인 키워드를 포함해주세요."
        data = {"hint": "예: 'Docetaxel 부작용', '유방암 통계', '병원 목록'"}

    return make_response(
        {"answer": answer, "detail": data, "intent": intent, "drug": drug_name},
        source=source,
    )


# ── 서버 실행 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("chat.api_server:app", host="0.0.0.0", port=8000, reload=True)
