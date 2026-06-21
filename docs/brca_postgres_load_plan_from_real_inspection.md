# BRCA PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T19:59:09.517928+00:00`
- disease: `BRCA`
- approved_artifact_count: `8`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/restored_protocol_top30_ev_top15_admet_multiresponse/final_update/final_multiresponse_ev_admet_integrated_ranking.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/restored_protocol_top30_ev_top15_admet_multiresponse/final_update/final_multiresponse_ev_admet_integrated_ranking.pre_protocol_backup.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/brca_directive_top30_tiered_candidates.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/brca_directive_top30_tiered_candidates.json | drug_candidate_tier | candidate_tiered | json | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/step6_metabric_validation/brca_top15_metabric_validated.csv | drug_candidate_tier | candidate_tiered | tabular | drug_id, drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/step6_metabric_validation/brca_top30_metabric_scored.csv | drug_candidate_tier | candidate_tiered | tabular | drug_id, drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/step7_admet_22assay/brca_admet_22assay_top30_detailed.csv | drug_candidate_tier | candidate_tiered | tabular | drug_id, drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/step7_admet_22assay/brca_final15_after_admet.csv | drug_candidate_tier | candidate_tiered | tabular | drug_id, drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
