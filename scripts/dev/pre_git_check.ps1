# scripts/dev/pre_git_check.ps1
# Safety checks before committing this repository.

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host " Pre-Git Safety Check"
Write-Host "========================================"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path

Set-Location $ProjectRoot

Write-Host "[INFO] Project root: $ProjectRoot"

# Resolve Python from PATH only.
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} else {
    Write-Warning "Python was not found in PATH. Skipping Python-based checks."
}

# Check git availability.
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "git was not found in PATH. Skipping git-based checks."
    exit 0
}

Write-Host "[INFO] Git detected. Running tracked-file checks..."

# Ensure .env is not tracked.
$TrackedEnv = git ls-files .env
if ($TrackedEnv) {
    Write-Error ".env is tracked. Remove it with: git rm --cached .env"
} else {
    Write-Host "[OK] .env is not tracked."
}

# Basic staged diff scan.
Write-Host "[INFO] Scanning staged diff for obvious secrets and local paths..."

$StagedDiff = git diff --cached

$Patterns = @(
    "AWS_SECRET_ACCESS_KEY",
    "aws_secret_access_key",
    "~1q2w3e4r5t"
)

$FoundProblem = $false

foreach ($Pattern in $Patterns) {
    if ($StagedDiff -match [regex]::Escape($Pattern)) {
        Write-Error "Potential secret found in staged diff: $Pattern"
        $FoundProblem = $true
    }
}

# Build local path patterns without embedding the full personal path literally.
$UsersPathPattern = ("C:" + "\Users\")
$CloudPathPattern = ("One" + "Drive")

if ($StagedDiff -match [regex]::Escape($UsersPathPattern)) {
    Write-Error "User-specific Windows path found in staged diff."
    $FoundProblem = $true
}

if ($StagedDiff -match [regex]::Escape($CloudPathPattern)) {
    Write-Error "Cloud-drive local path found in staged diff."
    $FoundProblem = $true
}

if ($FoundProblem) {
    throw "Pre-git safety check failed."
}

# Warn if generated folders exist locally.
$GeneratedDirs = @("outputs", "runs", "downloads", "reports", ".npm-cache", "catboost_info")
foreach ($Dir in $GeneratedDirs) {
    if (Test-Path (Join-Path $ProjectRoot $Dir)) {
        Write-Warning "$Dir exists locally. Ensure generated artifacts are not staged."
    }
}

Write-Host "[INFO] Staged files:"
git diff --cached --name-only

Write-Host "[INFO] Git status:"
git status --short

Write-Host "[OK] Pre-git safety check completed."