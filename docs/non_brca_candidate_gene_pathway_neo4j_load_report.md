# Non-BRCA Candidate-Gene-Pathway Neo4j Load Report

- Generated (UTC): 2026-05-26T06:53:31.296261+00:00
- Target diseases: COAD, LUAD, STAD, HNSC, LIHC, PAAD

## BRCA Schema Inspection

- Status: `error`
- Error: `AuthError: {code: Neo.ClientError.Security.Unauthorized} {message: The client is unauthorized due to authentication failure.}`
- Candidate-Gene relationship inventory: `[]`
- Gene-Pathway relationship inventory: `[]`
- Sample property keys: `{}`

## Per-Disease Load

### COAD
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

### LUAD
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

### STAD
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

### HNSC
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

### LIHC
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

### PAAD
- Status: `error`
- Error: `OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
`
- PostgreSQL evidence summary: `{}`
- Neo4j load summary: `{}`

## Local File Evidence Inspection

### COAD
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 7, 'sample_files': ['data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_comprehensive_drug_scores.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_top30_drugs_ensemble.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_top50_drugs_ensemble.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_run\\curated_data\\geo\\GSE39582\\GPL570_probe_to_gene.json', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_run\\results\\colon_top30_drugs_ensemble.csv']}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 4, 'sample_files': ['outputs\\config_validation\\coad_drugcandidate_cleanup_execute_report.json', 'outputs\\config_validation\\coad_drugcandidate_cleanup_preview.json', 'outputs\\config_validation\\coad_drugcandidate_contamination_fix_plan.json', 'outputs\\config_validation\\coad_postgres_target_schema_report.json']}], 'candidate_files': ['data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_comprehensive_drug_scores.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_top30_drugs_ensemble.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_external_validation_existing_results\\20260428_colon_v2_colon_top50_drugs_ensemble.csv', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_run\\curated_data\\geo\\GSE39582\\GPL570_probe_to_gene.json', 'data_cache\\final_data\\COAD\\20260428_colon_v2\\20260428_colon_v2_step6_run\\results\\colon_top30_drugs_ensemble.csv', 'outputs\\config_validation\\coad_drugcandidate_cleanup_execute_report.json', 'outputs\\config_validation\\coad_drugcandidate_cleanup_preview.json', 'outputs\\config_validation\\coad_drugcandidate_contamination_fix_plan.json', 'outputs\\config_validation\\coad_postgres_target_schema_report.json']}`

### LUAD
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 1, 'sample_files': ['outputs\\config_validation\\luad_generated_yaml_from_real_inspection_report.json']}], 'candidate_files': ['outputs\\config_validation\\luad_generated_yaml_from_real_inspection_report.json']}`

### STAD
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 0, 'sample_files': []}], 'candidate_files': []}`

### HNSC
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 0, 'sample_files': []}], 'candidate_files': []}`

### LIHC
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 0, 'sample_files': []}], 'candidate_files': []}`

### PAAD
- File inspection: `{'scanned_roots': [{'root': 'data_cache', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'models', 'exists': True, 'matches': 0, 'sample_files': []}, {'root': 'outputs', 'exists': True, 'matches': 0, 'sample_files': []}], 'candidate_files': []}`

## Obsidian API Validation

- Summary: `{'total_cases': 6, 'all_checks_pass_cases': 6, 'failed_cases': 0}`
### COAD
- Path: `/api/graph/COLON/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LUAD
- Path: `/api/graph/LUAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### STAD
- Path: `/api/graph/STAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### HNSC
- Path: `/api/graph/HNSC/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LIHC
- Path: `/api/graph/LIVER/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### PAAD
- Path: `/api/graph/PAAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'normalized_expected': True, 'candidate_gene_edge_count_positive_when_evidence_exists': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`
