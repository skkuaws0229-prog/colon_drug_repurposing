import argparse
import os
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    return GraphDatabase.driver(uri, auth=(user, password))


def fetch_graph_scores(session, disease_id: str) -> pd.DataFrame:
    query = """
    MATCH (dis:Disease {id: $disease_id})<-[:ASSOCIATED_WITH]-(g:Gene)<-[:TARGETS]-(dr:Drug)
    RETURN
      dr.id AS drug_id,
      dr.name AS drug_name,
      count(DISTINCT g) AS overlap_genes,
      collect(DISTINCT g.symbol) AS matched_genes
    ORDER BY overlap_genes DESC, drug_name ASC
    """
    rows = [r.data() for r in session.run(query, disease_id=disease_id)]
    if not rows:
        return pd.DataFrame(columns=["drug_id", "drug_name", "overlap_genes", "matched_genes"])
    return pd.DataFrame(rows)


def normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    mx = series.max()
    if mx == 0:
        return series * 0
    return series / mx


def build_spotfire_bundle(session, disease_id: str, top_df: pd.DataFrame):
    top_ids = top_df["drug_id"].tolist()
    if not top_ids:
        return

    edge_query = """
    MATCH (dr:Drug)-[:TARGETS]->(g:Gene)-[:ASSOCIATED_WITH]->(dis:Disease {id: $disease_id})
    WHERE dr.id IN $drug_ids
    OPTIONAL MATCH (g)-[:IN_PATHWAY]->(p:Pathway)
    RETURN
      dr.id AS drug_id,
      dr.name AS drug_name,
      g.symbol AS gene_symbol,
      dis.id AS disease_id,
      dis.name AS disease_name,
      p.id AS pathway_id,
      p.name AS pathway_name
    ORDER BY drug_name, gene_symbol
    """
    edge_rows = [r.data() for r in session.run(edge_query, disease_id=disease_id, drug_ids=top_ids)]
    edges_df = pd.DataFrame(edge_rows)
    if edges_df.empty:
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    edges_df.to_csv(OUT_DIR / "spotfire_drug_gene_pathway_edges.csv", index=False)

    pathway_df = (
        edges_df.dropna(subset=["pathway_id"])
        .groupby(["pathway_id", "pathway_name"], as_index=False)
        .agg(hit_genes=("gene_symbol", "nunique"), hit_drugs=("drug_id", "nunique"))
        .sort_values(["hit_drugs", "hit_genes"], ascending=False)
    )
    pathway_df.to_csv(OUT_DIR / "spotfire_pathway_hits.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Rank ontology-driven drug candidates.")
    parser.add_argument("--disease-id", default="MONDO:0007254")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    scores_df = pd.read_csv(DATA_DIR / "drug_scores.csv")
    driver = get_driver()

    with driver.session() as session:
        graph_df = fetch_graph_scores(session, args.disease_id)

        if graph_df.empty:
            print(f"No graph candidates found for disease_id={args.disease_id}")
            return

        merged = graph_df.merge(scores_df, on="drug_id", how="left")
        merged["reversal_score"] = merged["reversal_score"].fillna(0.0)
        merged["admet_score"] = merged["admet_score"].fillna(0.0)
        merged["kg_score"] = normalize(merged["overlap_genes"])

        merged["final_score"] = (
            0.5 * merged["kg_score"]
            + 0.3 * merged["reversal_score"]
            + 0.2 * merged["admet_score"]
        )

        ranked = merged.sort_values("final_score", ascending=False).reset_index(drop=True)
        top_df = ranked.head(args.top_k).copy()

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ranked.to_csv(OUT_DIR / "all_candidates_ranked.csv", index=False)
        top_df.to_csv(OUT_DIR / "top_candidates.csv", index=False)

        with (OUT_DIR / "top_candidates.md").open("w", encoding="utf-8") as f:
            f.write(f"# Top {args.top_k} Candidates for {args.disease_id}\n\n")
            cols = ["drug_id", "drug_name", "overlap_genes", "reversal_score", "admet_score", "final_score"]
            f.write(top_df[cols].to_markdown(index=False))
            f.write("\n")

        build_spotfire_bundle(session, args.disease_id, top_df)

    driver.close()
    print("Done. Outputs written to ontology_quick_demo/outputs/")


if __name__ == "__main__":
    main()
