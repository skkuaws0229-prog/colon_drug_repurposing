from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


BASE_INTERNAL = "http://127.0.0.1:8000"
BASE_EXTERNAL = "http://15.165.91.171"

NON_CANCER_DISEASES = ["PAH", "IPF", "RA", "PSORIASIS"]
REGRESSION_DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "STAD", "PAAD", "HNSC"]
REL_KEYS = [
    "HAS_RESULT_ARTIFACT",
    "HAS_CANDIDATE",
    "HAS_ADMET_EVIDENCE",
    "HAS_MODEL_EVIDENCE",
    "HAS_VALIDATION_EVIDENCE",
    "HAS_EVIDENCE",
    "HAS_IMAGE_MODAL",
]

JSON_OUT = Path("outputs/config_validation/non_cancer_fastapi_graph_links_patch_ec2.json")
MD_OUT = Path("docs/non_cancer_fastapi_graph_links_patch_ec2.md")


def _fetch_json(url: str, timeout: int = 120, retries: int = 2) -> tuple[int | None, dict[str, object]]:
    req = request.Request(url, headers={"ngrok-skip-browser-warning": "true"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw else {}
            if not isinstance(payload, dict):
                payload = {"raw": payload}
            return status, payload
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        payload: dict[str, object]
        try:
            parsed = json.loads(raw) if raw else {}
            payload = parsed if isinstance(parsed, dict) else {"raw": parsed}
        except Exception:
            payload = {"raw": raw}
        payload["http_error"] = exc.code
        if retries > 0 and exc.code in {502, 503, 504}:
            return _fetch_json(url, timeout=timeout, retries=retries - 1)
        return exc.code, payload
    except Exception as exc:  # noqa: BLE001
        if retries > 0:
            return _fetch_json(url, timeout=timeout, retries=retries - 1)
        return None, {"exception": f"{exc.__class__.__name__}: {exc}"}


def _ui_basic_record(base: str, disease: str) -> dict[str, object]:
    status, payload = _fetch_json(f"{base}/api/graph/{disease}/ui-basic")
    nodes = payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []
    links = payload.get("links", []) if isinstance(payload.get("links"), list) else []
    warnings = payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []
    return {
        "status_code": status,
        "ok": status == 200,
        "nodes_count": len(nodes),
        "links_count": len(links),
        "warnings": warnings,
        "detail": payload.get("detail"),
        "exception": payload.get("exception"),
    }


def _summary_record(disease: str) -> dict[str, object]:
    status, payload = _fetch_json(f"{BASE_INTERNAL}/api/graph/{disease}/summary")
    rel_counts = payload.get("relationship_counts", {}) if isinstance(payload.get("relationship_counts"), dict) else {}
    selected_rel_counts = {k: int(rel_counts.get(k, 0) or 0) for k in REL_KEYS}
    return {
        "status_code": status,
        "ok": status == 200,
        "relationship_counts_selected": selected_rel_counts,
        "full_relationship_counts": rel_counts,
        "warnings": payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else [],
        "status": payload.get("status"),
        "detail": payload.get("detail"),
        "exception": payload.get("exception"),
    }


def main() -> None:
    internal_ui_basic: dict[str, dict[str, object]] = {}
    external_ui_basic: dict[str, dict[str, object]] = {}
    relationship_summary: dict[str, dict[str, object]] = {}

    for disease in NON_CANCER_DISEASES:
        internal_ui_basic[disease] = _ui_basic_record(BASE_INTERNAL, disease)
        external_ui_basic[disease] = _ui_basic_record(BASE_EXTERNAL, disease)
        relationship_summary[disease] = _summary_record(disease)

    regression_internal: dict[str, dict[str, object]] = {}
    regression_external: dict[str, dict[str, object]] = {}
    for disease in REGRESSION_DISEASES:
        regression_internal[disease] = _ui_basic_record(BASE_INTERNAL, disease)
        regression_external[disease] = _ui_basic_record(BASE_EXTERNAL, disease)

    all_non_cancer_http_200 = all(
        internal_ui_basic[d]["status_code"] == 200 and external_ui_basic[d]["status_code"] == 200
        for d in NON_CANCER_DISEASES
    )
    all_non_cancer_nodes_gt_0 = all(
        internal_ui_basic[d]["nodes_count"] > 0 and external_ui_basic[d]["nodes_count"] > 0
        for d in NON_CANCER_DISEASES
    )
    all_non_cancer_links_gt_0 = all(
        internal_ui_basic[d]["links_count"] > 0 and external_ui_basic[d]["links_count"] > 0
        for d in NON_CANCER_DISEASES
    )
    all_regression_200 = all(
        regression_internal[d]["status_code"] == 200 and regression_external[d]["status_code"] == 200
        for d in REGRESSION_DISEASES
    )
    neo4j_relationships_present = {
        d: any(int(relationship_summary[d]["relationship_counts_selected"].get(k, 0)) > 0 for k in REL_KEYS)  # type: ignore[index]
        for d in NON_CANCER_DISEASES
    }

    status = (
        "PASS"
        if all_non_cancer_http_200
        and all_non_cancer_nodes_gt_0
        and all_non_cancer_links_gt_0
        and all_regression_200
        else "FAIL_OR_PARTIAL"
    )

    result: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "patch_scope": "non_cancer_fastapi_graph_links",
        "non_cancer_diseases": NON_CANCER_DISEASES,
        "regression_diseases": REGRESSION_DISEASES,
        "internal_ui_basic": internal_ui_basic,
        "external_ui_basic": external_ui_basic,
        "regression_internal_ui_basic": regression_internal,
        "regression_external_ui_basic": regression_external,
        "neo4j_relationship_summary_internal": relationship_summary,
        "neo4j_relationships_present": neo4j_relationships_present,
        "success_criteria": {
            "non_cancer_http_200": all_non_cancer_http_200,
            "non_cancer_nodes_gt_0": all_non_cancer_nodes_gt_0,
            "non_cancer_links_gt_0": all_non_cancer_links_gt_0,
            "regression_7_http_200": all_regression_200,
        },
        "status": status,
    }

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Non-Cancer FastAPI Graph Links Patch Validation (EC2)")
    lines.append("")
    lines.append(f"- status: `{status}`")
    lines.append("")
    lines.append("## Non-Cancer Internal/External UI Basic")
    for disease in NON_CANCER_DISEASES:
        i = internal_ui_basic[disease]
        e = external_ui_basic[disease]
        lines.append(
            f"- {disease}: internal(status={i['status_code']}, nodes={i['nodes_count']}, links={i['links_count']}), "
            f"external(status={e['status_code']}, nodes={e['nodes_count']}, links={e['links_count']})"
        )
    lines.append("")
    lines.append("## Neo4j Relationship Summary (Internal)")
    for disease in NON_CANCER_DISEASES:
        rels = relationship_summary[disease]["relationship_counts_selected"]
        lines.append(f"- {disease}: {rels}")
    lines.append("")
    lines.append("## Regression 7 Diseases HTTP Status")
    for disease in REGRESSION_DISEASES:
        i = regression_internal[disease]
        e = regression_external[disease]
        lines.append(f"- {disease}: internal={i['status_code']}, external={e['status_code']}")
    lines.append("")
    lines.append("## Success Criteria")
    for key, value in result["success_criteria"].items():  # type: ignore[index]
        lines.append(f"- {key}: `{value}`")

    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("status=", status)
    for disease in NON_CANCER_DISEASES:
        i = internal_ui_basic[disease]
        e = external_ui_basic[disease]
        print(
            f"{disease} internal={i['status_code']} n={i['nodes_count']} l={i['links_count']} "
            f"external={e['status_code']} n={e['nodes_count']} l={e['links_count']}"
        )
    print("json=", JSON_OUT.as_posix())
    print("md=", MD_OUT.as_posix())


if __name__ == "__main__":
    main()
