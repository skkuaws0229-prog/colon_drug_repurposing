#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * Feature Engineering Pipeline for Drug Response Prediction
 * Project: 20260408_pre_project_biso_myprotocol
 *
 * Steps:
 *   1. prepare_fe_inputs   — Bridge preprocessing (labels, sample features, drug features)
 *   2. build_features      — Main FE: merge sample+drug+labels, impute, filter, normalize
 *   3. build_pair_features — Advanced FE: pathway + chemistry + LINCS + target features
 */

// ── Processes ──────────────────────────────────────────────

process prepare_fe_inputs {
    tag "prepare_inputs_${params.run_id}"

    input:
    val ready

    output:
    path 'fe_inputs/', emit: fe_inputs_dir

    script:
    """
    mkdir -p fe_inputs
    python3 /workspace/nextflow/scripts/prepare_fe_inputs.py \
        --label-uri '${params.gdsc_ic50_uri}' \
        --drug-uri '${params.drug_features_uri}' \
        --sample-uri '${params.depmap_crispr_long_uri}' \
        --output-prefix fe_inputs \
        --run-id '${params.run_id}' \
        --binary-quantile ${params.binary_quantile}
    """
}

process build_features {
    tag "build_features_${params.run_id}"

    input:
    path fe_inputs_dir

    output:
    path 'features/', emit: features_dir

    script:
    """
    mkdir -p features
    python3 /workspace/nextflow/scripts/build_features.py \
        --sample-features '${fe_inputs_dir}/sample_features.parquet' \
        --drug-features '${fe_inputs_dir}/drug_features.parquet' \
        --labels '${fe_inputs_dir}/labels.parquet' \
        --output-dir features \
        --run-id '${params.run_id}'
    """
}

process build_pair_features {
    tag "pair_features_${params.run_id}"

    input:
    path features_dir

    output:
    path 'pair_features/', emit: pair_features_dir

    script:
    """
    mkdir -p pair_features
    python3 /workspace/nextflow/scripts/build_pair_features_newfe_v2.py \
        --features-dir '${features_dir}' \
        --lincs-uri '${params.lincs_mcf7_uri}' \
        --msigdb-uri '${params.msigdb_membership_uri}' \
        --string-uri '${params.string_links_uri}' \
        --opentargets-uri '${params.opentargets_uri}' \
        --output-dir pair_features \
        --run-id '${params.run_id}'
    """
}

process upload_results {
    tag "upload_${params.run_id}"

    input:
    path pair_features_dir

    script:
    """
    aws s3 cp --recursive '${pair_features_dir}' \
        '${params.fe_output_dir}/${params.run_id}/'
    echo "Uploaded to ${params.fe_output_dir}/${params.run_id}/"
    """
}

// ── Workflow ────────────────────────────────────────────────

workflow {
    // Trigger channel
    start_ch = Channel.of('start')

    // Step 1: Prepare FE inputs
    prepare_fe_inputs(start_ch)

    // Step 2: Build base features
    build_features(prepare_fe_inputs.out.fe_inputs_dir)

    // Step 3: Build pair features (advanced FE)
    build_pair_features(build_features.out.features_dir)

    // Step 4: Upload results to S3
    upload_results(build_pair_features.out.pair_features_dir)
}
