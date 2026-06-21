# LIHC Neo4j Write Plan Preview

- write_plan_status: `PASS_WITH_WARNINGS`
- postgres_validation_status: `PASS`
- project_root_match: `true`
- output_path_guardrail_status: `PASS`
- total_planned_nodes: `676`
- total_planned_relationships: `1576`

## Planned Node Counts
- Disease: 1
- DrugCandidate: 225
- CandidateScore: 225
- TierEvidence: 225
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
- CANDIDATE_FOR: 225
- HAS_CANDIDATE_SCORE: 225
- HAS_TIER: 225
- SELECTED_AS_FINAL: 0
- HAS_ADMET_PROFILE: 0
- VALIDATED_BY_EXTERNAL_DATA: 0
- HAS_EXTERNAL_VALIDATION: 0
- SUPPORTED_BY_MODEL: 0
- HAS_DETAILED_MODEL_METRIC: 0
- SUPPORTED_BY_ENSEMBLE: 0
- DERIVED_FROM_SOURCE: 450
- PRODUCED_EVIDENCE: 450
- AUDITS_LOAD_FOR: 1

## Failures
- (none)

## Warnings
- no_real_data_for_FinalCandidateEvidence
- no_real_data_for_AdmetEvidence
- no_real_data_for_ExternalValidationEvidence
- no_real_data_for_ModelEvidence
- no_real_data_for_ModelDetailEvidence
- no_real_data_for_EnsembleEvidence
- no_real_data_for_LoadAuditEvidence
- no_real_data_for_Run
