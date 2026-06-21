# PAAD PostgreSQL Deep-Load Execute Plan v2 (Dry Run)

## Executive Summary
- disease: `PAAD`
- execute readiness: `READY_FOR_EXECUTE_AFTER_HUMAN_CONFIRMATION_WITH_REVIEW_BACKLOG`
- PostgreSQL write: `not_performed`
- Neo4j write: `not_performed`
- image_modal_asset planned count: `0`
- HAS_IMAGE_MODAL planned count: `0`

## Target Table Planned Row Count v2
- drug_candidate_tier: `30`
- final_candidate_result: `15`
- admet_result: `405`
- model_metric: `72`
- model_metric_detailed: `270`
- external_validation_result: `111`
- source_artifact: `43`
- load_audit: `1`
- image_modal_asset: `0`

## Embedded ADMET Split Rule
- enabled: `True`
- target_table: `admet_result`
- expected_rows: `405`
- drug_identifier: `canonical_drug_id`
- display_drug_name: `drug_name`
- chembl_id_available: `False`
- ADMET columns: `admet_bonus, admet_category, admet_coverage, admet_filter, admet_no_match_assays, caution, info, low_confidence_toxic_signals, measured, minor, no_data, pass, sider_cids, sider_has_match, sider_penalty, sider_serious_examples, sider_serious_keyword_count, sider_side_effect_count, toxicity_flags`

## PAAD v2 Selected LOAD_CANDIDATE / Promotions
| role | target_table | expected_rows | source | relative_path |
| --- | --- | ---: | --- | --- |
| candidate_tiered | drug_candidate_tier | 30 | v1 LOAD_CANDIDATE | 0.Image_modal_PAAD/step_im4c/pdac_top30_4tier_classification.csv |
| final_after_admet | final_candidate_result | 15 | v1 LOAD_CANDIDATE | base_data/20260421_paad/admet/paad/final_drug_candidates.csv |
| embedded_admet_split | admet_result | 405 | ADMET embedded column split review | embedded_admet_split_from_two_paad_candidate_files |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_paad_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_pan_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 12 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_yapc_lincs/dl_fold_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_paad_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_paad_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_pan_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_pan_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric | 3 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_yapc_lincs/ensemble_metrics.csv |
| model_metric_promoted | model_metric_detailed | 9 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_yapc_lincs/individual_metrics.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ml_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ml_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ml_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_paad_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_paad_lincs/ml_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_pan_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_pan_lincs/ml_metrics_summary.csv |
| model_metric_promoted | model_metric_detailed | 24 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_yapc_lincs/ml_fold_metrics.csv |
| model_metric_promoted | model_metric | 6 | NEEDS_REVIEW promotion | base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_yapc_lincs/ml_metrics_summary.csv |
| external_validation_promoted | external_validation_result | 15 | NEEDS_REVIEW promotion | base_data/20260421_paad/external_validation/paad/groupcv4_drug/top15_validated.csv |
| external_validation_promoted | external_validation_result | 50 | NEEDS_REVIEW promotion | base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv |
| external_validation_promoted | external_validation_result | 15 | NEEDS_REVIEW promotion | base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv |
| external_validation_promoted | external_validation_result | 1 | NEEDS_REVIEW promotion | external_validation/20260427_pdac_step4_v1_no_holdout/external_validation_independent_summary.json |
| external_validation_promoted | external_validation_result | 30 | NEEDS_REVIEW promotion | results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv |

## Model Metric Promotion Files
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_paad_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_pan_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_yapc_lincs/dl_fold_metrics.csv` -> `model_metric_detailed` (12 rows)
- `base_data/20260421_paad/results/paad/dl/random4/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_paad_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_paad_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_pan_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_pan_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_yapc_lincs/ensemble_metrics.csv` -> `model_metric` (3 rows)
- `base_data/20260421_paad/results/paad/ensemble/random4/numeric_strong_context_smiles_yapc_lincs/individual_metrics.csv` -> `model_metric_detailed` (9 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_paad_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_paad_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_pan_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_pan_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_yapc_lincs/ml_fold_metrics.csv` -> `model_metric_detailed` (24 rows)
- `base_data/20260421_paad/results/paad/ml/random4/numeric_strong_context_smiles_yapc_lincs/ml_metrics_summary.csv` -> `model_metric` (6 rows)

## External Validation Promotion Files
- `base_data/20260421_paad/external_validation/paad/groupcv4_drug/top15_validated.csv` -> `external_validation_result` (15 rows)
- `base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv` -> `external_validation_result` (50 rows)
- `base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv` -> `external_validation_result` (15 rows)
- `external_validation/20260427_pdac_step4_v1_no_holdout/external_validation_independent_summary.json` -> `external_validation_result` (1 rows)
- `results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv` -> `external_validation_result` (30 rows)

## Review / Excluded Backlog
- NEEDS_REVIEW total: `71`
- promoted from NEEDS_REVIEW: `41`
- kept in review: `30`
- policy: scripts_snapshot/raw/temp/report-only/QC/duplicate ranking/image modal remain excluded or review-only

## Risk Assessment
- LOW: chembl_id absent; canonical_drug_id must be used as source drug identifier.
- MEDIUM: review backlog remains, but promoted model/validation files cover BRCA-standard model and validation table classes.
- LOW: ADMET split creates long-format rows from embedded columns; loader must preserve source file and source column for traceability.

## Guardrails
- postgres_write_performed: `False`
- neo4j_write_performed: `False`
- execute_postgres_flag_run: `False`
- execute_neo4j_flag_run: `False`
- loader_run: `False`
- fake_or_sample_rows_generated: `False`
- image_modal_loaded: `False`
