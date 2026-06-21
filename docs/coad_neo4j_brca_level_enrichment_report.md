# COAD Neo4j BRCA-Level Enrichment Report

- generated_at: 2026-05-19T17:45:17.736266+00:00
- disease: COAD
- execute_requested: false
- execute_performed: false
- overall_status: FAIL

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

## Source PostgreSQL Table Counts

## Dry-run Candidate Projection
- total_candidate_rows_seen: 0
- total_candidate_rows_allowed: 0
- total_candidate_rows_blocked: 0
- drug_candidate_result: seen=0 allowed=0 blocked=0 reasons={}
- drug_candidate_tier: seen=0 allowed=0 blocked=0 reasons={}
- final_candidate_result: seen=0 allowed=0 blocked=0 reasons={}
- admet_result: seen=0 allowed=0 blocked=0 reasons={}

## Loaded Nodes By Type

## Loaded Relationships By Type

## Skipped Rows By Source Table
- drug_candidate_result: 0
- drug_candidate_tier: 0
- final_candidate_result: 0
- admet_result: 0
- external_validation_result: 0
- model_metric: 0
- model_metric_detailed: 0
- ensemble_metric: 0
- source_artifact: 0
- coad_load_audit: 0

## Skipped Rows

## Failures
- POSTGRES_STATUS_NOT_LOADED
- NEO4J_NOT_REACHABLE
- POSTGRES_READ_FAILED:connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?

- CORE_TABLE_EMPTY:drug_candidate_result
- CORE_TABLE_EMPTY:drug_candidate_tier
- CORE_TABLE_EMPTY:final_candidate_result
- CORE_TABLE_EMPTY:admet_result
- CORE_TABLE_EMPTY:external_validation_result

## Warnings

## Table Columns By Source

## Validation Decision
- hard_failures_present
