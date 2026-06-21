# LIHC PostgreSQL Deep-Load Readiness

## Executive Summary
- object_count: `383`
- LOAD_CANDIDATE count: `11`
- NEEDS_REVIEW count: `41`
- EXCLUDED count: `31`
- BRCA parity status: `PARITY_OK`
- recommended next action: `READY_FOR_HUMAN_REVIEW`
- approved candidates manifest: `YES_WITH_HUMAN_REVIEW`

## Missing BRCA-Standard Roles
- none

## Candidate Roles Available
| role | count |
| --- | --- |
| admet_top30 | 1 |
| candidate_tiered | 7 |
| external_validation_top30 | 3 |

## Suspicious LOAD_CANDIDATE Rows
| relative_path | role | target_table | reason |
| --- | --- | --- | --- |
| generated/repro_20260428_liver_step4_v2_20260429/stad_results_20260428_liver_step4_v2/lihc_v2_top30_dedup_tier_summary.json | candidate_tiered | drug_candidate_tier | LIHC candidate path contains STAD token |
| generated/repro_20260428_liver_step4_v2_20260429/stad_results_20260428_liver_step4_v2/lihc_v2_top30_dedup_tiered.csv | candidate_tiered | drug_candidate_tier | LIHC candidate path contains STAD token |
| generated/repro_20260428_liver_step4_v2_20260429/stad_scripts_snapshot/prepare_lihc_v2_top30_dedup_tiered.py | candidate_tiered | drug_candidate_tier | LOAD_CANDIDATE points to source/script file; LIHC candidate path contains STAD token; LOAD_CANDIDATE is not CSV/JSON result artifact |

## LOAD_CANDIDATE Rows
| relative_path | role | target_table | reason |
| --- | --- | --- | --- |
| 0.Image_modal_LIHC/lihc_top30_4tier_classification.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| 0.Image_modal_LIHC/step_im4c/lihc_top30_4tier_classification.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| 0.Image_modal_LIHC/step_im4c/lihc_top30_admet_filtering.csv | admet_top30 | admet_result | matched_brca_standard_role_keywords |
| generated/external_validation/20260428_liver_step4_cv5_gc_sc/top30_external_validation_lihc_cptac_excluded.csv | external_validation_top30 | external_validation_result | matched_brca_standard_role_keywords |
| generated/external_validation/top30_external_validation_lihc_cptac_excluded_v1.csv | external_validation_top30 | external_validation_result | matched_brca_standard_role_keywords |
| generated/repro_20260428_liver_step4_v2_20260429/liver_cancer_external_validation_20260428_liver_step4_v2/top30_external_validation_lihc_cptac_excluded.csv | external_validation_top30 | external_validation_result | matched_brca_standard_role_keywords |
| generated/repro_20260428_liver_step4_v2_20260429/liver_cancer_results_20260428_liver_step4_v2/lihc_v2_top30_dedup_tiered.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| generated/repro_20260428_liver_step4_v2_20260429/stad_results_20260428_liver_step4_v2/lihc_v2_top30_dedup_tier_summary.json | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| generated/repro_20260428_liver_step4_v2_20260429/stad_results_20260428_liver_step4_v2/lihc_v2_top30_dedup_tiered.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| generated/repro_20260428_liver_step4_v2_20260429/stad_scripts_snapshot/prepare_lihc_v2_top30_dedup_tiered.py | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| generated/results/20260428_liver_step4_v2/lihc_v2_top30_dedup_tiered.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |

## Biology Mapping Snapshot
- source_config_path: `C:\work\drug-project\configs\diseases\lihc.yaml`
- driver_genes: `TP53, CTNNB1, AXIN1, ARID1A`
- molecular_subtypes: `iCluster 1/2/3`
- COAD MSI location: `not_applicable`
- COAD MSI preserved: `False`

## Guardrails
- postgres_write_performed: `False`
- neo4j_write_performed: `False`
- execute_postgres_flag_run: `False`
- execute_neo4j_flag_run: `False`
- execute_all_flag_run: `False`
- loaders_run: `False`
- fake_approved_candidates_generated: `False`
- brca_source_of_truth_preserved: `True`
- coad_msi_remains_under_driver_genes: `True`
