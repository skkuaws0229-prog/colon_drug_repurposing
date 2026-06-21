# Multi-Cancer File Inventory

- generated_at: 2026-05-05T10:53:16.328554+00:00
- inventory_version: v1.1.0

## Excluded S3 Prefixes
Raw/source/shared-input folders are intentionally excluded from release detection and likely file mapping.

- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/raw/`
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/`
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/raw_source_snapshot/`
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/raw/`
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/shared_inputs/`

## Disease Summary

| disease | object_count | excluded_object_count | top_level_prefixes | candidate_release_subdirs |
|---|---:|---:|---:|---:|
| BRCA | 6786 | 0 | 5 | 3 |
| COAD | 340 | 54 | 1 | 1 |
| HNSC | 232 | 56 | 7 | 1 |
| LIHC | 322 | 0 | 4 | 0 |
| LUNG | 804 | 2495 | 5 | 0 |
| PAAD | 247 | 269 | 7 | 1 |
| STAD | 171 | 819 | 2 | 0 |

## BRCA (Breast Cancer)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - `20260415_preproject_choi_protocol_v1_bisotest-1`
  - `20260415_preproject_protocol_choi`
  - `20260428_new_BRCA_data`

## COAD (Colon Adenocarcinoma / Colorectal Cancer)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/shared_inputs/`
- candidate_release_subdirs:
  - `20260428_colon_v2`

## HNSC (Head and Neck Squamous Cell Carcinoma)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/raw/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - `results`

## LIHC (Liver Hepatocellular Carcinoma)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - none

## LUNG (Lung Cancer)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/raw_source_snapshot/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - none

## PAAD (Pancreatic Ductal Adenocarcinoma)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/raw/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - `results`

## STAD (Stomach Adenocarcinoma / Gastric Cancer)
- s3_parent_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/`
- excluded_prefixes_applied:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/`
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/`
- candidate_release_subdirs:
  - none

## YAML Update Review

| disease | selected release prefix | mapped files | unresolved files | confidence | warning summary |
|---|---|---:|---:|---|---|
| COAD | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/` | 10 | 6 | high | Core candidate/model/validation/admet bundle is coherent; a few auxiliary roles remain TODO. |
| HNSC | `TODO_UNCONFIRMED` | 8 | 8 | medium | Results/base_data/workspace_seed are mixed; no single canonical release root confirmed. |
| LIHC | `TODO_UNCONFIRMED` | 6 | 10 | medium | Generated and repro trees both contain candidates; release boundary is still ambiguous. |
| LUNG | `TODO_UNCONFIRMED` | 9 | 7 | medium | Strong result files exist but no dated release folder and mixed package roots. |
| PAAD | `TODO_UNCONFIRMED` | 5 | 11 | medium | base_data/results/admet split remains; release root requires manual decision. |
| STAD | `TODO_UNCONFIRMED` | 2 | 14 | low | Only partial admet outputs are obvious; no consolidated release package detected. |
