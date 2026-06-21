CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE TABLE IF NOT EXISTS dashboard.mart_curated_inventory (
  dataset_name text,
  file_extension text,
  file_count numeric,
  total_size_mb numeric,
  role text,
  protocol_stage text,
  status text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_dataset_readiness (
  required_dataset text,
  required_for text,
  exists_flag boolean,
  file_count numeric,
  total_size_mb numeric,
  readiness_status text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_schema_profile (
  dataset_name text,
  file_name text,
  s3_uri text,
  readable boolean,
  n_columns numeric,
  has_label_like_columns boolean,
  has_drug_columns boolean,
  has_gene_columns boolean,
  has_cell_line_columns boolean,
  has_clinical_columns boolean,
  label_like_columns jsonb,
  drug_columns jsonb,
  gene_columns jsonb,
  cell_line_columns jsonb,
  clinical_columns jsonb,
  error text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_gdsc_label_profile (
  file_name text,
  has_ln_ic50 boolean,
  has_ic50 boolean,
  has_auc boolean,
  has_rmse boolean,
  has_z_score boolean,
  has_drug_column boolean,
  has_cell_line_column boolean,
  label_readiness_status text,
  leakage_warning text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_drug_source_coverage (
  dataset_name text,
  file_name text,
  has_smiles boolean,
  has_chembl_id boolean,
  has_drugbank_id boolean,
  has_pubchem_id boolean,
  has_drug_name boolean,
  has_synonym boolean,
  has_target boolean,
  source_grade text,
  matching_role text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_depmap_profile (
  file_name text,
  has_depmap_id boolean,
  has_cosmic_id boolean,
  has_cell_line boolean,
  has_gene_dependency_matrix boolean,
  n_columns numeric,
  likely_matrix boolean,
  role text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_lincs_profile (
  file_name text,
  has_cell_id boolean,
  has_pert_id boolean,
  has_gene_id boolean,
  has_gene_symbol boolean,
  has_signature_metric boolean,
  likely_mcf7_related boolean,
  role text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_metabric_validation_profile (
  file_name text,
  has_expression boolean,
  has_patient_id boolean,
  has_sample_id boolean,
  has_os_months boolean,
  has_os_status boolean,
  has_rfs_months boolean,
  has_rfs_status boolean,
  has_tumor_stage boolean,
  has_subtype_or_threegene boolean,
  validation_role text,
  readiness_status text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_leakage_audit (
  dataset_name text,
  file_name text,
  column_name text,
  risk_level text,
  risk_type text,
  reason text,
  recommended_action text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_evidence_source_profile (
  dataset_name text,
  file_name text,
  evidence_type text,
  has_gene boolean,
  has_disease boolean,
  has_target boolean,
  has_pathway boolean,
  has_score boolean,
  evidence_role text,
  notes text
);

CREATE TABLE IF NOT EXISTS dashboard.mart_dashboard_kpis (
  metric_group text,
  metric_name text,
  metric_value numeric,
  status text,
  notes text
);

CREATE INDEX IF NOT EXISTS idx_mart_curated_inventory_dataset_name
  ON dashboard.mart_curated_inventory (dataset_name);
CREATE INDEX IF NOT EXISTS idx_mart_curated_inventory_protocol_stage
  ON dashboard.mart_curated_inventory (protocol_stage);

CREATE INDEX IF NOT EXISTS idx_mart_dataset_readiness_readiness_status
  ON dashboard.mart_dataset_readiness (readiness_status);
CREATE INDEX IF NOT EXISTS idx_mart_dataset_readiness_required_dataset
  ON dashboard.mart_dataset_readiness (required_dataset);

CREATE INDEX IF NOT EXISTS idx_mart_schema_profile_dataset_name
  ON dashboard.mart_schema_profile (dataset_name);
CREATE INDEX IF NOT EXISTS idx_mart_schema_profile_file_name
  ON dashboard.mart_schema_profile (file_name);

CREATE INDEX IF NOT EXISTS idx_mart_gdsc_label_profile_file_name
  ON dashboard.mart_gdsc_label_profile (file_name);

CREATE INDEX IF NOT EXISTS idx_mart_drug_source_coverage_dataset_name
  ON dashboard.mart_drug_source_coverage (dataset_name);
CREATE INDEX IF NOT EXISTS idx_mart_drug_source_coverage_file_name
  ON dashboard.mart_drug_source_coverage (file_name);

CREATE INDEX IF NOT EXISTS idx_mart_depmap_profile_file_name
  ON dashboard.mart_depmap_profile (file_name);

CREATE INDEX IF NOT EXISTS idx_mart_lincs_profile_file_name
  ON dashboard.mart_lincs_profile (file_name);

CREATE INDEX IF NOT EXISTS idx_mart_metabric_validation_profile_file_name
  ON dashboard.mart_metabric_validation_profile (file_name);
CREATE INDEX IF NOT EXISTS idx_mart_metabric_validation_profile_readiness_status
  ON dashboard.mart_metabric_validation_profile (readiness_status);

CREATE INDEX IF NOT EXISTS idx_mart_leakage_audit_dataset_name
  ON dashboard.mart_leakage_audit (dataset_name);
CREATE INDEX IF NOT EXISTS idx_mart_leakage_audit_file_name
  ON dashboard.mart_leakage_audit (file_name);
CREATE INDEX IF NOT EXISTS idx_mart_leakage_audit_risk_level
  ON dashboard.mart_leakage_audit (risk_level);

CREATE INDEX IF NOT EXISTS idx_mart_evidence_source_profile_dataset_name
  ON dashboard.mart_evidence_source_profile (dataset_name);
CREATE INDEX IF NOT EXISTS idx_mart_evidence_source_profile_file_name
  ON dashboard.mart_evidence_source_profile (file_name);
