$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..")

Set-Location $projectRoot
$env:PYTHONPATH = "$projectRoot"

py -3.11 -m backend.scripts.rag_collect_all_literature `
  --config configs/rag/literature_targets.yaml `
  --diseases BRCA COAD LUAD LIHC STAD PAAD HNSC `
  --continue-on-error
