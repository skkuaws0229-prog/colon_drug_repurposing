from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.services.agent_tools.image_modal_tool import summarize_image_modal
from backend.services.agent_tools.neo4j_tool import query_neo4j_readonly
from backend.services.agent_tools.postgres_tool import query_postgres_readonly
from backend.services.agent_tools.report_reader_tool import read_reports_index


DISEASE_ALIAS_TO_CANONICAL: dict[str, str] = {
    "BRAC": "BRCA",
    "BRCA": "BRCA",
    "COAD": "COAD",
    "COLON": "COAD",
    "CRC": "COAD",
    "LUAD": "LUAD",
    "LUNG": "LUAD",
    "LIHC": "LIHC",
    "LIVER": "LIHC",
    "STAD": "STAD",
    "PAAD": "PAAD",
    "PDAC": "PAAD",
    "HNSC": "HNSC",
}

IMAGE_KEYWORDS = {"image", "이미지", "modal", "멀티모달", "embedding", "임베딩", "kaplan", "pca", "cluster", "클러스터"}
GRAPH_KEYWORDS = {"graph", "kg", "neo4j", "관계", "노드", "edge"}
DRUG_KEYWORDS = {"candidate", "drug", "admet", "약물", "후보", "score", "ranking"}


def normalize_disease(disease_input: str) -> str:
    key = (disease_input or "").strip().upper()
    if key in DISEASE_ALIAS_TO_CANONICAL:
        return DISEASE_ALIAS_TO_CANONICAL[key]
    raise ValueError(f"Unsupported disease alias: {disease_input}")


def contains_any(question_lower: str, keywords: set[str]) -> bool:
    return any(token in question_lower for token in keywords)


def run_read_only_assistant(disease_input: str, question: str, runtime_project_root: Path) -> dict[str, Any]:
    disease = normalize_disease(disease_input)
    q = (question or "").strip()
    ql = q.lower()

    tool_calls: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    limitations: list[str] = []

    is_image = contains_any(ql, IMAGE_KEYWORDS)
    is_graph = contains_any(ql, GRAPH_KEYWORDS)
    is_drug = contains_any(ql, DRUG_KEYWORDS)
    is_ambiguous = not any([is_image, is_graph, is_drug])

    if is_image or is_ambiguous:
        image_result = summarize_image_modal(disease=disease, project_root=runtime_project_root)
        tool_calls.append({"tool": "image_modal_tool", "status": image_result.get("status", "ok")})
        evidence.extend(image_result.get("evidence", []))
        limitations.extend(image_result.get("limitations", []))

    if is_graph:
        neo4j_result = query_neo4j_readonly(disease=disease, question=q)
        tool_calls.append({"tool": "neo4j_tool", "status": neo4j_result.get("status", "ok")})
        evidence.extend(neo4j_result.get("evidence", []))
        limitations.extend(neo4j_result.get("limitations", []))

    if is_drug:
        pg_result = query_postgres_readonly(disease=disease, question=q)
        tool_calls.append({"tool": "postgres_tool", "status": pg_result.get("status", "ok")})
        evidence.extend(pg_result.get("evidence", []))
        limitations.extend(pg_result.get("limitations", []))

    if is_ambiguous:
        rr_result = read_reports_index(project_root=runtime_project_root, disease=disease)
        tool_calls.append({"tool": "report_reader_tool", "status": rr_result.get("status", "ok")})
        evidence.extend(rr_result.get("evidence", []))
        limitations.extend(rr_result.get("limitations", []))

    current_facts = "현재 말할 수 있는 것: 질문과 관련된 리포트/DB(read-only) 근거만 요약합니다."
    blocked_facts = "아직 말하면 안 되는 것/한계: 외부 LLM 해석, 이미지 내용 해석, write 작업은 수행하지 않습니다."

    if disease == "BRCA" and (is_image or "image_modal_tool" in [t["tool"] for t in tool_calls]):
        brca_block = (
            "현재 BRCA image modal은 image 3개, metadata review 17개, needs review 4개, zero-byte placeholder 1개로 분류되었다. "
            "embedding 원본으로 보이는 .npy는 존재하지만, shape/dtype/mapping 검증 전이므로 바로 vector DB/PostgreSQL 적재하면 안 된다. "
            "우선 image registry + metadata evidence inspection + Neo4j HAS_IMAGE_MODAL 연결이 권장된다."
        )
        answer = f"{current_facts} {brca_block} {blocked_facts}"
    else:
        answer = f"{current_facts} {blocked_facts}"

    unique_limitations = []
    seen = set()
    for item in limitations + [
        "No OpenAI/LLM API calls were made.",
        "Rule-based fallback assistant only.",
    ]:
        if item not in seen:
            seen.add(item)
            unique_limitations.append(item)

    return {
        "disease": disease,
        "question": q,
        "answer": answer,
        "evidence": evidence,
        "limitations": unique_limitations,
        "tool_calls": tool_calls,
        "safety": {
            "mode": "read_only",
            "llm_provider": "none",
            "openai_used": False,
            "db_write_performed": False,
            "postgres_write_performed": False,
            "neo4j_write_performed": False,
            "s3_download_performed": False,
            "image_interpretation_performed": False,
        },
    }

