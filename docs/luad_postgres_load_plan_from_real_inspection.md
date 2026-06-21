# LUAD PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T20:04:22.950846+00:00`
- disease: `LUAD`
- approved_artifact_count: `10`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_all_admet_pass.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_drugs_with_admet.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_drug_ranking_dedup.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_drug_ranking_with_scores.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_directive_ensemble/lung_directive_ensemble_top30_unseen_drug_finalization_audit.csv | final_candidate_result | final_after_admet | tabular | canonical_drug_id, rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_current_package/lung_final_drug_ranking_dedup.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_current_package/lung_final_drug_ranking_with_scores.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, final_rank |  | HIGH | final_candidate_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_package/lung_step6_top30_tiered_candidates.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_package/lung_step6_top30_tiered_candidates.json | drug_candidate_tier | candidate_tiered | json | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
