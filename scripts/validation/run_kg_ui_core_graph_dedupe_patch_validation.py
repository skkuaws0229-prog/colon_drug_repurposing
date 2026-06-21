from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request


BASE_INTERNAL = "http://127.0.0.1:8000"
BASE_EXTERNAL = "http://15.165.91.171"

TARGET_DISEASES = ["PAAD", "PAH", "PSORIASIS"]
REGRESSION_DISEASES = ["BRCA", "COAD", "LUAD", "LIHC", "STAD", "HNSC", "IPF", "RA"]
NON_CANCER_CANDIDATE_EXPECTED = {"PAH": 11, "IPF": 2, "RA": 23, "PSORIASIS": 41}

OUT_JSON = Path("outputs/config_validation/kg_ui_core_graph_dedupe_patch_ec2.json")
OUT_MD = Path("docs/kg_ui_core_graph_dedupe_patch_ec2.md")


def _fetch_json(url: str) -> tuple[int | None, dict]:
    req = request.Request(url, headers={"ngrok-skip-browser-warning": "true"})
    try:
        with request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            if not isinstance(payload, dict):
                payload = {"raw": payload}
            return resp.getcode(), payload
    except error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {"raw": payload}
        payload["http_error"] = exc.code
        return exc.code, payload
    except Exception as exc:  # noqa: BLE001
        return None, {"exception": f"{exc.__class__.__name__}: {exc}"}


def _graph_url(base: str, disease: str, *, view: str) -> str:
    query = parse.urlencode({"view": view})
    return f"{base}/api/graph/{disease}/ui-basic?{query}"


def _node_semantic_key(node: dict) -> str:
    props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
    disease_code = str(node.get("disease_code") or props.get("disease_code") or props.get("code") or "").strip().upper()
    node_type = str(node.get("type") or node.get("group") or "").strip()
    label = str(node.get("label") or "").strip().lower()
    name = str(node.get("name") or "").strip().lower()
    identity_key = str(node.get("identity_key") or props.get("identity_key") or "").strip().lower()
    row_hash = str(node.get("row_hash") or props.get("row_hash") or "").strip().lower()
    return f"{disease_code}|{node_type}|{label}|{name}|{identity_key}|{row_hash}"


def _duplicate_counts(nodes: list[dict], links: list[dict]) -> dict[str, int]:
    node_ids: dict[str, int] = {}
    semantic: dict[str, int] = {}
    link_keys: dict[str, int] = {}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        if node_id:
            node_ids[node_id] = node_ids.get(node_id, 0) + 1
        key = _node_semantic_key(node)
        semantic[key] = semantic.get(key, 0) + 1

    for link in links:
        if not isinstance(link, dict):
            continue
        source = str(link.get("source") or "").strip()
        target = str(link.get("target") or "").strip()
        rel_type = str(link.get("type") or "").strip()
        if not (source and target and rel_type):
            continue
        key = f"{source}|{rel_type}|{target}"
        link_keys[key] = link_keys.get(key, 0) + 1

    return {
        "duplicate_node_id_count": sum(v - 1 for v in node_ids.values() if v > 1),
        "duplicate_semantic_node_count": sum(v - 1 for v in semantic.values() if v > 1),
        "duplicate_link_count": sum(v - 1 for v in link_keys.values() if v > 1),
    }


def _candidate_node_count(nodes: list[dict]) -> int:
    count = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        group = str(node.get("group") or node.get("type") or "").strip()
        if group == "CandidateDrug":
            count += 1
    return count


def _disease_node_count(nodes: list[dict], disease: str) -> int:
    target = disease.upper()
    count = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        group = str(node.get("group") or node.get("type") or "").strip()
        if group != "Disease":
            continue
        props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
        code = str(node.get("disease_code") or props.get("disease_code") or props.get("code") or node.get("name") or "").strip().upper()
        if code == target:
            count += 1
    return count


def _count_groups(nodes: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        group = str(node.get("group") or node.get("type") or "Unknown").strip() or "Unknown"
        out[group] = out.get(group, 0) + 1
    return out


def _graph_snapshot(base: str, disease: str, view: str) -> dict:
    status, payload = _fetch_json(_graph_url(base, disease, view=view))
    nodes = payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []
    links = payload.get("links", []) if isinstance(payload.get("links"), list) else []
    diagnostics = payload.get("diagnostics", {}) if isinstance(payload.get("diagnostics"), dict) else {}
    dups = _duplicate_counts(nodes, links)
    groups = _count_groups(nodes)
    return {
        "status_code": status,
        "disease": payload.get("disease"),
        "view": view,
        "nodes_count": len(nodes),
        "links_count": len(links),
        "candidate_node_count": _candidate_node_count(nodes),
        "disease_node_count": _disease_node_count(nodes, disease),
        "group_counts": groups,
        "diagnostics": diagnostics,
        **dups,
    }


def _candidate_api(base: str, disease: str, endpoint: str) -> dict:
    status, payload = _fetch_json(f"{base}/api/diseases/{disease}/{endpoint}")
    items = payload.get("items", []) if isinstance(payload.get("items"), list) else []
    return {
        "status_code": status,
        "count": int(payload.get("count") or 0),
        "items_len": len(items),
        "source_tables": (payload.get("diagnostics") or {}).get("source_tables") if isinstance(payload.get("diagnostics"), dict) else None,
    }


def main() -> None:
    target = {}
    for disease in TARGET_DISEASES:
        target[disease] = {
            "full_internal": _graph_snapshot(BASE_INTERNAL, disease, "full"),
            "core_internal": _graph_snapshot(BASE_INTERNAL, disease, "core"),
            "full_external": _graph_snapshot(BASE_EXTERNAL, disease, "full"),
            "core_external": _graph_snapshot(BASE_EXTERNAL, disease, "core"),
        }

    regression_graph = {d: _graph_snapshot(BASE_EXTERNAL, d, "core") for d in REGRESSION_DISEASES}

    non_cancer_candidates = {d: _candidate_api(BASE_EXTERNAL, d, "candidates") for d in NON_CANCER_CANDIDATE_EXPECTED}
    paad_candidates = _candidate_api(BASE_EXTERNAL, "PAAD", "candidates")
    paad_final_candidates = _candidate_api(BASE_EXTERNAL, "PAAD", "final-candidates")

    target_success = {}
    for disease in TARGET_DISEASES:
        core = target[disease]["core_external"]
        target_success[disease] = (
            core["status_code"] == 200
            and str(core.get("disease") or "").upper() == disease
            and core["nodes_count"] <= 200
            and core["links_count"] <= 300
            and core["nodes_count"] > 0
            and core["links_count"] > 0
            and core["candidate_node_count"] >= 1
            and core["disease_node_count"] >= 1
            and core["duplicate_node_id_count"] == 0
            and core["duplicate_link_count"] == 0
        )

    non_cancer_candidate_success = all(
        non_cancer_candidates[d]["status_code"] == 200
        and non_cancer_candidates[d]["count"] == NON_CANCER_CANDIDATE_EXPECTED[d]
        and non_cancer_candidates[d]["items_len"] == NON_CANCER_CANDIDATE_EXPECTED[d]
        for d in NON_CANCER_CANDIDATE_EXPECTED
    )
    paad_candidate_regression_ok = (
        paad_candidates["status_code"] == 200
        and paad_final_candidates["status_code"] == 200
        and paad_candidates["count"] == paad_candidates["items_len"]
        and paad_final_candidates["count"] == paad_final_candidates["items_len"]
    )
    graph_regression_ok = all(
        rec["status_code"] == 200 and rec["nodes_count"] > 0 and rec["links_count"] > 0 for rec in regression_graph.values()
    )

    status = (
        "PASS"
        if all(target_success.values()) and non_cancer_candidate_success and paad_candidate_regression_ok and graph_regression_ok
        else "PARTIAL_OR_FAIL"
    )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_diseases": target,
        "target_success": target_success,
        "non_cancer_candidates_external": non_cancer_candidates,
        "paad_candidates_external": paad_candidates,
        "paad_final_candidates_external": paad_final_candidates,
        "regression_graph_external_core": regression_graph,
        "checks": {
            "target_core_caps_ok": all(target_success.values()),
            "non_cancer_candidate_regression_ok": non_cancer_candidate_success,
            "paad_candidate_regression_ok": paad_candidate_regression_ok,
            "graph_regression_ok": graph_regression_ok,
            "postgres_write_performed": False,
            "neo4j_write_performed": False,
        },
        "status": status,
        "errors": [],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# KG UI Core Graph Dedupe Patch Validation (EC2)")
    lines.append("")
    lines.append(f"- status: `{status}`")
    lines.append("")
    lines.append("## Target Disease Before/After (full vs core, external)")
    for disease in TARGET_DISEASES:
        full = target[disease]["full_external"]
        core = target[disease]["core_external"]
        lines.append(
            f"- {disease}: full(nodes={full['nodes_count']}, links={full['links_count']}), "
            f"core(nodes={core['nodes_count']}, links={core['links_count']}), "
            f"dup_node_id={core['duplicate_node_id_count']}, dup_link={core['duplicate_link_count']}, "
            f"candidate_nodes={core['candidate_node_count']}, disease_nodes={core['disease_node_count']}"
        )
    lines.append("")
    lines.append("## Non-Cancer Candidate API Regression (external)")
    for disease in ("PAH", "IPF", "RA", "PSORIASIS"):
        rec = non_cancer_candidates[disease]
        lines.append(f"- {disease}: status={rec['status_code']}, count={rec['count']}, items={rec['items_len']}, tables={rec['source_tables']}")
    lines.append("")
    lines.append("## PAAD Candidate/Final Candidate Regression (external)")
    lines.append(f"- PAAD candidates: status={paad_candidates['status_code']}, count={paad_candidates['count']}, items={paad_candidates['items_len']}")
    lines.append(
        f"- PAAD final-candidates: status={paad_final_candidates['status_code']}, count={paad_final_candidates['count']}, items={paad_final_candidates['items_len']}"
    )
    lines.append("")
    lines.append("## Graph Regression (external core)")
    for disease, rec in regression_graph.items():
        lines.append(f"- {disease}: status={rec['status_code']}, nodes={rec['nodes_count']}, links={rec['links_count']}")
    lines.append("")
    lines.append("## Guardrail")
    lines.append("- PostgreSQL write: not performed")
    lines.append("- Neo4j write: not performed")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("status=", status)
    for disease in TARGET_DISEASES:
        core = target[disease]["core_external"]
        print(f"{disease} core nodes={core['nodes_count']} links={core['links_count']}")
    print("json=", OUT_JSON.as_posix())
    print("md=", OUT_MD.as_posix())


if __name__ == "__main__":
    main()

