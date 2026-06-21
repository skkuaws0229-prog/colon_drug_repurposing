param(
    [ValidateSet("public-demo", "full-reproduction")]
    [string]$Profile = "public-demo",
    [string]$Disease = "",
    [switch]$Verify,
    [switch]$RunSmokeTest,
    [switch]$InstallDependencies,
    [switch]$Download
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Repository root: $Root"
Write-Host "Profile: $Profile"

$PythonCandidates = @(
    "python",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)

$Python = $null
foreach ($Candidate in $PythonCandidates) {
    try {
        $Version = & $Candidate --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            $Python = $Candidate
            Write-Host "Python: $Version"
            break
        }
    } catch {}
}

if (-not $Python) {
    throw "Python was not found. Install Python 3.10+ or add it to PATH."
}

if ($InstallDependencies) {
    if (Test-Path ".\requirements.txt") {
        & $Python -m pip install -r .\requirements.txt
    } else {
        Write-Host "requirements.txt not found; skipping dependency install."
    }
} else {
    Write-Host "Dependency install skipped. Use -InstallDependencies to install."
}

$DownloadArgs = @("scripts\download_artifacts.py", "--profile", $Profile)
if ($Disease) { $DownloadArgs += @("--disease", $Disease) }
if ($Verify) { $DownloadArgs += "--verify" }
if ($Download) { $DownloadArgs += "--no-dry-run" }

Write-Host "Artifact download step:"
& $Python @DownloadArgs

if ($Verify) {
    $VerifyArgs = @("scripts\verify_artifacts.py", "--profile", $Profile)
    if ($Disease) { $VerifyArgs += @("--disease", $Disease) }
    & $Python @VerifyArgs
}

if ($RunSmokeTest) {
    & $Python scripts\run_smoke_test.py
}
