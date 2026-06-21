from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _normalize_disease(value: str | None) -> str:
    return (value or "").strip().upper()


def _normalize_drug(value: str | None) -> str:
    return (value or "").strip().lower()


@dataclass
class FaissSearchHit:
    score: float
    metadata: dict[str, Any]


class FaissVectorStore:
    def __init__(self, *, index: Any, metadata: list[dict[str, Any]], dim: int) -> None:
        self.index = index
        self.metadata = metadata
        self.dim = dim

    @staticmethod
    def _deps() -> tuple[Any, Any]:
        try:
            import faiss  # type: ignore
            import numpy as np  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "faiss/numpy is required. Install with: pip install faiss-cpu numpy"
            ) from exc
        return faiss, np

    @classmethod
    def build(
        cls, embeddings: list[list[float]], metadata: list[dict[str, Any]]
    ) -> "FaissVectorStore":
        if not embeddings:
            raise ValueError("No embeddings provided to build FAISS index.")
        if len(embeddings) != len(metadata):
            raise ValueError("Embedding count and metadata count do not match.")

        faiss, np = cls._deps()
        matrix = np.asarray(embeddings, dtype="float32")
        if matrix.ndim != 2:
            raise ValueError("Embeddings must be a 2D matrix.")
        faiss.normalize_L2(matrix)
        dim = int(matrix.shape[1])
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return cls(index=index, metadata=metadata, dim=dim)

    def save(self, output_dir: str | Path) -> None:
        faiss, _np = self._deps()
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        index_path = out / "index.faiss"
        metadata_path = out / "metadata.jsonl"
        manifest_path = out / "manifest.json"

        faiss.write_index(self.index, str(index_path))

        with metadata_path.open("w", encoding="utf-8") as f:
            for row in self.metadata:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        manifest = {
            "backend": "faiss_index_flat_ip",
            "dim": self.dim,
            "rows": len(self.metadata),
            "index_file": index_path.name,
            "metadata_file": metadata_path.name,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, output_dir: str | Path) -> "FaissVectorStore":
        faiss, _np = cls._deps()
        out = Path(output_dir)
        manifest_path = out / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"FAISS manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index_path = out / str(manifest.get("index_file", "index.faiss"))
        metadata_path = out / str(manifest.get("metadata_file", "metadata.jsonl"))
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                "FAISS index or metadata file is missing. Rebuild index first."
            )

        index = faiss.read_index(str(index_path))
        metadata: list[dict[str, Any]] = []
        with metadata_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                metadata.append(json.loads(line))

        return cls(index=index, metadata=metadata, dim=int(manifest.get("dim", 0) or 0))

    def search(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        disease: str | None = None,
        drug_name: str | None = None,
    ) -> list[FaissSearchHit]:
        faiss, np = self._deps()
        if self.index.ntotal == 0:
            return []
        if not query_embedding:
            return []

        q = np.asarray([query_embedding], dtype="float32")
        faiss.normalize_L2(q)

        disease_filter = _normalize_disease(disease)
        drug_filter = _normalize_drug(drug_name)
        k = int(self.index.ntotal) if (disease_filter or drug_filter) else min(int(self.index.ntotal), max(1, top_k))

        distances, indices = self.index.search(q, k)
        hits: list[FaissSearchHit] = []
        for score, row_idx in zip(distances[0], indices[0]):
            if row_idx < 0:
                continue
            row = self.metadata[int(row_idx)]
            if disease_filter and _normalize_disease(str(row.get("disease"))) != disease_filter:
                continue
            if drug_filter and _normalize_drug(str(row.get("drug_name"))) != drug_filter:
                continue
            hits.append(FaissSearchHit(score=float(score), metadata=row))
            if len(hits) >= top_k:
                break
        return hits
