from __future__ import annotations

import argparse
from pathlib import Path


def _print_file_status(label: str, path: Path) -> None:
    if path.exists():
        size = path.stat().st_size
        print(f"[OK] {label}: {path} ({size} bytes)")
    else:
        print(f"[MISSING] {label}: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local/EC2 Literature RAG deploy artifacts.")
    parser.add_argument("--project-root", default=".", help="Project root path (default: current directory).")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    docs_dir = root / "data" / "rag_docs" / "literature"
    index_dir = root / "data" / "rag_index" / "literature"

    print(f"Project root: {root}")
    print("")
    print("== Docs directory ==")
    if docs_dir.exists():
        print(f"[OK] {docs_dir}")
    else:
        print(f"[MISSING] {docs_dir}")

    print("")
    print("== Index files ==")
    _print_file_status("index.faiss", index_dir / "index.faiss")
    _print_file_status("store_rows.jsonl", index_dir / "store_rows.jsonl")
    _print_file_status("store_embeddings.jsonl", index_dir / "store_embeddings.jsonl")
    _print_file_status("manifest.json", index_dir / "manifest.json")

    print("")
    print("API test example:")
    print(
        "curl -X POST http://127.0.0.1:8000/api/rag/literature/ask "
        "-H \"Content-Type: application/json\" "
        "-d '{\"disease\":\"BRCA\",\"drug_name\":\"Metformin\",\"question\":\"Why can Metformin be considered a BRCA repurposing candidate?\",\"top_k\":5}'"
    )


if __name__ == "__main__":
    main()
