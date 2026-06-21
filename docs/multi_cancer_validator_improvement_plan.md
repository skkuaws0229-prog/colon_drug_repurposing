# Multi-Cancer Validator Improvement Plan

- Date: 2026-05-06
- Scope: Read-only review of generated blocker reports only
- Source files:
  - `outputs/config_validation/multi_cancer_validation_blockers.csv`
  - `outputs/config_validation/multi_cancer_missing_required_roles.csv`
  - `outputs/config_validation/multi_cancer_hold_reason_summary.csv`
  - `docs/multi_cancer_validation_blockers.md`
- Hard safety rule: No PostgreSQL load, no Neo4j load, no YAML edits yet, no BRCA logic changes

## 1) Disease-Level Blocker Classification

| disease | current_confidence | current_score | primary_blocker_class | evidence summary | likely_high_after_safe_validator_improvement |
|---|---|---:|---|---|---|
| COAD | medium | 65.44 | `filename_heuristic_gap` | Required pilot slots are all present as include/hold; key required files remain hold with `expected_only` + `needs_manual_review`. | Yes (likely) |
| LUNG | medium | 63.89 | `filename_heuristic_gap` | Same pattern as COAD: required pilot slots present as include/hold, but multiple required files are held due to role inference weakness. | Yes (likely) |
| LIHC | medium | 68.57 | `missing_required_role` | `final_after_admet` and `model_performance_summary` are `missing` in required-role matrix. | No (until missing roles found) |
| PAAD | medium | 73.17 | `missing_required_role` | `candidate_tiered`, `model_performance_summary`, and manifest slot are `missing`. | No (until missing roles found) |
| STAD | medium | 77.50 | `missing_required_role` | `candidate_tiered`, `model_performance_summary`, and manifest slot are `missing`. | No (until missing roles found) |
| HNSC | low | 56.62 | `missing_required_role` | Repro/copied manifest slot is `missing`; also many `role_unclear` holds remain. | No |

Notes:
- `ambiguous_file_role` is a major secondary blocker (high-volume `role_unclear`) across all diseases.
- `column_alias_gap` appears as a secondary blocker for several required hold candidates (missing required column groups).
- `actual_schema_mismatch` is not proven from blocker reports alone.

## 2) Files Held Mainly Due to Filename Heuristic Gaps

These are strong candidates for inclusion after conservative filename-rule improvements (same expected role, schema checked, low-risk profile):

- COAD
  - `S3_REPRODUCTION_MANIFEST.md` (required manifest slot currently hold)
- LUNG
  - `lung_s3_upload_manifest_20260429.md` (required manifest slot currently hold)

High-confidence interpretation:
- Both files are semantically manifest/repro artifacts but are not consistently recognized by current filename-role inference.

## 3) Files Held Mainly Due to Column Alias Gaps (Likely)

These files are mapped to expected required roles but fail strict required-column groups; diagnostics suggest likely alias/field-name adaptation need:

- COAD
  - `20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv` (`candidate_tiered`)
  - `20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv` (`final_after_admet`)
  - `20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv` (`model_performance_summary`)
- LUNG
  - `lung_step6_top30_tiered_candidates.csv` (`candidate_tiered`)
  - `lung_all_admet_pass.csv` (`final_after_admet`)
  - `lung_32_metrics_checklist.csv` (`model_performance_summary`)
- HNSC
  - `top30_tier1234_fixed_hnsc.csv` (`candidate_tiered`)
  - `hnsc_admet_filtered_top15.csv` (`final_after_admet`)
  - `metrics_summary.json` (`model_performance_summary`)
- LIHC
  - `lihc_v2_top30_dedup_tiered.csv` (`candidate_tiered`)
- PAAD
  - `step7_top15_pdac_admet_with_vt.csv` (`final_after_admet`)
- STAD
  - `stad_drugs_with_admet.csv` (`final_after_admet`)

Important caution:
- Keep these as `hold` until column-level evidence confirms semantic equivalence. Do not auto-include based on filename alone.

## 4) Files That Must Remain Hold (Genuine Ambiguity)

Rule:
- Any file group with `inferred_role='-'`, `expected_role='-'`, `decision_reason='role_unclear'` remains hold.

Examples (from current report):
- COAD:
  - `20260428_colon_v2_colon_comprehensive_drug_scores.csv`
  - `20260428_colon_v2_colon_comprehensive_validation_results.json`
  - `20260428_colon_v2_colon_cptac_validation_results.json`
  - `clinicaltrials_colorectal_cancer_page_001.json` (and many paginated clinicaltrials pages)
  - Multiple gate/protocol/report markdown/json artifacts not directly tied to required input roles

Why remain hold:
- Role is not uniquely inferable and/or file purpose is orchestration/reporting/raw-support rather than canonical loader input.

## 5) Specific Filename Patterns to Add (Conservative, Justified)

Add only co-occurrence-based patterns to reduce false positives:

- `candidate_tiered`
  - filename contains `top30` and any of: `tiered`, `tier1234`, `tier1`, `tier2`, `tier3`, `tier4`
- `final_after_admet`
  - filename contains `top15` and `admet` and any of: `pass`, `filtered`, `with_vt`, `with_admet`, `drugs_with_admet`
- `model_performance_summary`
  - filename contains any of: `metrics_summary`, `metrics_checklist`, `overfit_table`
- `reproducibility_manifest` / `copied_source_manifest`
  - filename contains any of: `repro_manifest`, `reproduction_manifest`, `s3_upload_manifest`, `source_manifest`

Safety guard:
- Require at least 2-3 tokens per rule and keep schema check mandatory before `include`.

## 6) Specific Column Aliases to Add (If Justified)

Current blocker reports show missing required column groups, but do not provide enough direct column-level evidence to safely add concrete new aliases without risk.

Safe decision now:
- Do not add blind aliases yet.
- First, use existing sampled-column evidence (already in prior validation output) to confirm exact synonym fields per held candidate.
- Then add only disease-agnostic aliases that repeat across at least 2 diseases.

This is intentionally conservative to avoid misclassification.

## 7) Revalidation Priority

Revalidate in this order after safe validator improvements:

1. COAD
2. LUNG
3. HNSC
4. LIHC
5. PAAD
6. STAD

Rationale:
- COAD/LUNG have the strongest chance to improve via validator logic only (without discovering new required files).
- LIHC/PAAD/STAD/HNSC still have required role slots marked `missing`, so they need file discovery/mapping evidence first.

## 8) Promotion Outlook (No Silent Promotion)

- Likely promotable to `high` after safe validator improvements (and revalidation confirms required slots as include): COAD, LUNG.
- Not promotable by validator tweaks alone (currently missing required roles): LIHC, PAAD, STAD, HNSC.

## 9) Hard Operational Constraint

No non-BRCA disease is allowed for database loading yet.

- No PostgreSQL loading.
- No Neo4j loading.
- No YAML changes until revalidation evidence confirms role-level readiness.
