# Colon Drug Repurposing Platform

Production-style ML pipeline for colorectal cancer drug repurposing, with external validation (METABRIC) and ADMET gating.

## If You Are Hiring
I built and operated this repository end-to-end: data engineering, feature pipeline orchestration, model training, external validation, and candidate ranking dashboard delivery.

Core proof points from current artifacts:
- Ensemble performance: `Spearman 0.824`, `RMSE 1.293`
- Step 6 external validation: `29/30 targets expressed`, `P@15 0.80`, `P@20 0.75`
- Step 7 ADMET gate: `22 assays`, final `15` candidates (`Approved 9 / Candidate 5 / Caution 1`)
- Cohort-aware pipeline support (`colon`, `rectal`) with per-run QC/manifest traces

## What I Built
1. Cohort-splittable Nextflow pipeline (`split -> fe_inputs -> features -> pair_features -> upload`)
2. Multi-source feature engineering (chemistry, LINCS similarity, target interaction)
3. Model stack integration (ML/DL/Graph + ensemble ranking)
4. External biological validation and ADMET-based candidate filtering
5. Dashboard-ready outputs for communication with clinical/research stakeholders

## Architecture
```mermaid
flowchart LR
  A["Raw Tables (GDSC/DepMap/Drug/LINCS/Target)"] --> B["Step 0: Cohort Split"]
  B --> C["Step 1: FE Inputs + QC"]
  C --> D["Step 2: Base Features"]
  D --> E["Step 3: Pair Features (Chem/LINCS/Target)"]
  E --> F["Step 4: ML/DL/Graph Training"]
  F --> G["Step 5: Ensemble Top30/Top15"]
  G --> H["Step 6: METABRIC Validation"]
  H --> I["Step 7: ADMET Gate"]
  I --> J["Dashboard + Candidate Reports"]
```

## Repository Guide
- `nextflow/`: production pipeline workflow and FE scripts
- `models/`: training scripts and model/validation artifacts
- `runs/`: run-scoped outputs, manifests, and QC reports
- `analysis/`: cross-pipeline analysis and operational documentation
- `infra/aws/`: Terraform/AWS Batch execution baseline

## Reproducibility
### Local/Default
```powershell
cd nextflow
nextflow run main.nf --run_id "20260421_local_demo"
```

### AWS Batch
See:
- `infra/aws/README.md`
- `infra/aws/run_nextflow_aws.ps1`

## Recent Engineering Improvements
- Added automatic SMILES backfill in FE stage:
  - Match priority: `drug_id exact -> normalized drug_name fallback`
  - Added QC observability:
    - `smiles_matched_by_drug_id`
    - `smiles_backfilled_by_name`
    - `smiles_unresolved_after_backfill`
    - `smiles_backfill_policy`

## Proof Artifacts
- Pipeline definition: `nextflow/main.nf`
- FE input QC example: `runs/20260420_crc_split_v2/colon/fe_inputs/join_qc_report.json`
- Step 6 result: `models/metabric_results/step6_metabric_results.json`
- Step 7 result: `models/admet_results/step7_admet_results.json`
- Colon vs BRCA step guide: `analysis/COLON_BRCA_PIPELINE_STEP_GUIDE_20260421.md`

## Recruiter One-Pager
For outbound sharing:
- `analysis/RECRUITER_ONE_PAGE_20260421.md`

## Contact
If this project matches your hiring needs, please contact via GitHub profile message or repository issue.

