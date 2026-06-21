from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/alphafold", tags=["alphafold"])

EC2_ALPHAFOLD_ROOT = Path("/home/ec2-user/drug-project/analysis/alphafold_gene_pdb")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ALPHAFOLD_ROOT = PROJECT_ROOT / "analysis" / "alphafold_gene_pdb"

UNIPROT_ID_RE = re.compile(r"^[A-Za-z0-9]+$")
AF_PDB_FILE_RE = re.compile(r"^AF-(?P<uniprot_id>[A-Za-z0-9]+)-F[^-]*-model_.*\.pdb$", re.IGNORECASE)


def _resolve_alphafold_root() -> Path:
    for base in (EC2_ALPHAFOLD_ROOT, LOCAL_ALPHAFOLD_ROOT):
        try:
            resolved = base.resolve()
        except Exception:
            continue
        if resolved.exists() and resolved.is_dir():
            return resolved
    return EC2_ALPHAFOLD_ROOT


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def _iter_alphafold_files(base_dir: Path) -> list[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []

    files: list[Path] = []
    for candidate in base_dir.rglob("AF-*.pdb"):
        if not candidate.is_file():
            continue
        if not _is_within(base_dir, candidate):
            continue
        if AF_PDB_FILE_RE.match(candidate.name) is None:
            continue
        files.append(candidate.resolve())
    return sorted(files, key=lambda p: p.name.lower())


def _extract_uniprot_id(file_name: str) -> str | None:
    match = AF_PDB_FILE_RE.match(file_name)
    if match is None:
        return None
    return str(match.group("uniprot_id")).upper()


@router.get("/structures")
def list_structures() -> dict[str, Any]:
    base_dir = _resolve_alphafold_root()
    items: list[dict[str, str]] = []

    for pdb_file in _iter_alphafold_files(base_dir):
        uniprot_id = _extract_uniprot_id(pdb_file.name)
        if not uniprot_id:
            continue
        items.append(
            {
                "id": pdb_file.stem,
                "uniprot_id": uniprot_id,
                "file_name": pdb_file.name,
                "source": "local_alphafold_file",
                "url": f"/api/alphafold/structures/{uniprot_id}/file",
            }
        )

    return {"count": len(items), "items": items}


@router.get("/structures/{uniprot_id}/file")
def get_structure_file(uniprot_id: str) -> FileResponse:
    normalized = (uniprot_id or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="uniprot_id is required.")
    if UNIPROT_ID_RE.match(normalized) is None:
        raise HTTPException(status_code=400, detail="Invalid uniprot_id format.")

    base_dir = _resolve_alphafold_root()
    if not base_dir.exists() or not base_dir.is_dir():
        raise HTTPException(status_code=404, detail="AlphaFold structure directory not found.")

    pattern = f"AF-{normalized}-F*-model_*.pdb"
    matched: list[Path] = []
    for candidate in base_dir.rglob(pattern):
        if not candidate.is_file():
            continue
        if not _is_within(base_dir, candidate):
            continue
        if AF_PDB_FILE_RE.match(candidate.name) is None:
            continue
        matched.append(candidate.resolve())

    if not matched:
        raise HTTPException(status_code=404, detail="AlphaFold structure file not found.")

    selected = sorted(matched, key=lambda p: p.name.lower())[0]
    return FileResponse(path=selected, media_type="chemical/x-pdb", filename=selected.name)
