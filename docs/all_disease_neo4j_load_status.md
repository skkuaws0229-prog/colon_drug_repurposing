# All Disease Neo4j Load Status (Read-only)

- generated_at_utc: 2026-05-20T07:23:18.143555+00:00
- source: EC2 live read-only via FastAPI endpoints
- base_url: http://15.165.91.171

## Final Table
| disease | disease_node | candidate_count | driver_gene_count | subtype_count | evidence_count | suspicious_count | api_nodes | api_links | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BRCA | 1 | 30 | 0 | 0 | 0 | 0 | 82 | 143 | COMPLETE |
| COAD | 1 | 30 | 5 | 5 | 159 | 0 | 37 | 36 | COMPLETE |
| LUAD | 1 | 30 | 0 | 0 | 0 | 0 | 31 | 30 | COMPLETE |
| LIHC | 1 | 15 | 0 | 0 | 0 | 0 | 16 | 15 | COMPLETE |
| STAD | 1 | 15 | 0 | 0 | 0 | 0 | 16 | 15 | COMPLETE |
| PAAD | 1 | 15 | 0 | 0 | 0 | 0 | 16 | 15 | COMPLETE |
| HNSC | 1 | 30 | 0 | 0 | 0 | 0 | 31 | 30 | COMPLETE |

## Detailed Counts
### BRCA
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 30
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=82, links=143, neo4j_status=ok

### COAD
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 30
- HAS_DRIVER_GENE count: 5
- MolecularSubtype count: 5
- ModelEvidence count: 15
- ExternalValidationEvidence count: 110
- LoadAuditEvidence count: 34
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=37, links=36, neo4j_status=ok

### LUAD
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 30
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=31, links=30, neo4j_status=ok

### LIHC
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 15
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=16, links=15, neo4j_status=ok

### STAD
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 15
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=16, links=15, neo4j_status=ok

### PAAD
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 15
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=16, links=15, neo4j_status=ok

### HNSC
- Disease node exists: True (count=1)
- DrugCandidate-CANDIDATE_FOR count: 30
- HAS_DRIVER_GENE count: 0
- MolecularSubtype count: 0
- ModelEvidence count: 0
- ExternalValidationEvidence count: 0
- LoadAuditEvidence count: 0
- Suspicious DrugCandidate count (drug_name/drug_name_norm null): 0
- Model contamination exists: false (count=0)
- /ui-basic: http=200, nodes=31, links=30, neo4j_status=ok

## Status Counts
- COMPLETE: 7
- COMPLETE_WITH_WARNINGS: 0
- PARTIAL: 0
- NOT_LOADED: 0
