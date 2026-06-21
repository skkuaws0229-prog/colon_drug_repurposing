# Non-Cancer BRCA-Equivalent Deep Load Review (No Image, EC2 Dry-run Reclassification)

- generated_at: `2026-05-26T07:33:53.301Z`
- mode: `DRY_RUN_RECLASSIFICATION_ONLY`
- execute_flags_run: `false`
- db_writes_occurred: `false`
- image_modal_asset planned count: `0`
- HAS_IMAGE_MODAL planned count: `0`

## Disease Summary

| disease | existing_selected_count | CORE_DEEP_LOAD | POSTGRES_DETAIL_ONLY | REGISTRY_ONLY | IMAGE_DEFERRED | REVIEW_ONLY | EXCLUDE | deep_load_feasibility |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| RA | 96 | 71 | 2 | 14 | 18 | 2 | 7 | YES_WITH_REVIEW |
| PSORIASIS | 99 | 77 | 2 | 15 | 16 | 3 | 7 | YES_WITH_REVIEW |
| IPF | 36 | 22 | 2 | 9 | 4 | 3 | 4 | YES_WITH_REVIEW |

## Execute Recommendation Order

1. PSORIASIS
2. RA
3. IPF

## RA

- source_s3_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/`
- existing_selected_count: `96`
- planned_postgres_row_count: `null`
- planned_postgres_file_count_for_row_level_load: `73`
- planned_neo4j_node_count_total_by_file_mapping: `142`
- planned_neo4j_relationship_count_total_by_file_mapping: `71`
- image_modal_asset_planned_count: `0`
- has_image_modal_planned_count: `0`
- risk_level: `MEDIUM`

### CORE_DEEP_LOAD Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im1/ra_xray_data_access_status_20260507.md | role=gene_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im3/ra_ramw600_clustering_summary.json | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im3/ra_ramw600_patient_clusters.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im4a/ra_ramw600_cluster_clinical_summary.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im4a/ra_ramw600_cluster_severity_distribution.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im4c/ra_ramw600_cluster_drug_linkage.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/README_REPRODUCE.md | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/details/phase2a_CatBoost_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/details/phase2a_ExtraTrees_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/details/phase2a_LightGBM_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/details/phase2a_RandomForest_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/details/phase2a_XGBoost_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/final_drug_candidates.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/final_drug_candidates_recommended_only.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_CatBoost_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_CatBoost_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_ExtraTrees_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_ExtraTrees_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_LightGBM_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_LightGBM_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_RandomForest_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_RandomForest_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_XGBoost_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/model_outputs/phase2a_XGBoost_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/ra_step7_admet_summary_20260507_v1.csv | role=candidate_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/selection_summary.json | role=candidate_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_CatBoost_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_CatBoost_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_ExtraTrees_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_ExtraTrees_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_LightGBM_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_LightGBM_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_RandomForest_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_RandomForest_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_XGBoost_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/model_outputs/phase2a_XGBoost_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/positive_controls.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/ra_step6_model_top30_validation_report_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/ra_step6_model_validation_summary_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/step6_ra_external_validation_20260507_v1_summary.json | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/validation_inputs/GSE55235_validation_samples_parsed_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/validation_inputs/GSE55457_validation_samples_parsed_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/validation_inputs/GSE89408_validation_samples_parsed_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/validation_inputs/GSE93272_validation_samples_parsed_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/model_input_summary.json | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/step4_ra_feature_engineering_20260507_v1_summary.json | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/metrics_summary.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/metrics_summary.json | role=model_metric | table=disease_model_metric
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/ra_v3_named_drug_baseline_ml_known_drug_ranks_20260507_v1.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/ra_v3_named_drug_baseline_ml_summary_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/ra_v3_named_drug_baseline_ml_summary_20260507_v1.json | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_CatBoost_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_CatBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_ExtraTrees_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_ExtraTrees_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_LightGBM_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_LightGBM_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_RandomForest_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_RandomForest_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_XGBoost_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_XGBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_CatBoost_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_CatBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_ExtraTrees_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_ExtraTrees_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_LightGBM_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_LightGBM_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_RandomForest_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_RandomForest_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_XGBoost_drug_rankings.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2b_XGBoost_top30.csv | role=drug_ranking | table=disease_candidate_result

### POSTGRES_DETAIL_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im4a/ra_ramw600_cluster_statistical_tests.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/ra_v3_named_drug_baseline_ml_fold_metrics_20260507_v1.csv | role=validation_result | table=disease_validation_result

### REGISTRY_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im1/ramw600_data_summary.json | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im2/ra_ramw600_biomedclip_embedding_summary.json | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im5/ra_ramw600_image_modal_summary.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/README.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/S3_REPRODUCTION_MANIFEST.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/admet/step7_ra_admet_filter_20260507_v1_summary.json | role=report_summary | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/manifests/packaged_asset_copy_summary_20260507_ra.json | role=run_manifest | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/ra_reproducibility_manifest_20260507.json | role=run_manifest | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/ra_reproduction_protocol_20260507.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/reports/FINAL_HANDOFF_20260507.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/reports/README.md | role=report_summary | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/reports/psoriasis_ra_baseline_handoff_20260507.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/reports/ra_step6_external_validation_spec_20260507_v1.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/reports/ra_v3_named_drug_baseline_lineage_manifest_20260507_v1.json | role=run_manifest | table=disease_result_artifact

### IMAGE_DEFERRED Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im1/ramw600_patient_manifest_with_svdh.csv | reason=image_modal_manifest_or_index_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im1/ramw600_wrist_manifest_with_svdh.csv | reason=image_modal_manifest_or_index_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im2/ra_ramw600_biomedclip_patient_embedding_index.csv | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im2/ra_ramw600_biomedclip_patient_embeddings.npy | reason=image_embedding_or_binary_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im2/ra_ramw600_biomedclip_wrist_embedding_index.csv | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im2/ra_ramw600_biomedclip_wrist_embeddings.npy | reason=image_embedding_or_binary_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im3/ra_ramw600_cluster_pca.png | reason=image_asset_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im3/ra_ramw600_svdh_by_cluster.png | reason=image_asset_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/drug_features_phase2a.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/drug_features_phase2b.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/labels_y.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/pair_features.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/ra_drug_labels_20260506_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/ra_patient_drug_pair_index_all_20260506_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/ra_x_drug_phase2a_all_20260506_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/ra_x_drug_phase2b_all_20260506_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/ra_x_patient_all_20260506_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/model_inputs/sample_features.parquet | reason=embedding_tabular_deferred_phase

### REVIEW_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im1/ramw600_metadata_parsed.csv | role=unknown_needs_review | table=review_pending
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/0.Image_modal_RA/step_im3/ra_ramw600_kmeans_silhouette.csv | role=unknown_needs_review | table=review_pending

### EXCLUDE Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/external_validation/step6/ra_step6_reference_drug_space_report_20260507_v1.csv | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/ra_compound_name_coverage_report_20260506_v2.json | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/ra_raw_source_manifest_20260507.json | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/ra_step0_source_inventory_20260507_v1.md | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/step1_ra_label_cleanup_normalization_20260506_v2_summary.json | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/step2_ra_disease_signature_20260506_v2_summary.json | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/raw_source/step3_ra_chembl_target_ic50_20260506_v2_summary.json | reason=raw_reference_glue_source_token

## PSORIASIS

- source_s3_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/`
- existing_selected_count: `99`
- planned_postgres_row_count: `null`
- planned_postgres_file_count_for_row_level_load: `79`
- planned_neo4j_node_count_total_by_file_mapping: `154`
- planned_neo4j_relationship_count_total_by_file_mapping: `77`
- image_modal_asset_planned_count: `0`
- has_image_modal_planned_count: `0`
- risk_level: `MEDIUM`

### CORE_DEEP_LOAD Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im3/psoriasis_clustering_summary.json | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im3/psoriasis_image_clusters.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4a/cluster_clinical_label_summary.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4c/psoriasis_4tier_counts.csv | role=candidate_result | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4c/psoriasis_cluster_drug_linkage.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4c/psoriasis_top_drugs_4tier_classification.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_candidate_cases.csv | role=candidate_result | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_candidate_cases_quality_20260509.csv | role=candidate_result | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_step1_summary_20260509.json | role=candidate_result | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/README_REPRODUCE.md | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/details/phase2a_CatBoost_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/details/phase2a_ExtraTrees_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/details/phase2a_LightGBM_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/details/phase2a_RandomForest_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/details/phase2a_XGBoost_admet_details.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/final_drug_candidates.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/final_drug_candidates_recommended_only.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_CatBoost_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_CatBoost_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_ExtraTrees_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_ExtraTrees_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_LightGBM_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_LightGBM_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_RandomForest_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_RandomForest_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_XGBoost_final15_filtered.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/model_outputs/phase2a_XGBoost_top30_admet_annotated.csv | role=validation_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/psoriasis_step7_admet_summary_20260507_v2_baseline.csv | role=candidate_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/selection_summary.json | role=candidate_result | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_CatBoost_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_CatBoost_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_ExtraTrees_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_ExtraTrees_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_LightGBM_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_LightGBM_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_RandomForest_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_RandomForest_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_XGBoost_top15_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/model_outputs/phase2a_XGBoost_top30_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/positive_controls.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/psoriasis_step6_model_top30_validation_report_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/psoriasis_step6_model_validation_summary_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/step6_psoriasis_external_validation_20260507_v2_baseline_summary.json | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/validation_inputs/GSE106992_validation_samples_parsed_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/validation_inputs/GSE117239_validation_samples_parsed_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/validation_inputs/GSE136757_validation_samples_parsed_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/validation_inputs/GSE69967_validation_samples_parsed_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/GSE136757_recovery_summary_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/GSE69967_recovery_summary_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_CatBoost_top15_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_CatBoost_top30_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_ExtraTrees_top15_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_ExtraTrees_top30_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_LightGBM_top15_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_LightGBM_top30_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_RandomForest_top15_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_RandomForest_top30_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_XGBoost_top15_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/model_outputs/phase2a_XGBoost_top30_empirical_validated.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/psoriasis_step6b_model_empirical_validation_summary_20260507_v2_baseline.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6b/step6b_psoriasis_molecular_validation_20260507_v2_baseline_summary.json | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/model_input_summary.json | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/step4_psoriasis_feature_engineering_20260504_v2_summary.json | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/metrics_summary.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/metrics_summary.json | role=model_metric | table=disease_model_metric
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/psoriasis_v2_baseline_ml_known_drug_ranks_20260507_v1.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/psoriasis_v2_baseline_ml_summary_20260507_v1.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_CatBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_ExtraTrees_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_LightGBM_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_RandomForest_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_XGBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2b_CatBoost_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2b_ExtraTrees_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2b_LightGBM_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2b_RandomForest_top30.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2b_XGBoost_top30.csv | role=drug_ranking | table=disease_candidate_result

### POSTGRES_DETAIL_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4a/cluster_statistical_tests.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/psoriasis_v2_baseline_ml_folds_20260507_v1.csv | role=validation_result | table=disease_validation_result

### REGISTRY_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im2/psoriasis_biomedclip_embedding_summary.json | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im5/psoriasis_image_modal_summary.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_step1_summary_20260509.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/README.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/S3_REPRODUCTION_MANIFEST.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/admet/step7_psoriasis_admet_filter_20260507_v2_baseline_summary.json | role=report_summary | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/manifests/packaged_asset_copy_summary_20260507_psoriasis.json | role=run_manifest | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/psoriasis_v2_baseline_ml_summary_20260507_v1.json | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/psoriasis_reproducibility_manifest_20260507.json | role=run_manifest | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/psoriasis_reproduction_protocol_20260507.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/reports/FINAL_HANDOFF_20260507.md | role=run_manifest | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/reports/README.md | role=report_summary | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/reports/psoriasis_ra_baseline_handoff_20260507.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/reports/psoriasis_step0_to_step7_process_20260507.html | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/reports/psoriasis_v2_baseline_lineage_manifest_20260507_v1.json | role=run_manifest | table=disease_result_artifact

### IMAGE_DEFERRED Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im2/psoriasis_biomedclip_image_embedding_index.csv | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im2/psoriasis_biomedclip_image_embeddings.npy | reason=image_embedding_or_binary_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im2/psoriasis_image_manifest.csv | reason=image_modal_manifest_or_index_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im3/psoriasis_biomedclip_kmeans_pca.png | reason=image_asset_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_filter_summary.json | reason=image_modal_manifest_or_index_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_planned_he_slides.csv | reason=image_modal_manifest_or_index_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/drug_features_phase2a.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/drug_features_phase2b.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/labels_y.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/pair_features.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/psoriasis_drug_labels_20260504_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/psoriasis_patient_drug_pair_index_20260504_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/psoriasis_x_drug_phase2a_20260504_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/psoriasis_x_drug_phase2b_20260504_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/psoriasis_x_patient_all_20260504_v2.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_inputs/sample_features.parquet | reason=embedding_tabular_deferred_phase

### REVIEW_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im3/psoriasis_kmeans_silhouette_metrics.csv | role=unknown_needs_review | table=review_pending
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis/step_im4a/severity_association_status.json | role=unknown_needs_review | table=review_pending
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/0.Image_modal_Psoriasis_UNI2/step_im1/histai_psoriasis_strong_positive_he_slides_20260509.csv | role=unknown_needs_review | table=review_pending

### EXCLUDE Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/external_validation/step6/psoriasis_step6_reference_drug_space_report_20260507_v2_baseline.csv | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/data_manifest.psoriasis_raw_20260427.json | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/psoriasis_geo_raw_file_manifest_20260504_v2.csv | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/psoriasis_raw_source_manifest_20260507.json | reason=explicit_do_not_load
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/psoriasis_step0_source_inventory_20260507_v1.md | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/sample_metadata_20260504_v2.csv | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/raw_source/step0_psoriasis_geo_omics_download_20260504_v2_summary.json | reason=raw_reference_glue_source_token

## IPF

- source_s3_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- existing_selected_count: `36`
- planned_postgres_row_count: `null`
- planned_postgres_file_count_for_row_level_load: `24`
- planned_neo4j_node_count_total_by_file_mapping: `44`
- planned_neo4j_relationship_count_total_by_file_mapping: `22`
- image_modal_asset_planned_count: `0`
- has_image_modal_planned_count: `0`
- risk_level: `MEDIUM`

### CORE_DEEP_LOAD Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im3/clustering_optimization.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im3/patient_clusters.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_fvc_cluster_summary_for_tests.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_progression_distribution.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4b/im4b_fvc_prediction_comparison.csv | role=model_metric | table=disease_model_metric
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4c/im4c_cluster_drug_mapping.csv | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4c/im4c_stratification_hypothesis.md | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_admet_22assay_results.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_admet_hard_fail_summary.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_clinical_drug_rank_lookup.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_final_15_tiered.csv | role=drug_ranking | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_top30_clinical_reranked.csv | role=drug_ranking | table=disease_candidate_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/2.External_validation/ev_drug_ranking_GSE110147.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/2.External_validation/ev_drug_ranking_GSE150910.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/2.External_validation/ev_performance_summary.csv | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/2.External_validation/ev_top30_overlap.json | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/3.Model_metadata/drug_target_pairs.csv | role=gene_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/3.Model_metadata/drug_target_summary.csv | role=gene_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/3.Model_metadata/ipf_pipeline_protocol_20260504.md | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/4.Cluster_drug_mapping/im4c_cluster_drug_mapping.csv | role=pathway_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/4.Cluster_drug_mapping/im4c_stratification_hypothesis.md | role=validation_result | table=disease_validation_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/README.md | role=validation_result | table=disease_admet_result

### POSTGRES_DETAIL_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_cluster_descriptive_stats.csv | role=cluster_result | table=disease_evidence_summary
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_progression_contingency_for_chisq.csv | role=cluster_result | table=disease_evidence_summary

### REGISTRY_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im1/step_im1_preprocessing_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im2/step_im2_embedding_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im3/step_im3_clustering_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_clinical_association_summary.csv | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/step_im4a_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4b/step_im4b_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4c/step_im4c_report.md | role=report_summary | table=disease_result_artifact
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im5/ipf_integrated_final_report_20260505.md | role=report_summary | table=disease_admet_result
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/2.External_validation/ev_report.md | role=report_summary | table=disease_result_artifact

### IMAGE_DEFERRED Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im2/ct_clip_embeddings_176.parquet | reason=embedding_tabular_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im3/umap_cluster_plot.png | reason=image_asset_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/cluster_fvc_trajectories.png | reason=image_asset_deferred_phase
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4b/im4b_roc_curves.png | reason=image_asset_deferred_phase

### REVIEW_ONLY Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im1/osic_clinical_baseline.csv | role=unknown_needs_review | table=review_pending
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im4a/im4a_quantitative_statistical_tests.csv | role=unknown_needs_review | table=review_pending
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/3.Model_metadata/ensemble_weights.json | role=unknown_needs_review | table=review_pending

### EXCLUDE Files
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/ | reason=zero-byte
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/ | reason=zero-byte
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/0.Image_modal_IPF/step_im5/ipf_image_modal_all_results.zip | reason=raw_reference_glue_source_token
- s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_reference_drugs.csv | reason=explicit_do_not_load

## BRCA-Equivalent Role Mapping Table

| brca_equivalent_role | postgres_target_table | neo4j_node_classes | neo4j_relationship_classes |
|---|---|---|---|
| candidate_result | disease_candidate_result | Disease,Candidate | HAS_CANDIDATE |
| final_candidate/tier | disease_candidate_result_or_disease_final_candidate_result | Disease,Candidate | HAS_CANDIDATE |
| admet_result | disease_admet_result | Disease,AdmetEvidence | HAS_ADMET_EVIDENCE |
| model_metric | disease_model_metric | Disease,ModelEvidence | HAS_MODEL_EVIDENCE |
| external_validation_result | disease_validation_result | Disease,ValidationEvidence | HAS_VALIDATION_EVIDENCE |
| evidence/KG relation | disease_evidence_summary | Disease,DiseaseEvidence | HAS_EVIDENCE |
| run/provenance summary | disease_result_artifact | Disease,ResultArtifact | HAS_RESULT_ARTIFACT |
| image modal assets/embeddings | deferred_phase_no_load_now | deferred | deferred |
