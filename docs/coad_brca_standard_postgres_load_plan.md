# COAD BRCA-Standard PostgreSQL Load Plan

## Scope
- disease: `COAD`
- source cache root: `C:\work\drug-project\data_cache\final_data\COAD`
- standard: BRCA-loaded file-role standard only
- mode default: dry-run
- COAD biology guardrails retained:
  - driver_genes: APC, TP53, KRAS, BRAF, PIK3CA, MSI
  - molecular_subtype: CMS1, CMS2, CMS3, CMS4
  - MSI remains under driver_genes (no biomarker creation)

## Role Mapping
| role | brca_artifact | target_table | matched | validation | file |
|---|---|---|---|---|---|
| top30_unique_candidates | `brca_directive_top30_unique_candidates.csv` | `drug_candidate_result` | missing | not_applicable_missing | `` |
| top30_tiered_candidates | `brca_directive_top30_tiered_candidates.csv` | `drug_candidate_tier` | missing | not_applicable_missing | `` |
| model_performance_summary | `brca_model_performance_summary.csv` | `model_metric` | matched | passed | `C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv` |
| model_performance_detailed | `brca_model_performance_detailed.csv` | `model_metric_detailed` | matched | passed | `C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step4_model_metrics_full_table.csv` |
| ensemble_validation_summary | `brca_directive_ensemble_validation_summary.csv` | `ensemble_metric` | missing | not_applicable_missing | `` |
| ensemble_source_manifest | `brca_directive_ensemble_source_manifest.csv` | `ensemble_source_manifest` | matched | passed | `C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step6_external_validation_asset_manifest.json` |
| copied_source_manifest | `copied_source_manifest.csv` | `source_artifact` | missing | not_applicable_missing | `` |
| reproducibility_manifest | `BRCA_reproducibility_manifest_20260428.json` | `run_manifest` | missing | not_applicable_missing | `` |
| external_validation_top30 | `step6_metabric_validation/brca_top30_metabric_scored.csv` | `external_validation_result` | matched | passed | `C:\work\drug-project\data_cache\final_data\COAD\20260428_colon_v2\20260428_colon_v2_step6_external_validation_existing_results\20260428_colon_v2_colon_top30_drugs_ensemble.csv` |
| external_validation_top15 | `step6_metabric_validation/brca_top15_metabric_validated.csv` | `external_validation_result` | missing | not_applicable_missing | `` |
| external_validation_method_a | `step6_metabric_validation/brca_metabric_method_a.csv` | `metabric_method_score` | missing | not_applicable_missing | `` |
| external_validation_method_b | `step6_metabric_validation/brca_metabric_method_b.csv` | `metabric_method_score` | missing | not_applicable_missing | `` |
| admet_top30_detailed | `step7_admet_22assay/brca_admet_22assay_top30_detailed.csv` | `admet_result` | missing | not_applicable_missing | `` |
| final15_after_admet | `step7_admet_22assay/brca_final15_after_admet.csv` | `final_candidate_result` | missing | not_applicable_missing | `` |
| admet_matches | `step7_admet_22assay/brca_admet_22assay_matches.json` | `admet_assay_match` | missing | not_applicable_missing | `` |
| admet_summary | `step7_admet_22assay/brca_admet_22assay_summary.json` | `admet_summary` | missing | not_applicable_missing | `` |

## Summary
- matched_roles_count: 4
- missing_roles_count: 12
- excluded_files_count: 155
- dry_run_status: FAIL
- execute_mode: false
