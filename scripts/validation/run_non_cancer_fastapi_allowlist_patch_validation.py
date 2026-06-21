from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


BASE_INTERNAL = "http://127.0.0.1:8000"
BASE_EXTERNAL = "http://15.165.91.171"

NEW_DISEASES = ["PAH", "IPF", "RA", "PSORIASIS"]
REGRESSION_DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "STAD", "PAAD", "HNSC"]
ALL_DISEASES = NEW_DISEASES + REGRESSION_DISEASES

JSON_OUT = Path("outputs/config_validation/non_cancer_fastapi_disease_allowlist_patch_ec2.json")
MD_OUT = Path("docs/non_cancer_fastapi_disease_allowlist_patch_ec2.md")


def fetch_graph(url: str) -> dict[str, object]:
    req = request.Request(url, headers={"ngrok-skip-browser-warning": "true"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
            try:
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {"raw_text": body}
            nodes = payload.get("nodes", []) if isinstance(payload, dict) else []
            links = payload.get("links", []) if isinstance(payload, dict) else []
            edges = payload.get("edges", []) if isinstance(payload, dict) else []
            links_count = len(links) if isinstance(links, list) and links else (len(edges) if isinstance(edges, list) else 0)
            return {
                "url": url,
                "status_code": code,
                "ok": 200 <= code < 300,
                "nodes_count": len(nodes) if isinstance(nodes, list) else 0,
                "links_count": links_count,
                "has_nodes": isinstance(nodes, list) and len(nodes) > 0,
                "has_links": links_count > 0,
                "error": None,
                "detail": payload.get("detail") if isinstance(payload, dict) else None,
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail: object = body
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                detail = parsed.get("detail")
        except Exception:
            pass
        return {
            "url": url,
            "status_code": exc.code,
            "ok": False,
            "nodes_count": 0,
            "links_count": 0,
            "has_nodes": False,
            "has_links": False,
            "error": f"HTTPError:{exc.code}",
            "detail": detail,
        }
    except Exception as exc:
        return {
            "url": url,
            "status_code": None,
            "ok": False,
            "nodes_count": 0,
            "links_count": 0,
            "has_nodes": False,
            "has_links": False,
            "error": f"{exc.__class__.__name__}:{exc}",
            "detail": None,
        }


def main() -> None:
    internal_results: dict[str, dict[str, object]] = {}
    external_results: dict[str, dict[str, object]] = {}
    for disease in ALL_DISEASES:
        internal_results[disease] = fetch_graph(f"{BASE_INTERNAL}/api/graph/{disease}/ui-basic")
        external_results[disease] = fetch_graph(f"{BASE_EXTERNAL}/api/graph/{disease}/ui-basic")

    new_ok = all(internal_results[d]["ok"] and external_results[d]["ok"] for d in NEW_DISEASES)
    new_graph_ok = all(
        internal_results[d]["has_nodes"]
        and internal_results[d]["has_links"]
        and external_results[d]["has_nodes"]
        and external_results[d]["has_links"]
        for d in NEW_DISEASES
    )
    regression_ok = all(internal_results[d]["ok"] and external_results[d]["ok"] for d in REGRESSION_DISEASES)

    result: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "patch_scope": "non_cancer_fastapi_disease_allowlist",
        "modified_files": [
            "api/core/disease_aliases.py",
            "api/services/disease_aliases.py",
            "backend/routes/image_modal.py",
        ],
        "added_disease_codes": NEW_DISEASES,
        "canonical_diseases_expected": [
            "BRCA",
            "COAD",
            "LUAD",
            "LIHC",
            "STAD",
            "PAAD",
            "HNSC",
            "PAH",
            "IPF",
            "RA",
            "PSORIASIS",
        ],
        "internal_ui_basic_results": internal_results,
        "external_ui_basic_results": external_results,
        "success_criteria": {
            "new_4_http_200_internal_and_external": new_ok,
            "new_4_have_nodes_links_internal_and_external": new_graph_ok,
            "existing_7_regression_http_200_internal_and_external": regression_ok,
        },
        "errors": [],
    }

    if not new_ok:
        result["errors"].append("new_non_cancer_disease_http_status_failed")
    if new_ok and not new_graph_ok:
        result["errors"].append("new_non_cancer_graph_payload_missing_nodes_or_links")
    if not regression_ok:
        result["errors"].append("existing_7_regression_failed")

    if new_ok and new_graph_ok and regression_ok:
        status = "PASS"
    elif new_ok:
        status = "PARTIAL_PASS_ALLOWLIST_FIXED_GRAPH_DATA_PENDING"
    else:
        status = "FAIL_ALLOWLIST_PATCH_INCOMPLETE"
    result["status"] = status

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Non-Cancer FastAPI Disease Allowlist Patch (EC2)")
    lines.append("")
    lines.append(f"- status: `{status}`")
    lines.append(f"- added_disease_codes: `{', '.join(NEW_DISEASES)}`")
    lines.append("- modified_files:")
    for path in result["modified_files"]:
        lines.append(f"  - `{path}`")
    lines.append("")
    lines.append("## Internal /api/graph/{disease}/ui-basic")
    for disease in ALL_DISEASES:
        r = internal_results[disease]
        lines.append(
            f"- {disease}: status={r['status_code']}, nodes={r['nodes_count']}, links={r['links_count']}, error={r['error']}, detail={r['detail']}"
        )
    lines.append("")
    lines.append("## External /api/graph/{disease}/ui-basic")
    for disease in ALL_DISEASES:
        r = external_results[disease]
        lines.append(
            f"- {disease}: status={r['status_code']}, nodes={r['nodes_count']}, links={r['links_count']}, error={r['error']}, detail={r['detail']}"
        )
    lines.append("")
    lines.append("## Success Criteria")
    for key, value in result["success_criteria"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append(f"- errors: `{result['errors']}`")
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("status=", status)
    for disease in NEW_DISEASES:
        i = internal_results[disease]
        e = external_results[disease]
        print(
            f"NEW {disease} internal={i['status_code']} external={e['status_code']} "
            f"nodes_i={i['nodes_count']} links_i={i['links_count']} "
            f"nodes_e={e['nodes_count']} links_e={e['links_count']}"
        )
    for disease in REGRESSION_DISEASES:
        i = internal_results[disease]
        e = external_results[disease]
        print(f"REG {disease} internal={i['status_code']} external={e['status_code']}")
    print("json=", str(JSON_OUT))
    print("md=", str(MD_OUT))


if __name__ == "__main__":
    main()

