#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class EndpointCheck:
    method: str
    path: str
    pg_dependent: bool = False
    body: Dict[str, Any] | None = None
    validator: Callable[[Any], Tuple[bool, str]] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BRAC/COAD FastAPI endpoints (BRCA alias supported, read-only).")
    parser.add_argument("--base-url", default="http://127.0.0.1:8200")
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def _request_json(base_url: str, check: EndpointCheck, timeout: int) -> Tuple[int, Any]:
    url = f"{base_url.rstrip('/')}{check.path}"
    data = None
    headers = {"Accept": "application/json"}
    if check.method == "POST":
        headers["Content-Type"] = "application/json"
        data = json.dumps(check.body or {}).encode("utf-8")
    req = Request(url=url, method=check.method, headers=headers, data=data)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return resp.status, payload


def _status_from_response(check: EndpointCheck, status_code: int, payload: Any) -> Tuple[str, str]:
    if 200 <= status_code < 300:
        if check.validator:
            ok, note = check.validator(payload)
            if not ok:
                return "FAIL", note
            return "PASS", note or "ok"
        return "PASS", "ok"

    detail = ""
    if isinstance(payload, dict):
        detail = str(payload.get("detail", ""))
    else:
        detail = str(payload)

    if check.pg_dependent and "PostgreSQL unavailable" in detail:
        return "PG_UNAVAILABLE", detail
    return "FAIL", detail or "request failed"


def _print_table(rows: List[Dict[str, str]]) -> None:
    headers = ["endpoint", "status_code", "status", "note"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row[h])))

    line = " | ".join(h.ljust(widths[h]) for h in headers)
    sep = "-+-".join("-" * widths[h] for h in headers)
    print(line)
    print(sep)
    for row in rows:
        print(" | ".join(str(row[h]).ljust(widths[h]) for h in headers))


def _validate_disease_list(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload_not_object"
    diseases = payload.get("diseases")
    if not isinstance(diseases, list):
        return False, "diseases_not_list"
    got = [str(x) for x in diseases]
    expected = ["BRAC", "COAD"]
    if got != expected:
        return False, f"unexpected_diseases={got}"
    return True, "diseases_ok"


def _validate_disease_brac(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload_not_object"
    disease = str(payload.get("disease", ""))
    if disease != "BRAC":
        return False, f"disease_not_brac:{disease}"
    return True, "disease_brac"


def _validate_candidates_disease_brac(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, list):
        return False, "payload_not_list"
    for row in payload:
        if isinstance(row, dict) and "disease" in row and str(row.get("disease")) != "BRAC":
            return False, f"candidate_row_disease_not_brac:{row.get('disease')}"
    return True, "candidate_rows_ok"


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    checks: List[EndpointCheck] = [
        EndpointCheck("GET", "/api/diseases", validator=_validate_disease_list),
        EndpointCheck("GET", "/api/graph/COAD/summary"),
        EndpointCheck("GET", "/api/graph/BRAC/summary", validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/graph/BRCA/summary", validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/graph/COAD"),
        EndpointCheck("GET", "/api/graph/BRAC", validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/graph/BRCA", validator=_validate_disease_brac),
        EndpointCheck("POST", "/api/assistant/COAD/ask", body={"question": "Summarize graph context.", "mode": "graph_context"}),
        EndpointCheck("POST", "/api/assistant/BRAC/ask", body={"question": "Summarize graph context.", "mode": "graph_context"}, validator=_validate_disease_brac),
        EndpointCheck("POST", "/api/assistant/BRCA/ask", body={"question": "Summarize graph context.", "mode": "graph_context"}, validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/diseases/COAD/summary", pg_dependent=True),
        EndpointCheck("GET", "/api/diseases/COAD/candidates", pg_dependent=True),
        EndpointCheck("GET", "/api/diseases/BRAC/summary", pg_dependent=True, validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/diseases/BRCA/summary", pg_dependent=True, validator=_validate_disease_brac),
        EndpointCheck("GET", "/api/diseases/BRAC/candidates", pg_dependent=True, validator=_validate_candidates_disease_brac),
        EndpointCheck("GET", "/api/diseases/BRCA/candidates", pg_dependent=True, validator=_validate_candidates_disease_brac),
    ]

    rows: List[Dict[str, str]] = []
    failed_non_pg = False

    for check in checks:
        endpoint = f"{check.method} {check.path}"
        status_code = 0
        payload: Any = ""
        try:
            status_code, payload = _request_json(base_url, check, args.timeout)
            status, note = _status_from_response(check, status_code, payload)
        except HTTPError as exc:
            status_code = exc.code
            body = ""
            try:
                body = exc.read().decode("utf-8")
                payload = json.loads(body)
            except Exception:
                payload = body
            status, note = _status_from_response(check, status_code, payload)
        except URLError as exc:
            status = "FAIL"
            note = f"connection_error: {exc}"
        except Exception as exc:  # noqa: BLE001
            status = "FAIL"
            note = f"unexpected_error: {exc}"

        if status == "FAIL":
            failed_non_pg = True

        rows.append(
            {
                "endpoint": endpoint,
                "status_code": str(status_code) if status_code else "-",
                "status": status,
                "note": note.replace("\n", " ").strip(),
            }
        )

    _print_table(rows)
    return 1 if failed_non_pg else 0


if __name__ == "__main__":
    raise SystemExit(main())
