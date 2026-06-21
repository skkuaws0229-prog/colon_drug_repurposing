# LUAD Neo4j Validation Report

- neo4j_validation_status: `PASS`
- execute_performed: `true`
- output_path_guardrail_status: `PASS`

## Node Counts
- Disease: 1
- DrugCandidate: 30
- CandidateScore: 120
- TierEvidence: 150
- FinalCandidateEvidence: 0
- AdmetEvidence: 0
- ExternalValidationEvidence: 0
- ModelEvidence: 0
- ModelDetailEvidence: 0
- EnsembleEvidence: 0
- SourceArtifact: 51
- LoadAuditEvidence: 0
- Run: 1

## Relationship Counts
- CANDIDATE_FOR: 30
- HAS_CANDIDATE_SCORE: 120
- HAS_TIER: 150
- SELECTED_AS_FINAL: 0
- HAS_ADMET_PROFILE: 0
- VALIDATED_BY_EXTERNAL_DATA: 0
- HAS_EXTERNAL_VALIDATION: 0
- SUPPORTED_BY_MODEL: 0
- HAS_DETAILED_MODEL_METRIC: 0
- SUPPORTED_BY_ENSEMBLE: 0
- DERIVED_FROM_SOURCE: 1797
- PRODUCED_EVIDENCE: 120
- AUDITS_LOAD_FOR: 1

## Guardrail Checks
- cross_disease_mismatch_count: 0
- duplicate_risk_count: 0

## Errors
- (none)
