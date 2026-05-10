$ErrorActionPreference = "Stop"

function Write-Step {
    param(
        [Parameter(Mandatory = $true)][int]$Number,
        [Parameter(Mandatory = $true)][string]$Title
    )
    Write-Host ""
    Write-Host ("========== STEP {0}: {1} ==========" -f $Number, $Title) -ForegroundColor Cyan
}

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)][string]$Context
    )
    if ($LASTEXITCODE -ne 0) {
        throw "$Context failed with exit code $LASTEXITCODE"
    }
}

Write-Step -Number 1 -Title "Set Project Root"
$ScriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    throw "Cannot resolve script path from invocation context."
}
$ScriptDir = Split-Path -Parent $ScriptPath
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path -Path $ScriptDir -ChildPath "..\.." )).Path
if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Project root not found: $ProjectRoot"
}
Set-Location -LiteralPath $ProjectRoot
Write-Host "Project root: $(Get-Location)"

Write-Step -Number 2 -Title "Set Console and Client Encoding"
chcp 65001 | Out-Null
Assert-LastExitCode -Context "chcp 65001"
$env:PGCLIENTENCODING = "UTF8"
Write-Host "PGCLIENTENCODING=$($env:PGCLIENTENCODING)"

Write-Step -Number 3 -Title "Set PostgreSQL Environment Variables"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "Drug"
$env:POSTGRES_USER = "Drug"
$env:POSTGRES_PASSWORD = "1234"
Write-Host "POSTGRES_HOST=$($env:POSTGRES_HOST)"
Write-Host "POSTGRES_PORT=$($env:POSTGRES_PORT)"
Write-Host "POSTGRES_DB=$($env:POSTGRES_DB)"
Write-Host "POSTGRES_USER=$($env:POSTGRES_USER)"

Write-Step -Number 4 -Title "Check Required Files"
$PsqlExe = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$MigrationSql = Join-Path -Path $ProjectRoot -ChildPath "scripts\db\002_fix_model_metric_unique_key.sql"
$LoaderPy = Join-Path -Path $ProjectRoot -ChildPath "scripts\db\load_brca_results_to_postgres.py"

$RequiredFiles = @($PsqlExe, $MigrationSql, $LoaderPy)
foreach ($File in $RequiredFiles) {
    if (-not (Test-Path -LiteralPath $File)) {
        throw "Required file missing: $File"
    }
    Write-Host "Found: $File"
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $PythonCommand) {
    $PythonExe = $PythonCommand.Source
} else {
    $FallbackPython = "C:\Users\hjy10\AppData\Local\Programs\Python\Python311\python.exe"
    if (Test-Path -LiteralPath $FallbackPython) {
        $PythonExe = $FallbackPython
    } else {
        throw "Python executable not found. Install Python or add python to PATH."
    }
}
Write-Host "Python: $PythonExe"

Write-Step -Number 5 -Title "Check PostgreSQL Connection"
& $PsqlExe `
    -h $env:POSTGRES_HOST `
    -p $env:POSTGRES_PORT `
    -U $env:POSTGRES_USER `
    -d $env:POSTGRES_DB `
    --set=client_encoding=UTF8 `
    -v ON_ERROR_STOP=1 `
    -c "SELECT current_database(), current_user;"
Assert-LastExitCode -Context "PostgreSQL connection check"

Write-Step -Number 6 -Title "Run Migration (002_fix_model_metric_unique_key.sql)"
& $PsqlExe `
    -h $env:POSTGRES_HOST `
    -p $env:POSTGRES_PORT `
    -U $env:POSTGRES_USER `
    -d $env:POSTGRES_DB `
    --set=client_encoding=UTF8 `
    -v ON_ERROR_STOP=1 `
    -f $MigrationSql
Assert-LastExitCode -Context "Migration apply"

Write-Step -Number 7 -Title "Run BRCA Loader"
& $PythonExe $LoaderPy
Assert-LastExitCode -Context "BRCA loader"

Write-Step -Number 8 -Title "Run Quick Row Count Check"
$RowCountSql = @"
SELECT 'brca_load_audit' AS table_name, COUNT(*) AS row_count FROM brca_load_audit WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'run_manifest', COUNT(*) FROM run_manifest WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'source_artifact', COUNT(*) FROM source_artifact WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'drug_candidate_result', COUNT(*) FROM drug_candidate_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'drug_candidate_tier', COUNT(*) FROM drug_candidate_tier WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'final_candidate_result', COUNT(*) FROM final_candidate_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'admet_result', COUNT(*) FROM admet_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'admet_assay_match', COUNT(*) FROM admet_assay_match WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'admet_summary', COUNT(*) FROM admet_summary WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'external_validation_result', COUNT(*) FROM external_validation_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'metabric_method_score', COUNT(*) FROM metabric_method_score WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'model_metric', COUNT(*) FROM model_metric WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'model_metric_detailed', COUNT(*) FROM model_metric_detailed WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'ensemble_metric', COUNT(*) FROM ensemble_metric WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'ensemble_source_manifest', COUNT(*) FROM ensemble_source_manifest WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
ORDER BY table_name;
"@

& $PsqlExe `
    -h $env:POSTGRES_HOST `
    -p $env:POSTGRES_PORT `
    -U $env:POSTGRES_USER `
    -d $env:POSTGRES_DB `
    --set=client_encoding=UTF8 `
    -v ON_ERROR_STOP=1 `
    -c $RowCountSql
Assert-LastExitCode -Context "Quick row count check"

Write-Step -Number 9 -Title "Optional Check: check_brca_table_counts.py"
$CheckCountsPy = Join-Path -Path $ProjectRoot -ChildPath "scripts\db\check_brca_table_counts.py"
if (Test-Path -LiteralPath $CheckCountsPy) {
    & $PythonExe $CheckCountsPy
    Assert-LastExitCode -Context "check_brca_table_counts.py"
} else {
    Write-Host "Skipped: file not found -> $CheckCountsPy"
}

Write-Step -Number 10 -Title "Optional Check: check_brca_postgres_loaded.py"
$CheckLoadedPy = Join-Path -Path $ProjectRoot -ChildPath "scripts\db\check_brca_postgres_loaded.py"
if (Test-Path -LiteralPath $CheckLoadedPy) {
    & $PythonExe $CheckLoadedPy
    Assert-LastExitCode -Context "check_brca_postgres_loaded.py"
} else {
    Write-Host "Skipped: file not found -> $CheckLoadedPy"
}

Write-Host ""
Write-Host "BRCA PostgreSQL migration + load + validation workflow completed." -ForegroundColor Green
