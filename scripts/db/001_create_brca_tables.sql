-- BRCA PostgreSQL schema for run BRCA_RELEASE_V1
-- Idempotent DDL with named unique constraints for deterministic upserts.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS brca_load_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    table_name TEXT NOT NULL,
    file_name TEXT,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_brca_load_audit UNIQUE (disease, run_id, source_s3_uri, table_name, status)
);

CREATE TABLE IF NOT EXISTS run_manifest (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    manifest_name TEXT NOT NULL,
    manifest_sha256 TEXT,
    manifest_json JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_run_manifest UNIQUE (disease, run_id, source_s3_uri, manifest_name)
);

CREATE TABLE IF NOT EXISTS source_artifact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    artifact_name TEXT NOT NULL DEFAULT '',
    artifact_type TEXT,
    artifact_uri TEXT NOT NULL DEFAULT '',
    artifact_hash TEXT,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_source_artifact UNIQUE (disease, run_id, source_s3_uri, artifact_name, artifact_uri)
);

CREATE TABLE IF NOT EXISTS drug_candidate_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_drug_candidate_result UNIQUE (disease, run_id, source_s3_uri, drug_id, drug_name, rank)
);

CREATE TABLE IF NOT EXISTS drug_candidate_tier (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    tier TEXT NOT NULL DEFAULT '',
    score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_drug_candidate_tier UNIQUE (disease, run_id, source_s3_uri, drug_id, drug_name, rank, tier)
);

CREATE TABLE IF NOT EXISTS final_candidate_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    final_verdict TEXT,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_final_candidate_result UNIQUE (disease, run_id, source_s3_uri, drug_id, drug_name, rank)
);

CREATE TABLE IF NOT EXISTS admet_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    admet_verdict TEXT,
    hard_fail BOOLEAN,
    score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_admet_result UNIQUE (disease, run_id, source_s3_uri, drug_id, drug_name, rank)
);

CREATE TABLE IF NOT EXISTS admet_assay_match (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    assay_name TEXT NOT NULL DEFAULT '',
    match_value TEXT,
    match_score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_admet_assay_match UNIQUE (disease, run_id, source_s3_uri, drug_id, drug_name, assay_name)
);

CREATE TABLE IF NOT EXISTS admet_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    summary_key TEXT NOT NULL,
    summary_value TEXT,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_admet_summary UNIQUE (disease, run_id, source_s3_uri, summary_key)
);

CREATE TABLE IF NOT EXISTS external_validation_result (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    validation_source TEXT NOT NULL DEFAULT '',
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    validation_score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_external_validation_result UNIQUE (disease, run_id, source_s3_uri, validation_source, drug_id, drug_name, rank)
);

CREATE TABLE IF NOT EXISTS metabric_method_score (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT '',
    drug_id TEXT NOT NULL DEFAULT '',
    drug_name TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT -1,
    score DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_metabric_method_score UNIQUE (disease, run_id, source_s3_uri, method, drug_id, drug_name, rank)
);

CREATE TABLE IF NOT EXISTS model_metric (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    metric TEXT NOT NULL DEFAULT '',
    metric_value DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_model_metric UNIQUE (disease, run_id, source_s3_uri, model, metric)
);

CREATE TABLE IF NOT EXISTS model_metric_detailed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    split TEXT NOT NULL DEFAULT '',
    metric TEXT NOT NULL DEFAULT '',
    metric_value DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_model_metric_detailed UNIQUE (disease, run_id, source_s3_uri, model, split, metric)
);

CREATE TABLE IF NOT EXISTS ensemble_metric (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    metric TEXT NOT NULL DEFAULT '',
    metric_value DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ensemble_metric UNIQUE (disease, run_id, source_s3_uri, metric)
);

CREATE TABLE IF NOT EXISTS ensemble_source_manifest (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disease TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source_s3_uri TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',
    source_uri TEXT NOT NULL DEFAULT '',
    weight DOUBLE PRECISION,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ensemble_source_manifest UNIQUE (disease, run_id, source_s3_uri, model, source_name, source_uri)
);

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'brca_load_audit',
        'run_manifest',
        'source_artifact',
        'drug_candidate_result',
        'drug_candidate_tier',
        'final_candidate_result',
        'admet_result',
        'admet_assay_match',
        'admet_summary',
        'external_validation_result',
        'metabric_method_score',
        'model_metric',
        'model_metric_detailed',
        'ensemble_metric',
        'ensemble_source_manifest'
    ]
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_updated_at ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t, t);
    END LOOP;
END;
$$;
