import os
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    return GraphDatabase.driver(uri, auth=(user, password))


def create_constraints(tx):
    tx.run("CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (d:Drug) REQUIRE d.id IS UNIQUE")
    tx.run(
        "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE"
    )
    tx.run(
        "CREATE CONSTRAINT pathway_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE"
    )
    tx.run(
        "CREATE CONSTRAINT gene_symbol IF NOT EXISTS FOR (g:Gene) REQUIRE g.symbol IS UNIQUE"
    )


def load_drug_target(tx, df: pd.DataFrame):
    query = """
    UNWIND $rows AS row
    MERGE (dr:Drug {id: row.drug_id})
    SET dr.name = row.drug_name
    MERGE (g:Gene {symbol: row.gene_symbol})
    MERGE (dr)-[:TARGETS]->(g)
    """
    tx.run(query, rows=df.to_dict("records"))


def load_disease_gene(tx, df: pd.DataFrame):
    query = """
    UNWIND $rows AS row
    MERGE (dis:Disease {id: row.disease_id})
    SET dis.name = row.disease_name
    MERGE (g:Gene {symbol: row.gene_symbol})
    MERGE (g)-[:ASSOCIATED_WITH]->(dis)
    """
    tx.run(query, rows=df.to_dict("records"))


def load_gene_pathway(tx, df: pd.DataFrame):
    query = """
    UNWIND $rows AS row
    MERGE (g:Gene {symbol: row.gene_symbol})
    MERGE (p:Pathway {id: row.pathway_id})
    SET p.name = row.pathway_name
    MERGE (g)-[:IN_PATHWAY]->(p)
    """
    tx.run(query, rows=df.to_dict("records"))


def print_counts(tx):
    result = tx.run(
        """
        RETURN
          size([(d:Drug) | d]) AS drugs,
          size([(g:Gene) | g]) AS genes,
          size([(d:Disease) | d]) AS diseases,
          size([(p:Pathway) | p]) AS pathways,
          size([(:Drug)-[:TARGETS]->(:Gene) | 1]) AS drug_targets,
          size([(:Gene)-[:ASSOCIATED_WITH]->(:Disease) | 1]) AS disease_links,
          size([(:Gene)-[:IN_PATHWAY]->(:Pathway) | 1]) AS pathway_links
        """
    )
    row = result.single()
    print("Graph loaded:")
    for key, value in row.items():
        print(f"- {key}: {value}")


def main():
    drug_target = pd.read_csv(DATA_DIR / "drug_target.csv")
    disease_gene = pd.read_csv(DATA_DIR / "disease_gene.csv")
    gene_pathway = pd.read_csv(DATA_DIR / "gene_pathway.csv")

    driver = get_driver()
    with driver.session() as session:
        session.execute_write(create_constraints)
        session.execute_write(load_drug_target, drug_target)
        session.execute_write(load_disease_gene, disease_gene)
        session.execute_write(load_gene_pathway, gene_pathway)
        session.execute_read(print_counts)
    driver.close()


if __name__ == "__main__":
    main()
