# PAAD PostgreSQL Deep-Load Readiness

## Executive Summary
- object_count: `541`
- LOAD_CANDIDATE count: `2`
- NEEDS_REVIEW count: `71`
- EXCLUDED count: `271`
- BRCA parity status: `PARITY_OK`
- recommended next action: `READY_FOR_HUMAN_REVIEW`
- approved candidates manifest: `YES_FINAL_AFTER_ADMET_AVAILABLE`

## Missing BRCA-Standard Roles
- none

## Candidate Roles Available
| role | count |
| --- | --- |
| candidate_tiered | 1 |
| final_after_admet | 1 |

## Suspicious LOAD_CANDIDATE Rows
- none

## LOAD_CANDIDATE Rows
| relative_path | role | target_table | reason |
| --- | --- | --- | --- |
| 0.Image_modal_PAAD/step_im4c/pdac_top30_4tier_classification.csv | candidate_tiered | drug_candidate_tier | matched_brca_standard_role_keywords |
| base_data/20260421_paad/admet/paad/final_drug_candidates.csv | final_after_admet | final_candidate_result | matched_brca_standard_role_keywords |

## Biology Mapping Snapshot
- source_config_path: `C:\work\drug-project\configs\diseases\paad.yaml`
- driver_genes: `KRAS, TP53, CDKN2A, SMAD4`
- molecular_subtypes: `Basal-like, Classical`
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
