param(
  [string]$RunId = "20260418_crc_v1",
  [string]$OutputPath = "colon_pipeline_dashboard_data.js"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing required file: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Get-OptionalProp {
  param(
    [Parameter(Mandatory = $true)]$Obj,
    [Parameter(Mandatory = $true)][string]$Name,
    $DefaultValue = $null
  )
  if ($null -eq $Obj) {
    return $DefaultValue
  }
  if ($Obj.PSObject.Properties.Name -contains $Name) {
    return $Obj.$Name
  }
  return $DefaultValue
}

$root = $PSScriptRoot

$ensemble = Read-JsonFile (Join-Path $root "models\ensemble_results\ensemble_results.json")
$metabric = Read-JsonFile (Join-Path $root "models\metabric_results\step6_metabric_results.json")
$admet = Read-JsonFile (Join-Path $root "models\admet_results\step7_admet_results.json")
$ml = Read-JsonFile (Join-Path $root "models\ml_results\ml_results.json")
$dl = Read-JsonFile (Join-Path $root "models\dl_results\dl_results.json")
$graph = Read-JsonFile (Join-Path $root "models\graph_results\graph_results.json")
$qc = Read-JsonFile (Join-Path $root "runs\$RunId\fe_inputs\join_qc_report.json")
$man = Read-JsonFile (Join-Path $root "runs\$RunId\features\manifest.json")
$pair = Read-JsonFile (Join-Path $root "runs\$RunId\pair_features\feature_manifest.json")

$mlSimple = @($ml | Select-Object model, spearman_mean, rmse_mean, pearson_mean, r2_mean)
$dlSimple = @($dl | Select-Object model, spearman_mean, rmse_mean, pearson_mean, r2_mean)
$graphSimple = @($graph | Select-Object model, spearman_mean, rmse_mean, p_at_20_mean, auroc_mean)
$step6Simple = @($metabric.top15_validated | Select-Object final_rank, drug_name, target, pathway, mean_pred_ic50, sensitivity_rate, validation_score)
$step7Simple = @($admet.final_candidates | Select-Object final_rank, drug_name, target, pathway, pred_ic50, safety_score, combined_score, category, flags)
$all30ByDrugId = @{}
foreach ($row in $metabric.all_30_scores) {
  $k = [string]$row.drug_id
  if (-not $all30ByDrugId.ContainsKey($k)) {
    $all30ByDrugId[$k] = $row
  }
}

$top30Simple = @(
  $ensemble.top30_drugs | ForEach-Object {
    $rankVal = $null
    if ($_.PSObject.Properties.Name -contains "final_rank") {
      $rankVal = $_.final_rank
    } elseif ($_.PSObject.Properties.Name -contains "rank") {
      $rankVal = $_.rank
    }
    $did = [string]$_.drug_id
    $meta = $null
    if ($all30ByDrugId.ContainsKey($did)) {
      $meta = $all30ByDrugId[$did]
    }
    [pscustomobject]@{
      final_rank = $rankVal
      drug_id = $_.drug_id
      drug_name = if ($meta) { $meta.drug_name } else { $null }
      target = if ($meta) { $meta.target } else { $null }
      pathway = if ($meta) { $meta.pathway } else { $null }
      mean_pred_ic50 = $_.mean_pred_ic50
      mean_true_ic50 = $_.mean_true_ic50
      sensitivity_rate = $_.sensitivity_rate
      n_samples = $_.n_samples
      category = $_.category
    }
  }
)

$p15 = $metabric.method_c.precision_at_k.PSObject.Properties["P@15"].Value.precision
$p20 = $metabric.method_c.precision_at_k.PSObject.Properties["P@20"].Value.precision

$result = [ordered]@{
  run_id = $qc.run_id
  generated_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  qc = [ordered]@{
    label_pair_rows = $qc.label_to_feature_join_qc.label_pair_rows
    unmatched_samples = $qc.label_to_feature_join_qc.unmatched_samples
    unmatched_drugs = $qc.label_to_feature_join_qc.unmatched_drugs
    join_rate_samples = $qc.label_to_feature_join_qc.join_rate_samples
    join_rate_drugs = $qc.label_to_feature_join_qc.join_rate_drugs
    labels_unique_samples = $qc.labels_qc.labels_unique_samples
    labels_unique_drugs = $qc.labels_qc.labels_unique_drugs
    sample_features_rows = $qc.sample_qc.sample_features_rows
    sample_features_cols = $qc.sample_qc.sample_features_cols
    drug_features_rows = $qc.drug_qc.drug_features_rows
    missing_smiles_rows = $qc.drug_qc.missing_smiles_rows
    missing_smiles_rate = $qc.drug_qc.missing_smiles_rate
    smiles_matched_by_drug_id = Get-OptionalProp -Obj $qc.drug_qc -Name "smiles_matched_by_drug_id" -DefaultValue $null
    smiles_backfilled_by_name = Get-OptionalProp -Obj $qc.drug_qc -Name "smiles_backfilled_by_name" -DefaultValue $null
    smiles_unresolved_after_backfill = Get-OptionalProp -Obj $qc.drug_qc -Name "smiles_unresolved_after_backfill" -DefaultValue $null
    smiles_backfill_policy = Get-OptionalProp -Obj $qc.drug_qc -Name "smiles_backfill_policy" -DefaultValue $null
  }
  features = [ordered]@{
    features_rows = $man.row_counts.features_rows
    features_cols = $man.row_counts.features_cols
    labels_rows = $man.row_counts.labels_rows
    pair_rows = $pair.row_counts.pairs
    pair_newfe_rows = $pair.row_counts.pair_features_newfe_rows
    pair_newfe_v2_rows = $pair.row_counts.pair_features_newfe_v2_rows
    target_missing_drug_count = $pair.feature_groups.pair_target.qc.target_missing_drug_count
    target_overlap_mean = $pair.feature_groups.pair_target.qc.target_overlap_count_summary.mean
    target_overlap_max = $pair.feature_groups.pair_target.qc.target_overlap_count_summary.max
    target_expr_mean = $pair.feature_groups.pair_target.qc.target_expr_mean_summary.mean
  }
  ensemble = [ordered]@{
    spearman = $ensemble.ensemble_metrics.spearman_mean
    rmse = $ensemble.ensemble_metrics.rmse_mean
    pearson = $ensemble.ensemble_metrics.pearson
    r2 = $ensemble.ensemble_metrics.r2
    weights = $ensemble.weights
  }
  metabric = [ordered]@{
    target_expressed = "$($metabric.method_a.n_targets_expressed)/$($metabric.method_a.n_total)"
    survival_significant = $metabric.method_b.n_significant
    p_at_15 = $p15
    p_at_20 = $p20
  }
  models = [ordered]@{
    ml = $mlSimple
    dl = $dlSimple
    graph = $graphSimple
  }
  step6 = $step6Simple
  step7 = $step7Simple
  top30 = $top30Simple
}

$json = $result | ConvertTo-Json -Depth 12
$js = "window.COLON_DASHBOARD_DATA = $json;`n"
$out = Join-Path $root $OutputPath
Set-Content -LiteralPath $out -Value $js -Encoding utf8

Write-Output "Generated: $out"
