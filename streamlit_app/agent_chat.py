#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request

import streamlit as st


API_BASE = os.getenv("ASSISTANT_API_BASE", "http://localhost:8000")
CHAT_URL = f"{API_BASE}/api/assistant/chat"


def call_assistant(message: str, limit: int) -> dict:
    payload = json.dumps({"message": message, "limit": limit}).encode("utf-8")
    req = urllib.request.Request(
        CHAT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return {"error": f"HTTP {exc.code}", "detail": body}
    except Exception as exc:  # noqa: BLE001
        return {"error": "request_failed", "detail": str(exc)}


def render_items(items):
    if not items:
        st.info("No rows returned.")
        return
    if isinstance(items[0], str):
        for x in items:
            st.write(f"- {x}")
        return
    st.dataframe(items, use_container_width=True)


st.set_page_config(page_title="BRCA Agentic Assistant", page_icon="KG", layout="wide")

st.title("BRCA Agentic Assistant")
st.caption("PostgreSQL + Neo4j 라우팅 채팅 UI")

with st.sidebar:
    st.markdown("### API")
    st.code(CHAT_URL)
    limit = st.slider("Row limit", min_value=5, max_value=100, value=20, step=5)
    st.markdown("### Quick prompts")
    quick_prompts = [
        "테이블 목록 보여줘",
        "최종 후보 점수순으로 보여줘",
        "ADMET PASS만 보여줘",
        "brca_import.brca_final15_after_admet 테이블 보여줘",
        "PRIMA-1MET 왜 후보야?",
        "타깃 pathway 근거 강한 후보 보여줘",
    ]
    for q in quick_prompts:
        if st.button(q, use_container_width=True):
            st.session_state["pending_prompt"] = q

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])
        if msg.get("items"):
            render_items(msg["items"])

pending = st.session_state.pop("pending_prompt", None)
prompt = pending or st.chat_input("질문을 입력하세요. 예: 최종 후보 점수순으로 보여줘")
if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching PostgreSQL/Neo4j..."):
            result = call_assistant(prompt, limit)
        if "error" in result:
            st.error(f"{result['error']}: {result.get('detail', '')}")
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": f"오류: {result['error']}",
                    "meta": result.get("detail", ""),
                }
            )
        else:
            answer = result.get("answer", "OK")
            route = result.get("route", "unknown")
            intent = result.get("intent", "unknown")
            items = result.get("items", [])
            st.markdown(answer)
            st.caption(f"route={route} / intent={intent}")
            render_items(items)
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": answer,
                    "meta": f"route={route} / intent={intent}",
                    "items": items,
                }
            )
