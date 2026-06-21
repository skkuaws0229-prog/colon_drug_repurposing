from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.scripts.rag_collect_literature import collect_literature


DEFAULT_DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "STAD", "PAAD", "HNSC"]


def _merge_run_summaries(
    *,
    summary_path: Path,
    per_disease_runs: list[dict[str, Any]],
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(per_disease_runs, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect literature for all configured diseases.")
    parser.add_argument("--config", default="configs/rag/literature_targets.yaml")
    parser.add_argument(
        "--diseases",
        nargs="+",
        default=DEFAULT_DISEASES,
        help="Disease codes to run. Default: BRCA COAD LUAD LIHC STAD PAAD HNSC",
    )
    parser.add_argument("--output-root", default="data/rag_docs/literature")
    parser.add_argument("--pubmed-retmax", type=int, default=25)
    parser.add_argument("--europepmc-page-size", type=int, default=25)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, Any]] = []

    for disease in [d.strip().upper() for d in args.diseases if d and d.strip()]:
        try:
            rows = collect_literature(
                config_path=args.config,
                output_root=output_root,
                disease_filters=[disease],
                pubmed_retmax=args.pubmed_retmax,
                europepmc_page_size=args.europepmc_page_size,
                continue_on_error=args.continue_on_error,
            )
            if not rows:
                run_rows.append(
                    {
                        "disease": disease,
                        "drug_name": "",
                        "pubmed_count": 0,
                        "europepmc_count": 0,
                        "total_count": 0,
                        "no_evidence": True,
                        "error": "No configured drugs or disease not found in config.",
                    }
                )
            else:
                run_rows.extend(rows)
        except Exception as exc:  # noqa: BLE001
            err = {
                "disease": disease,
                "drug_name": "",
                "pubmed_count": 0,
                "europepmc_count": 0,
                "total_count": 0,
                "no_evidence": True,
                "error": f"{exc.__class__.__name__}: {exc}",
            }
            run_rows.append(err)
            print(f"[ERROR] [{disease}] {err['error']}")
            if not args.continue_on_error:
                break

    summary_path = output_root / "collection_run_summary.json"
    _merge_run_summaries(summary_path=summary_path, per_disease_runs=run_rows)
    print(f"Saved merged summary: {summary_path}")


if __name__ == "__main__":
    main()
