# BRCA Neo4j Validation Report

- neo4j_validation_status: `FAIL`
- execute_performed: `false`
- output_path_guardrail_status: `PASS`

## Node Counts
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

## Relationship Counts
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

## Guardrail Checks
- cross_disease_mismatch_count: 0
- duplicate_risk_count: 0

## Errors
- missing_neo4j_execute_report:C:\work\drug-project\outputs\config_validation\brca_neo4j_execute_report.json
- neo4j_execute_not_performed
- missing_Disease
- missing_DrugCandidate
