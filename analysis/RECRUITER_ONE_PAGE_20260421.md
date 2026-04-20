# Recruiter One-Page (Copy/Paste Ready)

## Candidate Positioning
Applied ML Engineer / MLOps Engineer focused on drug repurposing pipelines.

## 30-Second Summary
Built a production-style colorectal cancer drug repurposing platform from raw data ingestion to validated candidate shortlist.
Implemented cohort-aware Nextflow orchestration, multi-source feature engineering, ensemble ranking, external METABRIC validation, and ADMET gating with reproducible artifacts.

## Quantified Results (Current Artifacts)
- Ensemble: `Spearman 0.824`, `RMSE 1.293`
- External validation: `29/30` target expression coverage, `P@15 0.80`, `P@20 0.75`
- ADMET stage: `22` assays, final `15` candidates (`Approved 9 / Candidate 5 / Caution 1`)
- Cohort operations: `colon/rectal` split execution with run-level QC manifests

## Technical Scope Delivered
1. Pipeline orchestration with Nextflow DSL2
2. FE automation (sample/drug/pair features)
3. Chemical + LINCS + target interaction feature synthesis
4. Multi-model stack integration (ML/DL/Graph + ensemble)
5. Validation and gating framework (METABRIC + ADMET)
6. Dashboard and reporting outputs for non-ML stakeholders

## Engineering Highlights
1. Added automatic SMILES backfill at FE stage (`drug_id -> name fallback`)
2. Added explicit QC observability for backfill outcomes
3. Standardized run artifacts for reproducibility and auditability
4. Documented cross-pipeline (Colon vs BRCA) operation guide

## Representative Files
- `nextflow/main.nf`
- `nextflow/scripts/prepare_fe_inputs.py`
- `models/metabric_results/step6_metabric_results.json`
- `models/admet_results/step7_admet_results.json`
- `analysis/COLON_BRCA_PIPELINE_STEP_GUIDE_20260421.md`

## Outreach Blurb (for headhunters)
I build and productionize end-to-end AI pipelines for biomedical decision support, including data engineering, model orchestration, external validation, and deployable reporting.  
If you are hiring for Applied ML, MLOps, or AI Platform roles, I am open to discussing impact-focused opportunities.

