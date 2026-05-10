[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Disease,

    [Parameter(Mandatory = $true)]
    [ValidateSet("DryRun", "Postgres", "ValidatePostgres", "Neo4jPreview", "Neo4jExecute", "Neo4jValidate", "FullSafe")]
    [string]$Mode,

    [string]$ProjectRoot = "C:\work\drug-project",
    [string]$PythonExe = "C:\Users\hjy10\AppData\Local\Programs\Python\Python311\python.exe",
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Ensure-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function Get-CanonicalDisease {
    param([Parameter(Mandatory = $true)][string]$InputDisease)

    $trimmed = $InputDisease.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        throw "Disease must not be empty."
    }

    $normalized = $trimmed.ToUpperInvariant()
    if ($normalized -eq "BRAC") {
        return "BRCA"
    }
    return $normalized
}

function Ensure-RequiredEnvVars {
    param([Parameter(Mandatory = $true)][string[]]$Names)

    $missing = @()
    foreach ($name in $Names) {
        $envEntry = Get-Item -Path ("Env:{0}" -f $name) -ErrorAction SilentlyContinue
        if ($null -eq $envEntry -or [string]::IsNullOrWhiteSpace($envEntry.Value)) {
            $missing += $name
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing required environment variables: $($missing -join ', ')"
    }
}

function Ensure-RelativeScriptExists {
    param([Parameter(Mandatory = $true)][string]$RelativeScriptPath)

    $trimmed = $RelativeScriptPath -replace '^[.\\/]+', ''
    $fullPath = Join-Path $ProjectRoot $trimmed
    Ensure-PathExists -Path $fullPath -Label "Required script"
}

function Resolve-ConfigPathForDisease {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalDisease,
        [string]$OptionalConfigPath
    )

    if (-not [string]::IsNullOrWhiteSpace($OptionalConfigPath)) {
        $candidate = if ([System.IO.Path]::IsPathRooted($OptionalConfigPath)) {
            $OptionalConfigPath
        }
        else {
            Join-Path $ProjectRoot $OptionalConfigPath
        }
        Ensure-PathExists -Path $candidate -Label "Disease config YAML"
        return (Resolve-Path -LiteralPath $candidate).Path
    }

    $defaultConfig = Join-Path $ProjectRoot ("configs\diseases\{0}.yaml" -f $CanonicalDisease.ToLowerInvariant())
    Ensure-PathExists -Path $defaultConfig -Label "Disease config YAML"
    return (Resolve-Path -LiteralPath $defaultConfig).Path
}

function Invoke-PythonStep {
    param(
        [Parameter(Mandatory = $true)][string]$RelativeScriptPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Ensure-RelativeScriptExists -RelativeScriptPath $RelativeScriptPath
    Write-Host ("Running: {0} {1} {2}" -f $PythonExe, $RelativeScriptPath, ($Arguments -join " "))
    & $PythonExe $RelativeScriptPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("Step failed with exit code {0}: {1}" -f $LASTEXITCODE, $RelativeScriptPath)
    }
}

Ensure-PathExists -Path $ProjectRoot -Label "ProjectRoot"
Ensure-PathExists -Path $PythonExe -Label "Python executable"

$canonicalDisease = Get-CanonicalDisease -InputDisease $Disease
$resolvedConfigPath = Resolve-ConfigPathForDisease -CanonicalDisease $canonicalDisease -OptionalConfigPath $ConfigPath

Write-Host ("ProjectRoot: {0}" -f $ProjectRoot)
Write-Host ("Input Disease: {0}" -f $Disease)
Write-Host ("Canonical Disease: {0}" -f $canonicalDisease)
Write-Host ("ConfigPath: {0}" -f $resolvedConfigPath)
Write-Host ("Mode: {0}" -f $Mode)

Push-Location $ProjectRoot
try {
    switch ($Mode) {
        "DryRun" {
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\run_disease_execute_pipeline.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath, "--dry-run")
        }
        "Postgres" {
            Ensure-RequiredEnvVars -Names @("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\run_disease_execute_pipeline.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath, "--execute-postgres")
        }
        "ValidatePostgres" {
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\validate_disease_postgres_load_result.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
        }
        "Neo4jPreview" {
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\build_disease_neo4j_write_plan.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
        }
        "Neo4jExecute" {
            Ensure-RequiredEnvVars -Names @("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\execute_disease_neo4j_from_write_plan.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
        }
        "Neo4jValidate" {
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\validate_disease_neo4j_load_result.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
        }
        "FullSafe" {
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\run_disease_execute_pipeline.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath, "--dry-run")
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\validate_disease_postgres_load_result.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
            Invoke-PythonStep -RelativeScriptPath ".\scripts\load\build_disease_neo4j_write_plan.py" -Arguments @("--disease", $canonicalDisease, "--config", $resolvedConfigPath)
        }
        default {
            throw "Unsupported mode: $Mode"
        }
    }
}
finally {
    Pop-Location
}
