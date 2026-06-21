CREATE TABLE IF NOT EXISTS ontology_concepts (
    concept_id SERIAL PRIMARY KEY,
    ontology_name TEXT NOT NULL,
    ontology_id TEXT NOT NULL,
    concept_type TEXT NOT NULL,
    preferred_name TEXT NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (ontology_name, ontology_id)
);

CREATE TABLE IF NOT EXISTS ontology_synonyms (
    synonym_id SERIAL PRIMARY KEY,
    concept_id INT REFERENCES ontology_concepts(concept_id),
    synonym TEXT NOT NULL,
    synonym_type TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entity_mappings (
    mapping_id SERIAL PRIMARY KEY,
    source_dataset TEXT NOT NULL,
    raw_entity_name TEXT NOT NULL,
    raw_entity_type TEXT NOT NULL,
    normalized_name TEXT,
    ontology_name TEXT,
    ontology_id TEXT,
    canonical_name TEXT,
    mapping_confidence TEXT,
    match_type TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ontology_relationships (
    relationship_id SERIAL PRIMARY KEY,
    subject_ontology_name TEXT NOT NULL,
    subject_ontology_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_ontology_name TEXT NOT NULL,
    object_ontology_id TEXT NOT NULL,
    source TEXT,
    evidence_level TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dataset_registry (
    dataset_id SERIAL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    disease TEXT,
    source_system TEXT,
    s3_uri TEXT NOT NULL,
    file_format TEXT,
    version TEXT,
    schema_json JSONB,
    row_count BIGINT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feature_registry (
    feature_id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    feature_group TEXT,
    source_dataset TEXT,
    disease TEXT,
    data_type TEXT,
    is_leakage_risk BOOLEAN DEFAULT FALSE,
    leakage_reason TEXT,
    used_in_training BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    pipeline_run_id SERIAL PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    disease TEXT,
    input_s3_uri TEXT,
    output_s3_uri TEXT,
    config_json JSONB,
    status TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_runs (
    run_id SERIAL PRIMARY KEY,
    disease TEXT NOT NULL,
    model_name TEXT NOT NULL,
    split_strategy TEXT,
    target_column TEXT,
    training_table_s3_uri TEXT,
    metrics_json JSONB,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_predictions (
    prediction_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES model_runs(run_id),
    disease TEXT NOT NULL,
    drug_id TEXT,
    drug_name TEXT,
    cell_line_id TEXT,
    cell_line_name TEXT,
    subtype TEXT,
    predicted_ln_ic50 DOUBLE PRECISION,
    predicted_rank INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_rankings (
    candidate_id SERIAL PRIMARY KEY,
    disease TEXT NOT NULL,
    subtype TEXT,
    drug_id TEXT,
    drug_name TEXT,
    model_score DOUBLE PRECISION,
    admet_score DOUBLE PRECISION,
    lincs_reversal_score DOUBLE PRECISION,
    evidence_score DOUBLE PRECISION,
    final_score DOUBLE PRECISION,
    rank INT,
    decision TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_evidence (
    evidence_id SERIAL PRIMARY KEY,
    disease TEXT,
    drug_id TEXT,
    drug_name TEXT,
    evidence_type TEXT,
    evidence_source TEXT,
    evidence_text TEXT,
    evidence_score DOUBLE PRECISION,
    source_uri TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admet_filter_results (
    admet_id SERIAL PRIMARY KEY,
    drug_id TEXT,
    drug_name TEXT,
    pass_admet BOOLEAN,
    herg_risk DOUBLE PRECISION,
    dili_risk DOUBLE PRECISION,
    ames_risk DOUBLE PRECISION,
    h_ht_risk DOUBLE PRECISION,
    lipinski_violations INT,
    tpsa DOUBLE PRECISION,
    logp DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lincs_reversal_results (
    lincs_id SERIAL PRIMARY KEY,
    disease TEXT,
    drug_id TEXT,
    drug_name TEXT,
    signature_id TEXT,
    reversal_score DOUBLE PRECISION,
    cosine_score DOUBLE PRECISION,
    pearson_score DOUBLE PRECISION,
    spearman_score DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ontology_concepts_name_type ON ontology_concepts (ontology_name, concept_type);
CREATE INDEX IF NOT EXISTS idx_ontology_concepts_preferred_name ON ontology_concepts (preferred_name);
CREATE INDEX IF NOT EXISTS idx_ontology_synonyms_synonym ON ontology_synonyms (synonym);
CREATE INDEX IF NOT EXISTS idx_ontology_synonyms_concept_id ON ontology_synonyms (concept_id);

CREATE INDEX IF NOT EXISTS idx_entity_mappings_entity_type ON entity_mappings (raw_entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_source_dataset ON entity_mappings (source_dataset);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_raw_name ON entity_mappings (raw_entity_name);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_canonical_name ON entity_mappings (canonical_name);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_match_type ON entity_mappings (match_type);
CREATE INDEX IF NOT EXISTS idx_entity_mappings_confidence ON entity_mappings (mapping_confidence);

CREATE INDEX IF NOT EXISTS idx_ontology_relationships_subject ON ontology_relationships (subject_ontology_name, subject_ontology_id);
CREATE INDEX IF NOT EXISTS idx_ontology_relationships_object ON ontology_relationships (object_ontology_name, object_ontology_id);
CREATE INDEX IF NOT EXISTS idx_ontology_relationships_predicate ON ontology_relationships (predicate);

CREATE INDEX IF NOT EXISTS idx_dataset_registry_name ON dataset_registry (dataset_name);
CREATE INDEX IF NOT EXISTS idx_dataset_registry_disease ON dataset_registry (disease);
CREATE INDEX IF NOT EXISTS idx_dataset_registry_s3_uri ON dataset_registry (s3_uri);

CREATE INDEX IF NOT EXISTS idx_feature_registry_name ON feature_registry (feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_registry_disease ON feature_registry (disease);
CREATE INDEX IF NOT EXISTS idx_feature_registry_source_dataset ON feature_registry (source_dataset);
CREATE INDEX IF NOT EXISTS idx_feature_registry_leakage ON feature_registry (is_leakage_risk);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_disease ON pipeline_runs (pipeline_name, disease);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs (status);

CREATE INDEX IF NOT EXISTS idx_model_runs_disease_model ON model_runs (disease, model_name);
CREATE INDEX IF NOT EXISTS idx_model_runs_status ON model_runs (status);

CREATE INDEX IF NOT EXISTS idx_model_predictions_run_id ON model_predictions (run_id);
CREATE INDEX IF NOT EXISTS idx_model_predictions_disease_drug ON model_predictions (disease, drug_name);
CREATE INDEX IF NOT EXISTS idx_model_predictions_rank ON model_predictions (predicted_rank);

CREATE INDEX IF NOT EXISTS idx_candidate_rankings_disease_subtype ON candidate_rankings (disease, subtype);
CREATE INDEX IF NOT EXISTS idx_candidate_rankings_drug_name ON candidate_rankings (drug_name);
CREATE INDEX IF NOT EXISTS idx_candidate_rankings_rank ON candidate_rankings (rank);
CREATE INDEX IF NOT EXISTS idx_candidate_rankings_final_score ON candidate_rankings (final_score DESC);

CREATE INDEX IF NOT EXISTS idx_candidate_evidence_disease_drug ON candidate_evidence (disease, drug_name);
CREATE INDEX IF NOT EXISTS idx_candidate_evidence_type ON candidate_evidence (evidence_type);
CREATE INDEX IF NOT EXISTS idx_candidate_evidence_source ON candidate_evidence (evidence_source);

CREATE INDEX IF NOT EXISTS idx_admet_filter_results_drug_name ON admet_filter_results (drug_name);
CREATE INDEX IF NOT EXISTS idx_admet_filter_results_pass_admet ON admet_filter_results (pass_admet);

CREATE INDEX IF NOT EXISTS idx_lincs_reversal_results_disease_drug ON lincs_reversal_results (disease, drug_name);
CREATE INDEX IF NOT EXISTS idx_lincs_reversal_results_signature_id ON lincs_reversal_results (signature_id);
