from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bedrock_embedding_service import BedrockEmbeddingService
from .bedrock_llm_service import BedrockLLMService
from .faiss_vector_store import FaissVectorStore


def _snippet(text: str, max_len: int = 320) -> str:
    body = (text or "").strip()
    if len(body) <= max_len:
        return body
    return body[: max_len - 3].rstrip() + "..."


def _normalize_source(src: str) -> str:
    raw = (src or "").strip().lower()
    if raw in {"pubmed", "med"}:
        return "PubMed"
    if raw in {"europepmc", "europe pmc"}:
        return "EuropePMC"
    return (src or "").strip() or "Unknown"


@dataclass
class LiteratureSearchOutput:
    no_evidence: bool
    query: str
    results: list[dict[str, Any]]
    error: str | None = None


@dataclass
class LiteratureAskOutput:
    no_evidence: bool
    answer: str
    evidence_summary: str
    retrieved_documents: list[dict[str, Any]]
    error: str | None = None


class LiteratureRAGService:
    def __init__(
        self,
        *,
        index_dir: str | Path | None = None,
        embedding_service: BedrockEmbeddingService | None = None,
        llm_service: BedrockLLMService | None = None,
    ) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.index_dir = self._resolve_index_dir(index_dir)
        self.embedding_service = embedding_service or BedrockEmbeddingService()
        self.llm_service = llm_service or BedrockLLMService()

    def _resolve_index_dir(self, index_dir: str | Path | None) -> Path:
        if index_dir and str(index_dir).strip():
            return Path(str(index_dir)).expanduser().resolve()

        env_local = (os.getenv("RAG_INDEX_LOCAL_DIR") or "").strip()
        if env_local:
            return Path(env_local).expanduser().resolve()

        return (self.project_root / "data" / "rag_index" / "literature").resolve()

    def _load_store(self) -> FaissVectorStore:
        return FaissVectorStore.load(self.index_dir)

    @staticmethod
    def _to_result_docs(hits: list[Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for hit in hits:
            row = hit.metadata
            results.append(
                {
                    "score": round(float(hit.score), 6),
                    "title": str(row.get("title") or ""),
                    "pmid": str(row.get("pmid") or ""),
                    "doi": str(row.get("doi") or ""),
                    "year": str(row.get("year") or ""),
                    "journal": str(row.get("journal") or ""),
                    "snippet": _snippet(str(row.get("chunk_text") or "")),
                    "source": _normalize_source(str(row.get("source") or "")),
                    "url": str(row.get("url") or ""),
                }
            )
        return results

    @staticmethod
    def _build_evidence_summary(results: list[dict[str, Any]]) -> str:
        if not results:
            return "No literature evidence retrieved."
        source_count: dict[str, int] = {}
        with_id = 0
        for r in results:
            source = str(r.get("source") or "Unknown")
            source_count[source] = source_count.get(source, 0) + 1
            if (r.get("pmid") or "").strip() or (r.get("doi") or "").strip():
                with_id += 1
        parts = [f"{k}:{v}" for k, v in sorted(source_count.items())]
        quality_note = (
            "\uadfc\uac70\uac00 \uc81c\ud55c\uc801\uc785\ub2c8\ub2e4."
            if len(results) < 3
            else "\uadfc\uac70\uac00 \uc874\uc7ac\ud569\ub2c8\ub2e4."
        )
        return (
            f"retrieved_chunks={len(results)}, identified_papers={with_id}, "
            f"sources=({', '.join(parts)}). {quality_note}"
        )

    def search(
        self,
        *,
        disease: str,
        drug_name: str,
        question: str,
        top_k: int = 5,
    ) -> LiteratureSearchOutput:
        query = (question or "").strip()
        if not query:
            return LiteratureSearchOutput(
                no_evidence=True,
                query=query,
                results=[],
                error="Question is empty.",
            )

        try:
            store = self._load_store()
        except FileNotFoundError:
            return LiteratureSearchOutput(
                no_evidence=True,
                query=query,
                results=[],
                error=(
                    "FAISS index not found. "
                    f"Resolved path: '{self.index_dir}'. "
                    "Set RAG_INDEX_LOCAL_DIR or sync/build index files first."
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return LiteratureSearchOutput(
                no_evidence=True,
                query=query,
                results=[],
                error=f"Failed to load FAISS index: {exc}",
            )

        try:
            query_vec = self.embedding_service.embed_text(query)
        except Exception as exc:  # noqa: BLE001
            return LiteratureSearchOutput(
                no_evidence=True,
                query=query,
                results=[],
                error=f"Bedrock embedding failed: {exc}",
            )

        hits = store.search(
            query_embedding=query_vec,
            top_k=max(1, int(top_k)),
            disease=(disease or "").strip(),
            drug_name=(drug_name or "").strip(),
        )
        if not hits:
            return LiteratureSearchOutput(no_evidence=True, query=query, results=[], error=None)

        results = self._to_result_docs(hits)
        return LiteratureSearchOutput(no_evidence=False, query=query, results=results, error=None)

    def ask(
        self,
        *,
        disease: str,
        drug_name: str,
        question: str,
        top_k: int = 5,
    ) -> LiteratureAskOutput:
        search_result = self.search(
            disease=disease,
            drug_name=drug_name,
            question=question,
            top_k=top_k,
        )
        if search_result.error:
            return LiteratureAskOutput(
                no_evidence=True,
                answer="\uadfc\uac70 \uc5c6\uc74c",
                evidence_summary=search_result.error,
                retrieved_documents=[],
                error=search_result.error,
            )

        if search_result.no_evidence or not search_result.results:
            return LiteratureAskOutput(
                no_evidence=True,
                answer=(
                    "\ud604\uc7ac \uc218\uc9d1\ub41c \ubb38\ud5cc\uc5d0\uc11c\ub294 "
                    "\uadfc\uac70\ub97c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4 "
                    "(\uadfc\uac70 \uc5c6\uc74c)."
                ),
                evidence_summary="No evidence was retrieved from the current literature index.",
                retrieved_documents=[],
                error=None,
            )

        evidence_summary = self._build_evidence_summary(search_result.results)
        try:
            answer = self.llm_service.generate_grounded_answer(
                disease=(disease or "").strip().upper(),
                drug_name=(drug_name or "").strip(),
                question=(question or "").strip(),
                retrieved_documents=search_result.results,
            )
        except Exception as exc:  # noqa: BLE001
            return LiteratureAskOutput(
                no_evidence=False,
                answer=(
                    "\uadfc\uac70 \uae30\ubc18 \ub2f5\ubcc0 \uc0dd\uc131\uc5d0 "
                    "\uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \uc544\ub798 \uac80\uc0c9 "
                    "\uadfc\uac70\ub97c \ud655\uc778\ud574\uc8fc\uc138\uc694."
                ),
                evidence_summary=f"{evidence_summary} LLM generation failed: {exc}",
                retrieved_documents=search_result.results,
                error=f"Bedrock LLM generation failed: {exc}",
            )

        return LiteratureAskOutput(
            no_evidence=False,
            answer=answer,
            evidence_summary=evidence_summary,
            retrieved_documents=search_result.results,
            error=None,
        )
