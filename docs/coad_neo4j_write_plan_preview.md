# COAD Neo4j Write-Plan Preview (Read-Only)

- timestamp: `2026-05-06T07:48:59.079290+00:00`
- PostgreSQL status: `POSTGRES_LOADED`
- Neo4j status: `REACHABLE`
- Neo4j execute was not run.

## Planned Node Labels
- `AdmetEvidence`
- `Disease`
- `DrugCandidate`
- `ExternalValidationEvidence`
- `ModelEvidence`
- `Run`
- `SourceArtifact`

## Planned Relationship Types
- `CANDIDATE_FOR`
- `DERIVED_FROM_SOURCE`
- `HAS_ADMET_PROFILE`
- `PRODUCED_BY_RUN`
- `SUPPORTED_BY_MODEL`
- `VALIDATED_BY_EXTERNAL_DATA`

## Plan Rows
| source_file_role | target_table | source_file | postgres_artifact_status | postgres_artifact_row_count | planned_node_labels | planned_relationship_types |
|---|---|---|---|---:|---|---|
| candidate_tiered | drug_candidate_tier | 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv | LOADED | 30 | Disease, DrugCandidate, Run, SourceArtifact | CANDIDATE_FOR, DERIVED_FROM_SOURCE, PRODUCED_BY_RUN |
| final_after_admet | final_candidate_result | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | LOADED | 15 | AdmetEvidence, Disease, DrugCandidate, Run, SourceArtifact | CANDIDATE_FOR, DERIVED_FROM_SOURCE, HAS_ADMET_PROFILE, PRODUCED_BY_RUN |
| external_validation_top30 | external_validation_result | colon_top30_drugs_ensemble.csv | LOADED | 30 | Disease, ExternalValidationEvidence, Run, SourceArtifact | DERIVED_FROM_SOURCE, PRODUCED_BY_RUN, VALIDATED_BY_EXTERNAL_DATA |
| admet_top30 | admet_result | 20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv | LOADED | 30 | AdmetEvidence, Disease, Run, SourceArtifact | DERIVED_FROM_SOURCE, HAS_ADMET_PROFILE, PRODUCED_BY_RUN |

## Blocked Decisions
- `BLOCKED`
- `DO_NOT_LOAD_EXCLUDED`
- `LOCAL_SYNC_NEEDED`
- `MISSING`
- `NEEDS_REVIEW`

## no_admet Guardrail
- blocked_tables: `admet_result, final_candidate_result, run_manifest`
- excluded_rows: `0`

## Source Input Reports
- postgres_execute_report: `C:\work\drug-project\outputs\config_validation\coad_postgres_execute_report.json`
- safe_write_plan_preview: `C:\work\drug-project\outputs\config_validation\coad_safe_write_plan_preview.json`
