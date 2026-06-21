# HNSC PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T20:11:43.380379+00:00`
- disease: `HNSC`
- approved_artifact_count: `17`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_filtered_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_selected_drugs_top50.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/positive_controls.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/repurposing_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/repurposing_top15.json | final_candidate_result | final_after_admet | json | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/step6_all_drugs.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/results/20260427_hnsc_step4_v1/step7_top15_hnsc_extended.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/results/20260427_hnsc_step4_v1/step7_top30_hnsc_extended.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/results/20260427_hnsc_step4_v1/top30_tier1234_fixed_hnsc.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_candidate_gate.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/hnsc_admet_filtered_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/hnsc_selected_drugs_top50.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/positive_controls.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/repurposing_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/repurposing_top15.json | final_candidate_result | final_after_admet | json | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/workspace_seed/base_data/20260421_hnsc/outputs/final_selection/step6_hnsc/step6_all_drugs.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
