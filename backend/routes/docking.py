from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path, PurePath
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.core.disease_aliases import normalize_disease

router = APIRouter(prefix="/api/docking", tags=["docking"])

CANONICAL_PROJECT_ROOT = Path(r"C:\work\drug-project")
if (CANONICAL_PROJECT_ROOT / "backend").exists() and (CANONICAL_PROJECT_ROOT / "analysis").exists():
    PROJECT_ROOT = CANONICAL_PROJECT_ROOT
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENE_PDB_ROOT = PROJECT_ROOT / "analysis" / "alphafold_gene_pdb"
KNOWN_EXTS = {".pdb", ".sdf", ".mol", ".mol2", ".pdbqt", ".csv", ".json", ".txt", ".md"}


class DockingPreviewRequest(BaseModel):
    drug_name: Optional[str] = Field(default=None)
    smiles: str
    target_gene: str


class DockingSmilesPreflightRequest(BaseModel):
    drug_name: Optional[str] = Field(default=None)
    smiles: str
    target_gene: str


PREFLIGHT_NEXT_STEPS = [
    "ligand_3d_generation",
    "receptor_preparation",
    "docking_box_definition",
    "vina_execution",
    "pose_result_export",
]


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _coerce_existing_path(path_text: str | None, base_dir: Path) -> Path | None:
    value = str(path_text or "").strip()
    if not value:
        return None

    candidates: list[Path] = []
    raw = Path(value)
    candidates.append(raw)
    candidates.append(base_dir / value)
    candidates.append(PROJECT_ROOT / value)

    normalized = value.replace("\\", "/")
    marker = normalized.lower().find("analysis/")
    if marker >= 0:
        tail = normalized[marker:]
        candidates.append(PROJECT_ROOT / tail)

    for cand in candidates:
        try:
            resolved = cand.resolve()
        except Exception:
            continue
        if resolved.exists() and _is_within(PROJECT_ROOT, resolved):
            return resolved
    return None


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as fp:
        reader = csv.DictReader(fp)
        return [{k: (v or "") for k, v in row.items()} for row in reader]


def _candidate_manifest_dirs(canonical: str) -> list[Path]:
    key = canonical.lower()
    base = PROJECT_ROOT / "analysis"
    names = [
        f"alphafold_topn_{key}_full_v2",
        f"alphafold_topn_{key}_20260426",
        f"alphafold_topn_{key}_full",
        f"alphafold_topn_{key}",
        f"alphafold_topn_{key}_uniprot",
    ]
    return [base / name for name in names if (base / name).exists()]


def _discover_manifest_files(manifest_dir: Path) -> tuple[Path | None, Path | None]:
    summary = manifest_dir / "run_summary.json"
    final_csv: Path | None = None
    model_csv: Path | None = None

    if summary.exists():
        try:
            payload = json.loads(summary.read_text(encoding="utf-8", errors="ignore"))
            outputs = payload.get("outputs", {}) if isinstance(payload, dict) else {}
            if isinstance(outputs, dict):
                final_csv = _coerce_existing_path(outputs.get("final_top_candidates_with_sites_csv"), manifest_dir)
                model_csv = _coerce_existing_path(outputs.get("alphafold_models_csv"), manifest_dir)
        except Exception:
            pass

    if final_csv is None:
        fallback = manifest_dir / "final_top_candidates_with_sites.csv"
        final_csv = fallback.resolve() if fallback.exists() else None
    if model_csv is None:
        fallback = manifest_dir / "alphafold_models.csv"
        model_csv = fallback.resolve() if fallback.exists() else None

    return final_csv, model_csv


def _row_targets(row: dict[str, str]) -> set[str]:
    keys = ("target_gene_symbol", "target_source_token", "target_raw")
    out: set[str] = set()
    for key in keys:
        value = str(row.get(key, "")).strip().upper()
        if value and value != "NAN":
            out.add(value)
    return out


def _find_best_row(rows: list[dict[str, str]], target_gene: str, drug_name: str | None) -> dict[str, str] | None:
    gene_key = target_gene.strip().upper()
    drug_key = (drug_name or "").strip().upper()
    candidates: list[dict[str, str]] = []
    for row in rows:
        if gene_key not in _row_targets(row):
            continue
        candidates.append(row)
    if not candidates:
        return None
    if not drug_key:
        return candidates[0]
    for row in candidates:
        if str(row.get("drug_name", "")).strip().upper() == drug_key:
            return row
    return None


def _score_from_row(row: dict[str, str]) -> float | None:
    score_cols = (
        "docking_score",
        "vina_score",
        "binding_affinity",
        "affinity_kcal_mol",
        "score",
    )
    for col in score_cols:
        value = str(row.get(col, "")).strip()
        if not value:
            continue
        try:
            return float(value)
        except ValueError:
            continue
    return None


@lru_cache(maxsize=32)
def _load_disease_index(canonical: str) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    allowed_roots: set[Path] = set()

    for manifest_dir in _candidate_manifest_dirs(canonical):
        final_csv, model_csv = _discover_manifest_files(manifest_dir)
        if final_csv is None:
            continue
        rows = _load_csv_rows(final_csv)
        model_rows = _load_csv_rows(model_csv) if model_csv and model_csv.exists() else []

        model_by_uniprot: dict[str, dict[str, str]] = {}
        for row in model_rows:
            uid = str(row.get("uniprot_id", "")).strip().upper()
            if uid:
                model_by_uniprot[uid] = row

        allowed_roots.add(manifest_dir.resolve())
        structures_dir = (manifest_dir / "structures").resolve()
        if structures_dir.exists():
            allowed_roots.add(structures_dir)
        if final_csv.parent.exists():
            allowed_roots.add(final_csv.parent.resolve())

        manifests.append(
            {
                "manifest_dir": manifest_dir.resolve(),
                "final_csv": final_csv.resolve(),
                "rows": rows,
                "model_by_uniprot": model_by_uniprot,
            }
        )

    return {
        "disease": canonical,
        "manifests": manifests,
        "allowed_roots": sorted(allowed_roots, key=lambda p: str(p)),
    }


def _asset_url(canonical: str, file_path: Path) -> str | None:
    if not _is_within(PROJECT_ROOT, file_path):
        return None
    rel = file_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    return f"/api/docking/assets/{canonical}/{rel}"


@lru_cache(maxsize=1)
def _load_gene_pdb_manifest() -> dict[str, Any]:
    manifest_path = GENE_PDB_ROOT / "gene_pdb_manifest.json"
    if not manifest_path.exists():
        return {"generated_at": "", "rows": []}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {"generated_at": "", "rows": []}
    if isinstance(payload, dict):
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []
        return {"generated_at": str(payload.get("generated_at", "")), "rows": rows}
    if isinstance(payload, list):
        return {"generated_at": "", "rows": payload}
    return {"generated_at": "", "rows": []}


def _gene_manifest_rows_for_disease(canonical: str) -> list[dict[str, Any]]:
    data = _load_gene_pdb_manifest()
    out: list[dict[str, Any]] = []
    for row in data.get("rows", []):
        disease = str(row.get("disease", "")).strip().upper()
        if disease != canonical:
            continue
        out.append(row)
    out.sort(key=lambda x: str(x.get("gene", "")).upper())
    return out


def _serialize_gene_row(canonical: str, row: dict[str, Any]) -> dict[str, Any]:
    local_path = str(row.get("local_path", "")).strip()
    gene = str(row.get("gene", "")).strip().upper()
    filename = str(row.get("alphafold_id", "")).strip()
    asset_url = ""
    if local_path and filename:
        asset_url = f"/api/docking/assets/gene-pdb/{canonical}/{gene}/{filename}"
    warnings = row.get("warnings", [])
    if isinstance(warnings, str):
        warnings = [warnings] if warnings else []
    if not isinstance(warnings, list):
        warnings = []
    return {
        "disease": canonical,
        "gene": gene,
        "uniprot_id": str(row.get("uniprot_id", "")).strip(),
        "alphafold_id": filename,
        "local_path": local_path,
        "structure_url": str(row.get("structure_url", "")).strip(),
        "available": bool(row.get("available", False)),
        "status": str(row.get("status", "")).strip(),
        "source": str(row.get("source", "")).strip(),
        "warnings": [str(x) for x in warnings],
        "asset_url": asset_url,
    }


def _lightweight_smiles_validate(smiles: str) -> bool:
    value = smiles.strip()
    if not value:
        return False
    blocked = {"INVALID", "INVALID_SMILES", "N/A", "NA", "NONE", "NULL", "-", "?"}
    if value.upper() in blocked:
        return False
    return True


def _validate_smiles(smiles: str) -> tuple[bool, list[str]]:
    try:
        from rdkit import Chem  # type: ignore
    except Exception:
        return _lightweight_smiles_validate(smiles), ["RDKit not installed; lightweight validation only"]

    try:
        mol = Chem.MolFromSmiles(smiles.strip())
    except Exception:
        return False, []
    return mol is not None, []


def _build_preflight_protein(canonical: str, target_gene: str, row: dict[str, Any] | None) -> dict[str, str]:
    gene = target_gene.strip().upper()
    if row is None:
        return {"gene": gene, "uniprot_id": "", "alphafold_id": "", "structure_url": ""}

    serialized = _serialize_gene_row(canonical, row)
    uniprot_id = str(row.get("uniprot_id", "")).strip()
    alphafold_id = str(row.get("alphafold_id", "")).strip()
    structure_url = str(serialized.get("asset_url", "")).strip()
    if not structure_url and uniprot_id and bool(row.get("available", False)) and alphafold_id:
        structure_url = f"/api/docking/assets/gene-pdb/{canonical}/{gene}/{alphafold_id}"
    return {
        "gene": gene,
        "uniprot_id": uniprot_id,
        "alphafold_id": alphafold_id.replace(".pdb", ""),
        "structure_url": structure_url,
    }


def _preflight_response(
    *,
    status: str,
    canonical: str,
    payload: DockingSmilesPreflightRequest,
    smiles_valid: bool,
    target_available: bool,
    protein: dict[str, str],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "disease": canonical,
        "drug_name": (payload.drug_name or "").strip(),
        "smiles": payload.smiles,
        "target_gene": payload.target_gene,
        "smiles_valid": smiles_valid,
        "target_available": target_available,
        "protein": protein,
        "docking": {
            "run_supported": False,
            "message": "SMILES docking execution is not implemented yet. This endpoint validates readiness only.",
        },
        "required_next_steps": list(PREFLIGHT_NEXT_STEPS),
        "warnings": warnings or [],
    }


def _empty_preview_response(canonical: str, payload: DockingPreviewRequest, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "NO_RESULT",
        "disease": canonical,
        "drug_name": payload.drug_name or "",
        "smiles": payload.smiles,
        "target_gene": payload.target_gene,
        "protein": {
            "source": "",
            "protein_id": "",
            "structure_url": "",
            "local_path": "",
        },
        "ligand": {
            "ligand_url": "",
            "local_path": "",
        },
        "docking": {
            "score": None,
            "unit": "kcal/mol",
            "method": "existing_result",
            "result_file": "",
        },
        "evidence": {},
        "warnings": warnings or [],
    }


@router.post("/{disease}/smiles/preflight")
def preflight_smiles_docking(disease: str, payload: DockingSmilesPreflightRequest) -> dict[str, Any]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    smiles = payload.smiles.strip()
    target_gene = payload.target_gene.strip().upper()
    if not smiles:
        raise HTTPException(status_code=400, detail="smiles is required.")
    if not target_gene:
        raise HTTPException(status_code=400, detail="target_gene is required.")

    smiles_valid, warnings = _validate_smiles(smiles)
    payload = DockingSmilesPreflightRequest(
        drug_name=payload.drug_name,
        smiles=smiles,
        target_gene=target_gene,
    )

    rows = _gene_manifest_rows_for_disease(canonical)
    row = next((x for x in rows if str(x.get("gene", "")).strip().upper() == target_gene), None)

    if not smiles_valid:
        protein = _build_preflight_protein(canonical, target_gene, row)
        target_available = bool(row and row.get("available", False) and protein.get("structure_url"))
        return _preflight_response(
            status="INVALID_SMILES",
            canonical=canonical,
            payload=payload,
            smiles_valid=False,
            target_available=target_available,
            protein=protein,
            warnings=warnings,
        )

    if row is None:
        return _preflight_response(
            status="TARGET_NOT_IN_DISEASE",
            canonical=canonical,
            payload=payload,
            smiles_valid=True,
            target_available=False,
            protein=_build_preflight_protein(canonical, target_gene, None),
            warnings=warnings,
        )

    protein = _build_preflight_protein(canonical, target_gene, row)
    target_available = bool(row.get("available", False)) and bool(protein.get("structure_url"))
    if not target_available:
        return _preflight_response(
            status="TARGET_PDB_MISSING",
            canonical=canonical,
            payload=payload,
            smiles_valid=True,
            target_available=False,
            protein=protein,
            warnings=warnings,
        )

    return _preflight_response(
        status="READY_FOR_DOCKING",
        canonical=canonical,
        payload=payload,
        smiles_valid=True,
        target_available=True,
        protein=protein,
        warnings=warnings,
    )


@router.post("/{disease}/preview")
def preview_existing_docking_result(disease: str, payload: DockingPreviewRequest) -> dict[str, Any]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.smiles.strip():
        raise HTTPException(status_code=400, detail="smiles is required.")
    if not payload.target_gene.strip():
        raise HTTPException(status_code=400, detail="target_gene is required.")

    index = _load_disease_index(canonical)
    manifests = index["manifests"]

    if not manifests:
        return _empty_preview_response(
            canonical,
            payload,
            warnings=["No AlphaFold/docking discovery artifacts found for this disease."],
        )

    matched: tuple[dict[str, Any], dict[str, str]] | None = None
    for manifest in manifests:
        row = _find_best_row(manifest["rows"], payload.target_gene, payload.drug_name)
        if row is not None:
            matched = (manifest, row)
            break

    if matched is None:
        return _empty_preview_response(canonical, payload, warnings=["No existing docking result found for the given query."])

    manifest, row = matched
    warnings: list[str] = []
    uniprot_id = str(row.get("uniprot_id", "")).strip()

    structure_path = _coerce_existing_path(row.get("alphafold_pdb_path"), manifest["manifest_dir"])
    if structure_path is None and uniprot_id:
        model_row = manifest["model_by_uniprot"].get(uniprot_id.upper())
        if model_row:
            structure_path = _coerce_existing_path(model_row.get("alphafold_pdb_path"), manifest["manifest_dir"])

    structure_url = _asset_url(canonical, structure_path) if structure_path else ""
    if structure_path is None:
        warnings.append("Protein structure file was not found in allowed local result directories.")

    score = _score_from_row(row)
    if score is None:
        warnings.append("Docking score is not present in the discovered existing result files.")

    result_file = str(manifest["final_csv"])
    status = "PASS_WITH_WARNINGS" if warnings else "PASS"

    return {
        "status": status,
        "disease": canonical,
        "drug_name": str(row.get("drug_name") or payload.drug_name or "").strip(),
        "smiles": payload.smiles,
        "target_gene": payload.target_gene,
        "protein": {
            "source": "alphafold_topn_pipeline",
            "protein_id": uniprot_id,
            "structure_url": structure_url,
            "local_path": str(structure_path) if structure_path else "",
        },
        "ligand": {
            "ligand_url": "",
            "local_path": "",
        },
        "docking": {
            "score": score,
            "unit": "kcal/mol",
            "method": "existing_result",
            "result_file": result_file,
        },
        "evidence": {
            "manifest_dir": str(manifest["manifest_dir"]),
            "matched_row": {
                "rank": row.get("rank", ""),
                "drug_name": row.get("drug_name", ""),
                "target_gene_symbol": row.get("target_gene_symbol", ""),
                "uniprot_id": row.get("uniprot_id", ""),
            },
        },
        "warnings": warnings,
    }


@router.get("/{disease}/gene-pdb")
def list_gene_pdb_by_disease(disease: str) -> dict[str, Any]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    manifest = _load_gene_pdb_manifest()
    rows = _gene_manifest_rows_for_disease(canonical)
    serialized = [_serialize_gene_row(canonical, row) for row in rows]
    return {
        "disease": canonical,
        "generated_at": manifest.get("generated_at", ""),
        "count": len(serialized),
        "rows": serialized,
    }


@router.get("/{disease}/gene-pdb/{gene}")
def get_gene_pdb_by_gene(disease: str, gene: str) -> dict[str, Any]:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    gene_key = gene.strip().upper()
    if not gene_key:
        raise HTTPException(status_code=400, detail="gene is required.")

    rows = _gene_manifest_rows_for_disease(canonical)
    for row in rows:
        if str(row.get("gene", "")).strip().upper() == gene_key:
            return _serialize_gene_row(canonical, row)
    raise HTTPException(status_code=404, detail="Gene PDB metadata not found.")


@router.get("/assets/gene-pdb/{disease}/{gene}/{filename}")
def get_gene_pdb_asset(disease: str, gene: str, filename: str) -> FileResponse:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    gene_key = gene.strip().upper()
    if not gene_key:
        raise HTTPException(status_code=400, detail="gene is required.")

    requested = PurePath(filename)
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute filename is not allowed.")
    if ".." in requested.parts:
        raise HTTPException(status_code=400, detail="Path traversal is not allowed.")
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in KNOWN_EXTS:
        raise HTTPException(status_code=404, detail="Unsupported asset extension.")

    base_dir = (GENE_PDB_ROOT / canonical / gene_key)
    candidate = (base_dir / filename).resolve()
    if not _is_within(GENE_PDB_ROOT, candidate):
        raise HTTPException(status_code=400, detail="Path traversal is not allowed.")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset file not found.")
    return FileResponse(path=candidate)


@router.get("/assets/{disease}/{path:path}")
def get_docking_asset(disease: str, path: str) -> FileResponse:
    try:
        canonical = normalize_disease(disease)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    requested = PurePath(path)
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed.")
    if ".." in requested.parts:
        raise HTTPException(status_code=400, detail="Path traversal is not allowed.")

    index = _load_disease_index(canonical)
    allowed_roots: list[Path] = index["allowed_roots"]
    if not allowed_roots:
        raise HTTPException(status_code=404, detail="No allowed docking result directories are registered for this disease.")

    requested_path = Path(path)
    if requested_path.suffix and requested_path.suffix.lower() not in KNOWN_EXTS:
        raise HTTPException(status_code=404, detail="Unsupported asset extension.")

    candidate = (PROJECT_ROOT / requested_path).resolve()
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset file not found.")

    for root in allowed_roots:
        if _is_within(root, candidate):
            return FileResponse(path=candidate)

    raise HTTPException(status_code=404, detail="Asset file not found.")
