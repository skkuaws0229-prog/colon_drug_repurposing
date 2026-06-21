# PAAD PostgreSQL Load Plan From Real Inspection

- generated_at: `2026-05-10T20:08:22.256901+00:00`
- disease: `PAAD`
- approved_artifact_count: `3`
- status: `PASS`
- PostgreSQL execute: `not run`
- Neo4j execute: `not run`

| source_s3_uri | target_table | role | parser_strategy | required_columns_found | missing_columns | confidence | reason |
|---|---|---|---|---|---|---|---|
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/knowledge_validation/paad/groupcv4_drug/validation_summary.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/final_comprehensive_candidates.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
| s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/phase5_final_results/paad/groupcv4_drug/tier1_high_confidence.csv | drug_candidate_tier | candidate_tiered | tabular | drug_name, canonical_drug_id, tier |  | HIGH | tier_and_drug_columns_detected |
