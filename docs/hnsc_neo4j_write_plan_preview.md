# HNSC Neo4j Write Plan Preview

- write_plan_status: `PASS_WITH_WARNINGS`
- postgres_validation_status: `PASS`
- project_root_match: `true`
- output_path_guardrail_status: `PASS`
- total_planned_nodes: `994`
- total_planned_relationships: `2830`

## Planned Node Counts
- Disease: 1
- DrugCandidate: 75
- CandidateScore: 75
- TierEvidence: 75
- FinalCandidateEvidence: 768
- AdmetEvidence: 0
- ExternalValidationEvidence: 0
- ModelEvidence: 0
- ModelDetailEvidence: 0
- EnsembleEvidence: 0
- SourceArtifact: 0
- LoadAuditEvidence: 0
- Run: 0

## Planned Relationship Counts
- CANDIDATE_FOR: 75
- HAS_CANDIDATE_SCORE: 75
- HAS_TIER: 75
- SELECTED_AS_FINAL: 768
- HAS_ADMET_PROFILE: 0
- VALIDATED_BY_EXTERNAL_DATA: 0
- HAS_EXTERNAL_VALIDATION: 0
- SUPPORTED_BY_MODEL: 0
- HAS_DETAILED_MODEL_METRIC: 0
- SUPPORTED_BY_ENSEMBLE: 0
- DERIVED_FROM_SOURCE: 918
- PRODUCED_EVIDENCE: 918
- AUDITS_LOAD_FOR: 1

## Failures
- (none)

## Warnings
- no_real_data_for_AdmetEvidence
- no_real_data_for_ExternalValidationEvidence
- no_real_data_for_ModelEvidence
- no_real_data_for_ModelDetailEvidence
- no_real_data_for_EnsembleEvidence
- no_real_data_for_LoadAuditEvidence
- no_real_data_for_Run
