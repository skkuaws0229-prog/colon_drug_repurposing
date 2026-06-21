from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from backend.services.literature_search_service import run_literature_collection_for_drug


def _load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Config must be a mapping.")
    return data


def _extract_drug_names(drugs: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(drugs, list):
        return out
    for item in drugs:
        if isinstance(item, str):
            name = item.strip()
            if name:
                out.append(name)
            continue
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            if name:
                out.append(name)
    return out


def _iter_targets_from_targets_list(config: dict[str, Any], disease_filters: set[str] | None = None):
    targets = config.get("targets", []) or []
    if not isinstance(targets, list):
        return
    for item in targets:
        if not isinstance(item, dict):
            continue
        disease_obj = item.get("disease", {}) or {}
        if not isinstance(disease_obj, dict):
            continue
        disease_code = str(disease_obj.get("code", "")).strip().upper()
        if not disease_code:
            continue
        if disease_filters and disease_code not in disease_filters:
            continue
        aliases = disease_obj.get("aliases", []) or []
        driver_genes = item.get("driver_genes", []) or []
        pathways = item.get("pathways", []) or []
        drugs = _extract_drug_names(item.get("drugs", []))
        for drug in drugs:
            yield disease_code, aliases, driver_genes, pathways, drug


def _iter_targets(config: dict[str, Any], disease_filters: set[str] | None = None):
    yielded = False
    for row in _iter_targets_from_targets_list(config, disease_filters):
        yielded = True
        yield row
    if yielded:
        return

    diseases = config.get("diseases", {}) or {}
    if not isinstance(diseases, dict):
        raise ValueError("Config must have either 'targets' list or 'diseases' mapping.")

    for disease_code, payload in diseases.items():
        disease_code_up = str(disease_code).strip().upper()
        if not disease_code_up:
            continue
        if disease_filters and disease_code_up not in disease_filters:
            continue
        payload = payload or {}
        aliases = payload.get("aliases", []) or []
        driver_genes = payload.get("driver_genes", []) or []
        pathways = payload.get("pathways", []) or []
        drugs = _extract_drug_names(payload.get("drugs", []))
        if not drugs:
            drugs = [str(x) for x in (payload.get("drugs", []) or []) if str(x).strip()]
        for drug in drugs:
            yield disease_code_up, aliases, driver_genes, pathways, str(drug)


def collect_literature(
    *,
    config_path: str | Path,
    output_root: str | Path = "data/rag_docs/literature",
    disease_filters: list[str] | None = None,
    pubmed_retmax: int = 25,
    europepmc_page_size: int = 25,
    continue_on_error: bool = False,
) -> list[dict[str, Any]]:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    config = _load_config(cfg_path)
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    filters = {d.strip().upper() for d in (disease_filters or []) if d and d.strip()}

    runs: list[dict[str, Any]] = []
    for disease, aliases, genes, pathways, drug in _iter_targets(config, filters if filters else None):
        try:
            status = run_literature_collection_for_drug(
                disease=disease,
                drug_name=drug,
                disease_aliases=[str(x) for x in aliases],
                driver_genes=[str(x) for x in genes],
                pathways=[str(x) for x in pathways],
                out_root=out_root,
                pubmed_retmax=pubmed_retmax,
                europepmc_page_size=europepmc_page_size,
            )
            runs.append(status)
            print(
                f"[{disease}] {drug}: pubmed={status['pubmed_count']} "
                f"europepmc={status['europepmc_count']} total={status['total_count']} no_evidence={status['no_evidence']}"
            )
        except Exception as exc:  # noqa: BLE001
            error_row = {
                "disease": disease,
                "drug_name": drug,
                "pubmed_count": 0,
                "europepmc_count": 0,
                "total_count": 0,
                "no_evidence": True,
                "error": f"{exc.__class__.__name__}: {exc}",
            }
            runs.append(error_row)
            print(f"[ERROR] [{disease}] {drug}: {error_row['error']}")
            if not continue_on_error:
                raise

    run_summary_path = out_root / "collection_run_summary.json"
    run_summary_path.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved summary: {run_summary_path}")
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect external literature (PubMed + Europe PMC) for RAG.")
    parser.add_argument("--config", required=True, help="YAML path, e.g. configs/rag/literature_targets.yaml")
    parser.add_argument("--disease", default=None, help="Optional disease filter, e.g. BRCA")
    parser.add_argument("--output-root", default="data/rag_docs/literature", help="Base output directory")
    parser.add_argument("--pubmed-retmax", type=int, default=25, help="PubMed hits per query")
    parser.add_argument("--europepmc-page-size", type=int, default=25, help="Europe PMC hits per query")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue collection on per-drug errors.")
    args = parser.parse_args()
    filters = [args.disease] if args.disease else None
    collect_literature(
        config_path=args.config,
        output_root=args.output_root,
        disease_filters=filters,
        pubmed_retmax=args.pubmed_retmax,
        europepmc_page_size=args.europepmc_page_size,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    main()
