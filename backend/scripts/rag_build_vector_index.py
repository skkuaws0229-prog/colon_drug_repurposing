from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.vector_store import (
    LocalVectorStore,
    build_chunk_rows,
    detect_vector_backend,
    export_chroma,
    export_faiss,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _dedupe_docs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        pmid = str(row.get("pmid", "")).strip()
        doi = str(row.get("doi", "")).strip().lower()
        title = str(row.get("title", "")).strip().lower()
        key = pmid or doi or title
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _iter_raw_leaf_dirs(raw_root: Path):
    if not raw_root.exists():
        return
    for disease_dir in raw_root.iterdir():
        if not disease_dir.is_dir():
            continue
        for drug_dir in disease_dir.iterdir():
            if drug_dir.is_dir():
                yield disease_dir.name, drug_dir.name, drug_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build vector index from collected literature JSONL files.")
    parser.add_argument("--input", default="data/rag_docs/literature", help="Literature base directory")
    parser.add_argument("--output", default="data/rag_index/literature", help="Vector index output directory")
    parser.add_argument("--chunk-size", type=int, default=1200, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=180, help="Chunk overlap in characters")
    parser.add_argument("--embedding-dim", type=int, default=384, help="Hash embedding dimension")
    args = parser.parse_args()

    base_input = Path(args.input)
    raw_root = base_input / "raw"
    chunk_root = base_input / "chunks"
    chunk_root.mkdir(parents=True, exist_ok=True)

    store = LocalVectorStore(dim=args.embedding_dim)
    all_chunks_count = 0

    for disease, drug_slug, leaf in _iter_raw_leaf_dirs(raw_root):
        pubmed_rows = _read_jsonl(leaf / "pubmed_results.jsonl")
        epmc_rows = _read_jsonl(leaf / "europepmc_results.jsonl")
        docs = _dedupe_docs(pubmed_rows + epmc_rows)
        chunk_rows = build_chunk_rows(
            docs,
            disease=disease,
            drug_name=drug_slug,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
        )
        out_chunks_path = chunk_root / disease / drug_slug / "chunks.jsonl"
        _write_jsonl(out_chunks_path, chunk_rows)
        store.add_rows(chunk_rows)
        all_chunks_count += len(chunk_rows)
        print(f"[{disease}/{drug_slug}] docs={len(docs)} chunks={len(chunk_rows)}")

    output_dir = Path(args.output)
    store.save(output_dir)
    backend = detect_vector_backend()
    if backend == "faiss":
        saved = export_faiss(store, output_dir)
        print(f"FAISS export: {saved}")
    elif backend == "chroma":
        saved = export_chroma(store, output_dir)
        print(f"Chroma export: {saved}")
    else:
        print("FAISS/Chroma not installed. Saved local hash-embedding index only.")

    print(f"Saved vector index: {output_dir} (chunks={all_chunks_count}, rows={len(store.rows)})")


if __name__ == "__main__":
    main()
