# STAD PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T20:06:54.789096+00:00`
- disease: `STAD`
- approved_artifact_count: `2`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/workspace_git_snapshot/results/lihc_step7_final_top15_tier4.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/workspace_git_snapshot/results/stad_final_top15.csv | final_candidate_result | final_after_admet | tabular | drug_name, canonical_drug_id, rank |  | HIGH | final_candidate_columns_detected |
