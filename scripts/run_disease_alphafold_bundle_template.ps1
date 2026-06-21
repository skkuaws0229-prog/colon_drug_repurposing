param(
  [string]$Disease = "BRCA",
  [string]$RankingJson = "20260414_re_pre_project_v3\\step4_results\\step6_final\\repurposing_summary.json",
  [int]$TopN = 20,
  [switch]$DryRun
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptDir "run_disease_alphafold_bundle.cmd"

if (-not (Test-Path $runner)) {
  Write-Error "Runner not found: $runner"
  exit 1
}

$args = @(
  "--disease", $Disease,
  "--ranking-json", $RankingJson,
  "--top-n", "$TopN",
  "--viewer-max-items", "$TopN"
)
if ($DryRun) { $args += "--dry-run" }

& $runner @args
exit $LASTEXITCODE
