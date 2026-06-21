# Multi-Cancer Input File Validation Report

- generated_at: 2026-05-24T18:57:34.304776+00:00
- scope: non-BRCA disease input file mapping validation
- safety: metadata + small header/sample only; no PostgreSQL/Neo4j writes

## Disease-level summary

| disease | listed_objects | include | hold | exclude | avg_confidence | disease_confidence |
|---|---:|---:|---:|---:|---:|---|
| COAD | 437 | 7 | 397 | 33 | 75.44 | medium |
| LUNG | 3329 | 4 | 779 | 2546 | 73.89 | medium |
| LIHC | 383 | 5 | 340 | 38 | 72.86 | medium |
| PAAD | 541 | 5 | 269 | 267 | 76.5 | medium |
| HNSC | 317 | 0 | 261 | 56 | 65.0 | medium |
| STAD | 1017 | 1 | 155 | 861 | 80.0 | medium |

## File-level decision table

| disease | file_name | inferred_role | yaml_key | score | decision | reason |
|---|---|---|---|---:|---|---|
| COAD | 20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json | admet_summary | admet_summary | 100 | include | high_confidence_mapping |
| COAD | S3_REPRODUCTION_MANIFEST.md | reproducibility_manifest | reproducibility_manifest | 98 | include | high_confidence_mapping |
| COAD | 20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv | model_performance_summary | model_performance_summary | 85 | include | high_confidence_mapping |
| COAD | 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv | candidate_tiered | candidate_tiered | 85 | include | high_confidence_mapping |
| COAD | 20260428_colon_v2_step7_summary_no_admet_tier_sort_only.json | admet_summary | - | 80 | include | high_confidence_mapping |
| COAD | coad_admet_4tier_cluster_summary.json | admet_summary | - | 80 | include | high_confidence_mapping |
| COAD | 20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv | - | admet_top30 | 70 | include | schema_ok_with_medium_confidence |
| COAD | 20260428_colon_v2_step6_external_validation_asset_manifest.json | - | ensemble_source_manifest | 68 | hold | needs_manual_review |
| COAD | colon_top30_drugs_ensemble.csv | - | external_validation_top30 | 63 | hold | needs_manual_review |
| COAD | 20260428_colon_v2_step4_model_metrics_full_table.csv | - | model_performance_detailed | 55 | hold | needs_manual_review |
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv | - | final_after_admet | 55 | hold | needs_manual_review |
| COAD | 20260428_colon_v2_colon_clinical_trials_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_comprehensive_drug_scores.csv | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_comprehensive_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_cosmic_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_cptac_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_geo_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_prism_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_top30_drugs_ensemble.csv | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_colon_top50_drugs_ensemble.csv | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_pipeline_report_step6_step7.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_prism-repurposing-20q2-primary-screen-cell-line-info.csv | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | 20260428_colon_v2_prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | 20260428_colon_v2_reproduction_protocol.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step4_2abc_15models_metrics_preview.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_execution_gate_decision.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_execution_gate_decision.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_external_validation_clinicaltrials_api_snapshot.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_external_validation_gap_report.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_external_validation_path_mapping.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_external_validation_raw_check_and_collection_report.json | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | 20260428_colon_v2_step6_external_validation_raw_check_and_collection_report.md | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | 20260428_colon_v2_step6_external_validation_surrogate_compound_matching_protocol.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_prism_compound_name_lookup_report.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_readiness_gate_report.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step6_readiness_gate_report.md | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step7_crc_clinical_tier_seed.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json | - | - | 35 | hold | role_unclear |
| COAD | 20260428_colon_v2_step7_top15_crc_tier1234_no_admet_tier_sort_only.csv | - | - | 35 | hold | role_unclear |
| COAD | GPL570_probe_to_gene.json | - | - | 35 | hold | role_unclear |
| COAD | README.md | - | - | 35 | hold | role_unclear |
| COAD | ablation_comparison_full_20260430_v1.csv | - | - | 35 | hold | role_unclear |
| COAD | ablation_report_full_20260430_v1.md | - | - | 35 | hold | role_unclear |
| COAD | ablation_summary_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | all_slide_embeddings_coad_merged_metadata.csv | - | - | 35 | hold | role_unclear |
| COAD | cbio_coadread_driver_mmr_mutations_20260507.json | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | cbio_coadread_patient_clinical_long_20260507.json | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | cbio_coadread_sample_clinical_long_20260507.json | - | - | 35 | exclude | irrelevant_or_raw_feature_artifact |
| COAD | clinicaltrials_colorectal_cancer_all_studies.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_001.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_002.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_003.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_004.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_005.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_006.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_007.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_008.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_009.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_010.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_011.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_012.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_013.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_014.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_015.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_016.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_017.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_018.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_019.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_020.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_021.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_022.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_023.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_024.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_025.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_026.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_027.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_028.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_029.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_030.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_031.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_032.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_033.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_034.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_035.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_036.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_037.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_038.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_039.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_040.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_041.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_042.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_043.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_044.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_045.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_046.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_047.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_048.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_049.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_050.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_051.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_052.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_053.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_054.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_055.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_056.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_057.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_058.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_059.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_060.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_061.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_062.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_063.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_064.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_065.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_066.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_067.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_068.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_069.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_070.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_071.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_072.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_073.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_074.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_075.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_076.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_077.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_078.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_079.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_080.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_081.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_082.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_083.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_084.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_085.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_086.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_087.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_088.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_089.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_090.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_091.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_092.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_093.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_094.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_095.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_096.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_097.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_098.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_099.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_100.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_101.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_102.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_103.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_104.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_105.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_106.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_page_107.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_colorectal_cancer_summary.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_001.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_001.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_002.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_002.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_003.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_003.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_004.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_004.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_005.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_005.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_006.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_page_006.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_summary.json | - | - | 35 | hold | role_unclear |
| COAD | clinicaltrials_liver_cancer_summary.json | - | - | 35 | hold | role_unclear |
| COAD | cluster_mutation_frequency.csv | - | - | 35 | hold | role_unclear |
| COAD | cluster_statistical_tests.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_cluster_clinical_mutation_table.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_cluster_pathway_profiles.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_drug_cluster_recommendation_report.md | - | - | 35 | hold | role_unclear |
| COAD | coad_final_drug_cluster_recommendations.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_image_modal_downstream_summary.json | - | - | 35 | hold | role_unclear |
| COAD | coad_top30_4tier_classification.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_top30_admet_4tier_classification.csv | - | - | 35 | hold | role_unclear |
| COAD | coad_top30_drug_cluster_hypotheses.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_clinical_trials_matched_drugs.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_clinical_trials_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_comprehensive_drug_scores.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_comprehensive_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_cosmic_matched_drugs.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_cosmic_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_cptac_matched_drugs.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_cptac_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_geo_matched_drugs.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_geo_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_prism_matched_drugs.csv | - | - | 35 | hold | role_unclear |
| COAD | colon_prism_validation_results.json | - | - | 35 | hold | role_unclear |
| COAD | colon_validation_drug_aliases.json | - | - | 35 | hold | role_unclear |
| COAD | context_vocab.json | - | - | 35 | hold | role_unclear |
| COAD | download_records.json | - | - | 35 | hold | role_unclear |
| COAD | download_records.json | - | - | 35 | hold | role_unclear |
| COAD | embedding_qc.json | - | - | 35 | hold | role_unclear |
| COAD | feature_importance_20260430_v1.csv | - | - | 35 | hold | role_unclear |
| COAD | feature_importance_summary_20260430_v1.csv | - | - | 35 | hold | role_unclear |
| COAD | kmeans_silhouette_scores.csv | - | - | 35 | hold | role_unclear |
| COAD | patient_clusters.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-cell-line-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-cell-line-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-primary-mfi.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-primary-mfi.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-collapsed-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-collapsed-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-primary-screen-replicate-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-cell-line-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-cell-line-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-dose-response-curve-parameters.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-dose-response-curve-parameters.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-mfi.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-mfi.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-pooling-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-pooling-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-collapsed-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-collapsed-logfold-change.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-collapsed-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-collapsed-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism-repurposing-20q2-secondary-screen-replicate-treatment-info.csv | - | - | 35 | hold | role_unclear |
| COAD | prism_repurposing_20q2_figshare_metadata.json | - | - | 35 | hold | role_unclear |
| COAD | prism_repurposing_20q2_figshare_metadata.json | - | - | 35 | hold | role_unclear |
| COAD | reranked_top30_baseline_plus_image_20260430_v1.csv | - | - | 35 | hold | role_unclear |
| COAD | reranking_comparison_20260430_v1.csv | - | - | 35 | hold | role_unclear |
| COAD | reranking_cv5_baseline_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_cv5_baseline_plus_image_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_groupcv_baseline_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_groupcv_baseline_plus_image_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_holdout_baseline_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_holdout_baseline_plus_image_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_scaffoldcv_baseline_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | reranking_scaffoldcv_baseline_plus_image_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | step4_run_manifest_20260430_v1.json | - | - | 35 | hold | role_unclear |
| COAD | survival_logrank_pvalue.json | - | - | 35 | hold | role_unclear |
| COAD | tcga_coadread_driver_mmr_mutations.csv | - | - | 35 | hold | role_unclear |

## Why COAD/COLON remains pilot candidate
COAD/COLON remains the pilot because its candidate_tiered/final_after_admet/model_performance_summary patterns are the most consistently discoverable from filenames and schema hints under a single disease family.

## Diseases promotable from medium to high
- COAD: promote after resolving remaining held required pilot role(s).
- LIHC: promote after resolving remaining held required pilot role(s).
- LUNG: promote after resolving remaining held required pilot role(s).
- PAAD: promote after resolving remaining held required pilot role(s).

## Held files and reasons
- role_unclear: 2158 file(s)
- needs_manual_review: 43 file(s)

## Excluded files and reasons
- irrelevant_or_raw_feature_artifact: 3709 file(s)
- hidden_or_editor_artifact: 44 file(s)
- log_file: 38 file(s)
- directory_or_folder_marker: 10 file(s)

## Next action per disease
- COAD: resolve held required roles (final_after_admet) and re-run validation.
- LUNG: resolve held required roles (final_after_admet) and re-run validation.
- LIHC: resolve held required roles (final_after_admet, model_performance_summary) and re-run validation.
- PAAD: resolve held required roles (candidate_tiered, model_performance_summary) and re-run validation.
- HNSC: resolve held required roles (candidate_tiered, final_after_admet, model_performance_summary, admet_detailed or admet_summary, reproducibility_manifest or copied_source_manifest) and re-run validation.
- STAD: resolve held required roles (candidate_tiered, final_after_admet, model_performance_summary, reproducibility_manifest or copied_source_manifest) and re-run validation.
