from __future__ import annotations

import json
import os
import time
from typing import Any

import boto3


class BedrockEmbeddingService:
    def __init__(
        self,
        *,
        region_name: str | None = None,
        model_id: str | None = None,
        dimensions: int | None = None,
        normalize: bool = True,
        max_retries: int = 4,
    ) -> None:
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.model_id = model_id or os.getenv(
            "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
        )
        if not (self.region_name or "").strip():
            raise ValueError("AWS_REGION is empty. Set AWS_REGION (e.g., us-east-1).")
        if not (self.model_id or "").strip():
            raise ValueError(
                "BEDROCK_EMBED_MODEL_ID is empty. Set BEDROCK_EMBED_MODEL_ID "
                "(e.g., amazon.titan-embed-text-v2:0)."
            )
        self.dimensions = dimensions
        self.normalize = normalize
        self.max_retries = max_retries
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    def _build_payload(self, text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"inputText": text}
        if self.dimensions is not None:
            payload["dimensions"] = int(self.dimensions)
        payload["normalize"] = bool(self.normalize)
        return payload

    @staticmethod
    def _extract_embedding(response_payload: dict[str, Any]) -> list[float]:
        if isinstance(response_payload.get("embedding"), list):
            return [float(v) for v in response_payload["embedding"]]

        emb_by_type = response_payload.get("embeddingsByType")
        if isinstance(emb_by_type, dict):
            if isinstance(emb_by_type.get("float"), list):
                return [float(v) for v in emb_by_type["float"]]
            for value in emb_by_type.values():
                if isinstance(value, list):
                    return [float(v) for v in value]

        raise RuntimeError("Bedrock embedding response missing embedding vector.")

    def embed_text(self, text: str) -> list[float]:
        body = (text or "").strip()
        if not body:
            raise ValueError("Cannot embed empty text.")

        payload = self._build_payload(body)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload),
                )
                data = json.loads(response["body"].read())
                vector = self._extract_embedding(data)
                if not vector:
                    raise RuntimeError("Received empty embedding vector from Bedrock.")
                return vector
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt, 10))

        raise RuntimeError(f"Bedrock embedding failed after retries: {last_error}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            embeddings.append(self.embed_text(text))
        return embeddings
