# BRAC/COAD Standard Pipeline

## Reusable Automation Runner

Use the standard reusable runner at `scripts/run_standard_pipeline.ps1` for BRCA/BRAC, COAD, and additional diseases with configured YAML.

- Supported diseases: any disease code with a matching YAML under `configs/diseases/` (for example `brca.yaml`, `coad.yaml`, `stad.yaml`, `paad.yaml`)
- `BRAC` is auto-normalized to canonical `BRCA`
- Supported modes: `DryRun`, `Postgres`, `ValidatePostgres`, `Neo4jPreview`, `Neo4jExecute`, `Neo4jValidate`, `FullSafe`
- `FullSafe` only executes read-only/safe steps: `DryRun`, `ValidatePostgres`, `Neo4jPreview`

### Examples

```powershell
.\scripts\run_standard_pipeline.ps1 -Disease BRAC -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode FullSafe
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode Postgres
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode Neo4jPreview
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode Neo4jExecute
```

## YAML as Source-of-Truth

The runner resolves disease configuration from YAML and uses it as the official source-of-truth for disease code/name, aliases, S3 prefix, local cache path, driver genes, molecular subtypes, and exclude rules.

- If you provide only `-Disease`, the runner auto-resolves `configs/diseases/{canonical_disease_lower}.yaml`
- If you provide `-ConfigPath`, that YAML path is used explicitly
- `BRAC` resolves to canonical `BRCA`, and auto-resolves to `configs/diseases/brca.yaml`
- S3 path and loading policy come from YAML configuration, not manual command arguments
- PostgreSQL and Neo4j writes remain explicit opt-in via `Postgres` and `Neo4jExecute` modes

### Source-of-Truth Examples

```powershell
.\scripts\run_standard_pipeline.ps1 -Disease BRAC -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease COAD -Mode FullSafe
.\scripts\run_standard_pipeline.ps1 -Disease STAD -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease PAAD -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease HNSC -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease LIHC -Mode DryRun
.\scripts\run_standard_pipeline.ps1 -Disease COAD -ConfigPath .\configs\diseases\coad.yaml -Mode DryRun
```
