# LUAD Neo4j Write Plan

- generated_at: `2026-05-10T11:58:10.840771+00:00`
- disease: `LUAD`
- source: `validated PostgreSQL canonical LUAD rows`
- plan_status: `PASS`
- write_plan_row_count: `2`

## Plan Rows

| role | target_table | source_s3_uri | row_count | planned_nodes | planned_relationships |
|---|---|---|---:|---|---|
| final_after_admet | final_candidate_result | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_final_top15.csv | 15 | Disease, DrugCandidate, FinalCandidateEvidence, SourceArtifact, Run | CANDIDATE_FOR, SELECTED_AS_FINAL, DERIVED_FROM_SOURCE, PRODUCED_EVIDENCE |
| candidate_tiered | drug_candidate_tier | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/workspace_reports/lung_step6_package/lung_step6_top30_tiered_candidates.csv | 30 | Disease, DrugCandidate, TierEvidence, SourceArtifact, Run | CANDIDATE_FOR, HAS_TIER, DERIVED_FROM_SOURCE, PRODUCED_EVIDENCE |
