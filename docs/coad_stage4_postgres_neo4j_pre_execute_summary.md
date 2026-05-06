# COAD Stage 4 PostgreSQL/Neo4j Pre-Execute Summary

## 1) COAD PostgreSQL Load Status
- final status: `POSTGRES_LOADED`
- approved_candidate_count: `31`
- attempted_artifact_count: `31`
- loaded_artifact_count: `31`
- skipped_artifact_count: `0`
- failed_artifact_count: `0`

## 2) PostgreSQL Table Counts
- admet_result: `32`
- coad_load_audit: `4`
- drug_candidate_result: `331`
- drug_candidate_tier: `30`
- ensemble_metric: `1`
- external_validation_result: `92`
- final_candidate_result: `15`
- model_metric: `45`
- model_metric_detailed: `129`
- source_artifact: `2`

## 3) Neo4j Write-Plan Preview Status
- PostgreSQL status: `POSTGRES_LOADED`
- Neo4j status: `REACHABLE`
- Neo4j execute was not run
- execute: `false`

## 4) Planned Neo4j Node Labels
- `AdmetEvidence`
- `Disease`
- `DrugCandidate`
- `ExternalValidationEvidence`
- `ModelEvidence`
- `Run`
- `SourceArtifact`

## 5) Planned Neo4j Relationship Types
- `CANDIDATE_FOR`
- `DERIVED_FROM_SOURCE`
- `HAS_ADMET_PROFILE`
- `PRODUCED_BY_RUN`
- `SUPPORTED_BY_MODEL`
- `VALIDATED_BY_EXTERNAL_DATA`

## 6) Neo4j Plan Rows
- `candidate_tiered -> drug_candidate_tier`
- `final_after_admet -> final_candidate_result`
- `external_validation_top30 -> external_validation_result`
- `admet_top30 -> admet_result`

## 7) Guardrails Confirmed
- Do not load `NEEDS_REVIEW`
- Do not load `DO_NOT_LOAD_EXCLUDED`
- Do not load `BLOCKED`
- Do not load `MISSING`
- Do not load `LOCAL_SYNC_NEEDED`
- `no_admet` files are blocked from `admet_result`, `final_candidate_result`, `run_manifest`

## 8) Current Stage Decision
- COAD PostgreSQL is complete
- COAD Neo4j preview is complete
- COAD Neo4j execute is not yet run
- Next action requires explicit approval before execute

## 9) Multi-Cancer Expansion Note
- After COAD Neo4j execute or explicit defer decision, repeat this workflow for `LUAD`, `LIHC`, `STAD`, `PAAD`, and `HNSC` using disease-specific configs and compact artifact selection only.

## Source Reports
- `docs/coad_postgres_execute_report.md`
- `docs/coad_neo4j_write_plan_preview.md`
- `outputs/config_validation/coad_postgres_execute_report.json`
- `outputs/config_validation/coad_neo4j_write_plan_preview.json`
