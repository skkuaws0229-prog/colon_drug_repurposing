from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _norm_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    body = _norm_text(text)
    if not body:
        return []
    if len(body) <= chunk_size:
        return [body]

    chunks: list[str] = []
    start = 0
    n = len(body)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = body[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def _hash_token(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "little") % dim
    sign = 1.0 if (digest[4] % 2 == 0) else -1.0
    return idx, sign


def embed_text(text: str, *, dim: int = 384) -> list[float]:
    vec = [0.0] * dim
    tokens = TOKEN_RE.findall((text or "").lower())
    if not tokens:
        return vec
    for token in tokens:
        idx, sign = _hash_token(token, dim)
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def build_chunk_rows(
    documents: list[dict[str, Any]],
    *,
    disease: str,
    drug_name: str,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in documents:
        abstract = _norm_text(doc.get("abstract"))
        full_text = _norm_text(doc.get("full_text"))
        body = full_text if full_text else abstract
        if not body:
            continue
        segments = chunk_text(body, chunk_size=chunk_size, overlap=overlap)
        for idx, segment in enumerate(segments):
            out.append(
                {
                    "disease": disease,
                    "drug_name": drug_name,
                    "source": doc.get("source", ""),
                    "title": doc.get("title", ""),
                    "pmid": doc.get("pmid", ""),
                    "pmcid": doc.get("pmcid", ""),
                    "doi": doc.get("doi", ""),
                    "year": doc.get("year", ""),
                    "journal": doc.get("journal", ""),
                    "url": doc.get("url", ""),
                    "chunk_id": f"{disease}:{drug_name}:{doc.get('source','doc')}:{doc.get('pmid') or doc.get('doi') or idx}:{idx}",
                    "chunk_index": idx,
                    "text": segment,
                }
            )
    return out


class LocalVectorStore:
    def __init__(self, *, dim: int = 384) -> None:
        self.dim = dim
        self.rows: list[dict[str, Any]] = []
        self.embeddings: list[list[float]] = []

    def add_rows(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            text = _norm_text(row.get("text"))
            if not text:
                continue
            emb = embed_text(text, dim=self.dim)
            self.rows.append(row)
            self.embeddings.append(emb)

    def save(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        meta_path = output_dir / "store_rows.jsonl"
        emb_path = output_dir / "store_embeddings.jsonl"
        manifest_path = output_dir / "manifest.json"

        with meta_path.open("w", encoding="utf-8") as mf, emb_path.open("w", encoding="utf-8") as ef:
            for row, emb in zip(self.rows, self.embeddings):
                mf.write(json.dumps(row, ensure_ascii=False) + "\n")
                ef.write(json.dumps(emb) + "\n")

        manifest = {
            "backend": "local_hash_embedding",
            "dim": self.dim,
            "rows": len(self.rows),
            "files": {
                "rows": str(meta_path.name),
                "embeddings": str(emb_path.name),
            },
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, output_dir: Path) -> "LocalVectorStore":
        manifest_path = output_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Vector index manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        store = cls(dim=int(manifest.get("dim", 384)))
        meta_path = output_dir / manifest["files"]["rows"]
        emb_path = output_dir / manifest["files"]["embeddings"]
        if not meta_path.exists() or not emb_path.exists():
            raise FileNotFoundError("Vector store files are missing.")

        with meta_path.open("r", encoding="utf-8") as mf, emb_path.open("r", encoding="utf-8") as ef:
            for row_line, emb_line in zip(mf, ef):
                store.rows.append(json.loads(row_line))
                store.embeddings.append(json.loads(emb_line))
        return store

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        disease: str | None = None,
        drug_name: str | None = None,
    ) -> list[dict[str, Any]]:
        q_emb = embed_text(query, dim=self.dim)
        scored: list[tuple[float, dict[str, Any]]] = []
        disease_norm = (disease or "").strip().upper()
        drug_norm = (drug_name or "").strip().lower()

        for row, emb in zip(self.rows, self.embeddings):
            if disease_norm and str(row.get("disease", "")).upper() != disease_norm:
                continue
            if drug_norm and str(row.get("drug_name", "")).strip().lower() != drug_norm:
                continue
            score = cosine_similarity(q_emb, emb)
            scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict[str, Any]] = []
        for score, row in scored[:top_k]:
            item = dict(row)
            item["score"] = round(float(score), 6)
            out.append(item)
        return out


def detect_vector_backend() -> str:
    try:
        import faiss  # type: ignore  # noqa: F401
        import numpy  # type: ignore  # noqa: F401

        return "faiss"
    except Exception:
        pass
    try:
        import chromadb  # type: ignore  # noqa: F401

        return "chroma"
    except Exception:
        pass
    return "local"


def export_faiss(store: LocalVectorStore, output_dir: Path) -> bool:
    try:
        import faiss  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return False
    if not store.embeddings:
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.array(store.embeddings, dtype="float32")
    index = faiss.IndexFlatIP(store.dim)
    index.add(matrix)
    faiss.write_index(index, str(output_dir / "index.faiss"))
    (output_dir / "backend_hint.txt").write_text("faiss", encoding="utf-8")
    return True


def export_chroma(store: LocalVectorStore, output_dir: Path) -> bool:
    try:
        import chromadb  # type: ignore
    except Exception:
        return False
    if not store.embeddings:
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(output_dir / "chroma_db"))
    collection = client.get_or_create_collection(name="literature_rag")

    ids = []
    docs = []
    metas = []
    embs = []
    for i, (row, emb) in enumerate(zip(store.rows, store.embeddings)):
        chunk_id = str(row.get("chunk_id", "")) or f"chunk_{i}"
        ids.append(chunk_id)
        docs.append(str(row.get("text", "")))
        metas.append(
            {
                "disease": str(row.get("disease", "")),
                "drug_name": str(row.get("drug_name", "")),
                "source": str(row.get("source", "")),
                "pmid": str(row.get("pmid", "")),
                "doi": str(row.get("doi", "")),
                "year": str(row.get("year", "")),
                "title": str(row.get("title", "")),
            }
        )
        embs.append(emb)

    # Upsert in batches to keep request size manageable.
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=docs[i : i + batch_size],
            metadatas=metas[i : i + batch_size],
            embeddings=embs[i : i + batch_size],
        )
    (output_dir / "backend_hint.txt").write_text("chroma", encoding="utf-8")
    return True
