#!/usr/bin/env python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL = {
    "disease",
    "display_name",
    "run_id",
    "s3_parent_prefix",
    "s3_release_prefix",
    "status",
    "input_files",
    "biology",
    "kg",
}
REQUIRED_BIOLOGY = {"disease_aliases", "marker_genes", "subtypes"}
REQUIRED_KG = {"disease_node_name", "disease_display_name"}
LEGACY_REQUIRED_TOP_LEVEL = {"disease", "biology", "paths", "load_policy"}
LEGACY_REQUIRED_DISEASE = {"code", "name", "aliases"}
LEGACY_REQUIRED_BIOLOGY = {"driver_genes", "molecular_subtypes"}
LEGACY_REQUIRED_PATHS = {"s3_prefix", "local_cache"}


@dataclass
class ValidationRow:
    disease: str
    run_id: str
    status: str
    s3_parent_prefix: str
    s3_release_prefix: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_project_markers(path: Path) -> bool:
    return (path / "scripts").is_dir() and (path / "configs").is_dir() and (path / "outputs").is_dir()


def find_project_root() -> Path:
    cwd = Path.cwd()
    if has_project_markers(cwd):
        return cwd
    script_root = Path(__file__).absolute().parents[2]
    if has_project_markers(script_root):
        return script_root
    return script_root


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def validate_one(path: Path) -> ValidationRow:
    cfg = load_yaml(path)
    disease_value = cfg.get("disease", path.stem)
    if isinstance(disease_value, dict):
        disease = str(disease_value.get("code", path.stem)).strip() or path.stem
    else:
        disease = str(disease_value).strip() or path.stem

    paths = cfg.get("paths") if isinstance(cfg.get("paths"), dict) else {}
    row = ValidationRow(
        disease=disease,
        run_id=str(cfg.get("run_id", "")),
        status=str(cfg.get("status", "")),
        s3_parent_prefix=str(cfg.get("s3_parent_prefix", paths.get("s3_prefix", ""))),
        s3_release_prefix=str(cfg.get("s3_release_prefix", "")),
    )

    canonical_mode = REQUIRED_TOP_LEVEL.issubset(set(cfg.keys()))
    legacy_mode = LEGACY_REQUIRED_TOP_LEVEL.issubset(set(cfg.keys()))

    if not canonical_mode and not legacy_mode:
        missing_top = sorted(REQUIRED_TOP_LEVEL - set(cfg.keys()))
        missing_legacy = sorted(LEGACY_REQUIRED_TOP_LEVEL - set(cfg.keys()))
        row.errors.append(
            "Unsupported schema. "
            f"Missing canonical keys: {', '.join(missing_top)}; "
            f"missing legacy keys: {', '.join(missing_legacy)}"
        )
        return row

    biology = cfg.get("biology")
    if not isinstance(biology, dict):
        row.errors.append("biology must be a mapping.")
        return row

    if canonical_mode:
        if not isinstance(cfg.get("input_files"), dict):
            row.errors.append("input_files must be a mapping.")

        missing_bio = sorted(REQUIRED_BIOLOGY - set(biology.keys()))
        if missing_bio:
            row.errors.append(f"Missing biology keys: {', '.join(missing_bio)}")

        kg = cfg.get("kg")
        if not isinstance(kg, dict):
            row.errors.append("kg must be a mapping.")
        else:
            missing_kg = sorted(REQUIRED_KG - set(kg.keys()))
            if missing_kg:
                row.errors.append(f"Missing kg keys: {', '.join(missing_kg)}")
    else:
        disease_map = cfg.get("disease")
        if not isinstance(disease_map, dict):
            row.errors.append("legacy disease must be a mapping.")
        else:
            missing_disease = sorted(LEGACY_REQUIRED_DISEASE - set(disease_map.keys()))
            if missing_disease:
                row.errors.append(f"Missing legacy disease keys: {', '.join(missing_disease)}")

        missing_bio = sorted(LEGACY_REQUIRED_BIOLOGY - set(biology.keys()))
        if missing_bio:
            row.errors.append(f"Missing legacy biology keys: {', '.join(missing_bio)}")

        if not isinstance(paths, dict):
            row.errors.append("legacy paths must be a mapping.")
        else:
            missing_paths = sorted(LEGACY_REQUIRED_PATHS - set(paths.keys()))
            if missing_paths:
                row.errors.append(f"Missing legacy paths keys: {', '.join(missing_paths)}")

        if not row.status:
            row.status = "legacy_schema_compatible"

    if disease == "BRCA" and canonical_mode:
        if cfg.get("s3_release_prefix") == "TODO_UNCONFIRMED":
            row.errors.append("BRCA s3_release_prefix must not be TODO_UNCONFIRMED.")
        if cfg.get("status") != "verified_brca_pipeline":
            row.errors.append("BRCA status should be verified_brca_pipeline.")
    elif canonical_mode:
        input_files = cfg.get("input_files", {})
        if isinstance(input_files, dict):
            todo_keys = [
                key
                for key, value in input_files.items()
                if isinstance(value, str) and "TODO_UNCONFIRMED" in value
            ]
            if todo_keys:
                row.warnings.append(
                    "TODO_UNCONFIRMED input_files placeholders present: " + ", ".join(sorted(todo_keys))
                )

    return row


def main() -> int:
    root = find_project_root()
    config_dir = root / "configs" / "diseases"
    out_dir = root / "outputs" / "config_validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(config_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"[error] no disease yaml files found under {config_dir}")
        return 1

    rows: list[ValidationRow] = []
    has_errors = False
    for path in yaml_files:
        try:
            row = validate_one(path)
        except Exception as exc:  # noqa: BLE001
            row = ValidationRow(
                disease=path.stem.upper(),
                run_id="",
                status="",
                s3_parent_prefix="",
                s3_release_prefix="",
                errors=[f"failed to parse {path.name}: {exc}"],
            )
        if row.errors:
            has_errors = True
        rows.append(row)

    report = {
        "generated_at": now_iso(),
        "config_dir": str(config_dir),
        "total_files": len(rows),
        "error_count": sum(1 for row in rows if row.errors),
        "warning_count": sum(len(row.warnings) for row in rows),
        "items": [
            {
                "disease": row.disease,
                "run_id": row.run_id,
                "status": row.status,
                "s3_parent_prefix": row.s3_parent_prefix,
                "s3_release_prefix": row.s3_release_prefix,
                "warnings": row.warnings,
                "errors": row.errors,
            }
            for row in rows
        ],
    }

    report_path = out_dir / "disease_config_validation_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("disease | run_id | status | s3_parent_prefix | s3_release_prefix | warnings")
    for row in rows:
        warn = "; ".join(row.warnings) if row.warnings else "-"
        print(
            f"{row.disease} | {row.run_id} | {row.status} | "
            f"{row.s3_parent_prefix} | {row.s3_release_prefix} | {warn}"
        )

    if has_errors:
        print(f"[error] validation failed. report: {report_path}")
        return 1
    print(f"[ok] validation passed. report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
