# Colon vs BRCA Graph Data (PostgreSQL ACE)

## What This Builds

`analysis/postgres_ace/colon_brca_graph.sql` materializes graph-shaped data from `ace.repurposing_result`:

- Node types:
`disease`, `drug`, `pathway`, `target`
- Edge types:
`has_candidate`, `in_pathway`, `targets`, `shared_candidate`

## Prerequisite

Run relationship loader first:

```bash
psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_relationship.sql
```

## Build Graph Tables

```bash
psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_graph.sql
```

## UI Dashboard

Graph UI files:

- `analysis/postgres_ace/colon_brca_graph_dashboard.html`
- `analysis/postgres_ace/colon_brca_graph_data.json`
- `analysis/postgres_ace/colon_brca_graph_data.js`
- `analysis/postgres_ace/export_colon_brca_graph_data.ps1`

Rebuild UI data JSON from source CSV:

```powershell
powershell -ExecutionPolicy Bypass -File analysis/postgres_ace/export_colon_brca_graph_data.ps1
```

Then open:

```text
analysis/postgres_ace/colon_brca_graph_dashboard.html
```

## Quick Validation

```sql
SELECT * FROM ace.v_graph_node_counts;
SELECT * FROM ace.v_graph_edge_counts;
SELECT * FROM ace.v_graph_top_degree LIMIT 20;
```

## Example Traversal

```sql
SELECT d.label AS disease, dr.label AS drug, p.label AS pathway
FROM ace.graph_edge e1
JOIN ace.graph_node d ON d.node_id = e1.src_node_id AND d.node_type = 'disease'
JOIN ace.graph_node dr ON dr.node_id = e1.dst_node_id AND dr.node_type = 'drug'
JOIN ace.graph_edge e2 ON e2.src_node_id = dr.node_id AND e2.edge_type = 'in_pathway'
JOIN ace.graph_node p ON p.node_id = e2.dst_node_id AND p.node_type = 'pathway'
WHERE d.attrs->>'disease' = 'colon'
ORDER BY dr.label, p.label;
```
