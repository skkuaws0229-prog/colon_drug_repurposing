from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from api.core.disease_aliases import normalize_disease


router = APIRouter(prefix="/api/assistant", tags=["assistant"])

INTERNAL_API_BASE = "http://127.0.0.1:8000"
DEFAULT_TOP_N = 3

TOP_KEYWORDS = [
    "상위",
    "top",
    "탑",
    "랭킹",
    "순위",
    "후보",
    "추천",
    "best",
    "rank",
]
DOCKING_KEYWORDS = ["도킹", "docking", "pdb", "alphafold", "구조", "protein", "단백질"]
GRAPH_KEYWORDS = ["그래프", "graph", "kg", "관계", "연결", "노드", "edge", "target", "타겟"]
EXPLANATION_KEYWORDS = ["왜", "근거", "이유", "설명", "좋은", "유망", "해석"]

RANK_FIELDS = ["rank", "final_rank", "drug_rank", "candidate_rank", "ranking", "rank_order"]
SCORE_FIELDS = [
    "drug_level_score",
    "final_score",
    "ensemble_score",
    "score",
    "confidence_score",
    "prediction_score",
]
NAME_FIELDS = ["drug_name", "drug_name_norm", "drug", "name", "candidate", "compound"]
TIER_FIELDS = ["tier", "grade"]

DISEASE_ALIASES = {
    "BRCA": ["brca", "brac", "breast cancer", "breast", "유방암"],
    "COAD": ["coad", "crc", "colorectal cancer", "colorectal", "colon cancer", "colon", "대장암", "결장암"],
    "LUAD": ["luad", "lung adenocarcinoma", "lung cancer", "lung", "폐암", "폐선암"],
    "LIHC": ["lihc", "hepatocellular carcinoma", "liver cancer", "liver", "간암"],
    "STAD": ["stad", "gastric cancer", "stomach", "위암"],
    "PAAD": ["paad", "pdac", "pancreatic cancer", "췌장암"],
    "HNSC": ["hnsc", "head and neck", "두경부암"],
}

DISEASE_GENES = {
    "BRCA": ["TP53", "PIK3CA", "BRCA1", "BRCA2", "CDH1", "GATA3"],
    "LUAD": ["EGFR", "KRAS", "ALK", "STK11", "KEAP1", "TP53"],
    "LIHC": ["TP53", "CTNNB1", "AXIN1", "ARID1A"],
    "COAD": ["APC", "TP53", "KRAS", "BRAF", "PIK3CA", "MSI"],
    "STAD": ["TP53", "CDH1", "ARID1A", "PIK3CA", "ERBB2"],
    "PAAD": ["KRAS", "TP53", "CDKN2A", "SMAD4"],
    "HNSC": ["TP53", "CDKN2A", "PIK3CA", "NOTCH1"],
}


class AssistantAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class BedrockContext(BaseModel):
    instruction: str
    facts: List[str]
    safety_rules: List[str]


class AssistantAskResponse(BaseModel):
    disease: str
    intent: str
    answer: str
    evidence: Dict[str, Any]
    bedrock_context: BedrockContext
    warnings: List[str]
    diagnostics: Dict[str, Any]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _contains_any(question: str, keywords: List[str]) -> bool:
    lowered = question.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _detect_intent(question: str) -> str:
    if _contains_any(question, TOP_KEYWORDS):
        return "top_candidates"
    if _contains_any(question, DOCKING_KEYWORDS):
        return "docking_gene_pdb"
    if _contains_any(question, GRAPH_KEYWORDS):
        return "graph_summary"
    if _contains_any(question, EXPLANATION_KEYWORDS):
        return "candidate_explanation"
    return "general"


def _normalize_disease(path_disease: str, question: str) -> Tuple[str, Optional[str]]:
    try:
        canonical = normalize_disease(path_disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalized_path = _text(path_disease).upper()
    if normalized_path != canonical:
        return canonical, normalized_path
    return canonical, None


def _extract_top_n(question: str) -> int:
    lowered = question.lower()
    patterns = [
        r"(?:상위|top|탑|랭킹|순위)\s*(\d+)",
        r"(\d+)\s*개",
        r"(\d+)\s*(?:위|순위)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            try:
                parsed = int(match.group(1))
                if parsed > 0:
                    return parsed
            except ValueError:
                continue
    return DEFAULT_TOP_N


def _http_get_json(path: str, timeout_sec: float = 8.0) -> Tuple[Optional[Dict[str, Any]], int, Optional[str]]:
    url = INTERNAL_API_BASE + path
    req = request.Request(url=url, method="GET", headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = int(getattr(resp, "status", 200))
            parsed = json.loads(body) if body else {}
            if isinstance(parsed, dict):
                return parsed, status, None
            return {"data": parsed}, status, None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, int(exc.code), "HTTPError: " + detail
    except error.URLError as exc:
        return None, 0, "URLError: " + str(exc.reason)
    except Exception as exc:
        return None, 0, exc.__class__.__name__ + ": " + str(exc)


def _list_from_payload(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("items", "rows"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [row for row in candidate if isinstance(row, dict)]
    return []


def _first_present(item: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in item and item.get(key) not in ("", None):
            return item.get(key)
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text_value = _text(value)
    if not text_value:
        return None
    try:
        return float(text_value)
    except ValueError:
        return None


def _sort_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = []
    scored = []
    others = []
    for item in items:
        rank_value = _to_float(_first_present(item, RANK_FIELDS))
        if rank_value is not None:
            ranked.append((rank_value, item))
            continue
        score_value = _to_float(_first_present(item, SCORE_FIELDS))
        if score_value is not None:
            scored.append((score_value, item))
            continue
        others.append(item)

    ranked_sorted = [row for _, row in sorted(ranked, key=lambda pair: pair[0])]
    scored_sorted = [row for _, row in sorted(scored, key=lambda pair: pair[0], reverse=True)]
    return ranked_sorted + scored_sorted + others


def _extract_gene(disease: str, question: str) -> Optional[str]:
    upper_question = question.upper()
    for gene in DISEASE_GENES.get(disease, []):
        if gene.upper() in upper_question:
            return gene
    fallback = re.findall(r"\b[A-Z0-9]{3,12}\b", upper_question)
    return fallback[0] if fallback else None


def _compose_bedrock_context(disease: str, intent: str, evidence: Dict[str, Any]) -> BedrockContext:
    facts = ["disease=" + disease, "intent=" + intent]

    source_path = _text(evidence.get("source_path"))
    if source_path:
        facts.append("source_path=" + source_path)

    final_source_path = _text(evidence.get("final_source_path"))
    if final_source_path:
        facts.append("final_source_path=" + final_source_path)

    candidate_source_path = _text(evidence.get("candidate_source_path"))
    if candidate_source_path:
        facts.append("candidate_source_path=" + candidate_source_path)

    if evidence.get("requested_top_n") is not None:
        facts.append("requested_top_n=" + str(evidence.get("requested_top_n")))
    if evidence.get("returned_count") is not None:
        facts.append("returned_count=" + str(evidence.get("returned_count")))
    if evidence.get("node_count") is not None:
        facts.append("node_count=" + str(evidence.get("node_count")))
    if evidence.get("edge_count") is not None:
        facts.append("edge_count=" + str(evidence.get("edge_count")))

    gene = _text(evidence.get("gene"))
    if gene:
        facts.append("gene=" + gene)

    match_status = _text(evidence.get("match_status"))
    if match_status:
        facts.append("match_status=" + match_status)

    matched_item = evidence.get("matched_item")
    if isinstance(matched_item, dict):
        matched_name = _text(_first_present(matched_item, NAME_FIELDS))
        if matched_name:
            facts.append("matched_drug=" + matched_name)

    return BedrockContext(
        instruction="Use only the provided evidence. Do not fabricate missing values.",
        facts=facts,
        safety_rules=[
            "Do not claim clinical efficacy or approval unless present in evidence.",
            "State that candidates are internal model outputs.",
            "If evidence is empty, say evidence is insufficient.",
        ],
    )


def _top_candidates_response(disease: str, normalized_from: Optional[str], question: str) -> AssistantAskResponse:
    warnings = []
    api_calls = []
    top_n = _extract_top_n(question)

    primary_path = "/api/diseases/{}/final-candidates".format(disease)
    payload, status, err = _http_get_json(primary_path)
    api_calls.append({"path": primary_path, "status_code": status, "error": err or ""})
    items = _list_from_payload(payload)

    source_type = "final-candidates"
    source_path = primary_path
    selection_method = "rank_then_score"

    if status >= 400 or not items:
        fallback_path = "/api/diseases/{}/candidates".format(disease)
        fallback_payload, fallback_status, fallback_err = _http_get_json(fallback_path)
        api_calls.append({"path": fallback_path, "status_code": fallback_status, "error": fallback_err or ""})
        fallback_items = _list_from_payload(fallback_payload)
        if fallback_items:
            source_type = "candidates"
            source_path = fallback_path
            items = fallback_items
            warnings.append("final-candidates unavailable_or_empty; used candidates fallback")
        else:
            warnings.append("evidence is insufficient")

    sorted_items = _sort_candidates(items)
    top_items = sorted_items[:top_n]

    lines = []
    if top_items:
        lines.append("{} 기준 상위 {}개 후보입니다.".format(disease, top_n))
        for idx, item in enumerate(top_items, start=1):
            name = _text(_first_present(item, NAME_FIELDS)) or "(unknown)"
            rank_value = _text(_first_present(item, RANK_FIELDS)) or "-"
            score_value = _text(_first_present(item, SCORE_FIELDS)) or "-"
            tier_value = _text(_first_present(item, TIER_FIELDS)) or "-"
            lines.append(
                "{}. {} / rank={} / score={} / tier/grade={}".format(
                    idx, name, rank_value, score_value, tier_value
                )
            )
        lines.append("사용한 근거는 {} API입니다.".format(source_type))
    else:
        lines.append("{} 기준 후보 근거가 부족합니다.".format(disease))

    evidence = {
        "source_type": source_type,
        "source_path": source_path,
        "requested_top_n": top_n,
        "returned_count": len(top_items),
        "items": top_items,
        "selection_method": selection_method,
    }
    if normalized_from:
        evidence["normalized_from"] = normalized_from

    return AssistantAskResponse(
        disease=disease,
        intent="top_candidates",
        answer="\n".join(lines),
        evidence=evidence,
        bedrock_context=_compose_bedrock_context(disease, "top_candidates", evidence),
        warnings=warnings,
        diagnostics={"api_calls": api_calls},
    )


def _docking_response(disease: str, normalized_from: Optional[str], question: str) -> AssistantAskResponse:
    warnings = []
    api_calls = []

    gene = _extract_gene(disease, question)
    if gene:
        source_path = "/api/docking/{}/gene-pdb/{}".format(disease, gene)
    else:
        source_path = "/api/docking/{}/gene-pdb".format(disease)
        warnings.append("gene_not_detected; used disease-level docking list")

    payload, status, err = _http_get_json(source_path)
    api_calls.append({"path": source_path, "status_code": status, "error": err or ""})
    if status >= 400:
        warnings.append("evidence is insufficient")

    rows = _list_from_payload(payload)
    evidence = {
        "source_path": source_path,
        "gene": gene or "",
        "items": rows,
        "raw": payload or {},
    }
    if normalized_from:
        evidence["normalized_from"] = normalized_from

    answer = "{} 도킹/PDB 근거를 조회했습니다. source={}".format(disease, source_path)
    return AssistantAskResponse(
        disease=disease,
        intent="docking_gene_pdb",
        answer=answer,
        evidence=evidence,
        bedrock_context=_compose_bedrock_context(disease, "docking_gene_pdb", evidence),
        warnings=warnings,
        diagnostics={"api_calls": api_calls},
    )


def _graph_response(disease: str, normalized_from: Optional[str]) -> AssistantAskResponse:
    warnings = []
    source_path = "/api/graph/{}/ui-basic".format(disease)
    payload, status, err = _http_get_json(source_path)
    api_calls = [{"path": source_path, "status_code": status, "error": err or ""}]

    if status >= 400 or not isinstance(payload, dict):
        warnings.append("evidence is insufficient")
        evidence = {"source_path": source_path, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
        if normalized_from:
            evidence["normalized_from"] = normalized_from
        return AssistantAskResponse(
            disease=disease,
            intent="graph_summary",
            answer="{} 그래프 근거가 부족합니다.".format(disease),
            evidence=evidence,
            bedrock_context=_compose_bedrock_context(disease, "graph_summary", evidence),
            warnings=warnings,
            diagnostics={"api_calls": api_calls},
        )

    nodes = payload.get("nodes", [])
    edges = payload.get("edges", payload.get("links", []))
    summary = payload.get("summary", {})
    node_count = summary.get("node_count", len(nodes) if isinstance(nodes, list) else 0)
    edge_count = summary.get("edge_count", len(edges) if isinstance(edges, list) else 0)

    evidence = {
        "source_path": source_path,
        "nodes": nodes if isinstance(nodes, list) else [],
        "edges": edges if isinstance(edges, list) else [],
        "node_count": node_count,
        "edge_count": edge_count,
    }
    if normalized_from:
        evidence["normalized_from"] = normalized_from

    answer = "{} 그래프 요약입니다. node_count={}, edge_count={}".format(disease, node_count, edge_count)
    return AssistantAskResponse(
        disease=disease,
        intent="graph_summary",
        answer=answer,
        evidence=evidence,
        bedrock_context=_compose_bedrock_context(disease, "graph_summary", evidence),
        warnings=warnings,
        diagnostics={"api_calls": api_calls},
    )


def _candidate_explanation_response(disease: str, normalized_from: Optional[str], question: str) -> AssistantAskResponse:
    warnings = []
    api_calls = []

    final_path = "/api/diseases/{}/final-candidates".format(disease)
    candidate_path = "/api/diseases/{}/candidates".format(disease)

    final_payload, final_status, final_err = _http_get_json(final_path)
    candidate_payload, candidate_status, candidate_err = _http_get_json(candidate_path)
    api_calls.append({"path": final_path, "status_code": final_status, "error": final_err or ""})
    api_calls.append({"path": candidate_path, "status_code": candidate_status, "error": candidate_err or ""})

    merged = _list_from_payload(final_payload) + _list_from_payload(candidate_payload)
    lowered_question = question.lower()

    matched_item = None
    for item in merged:
        item_name = _text(_first_present(item, NAME_FIELDS))
        if item_name and item_name.lower() in lowered_question:
            matched_item = item
            break

    match_status = "matched" if matched_item is not None else "not_matched"
    if match_status != "matched":
        warnings.append("candidate_not_matched")
        warnings.append("evidence is insufficient")

    evidence = {
        "final_source_path": final_path,
        "candidate_source_path": candidate_path,
        "matched_item": matched_item or {},
        "match_status": match_status,
    }
    if normalized_from:
        evidence["normalized_from"] = normalized_from

    caution = (
        "이 답변은 내부 후보/점수 근거 기반 설명이며, 실제 치료제 적합성이나 임상 사용 가능성을 의미하지는 않습니다."
    )
    if matched_item:
        answer = "{} 후보 설명 근거를 찾았습니다. {}".format(disease, caution)
    else:
        answer = "{} 후보 설명 근거가 부족합니다. {}".format(disease, caution)

    return AssistantAskResponse(
        disease=disease,
        intent="candidate_explanation",
        answer=answer,
        evidence=evidence,
        bedrock_context=_compose_bedrock_context(disease, "candidate_explanation", evidence),
        warnings=warnings,
        diagnostics={"api_calls": api_calls},
    )


def _general_response(disease: str, normalized_from: Optional[str]) -> AssistantAskResponse:
    evidence = {"source_path": "", "returned_count": 0, "items": []}
    if normalized_from:
        evidence["normalized_from"] = normalized_from

    return AssistantAskResponse(
        disease=disease,
        intent="general",
        answer="질문 의도를 분류하지 못했습니다. 후보/도킹/그래프/설명 형태로 질문해 주세요.",
        evidence=evidence,
        bedrock_context=_compose_bedrock_context(disease, "general", evidence),
        warnings=["evidence is insufficient"],
        diagnostics={},
    )


@router.post("/{disease}/ask", response_model=AssistantAskResponse)
def ask_assistant(disease: str, payload: AssistantAskRequest) -> AssistantAskResponse:
    question = _text(payload.question)
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    normalized_disease, normalized_from = _normalize_disease(disease, question)
    intent = _detect_intent(question)

    if intent == "top_candidates":
        return _top_candidates_response(normalized_disease, normalized_from, question)
    if intent == "docking_gene_pdb":
        return _docking_response(normalized_disease, normalized_from, question)
    if intent == "graph_summary":
        return _graph_response(normalized_disease, normalized_from)
    if intent == "candidate_explanation":
        return _candidate_explanation_response(normalized_disease, normalized_from, question)
    return _general_response(normalized_disease, normalized_from)
