param(
  [string]$RunId = "20260420_crc_split_v2",
  [string]$BaselineRunId = "20260418_crc_v1",
  [string]$OutputPath = "crc_results_dashboard_split_data.js"
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

function Read-CsvFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing required file: $Path"
  }
  return Import-Csv -LiteralPath $Path
}

function Get-ModelOkCount {
  param($Obj)
  if ($null -eq $Obj) { return 0 }
  $count = 0
  foreach ($p in $Obj.PSObject.Properties) {
    if ([string]$p.Value -eq "ok") { $count += 1 }
  }
  return $count
}

function Get-SkippedReason {
  param($Obj)
  if ($null -eq $Obj) { return $null }
  if ($Obj.PSObject.Properties.Name -contains "skipped") {
    return [string]$Obj.skipped
  }
  return $null
}

function Build-CohortData {
  param(
    [Parameter(Mandatory = $true)][string]$Cohort,
    [Parameter(Mandatory = $true)]$RunSummary,
    [Parameter(Mandatory = $true)]$PipelineStatus,
    [Parameter(Mandatory = $true)][string]$BaseDir
  )

  $cohortSummary = $RunSummary.cohorts.$Cohort
  $cohortStatus = $PipelineStatus.cohorts.$Cohort
  $cohortRoot = Split-Path -Parent $BaseDir

  $splitManifest = Read-JsonFile (Join-Path $cohortRoot "raw_inputs\split_manifest.json")
  $joinQc = Read-JsonFile (Join-Path $cohortRoot "fe_inputs\join_qc_report.json")
  $featuresManifest = Read-JsonFile (Join-Path $cohortRoot "features\manifest.json")
  $pairManifest = Read-JsonFile (Join-Path $cohortRoot "pair_features\feature_manifest.json")

  $ensemble = Read-JsonFile (Join-Path $BaseDir "ensemble_results\ensemble_results.json")
  $step7 = Read-JsonFile (Join-Path $BaseDir "admet_results\step7_admet_results.json")
  $finalCsv = Read-CsvFile (Join-Path $BaseDir "admet_results\final_drug_candidates.csv")

  if ($Cohort -eq "colon") {
    $step6 = Read-JsonFile (Join-Path $BaseDir "crc_external_results\step6_crc_external_results.json")
    $targetExpr = "{0}/{1}" -f $step6.method_a_tcga_expression.n_targets_expressed, $step6.method_a_tcga_expression.n_total
    $p15 = [double]$step6.method_c_known_crc_precision.'P@15'.precision
    $p20 = [double]$step6.method_c_known_crc_precision.'P@20'.precision
    $step6Type = "TCGA-COAD + GSE39582"
  }
  else {
    $step6 = Read-JsonFile (Join-Path $BaseDir "metabric_results\step6_metabric_results.json")
    $targetExpr = "{0}/{1}" -f $step6.method_a.n_targets_expressed, $step6.method_a.n_total
    $p15 = [double]$step6.method_c.precision_at_k.'P@15'.precision
    $p20 = [double]$step6.method_c.precision_at_k.'P@20'.precision
    $step6Type = "METABRIC"
  }

  $candidateCount = @($step7.final_candidates | Where-Object { $_.category -eq "Candidate" }).Count
  $approvedCount = @($step7.final_candidates | Where-Object { $_.category -eq "Approved" }).Count

  $weights = [ordered]@{}
  foreach ($p in $ensemble.weights.PSObject.Properties) {
    $weights[$p.Name] = [double]$p.Value
  }

  $mlOk = Get-ModelOkCount $cohortStatus.ml
  $dlOk = Get-ModelOkCount $cohortStatus.dl
  $graphOk = Get-ModelOkCount $cohortStatus.graph
  $mlSkip = Get-SkippedReason $cohortStatus.ml
  $dlSkip = Get-SkippedReason $cohortStatus.dl
  $graphSkip = Get-SkippedReason $cohortStatus.graph

  $top5 = @(
    $finalCsv |
      Select-Object -First 5 final_rank,drug_name,target,pathway,pred_ic50,combined_score,category
  )

  $stageTables = @(
    [ordered]@{
      stage = "Stage0 Raw Cohort Split"
      input_tables = "label, sample, drug, lincs, drug_target (raw full)"
      output_tables = "raw_inputs/*.parquet"
      row_summary = "label $($splitManifest.row_counts.label_before) -> $($splitManifest.row_counts.label_after), sample $($splitManifest.row_counts.sample_before) -> $($splitManifest.row_counts.sample_after)"
      feature_summary = "cohort retention " + ([math]::Round([double]$splitManifest.cohort_filter.retention_rate * 100, 2)) + "%"
      note = "rule mode: $($splitManifest.cohort_filter.mode)"
    }
    [ordered]@{
      stage = "Stage1 FE Input Build"
      input_tables = "raw_inputs/label + sample + drug"
      output_tables = "fe_inputs/sample_features, drug_features, labels"
      row_summary = "label_pair=$($joinQc.label_to_feature_join_qc.label_pair_rows), sample_rows=$($joinQc.sample_qc.sample_features_rows), drug_rows=$($joinQc.drug_qc.drug_features_rows)"
      feature_summary = "sample_cols=$($joinQc.sample_qc.sample_features_cols), drug_cols=$($joinQc.drug_qc.drug_features_cols)"
      note = "sample join_rate=" + ([math]::Round([double]$joinQc.label_to_feature_join_qc.join_rate_samples * 100, 2)) + "%"
    }
    [ordered]@{
      stage = "Stage2 Training Feature Matrix"
      input_tables = "fe_inputs/sample_features + drug_features + labels"
      output_tables = "features/features.parquet + features/labels.parquet"
      row_summary = "features_rows=$($featuresManifest.row_counts.features_rows), labels_rows=$($featuresManifest.row_counts.labels_rows)"
      feature_summary = "features_cols=$($featuresManifest.row_counts.features_cols)"
      note = "dropped_low_variance_columns=$($featuresManifest.filters.dropped_low_variance_columns.Count)"
    }
    [ordered]@{
      stage = "Stage3 Pair Feature Engineering"
      input_tables = "features + pair sources(lincs, target, chem)"
      output_tables = "pair_features/pair_features_newfe_v2.parquet"
      row_summary = "pairs=$($pairManifest.row_counts.pair_features_newfe_v2_rows)"
      feature_summary = "lincs_metrics=$($pairManifest.feature_groups.pair_lincs.metrics.Count), target_cols=$($pairManifest.feature_groups.pair_target.columns.Count)"
      note = "invalid_smiles_ratio=" + ([math]::Round([double]$pairManifest.feature_groups.drug_chem.invalid_smiles_qc.invalid_smiles_ratio * 100, 2)) + "%"
    }
    [ordered]@{
      stage = "Stage4 Model Bank (ML/DL/Graph)"
      input_tables = "features + pair_features + labels"
      output_tables = "model_results/ml_results.json, dl_results.json, graph_results.json"
      row_summary = "ML=$mlOk, DL=$dlOk, Graph=$graphOk"
      feature_summary = "same model input matrix from Stage2+3"
      note = "skip_flags: ml=$mlSkip, dl=$dlSkip, graph=$graphSkip"
    }
    [ordered]@{
      stage = "Stage5 Ensemble"
      input_tables = "Stage4 model outputs"
      output_tables = "ensemble_results.json + top30_drugs.csv + top15_drugs.csv"
      row_summary = "top30=$(@($ensemble.top30_drugs).Count), top15=$(@($ensemble.top15_drugs).Count)"
      feature_summary = "ensemble_n_models=$($ensemble.n_models), spearman=" + ([math]::Round([double]$ensemble.ensemble_metrics.spearman_mean, 4))
      note = "method=spearman_weighted_average"
    }
    [ordered]@{
      stage = "Stage6 External Validation"
      input_tables = "top30_drugs + external cohort datasets"
      output_tables = "top15_validated.csv + step6 results json"
      row_summary = "validated_top15=$(@($step6.top15_validated).Count)"
      feature_summary = "target_expressed=$targetExpr, P@15=" + ([math]::Round([double]$p15, 4))
      note = "set=$step6Type"
    }
    [ordered]@{
      stage = "Stage7 ADMET Gate"
      input_tables = "top15_validated + drug safety profiles"
      output_tables = "final_drug_candidates.csv + step7_admet_results.json"
      row_summary = "input=$($step7.n_drugs_input), output=$($step7.n_drugs_output), assays=$($step7.n_assays)"
      feature_summary = "approved=$approvedCount, candidate=$candidateCount"
      note = "final score = efficacy + safety composite"
    }
  )

  return [ordered]@{
    cohort = $Cohort
    split_counts = $cohortSummary.split_row_counts
    features = $cohortSummary.features
    labels = $cohortSummary.labels
    pair_features = $cohortSummary.pair_features_row_counts
    chem_qc = $cohortSummary.chem_qc
    pipeline = [ordered]@{
      ml_ok_count = $mlOk
      dl_ok_count = $dlOk
      graph_ok_count = $graphOk
      ml_skipped_reason = $mlSkip
      dl_skipped_reason = $dlSkip
      graph_skipped_reason = $graphSkip
      ml_results_exists = (Test-Path (Join-Path $BaseDir "ml_results.json"))
      dl_results_exists = (Test-Path (Join-Path $BaseDir "dl_results.json"))
      graph_results_exists = (Test-Path (Join-Path $BaseDir "graph_results.json"))
      ensemble_ok = [bool]$cohortStatus.ensemble.ok
      step6_ok = [bool]$cohortStatus.step6.ok
      step7_ok = [bool]$cohortStatus.step7.ok
      ensemble_error = $cohortStatus.ensemble.error
      step6_error = $cohortStatus.step6.error
      step7_error = $cohortStatus.step7.error
      run_mode = $cohortStatus.ensemble.mode
    }
    ensemble = [ordered]@{
      n_models = [int]$ensemble.n_models
      spearman = [double]$ensemble.ensemble_metrics.spearman_mean
      rmse = [double]$ensemble.ensemble_metrics.rmse_mean
      pearson = [double]$ensemble.ensemble_metrics.pearson
      r2 = [double]$ensemble.ensemble_metrics.r2
      weights = $weights
    }
    step6 = [ordered]@{
      type = $step6Type
      top15_count = @($step6.top15_validated).Count
      target_expressed = $targetExpr
      precision_at_15 = $p15
      precision_at_20 = $p20
    }
    step7 = [ordered]@{
      n_assays = [int]$step7.n_assays
      n_input = [int]$step7.n_drugs_input
      n_output = [int]$step7.n_drugs_output
      candidate_count = $candidateCount
      approved_count = $approvedCount
      top5 = $top5
    }
    stage_tables = $stageTables
  }
}

$root = $PSScriptRoot
$runBase = Join-Path $root ("runs\" + $RunId)

$runSummary = Read-JsonFile (Join-Path $runBase "run_summary.json")
$colonStatus = Read-JsonFile (Join-Path $runBase "remaining_pipeline_status_colon.json")
$rectalStatus = Read-JsonFile (Join-Path $runBase "remaining_pipeline_status_rectal.json")

$colonData = Build-CohortData -Cohort "colon" -RunSummary $runSummary -PipelineStatus $colonStatus -BaseDir (Join-Path $runBase "colon\model_results")
$rectalData = Build-CohortData -Cohort "rectal" -RunSummary $runSummary -PipelineStatus $rectalStatus -BaseDir (Join-Path $runBase "rectal\model_results")

$baseline = $null
$baselineBase = Join-Path $root ("runs\" + $BaselineRunId)
$baselineManifestPath = Join-Path $baselineBase "features\manifest.json"
$baselineJoinQcPath = Join-Path $baselineBase "fe_inputs\join_qc_report.json"
$baselinePairPath = Join-Path $baselineBase "pair_features\feature_manifest.json"
if ((Test-Path $baselineManifestPath) -and (Test-Path $baselineJoinQcPath) -and (Test-Path $baselinePairPath)) {
  $bMan = Read-JsonFile $baselineManifestPath
  $bQc = Read-JsonFile $baselineJoinQcPath
  $bPair = Read-JsonFile $baselinePairPath

  $baseline = [ordered]@{
    run_id = $BaselineRunId
    features_rows = [int]$bMan.row_counts.features_rows
    features_cols = [int]$bMan.row_counts.features_cols
    labels_rows = [int]$bMan.row_counts.labels_rows
    labels_unique_samples = [int]$bQc.labels_qc.labels_unique_samples
    labels_unique_drugs = [int]$bQc.labels_qc.labels_unique_drugs
    join_rate_samples = [double]$bQc.label_to_feature_join_qc.join_rate_samples
    pair_rows = [int]$bPair.row_counts.pair_features_newfe_v2_rows
  }
}

$result = [ordered]@{
  run_id = $RunId
  generated_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  baseline_integrated_crc = $baseline
  master_table = $runSummary.master_table
  cohorts = [ordered]@{
    colon = $colonData
    rectal = $rectalData
  }
}

$json = $result | ConvertTo-Json -Depth 15
$js = "window.CRC_SPLIT_DASHBOARD_DATA = $json;`n"
$out = Join-Path $root $OutputPath
Set-Content -LiteralPath $out -Value $js -Encoding utf8

Write-Output "Generated: $out"
