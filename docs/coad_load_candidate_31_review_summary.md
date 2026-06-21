# COAD LOAD_CANDIDATE (31) Review Summary

- total_rows_reviewed: 31
- safe_looking_row_count: 30
- suspicious_row_count: 1
- recommendation: HOLD_FOR_REVIEW
- config_validation_status: passed
- coad_msi_location: driver_genes
- biology_snapshot_consistent_with_config: True
- execute_flags_appeared_in_inputs: True
- db_writes_occurred: False

## Role Counts
- `admet_result_candidate;neo4j_graph_candidate;postgres_load_candidate`: 2
- `admet_result_candidate;neo4j_graph_candidate;postgres_load_candidate;ranking_candidate`: 2
- `model_metric_candidate;postgres_load_candidate`: 2
- `neo4j_graph_candidate;postgres_load_candidate;ranking_candidate`: 4
- `neo4j_graph_candidate;postgres_load_candidate;ranking_candidate;validation_result_candidate`: 2
- `neo4j_graph_candidate;postgres_load_candidate;source_manifest_candidate`: 4
- `neo4j_graph_candidate;postgres_load_candidate;source_manifest_candidate;validation_result_candidate`: 1
- `neo4j_graph_candidate;postgres_load_candidate;validation_result_candidate`: 14

## Target Table Counts
- `admet_result`: 3
- `drug_candidate_result`: 3
- `drug_candidate_tier`: 1
- `ensemble_metric`: 1
- `external_validation_result`: 14
- `final_candidate_result`: 1
- `load_audit`: 4
- `model_metric`: 1
- `model_metric_detailed`: 1
- `source_artifact`: 2

## Suspicious Rows
| index | disease | role | target_table | s3_uri | reason | matched_patterns |
|---:|---|---|---|---|---|---|
| 18 | COAD | neo4j_graph_candidate;postgres_load_candidate;validation_result_candidate | source_artifact | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_raw_check_and_collection_report.json | compact_structured_result_artifact | s3_uri:raw |
