$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..")

Set-Location $projectRoot
$env:PYTHONPATH = "$projectRoot"

py -3.11 -m backend.scripts.rag_build_vector_index `
  --input data/rag_docs/literature `
  --output data/rag_index/literature
