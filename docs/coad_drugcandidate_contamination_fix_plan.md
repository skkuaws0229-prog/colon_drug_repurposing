# COAD DrugCandidate Contamination Fix Plan

- generated_at: 2026-05-19T17:53:01.077956+00:00
- mode: read-only diagnostics + code fix (no DB write/delete)

## Existing Contamination
- status: fallback_cached
- total DrugCandidate: 45
- contaminated count: 15
- normal count: 30
- contaminated drug_id list:
  - CatBoost
  - CrossAttention
  - ExtraTrees
  - FTTransformer
  - FlatMLP
  - GAT
  - GraphSAGE
  - LightGBM
  - LightGBM_DART
  - RandomForest
  - ResidualMLP
  - TabNet
  - TabTransformer
  - WideDeep
  - XGBoost
- note: [WinError 10061] 대상 컴퓨터에서 연결을 거부했으므로 연결하지 못했습니다

## Dry-run Forecast (new guard)
- postgres status: fallback_cached_projection
- total rows: 45
- allowed rows: 30
- blocked rows: 15
- blocked reasons: {"MISSING_DRUG_NAME_AND_CANONICAL_ID+MODEL_KEYWORD_IN_DRUG_FIELDS": 15}
- blocked drug_id list:
  - CatBoost
  - CrossAttention
  - ExtraTrees
  - FTTransformer
  - FlatMLP
  - GAT
  - GraphSAGE
  - LightGBM
  - LightGBM_DART
  - RandomForest
  - ResidualMLP
  - TabNet
  - TabTransformer
  - WideDeep
  - XGBoost
- note: connection to server at "localhost" (::1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused (0x0000274D/10061)
	Is the server running on that host and accepting TCP/IP connections?


## Code Changes
- run_coad_execute_pipeline.py: removed model fallback to drug fields and added candidate guard.
- enrich_coad_neo4j_brca_level.py: added candidate guard and blocked model/ensemble -> DrugCandidate linkage.

## Execution Status
- No data deletion or reload performed.
- Re-ingestion/cleanup is required after approval.
