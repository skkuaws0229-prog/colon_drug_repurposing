# Non-BRCA Obsidian Gene/Pathway Neo4j Load Report

- Generated (UTC): 2026-05-26T06:50:41.994699+00:00
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

## Obsidian API Validation

- Summary: `{'total_cases': 6, 'all_checks_pass_cases': 0, 'failed_cases': 6}`
### COAD
- Path: `/api/graph/COLON/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LUAD
- Path: `/api/graph/LUAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### STAD
- Path: `/api/graph/STAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### HNSC
- Path: `/api/graph/HNSC/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### LIHC
- Path: `/api/graph/LIVER/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`

### PAAD
- Path: `/api/graph/PAAD/obsidian`
- HTTP: `200`
- Counts: `{'candidate_nodes': 0, 'gene_nodes': 0, 'pathway_nodes': 0}`
- Diagnostics: `{'neo4j_status': 'unavailable', 'source': 'neo4j', 'label_inventory': [], 'relationship_inventory': [], 'disease_drug_row_count': 0, 'drug_gene_row_count': 0, 'disease_gene_row_count': 0, 'gene_pathway_row_count': 0, 'disease_candidate_edge_count': 0, 'candidate_gene_edge_count': 0, 'disease_gene_edge_count': 0, 'gene_pathway_edge_count': 0, 'node_types': []}`
- Checks: `{'links_edges_identical': True, 'no_postgres_fallback_warning': True, 'candidate_gene_edge_count_positive': False, 'normalized_expected': True}`
- Warnings: `['NEO4J_AUTH_FAILED']`
