# Generic Disease Loader Plan

## Unified Command Pattern (BRCA/COAD Standard)
- Scope: STAD, PAAD, HNSC, LIHC, LUAD, COAD, BRCA (and BRAC alias).
- Single YAML-driven execute entrypoint:
  - `python .\scripts\load\run_disease_execute_pipeline.py --disease STAD`
- Auto-resolved defaults from `--disease`:
  - config: `configs/diseases/{disease_lower}.yaml`
  - plan: `outputs/config_validation/{disease_lower}_postgres_load_plan_from_real_inspection.json`
  - reports:
    - `outputs/config_validation/{disease_lower}_postgres_execute_report.json`
    - `docs/{disease_lower}_postgres_execute_report.md`
    - `outputs/config_validation/{disease_lower}_execute_pipeline_report.json`
    - `docs/{disease_lower}_execute_pipeline_report.md`
- Optional overrides remain available:
  - `--config <path>`
  - `--plan-json <path>`
- BRCA alias policy:
  - `BRAC` is normalized to `BRCA`.

## Safe Mode / Execution Control
- Default run is safe mode (no PostgreSQL writes):
  - `python .\scripts\load\run_disease_execute_pipeline.py --disease STAD`
- Explicit PostgreSQL execute is required:
  - `python .\scripts\load\run_disease_execute_pipeline.py --disease STAD --execute-postgres`
- Explicit read-only mode is also available:
  - `python .\scripts\load\run_disease_execute_pipeline.py --disease STAD --dry-run`
- Safety gates remain unchanged:
  - approved real-inspection plan rows only
  - no `NEEDS_REVIEW`, `DO_NOT_LOAD_EXCLUDED`, `BLOCKED`, `MISSING`, `LOCAL_SYNC_NEEDED`
  - no `no_admet` violations for blocked target tables
  - guarded project root and output path checks

## Why COAD/COLON is the first pilot
- `configs/diseases/colon.yaml` has the highest-confidence non-BRCA release mapping.
- S3 release candidates and key result files are already identified.
- It is the safest path to validate generic loader behavior before wider expansion.

## Why medium/low confidence diseases are not loaded yet
- LIHC, PAAD, HNSC, STAD, and LUNG still include unresolved `TODO_UNCONFIRMED` mappings.
- Premature loading would create noisy provenance and weak repeatability.
- Historical note: older pilot scripts blocked `--execute` outside COAD. The unified runner now stays safe-by-default and requires explicit `--execute-postgres`.

## COAD candidate source decision
- Execute mode is safe-by-default in the unified runner unless `--execute-postgres` is explicitly provided.
- `candidate_unique` is not used for `drug_candidate_result` until a correct unique-candidate file is found.
- Current primary COAD candidate sources are:
  - `candidate_tiered` for tier-level candidate loading.
  - `final_after_admet` for final candidate loading.
- Rationale: column profiling showed the previously mapped `candidate_unique` file contains model/generalization summary fields (`model`, `cv5_mean`, `group_mean`, `scaffold_mean`, `generalization_drop`, `ensemble_score`) rather than drug candidate identifiers (`drug_id`, `drug_name`, `rank`).
## Shared table strategy
- Use existing shared tables only:
  `drug_candidate_result`, `drug_candidate_tier`, `model_metric`, `model_metric_detailed`,
  `ensemble_metric`, `ensemble_source_manifest`, `external_validation_result`,
  `admet_result`, `final_candidate_result`, `admet_summary`, `source_artifact`, `run_manifest`.
- No disease-specific tables are created.
- If a required table is missing, execution stops with a clear error.

## Required metadata fields
Every inserted record carries:
- `disease`
- `run_id`
- `source_s3_uri`
- `source_file_role`
- `loaded_at`

If the target table does not expose dedicated columns for `source_file_role` or `loaded_at`,
the loader writes them into `payload` for provenance consistency.

## Dry-run first workflow
1. Validate load plan:
   `python .\scripts\load\validate_disease_load_plan.py --disease COAD --check-s3 --check-db`
2. Inspect dry-run:
   `python .\scripts\load\load_disease_results_to_postgres.py --disease COAD --dry-run`
3. Review:
   - mapped S3 files
   - table targets
   - preview columns/sample rows
   - schema confidence and warnings

## Column profiling before execute mode
- Run column profiling first to validate sampled schema from each mapped input file:
  `python .\scripts\load\profile_disease_input_columns.py --disease COAD --limit-rows 50`
- Column profiling uses `boto3` directly and does not require `s3fs`.
- Run from `C:\work\drug-project`.
- Review the outputs:
  - `.\outputs\config_validation\coad_input_column_profile.json`
  - `.\docs\coad_input_column_profile.md`
- Use this report to finalize role-to-table column mappings before execute mode is ever enabled.

## PostgreSQL target schema inspection before execute mode
- Run schema introspection for execute-ready mapping candidates:
  `python .\scripts\load\inspect_postgres_target_schema.py --mapping-spec .\outputs\config_validation\coad_postgres_column_mapping_spec.json`
- This inspection is read-only and checks actual target table columns, keys, metadata columns, and payload fallback options.
- Review outputs:
  - `.\outputs\config_validation\coad_postgres_target_schema_report.json`
  - `.\docs\coad_postgres_target_schema_report.md`

## Safe write-plan preview before execute mode
- Build a row-level safe write-plan preview for execute-ready COAD roles without touching PostgreSQL:
  `python .\scripts\load\build_coad_safe_write_plan.py --limit-rows 5`
- This preview transforms sampled source rows into proposed insert rows aligned to actual target columns.
- Review outputs:
  - `.\outputs\config_validation\coad_safe_write_plan_preview.json`
  - `.\docs\coad_safe_write_plan_preview.md`

## Execution workflow
1. Run dry-run and resolve warnings first.
2. Run column profiling and review role confidence diagnostics.
3. Keep execute mode disabled in the scaffold until mappings are reviewed and approved.

## Rollback strategy
- This version does not issue destructive rollback operations.
- To rollback a loaded source safely, remove by (`disease`, `run_id`, `source_s3_uri`) per table.
- Keep rollback SQL as a separate reviewed operation outside loader runtime.

## Known limitations
- Execute mode is intentionally conservative and limited to COAD pilot.
- Some file roles are skipped when schema confidence is low.
- JSON variants beyond current known shapes may require parser extensions.
- Strict column contracts per role are not fully enforced yet.
- Automatic upsert conflict-key tuning is deferred until pilot feedback is complete.

## Subtype-specific drug effect audit before docking viewer
- Before implementing structure docking visualization, run a read-only subtype-specific drug effect audit to confirm real subtype, drug identifier, and response-score availability from discovered disease result files.
- Subtype effect visualization should be implemented and validated first, because it directly communicates disease biology and candidate behavior across molecular subtypes/cell lines.
- Docking visualization should remain a later-stage view that is enabled only after subtype-effect data readiness is confirmed.


