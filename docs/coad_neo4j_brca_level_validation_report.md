# COAD Neo4j BRCA-Level Validation Report

- generated_at: 2026-05-19T17:45:17.738271+00:00
- disease: COAD
- execute_requested: false
- execute_performed: false
- overall_status: FAIL

## Node Counts

## Relationship Counts

## Guardrails
- postgres_write_disabled: True
- neo4j_merge_only: True
- disease_is_coad: True
- postgres_status_in_report: UNKNOWN
- neo4j_initial_execute_performed: True
- neo4j_initial_status: PASS
- neo4j_reachable: False
- neo4j_reachability_reason: not_reachable: [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다
- biology_config_path: C:\work\drug-project\configs\diseases\coad.yaml
- blocked_decisions_rejected: True
- no_admet_guardrail: True
