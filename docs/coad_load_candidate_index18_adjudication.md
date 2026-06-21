# COAD LOAD_CANDIDATE Index 18 Adjudication

- index: 18
- s3_uri: s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_raw_check_and_collection_report.json
- role: neo4j_graph_candidate;postgres_load_candidate;validation_result_candidate
- target_table: source_artifact
- load_decision: LOAD_CANDIDATE
- reason: compact_structured_result_artifact
- raw_match_type: FILENAME_RAW_CHECK_ONLY
- classification: final/report artifact documenting raw-check results
- recommended_action: KEEP_AS_LOAD_CANDIDATE_WITH_HUMAN_APPROVAL
- preview_execute_flag_present: True
- actual_safety_violation: False
- db_writes_occurred: false

## Rationale
index 18 row is LOAD_CANDIDATE with target_table 'source_artifact' and reason 'compact_structured_result_artifact'. s3_uri does not contain '/raw/' as an independent path segment. The only raw token in the URI is within filename 'external_validation_raw_check_and_collection_report.json'. coad_postgres_load_decision_list.csv contains the same selected_s3_uri as LOAD_CANDIDATE/source_artifact with required_before_execute='none'.

## Decision List Cross-Check
- decision: LOAD_CANDIDATE
- target_table_candidate: source_artifact
- selected_file: 20260428_colon_v2_step6_external_validation_raw_check_and_collection_report.json
- required_before_execute: none
