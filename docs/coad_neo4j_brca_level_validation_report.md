# COAD Neo4j BRCA-Level Validation Report

- generated_at: 2026-05-07T07:39:07.775755+00:00
- disease: COAD
- execute_requested: true
- execute_performed: true
- overall_status: PASS_WITH_WARNINGS

## Node Counts
- Disease_COAD: 1
- DrugCandidate_for_COAD: 45
- CandidateScore: 15
- TierEvidence: 0
- FinalCandidateEvidence: 15
- AdmetEvidence: 75
- ExternalValidationEvidence: 110
- ModelEvidence: 15
- ModelDetailEvidence: 43
- EnsembleEvidence: 1
- SourceArtifact: 35
- LoadAuditEvidence: 34
- Run: 4

## Relationship Counts
- CANDIDATE_FOR: 45
- HAS_CANDIDATE_SCORE: 15
- HAS_TIER: 0
- SELECTED_AS_FINAL: 15
- HAS_ADMET_PROFILE: 75
- VALIDATED_BY_EXTERNAL_DATA: 110
- HAS_EXTERNAL_VALIDATION: 0
- SUPPORTED_BY_MODEL: 0
- HAS_DETAILED_MODEL_METRIC: 43
- SUPPORTED_BY_ENSEMBLE: 0
- DERIVED_FROM_SOURCE: 492
- PRODUCED_EVIDENCE: 699
- AUDITS_LOAD_FOR: 34

## Guardrails
- postgres_write_disabled: True
- neo4j_merge_only: True
- disease_is_coad: True
- postgres_status_in_report: POSTGRES_LOADED
- neo4j_initial_execute_performed: True
- neo4j_initial_status: PASS
- neo4j_reachable: True
- neo4j_reachability_reason: reachable
- biology_config_path: C:\work\drug-project\configs\diseases\colon.yaml
- postgres_driver: psycopg
- blocked_decisions_rejected: True
- no_admet_guardrail: True
