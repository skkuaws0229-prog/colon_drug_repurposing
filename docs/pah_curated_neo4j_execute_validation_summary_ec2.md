# PAH Curated Neo4j Execute + Validation Summary (EC2)

## Scope
- Documentation-only summary generated from existing report artifacts and provided read-only Cypher validation counts.
- No execute command was run in this step.

## Source Inputs
- `outputs/config_validation/pah_non_cancer_neo4j_execute_report_ec2.json`
- `outputs/config_validation/pah_non_cancer_validation_report_ec2.json`
- `outputs/config_validation/pah_non_cancer_load_plan_ec2.json`
- Terminal read-only validation counts provided by operator.

## Execution/Validation Flags
- `execute_postgres`: `false`
- `execute_neo4j`: `true`
- `neo4j_connectivity_restored`: `true`
- `password_reset_performed`: `true`
- `read_only_validation_passed`: `true`

## Timestamp
- `execution_timestamp` (from report metadata `generated_at`): `2026-05-22T00:28:12.918716+00:00`

## Read-Only Neo4j Validation Counts
### Nodes
- `Disease (PAH)`: `1`
- `DiseaseEvidence`: `7897`
- `ModelEvidence`: `63`
- `ValidationEvidence`: `26`
- `ResultArtifact`: `21`
- `Candidate`: `11`
- `ImageModalAsset`: `4`

### Relationships
- `HAS_EVIDENCE`: `7897`
- `HAS_MODEL_EVIDENCE`: `63`
- `HAS_VALIDATION_EVIDENCE`: `26`
- `HAS_RESULT_ARTIFACT`: `21`
- `HAS_CANDIDATE`: `11`
- `HAS_IMAGE_MODAL`: `4`

## Warning
- `EmbeddingArtifact` and `HAS_EMBEDDING_ARTIFACT` are not present in the provided read-only validation result set.
- Interpretation: this is treated as a schema-mismatch/non-critical warning unless `EmbeddingArtifact` is explicitly required by design for this PAH curated load.

## Final Outcome
- `final_status`: `PAH_NEO4J_VALIDATED`
- `rerun_required`: `false`
- PostgreSQL write was not executed.
- No PostgreSQL/Neo4j write command was executed during this documentation step.

