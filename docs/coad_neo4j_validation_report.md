# COAD Neo4j Validation Report

- generated_at: 2026-05-06T15:24:33.196099+00:00
- disease: COAD
- execute_requested: true
- execute_performed: true
- overall_status: PASS

## Node Counts
- Disease_COAD: 1
- DrugCandidate_for_COAD: 30
- SourceArtifact: 5
- Run: 2

## Relationship Counts
- HAS_ADMET_PROFILE: 45
- VALIDATED_BY_EXTERNAL_DATA: 30

## Guardrail Checks
- postgres_status_in_plan: POSTGRES_LOADED
- postgres_status_in_execute_report: POSTGRES_LOADED
- neo4j_status_in_plan: REACHABLE
- blocked_decisions_rejected: True
- no_admet_guardrail: True
- approved_roles_only: True
- non_compact_artifacts_blocked: True

## Source Artifacts Used
- candidate_tiered | drug_candidate_tier | C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv
- final_after_admet | final_candidate_result | C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv
- external_validation_top30 | external_validation_result | C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step6_run\results\colon_top30_drugs_ensemble.csv
- admet_top30 | admet_result | C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\admet\20260428_colon_v2_step7\20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv

## Skipped Rows
