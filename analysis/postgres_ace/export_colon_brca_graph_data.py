#!/usr/bin/env python
"""
Build graph JSON for Colon vs BRCA repurposing candidates.

Input:
  - models/admet_results/final_drug_candidates.csv
  - 20260414_re_pre_project_v3/step4_results/step6_final/repurposing_top15.csv

Output:
  - analysis/postgres_ace/colon_brca_graph_data.json
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COLON_CSV = ROOT / "models" / "admet_results" / "final_drug_candidates.csv"
BRCA_CSV = (
    ROOT
    / "20260414_re_pre_project_v3"
    / "step4_results"
    / "step6_final"
    / "repurposing_top15.csv"
)
OUT_JSON = Path(__file__).resolve().parent / "colon_brca_graph_data.json"


def norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def split_tokens(value: str) -> list[str]:
    if not value:
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


def safe_float(value: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def add_node(
    node_map: dict[str, dict],
    node_id: str,
    node_type: str,
    label: str,
    **attrs,
) -> None:
    if node_id in node_map:
        node_map[node_id]["attrs"].update(
            {k: v for k, v in attrs.items() if v is not None and v != ""}
        )
        return
    node_map[node_id] = {
        "id": node_id,
        "type": node_type,
        "label": label,
        "attrs": {k: v for k, v in attrs.items() if v is not None and v != ""},
    }


def add_edge(
    edge_map: dict[tuple[str, str, str], dict],
    source: str,
    target: str,
    edge_type: str,
    weight: float | None = None,
    **attrs,
) -> None:
    key = (source, target, edge_type)
    clean_attrs = {k: v for k, v in attrs.items() if v is not None and v != ""}
    if key not in edge_map:
        edge_map[key] = {
            "source": source,
            "target": target,
            "type": edge_type,
            "weight": weight,
            "attrs": clean_attrs,
        }
        return
    prev = edge_map[key]
    if prev.get("weight") is None and weight is not None:
        prev["weight"] = weight
    prev["attrs"].update(clean_attrs)


def build_graph() -> dict:
    colon_rows = read_csv_rows(COLON_CSV)
    brca_rows = read_csv_rows(BRCA_CSV)

    node_map: dict[str, dict] = {}
    edge_map: dict[tuple[str, str, str], dict] = {}

    add_node(node_map, "disease:colon", "disease", "COLON", disease="colon")
    add_node(node_map, "disease:brca", "disease", "BRCA", disease="brca")

    disease_drug_norms: dict[str, dict[str, str]] = {"colon": {}, "brca": {}}

    for row in colon_rows:
        drug_name = (row.get("drug_name") or "").strip()
        if not drug_name:
            continue
        drug_norm = norm_text(drug_name)
        if not drug_norm:
            continue

        disease = "colon"
        drug_id = f"drug:{disease}:{drug_norm}"
        disease_drug_norms[disease][drug_norm] = drug_id
        add_node(
            node_map,
            drug_id,
            "drug",
            drug_name,
            disease=disease,
            drug_name_norm=drug_norm,
            drug_ref_id=(row.get("drug_id") or "").strip(),
            rank=safe_float(row.get("final_rank") or ""),
            combined_score=safe_float(row.get("combined_score") or ""),
            category=(row.get("category") or "").strip(),
        )
        add_edge(
            edge_map,
            "disease:colon",
            drug_id,
            "has_candidate",
            weight=safe_float(row.get("combined_score") or ""),
            source="colon_csv",
        )

        pathway = (row.get("pathway") or "").strip()
        if pathway:
            pathway_norm = norm_text(pathway)
            pathway_id = f"pathway:{pathway_norm}"
            add_node(node_map, pathway_id, "pathway", pathway, pathway_norm=pathway_norm)
            add_edge(edge_map, drug_id, pathway_id, "in_pathway", source="colon_csv")

        for token in split_tokens(row.get("target") or ""):
            target_norm = norm_text(token)
            if not target_norm:
                continue
            target_id = f"target:{target_norm}"
            add_node(node_map, target_id, "target", token, target_norm=target_norm)
            add_edge(edge_map, drug_id, target_id, "targets", source="colon_csv")

    for row in brca_rows:
        drug_name = (row.get("drug_name") or "").strip()
        if not drug_name:
            continue
        drug_norm = norm_text(drug_name)
        if not drug_norm:
            continue

        disease = "brca"
        drug_id = f"drug:{disease}:{drug_norm}"
        disease_drug_norms[disease][drug_norm] = drug_id
        add_node(
            node_map,
            drug_id,
            "drug",
            drug_name,
            disease=disease,
            drug_name_norm=drug_norm,
            drug_ref_id=(row.get("canonical_drug_id") or "").strip(),
            rank=safe_float(row.get("repurposing_rank") or row.get("rank") or ""),
            combined_score=safe_float(row.get("final_score") or ""),
            category=(row.get("category") or "").strip(),
        )
        add_edge(
            edge_map,
            "disease:brca",
            drug_id,
            "has_candidate",
            weight=safe_float(row.get("final_score") or ""),
            source="brca_csv",
        )

        pathway = (row.get("pathway") or "").strip()
        if pathway:
            pathway_norm = norm_text(pathway)
            pathway_id = f"pathway:{pathway_norm}"
            add_node(node_map, pathway_id, "pathway", pathway, pathway_norm=pathway_norm)
            add_edge(edge_map, drug_id, pathway_id, "in_pathway", source="brca_csv")

        for token in split_tokens(row.get("target") or ""):
            target_norm = norm_text(token)
            if not target_norm:
                continue
            target_id = f"target:{target_norm}"
            add_node(node_map, target_id, "target", token, target_norm=target_norm)
            add_edge(edge_map, drug_id, target_id, "targets", source="brca_csv")

    overlaps = sorted(
        set(disease_drug_norms["colon"].keys()) & set(disease_drug_norms["brca"].keys())
    )
    for norm in overlaps:
        add_edge(
            edge_map,
            disease_drug_norms["colon"][norm],
            disease_drug_norms["brca"][norm],
            "shared_candidate",
            weight=1.0,
            drug_name_norm=norm,
        )

    nodes = sorted(node_map.values(), key=lambda x: (x["type"], x["label"], x["id"]))
    edges = sorted(
        edge_map.values(), key=lambda x: (x["type"], x["source"], x["target"])
    )

    node_counts: dict[str, int] = {}
    for n in nodes:
        node_counts[n["type"]] = node_counts.get(n["type"], 0) + 1

    edge_counts: dict[str, int] = {}
    for e in edges:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1

    return {
        "meta": {
            "name": "Colon vs BRCA Repurposing Graph",
            "sources": [str(COLON_CSV.relative_to(ROOT)), str(BRCA_CSV.relative_to(ROOT))],
            "counts": {
                "node_total": len(nodes),
                "edge_total": len(edges),
                "node_by_type": node_counts,
                "edge_by_type": edge_counts,
                "overlap_drug_count": len(overlaps),
            },
            "overlap_drug_norms": overlaps,
        },
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    graph = build_graph()
    OUT_JSON.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON}")
    print(
        "Nodes:",
        graph["meta"]["counts"]["node_total"],
        "| Edges:",
        graph["meta"]["counts"]["edge_total"],
    )


if __name__ == "__main__":
    main()
