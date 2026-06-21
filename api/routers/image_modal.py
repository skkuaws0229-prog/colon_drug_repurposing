from __future__ import annotations

import os
from functools import lru_cache
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query

from api.core.disease_aliases import get_disease_query_values, normalize_disease_code
from api.db.neo4j import get_neo4j_driver
from api.core.config import get_settings


router = APIRouter(prefix="/api", tags=["image-modal"])


def _disease_match_clause(var_name: str = "d") -> str:
    return f"""
    any(alias IN $aliases WHERE
      toUpper(coalesce({var_name}.disease_code, '')) = alias OR
      toUpper(coalesce({var_name}.code, '')) = alias OR
      toUpper(coalesce({var_name}.name, '')) = alias OR
      toUpper(coalesce({var_name}.disease, '')) = alias
    )
    """


def _normalize_file_name(file_name: str) -> str:
    decoded = unquote((file_name or "").strip())
    if not decoded:
        raise HTTPException(status_code=400, detail="file_name is required.")
    if "/" in decoded or "\\" in decoded:
        raise HTTPException(status_code=400, detail="file_name must not include path separators.")
    return decoded


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    value = (s3_uri or "").strip()
    if not value.startswith("s3://"):
        raise ValueError("s3_uri must start with 's3://'.")
    remainder = value[5:]
    if not remainder or "/" not in remainder:
        raise ValueError("s3_uri must be in 's3://bucket/key' format.")
    bucket, key = remainder.split("/", 1)
    if not bucket.strip():
        raise ValueError("s3_uri bucket is empty.")
    if not key.strip() or key.strip() == "/":
        raise ValueError("s3_uri key is empty.")
    return bucket.strip(), key.strip()


@lru_cache(maxsize=1)
def _get_s3_client():
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="boto3 is not installed. Add 'boto3' to requirements and install dependencies.",
        ) from exc

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
    if region:
        return boto3.client("s3", region_name=region)
    return boto3.client("s3")


def _build_presigned_url(s3_uri: str, expires_in: int) -> str:
    bucket, key = _parse_s3_uri(s3_uri)
    try:
        return _get_s3_client().generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {exc.__class__.__name__}") from exc


def _query_assets_by_disease(disease: str) -> list[dict[str, Any]]:
    canonical = normalize_disease_code(disease).upper()
    aliases = get_disease_query_values(canonical)
    query = f"""
    MATCH (a:ImageModalAsset)-[:IMAGE_MODAL_ASSET_FOR|HAS_IMAGE_MODAL]->(d:Disease)
    WHERE {_disease_match_clause("d")}
    RETURN DISTINCT
      coalesce(a.file_name, a.name) AS file_name,
      coalesce(a.disease_code, d.code, d.disease_code, d.name, $canonical) AS disease_code,
      coalesce(a.inferred_asset_type, a.asset_type, 'image') AS inferred_asset_type,
      coalesce(a.load_status, 'REGISTERED') AS load_status,
      a.s3_uri AS s3_uri
    ORDER BY file_name
    """
    settings = get_settings()
    with get_neo4j_driver().session(database=settings.neo4j_database) as session:
        rows = list(session.run(query, aliases=aliases, canonical=canonical, timeout=12))

    assets: list[dict[str, Any]] = []
    for row in rows:
        file_name = str(row.get("file_name") or "").strip()
        s3_uri = str(row.get("s3_uri") or "").strip()
        if not file_name:
            continue
        assets.append(
            {
                "file_name": file_name,
                "disease_code": str(row.get("disease_code") or canonical).upper(),
                "inferred_asset_type": str(row.get("inferred_asset_type") or "image"),
                "load_status": str(row.get("load_status") or "REGISTERED"),
                "s3_uri": s3_uri,
            }
        )
    return assets


def _query_single_asset(disease: str, file_name: str) -> dict[str, Any] | None:
    canonical = normalize_disease_code(disease).upper()
    normalized_file_name = _normalize_file_name(file_name)
    aliases = get_disease_query_values(canonical)
    query = f"""
    MATCH (a:ImageModalAsset)-[:IMAGE_MODAL_ASSET_FOR|HAS_IMAGE_MODAL]->(d:Disease)
    WHERE {_disease_match_clause("d")}
      AND toLower(coalesce(a.file_name, a.name, '')) = toLower($file_name)
    RETURN DISTINCT
      coalesce(a.file_name, a.name) AS file_name,
      coalesce(a.disease_code, d.code, d.disease_code, d.name, $canonical) AS disease_code,
      coalesce(a.inferred_asset_type, a.asset_type, 'image') AS inferred_asset_type,
      coalesce(a.load_status, 'REGISTERED') AS load_status,
      a.s3_uri AS s3_uri
    LIMIT 1
    """
    settings = get_settings()
    with get_neo4j_driver().session(database=settings.neo4j_database) as session:
        row = session.run(
            query,
            aliases=aliases,
            canonical=canonical,
            file_name=normalized_file_name,
            timeout=12,
        ).single()

    if not row:
        return None

    return {
        "file_name": str(row.get("file_name") or normalized_file_name).strip(),
        "disease_code": str(row.get("disease_code") or canonical).upper(),
        "inferred_asset_type": str(row.get("inferred_asset_type") or "image"),
        "load_status": str(row.get("load_status") or "REGISTERED"),
        "s3_uri": str(row.get("s3_uri") or "").strip(),
    }


@router.get("/image-modal/{disease}")
def get_image_modal_assets(
    disease: str,
    expires_in: int = Query(default=3600, ge=1, le=604800),
) -> dict[str, Any]:
    canonical = normalize_disease_code(disease).upper()
    assets = _query_assets_by_disease(canonical)

    output_assets: list[dict[str, Any]] = []
    for asset in assets:
        s3_uri = asset.get("s3_uri", "")
        if not s3_uri:
            raise HTTPException(status_code=500, detail=f"Missing s3_uri for asset '{asset.get('file_name', '')}'.")
        try:
            presigned_url = _build_presigned_url(s3_uri, expires_in=expires_in)
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid s3_uri for asset '{asset.get('file_name', '')}': {exc}",
            ) from exc
        output_assets.append({**asset, "presigned_url": presigned_url})

    return {
        "disease": canonical,
        "count": len(output_assets),
        "assets": output_assets,
    }


@router.get("/image-modal/{disease}/{file_name}/url")
def get_image_modal_asset_url(
    disease: str,
    file_name: str,
    expires_in: int = Query(default=3600, ge=1, le=604800),
) -> dict[str, Any]:
    canonical = normalize_disease_code(disease).upper()
    asset = _query_single_asset(canonical, file_name)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"ImageModalAsset not found for disease={canonical}, file_name={file_name}.")

    s3_uri = str(asset.get("s3_uri") or "").strip()
    if not s3_uri:
        raise HTTPException(status_code=500, detail=f"Missing s3_uri for asset '{asset.get('file_name', file_name)}'.")

    try:
        presigned_url = _build_presigned_url(s3_uri, expires_in=expires_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid s3_uri for asset '{asset.get('file_name', file_name)}': {exc}",
        ) from exc

    return {
        "disease": canonical,
        "file_name": str(asset.get("file_name") or _normalize_file_name(file_name)),
        "s3_uri": s3_uri,
        "presigned_url": presigned_url,
        "expires_in": expires_in,
    }
