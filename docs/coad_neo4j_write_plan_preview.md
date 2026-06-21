# COAD Neo4j Write Plan Preview

- write_plan_status: `FAIL`
- postgres_validation_status: `FAIL`
- project_root_match: `true`
- output_path_guardrail_status: `PASS`
- total_planned_nodes: `0`
- total_planned_relationships: `0`

## Planned Node Counts
- Disease: 0
- DrugCandidate: 0
- CandidateScore: 0
- TierEvidence: 0
- FinalCandidateEvidence: 0
- AdmetEvidence: 0
- ExternalValidationEvidence: 0
- ModelEvidence: 0
- ModelDetailEvidence: 0
- EnsembleEvidence: 0
- SourceArtifact: 0
- LoadAuditEvidence: 0
- Run: 0

## Planned Relationship Counts
- CANDIDATE_FOR: 0
- HAS_CANDIDATE_SCORE: 0
- HAS_TIER: 0
- SELECTED_AS_FINAL: 0
- HAS_ADMET_PROFILE: 0
- VALIDATED_BY_EXTERNAL_DATA: 0
- HAS_EXTERNAL_VALIDATION: 0
- SUPPORTED_BY_MODEL: 0
- HAS_DETAILED_MODEL_METRIC: 0
- SUPPORTED_BY_ENSEMBLE: 0
- DERIVED_FROM_SOURCE: 0
- PRODUCED_EVIDENCE: 0
- AUDITS_LOAD_FOR: 0

## Failures
- postgres_validation_not_pass:FAIL
- no_real_graph_data_planned

## Warnings
- no_real_data_for_FinalCandidateEvidence
- no_real_data_for_AdmetEvidence
- no_real_data_for_ExternalValidationEvidence
- no_real_data_for_ModelEvidence
- no_real_data_for_ModelDetailEvidence
- no_real_data_for_EnsembleEvidence
- no_real_data_for_LoadAuditEvidence
- no_real_data_for_Run
