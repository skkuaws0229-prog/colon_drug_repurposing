$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$colonCsv = Join-Path $root "models\admet_results\final_drug_candidates.csv"
$brcaCsv = Join-Path $root "20260414_re_pre_project_v3\step4_results\step6_final\repurposing_top15.csv"
$outJson = Join-Path $PSScriptRoot "colon_brca_graph_data.json"

function Normalize-Text {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  return (($Text.ToLower()) -replace "[^a-z0-9]+", "")
}

function Split-Tokens {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return @() }
  return ($Text -split ",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
}

function To-Number {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
  $n = 0.0
  if ([double]::TryParse($Text, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$n)) {
    return $n
  }
  return $null
}

$nodeMap = @{}
$edgeMap = @{}
$diseaseDrugNorms = @{
  colon = @{}
  brca  = @{}
}

function Add-Node {
  param(
    [string]$NodeId,
    [string]$NodeType,
    [string]$Label,
    [hashtable]$Attrs
  )

  $cleanAttrs = @{}
  foreach ($k in $Attrs.Keys) {
    $v = $Attrs[$k]
    if ($null -ne $v -and $v -ne "") {
      $cleanAttrs[$k] = $v
    }
  }

  if ($nodeMap.ContainsKey($NodeId)) {
    foreach ($k in $cleanAttrs.Keys) {
      $nodeMap[$NodeId].attrs[$k] = $cleanAttrs[$k]
    }
    return
  }

  $nodeMap[$NodeId] = [ordered]@{
    id    = $NodeId
    type  = $NodeType
    label = $Label
    attrs = $cleanAttrs
  }
}

function Add-Edge {
  param(
    [string]$Source,
    [string]$Target,
    [string]$EdgeType,
    [Nullable[Double]]$Weight,
    [hashtable]$Attrs
  )

  $key = "$Source|$Target|$EdgeType"
  $cleanAttrs = @{}
  foreach ($k in $Attrs.Keys) {
    $v = $Attrs[$k]
    if ($null -ne $v -and $v -ne "") {
      $cleanAttrs[$k] = $v
    }
  }

  if (-not $edgeMap.ContainsKey($key)) {
    $edgeMap[$key] = [ordered]@{
      source = $Source
      target = $Target
      type   = $EdgeType
      weight = $Weight
      attrs  = $cleanAttrs
    }
    return
  }

  if ($null -eq $edgeMap[$key].weight -and $null -ne $Weight) {
    $edgeMap[$key].weight = $Weight
  }
  foreach ($k in $cleanAttrs.Keys) {
    $edgeMap[$key].attrs[$k] = $cleanAttrs[$k]
  }
}

Add-Node -NodeId "disease:colon" -NodeType "disease" -Label "COLON" -Attrs @{ disease = "colon" }
Add-Node -NodeId "disease:brca" -NodeType "disease" -Label "BRCA" -Attrs @{ disease = "brca" }

$colonRows = Import-Csv -Path $colonCsv
foreach ($row in $colonRows) {
  $drugName = ($row.drug_name | ForEach-Object { "$_".Trim() })
  if ([string]::IsNullOrWhiteSpace($drugName)) { continue }
  $norm = Normalize-Text $drugName
  if ($norm -eq "") { continue }

  $drugId = "drug:colon:$norm"
  $diseaseDrugNorms.colon[$norm] = $drugId

  Add-Node -NodeId $drugId -NodeType "drug" -Label $drugName -Attrs @{
    disease       = "colon"
    drug_name_norm = $norm
    drug_ref_id   = ($row.drug_id | ForEach-Object { "$_".Trim() })
    rank          = (To-Number $row.final_rank)
    combined_score = (To-Number $row.combined_score)
    category      = ($row.category | ForEach-Object { "$_".Trim() })
  }

  Add-Edge -Source "disease:colon" -Target $drugId -EdgeType "has_candidate" -Weight (To-Number $row.combined_score) -Attrs @{
    source = "colon_csv"
  }

  $pathway = ($row.pathway | ForEach-Object { "$_".Trim() })
  if (-not [string]::IsNullOrWhiteSpace($pathway)) {
    $pathwayNorm = Normalize-Text $pathway
    $pathwayId = "pathway:$pathwayNorm"
    Add-Node -NodeId $pathwayId -NodeType "pathway" -Label $pathway -Attrs @{ pathway_norm = $pathwayNorm }
    Add-Edge -Source $drugId -Target $pathwayId -EdgeType "in_pathway" -Weight $null -Attrs @{ source = "colon_csv" }
  }

  foreach ($token in (Split-Tokens $row.target)) {
    $targetNorm = Normalize-Text $token
    if ($targetNorm -eq "") { continue }
    $targetId = "target:$targetNorm"
    Add-Node -NodeId $targetId -NodeType "target" -Label $token -Attrs @{ target_norm = $targetNorm }
    Add-Edge -Source $drugId -Target $targetId -EdgeType "targets" -Weight $null -Attrs @{ source = "colon_csv" }
  }
}

$brcaRows = Import-Csv -Path $brcaCsv
foreach ($row in $brcaRows) {
  $drugName = ($row.drug_name | ForEach-Object { "$_".Trim() })
  if ([string]::IsNullOrWhiteSpace($drugName)) { continue }
  $norm = Normalize-Text $drugName
  if ($norm -eq "") { continue }

  $drugId = "drug:brca:$norm"
  $diseaseDrugNorms.brca[$norm] = $drugId

  $rankRaw = $row.repurposing_rank
  if ([string]::IsNullOrWhiteSpace($rankRaw)) {
    $rankRaw = $row.rank
  }

  Add-Node -NodeId $drugId -NodeType "drug" -Label $drugName -Attrs @{
    disease        = "brca"
    drug_name_norm = $norm
    drug_ref_id    = ($row.canonical_drug_id | ForEach-Object { "$_".Trim() })
    rank           = (To-Number $rankRaw)
    combined_score = (To-Number $row.final_score)
    category       = ($row.category | ForEach-Object { "$_".Trim() })
  }

  Add-Edge -Source "disease:brca" -Target $drugId -EdgeType "has_candidate" -Weight (To-Number $row.final_score) -Attrs @{
    source = "brca_csv"
  }

  $pathway = ($row.pathway | ForEach-Object { "$_".Trim() })
  if (-not [string]::IsNullOrWhiteSpace($pathway)) {
    $pathwayNorm = Normalize-Text $pathway
    $pathwayId = "pathway:$pathwayNorm"
    Add-Node -NodeId $pathwayId -NodeType "pathway" -Label $pathway -Attrs @{ pathway_norm = $pathwayNorm }
    Add-Edge -Source $drugId -Target $pathwayId -EdgeType "in_pathway" -Weight $null -Attrs @{ source = "brca_csv" }
  }

  foreach ($token in (Split-Tokens $row.target)) {
    $targetNorm = Normalize-Text $token
    if ($targetNorm -eq "") { continue }
    $targetId = "target:$targetNorm"
    Add-Node -NodeId $targetId -NodeType "target" -Label $token -Attrs @{ target_norm = $targetNorm }
    Add-Edge -Source $drugId -Target $targetId -EdgeType "targets" -Weight $null -Attrs @{ source = "brca_csv" }
  }
}

$overlapNorms = @(
  $diseaseDrugNorms.colon.Keys | Where-Object { $diseaseDrugNorms.brca.ContainsKey($_) } | Sort-Object
)
foreach ($norm in $overlapNorms) {
  Add-Edge -Source $diseaseDrugNorms.colon[$norm] -Target $diseaseDrugNorms.brca[$norm] -EdgeType "shared_candidate" -Weight 1.0 -Attrs @{
    drug_name_norm = $norm
  }
}

$nodes = @($nodeMap.Values | Sort-Object type, label, id)
$edges = @($edgeMap.Values | Sort-Object type, source, target)

$nodeTypeCounts = @{}
foreach ($n in $nodes) {
  if (-not $nodeTypeCounts.ContainsKey($n.type)) { $nodeTypeCounts[$n.type] = 0 }
  $nodeTypeCounts[$n.type]++
}

$edgeTypeCounts = @{}
foreach ($e in $edges) {
  if (-not $edgeTypeCounts.ContainsKey($e.type)) { $edgeTypeCounts[$e.type] = 0 }
  $edgeTypeCounts[$e.type]++
}

$graph = [ordered]@{
  meta = [ordered]@{
    name = "Colon vs BRCA Repurposing Graph"
    sources = @(
      "models/admet_results/final_drug_candidates.csv",
      "20260414_re_pre_project_v3/step4_results/step6_final/repurposing_top15.csv"
    )
    counts = [ordered]@{
      node_total = $nodes.Count
      edge_total = $edges.Count
      node_by_type = $nodeTypeCounts
      edge_by_type = $edgeTypeCounts
      overlap_drug_count = $overlapNorms.Count
    }
    overlap_drug_norms = $overlapNorms
  }
  nodes = $nodes
  edges = $edges
}

$json = $graph | ConvertTo-Json -Depth 12
Set-Content -Path $outJson -Value $json -Encoding utf8

Write-Host "Wrote $outJson"
Write-Host ("Nodes: {0} | Edges: {1}" -f $nodes.Count, $edges.Count)
