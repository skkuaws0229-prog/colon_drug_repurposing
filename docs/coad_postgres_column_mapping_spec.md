# COAD PostgreSQL Column Mapping Specification

## Executive summary
- Disease: `COAD`
- Run ID: `COLON_RELEASE_V1`
- Scope: mapping specification only (no writes)
- Canonical workspace: `C:\work\drug-project`
- Primary candidate sources: `candidate_tiered`, `final_after_admet`
- Held source: `candidate_unique` is unresolved and must not be used for `drug_candidate_result`

**Execute mode remains disabled.**

## Current COAD readiness status
- COAD config/profile/dry-run checks are complete and consistent under the workspace root.
- Mapping design is ready for review.
- Only selected pilot mappings are marked `execute_ready=true` at the specification level.
- Loader execute mode is still disabled globally until unresolved items are closed.

## Required vs optional mappings
| source_file_role | target_table | required_for_pilot | execute_ready | confidence |
|---|---|---:|---:|---|
| candidate_tiered | drug_candidate_tier | 1 | 1 | high |
| final_after_admet | final_candidate_result | 1 | 1 | high |
| external_validation_top30 | external_validation_result | 1 | 1 | high |
| admet_top30 | admet_result | 1 | 1 | high |
| model_performance_summary | model_metric | 0 | 0 | medium |
| model_performance_detailed | model_metric_detailed | 0 | 0 | medium |
| admet_summary | admet_summary | 0 | 0 | low |
| reproducibility_manifest | run_manifest (or source_artifact) | 0 | 0 | low |
| ensemble_source_manifest | ensemble_source_manifest (or source_artifact) | 0 | 0 | low |

## Execute-ready table
| source_file_role | target_table | execute_ready | notes |
|---|---|---:|---|
| candidate_tiered | drug_candidate_tier | 1 | Requires payload fallback for non-standard columns |
| final_after_admet | final_candidate_result | 1 | Requires payload fallback for duplicate/extra fields |
| external_validation_top30 | external_validation_result | 1 | Validation-score semantics must be confirmed |
| admet_top30 | admet_result | 1 | Descriptor columns may remain in payload |
| model_performance_summary | model_metric | 0 | Wide-to-long unpivot required |
| model_performance_detailed | model_metric_detailed | 0 | Target contract and keying not finalized |
| admet_summary | admet_summary | 0 | JSON payload column contract not finalized |
| reproducibility_manifest | run_manifest/source_artifact | 0 | Text payload strategy not finalized |
| ensemble_source_manifest | ensemble_source_manifest/source_artifact | 0 | JSON payload strategy not finalized |

## Required metadata columns
Every mapping must carry:
- `disease`
- `run_id`
- `source_s3_uri`
- `source_file_role`
- `loaded_at`

## Detailed mapping sections

### 1) candidate_tiered -> drug_candidate_tier
- source_file_role: `candidate_tiered`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv`
- source_file_kind: `csv`
- target_table: `drug_candidate_tier`
- source_columns: `canonical_drug_id`, `pred_ic50_mean`, `pred_ic50_std`, `pred_ic50_min`, `pred_ic50_max`, `y_true_mean`, `n_cell_lines`, `drug_name_norm`, `drug_name`, `target`, `target_pathway`, `rank`, `rank_20260428_colon_v2`, `tier_20260428_colon_v2`, `tier_rationale_20260428_colon_v2`
- proposed_target_columns: `canonical_drug_id`, `drug_name`, `drug_name_norm`, `rank`, `disease_specific_rank`, `tier`, `tier_rationale`, `target`, `target_pathway`, `pred_ic50_mean`, `pred_ic50_std`, `pred_ic50_min`, `pred_ic50_max`, `observed_ic50_mean`, `n_cell_lines`, `payload`
- transformation_rules:
  - `rank_20260428_colon_v2 -> disease_specific_rank`
  - `tier_20260428_colon_v2 -> tier`
  - `tier_rationale_20260428_colon_v2 -> tier_rationale`
  - `y_true_mean -> observed_ic50_mean`
  - non-direct fields -> `payload`
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `canonical_drug_id`, `rank`, `source_file_role`)
- required_for_pilot: `true`
- execute_ready: `true`
- confidence: `high`
- unresolved_questions:
  - Are `disease_specific_rank` and `tier_rationale` physical columns or payload-only?
  - Should canonical rank be `rank` or `rank_20260428_colon_v2`?
- reason: primary tiered candidate source with required identifiers.

### 2) final_after_admet -> final_candidate_result
- source_file_role: `final_after_admet`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv`
- source_file_kind: `csv`
- target_table: `final_candidate_result`
- source_columns: includes identifiers/ranks/tier fields plus ADMET and descriptor fields from profile
- proposed_target_columns: `canonical_drug_id`, `drug_name`, `drug_name_norm`, `final_rank`, `ensemble_rank`, `admet_rank`, `tier`, `tier_rationale`, `crc_clinical_tier`, `pred_ic50_mean`, `pred_ic50_std`, `y_true_mean`, `safety_score`, `verdict`, `admet_coverage`, `smiles`, `target`, `target_pathway`, `payload`
- transformation_rules:
  - `step7_final_rank -> final_rank`
  - `rank_20260428_colon_v2 or rank -> ensemble_rank`
  - `rank_admet -> admet_rank`
  - `tier_20260428_colon_v2 -> tier`
  - `tier_rationale_20260428_colon_v2 -> tier_rationale`
  - duplicate fields (`*_2`) and extras -> `payload`
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `canonical_drug_id`, `final_rank`, `source_file_role`)
- required_for_pilot: `true`
- execute_ready: `true`
- confidence: `high`
- unresolved_questions:
  - Should Korean label columns be persisted as payload-only?
  - Is `crc_clinical_tier` a physical column in `final_candidate_result`?
- reason: primary post-ADMET final candidate source for pilot loading.

### 3) external_validation_top30 -> external_validation_result
- source_file_role: `external_validation_top30`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_run/results/colon_top30_drugs_ensemble.csv`
- source_file_kind: `csv`
- target_table: `external_validation_result`
- source_columns: `canonical_drug_id`, `pred_ic50_mean`, `pred_ic50_std`, `pred_ic50_min`, `pred_ic50_max`, `y_true_mean`, `n_cell_lines`, `drug_name_norm`, `drug_name`, `target`, `target_pathway`, `rank`
- proposed_target_columns: `canonical_drug_id`, `drug_name`, `drug_name_norm`, `rank`, `validation_score`, IC50 summary columns, `target`, `target_pathway`, `validation_method`, `payload`
- transformation_rules:
  - `pred_ic50_mean` may map to `validation_score` when no explicit external score exists
  - set `validation_method='ensemble_top30'`
  - extras -> `payload`
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `canonical_drug_id`, `rank`, `source_file_role`)
- required_for_pilot: `true`
- execute_ready: `true`
- confidence: `high`
- unresolved_questions:
  - Confirm semantic definition of `validation_score` in this table.
- reason: ranked external validation candidates required for pilot evidence output.

### 4) admet_top30 -> admet_result
- source_file_role: `admet_top30`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv`
- source_file_kind: `csv`
- target_table: `admet_result`
- source_columns: `rank`, `drug_name`, `canonical_drug_id`, `pred_ic50_mean`, `target`, `target_pathway`, `smiles`, `safety_score`, `verdict`, `n_total_matches`, `n_exact`, `n_close_analog`, `n_analog`, `pains_alert`, `mw`, `logp`, `hbd`, `hba`, `tpsa`, `rotatable_bonds`, `admet_coverage`, `admet_category`
- proposed_target_columns: identifiers, `rank`, `safety_score`, `verdict`, match counts, `pains_alert`, `admet_coverage`, `admet_category`, `smiles`, `payload`
- transformation_rules:
  - descriptor fields (`mw`, `logp`, `hbd`, `hba`, `tpsa`, `rotatable_bonds`) -> payload when no physical columns exist
  - keep ADMET scores/verdict as first-class columns
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `canonical_drug_id`, `rank`, `source_file_role`)
- required_for_pilot: `true`
- execute_ready: `true`
- confidence: `high`
- unresolved_questions:
  - Confirm whether descriptor fields are modeled directly in `admet_result`.
- reason: pilot ADMET decision table source.

### 5) model_performance_summary -> model_metric
- source_file_role: `model_performance_summary`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv`
- source_file_kind: `csv`
- target_table: `model_metric`
- source_columns: `phase`, `model`, `cv5_spearman`, `cv5_gap`, `cv5_overfit`, `groupcv_spearman`, `groupcv_gap`, `groupcv_overfit`, `scaffoldcv_spearman`, `scaffoldcv_gap`, `scaffoldcv_overfit`
- proposed_target_columns: `phase`, `model`, `split`, `metric`, `metric_value`, `payload`
- transformation_rules:
  - unpivot wide metrics into long rows
  - `cv5_spearman -> split=cv5, metric=spearman`
  - `cv5_gap -> split=cv5, metric=gap`
  - `cv5_overfit -> split=cv5, metric=overfit_flag`
  - `groupcv_*` and `scaffoldcv_*` follow same pattern
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `phase`, `model`, `split`, `metric`)
- required_for_pilot: `false`
- execute_ready: `false`
- confidence: `medium`
- unresolved_questions:
  - should boolean overfit metrics be stored in `metric_value`?
- reason: wide-format transformation required before safe writes.

### 6) model_performance_detailed -> model_metric_detailed
- source_file_role: `model_performance_detailed`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step4_model_metrics_full_table.csv`
- source_file_kind: `csv`
- target_table: `model_metric_detailed`
- source_columns: `rank`, `experiment_id`, `phase`, `split`, `category`, `model`, `val_spearman_mean`, `val_spearman_std`, `train_spearman_mean`, `gap_mean`, `n_folds`, `overfitting_flag`, `stability_flag`, `source_file`
- proposed_target_columns: `experiment_id`, `phase`, `family`, `model`, `split`, `metric`, `metric_value`, `rank`, `source_model_dir`, `payload`
- transformation_rules:
  - `category -> family`
  - `source_file -> source_model_dir` (or keep as source_file by schema)
  - either keep metric columns wide or convert to metric/value long format
  - non-modeled columns -> payload
- payload_strategy: `hybrid`
- upsert_key_recommendation: (`disease`, `run_id`, `experiment_id`, `split`, `model`, `source_file_role`)
- required_for_pilot: `false`
- execute_ready: `false`
- confidence: `medium`
- unresolved_questions:
  - final table contract: wide metric columns vs normalized metric/value rows?
  - final unique key for repeated experiments across artifacts?
- reason: mapping is close but schema contract and keying remain open.

### 7) admet_summary -> admet_summary (JSON payload)
- source_file_role: `admet_summary`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json`
- source_file_kind: `json`
- target_table: `admet_summary`
- source_columns: none (JSON document)
- proposed_target_columns: `summary_payload`
- transformation_rules:
  - store full JSON as payload
  - optionally project key summary scalars into explicit columns if supported
- payload_strategy: `json_payload`
- upsert_key_recommendation: (`disease`, `run_id`, `source_file_role`)
- required_for_pilot: `false`
- execute_ready: `false`
- confidence: `low`
- unresolved_questions:
  - exact payload column name/type (`json` vs `jsonb`)?
- reason: weak confidence is acceptable for payload-only summary storage.

### 8) reproducibility_manifest -> run_manifest or source_artifact
- source_file_role: `reproducibility_manifest`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/S3_REPRODUCTION_MANIFEST.md`
- source_file_kind: `text_manifest`
- target_table: `run_manifest` (fallback: `source_artifact`)
- source_columns: none (text/markdown content)
- proposed_target_columns: `manifest_text`, `payload`
- transformation_rules:
  - store full manifest text when table supports it
  - otherwise persist text in payload JSON
- payload_strategy: `text_payload`
- upsert_key_recommendation: (`disease`, `run_id`, `source_s3_uri`, `source_file_role`)
- required_for_pilot: `false`
- execute_ready: `false`
- confidence: `low`
- unresolved_questions:
  - canonical destination table for text manifests?
- reason: optional artifact mapping pending payload design decision.

### 9) ensemble_source_manifest -> ensemble_source_manifest or source_artifact
- source_file_role: `ensemble_source_manifest`
- source_s3_uri: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_asset_manifest.json`
- source_file_kind: `json`
- target_table: `ensemble_source_manifest` (fallback: `source_artifact`)
- source_columns: none (JSON document)
- proposed_target_columns: `manifest_payload`
- transformation_rules:
  - store full JSON as payload
  - optionally mirror key status fields into physical columns
- payload_strategy: `json_payload`
- upsert_key_recommendation: (`disease`, `run_id`, `source_file_role`, `source_s3_uri`)
- required_for_pilot: `false`
- execute_ready: `false`
- confidence: `low`
- unresolved_questions:
  - should this role route to `ensemble_source_manifest` or `source_artifact` for pilot consistency?
- reason: optional manifest source, payload route still open.

## Unresolved candidate_unique decision
- mapping: `candidate_unique -> unresolved`
- decision: do not use for `drug_candidate_result`
- profiled columns:
  - `model`
  - `cv5_mean`
  - `group_mean`
  - `scaffold_mean`
  - `cv5_gap_mean`
  - `group_gap_mean`
  - `scaffold_gap_mean`
  - `cv5_overfit_cnt`
  - `group_overfit_cnt`
  - `scaffold_overfit_cnt`
  - `phase_cov`
  - `generalization_drop`
  - `overfit_total`
  - `ensemble_score`
- reason: no `drug_id`, `drug_name`, or `rank` present.

## Next steps before execute mode
1. Confirm physical columns and payload contracts for pilot-required target tables.
2. Finalize the unpivot implementation and data contract for `model_performance_summary`.
3. Finalize `model_metric_detailed` representation (wide vs long) and conflict keys.
4. Decide artifact routing for `reproducibility_manifest` and `ensemble_source_manifest`.
5. Re-run dry-run mapping review after these decisions.
6. Keep execute mode disabled until all unresolved questions are closed.

**Execute mode remains disabled.**
