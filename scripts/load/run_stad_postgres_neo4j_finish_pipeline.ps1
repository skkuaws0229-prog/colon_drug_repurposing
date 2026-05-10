[CmdletBinding()]
param(
    [string]$ProjectRoot = 'C:\work\drug-project',
    [string]$Disease = 'STAD',
    [string]$ConfigPath = 'C:\work\drug-project\configs\diseases\stad.yaml',
    [string]$PythonExe = 'C:\Users\hjy10\AppData\Local\Programs\Python\Python311\python.exe'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$CanonicalProjectRoot = 'C:\work\drug-project'
$ForbiddenDecisions = @('BLOCKED', 'LOCAL_SYNC_NEEDED', 'DO_NOT_LOAD_EXCLUDED', 'NEEDS_REVIEW', 'MISSING')
$AcceptStatuses = @('PASS', 'PASS_WITH_WARNINGS')
$PostgresCandidatePorts = @(5433, 5432, 5443)
$PostgresHost = 'localhost'
$PostgresUser = 'Drug'
$PostgresDatabase = 'Drug'
$Neo4jUri = 'bolt://127.0.0.1:7687'
$Neo4jUser = 'neo4j'
$Neo4jDatabase = 'neo4j'
$Neo4jBoltPort = 7687
$Neo4jHttpPort = 7474

function Write-Step {
    param([string]$Message)
    Write-Host "[STAD-FINISH] $Message"
}

function Assert-Exists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function Convert-SecureStringToPlainText {
    param([Parameter(Mandatory = $true)][securestring]$Secure)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$StepName
    )

    Write-Step ("Running {0}" -f $StepName)
    & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed ({0}), exit code {1}" -f $StepName, $LASTEXITCODE
    }
}

function Test-PostgresConnection {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Password
    )

    $code = @"
import sys
host = sys.argv[1]
port = int(sys.argv[2])
db = sys.argv[3]
user = sys.argv[4]
pw = sys.argv[5]
try:
    import psycopg2 as pg
except Exception:
    import psycopg as pg
try:
    conn = pg.connect(host=host, port=port, dbname=db, user=user, password=pw)
    cur = conn.cursor()
    cur.execute('SELECT 1')
    cur.fetchone()
    conn.close()
    print('OK')
    sys.exit(0)
except Exception as exc:
    print(f'ERROR:{exc}')
    sys.exit(1)
"@

    & $PythonExe '-c' $code $PostgresHost $Port $PostgresDatabase $PostgresUser $Password 1>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-Neo4jVerifyConnectivity {
    param([Parameter(Mandatory = $true)][string]$Password)

    $code = @"
import sys
from neo4j import GraphDatabase
uri = sys.argv[1]
user = sys.argv[2]
pw = sys.argv[3]
db = sys.argv[4]
try:
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    driver.verify_connectivity()
    driver.close()
    print('OK')
    sys.exit(0)
except Exception as exc:
    print(f'ERROR:{exc}')
    sys.exit(1)
"@

    & $PythonExe '-c' $code $Neo4jUri $Neo4jUser $Password $Neo4jDatabase
    return ($LASTEXITCODE -eq 0)
}

function Test-Neo4jBoltListening {
    $lines = @(& netstat -ano -p tcp 2>$null)
    foreach ($line in $lines) {
        $trimmed = [string]$line
        if ($trimmed -match '^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+\d+\s*$') {
            $localAddress = $matches[1]
            $port = [int]$matches[2]
            if ($port -eq $Neo4jBoltPort -and @('127.0.0.1', '0.0.0.0', '[::1]', '[::]') -contains $localAddress) {
                return $true
            }
        }
    }
    return $false
}

function Start-Neo4jWindowsServices {
    $startedOrRunning = $false
    try {
        $services = @(Get-Service | Where-Object { $_.Name -like '*neo4j*' -or $_.DisplayName -like '*neo4j*' })
        foreach ($svc in $services) {
            if ($svc.Status -eq 'Running') {
                $startedOrRunning = $true
                continue
            }
            try {
                Write-Step ("Attempting to start Neo4j Windows service: {0}" -f $svc.Name)
                Start-Service -Name $svc.Name -ErrorAction Stop
                $startedOrRunning = $true
            }
            catch {
                Write-Step ("Service start failed for {0}: {1}" -f $svc.Name, $_.Exception.Message)
            }
        }
    }
    catch {
        Write-Step ("Neo4j service discovery failed: {0}" -f $_.Exception.Message)
    }
    return $startedOrRunning
}

function Start-Neo4jDockerContainers {
    $startedOrRunning = $false
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $dockerCmd) {
        return $false
    }

    try {
        $rows = @(& docker ps -a --format '{{.ID}}|{{.Image}}|{{.Names}}|{{.Status}}' 2>$null)
        if ($LASTEXITCODE -ne 0) {
            Write-Step 'Docker command is present, but docker daemon is unavailable.'
            return $false
        }
        foreach ($row in $rows) {
            $parts = ([string]$row).Split('|')
            if ($parts.Count -lt 4) {
                continue
            }
            $id = $parts[0]
            $image = $parts[1]
            $name = $parts[2]
            $status = $parts[3]
            if ($image -notlike '*neo4j*' -and $name -notlike '*neo4j*') {
                continue
            }
            if ($status -like 'Up*') {
                $startedOrRunning = $true
                continue
            }
            try {
                Write-Step ("Attempting to start Neo4j Docker container: {0}" -f $name)
                & docker start $id 1>$null 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $startedOrRunning = $true
                }
            }
            catch {
                Write-Step ("Docker start failed for {0}: {1}" -f $name, $_.Exception.Message)
            }
        }
    }
    catch {
        Write-Step ("Neo4j docker discovery failed: {0}" -f $_.Exception.Message)
    }
    return $startedOrRunning
}

function Start-Neo4jFromHome {
    $neo4jHome = $env:NEO4J_HOME
    if ([string]::IsNullOrWhiteSpace($neo4jHome)) {
        return $false
    }
    $neo4jBat = Join-Path $neo4jHome 'bin\neo4j.bat'
    if (-not (Test-Path -LiteralPath $neo4jBat)) {
        return $false
    }
    try {
        Write-Step ("Attempting to start Neo4j via NEO4J_HOME: {0}" -f $neo4jBat)
        Start-Process -FilePath $neo4jBat -ArgumentList 'start' -WindowStyle Hidden | Out-Null
        return $true
    }
    catch {
        Write-Step ("NEO4J_HOME start failed: {0}" -f $_.Exception.Message)
        return $false
    }
}

function Wait-ForNeo4jBoltListening {
    param([int]$TimeoutSeconds = 60)

    if (Test-Neo4jBoltListening) {
        return $true
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        if (Test-Neo4jBoltListening) {
            return $true
        }
    }
    return $false
}

function Show-Neo4jManualStartInstructions {
    Write-Host ''
    Write-Host 'Neo4j Bolt port 7687 is still not LISTENING.'
    Write-Host 'Please do the following and rerun this script:'
    Write-Host '1. Open Neo4j Desktop'
    Write-Host '2. Start the target DBMS'
    Write-Host ("3. Confirm netstat LISTENING on {0} and {1}" -f $Neo4jBoltPort, $Neo4jHttpPort)
    Write-Host '4. Rerun the script'
    Write-Host ''
}

function Ensure-Neo4jListeningAndVerified {
    param(
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][string]$StageLabel
    )

    Write-Step ("Checking Neo4j Bolt LISTENING state ({0})" -f $StageLabel)
    if (-not (Test-Neo4jBoltListening)) {
        Write-Step 'Bolt 7687 is not LISTENING. Attempting safe Neo4j start methods.'
        [void](Start-Neo4jWindowsServices)
        [void](Start-Neo4jDockerContainers)
        [void](Start-Neo4jFromHome)

        Write-Step 'Waiting up to 60 seconds for Bolt 7687 LISTENING'
        if (-not (Wait-ForNeo4jBoltListening -TimeoutSeconds 60)) {
            Show-Neo4jManualStartInstructions
            throw ("Neo4j Bolt {0} not LISTENING after auto-start attempts ({1})." -f $Neo4jBoltPort, $StageLabel)
        }
    }

    Write-Step ("Neo4j Bolt {0} is LISTENING ({1})" -f $Neo4jBoltPort, $StageLabel)
    Write-Step ("Running Neo4j driver.verify_connectivity() ({0})" -f $StageLabel)
    if (-not (Test-Neo4jVerifyConnectivity -Password $Password)) {
        throw ("Neo4j verify_connectivity failed ({0})." -f $StageLabel)
    }
}

$resolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$resolvedCanonicalRoot = [System.IO.Path]::GetFullPath($CanonicalProjectRoot)
$rootHasOneDrive = $resolvedProjectRoot.ToLowerInvariant().Contains('onedrive')
if ($rootHasOneDrive) {
    throw "Blocked project root (OneDrive detected): $resolvedProjectRoot"
}
if (-not $resolvedProjectRoot.Equals($resolvedCanonicalRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Project root mismatch. Expected $resolvedCanonicalRoot but got $resolvedProjectRoot"
}

Set-Location -LiteralPath $resolvedCanonicalRoot

Assert-Exists -Path $PythonExe -Label 'Python executable'
Assert-Exists -Path $ConfigPath -Label 'STAD config'

$outputDir = Join-Path $resolvedCanonicalRoot 'outputs\config_validation'
$docsDir = Join-Path $resolvedCanonicalRoot 'docs'
Assert-Exists -Path $outputDir -Label 'Output directory'
Assert-Exists -Path $docsDir -Label 'Docs directory'

$planJson = Join-Path $outputDir 'stad_postgres_load_plan_from_real_inspection.json'
$postgresExecuteJson = Join-Path $outputDir 'stad_postgres_execute_report.json'
$postgresValidationJson = Join-Path $outputDir 'stad_postgres_load_validation_report.json'
$postgresValidationMd = Join-Path $docsDir 'stad_postgres_load_validation_report.md'
$neo4jPreviewJson = Join-Path $outputDir 'stad_neo4j_write_plan_preview.json'
$neo4jPreviewMd = Join-Path $docsDir 'stad_neo4j_write_plan_preview.md'
$neo4jExecuteJson = Join-Path $outputDir 'stad_neo4j_execute_report.json'
$neo4jExecuteMd = Join-Path $docsDir 'stad_neo4j_execute_report.md'
$neo4jValidationJson = Join-Path $outputDir 'stad_neo4j_validation_report.json'
$neo4jValidationMd = Join-Path $docsDir 'stad_neo4j_validation_report.md'

Assert-Exists -Path $planJson -Label 'STAD PostgreSQL load plan JSON'
Assert-Exists -Path $postgresExecuteJson -Label 'STAD PostgreSQL execute report JSON'

Write-Step 'Checking plan for forbidden selected-row decisions'
$plan = Get-Content -LiteralPath $planJson -Raw | ConvertFrom-Json
if ($null -eq $plan.plan_rows) {
    throw "Plan is missing plan_rows: $planJson"
}
$selectedRows = @($plan.plan_rows)
if ($selectedRows.Count -le 0) {
    throw "Plan has zero selected rows: $planJson"
}

$decisionFields = @('decision', 'decision_preview', 'selected_decision', 'final_decision', 'load_decision', 'status')
$blockedHits = New-Object System.Collections.Generic.List[string]
for ($i = 0; $i -lt $selectedRows.Count; $i++) {
    $row = $selectedRows[$i]
    foreach ($field in $decisionFields) {
        if ($row.PSObject.Properties.Name -contains $field) {
            $value = [string]$row.$field
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $upper = $value.Trim().ToUpperInvariant()
                if ($ForbiddenDecisions -contains $upper) {
                    $src = ''
                    if ($row.PSObject.Properties.Name -contains 'source_s3_uri') {
                        $src = [string]$row.source_s3_uri
                    }
                    $blockedHits.Add("row_index=$i field=$field value=$upper source=$src") | Out-Null
                }
            }
        }
    }
}
if ($blockedHits.Count -gt 0) {
    throw ("Refusing to continue because forbidden decisions were found in selected rows: {0}" -f ($blockedHits -join '; '))
}

$originalEnv = @{}
foreach ($name in @('PGHOST','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','NEO4J_URI','NEO4J_USER','NEO4J_PASSWORD','NEO4J_DATABASE')) {
    $originalEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    $pgPassword = $null
    if (-not [string]::IsNullOrWhiteSpace($env:POSTGRES_PASSWORD)) {
        Write-Step 'Using PostgreSQL password from POSTGRES_PASSWORD environment variable'
        $pgPassword = [string]$env:POSTGRES_PASSWORD
    }
    else {
        Write-Step 'Prompting for PostgreSQL password'
        $pgSecure = Read-Host -Prompt 'Enter PostgreSQL password for user Drug' -AsSecureString
        $pgPassword = Convert-SecureStringToPlainText -Secure $pgSecure
    }
    if ([string]::IsNullOrWhiteSpace($pgPassword)) {
        throw 'PostgreSQL password was empty.'
    }

    Write-Step 'Testing PostgreSQL candidate ports (5433, 5432, 5443)'
    $workingPgPort = $null
    foreach ($port in $PostgresCandidatePorts) {
        if (Test-PostgresConnection -Port $port -Password $pgPassword) {
            $workingPgPort = $port
            break
        }
    }
    if ($null -eq $workingPgPort) {
        throw 'Could not connect to PostgreSQL on candidate ports 5433, 5432, 5443.'
    }
    Write-Step ("Using PostgreSQL port $workingPgPort")

    $env:PGHOST = $PostgresHost
    $env:PGPORT = [string]$workingPgPort
    $env:PGDATABASE = $PostgresDatabase
    $env:PGUSER = $PostgresUser
    $env:PGPASSWORD = $pgPassword

    Invoke-PythonChecked -StepName 'STAD PostgreSQL validation' -Arguments @(
        'scripts\load\validate_disease_postgres_load_result.py',
        '--project-root', $resolvedCanonicalRoot,
        '--disease', $Disease,
        '--config', $ConfigPath,
        '--plan-json', $planJson,
        '--execute-report-json', $postgresExecuteJson,
        '--pg-host', $PostgresHost,
        '--pg-port', [string]$workingPgPort,
        '--pg-database', $PostgresDatabase,
        '--pg-user', $PostgresUser
    )

    Assert-Exists -Path $postgresValidationJson -Label 'STAD PostgreSQL validation JSON'
    $pgValidation = Get-Content -LiteralPath $postgresValidationJson -Raw | ConvertFrom-Json
    $pgStatus = [string]$pgValidation.postgres_validation_status
    if ($AcceptStatuses -notcontains $pgStatus) {
        throw "PostgreSQL validation status is not acceptable: $pgStatus"
    }
    Write-Step ("PostgreSQL validation status: $pgStatus")

    $neo4jPassword = $null
    if (-not [string]::IsNullOrWhiteSpace($env:NEO4J_PASSWORD)) {
        Write-Step 'Using Neo4j password from NEO4J_PASSWORD environment variable'
        $neo4jPassword = [string]$env:NEO4J_PASSWORD
    }
    else {
        Write-Step 'Prompting for Neo4j password'
        $neo4jSecure = Read-Host -Prompt 'Enter Neo4j password for user neo4j' -AsSecureString
        $neo4jPassword = Convert-SecureStringToPlainText -Secure $neo4jSecure
    }
    if ([string]::IsNullOrWhiteSpace($neo4jPassword)) {
        throw 'Neo4j password was empty.'
    }

    $env:NEO4J_URI = $Neo4jUri
    $env:NEO4J_USER = $Neo4jUser
    $env:NEO4J_PASSWORD = $neo4jPassword
    $env:NEO4J_DATABASE = $Neo4jDatabase

    Ensure-Neo4jListeningAndVerified -Password $neo4jPassword -StageLabel 'before Neo4j preview rebuild'

    Invoke-PythonChecked -StepName 'Rebuild STAD Neo4j write-plan preview' -Arguments @(
        'scripts\load\build_disease_neo4j_write_plan.py',
        '--project-root', $resolvedCanonicalRoot,
        '--disease', $Disease,
        '--config', $ConfigPath,
        '--postgres-validation-json', $postgresValidationJson
    )

    Assert-Exists -Path $neo4jPreviewJson -Label 'STAD Neo4j write-plan preview JSON'
    $preview = Get-Content -LiteralPath $neo4jPreviewJson -Raw | ConvertFrom-Json
    $previewStatus = [string]$preview.write_plan_status
    if ($AcceptStatuses -notcontains $previewStatus) {
        throw "Neo4j write-plan preview status is not acceptable: $previewStatus"
    }
    Write-Step ("Neo4j write-plan preview status: $previewStatus")

    Ensure-Neo4jListeningAndVerified -Password $neo4jPassword -StageLabel 'before Neo4j execute'

    Invoke-PythonChecked -StepName 'Execute STAD Neo4j write' -Arguments @(
        'scripts\load\execute_disease_neo4j_from_write_plan.py',
        '--project-root', $resolvedCanonicalRoot,
        '--disease', $Disease,
        '--config', $ConfigPath,
        '--write-plan-json', 'C:\work\drug-project\outputs\config_validation\stad_neo4j_write_plan_preview.json',
        '--neo4j-database', $Neo4jDatabase
    )

    Invoke-PythonChecked -StepName 'Validate STAD Neo4j load' -Arguments @(
        'scripts\load\validate_disease_neo4j_load_result.py',
        '--project-root', $resolvedCanonicalRoot,
        '--disease', $Disease,
        '--config', $ConfigPath,
        '--write-plan-json', 'C:\work\drug-project\outputs\config_validation\stad_neo4j_write_plan_preview.json',
        '--neo4j-database', $Neo4jDatabase
    )

    $neo4jValidation = Get-Content -LiteralPath $neo4jValidationJson -Raw | ConvertFrom-Json
    $neo4jStatus = [string]$neo4jValidation.neo4j_validation_status

    Write-Host ''
    Write-Host '========== FINAL STATUS =========='
    Write-Host ("Disease: {0}" -f $Disease)
    Write-Host ("Project Root: {0}" -f $resolvedCanonicalRoot)
    Write-Host ("PostgreSQL port used: {0}" -f $workingPgPort)
    Write-Host ("PostgreSQL validation: {0}" -f $pgStatus)
    Write-Host ("Neo4j write-plan preview: {0}" -f $previewStatus)
    Write-Host ("Neo4j validation: {0}" -f $neo4jStatus)
    Write-Host ''
    Write-Host 'Reports:'
    Write-Host ("- {0}" -f $planJson)
    Write-Host ("- {0}" -f $postgresValidationJson)
    Write-Host ("- {0}" -f $postgresValidationMd)
    Write-Host ("- {0}" -f $neo4jPreviewJson)
    Write-Host ("- {0}" -f $neo4jPreviewMd)
    Write-Host ("- {0}" -f $neo4jExecuteJson)
    Write-Host ("- {0}" -f $neo4jExecuteMd)
    Write-Host ("- {0}" -f $neo4jValidationJson)
    Write-Host ("- {0}" -f $neo4jValidationMd)
}
finally {
    foreach ($key in $originalEnv.Keys) {
        $previous = $originalEnv[$key]
        if ($null -eq $previous) {
            Remove-Item -Path ("Env:{0}" -f $key) -ErrorAction SilentlyContinue
        }
        else {
            Set-Item -Path ("Env:{0}" -f $key) -Value $previous
        }
    }
}
