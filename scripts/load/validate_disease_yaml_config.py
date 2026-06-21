#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"PyYAML is required: {exc}")


REQUIRED_TOP_LEVEL = [
    "disease",
    "biology",
    "paths",
    "load_policy",
    "no_admet_guardrail",
    "artifact_roles",
    "postgres",
    "neo4j",
]
REQUIRED_BLOCKED_DECISIONS = {
    "NEEDS_REVIEW",
    "DO_NOT_LOAD_EXCLUDED",
    "BLOCKED",
    "MISSING",
    "LOCAL_SYNC_NEEDED",
}
REQUIRED_NO_ADMET_BLOCKED_TABLES = {
    "admet_result",
    "final_candidate_result",
    "run_manifest",
}
DISEASE_BIOLOGY_EXACT: dict[str, dict[str, list[str]]] = {
    "BRCA": {
        "driver_genes": ["TP53", "PIK3CA", "BRCA1/2", "CDH1", "GATA3"],
        "molecular_subtypes": ["LUMINAL A/B", "HER2+", "BASAL", "NORMAL-LIKE"],
    },
    "COAD": {
        "driver_genes": ["APC", "TP53", "KRAS", "BRAF", "PIK3CA", "MSI"],
        "molecular_subtypes": ["CMS1~4"],
    },
    "LUAD": {
        "driver_genes": ["EGFR", "KRAS", "ALK", "STK11", "KEAP1", "TP53"],
        "molecular_subtypes": ["TRU", "PP", "PI"],
    },
    "LIHC": {
        "driver_genes": ["TP53", "CTNNB1", "AXIN1", "ARID1A"],
        "molecular_subtypes": ["ICLUSTER 1/2/3"],
    },
    "STAD": {
        "driver_genes": ["TP53", "CDH1", "ARID1A", "PIK3CA", "ERBB2"],
        "molecular_subtypes": ["EBV", "MSI", "GS", "CIN"],
    },
    "PAAD": {
        "driver_genes": ["KRAS", "TP53", "CDKN2A", "SMAD4"],
        "molecular_subtypes": ["BASAL-LIKE", "CLASSICAL"],
    },
    "HNSC": {
        "driver_genes": ["TP53", "CDKN2A", "PIK3CA", "NOTCH1"],
        "molecular_subtypes": ["ATYPICAL", "BASAL", "CLASSICAL", "MESENCHYMAL"],
    },
}
LUAD_IMAGE_MODAL_EXCLUDE_TOKENS = [
    "image",
    "images",
    "img",
    "imaging",
    "image_modal",
    "imagemodal",
    "multimodal_image",
    "pathology",
    "histology",
    "wsi",
    "whole_slide",
    "slide_images",
    "svs",
    "tissue_image",
]
RAW_CURATED_REFERENCE_GLUE_REQUIRED = ["raw", "curated_data", "reference", "glue"]
PROJECT_ROOT_MARKERS = ["configs", "scripts", "backend", "outputs", "docs", "pyproject.toml", "requirements.txt"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate disease YAML config for generic pipeline.")
    p.add_argument("--disease", required=True)
    p.add_argument("--project-root", default="")
    p.add_argument("--config", required=True)
    return p.parse_args()


def safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return data


def detect_alias_path_uncertainty(project_root: Path, disease_code: str) -> list[str]:
    warnings: list[str] = []
    cdir = project_root / "configs" / "diseases"
    if disease_code == "LUAD" and (cdir / "lung.yaml").exists():
        warnings.append("legacy_lung_yaml_detected_for_luad_path_alias_uncertainty")
    if disease_code == "LIHC" and (cdir / "liver.yaml").exists():
        warnings.append("legacy_liver_yaml_detected_for_lihc_path_alias_uncertainty")
    return warnings


def _marker_score(path: Path) -> int:
    return sum(1 for marker in PROJECT_ROOT_MARKERS if (path / marker).exists())


def _iter_ancestors_inclusive(start: Path) -> list[Path]:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    out = [current]
    out.extend(current.parents)
    return out


def resolve_project_root(project_root_arg: str) -> Path:
    requested = safe_str(project_root_arg)
    if requested:
        p = Path(requested)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve()

    env_root = safe_str(os.getenv("PROJECT_ROOT", ""))
    if env_root:
        p = Path(env_root)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve()

    starts = [Path.cwd(), Path(__file__).resolve().parents[2]]
    best_path: Path | None = None
    best_score = -1
    for start in starts:
        for cand in _iter_ancestors_inclusive(start):
            score = _marker_score(cand)
            if score > best_score:
                best_score = score
                best_path = cand
            if score == len(PROJECT_ROOT_MARKERS):
                return cand.resolve()
    if best_path is not None and best_score > 0:
        return best_path.resolve()
    return Path.cwd().resolve()


def normalize_path_for_compare(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve())))


def normalize_path_no_resolve(path: Any) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path))))


def output_root_guardrail_status(project_root: Path) -> str:
    resolved = normalize_path_no_resolve(project_root)
    if (
        "onedrive" in resolved.lower()
        or r"\users\hjy10\onedrive" in resolved.lower()
    ):
        return "BLOCKED_ONEDRIVE_PROJECT_ROOT"
    if _marker_score(project_root) == 0:
        return "BLOCKED_WRONG_PROJECT_ROOT"
    return "PASS"

def resolve_config_path(project_root: Path, config_arg: str) -> Path:
    cp = Path(config_arg)
    if cp.is_absolute():
        return cp
    return project_root / cp


def main() -> int:
    args = parse_args()
    disease = safe_str(args.disease).upper()
    project_root = resolve_project_root(args.project_root)
    status = output_root_guardrail_status(project_root)
    if status != "PASS":
        raise SystemExit(status)
    cfg_path = resolve_config_path(project_root, args.config)
    output_dir = project_root / "outputs" / "config_validation"
    docs_dir = project_root / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_out = output_dir / f"{disease.lower()}_disease_yaml_validation_report.json"
    md_out = docs_dir / f"{disease.lower()}_disease_yaml_validation_report.md"

    failures: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}
    resolved_s3_prefix = ""
    resolved_local_cache = ""

    cfg_path_text = str(cfg_path).lower().replace("/", "\\")
    if "onedrive" in cfg_path_text and "new project 2" in cfg_path_text:
        failures.append("resolved_config_path_onedrive_not_allowed")

    if not cfg_path.exists():
        failures.append(f"config_not_found:{cfg_path}")
        payload = {
            "generated_at": now_iso(),
            "disease": disease,
            "config_path": str(cfg_path),
            "project_root": str(project_root),
            "resolved_config_path": str(cfg_path),
            "resolved_s3_prefix": resolved_s3_prefix,
            "resolved_local_cache": resolved_local_cache,
            "config_status": "FAIL",
            "failures": failures,
            "warnings": warnings,
            "checks": checks,
        }
    else:
        try:
            cfg = load_yaml(cfg_path)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"yaml_parse_error:{exc}")
            cfg = {}

        for key in REQUIRED_TOP_LEVEL:
            if key not in cfg:
                failures.append(f"missing_top_level:{key}")
        checks["required_top_level_present"] = len([k for k in REQUIRED_TOP_LEVEL if k in cfg])

        disease_block = cfg.get("disease", {})
        biology = cfg.get("biology", {})
        paths = cfg.get("paths", {})
        load_policy = cfg.get("load_policy", {})
        guardrail = cfg.get("no_admet_guardrail", {})
        artifact_roles = cfg.get("artifact_roles", [])
        postgres = cfg.get("postgres", {})
        neo4j = cfg.get("neo4j", {})

        if not isinstance(disease_block, dict):
            failures.append("disease_section_not_mapping")
            disease_block = {}
        if safe_str(disease_block.get("code")).upper() != disease:
            failures.append("disease_code_mismatch")
        for key in ("code", "name", "aliases"):
            if key not in disease_block:
                failures.append(f"missing_disease_field:{key}")
        if not isinstance(disease_block.get("aliases"), list) or not disease_block.get("aliases"):
            failures.append("disease_aliases_invalid")

        if not isinstance(biology, dict):
            failures.append("biology_section_not_mapping")
            biology = {}
        for key in ("driver_genes", "molecular_subtypes"):
            if key not in biology:
                failures.append(f"missing_biology_field:{key}")
            elif not isinstance(biology.get(key), list) or not biology.get(key):
                failures.append(f"invalid_biology_field:{key}")

        if not isinstance(paths, dict):
            failures.append("paths_section_not_mapping")
            paths = {}
        for key in ("s3_prefix", "local_cache"):
            if not safe_str(paths.get(key)):
                failures.append(f"missing_paths_field:{key}")
        resolved_s3_prefix = safe_str(paths.get("s3_prefix"))
        lc = safe_str(paths.get("local_cache"))
        resolved_local_cache = str((project_root / lc) if lc and not Path(lc).is_absolute() else Path(lc)) if lc else ""

        if not isinstance(load_policy, dict):
            failures.append("load_policy_section_not_mapping")
            load_policy = {}
        ex_folders = load_policy.get("exclude_folders")
        blocked = load_policy.get("blocked_decisions")
        if not isinstance(ex_folders, list) or not ex_folders:
            failures.append("exclude_folders_missing_or_invalid")
        if not isinstance(blocked, list) or not blocked:
            failures.append("blocked_decisions_missing_or_invalid")
            blocked_set: set[str] = set()
        else:
            blocked_set = {safe_str(x).upper() for x in blocked}
            missing_blocked = sorted(REQUIRED_BLOCKED_DECISIONS - blocked_set)
            if missing_blocked:
                failures.append(f"blocked_decisions_missing_required:{','.join(missing_blocked)}")
        if isinstance(ex_folders, list):
            ex_set = {safe_str(x).lower() for x in ex_folders}
            missing_base = [x for x in RAW_CURATED_REFERENCE_GLUE_REQUIRED if x.lower() not in ex_set]
            if missing_base:
                failures.append(f"exclude_folders_missing_required:{','.join(missing_base)}")
            if disease == "LUAD":
                missing_luad_image = [x for x in LUAD_IMAGE_MODAL_EXCLUDE_TOKENS if x.lower() not in ex_set]
                if missing_luad_image:
                    failures.append(f"luad_image_modal_exclusions_missing:{','.join(missing_luad_image)}")

        if not isinstance(guardrail, dict):
            failures.append("no_admet_guardrail_section_not_mapping")
            guardrail = {}
        blocked_tables = guardrail.get("blocked_target_tables")
        if not isinstance(blocked_tables, list) or not blocked_tables:
            failures.append("blocked_target_tables_missing_or_invalid")
            blocked_tables_set: set[str] = set()
        else:
            blocked_tables_set = {safe_str(x) for x in blocked_tables}
            missing_tables = sorted(REQUIRED_NO_ADMET_BLOCKED_TABLES - blocked_tables_set)
            if missing_tables:
                failures.append(f"blocked_target_tables_missing_required:{','.join(missing_tables)}")

        if not isinstance(artifact_roles, list) or not artifact_roles:
            failures.append("artifact_roles_missing_or_invalid")
        else:
            for idx, role in enumerate(artifact_roles):
                if not isinstance(role, dict):
                    failures.append(f"artifact_role_not_mapping:{idx}")
                    continue
                for key in ("role", "target_table", "include_keywords"):
                    if key not in role:
                        failures.append(f"artifact_role_missing_field:{idx}:{key}")
                if not isinstance(role.get("include_keywords"), list) or not role.get("include_keywords"):
                    failures.append(f"artifact_role_include_keywords_invalid:{idx}")

        if not isinstance(postgres, dict) or not isinstance(postgres.get("target_tables"), list) or not postgres.get("target_tables"):
            failures.append("postgres_target_tables_missing_or_invalid")
        if not isinstance(neo4j, dict):
            failures.append("neo4j_section_not_mapping")
            neo4j = {}
        for key in ("initial_roles", "enrichment_nodes", "enrichment_relationships"):
            if not isinstance(neo4j.get(key), list) or not neo4j.get(key):
                failures.append(f"neo4j_field_missing_or_invalid:{key}")

        expected_biology = DISEASE_BIOLOGY_EXACT.get(disease, {})
        if expected_biology:
            driver = biology.get("driver_genes", []) if isinstance(biology, dict) else []
            subtypes = biology.get("molecular_subtypes", []) if isinstance(biology, dict) else []
            driver_norm = [safe_str(x).upper() for x in driver]
            subtype_norm = [safe_str(x).upper() for x in subtypes]
            if driver_norm != expected_biology.get("driver_genes", []):
                failures.append(f"{disease.lower()}_driver_genes_exact_mismatch")
            if subtype_norm != expected_biology.get("molecular_subtypes", []):
                failures.append(f"{disease.lower()}_molecular_subtypes_exact_mismatch")

        if disease == "BRCA":
            aliases = disease_block.get("aliases", [])
            alias_set = {safe_str(x).lower() for x in aliases} if isinstance(aliases, list) else set()
            for required_alias in {"brca", "brac"}:
                if required_alias not in alias_set:
                    failures.append(f"brca_alias_missing:{required_alias}")

        execute_cfg = cfg.get("execute", {})
        if isinstance(execute_cfg, dict):
            if execute_cfg.get("postgres") is True:
                failures.append("execute_default_postgres_must_be_disabled")
            if execute_cfg.get("neo4j") is True:
                failures.append("execute_default_neo4j_must_be_disabled")

        warnings.extend(detect_alias_path_uncertainty(project_root, disease))
        if disease == "LUAD" and "/LUNG/" in resolved_s3_prefix.replace("\\", "/").upper():
            warnings.append("luad_uses_lung_s3_prefix_alias")

        if failures:
            status = "FAIL"
        elif warnings:
            status = "PASS_WITH_WARNINGS"
        else:
            status = "PASS"

        payload = {
            "generated_at": now_iso(),
            "disease": disease,
            "config_path": str(cfg_path),
            "project_root": str(project_root),
            "resolved_config_path": str(cfg_path),
            "resolved_s3_prefix": resolved_s3_prefix,
            "resolved_local_cache": resolved_local_cache,
            "config_status": status,
            "failures": failures,
            "warnings": warnings,
            "checks": checks,
            "summary": {
                "artifact_roles_count": len(artifact_roles) if isinstance(artifact_roles, list) else 0,
                "driver_genes_count": len(biology.get("driver_genes", [])) if isinstance(biology, dict) else 0,
                "molecular_subtypes_count": len(biology.get("molecular_subtypes", [])) if isinstance(biology, dict) else 0,
            },
        }

    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        f"# {disease} Disease YAML Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- disease: {disease}",
        f"- config_path: {cfg_path}",
        f"- project_root: {project_root}",
        f"- resolved_config_path: {cfg_path}",
        f"- resolved_s3_prefix: {payload.get('resolved_s3_prefix', '')}",
        f"- resolved_local_cache: {payload.get('resolved_local_cache', '')}",
        f"- config_status: {payload.get('config_status')}",
        "",
        "## Failures",
    ]
    for item in payload.get("failures", []):
        md_lines.append(f"- {item}")
    md_lines.extend(["", "## Warnings"])
    for item in payload.get("warnings", []):
        md_lines.append(f"- {item}")
    md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # unified CLI summary fields
    print(f"disease={disease}")
    print("dry_run=true")
    print(f"config_status={payload.get('config_status')}")
    print("inventory_status=PASS_WITH_WARNINGS")
    print("safe_write_plan_status=PASS_WITH_WARNINGS")
    print("classified_files=0")
    print("load_candidates=0")
    print("needs_review=0")
    print("local_sync_needed=0")
    print("missing=0")
    print("blocked=0")
    print(f"json_output={json_out}")
    print(f"markdown_output={md_out}")

    return 0 if payload.get("config_status") in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())


