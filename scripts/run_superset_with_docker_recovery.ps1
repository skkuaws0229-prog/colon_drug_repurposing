param(
    [string]$ProjectDir = "C:\Users\hjy10\superset",
    [string]$ComposeFile = "docker-compose-image-tag.yml",
    [switch]$Detach,
    [switch]$RepairContext,
    [int]$WaitSeconds = 120,
    [switch]$SkipCompose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $Message"
}

function Test-DockerServerReady {
    try {
        $serverVersion = & docker version --format "{{.Server.Version}}" 2>$null
        return ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($serverVersion))
    } catch {
        return $false
    }
}

function Wait-DockerServer {
    param([int]$TimeoutSeconds)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerServerReady) {
            return $true
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Repair-DesktopLinuxContext {
    Write-Step "Repairing docker context 'desktop-linux'..."
    $names = & docker context ls --format "{{.Name}}" 2>$null
    if ($LASTEXITCODE -eq 0 -and ($names -contains "desktop-linux")) {
        & docker context rm desktop-linux -f | Out-Null
    }
    & docker context create desktop-linux --docker "host=npipe:////./pipe/dockerDesktopLinuxEngine" | Out-Null
    & docker context use desktop-linux | Out-Null
}

Write-Step "Starting Docker recovery + Superset compose protocol..."

if (Test-Path Env:DOCKER_HOST) {
    Write-Step "Removing current-shell DOCKER_HOST to avoid endpoint conflicts."
    Remove-Item Env:DOCKER_HOST -ErrorAction SilentlyContinue
}

$svc = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($null -eq $svc) {
    throw "Service 'com.docker.service' was not found. Reinstall Docker Desktop first."
}

Write-Step "Ensuring com.docker.service startup type is Automatic."
& sc.exe config com.docker.service start= auto | Out-Null

if ($svc.Status -ne "Running") {
    Write-Step "Starting com.docker.service..."
    Start-Service -Name "com.docker.service"
}

$desktopExe = Join-Path $Env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
if (-not (Test-Path $desktopExe)) {
    throw "Docker Desktop executable not found: $desktopExe"
}

$desktopProc = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($null -eq $desktopProc) {
    Write-Step "Launching Docker Desktop UI..."
    Start-Process -FilePath $desktopExe | Out-Null
}

Write-Step "Resetting WSL backend state..."
& wsl --shutdown 2>$null | Out-Null

Write-Step "Waiting for Docker server (timeout: $WaitSeconds sec)..."
$ready = Wait-DockerServer -TimeoutSeconds $WaitSeconds

if (-not $ready -and $RepairContext) {
    Repair-DesktopLinuxContext
    Write-Step "Waiting again after context repair..."
    $ready = Wait-DockerServer -TimeoutSeconds 60
}

if (-not $ready) {
    throw "Docker server is still not ready. Open Docker Desktop > Troubleshoot > Reset to factory defaults, then retry."
}

$ctxNames = & docker context ls --format "{{.Name}}" 2>$null
if ($LASTEXITCODE -eq 0 -and ($ctxNames -contains "desktop-linux")) {
    & docker context use desktop-linux | Out-Null
}

Write-Step "Docker is ready. Verifying with 'docker version'..."
& docker version

if ($SkipCompose) {
    Write-Step "SkipCompose enabled. Recovery protocol completed."
    exit 0
}

$composePath = Join-Path $ProjectDir $ComposeFile
if (-not (Test-Path $composePath)) {
    throw "Compose file not found: $composePath"
}

Write-Step "Running compose in: $ProjectDir"
Push-Location $ProjectDir
try {
    $args = @("compose", "-f", $ComposeFile, "up")
    if ($Detach) {
        $args += "-d"
    }
    & docker @args
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Step "Completed successfully."
