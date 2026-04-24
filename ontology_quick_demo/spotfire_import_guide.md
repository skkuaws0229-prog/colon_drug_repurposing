# Spotfire-Centered Import Guide

This guide uses outputs from `scripts/rank_candidates.py`.

## Files to import into Spotfire
- `outputs/top_candidates.csv`
- `outputs/spotfire_drug_gene_pathway_edges.csv`
- `outputs/spotfire_pathway_hits.csv`

## Suggested Spotfire data model
1. `top_candidates` (primary table)
   - Key: `drug_id`
2. `drug_gene_pathway_edges`
   - Keys: `drug_id`, `gene_symbol`, `pathway_id`
3. `pathway_hits`
   - Key: `pathway_id`

Relation suggestions:
- `top_candidates.drug_id` -> `drug_gene_pathway_edges.drug_id`
- `drug_gene_pathway_edges.pathway_id` -> `pathway_hits.pathway_id`

## Visuals for fast demo
1. Candidate ranking bar chart
   - X: `drug_name`
   - Y: `final_score`
   - Color: `admet_score`

2. Target overlap heatmap
   - Rows: `drug_name`
   - Columns: `gene_symbol`
   - Cell value: count

3. Pathway impact table
   - Columns: `pathway_name`, `hit_drugs`, `hit_genes`
   - Sort by `hit_drugs DESC`

## Demo script (2-3 minutes)
1. Show top candidate list and explain scoring formula.
2. Click top drug and show matched target genes.
3. Show impacted pathways to explain mechanism hypothesis.
4. End with "next step": validate top 3 with external evidence.
