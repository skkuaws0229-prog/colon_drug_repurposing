from __future__ import annotations

import json
import os
import time
from typing import Any

import boto3


SYSTEM_PROMPT = (
    "You are a biomedical RAG assistant.\n"
    "Use only the provided retrieved literature context.\n"
    "Do not invent facts.\n"
    "Separate direct evidence from indirect evidence.\n"
    "Do not claim clinical efficacy unless the context explicitly supports it.\n"
    "Return a cautious drug-repurposing interpretation."
)


class BedrockLLMService:
    def __init__(
        self,
        *,
        region_name: str | None = None,
        model_id: str | None = None,
        max_tokens: int = 900,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> None:
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.model_id = model_id or os.getenv(
            "BEDROCK_LLM_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        if not (self.region_name or "").strip():
            raise ValueError("AWS_REGION is empty. Set AWS_REGION (e.g., us-east-1).")
        if not (self.model_id or "").strip():
            raise ValueError(
                "BEDROCK_LLM_MODEL_ID is empty. Set BEDROCK_LLM_MODEL_ID "
                "(e.g., anthropic.claude-3-5-sonnet-20241022-v2:0)."
            )
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    @staticmethod
    def _format_context(retrieved_documents: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for i, doc in enumerate(retrieved_documents, start=1):
            lines.append(f"[Document {i}]")
            lines.append(f"score: {doc.get('score', '')}")
            lines.append(f"title: {doc.get('title', '')}")
            lines.append(f"pmid: {doc.get('pmid', '')}")
            lines.append(f"doi: {doc.get('doi', '')}")
            lines.append(f"year: {doc.get('year', '')}")
            lines.append(f"journal: {doc.get('journal', '')}")
            lines.append(f"source: {doc.get('source', '')}")
            lines.append(f"url: {doc.get('url', '')}")
            lines.append(f"snippet: {doc.get('snippet', '')}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_user_prompt(
        *,
        disease: str,
        drug_name: str,
        question: str,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        context = BedrockLLMService._format_context(retrieved_documents)
        return (
            f"Disease: {disease}\n"
            f"Drug: {drug_name}\n"
            f"Question: {question}\n\n"
            "Retrieved literature context:\n"
            f"{context}\n\n"
            "Output requirements:\n"
            "1) Use only the context above.\n"
            "2) Separate sections: Direct evidence, Indirect evidence, Limitations.\n"
            "3) If evidence is weak or sparse, explicitly say "
            "'\uadfc\uac70\uac00 \uc81c\ud55c\uc801\uc785\ub2c8\ub2e4'.\n"
            "4) Avoid overclaims such as "
            "'\uce58\ub8cc \ud6a8\uacfc\uac00 \uc785\uc99d\ub428'.\n"
            "5) Use cautious wording like "
            "'\uc7ac\ucc3d\ucd9c \ud6c4\ubcf4 \uac00\ub2a5\uc131'.\n"
            "6) Include inline citations in style [PMID:xxxx] or [DOI:xxxx].\n"
            "7) Mention key paper identifiers (title/year and PMID or DOI) when possible.\n"
            "8) If context is insufficient, state uncertainty clearly without invention.\n"
        )

    @staticmethod
    def _extract_text(response_payload: dict[str, Any]) -> str:
        content = response_payload.get("content")
        if isinstance(content, list):
            texts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_val = block.get("text")
                    if isinstance(text_val, str):
                        texts.append(text_val)
            if texts:
                return "\n".join(texts).strip()
        return ""

    def generate_grounded_answer(
        self,
        *,
        disease: str,
        drug_name: str,
        question: str,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        user_prompt = self._build_user_prompt(
            disease=disease,
            drug_name=drug_name,
            question=question,
            retrieved_documents=retrieved_documents,
        )
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": int(self.max_tokens),
            "temperature": float(self.temperature),
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body),
                )
                payload = json.loads(response["body"].read())
                answer = self._extract_text(payload)
                if answer:
                    return answer
                raise RuntimeError("Bedrock LLM returned empty text.")
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt, 8))

        raise RuntimeError(f"Bedrock LLM generation failed after retries: {last_error}")
