from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3

try:
    from services.bedrock_embedding_service import BedrockEmbeddingService
    from services.faiss_vector_store import FaissVectorStore
except ModuleNotFoundError:
    from backend.services.bedrock_embedding_service import BedrockEmbeddingService
    from backend.services.faiss_vector_store import FaissVectorStore


def _norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    body = _norm_text(text)
    if not body:
        return []
    if len(body) <= chunk_size:
        return [body]
    out: list[str] = []
    start = 0
    n = len(body)
    while start < n:
        end = min(start + chunk_size, n)
        piece = body[start:end].strip()
        if piece:
            out.append(piece)
        if end >= n:
            break
        start = max(0, end - overlap)
    return out


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    without_scheme = uri[5:]
    if "/" not in without_scheme:
        return without_scheme, ""
    bucket, prefix = without_scheme.split("/", 1)
    return bucket, prefix.strip("/")


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip().lower())
    return cleaned.strip("_") or "unknown"


@dataclass
class RawFileRef:
    disease: str
    drug_name: str
    source_file: str
    s3_key: str


def _extract_disease_and_drug(key: str, raw_prefix: str) -> tuple[str, str] | None:
    rel = key[len(raw_prefix) :].lstrip("/")
    parts = rel.split("/")
    if len(parts) < 3:
        return None
    return parts[0], parts[1]


def _list_jsonl_files(
    s3_client: Any,
    *,
    bucket: str,
    prefix: str,
    disease_filter: str | None = None,
    drug_filter: str | None = None,
) -> list[RawFileRef]:
    raw_prefix = f"{prefix.strip('/')}/raw/"
    paginator = s3_client.get_paginator("list_objects_v2")
    refs: list[RawFileRef] = []

    disease_filter_norm = (disease_filter or "").strip().lower()
    drug_filter_norm = _safe_slug(drug_filter or "") if drug_filter else ""

    for page in paginator.paginate(Bucket=bucket, Prefix=raw_prefix):
        for item in page.get("Contents", []) or []:
            key = str(item.get("Key") or "")
            if not (
                key.endswith("/pubmed_results.jsonl")
                or key.endswith("/europepmc_results.jsonl")
            ):
                continue
            parsed = _extract_disease_and_drug(key, raw_prefix)
            if not parsed:
                continue
            disease, drug = parsed
            if disease_filter_norm and disease.strip().lower() != disease_filter_norm:
                continue
            if drug_filter_norm and drug.strip().lower() != drug_filter_norm:
                continue
            refs.append(
                RawFileRef(
                    disease=disease,
                    drug_name=drug,
                    source_file=Path(key).name,
                    s3_key=key,
                )
            )
    return refs


def _read_jsonl_from_s3(s3_client: Any, *, bucket: str, key: str) -> list[dict[str, Any]]:
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read().decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _dedupe_docs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("no_evidence") is True:
            continue
        pmid = _norm_text(str(row.get("pmid") or ""))
        doi = _norm_text(str(row.get("doi") or "")).lower()
        title = _norm_text(str(row.get("title") or "")).lower()
        disease = _norm_text(str(row.get("disease") or "")).upper()
        drug = _norm_text(str(row.get("drug_name") or "")).lower()
        key = f"{disease}|{drug}|{pmid or doi or title}"
        if key.endswith("|"):
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _build_document_text(row: dict[str, Any]) -> str:
    title = _norm_text(str(row.get("title") or ""))
    abstract = _norm_text(str(row.get("abstract") or ""))
    full_text = _norm_text(str(row.get("full_text") or ""))
    parts: list[str] = []
    if title:
        parts.append(f"Title: {title}")
    if abstract:
        parts.append(f"Abstract: {abstract}")
    if full_text:
        parts.append(f"Full text: {full_text}")
    return "\n\n".join(parts).strip()


def _chunk_documents(
    rows: list[dict[str, Any]], *, chunk_size: int, overlap: int
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for row in rows:
        disease = _norm_text(str(row.get("disease") or "")).upper()
        drug_name = _norm_text(str(row.get("drug_name") or ""))
        if not disease or not drug_name:
            continue

        text = _build_document_text(row)
        if not text:
            continue
        pieces = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for idx, piece in enumerate(pieces):
            chunks.append(
                {
                    "disease": disease,
                    "drug_name": drug_name,
                    "pmid": _norm_text(str(row.get("pmid") or "")),
                    "doi": _norm_text(str(row.get("doi") or "")),
                    "title": _norm_text(str(row.get("title") or "")),
                    "journal": _norm_text(str(row.get("journal") or "")),
                    "year": _norm_text(str(row.get("year") or "")),
                    "source": _norm_text(str(row.get("source") or "")),
                    "query": _norm_text(str(row.get("query") or "")),
                    "url": _norm_text(str(row.get("url") or "")),
                    "chunk_index": idx,
                    "chunk_text": piece,
                }
            )
    return chunks


def _write_metadata_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build FAISS literature RAG index from S3 JSONL files."
    )
    parser.add_argument(
        "--s3-prefix",
        default=f"s3://{os.getenv('RAG_S3_BUCKET', 'say2-4team')}/{os.getenv('RAG_S3_PREFIX', 'rag/literature')}",
        help="S3 prefix containing raw literature files.",
    )
    parser.add_argument(
        "--output",
        default="data/rag_index/literature",
        help="Output directory for FAISS index and metadata.",
    )
    parser.add_argument("--disease", default=None, help="Optional disease filter, e.g. BRCA")
    parser.add_argument("--drug-name", default=None, help="Optional drug slug filter")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=180)
    args = parser.parse_args()

    bucket, prefix = _parse_s3_uri(args.s3_prefix)
    region = os.getenv("AWS_REGION", "us-east-1")
    s3_client = boto3.client("s3", region_name=region)

    refs = _list_jsonl_files(
        s3_client,
        bucket=bucket,
        prefix=prefix,
        disease_filter=args.disease,
        drug_filter=args.drug_name,
    )
    if not refs:
        raise RuntimeError(
            f"No literature JSONL files found under s3://{bucket}/{prefix}/raw/"
        )

    all_rows: list[dict[str, Any]] = []
    for ref in refs:
        rows = _read_jsonl_from_s3(s3_client, bucket=bucket, key=ref.s3_key)
        for row in rows:
            row.setdefault("disease", ref.disease)
            row.setdefault("drug_name", ref.drug_name)
        all_rows.extend(rows)

    deduped_docs = _dedupe_docs(all_rows)
    chunk_rows = _chunk_documents(
        deduped_docs,
        chunk_size=max(300, int(args.chunk_size)),
        overlap=max(0, int(args.chunk_overlap)),
    )
    if not chunk_rows:
        raise RuntimeError("No chunkable evidence found. All documents are empty/no_evidence.")

    embedder = BedrockEmbeddingService()
    texts = [row["chunk_text"] for row in chunk_rows]
    embeddings = embedder.embed_texts(texts)
    if len(embeddings) != len(chunk_rows):
        raise RuntimeError("Embedding count mismatch with chunk rows.")

    store = FaissVectorStore.build(embeddings=embeddings, metadata=chunk_rows)
    output_dir = Path(args.output)
    store.save(output_dir)
    _write_metadata_jsonl(output_dir / "metadata.jsonl", chunk_rows)

    summary = {
        "s3_prefix": args.s3_prefix,
        "output_dir": str(output_dir),
        "input_rows": len(all_rows),
        "deduped_docs": len(deduped_docs),
        "chunk_rows": len(chunk_rows),
        "faiss_dim": store.dim,
        "disease_filter": args.disease,
        "drug_filter": args.drug_name,
    }
    (output_dir / "build_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
