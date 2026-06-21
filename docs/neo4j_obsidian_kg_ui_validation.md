# Neo4j Obsidian KG UI Validation

- Generated (UTC): 2026-05-26T06:46:19.507411+00:00
- Target app: `api.main:app`

## Route Checks

- `/api/graph/{disease}/obsidian`: `True`

## Summary

- Total cases: 9
- All-check pass cases: 9
- Failed cases: 0

## Per-Case

### BRAC

- Path: `/api/graph/BRAC/obsidian`
- HTTP: `200`
- Expected normalized disease: `BRCA`
- Actual: `{'disease': 'BRCA', 'requested_disease': 'BRAC', 'normalized_disease': 'BRCA', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### COAD

- Path: `/api/graph/COAD/obsidian`
- HTTP: `200`
- Expected normalized disease: `COAD`
- Actual: `{'disease': 'COAD', 'requested_disease': 'COAD', 'normalized_disease': 'COAD', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### COLON

- Path: `/api/graph/COLON/obsidian`
- HTTP: `200`
- Expected normalized disease: `COAD`
- Actual: `{'disease': 'COAD', 'requested_disease': 'COLON', 'normalized_disease': 'COAD', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LUAD

- Path: `/api/graph/LUAD/obsidian`
- HTTP: `200`
- Expected normalized disease: `LUAD`
- Actual: `{'disease': 'LUAD', 'requested_disease': 'LUAD', 'normalized_disease': 'LUAD', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### STAD

- Path: `/api/graph/STAD/obsidian`
- HTTP: `200`
- Expected normalized disease: `STAD`
- Actual: `{'disease': 'STAD', 'requested_disease': 'STAD', 'normalized_disease': 'STAD', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### HNSC

- Path: `/api/graph/HNSC/obsidian`
- HTTP: `200`
- Expected normalized disease: `HNSC`
- Actual: `{'disease': 'HNSC', 'requested_disease': 'HNSC', 'normalized_disease': 'HNSC', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LIHC

- Path: `/api/graph/LIHC/obsidian`
- HTTP: `200`
- Expected normalized disease: `LIHC`
- Actual: `{'disease': 'LIHC', 'requested_disease': 'LIHC', 'normalized_disease': 'LIHC', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### PAAD

- Path: `/api/graph/PAAD/obsidian`
- HTTP: `200`
- Expected normalized disease: `PAAD`
- Actual: `{'disease': 'PAAD', 'requested_disease': 'PAAD', 'normalized_disease': 'PAAD', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LIVER

- Path: `/api/graph/LIVER/obsidian`
- HTTP: `200`
- Expected normalized disease: `LIHC`
- Actual: `{'disease': 'LIHC', 'requested_disease': 'LIVER', 'normalized_disease': 'LIHC', 'view': 'obsidian', 'source': 'neo4j'}`
- Counts: `{'nodes': 0, 'links': 0, 'edges': 0, 'node_types': [], 'candidate_nodes': 0, 'gene_nodes': 0, 'candidate_gene_edges': 0, 'neo4j_disease_drug_rows': 0, 'neo4j_drug_gene_rows': 0}`
- Checks: `{'required_keys_present': True, 'view_source_ok': True, 'requested_disease_preserved': True, 'normalized_disease_ok': True, 'count_consistent': True, 'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'auth_warning_contract_ok': True, 'node_types_allowed': True, 'candidate_nodes_present_when_evidence_exists': True, 'gene_nodes_present_when_evidence_exists': True, 'candidate_gene_edge_present_when_evidence_exists': True, 'cross_disease_contamination_ok': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`
