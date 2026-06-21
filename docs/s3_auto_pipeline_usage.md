# S3 Auto Pipeline Usage (Dry-Run)

The orchestrator defaults to safe dry-run behavior and avoids PostgreSQL/Neo4j writes unless explicit execute flags are provided.

## COAD Dry-Run (Inventory/Manifest/Report Only)

```powershell
Set-Location C:\work\drug-project
python .\scripts\pipeline\run_s3_auto_pipeline.py `
  --disease COAD `
  --local-dir "C:\work\drug-project\data_cache\final_data\COAD" `
  --no-run-existing-scripts
```

## BRCA Dry-Run (Inventory/Manifest/Report Only)

```powershell
Set-Location C:\work\drug-project
python .\scripts\pipeline\run_s3_auto_pipeline.py `
  --disease BRCA `
  --local-dir "C:\work\drug-project\data_cache\final_data\BRCA" `
  --no-run-existing-scripts
```

## Optional: Dry-Run While Calling Existing Scripts (COAD)

```powershell
Set-Location C:\work\drug-project
python .\scripts\pipeline\run_s3_auto_pipeline.py `
  --disease COAD `
  --local-dir "C:\work\drug-project\data_cache\final_data\COAD"
```

Notes:
- `--no-run-existing-scripts` limits the run to inventory/manifest/report generation.
- Excluded policy tokens: `raw, reference, curated, glue, shared_inputs, ipf, no_admet, needs_review, do_not_load_excluded, blocked, missing, local_sync_needed`.
- COAD biology mappings (including MSI note) are preserved from `configs/diseases/colon.yaml` without reinterpretation.
