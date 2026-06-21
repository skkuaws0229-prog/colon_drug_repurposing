# Multi-Cancer Parallel Preflight Report

- generated_at: `2026-05-10T17:36:22.055203+00:00`
- dry_run: `true`
- postgres_execute: `not run`
- neo4j_execute: `not run`
- combined_status: `PASS_WITH_WARNINGS`

## Combined Summary
- scanned_object_count: `5587`
- excluded_object_count: `4061`
- approved_postgres_load_candidates: `37`
- blocked_files_count: `0`
- missing_required_roles_count: `12`

## Per Disease Status

| disease | scanned_object_count | excluded_object_count | approved_postgres_load_candidates | blocked_files_count | missing_required_roles | target_postgres_tables | neo4j_nodes | neo4j_relationships | final_status |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| LUAD | 3329 | 2756 | 10 | 0 | 2 | drug_candidate_tier, final_candidate_result | 15 | 38 | PASS_WITH_WARNINGS |
| LIHC | 383 | 87 | 5 | 0 | 3 | drug_candidate_tier | 16 | 35 | PASS_WITH_WARNINGS |
| STAD | 1017 | 852 | 2 | 0 | 2 | drug_candidate_tier, final_candidate_result | 5 | 10 | PASS_WITH_WARNINGS |
| PAAD | 541 | 274 | 3 | 0 | 3 | drug_candidate_tier | 10 | 21 | PASS_WITH_WARNINGS |
| HNSC | 317 | 92 | 17 | 0 | 2 | drug_candidate_tier, final_candidate_result | 24 | 63 | PASS_WITH_WARNINGS |
