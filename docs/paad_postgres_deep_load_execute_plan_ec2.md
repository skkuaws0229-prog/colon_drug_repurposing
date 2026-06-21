# PAAD PostgreSQL Deep-Load Execute Plan (Dry Run)

## Executive Summary
- disease: `PAAD`
- selected LOAD_CANDIDATE files: `2`
- BRCA parity status: `PARITY_OK`
- execute readiness: `READY_FOR_EXECUTE_AFTER_HUMAN_CONFIRMATION`
- PostgreSQL write: `not_performed`
- Neo4j write: `not_performed`

## Selected LOAD_CANDIDATE Files
| role | target_table | expected_rows | header_columns | compatibility | relative_path |
| --- | --- | ---: | ---: | --- | --- |
| candidate_tiered | drug_candidate_tier | 30 | 84 | PASS | 0.Image_modal_PAAD/step_im4c/pdac_top30_4tier_classification.csv |
| final_after_admet | final_candidate_result | 15 | 13 | PASS | base_data/20260421_paad/admet/paad/final_drug_candidates.csv |

## Target Table Planned Row Count
- drug_candidate_tier: `30`
- final_candidate_result: `15`
- admet_result: `0`
- external_validation_result: `0`
- model_metric: `0`
- source_artifact: `2`
- load_audit: `1`

## Role Mapping
- candidate_tiered: `drug_candidate_tier` (30 rows)
- final_after_admet: `final_candidate_result` (15 rows)

## Mapping Confirmation
- candidate: candidate_tiered -> drug_candidate_tier
- final_after_admet: final_after_admet -> final_candidate_result
- admet: no admet_top30 LOAD_CANDIDATE row; ADMET attributes are present in final_after_admet/candidate_tiered columns and should not be separately loaded into admet_result in this step
- model: no model_metric LOAD_CANDIDATE row planned
- validation: no external_validation LOAD_CANDIDATE row planned
- result_artifact: register both LOAD_CANDIDATE files as source_artifact/load audit if the BRCA-standard loader does artifact registry as part of execute

## Excluded / Review Summary
- needs_review_count: `71`
- excluded_count: `271`
- skipped_non_candidate_count: `197`
- needs_review_role_count: `{'unclassified': 71}`
- excluded_policy_note: `raw/reference/glue/scripts_snapshot exclusions remain governed by source classification manifest; no excluded/review files are planned for execute`

## Risk Assessment
- MEDIUM: 71 NEEDS_REVIEW artifacts remain outside this execute plan
- LOW: No ADMET/model/validation row-level LOAD_CANDIDATE files are available; only final_after_admet and candidate_tiered are planned for this PAAD PostgreSQL execute.

## Guardrails
- postgres_write_performed: `False`
- neo4j_write_performed: `False`
- execute_postgres_flag_run: `False`
- execute_neo4j_flag_run: `False`
- execute_all_flag_run: `False`
- loader_run: `False`
- fake_or_sample_rows_generated: `False`
- lihc_write_performed: `False`
