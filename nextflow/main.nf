#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * Feature Engineering Pipeline for Drug Response Prediction
 * Project: 20260408_pre_project_biso_myprotocol
 *
 * Steps:
 *   0. split_raw_inputs    -> Split raw tables by cohort YAML (parallel per cohort)
 *   1. prepare_fe_inputs   -> Bridge preprocessing (labels, sample features, drug features)
 *   2. build_features      -> Main FE: merge sample+drug+labels, impute, filter, normalize
 *   3. build_pair_features -> Advanced FE: pathway + chemistry + LINCS + target features
 *   4. upload_results      -> Upload all outputs to S3
 */

def resolveCohorts() {
    def cohortsArg = (params.cohorts ?: "").toString().trim()
    if (cohortsArg) {
        return cohortsArg.split(",").collect { it.trim() }.findAll { it }
    }
    def single = (params.cohort_name ?: "").toString().trim()
    if (single) {
        return [single]
    }
    return [""]
}

process split_raw_inputs {
    tag "split_raw_${params.run_id}_${cohort_name ?: 'all'}"

    input:
    val cohort_name

    output:
    tuple val(cohort_name), path('cohort_raw/'), emit: raw_dir

    script:
    """
    mkdir -p cohort_raw

    python3 /workspace/nextflow/scripts/split_cohort_raw_inputs.py \\
        --label-uri '${params.gdsc_ic50_uri}' \\
        --sample-uri '${params.depmap_crispr_long_uri}' \\
        --drug-uri '${params.drug_features_uri}' \\
        --lincs-drug-signature-uri '${params.lincs_drug_sig_uri}' \\
        --drug-target-uri '${params.drug_target_uri}' \\
        --cohort-yaml '${params.cohort_yaml}' \\
        --cohort-name '${cohort_name}' \\
        --out-dir cohort_raw \\
        --run-id '${params.run_id}'
    """
}

process prepare_fe_inputs {
    tag "prepare_inputs_${params.run_id}_${cohort_name ?: 'all'}"

    input:
    tuple val(cohort_name), path(raw_dir)

    output:
    tuple val(cohort_name), path('fe_inputs/'), emit: fe_inputs_dir

    script:
    """
    mkdir -p fe_inputs
    RUN_ID='${params.run_id}'
    if [ -n '${cohort_name}' ]; then
      RUN_ID="\${RUN_ID}_${cohort_name}"
    fi

    python3 /workspace/nextflow/scripts/prepare_fe_inputs.py \\
        --label-uri '${raw_dir}/label.parquet' \\
        --drug-uri '${raw_dir}/drug.parquet' \\
        --sample-uri '${raw_dir}/sample.parquet' \\
        --output-prefix fe_inputs \\
        --run-id "\${RUN_ID}" \\
        --binary-quantile ${params.binary_quantile}
    """
}

process build_features {
    tag "build_features_${params.run_id}_${cohort_name ?: 'all'}"

    input:
    tuple val(cohort_name), path(fe_inputs_dir)

    output:
    tuple val(cohort_name), path('features/'), emit: features_dir

    script:
    """
    mkdir -p features
    RUN_ID='${params.run_id}'
    if [ -n '${cohort_name}' ]; then
      RUN_ID="\${RUN_ID}_${cohort_name}"
    fi

    python3 /workspace/nextflow/scripts/build_features.py \\
        --sample-feature-uri '${fe_inputs_dir}/sample_features.parquet' \\
        --drug-feature-uri '${fe_inputs_dir}/drug_features.parquet' \\
        --label-uri '${fe_inputs_dir}/labels.parquet' \\
        --out-features features/features.parquet \\
        --out-labels features/labels.parquet \\
        --out-manifest features/manifest.json \\
        --run-id "\${RUN_ID}"
    """
}

process build_pair_features {
    tag "pair_features_${params.run_id}_${cohort_name ?: 'all'}"

    input:
    tuple val(cohort_name), path(features_dir), path(fe_inputs_dir), path(raw_dir)

    output:
    tuple val(cohort_name), path('pair_features/'), emit: pair_features_dir

    script:
    """
    mkdir -p pair_features
    RUN_ID='${params.run_id}'
    if [ -n '${cohort_name}' ]; then
      RUN_ID="\${RUN_ID}_${cohort_name}"
    fi

    python3 /workspace/nextflow/scripts/build_pair_features_newfe_v2.py \\
        --pairs-uri '${features_dir}/labels.parquet' \\
        --sample-expression-uri '${fe_inputs_dir}/sample_features.parquet' \\
        --drug-uri '${fe_inputs_dir}/drug_features.parquet' \\
        --lincs-drug-signature-uri '${raw_dir}/lincs_drug_signature.parquet' \\
        --drug-target-uri '${raw_dir}/drug_target.parquet' \\
        --chem-feature-mode '${params.chem_feature_mode ?: "auto"}' \\
        --min-morgan-bit-density ${params.min_morgan_bit_density ?: 0.02} \\
        --smiles-col smiles \\
        --out-dir pair_features \\
        --run-id "\${RUN_ID}"
    """
}

process upload_results {
    tag "upload_${params.run_id}_${cohort_name ?: 'all'}"

    input:
    tuple val(cohort_name), path(features_dir), path(pair_features_dir)

    script:
    """
    RUN_KEY='${params.run_id}'
    if [ -n '${cohort_name}' ]; then
      RUN_KEY="\${RUN_KEY}_${cohort_name}"
    fi

    aws s3 cp --recursive '${features_dir}' \\
        '${params.fe_output_dir}/'"\${RUN_KEY}"'/features/'
    aws s3 cp --recursive '${pair_features_dir}' \\
        '${params.fe_output_dir}/'"\${RUN_KEY}"'/pair_features/'
    echo "Uploaded to ${params.fe_output_dir}/\${RUN_KEY}/"
    """
}

workflow {
    cohorts = resolveCohorts()
    println "[workflow] cohorts = ${cohorts}"

    cohort_ch = Channel.fromList(cohorts)

    // Step 0: split raw data by cohort (parallel)
    split_raw_inputs(cohort_ch)
    raw_dirs = split_raw_inputs.out.raw_dir

    // Step 1: prepare FE inputs
    prepare_fe_inputs(raw_dirs)
    fe_inputs = prepare_fe_inputs.out.fe_inputs_dir

    // Step 2: build base features
    build_features(fe_inputs)
    features = build_features.out.features_dir

    // Step 3: build pair features (needs cohort-specific raw aux tables)
    pair_inputs = features.join(fe_inputs).join(raw_dirs)
    build_pair_features(pair_inputs)
    pair_features = build_pair_features.out.pair_features_dir

    // Step 4: upload
    upload_inputs = features.join(pair_features)
    upload_results(upload_inputs)
}
