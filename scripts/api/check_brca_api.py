#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check BRCA FastAPI endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8200")
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def http_get_json(url: str, timeout: int) -> Tuple[int, Dict[str, Any] | List[Any]]:
    req = Request(url=url, method="GET", headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
        return resp.status, json.loads(payload)


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")

    try:
        status, health = http_get_json(f"{base}/api/health", args.timeout)
        if status != 200:
            print(f"[error] /api/health status={status}")
            return 1
        print("[ok] /api/health")

        status, candidates = http_get_json(f"{base}/api/brca/candidates", args.timeout)
        if status != 200:
            print(f"[error] /api/brca/candidates status={status}")
            return 1
        if not isinstance(candidates, list) or not candidates:
            print("[error] /api/brca/candidates returned empty list")
            return 1
        first = candidates[0]
        drug_id = str(first.get("drug_id") or "").strip()
        if not drug_id:
            print("[error] first candidate has empty drug_id")
            return 1
        print(f"[ok] /api/brca/candidates count={len(candidates)} first_drug_id={drug_id}")

        paths = [
            f"/api/brca/candidates/{drug_id}",
            f"/api/brca/candidates/{drug_id}/admet",
            f"/api/brca/candidates/{drug_id}/validation",
            f"/api/brca/candidates/{drug_id}/kg",
            f"/api/brca/agent-context/{drug_id}",
        ]
        results: Dict[str, Any] = {}
        for path in paths:
            status, body = http_get_json(f"{base}{path}", args.timeout)
            if status != 200:
                print(f"[error] {path} status={status}")
                return 1
            results[path] = body
            print(f"[ok] {path}")

        admet_n = len(results[f"/api/brca/candidates/{drug_id}/admet"].get("admet_results", []))
        valid_n = len(results[f"/api/brca/candidates/{drug_id}/validation"].get("validation_results", []))
        genes_n = len(results[f"/api/brca/candidates/{drug_id}/kg"].get("genes", []))
        pathways_n = len(results[f"/api/brca/candidates/{drug_id}/kg"].get("pathways", []))
        warnings_n = len(results[f"/api/brca/agent-context/{drug_id}"].get("warnings_caveats", []))

        print("\n[summary]")
        print(f"- drug_id: {drug_id}")
        print(f"- admet_rows: {admet_n}")
        print(f"- validation_rows: {valid_n}")
        print(f"- genes: {genes_n}")
        print(f"- pathways: {pathways_n}")
        print(f"- warnings: {warnings_n}")
        print("[success] BRCA API check passed")
        return 0

    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = "<no body>"
        print(f"[error] HTTP {exc.code}: {detail}")
        return 1
    except URLError as exc:
        print(f"[error] URL error: {exc}")
        return 1
    except Exception as exc:
        print(f"[error] Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
