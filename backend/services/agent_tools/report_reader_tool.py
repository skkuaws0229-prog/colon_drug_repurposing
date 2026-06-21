from __future__ import annotations

from pathlib import Path
from typing import Any


ALLOWED_TOP_DIRS = {"docs", "outputs/config_validation"}
ALLOWED_SUFFIXES = {".json", ".md"}


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:  # noqa: BLE001
        return False


def _is_allowed_rel(rel: Path) -> bool:
    rel_str = str(rel).replace("\\", "/")
    if not any(rel_str == x or rel_str.startswith(x + "/") for x in ALLOWED_TOP_DIRS):
        return False
    return rel.suffix.lower() in ALLOWED_SUFFIXES


def safe_read_report(path_like: str, project_root: Path) -> dict[str, Any]:
    candidate = (project_root / path_like).resolve()
    if not _is_within_root(candidate, project_root):
        return {"status": "blocked", "error": "path_outside_project_root"}

    rel = candidate.relative_to(project_root.resolve())
    if not _is_allowed_rel(rel):
        return {"status": "blocked", "error": "path_not_allowed"}

    if not candidate.exists():
        return {"status": "missing", "path": str(candidate)}

    try:
        text = candidate.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "path": str(candidate), "error": str(exc)}

    return {"status": "ok", "path": str(candidate), "preview": text[:1200]}


def read_reports_index(project_root: Path, disease: str) -> dict[str, Any]:
    targets = [
        f"docs/{disease.lower()}_image_modal_neo4j_write_plan_preview.md",
        f"outputs/config_validation/{disease.lower()}_image_modal_file_classification_report.json",
        f"outputs/config_validation/{disease.lower()}_image_modal_inventory_report.json",
    ]
    results = [safe_read_report(t, project_root) for t in targets]
    return {
        "status": "ok",
        "evidence": [
            {
                "type": "report_reader_index",
                "disease": disease,
                "checked_reports": results,
            }
        ],
        "limitations": ["report_reader_tool reads only docs/ and outputs/config_validation with .json/.md files."],
    }

