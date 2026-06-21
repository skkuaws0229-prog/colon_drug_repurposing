# Multi-Cancer Validator Improvement Implementation Summary

- Date: 2026-05-06
- Scope: Safe filename-role heuristic improvements only
- Updated file: `scripts/config/validate_multi_cancer_input_files.py`
- Not changed: scoring rubric, disease-level confidence thresholds, required pilot role checks, YAML mappings, BRCA logic

## 1) Exactly Which Filename Patterns Were Added

Added to role inference rules (`ROLE_RULES`) only:

- `candidate_tiered`
  - `top30 + tiered + candidate` (existing, kept)
  - `top30 + tiered`
  - `top30 + tier1234`
  - `top30 + tier1 + tier2 + tier3 + tier4`

- `final_after_admet`
  - `final15` (existing, kept)
  - `final + after + admet` (existing, kept)
  - `top15 + admet + pass`
  - `top15 + admet + filtered`
  - `top15 + admet + with + vt`
  - `top15 + admet + with + admet`
  - `top15 + drugs + with + admet`

- `model_performance_summary`
  - `model + performance + summary` (existing, kept)
  - `metrics + summary`
  - `metrics + checklist`
  - `overfit + table`

- `copied_source_manifest`
  - `copied_source_manifest` (existing, kept)
  - `copied + source + manifest` (existing, kept)
  - `source + manifest`

- `reproducibility_manifest`
  - `reproducibility_manifest` (existing, kept)
  - `repro + manifest` (existing, kept)
  - `reproducibility + manifest` (existing, kept)
  - `reproduction + manifest`
  - `s3 + upload + manifest`

## 2) Files Changed From Hold to Include

After re-run, the following files changed `hold -> include` (deduplicated by disease + file name):

| disease | file_name | inferred_role_after | score_after |
|---|---|---|---:|
| COAD | `20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv` | `model_performance_summary` | 85 |
| COAD | `20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv` | `candidate_tiered` | 85 |
| COAD | `S3_REPRODUCTION_MANIFEST.md` | `reproducibility_manifest` | 98 |
| HNSC | `hnsc_admet_filtered_top15.csv` | `final_after_admet` | 85 |
| HNSC | `metrics_summary.json` | `model_performance_summary` | 85 |
| HNSC | `top30_tier1234_fixed_hnsc.csv` | `candidate_tiered` | 85 |
| LIHC | `lihc_v2_top30_dedup_tiered.csv` | `candidate_tiered` | 85 |
| LUNG | `lung_32_metrics_checklist.csv` | `model_performance_summary` | 85 |
| LUNG | `lung_s3_upload_manifest_20260429.md` | `reproducibility_manifest` | 98 |
| LUNG | `lung_step6_top30_tiered_candidates.csv` | `candidate_tiered` | 85 |
| PAAD | `step7_top15_pdac_admet_with_vt.csv` | `final_after_admet` | 85 |

## 3) Before/After Disease Confidence Scores

| disease | before_score | before_confidence | after_score | after_confidence |
|---|---:|---|---:|---|
| COAD | 65.44 | medium | 75.44 | medium |
| LUNG | 63.89 | medium | 73.89 | medium |
| LIHC | 68.57 | medium | 72.86 | medium |
| PAAD | 73.17 | medium | 76.50 | medium |
| HNSC | 56.62 | low | 67.88 | medium |
| STAD | 77.50 | medium | 77.50 | medium |

## 4) Diseases Promoted to High

No disease was promoted to `high`.

## 5) Diseases Still Blocked and Why

- COAD: still `medium`; `final_after_admet` remains uncertain/hold in required pilot role set.
- LUNG: still `medium`; `final_after_admet` remains uncertain/hold in required pilot role set.
- LIHC: still `medium`; required roles still missing (`final_after_admet`, `model_performance_summary`).
- PAAD: still `medium`; required role still missing (`candidate_tiered`).
- HNSC: improved to `medium` from `low`, but required manifest role still missing.
- STAD: still `medium`; required roles missing (`candidate_tiered`, `model_performance_summary`, `reproducibility/copy manifest`).

## 6) Safety and Operational Gate

Database loading is still blocked.

- No PostgreSQL loading is allowed yet.
- No Neo4j loading is allowed yet.
- Loading can be considered only if at least one disease reaches `high` confidence and passes dry-run validation.
