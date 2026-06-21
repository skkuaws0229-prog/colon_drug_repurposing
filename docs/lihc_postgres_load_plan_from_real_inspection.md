# LIHC PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T20:05:49.469042+00:00`
- disease: `LIHC`
- approved_artifact_count: `5`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/lihc_final_top15.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/lihc_final_top15_v1.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/lihc_step7_final_top15_tier4.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/lihc_step7_final_top15_tier4_v1.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/stad_final_top15.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
