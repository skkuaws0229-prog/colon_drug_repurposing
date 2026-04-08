#!/usr/bin/env python3
"""
Drug Discovery Pipeline - Streamlit Chat App
UI + Data source integration (Bedrock TBD)
"""
import streamlit as st
import json
import time
from pathlib import Path

from data_sources import (
    query_s3_drug_candidates,
    query_s3_model_results,
    query_s3_admet_results,
    query_pubmed,
    query_faers,
    query_clinicaltrials,
    query_chembl,
    query_pubchem,
    DATA_SOURCE_STATUS,
)

st.set_page_config(
    page_title="Drug Discovery Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    .main .block-container { padding-top: 1rem; max-width: 1200px; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #e2e8f0; }

    .source-badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 600; margin-left: 4px;
    }
    .badge-ok { background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }
    .badge-pending { background: #f59e0b20; color: #f59e0b; border: 1px solid #f59e0b40; }
    .badge-na { background: #64748b20; color: #64748b; border: 1px solid #64748b40; }

    .result-card {
        background: #1e293b; border: 1px solid #334155; border-radius: 8px;
        padding: 16px; margin: 8px 0;
    }
    .drug-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .drug-table th { text-align: left; padding: 8px; background: #0f172a; color: #94a3b8;
                     border-bottom: 2px solid #334155; }
    .drug-table td { padding: 6px 8px; border-bottom: 1px solid #1e293b80; color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "follow_up" not in st.session_state:
    st.session_state.follow_up = None


def classify_query(query: str) -> str:
    """Classify user query into a category for routing."""
    q = query.lower()
    if any(k in q for k in ["약물 후보", "추천", "drug candidate", "top 15", "top15", "top 30"]):
        return "drug_candidates"
    if any(k in q for k in ["모델 결과", "model result", "성능", "spearman", "rmse", "앙상블", "ensemble"]):
        return "model_results"
    if any(k in q for k in ["부작용", "adverse", "side effect", "faers", "sider"]):
        return "adverse_events"
    if any(k in q for k in ["논문", "연구", "pubmed", "paper", "research", "최신"]):
        return "pubmed"
    if any(k in q for k in ["약가", "보험", "급여", "hira", "가격"]):
        return "hira"
    if any(k in q for k in ["임상", "clinical trial", "시험"]):
        return "clinical_trials"
    if any(k in q for k in ["admet", "독성", "안전", "toxicity", "safety"]):
        return "admet"
    if any(k in q for k in ["신약", "후보물질", "chembl", "화합물"]):
        return "chembl"
    if any(k in q for k in ["구조", "분자", "pubchem", "smiles", "structure"]):
        return "pubchem"
    if any(k in q for k in ["파이프라인", "진행", "현황", "status", "pipeline"]):
        return "pipeline_status"
    return "general"


def get_follow_up_questions(category: str) -> list:
    """Return follow-up question suggestions based on category."""
    follow_ups = {
        "drug_candidates": [
            "이 약물들의 부작용 알려줘",
            "관련 최신 논문 검색해줘",
            "임상시험 현황 알려줘",
        ],
        "model_results": [
            "앙상블 결과 보여줘",
            "Top 15 약물 추천해줘",
            "과적합 분석 결과 알려줘",
        ],
        "adverse_events": [
            "안전한 대안 약물 추천해줘",
            "관련 논문 검색해줘",
            "ADMET 프로파일 보여줘",
        ],
        "pubmed": [
            "약물 후보 목록 보여줘",
            "임상시험 현황 알려줘",
            "ADMET 결과 알려줘",
        ],
        "clinical_trials": [
            "관련 약물 후보 보여줘",
            "최신 논문 검색해줘",
            "부작용 데이터 알려줘",
        ],
        "admet": [
            "약물 후보 목록 보여줘",
            "부작용 데이터 보여줘",
            "관련 논문 검색해줘",
        ],
        "pipeline_status": [
            "모델 결과 보여줘",
            "약물 후보 추천해줘",
            "ADMET 결과 알려줘",
        ],
    }
    return follow_ups.get(category, ["약물 후보 추천해줘", "모델 결과 보여줘", "최신 논문 검색해줘"])


def process_query(query: str) -> tuple:
    """Process user query and return (response_text, category)."""
    category = classify_query(query)

    if category == "drug_candidates":
        result = query_s3_drug_candidates()
        if result["status"] == "ok":
            drugs = result["data"]
            text = f"**Top {len(drugs)} 약물 후보 목록** (앙상블 예측 기반)\n\n"
            text += "| # | Drug ID | Pred IC50 | True IC50 | Sensitivity | Category |\n"
            text += "|---|---------|-----------|-----------|-------------|----------|\n"
            for d in drugs:
                text += (f"| {d.get('final_rank', d.get('rank', '-'))} | {d['drug_id']} | "
                        f"{d['mean_pred_ic50']:.3f} | {d['mean_true_ic50']:.3f} | "
                        f"{d['sensitivity_rate']:.1%} | {d['category']} |\n")
            text += f"\n> 기준: 앙상블 Spearman-weighted average (6개 모델)"
        else:
            text = f"아직 약물 후보 데이터가 준비되지 않았습니다.\n\n상태: {result['message']}"

    elif category == "model_results":
        result = query_s3_model_results()
        if result["status"] == "ok":
            text = "**모델 학습 결과 요약**\n\n"
            for section, models in result["data"].items():
                text += f"\n### {section}\n"
                text += "| Model | Val Spearman | RMSE | Status |\n"
                text += "|-------|-------------|------|--------|\n"
                for m in models:
                    text += f"| {m['model']} | {m['spearman']:.4f} | {m['rmse']:.4f} | {m['status']} |\n"

            if "ensemble" in result:
                e = result["ensemble"]
                text += f"\n### Ensemble\n"
                text += f"- Spearman: {e['spearman']:.4f}\n"
                text += f"- RMSE: {e['rmse']:.4f}\n"
                text += f"- Method: Spearman-weighted average (6 models)\n"
        else:
            text = f"모델 결과 조회 중 오류: {result['message']}"

    elif category == "admet":
        result = query_s3_admet_results()
        text = result.get("message", "ADMET 결과를 조회합니다...")
        if result["status"] == "ok":
            text = result["data"]

    elif category == "pubmed":
        drug_terms = []
        for word in query.split():
            if len(word) > 2 and word not in ["최신", "논문", "검색", "연구", "알려줘", "보여줘", "해줘"]:
                drug_terms.append(word)
        search_term = " ".join(drug_terms) if drug_terms else "breast cancer drug sensitivity GDSC"
        result = query_pubmed(search_term)
        if result["status"] == "ok":
            articles = result["data"]
            text = f"**PubMed 검색 결과** ('{search_term}')\n\n"
            for i, a in enumerate(articles, 1):
                text += f"**{i}. {a['title']}**\n"
                text += f"- Authors: {a['authors']}\n"
                text += f"- Journal: {a['journal']} ({a['pub_date']})\n"
                text += f"- PMID: [{a['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/)\n\n"
        else:
            text = f"PubMed 검색 오류: {result['message']}"

    elif category == "adverse_events":
        result = query_faers(query)
        if result["status"] == "ok":
            text = result["data"]
        else:
            text = f"부작용 데이터 조회 오류: {result['message']}"

    elif category == "clinical_trials":
        result = query_clinicaltrials(query)
        if result["status"] == "ok":
            text = result["data"]
        else:
            text = f"임상시험 데이터 조회 오류: {result['message']}"

    elif category == "chembl":
        result = query_chembl(query)
        if result["status"] == "ok":
            text = result["data"]
        else:
            text = f"ChEMBL 조회 오류: {result['message']}"

    elif category == "pubchem":
        result = query_pubchem(query)
        if result["status"] == "ok":
            text = result["data"]
        else:
            text = f"PubChem 조회 오류: {result['message']}"

    elif category == "hira":
        text = ("HIRA API 연동에는 **공공데이터포털 API 키**가 필요합니다.\n\n"
                "API 키를 제공해 주시면 연동을 진행하겠습니다.\n"
                "(https://www.data.go.kr)")

    elif category == "pipeline_status":
        text = ("**파이프라인 진행 현황**\n\n"
                "| Step | 단계 | 상태 |\n"
                "|------|------|------|\n"
                "| 1 | Environment Setup | Completed |\n"
                "| 2 | Data Preparation | Completed |\n"
                "| 3 | Feature Engineering | Completed |\n"
                "| 4 | Model Training (15) | Completed |\n"
                "| 5 | Ensemble Track2 | In Progress |\n"
                "| 6 | METABRIC Validation | Pending |\n"
                "| 7 | ADMET Gate | Pending |\n\n"
                "> 4/7 Steps 완료 (57.1%)\n"
                "> [대시보드 보기](dashboard.html)")

    else:
        text = ("질문을 이해했습니다. 현재 Bedrock 연동 전이라 자연어 대화는 제한적입니다.\n\n"
                "아래 빠른 질문 버튼을 사용해 보세요:\n"
                "- 약물 후보 추천\n"
                "- 모델 결과 조회\n"
                "- 최신 논문 검색\n"
                "- 부작용 데이터\n"
                "- 파이프라인 현황")

    return text, category


# ── Sidebar ──
with st.sidebar:
    st.markdown("### 💊 Drug Discovery Assistant")
    st.markdown("---")

    st.markdown("#### 빠른 질문")
    quick_questions = [
        ("약물 후보 추천해줘", "drug"),
        ("모델 결과 보여줘", "model"),
        ("ADMET 결과 알려줘", "admet"),
        ("최신 논문 검색해줘", "paper"),
        ("부작용 알려줘", "adverse"),
        ("임상시험 알려줘", "trial"),
        ("파이프라인 현황", "status"),
    ]

    for q_text, q_key in quick_questions:
        if st.button(q_text, key=f"quick_{q_key}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": q_text})
            response, cat = process_query(q_text)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.follow_up = get_follow_up_questions(cat)
            st.rerun()

    st.markdown("---")
    st.markdown("#### 데이터 소스 현황")
    for source, info in DATA_SOURCE_STATUS.items():
        badge_class = {
            "connected": "badge-ok",
            "available": "badge-ok",
            "pending": "badge-pending",
            "api_key_required": "badge-na",
        }.get(info["status"], "badge-na")
        status_text = {
            "connected": "연동 완료",
            "available": "사용 가능",
            "pending": "예정",
            "api_key_required": "API 키 필요",
        }.get(info["status"], info["status"])
        st.markdown(
            f"**{source}** <span class='source-badge {badge_class}'>{status_text}</span>",
            unsafe_allow_html=True,
        )
        st.caption(info["description"])

    st.markdown("---")
    st.caption("Bedrock 연동: 별도 지시 예정")
    st.caption(f"Version: 1.0.0 | 2026-04-08")


# ── Main Chat Area ──
st.markdown("## Drug Discovery Pipeline Chat")

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Follow-up buttons
if st.session_state.follow_up and st.session_state.messages:
    cols = st.columns(len(st.session_state.follow_up))
    for i, fq in enumerate(st.session_state.follow_up):
        with cols[i]:
            if st.button(fq, key=f"followup_{i}_{len(st.session_state.messages)}"):
                st.session_state.messages.append({"role": "user", "content": fq})
                response, cat = process_query(fq)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.follow_up = get_follow_up_questions(cat)
                st.rerun()

# Chat input
if prompt := st.chat_input("질문을 입력하세요 (예: 약물 후보 추천해줘)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("데이터 조회 중..."):
            response, category = process_query(prompt)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.follow_up = get_follow_up_questions(category)

    st.rerun()
