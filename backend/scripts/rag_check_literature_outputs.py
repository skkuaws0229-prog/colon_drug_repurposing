from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "STAD", "PAAD", "HNSC"]


def _read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _load_summary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def _build_md_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "disease",
        "raw_dir_exists",
        "drug_dir_count",
        "pubmed_jsonl_count",
        "europepmc_jsonl_count",
        "chunks_jsonl_count",
        "total_retrieved_documents",
        "no_evidence_count",
        "error_count",
    ]
    lines = [
        "# Literature Collection Output Check",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    base = Path("data/rag_docs/literature")
    raw_root = base / "raw"
    chunks_root = base / "chunks"
    summary_path = base / "collection_run_summary.json"
    summary_rows = _load_summary(summary_path)

    out_rows: list[dict[str, Any]] = []
    for disease in DEFAULT_DISEASES:
        disease_upper = disease.upper()
        raw_disease_dir = raw_root / disease_upper
        chunks_disease_dir = chunks_root / disease_upper

        drug_dirs = [p for p in raw_disease_dir.iterdir() if p.is_dir()] if raw_disease_dir.exists() else []
        pubmed_jsonl_count = 0
        europepmc_jsonl_count = 0
        total_docs = 0
        for drug_dir in drug_dirs:
            pubmed_path = drug_dir / "pubmed_results.jsonl"
            epmc_path = drug_dir / "europepmc_results.jsonl"
            pubmed_count = _read_jsonl_count(pubmed_path)
            epmc_count = _read_jsonl_count(epmc_path)
            if pubmed_path.exists():
                pubmed_jsonl_count += 1
            if epmc_path.exists():
                europepmc_jsonl_count += 1
            total_docs += pubmed_count + epmc_count

        chunk_files = list(chunks_disease_dir.glob("*/chunks.jsonl")) if chunks_disease_dir.exists() else []
        disease_summary_rows = [r for r in summary_rows if str(r.get("disease", "")).upper() == disease_upper]
        no_evidence_count = sum(1 for r in disease_summary_rows if bool(r.get("no_evidence", False)))
        error_count = sum(1 for r in disease_summary_rows if str(r.get("error", "")).strip())

        out_rows.append(
            {
                "disease": disease_upper,
                "raw_dir_exists": raw_disease_dir.exists(),
                "drug_dir_count": len(drug_dirs),
                "pubmed_jsonl_count": pubmed_jsonl_count,
                "europepmc_jsonl_count": europepmc_jsonl_count,
                "chunks_jsonl_count": len(chunk_files),
                "total_retrieved_documents": total_docs,
                "no_evidence_count": no_evidence_count,
                "error_count": error_count,
            }
        )

    out_json_path = Path("outputs/rag/literature_collection_check.json")
    out_md_path = Path("docs/literature_collection_check.md")
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(out_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md_path.write_text(_build_md_table(out_rows), encoding="utf-8")

    print(f"Saved: {out_json_path}")
    print(f"Saved: {out_md_path}")


if __name__ == "__main__":
    main()
