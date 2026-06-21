# BRCA Neo4j Write Plan Preview

- write_plan_status: `PASS_WITH_WARNINGS`
- postgres_validation_status: `PASS`
- project_root_match: `true`
- output_path_guardrail_status: `PASS`
- total_planned_nodes: `1489`
- total_planned_relationships: `4204`

## Planned Node Counts
- Disease: 1
- DrugCandidate: 150
- CandidateScore: 150
- TierEvidence: 150
- FinalCandidateEvidence: 135
- AdmetEvidence: 30
- ExternalValidationEvidence: 45
- ModelEvidence: 215
- ModelDetailEvidence: 602
- EnsembleEvidence: 9
- SourceArtifact: 1
- LoadAuditEvidence: 0
- Run: 1

## Planned Relationship Counts
- CANDIDATE_FOR: 150
- HAS_CANDIDATE_SCORE: 150
- HAS_TIER: 150
- SELECTED_AS_FINAL: 135
- HAS_ADMET_PROFILE: 30
- VALIDATED_BY_EXTERNAL_DATA: 45
- HAS_EXTERNAL_VALIDATION: 45
- SUPPORTED_BY_MODEL: 215
- HAS_DETAILED_MODEL_METRIC: 602
- SUPPORTED_BY_ENSEMBLE: 9
- DERIVED_FROM_SOURCE: 1336
- PRODUCED_EVIDENCE: 1336
- AUDITS_LOAD_FOR: 1

## Failures
- (none)

## Warnings
- no_real_data_for_LoadAuditEvidence
