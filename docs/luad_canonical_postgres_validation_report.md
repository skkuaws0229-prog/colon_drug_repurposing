# LUAD Canonical PostgreSQL Validation Report

- generated_at: `2026-05-10T10:24:42.029704+00:00`
- canonical_plan_file_count: `2`
- already_loaded_canonical_count: `2`
- newly_loaded_canonical_count: `0`
- duplicate_insert_prevented_count: `2`
- final_candidate_result row count: `15`
- drug_candidate_tier row count: `30`
- postgres_validation_status: `PASS`
- reason: `canonical_postgres_validation_passed`

## Guardrails

- disease_code_luad_only: `True`
- no_lung_rows: `{'final_candidate_result': 0, 'drug_candidate_tier': 0}`
- no_laud_rows: `{'final_candidate_result': 0, 'drug_candidate_tier': 0}`
- blocked_path_violation_count: `0`
- no_admet_guardrail_violation_count: `0`
- two_admet_like_files_loaded: `False`
- noncanonical_files_required_for_success: `False`
