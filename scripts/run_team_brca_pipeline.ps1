$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

param(
    [ValidateSet("all", "postgres", "kg", "api", "check")]
    [string]$Stage = "all",
    [switch]$SkipPostgres,
    [switch]$SkipKG,
    [switch]$SkipAPI,
    [switch]$StartApiServer,
    [switch]$CheckOnly
)

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
    if (($null -ne $LASTEXITCODE) -and ($LASTEXITCODE -ne 0)) {
        throw "$Context failed with exit code $LASTEXITCODE"
    }
}

function Set-DefaultEnv {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $current = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($current)) {
        Set-Item -Path ("Env:{0}" -f $Name) -Value $Value
    }
}

function Invoke-PwshScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath
    )
    & powershell -ExecutionPolicy Bypass -File $ScriptPath
    Assert-LastExitCode -Context "PowerShell script $ScriptPath"
}

function Invoke-PythonScript {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string]$ScriptPath
    )
    & $PythonExe $ScriptPath
    Assert-LastExitCode -Context "Python script $ScriptPath"
}

function Test-ApiHealth {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/api/health" -Method Get -UseBasicParsing -TimeoutSec 3
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

$startedAt = (Get-Date).ToString("o")
$warnings = New-Object System.Collections.Generic.List[string]
$errors = New-Object System.Collections.Generic.List[string]
$nextSteps = New-Object System.Collections.Generic.List[string]

$postgresStageStatus = "skipped"
$kgStageStatus = "skipped"
$apiStageStatus = "skipped"

$ProjectRoot = $null
$PythonExe = $null
$PsqlExe = $null
$ApiBaseUrl = "http://127.0.0.1:8000"

try {
    Write-Step -Number 1 -Title "Resolve Project Root and Encoding"
    $scriptPath = $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrWhiteSpace($scriptPath)) {
        throw "Cannot resolve script path from invocation context."
    }
    $scriptDir = Split-Path -Parent $scriptPath
    $ProjectRoot = (Resolve-Path -LiteralPath (Join-Path -Path $scriptDir -ChildPath "..")).Path
    Set-Location -LiteralPath $ProjectRoot
    chcp 65001 | Out-Null
    Assert-LastExitCode -Context "chcp 65001"
    $env:PGCLIENTENCODING = "UTF8"

    Write-Step -Number 2 -Title "Set Default Environment Variables"
    Set-DefaultEnv -Name "POSTGRES_HOST" -Value "localhost"
    Set-DefaultEnv -Name "POSTGRES_PORT" -Value "5432"
    Set-DefaultEnv -Name "POSTGRES_DB" -Value "Drug"
    Set-DefaultEnv -Name "POSTGRES_USER" -Value "Drug"
    Set-DefaultEnv -Name "POSTGRES_PASSWORD" -Value "1234"

    Set-DefaultEnv -Name "NEO4J_URI" -Value "bolt://127.0.0.1:7687"
    Set-DefaultEnv -Name "NEO4J_USER" -Value "neo4j"
    Set-DefaultEnv -Name "NEO4J_DATABASE" -Value "neo4j"

    if ([string]::IsNullOrWhiteSpace($env:NEO4J_PASSWORD)) {
        throw "NEO4J_PASSWORD is not set. Please set it before running this pipeline."
    }

    Write-Host "POSTGRES_HOST=$($env:POSTGRES_HOST)"
    Write-Host "POSTGRES_PORT=$($env:POSTGRES_PORT)"
    Write-Host "POSTGRES_DB=$($env:POSTGRES_DB)"
    Write-Host "POSTGRES_USER=$($env:POSTGRES_USER)"
    Write-Host "NEO4J_URI=$($env:NEO4J_URI)"
    Write-Host "NEO4J_USER=$($env:NEO4J_USER)"
    Write-Host "NEO4J_DATABASE=$($env:NEO4J_DATABASE)"

    Write-Step -Number 3 -Title "Check Prerequisites"
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCmd) {
        throw "Python is not available. Install Python 3.11+ and add it to PATH."
    }
    $PythonExe = $pythonCmd.Source
    Write-Host "Python: $PythonExe"

    $preferredPsql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
    if (Test-Path -LiteralPath $preferredPsql) {
        $PsqlExe = $preferredPsql
    } else {
        $psqlCmd = Get-Command psql -ErrorAction SilentlyContinue
        if ($null -eq $psqlCmd) {
            throw "psql is not available. Install PostgreSQL client or add psql to PATH."
        }
        $PsqlExe = $psqlCmd.Source
    }
    Write-Host "psql: $PsqlExe"

    $PostgresLoadScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\db\run_brca_postgres_load.ps1"
    $KgLoadScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\kg\run_brca_kg_load.ps1"
    $ApiRunScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\api\run_brca_api.ps1"
    $ApiCheckScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\api\check_brca_api.py"
    $KgCheckScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\kg\check_brca_kg.py"

    $required = @($PostgresLoadScript, $KgLoadScript, $ApiRunScript, $ApiCheckScript)
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Required script missing: $path"
        }
    }

    $runPostgres = $false
    $runKg = $false
    $runApi = $false
    $runCheck = $false

    switch ($Stage) {
        "all" {
            $runPostgres = -not $SkipPostgres
            $runKg = -not $SkipKG
            $runApi = -not $SkipAPI
        }
        "postgres" { $runPostgres = -not $SkipPostgres }
        "kg" { $runKg = -not $SkipKG }
        "api" { $runApi = -not $SkipAPI }
        "check" { $runCheck = $true }
    }

    if ($runPostgres) {
        Write-Step -Number 4 -Title "Stage postgres"
        Invoke-PwshScript -ScriptPath $PostgresLoadScript
        $postgresStageStatus = "completed"
    } elseif ($Stage -eq "postgres" -and $SkipPostgres) {
        $postgresStageStatus = "skipped_by_flag"
    }

    if ($runKg) {
        Write-Step -Number 5 -Title "Stage kg"
        Invoke-PwshScript -ScriptPath $KgLoadScript
        $kgStageStatus = "completed"
    } elseif ($Stage -eq "kg" -and $SkipKG) {
        $kgStageStatus = "skipped_by_flag"
    }

    if ($runApi) {
        Write-Step -Number 6 -Title "Stage api"
        if ($CheckOnly) {
            Invoke-PythonScript -PythonExe $PythonExe -ScriptPath $ApiCheckScript
            $apiStageStatus = "checked"
        } elseif ($StartApiServer) {
            Write-Host "Starting FastAPI server. This keeps the terminal occupied while the server runs." -ForegroundColor Yellow
            $apiStageStatus = "server_started"
            Invoke-PwshScript -ScriptPath $ApiRunScript
        } else {
            Write-Host "Start API in one terminal, then run check script in another terminal." -ForegroundColor Yellow
            Write-Host ("powershell -ExecutionPolicy Bypass -File {0}" -f $ApiRunScript)
            Write-Host ("python {0}" -f $ApiCheckScript)
            $apiStageStatus = "manual_required"
            $nextSteps.Add("Run API server: powershell -ExecutionPolicy Bypass -File .\scripts\api\run_brca_api.ps1")
            $nextSteps.Add("Run API checks: python .\scripts\api\check_brca_api.py")
        }
    } elseif ($Stage -eq "api" -and $SkipAPI) {
        $apiStageStatus = "skipped_by_flag"
    }

    if ($runCheck) {
        Write-Step -Number 7 -Title "Stage check (PostgreSQL, Neo4j, API-if-running)"

        $criticalSql = @"
SELECT 'drug_candidate_result' AS table_name, COUNT(*) AS row_count FROM drug_candidate_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'drug_candidate_tier', COUNT(*) FROM drug_candidate_tier WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'final_candidate_result', COUNT(*) FROM final_candidate_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'admet_result', COUNT(*) FROM admet_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'external_validation_result', COUNT(*) FROM external_validation_result WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'model_metric', COUNT(*) FROM model_metric WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'model_metric_detailed', COUNT(*) FROM model_metric_detailed WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
UNION ALL
SELECT 'ensemble_metric', COUNT(*) FROM ensemble_metric WHERE disease='BRCA' AND run_id='BRCA_RELEASE_V1'
ORDER BY table_name;
"@

        $countLines = & $PsqlExe `
            -h $env:POSTGRES_HOST `
            -p $env:POSTGRES_PORT `
            -U $env:POSTGRES_USER `
            -d $env:POSTGRES_DB `
            --set=client_encoding=UTF8 `
            -v ON_ERROR_STOP=1 `
            -t -A -F "|" `
            -c $criticalSql
        Assert-LastExitCode -Context "PostgreSQL critical row count check"

        $countMap = @{}
        foreach ($line in $countLines) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            $parts = $line.Split("|")
            if ($parts.Count -eq 2) {
                $countMap[$parts[0].Trim()] = [int]$parts[1].Trim()
            }
        }

        if (($countMap["drug_candidate_result"] -lt 1) -or ($countMap["drug_candidate_tier"] -lt 1)) {
            $warnings.Add("PostgreSQL critical candidate tables look empty.")
        }
        if ($countMap["final_candidate_result"] -lt 1) {
            $warnings.Add("final_candidate_result has zero rows for BRCA_RELEASE_V1.")
        }

        Invoke-PythonScript -PythonExe $PythonExe -ScriptPath $KgCheckScript
        $kgStageStatus = "validated"

        if (Test-ApiHealth -BaseUrl $ApiBaseUrl) {
            Invoke-PythonScript -PythonExe $PythonExe -ScriptPath $ApiCheckScript
            $apiStageStatus = "checked"
        } else {
            $warnings.Add("API server is not running at $ApiBaseUrl. Skipped API check.")
            if ($apiStageStatus -eq "skipped") {
                $apiStageStatus = "skipped_not_running"
            }
        }

        $postgresStageStatus = if ($postgresStageStatus -eq "skipped") { "validated" } else { $postgresStageStatus }
    }

    if ($Stage -eq "all" -and -not $StartApiServer -and -not $CheckOnly) {
        Write-Host ""
        Write-Host "Next commands:" -ForegroundColor Yellow
        Write-Host "powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage api -StartApiServer"
        Write-Host "python .\scripts\api\check_brca_api.py"
        if ($apiStageStatus -eq "skipped" -or $apiStageStatus -eq "manual_required") {
            $apiStageStatus = "manual_required"
        }
    }
}
catch {
    $msg = $_.Exception.Message
    $errors.Add($msg)
    if ($postgresStageStatus -eq "skipped" -and ($Stage -eq "postgres" -or $Stage -eq "all" -or $Stage -eq "check")) {
        $postgresStageStatus = "failed"
    }
    if ($kgStageStatus -eq "skipped" -and ($Stage -eq "kg" -or $Stage -eq "all" -or $Stage -eq "check")) {
        $kgStageStatus = "failed"
    }
    if ($apiStageStatus -eq "skipped" -and ($Stage -eq "api" -or $Stage -eq "all" -or $Stage -eq "check")) {
        $apiStageStatus = "failed"
    }
    Write-Error $msg
    throw
}
finally {
    $completedAt = (Get-Date).ToString("o")
    if ($nextSteps.Count -eq 0) {
        $nextSteps.Add("Run stage check after services are ready: powershell -ExecutionPolicy Bypass -File .\scripts\run_team_brca_pipeline.ps1 -Stage check")
    }

    $rootForReport = $ProjectRoot
    if ([string]::IsNullOrWhiteSpace($rootForReport)) {
        $rootForReport = (Get-Location).Path
    }
    $reportDir = Join-Path -Path $rootForReport -ChildPath "outputs\pipeline_validation"
    if (-not (Test-Path -LiteralPath $reportDir)) {
        New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    }
    $reportPath = Join-Path -Path $reportDir -ChildPath "team_brca_pipeline_report.json"

    $report = [ordered]@{
        started_at = $startedAt
        completed_at = $completedAt
        selected_stage = $Stage
        postgres_target = "$($env:POSTGRES_HOST):$($env:POSTGRES_PORT)/$($env:POSTGRES_DB)"
        neo4j_target = "$($env:NEO4J_URI) (db=$($env:NEO4J_DATABASE))"
        postgres_stage_status = $postgresStageStatus
        kg_stage_status = $kgStageStatus
        api_stage_status = $apiStageStatus
        warnings = @($warnings)
        errors = @($errors)
        next_steps = @($nextSteps)
    }

    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8
    Write-Host ""
    Write-Host "Report written: $reportPath"
}
