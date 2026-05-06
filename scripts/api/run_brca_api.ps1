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

Write-Step -Number 1 -Title "Resolve Project Root"
$ScriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    throw "Cannot resolve script path from invocation context."
}
$ScriptDir = Split-Path -Parent $ScriptPath
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path -Path $ScriptDir -ChildPath "..\..")).Path
Set-Location -LiteralPath $ProjectRoot
Write-Host "Project root: $(Get-Location)"

Write-Step -Number 2 -Title "Set PostgreSQL Environment Variables"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "Drug"
$env:POSTGRES_USER = "Drug"
$env:POSTGRES_PASSWORD = "1234"

Write-Step -Number 3 -Title "Set Neo4j Environment Variables"
$env:NEO4J_URI = "bolt://localhost:7687"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "1234"
$env:NEO4J_DATABASE = "neo4j"

Write-Step -Number 4 -Title "Check Required Files"
$RequiredFiles = @(
    (Join-Path -Path $ProjectRoot -ChildPath "api\main.py"),
    (Join-Path -Path $ProjectRoot -ChildPath "scripts\api\check_brca_api.py")
)
foreach ($File in $RequiredFiles) {
    if (-not (Test-Path -LiteralPath $File)) {
        throw "Required file missing: $File"
    }
    Write-Host "Found: $File"
}

Write-Step -Number 5 -Title "Resolve Python Executable"
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

Write-Step -Number 6 -Title "Run FastAPI (uvicorn)"
& $PythonExe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
Assert-LastExitCode -Context "uvicorn api.main:app"
