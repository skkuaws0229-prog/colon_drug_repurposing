# Ontology-First Drug Repurposing Quick Demo (Spotfire-Centered, 2-3 days)

This is a fast, portfolio-ready demo template for ontology-driven drug repurposing.

## What you get
- Neo4j knowledge graph with ontology-friendly IDs
- Minimal ETL scripts to load drug-gene-disease-pathway relations
- Candidate ranking script combining:
  - graph overlap score
  - expression reversal score
  - ADMET score
- Spotfire-ready CSV bundle for fast business/science demo

## Data model (minimal)
- `Drug(id, name)`
- `Gene(symbol)`
- `Disease(id, name)`
- `Pathway(id, name)`

Relationships:
- `(Drug)-[:TARGETS]->(Gene)`
- `(Gene)-[:ASSOCIATED_WITH]->(Disease)`
- `(Gene)-[:IN_PATHWAY]->(Pathway)`

## Quick start

1) Start Neo4j

```powershell
cd ontology_quick_demo
docker compose up -d
```

2) Create Python env + install deps

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3) Load graph

```powershell
python scripts/load_graph.py
```

4) Rank candidates

```powershell
python scripts/rank_candidates.py --disease-id MONDO:0007254 --top-k 10
```

5) Open outputs
- `outputs/top_candidates.csv`
- `outputs/top_candidates.md`
- `outputs/spotfire_drug_gene_pathway_edges.csv`
- `outputs/spotfire_pathway_hits.csv`
- Spotfire import steps: `spotfire_import_guide.md`

## Environment variables
Defaults are already set for local demo:
- `NEO4J_URI` (default: `bolt://localhost:7687`)
- `NEO4J_USER` (default: `neo4j`)
- `NEO4J_PASSWORD` (default: `neo4j_password`)

## Spotfire-centered 2-3 day execution plan
- Day 1: Run this template end-to-end and validate rank output.
- Day 2: Replace CSVs in `data/` with your real disease/drug mappings.
- Day 3: Import output bundle to Spotfire and produce a 2-3 minute demo story.

## Notes
- This demo is for analysis prototyping and portfolio storytelling, not clinical use.
- Keep ontology IDs stable across files when replacing toy data.
