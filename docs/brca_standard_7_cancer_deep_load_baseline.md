# BRCA-Standard 7-Cancer Deep Load Baseline (Read-only)

- execution_mode: `READ_ONLY_BASELINE_DISCOVERY`
- execute_flags_run: `false`
- db_writes_occurred: `false`
- status: `DEFERRED_TO_EC2_READONLY_RUN`

## Disease Load Status Table

| disease | postgres_candidate_count | postgres_final_candidate_count | postgres_admet_count | postgres_model_metric_count | postgres_external_validation_count | postgres_image_modal_count | neo4j_disease_node_count | neo4j_candidate_count | neo4j_model_evidence_count | neo4j_validation_evidence_count | neo4j_admet_evidence_count | neo4j_result_artifact_count | neo4j_image_modal_count | graph_api_status | recommended_next_action |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BRCA | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| COAD | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| LUAD | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| LIHC | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| STAD | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| PAAD | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |
| HNSC | null | null | null | null | null | null | null | null | null | null | null | null | null | not_checked | BLOCKED_NEEDS_REVIEW |

## Aggregate Summary

- diseases_with_postgres_data: ``
- diseases_missing_postgres_data: `BRCA, COAD, LUAD, LIHC, STAD, PAAD, HNSC`
- diseases_with_neo4j_data: ``
- diseases_missing_neo4j_data: `BRCA, COAD, LUAD, LIHC, STAD, PAAD, HNSC`
- diseases_ready_for_graph_api_validation: ``
- diseases_needing_postgres_deep_load: ``
- diseases_needing_neo4j_write_plan: ``

## Notes

- Live DB counts are not fabricated in local preparation.
- Live counts must be produced only by running:
  - [readonly_brca_standard_7_cancer_deep_load_baseline.py](/C:/work/drug-project/scripts/validation/readonly_brca_standard_7_cancer_deep_load_baseline.py)
  on EC2 with read-only DB access.
- COAD MSI preservation is sourced from `configs/diseases/coad.yaml` and must remain under `driver_genes`.
- BRCA remains the source-of-truth standard disease.
