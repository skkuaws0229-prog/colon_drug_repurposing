# Multi-Cancer S3FS Profile

- generated_at: 2026-05-05T10:18:34.503343+00:00
- profiler_version: v1.0.0

## Summary by Disease

| disease | object_count | inspected_files | candidate_like | admet_like | metric_like | validation_like | manifest_like | warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BRCA | 6786 | 80 | 8 | 1 | 5 | 2 | 4 | 1 |
| COAD | 394 | 80 | 20 | 0 | 17 | 14 | 2 | 1 |
| HNSC | 288 | 80 | 120 | 5 | 25 | 9 | 2 | 1 |
| LIHC | 322 | 80 | 51 | 0 | 28 | 19 | 2 | 1 |
| LUNG | 3299 | 80 | 0 | 0 | 0 | 0 | 0 | 1 |
| PAAD | 516 | 80 | 36 | 16 | 46 | 10 | 3 | 1 |
| STAD | 990 | 80 | 45 | 0 | 4 | 0 | 4 | 1 |

## BRCA (Breast Cancer)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`
- Config release prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/`
- Candidate release prefixes:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_protocol_choi/`
- Likely input files by role:
  - `admet_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cancerwise_top30_top15_unique_drug_summary.csv`
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/drug_interpretation/cluster_drug_pathway_hypothesis.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cancerwise_top30_top15_unique_drug_summary.csv`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/drug_interpretation/cluster_drug_pathway_hypothesis.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cancerwise_top30_top15_unique_drug_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv`
  - `ensemble_validation_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cosmic_and_external_validation_status_v2.csv`
  - `external_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cosmic_and_external_validation_status_v2.csv`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/drug_interpretation/cluster_drug_pathway_hypothesis.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv`
  - `metabric_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cosmic_and_external_validation_status_v2.csv`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/step5_ablation_comparison.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/step5_ablation_comparison.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cancerwise_step5_8_source_map.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/dashboard_extracts/dashboard_cosmic_aware_step6_source_map.csv`
- Important columns found:
  - 0, AGE, AJCC_PATHOLOGIC_TUMOR_STAGE, AJCC_STAGING_EDITION, BRCA1_mut, BRCA1_mut_n, BRCA1_mut_pct, BRCA2_mut, BRCA2_mut_n, BRCA2_mut_pct, BRCA_Basal, BRCA_Her2, BRCA_LumA, BRCA_LumB, BRCA_Normal, BUFFA_HYPOXIA_SCORE, CANCER_TYPE_ACRONYM, DAYS_LAST_FOLLOWUP, DAYS_TO_BIRTH, DAYS_TO_INITIAL_PATHOLOGIC_DIAGNOSIS, DFS_MONTHS, DFS_STATUS, DSS_MONTHS, DSS_STATUS, Drug, Drug_ID, ER_STATUS_BY_IHC, ETHNICITY, FORM_COMPLETION_DATE, GENETIC_ANCESTRY_LABEL, HER2_COPY_NUMBER, HER2_FISH_STATUS, HISTOLOGICAL_SUBTYPE, HISTORY_NEOADJUVANT_TRTYN, I, IA, ICD_10, ICD_O_3_HISTOLOGY, ICD_O_3_SITE, IHC_HER2
- Warnings:
  - Skipped 6706 objects due to max-files-per-disease=80 limit.

## COAD (Colon Adenocarcinoma / Colorectal Cancer)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/`
- Likely input files by role:
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top30_drugs_ensemble.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top50_drugs_ensemble.csv`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top30_drugs_ensemble.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top50_drugs_ensemble.csv`
  - `ensemble_validation_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_cosmic_validation_results.json`
  - `external_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_gap_report.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_asset_manifest.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_clinicaltrials_api_snapshot.json`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top30_drugs_ensemble.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top50_drugs_ensemble.csv`
  - `metabric_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_cosmic_validation_results.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_cptac_validation_results.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_geo_validation_results.json`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_model_metrics_full_table.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_model_metrics_full_table.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_asset_manifest.json`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_asset_manifest.json`
- Important columns found:
  - CANCER_SYNDROME, CHROMOSOME, CHR_BAND, COSMIC_GENE_ID, COSMIC_PHENOTYPE_ID, COSMIC_SAMPLE_ID, COSMIC_STUDY_ID, DRUG_NAME, GENE_SYMBOL, GENOME_START, GENOME_STOP, GENOMIC_MUTATION_ID, GENOMIC_MUT_ALLELE, GENOMIC_WT_ALLELE, GERMLINE, HGVSC, HGVSG, HGVSP, LEGACY_MUTATION_ID, LOH, MOLECULAR_GENETICS, MUTATION_AA, MUTATION_CDS, MUTATION_DESCRIPTION, MUTATION_ID, MUTATION_SOMATIC_STATUS, MUTATION_TYPES, MUTATION_ZYGOSITY, NAME, OTHER_GERMLINE_MUT, OTHER_SYNDROME, PUBMED_PMID, ROLE_IN_CANCER, SAMPLE_NAME, SOMATIC, STRAND, SYNONYMS, TARGET, TARGET_PATHWAY, TIER
- Warnings:
  - Skipped 314 objects due to max-files-per-disease=80 limit.

## HNSC (Head and Neck Squamous Cell Carcinoma)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/`
- Likely input files by role:
  - `admet_result`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_filtered_top15.csv`
  - `admet_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_filtered_top15.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/selection_summary.json`
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv`
  - `ensemble_validation_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/validation_inputs/validation_input_summary.json`
  - `external_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/validation_inputs/external_validation_summary.json`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv`
  - `metabric_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/validation_inputs/validation_input_summary.json`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/sample_features.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/sample_features.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/slim_inputs/train_table.parquet`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/data/processed/model_inputs/train_table.parquet`
- Important columns found:
  - AUC, C3L-00977, C3L-00987, C3L-00994, C3L-00995, C3L-00997, C3L-00999, C3L-01138, C3L-01237, C3L-02617, C3L-02621, C3L-02651, C3L-03378, C3L-04025, C3L-04354, C3L-04791, C3L-04844, C3L-04849, C3N-00204, C3N-00295, C3N-00297, C3N-00299, C3N-00306, C3N-00307, C3N-00498, C3N-00519, C3N-00822, C3N-00825, C3N-00828, C3N-00829, C3N-00846, C3N-00857, C3N-00871, C3N-01337, C3N-01338, C3N-01339, C3N-01340, C3N-01620, C3N-01645, C3N-01752
- Warnings:
  - Skipped 208 objects due to max-files-per-disease=80 limit.

## LIHC (Liver Hepatocellular Carcinoma)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/`
- Likely input files by role:
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `ensemble_validation_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `external_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `metabric_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/slim_inputs/train_table.parquet`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/sample_features.parquet`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/slim_inputs/train_table.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/sample_features.parquet`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/repro_20260428_liver_step4_v2_20260429/liver_processed_snapshot/model_inputs/train_table.parquet`
- Important columns found:
  - DL_MLP_1024_512_256, DL_MLP_2x1024, DL_MLP_2x512, DL_MLP_3x512, DL_MLP_ResidualStyle, DL_MLP_SELU_3x256, DL_MLP_WideNarrow, DRUG_ID, DRUG_NAME, PATHWAY_NAME_NORMALIZED, TARGET, TCGA_DESC, TCGA_DESC_x, TCGA_DESC_y, WEBRELEASE, admet_skipped_by_request, anchor_note_ko, binary_threshold, bundle_stamp, canonical_drug_id, canonical_smiles, cell_line_name, checks, classification, clinical_tier, clinical_tier_label_ko, clinical_trial_mention_count, clinical_trials_has_evidence, clinical_trials_status, cohort, confidence_grade, context_dim, context_smiles, cosmic_cgc_target_matches, cosmic_has_evidence, cosmic_status, cptac_has_evidence, cptac_status, ctxcat__classification__all_tokens_gene_matched, ctxcat__classification__mixed_gene_and_ambiguous
- Warnings:
  - Skipped 242 objects due to max-files-per-disease=80 limit.

## LUNG (Lung Cancer)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - none suggested
- Likely input files by role:
  - none
- Important columns found:
  - Drug, Drug_ID, Passed, RMSE, Remaining, Y, iter, iterations, meta
- Warnings:
  - Skipped 3219 objects due to max-files-per-disease=80 limit.

## PAAD (Pancreatic Ductal Adenocarcinoma)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/`
- Likely input files by role:
  - `admet_result`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/admet/paad/admet_detailed_candidates.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/admet/paad/admet_summary.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/admet/paad/final_drug_candidates.csv`
  - `admet_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/admet/paad/admet_summary.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/admet/20260427_pdac_step4_v1_no_holdout/admet_summary_independent.json`
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/final_comprehensive_candidates.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/tier1_high_confidence.csv`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/final_comprehensive_candidates.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/tier1_high_confidence.csv`
  - `ensemble_validation_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top15_validated.csv`
  - `external_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top15_validated.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/final_comprehensive_candidates.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/tier1_high_confidence.csv`
  - `metabric_validation`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top15_validated.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_paad_lincs/dl_metrics_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_pan_lincs/dl_metrics_summary.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/results/paad/dl/groupcv4_drug/numeric_strong_context_smiles_yapc_lincs/dl_metrics_summary.csv`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/reports/paad/qc_paad_lincs_variant_20260422.json`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/reports/paad/qc_paad_lincs_variant_20260422.json`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/reports/paad/qc_paad_source_to_model_ready_20260421.json`
- Important columns found:
  - AUC, PATHWAY_NAME_NORMALIZED, TCGA_DESC, Z_SCORE, admet, admet_bonus, admet_category, admet_coverage, admet_no_match_assays, admet_qc, all_gctx_gene_features, all_zero_columns_before_constant_filter, all_zero_row_count, assay, assay_count, base_input, base_shape, best_epoch, best_valid_rmse, candidate_count, candidate_source, canonical_drug_id, canonical_smiles, category_counts, cell_id, cell_line_name, classification, clinical_trial_bonus, clinical_trial_mention_count, clinical_trial_supported_top15, completed_at, config, constant_columns_removed, cv, cv_results, data_filters, decompressed_gctx, definition, device, drug__yapc_lincs__AARS
- Warnings:
  - Skipped 436 objects due to max-files-per-disease=80 limit.

## STAD (Stomach Adenocarcinoma / Gastric Cancer)

- S3 parent prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/`
- Config release prefix: `TODO_UNCONFIRMED`
- Candidate release prefixes:
  - none suggested
- Likely input files by role:
  - `candidate_tiered`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC2-dataset.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/dgidb/interactions.tsv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC_DATASET.csv`
  - `candidate_unique`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC2-dataset.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/dgidb/interactions.tsv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC_DATASET.csv`
  - `final_candidate`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC2-dataset.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/dgidb/interactions.tsv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC_DATASET.csv`
  - `model_performance_detailed`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/prism/prism-repurposing-20q2-secondary-screen-dose-response-curve-parameters.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC2-dataset.csv`
  - `model_performance_summary`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/prism/prism-repurposing-20q2-secondary-screen-dose-response-curve-parameters.csv`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/GDSC/GDSC2-dataset.csv`
  - `reproducibility_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/cosmic_stad/20260421/cosmic_stad_actionability_v19_grch37.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/cosmic_stad/20260421/cosmic_stad_actionability_v19_grch37.tsv.gz`
  - `source_manifest`:
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/cosmic_stad/20260421/cosmic_stad_actionability_v19_grch37.parquet`
    - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/additional_sources/cosmic_stad/20260421/cosmic_stad_actionability_v19_grch37.tsv.gz`
- Important columns found:
  - ACTIONABILITY_RANK, ACTIONABILITY_RANK_DESCRIPTION, AUC, BLOOD_RESPONSE, BRD-A00055058-001-01-0::2.325889319::MTS004, BRD-A00077618-236-07-6::0.00061034::HTS002, BRD-A00077618-236-07-6::0.0024414::HTS002, BRD-A00077618-236-07-6::0.00976562::HTS002, BRD-A00077618-236-07-6::0.0390625::HTS002, BRD-A00077618-236-07-6::0.15625::HTS002, BRD-A00077618-236-07-6::0.625::HTS002, BRD-A00077618-236-07-6::10::HTS002, BRD-A00077618-236-07-6::2.5::HTS, BRD-A00077618-236-07-6::2.5::HTS002, BRD-A00100033-001-08-9::2.5::HTS, BRD-A00147595-001-01-5::2.5::HTS, BRD-A00218260-001-03-4::2.5::HTS, BRD-A00376169-001-01-6::2.5::HTS, BRD-A00520476-001-07-4::2.5::HTS, BRD-A00546892-001-02-6::2.5::HTS, BRD-A00578795-001-04-3::2.5::HTS, BRD-A00758722-001-04-9::0.00061034::HTS002, BRD-A00758722-001-04-9::0.0024414::HTS002, BRD-A00758722-001-04-9::0.00976562::HTS002, BRD-A00758722-001-04-9::0.0390625::HTS002, BRD-A00758722-001-04-9::0.15625::HTS002, BRD-A00758722-001-04-9::0.625::HTS002, BRD-A00758722-001-04-9::10::HTS002, BRD-A00758722-001-04-9::2.5::HTS, BRD-A00758722-001-04-9::2.5::HTS002, BRD-A00827783-001-24-6::2.5::HTS, BRD-A00842753-001-01-9::2.5::MTS004, BRD-A00993607-003-24-6::2.5::HTS, BRD-A01098288-001-02-9::2.5::HTS, BRD-A01307728-001-01-4::2.5::MTS007, BRD-A01412266-001-01-0::2.5::HTS, BRD-A01493904-003-12-1::2.5::HTS, BRD-A01563671-001-02-7::2.5::HTS, BRD-A01593789-001-03-1::2.5::HTS, BRD-A01636364-003-15-1::2.5::HTS
- Warnings:
  - Skipped 910 objects due to max-files-per-disease=80 limit.

## What can be loaded next?
- BRCA: already verified.
- Non-BRCA: load candidates depend on manual review of suggested release prefixes and input file mappings.

## Manual review required
s3fs profiling provides file-level suggestions (headers/samples/roles), but final YAML `input_files` mappings must be manually reviewed before PostgreSQL load.
