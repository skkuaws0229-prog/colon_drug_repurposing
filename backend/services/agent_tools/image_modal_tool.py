from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def summarize_image_modal(disease: str, project_root: Path) -> dict[str, Any]:
    inventory_path = project_root / "outputs" / "config_validation" / "brca_image_modal_inventory_report.json"
    classification_path = project_root / "outputs" / "config_validation" / "brca_image_modal_file_classification_report.json"

    inventory = _read_json(inventory_path)
    classification = _read_json(classification_path)

    if (disease != "BRCA") or (inventory is None and classification is None):
        return {
            "status": "fallback",
            "evidence": [
                {
                    "type": "image_modal_summary",
                    "status": "unavailable",
                    "message": "BRCA image modal report files are missing or disease is not BRCA.",
                }
            ],
            "limitations": ["Image modal evidence is limited due to missing report files."],
        }

    total_object_count = (inventory or {}).get("summary", {}).get("total_object_count", None)
    metadata_count = None
    needs_review_files: list[str] = []
    do_not_load_files: list[str] = []
    image_candidates: list[str] = []

    if classification:
        rows = classification.get("files", []) if isinstance(classification.get("files"), list) else []
        for row in rows:
            if row.get("proposed_postgres_target") == "image_modal_asset":
                image_candidates.append(str(row.get("file_name", "")))
            if row.get("proposed_postgres_target") == "manual_review_required":
                needs_review_files.append(str(row.get("file_name", "")))
            if row.get("proposed_postgres_target") == "do_not_load":
                do_not_load_files.append(str(row.get("file_name", "")))
        metadata_count = int(
            sum(1 for r in rows if r.get("proposed_postgres_target") == "image_modal_metadata_review")
        )

    known_images = [
        "cluster_kaplan_meier_os.png",
        "kaplan_meier_os.png",
        "pca_plot.png",
    ]

    return {
        "status": "ok",
        "evidence": [
            {
                "type": "image_modal_summary",
                "disease": disease,
                "source_files": [str(inventory_path), str(classification_path)],
                "total_object_count": total_object_count,
                "image_modal_asset_candidates": image_candidates,
                "metadata_review_candidate_count": metadata_count,
                "needs_review_files": needs_review_files,
                "do_not_load_files": do_not_load_files,
                "known_image_files": known_images,
                "embedding_candidate": "all_slide_embeddings_shard00_merged.npy",
            }
        ],
        "limitations": [
            "No image binary interpretation was performed.",
            "No embedding .npy loading/shape verification was performed.",
        ],
    }

