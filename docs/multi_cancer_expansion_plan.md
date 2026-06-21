# Multi-Cancer Expansion Plan

## 1) Current verified BRCA status
- PostgreSQL load/validation: done
- Neo4j KG load/validation: done
- FastAPI agent-context check: passed

## 2) Seven target diseases and S3 parent prefixes
- BRCA: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`
- Colon: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`
- HNSC: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/`
- Liver: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- LUNG: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- PDAC: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/`
- STAD: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/`

## 3) Why s3fs profiling is used
- It is not only S3 object listing.
- It reads headers, columns, and small samples.
- It helps verify whether files can be mapped into loader roles before ETL work starts.

## 4) Why YAML configs are used
- Per-disease metadata is explicit and reviewable.
- Release prefix and file-role mapping can be updated without changing loader code.
- It becomes the contract between S3 profiling and generic loader implementation.

## 5) Why shared PostgreSQL tables are used
- Shared schema keeps cross-disease analytics consistent.
- Disease dimensioning is done with `disease`, `run_id`, and provenance fields.
- Avoids schema drift and duplicated table logic per disease.

## 6) Why disease/run_id/source_s3_uri are required
- `disease`: partitioning and API routing.
- `run_id`: release traceability and reproducibility.
- `source_s3_uri`: strict provenance for audit/debug/backfill.

## 7) Why model_metric needs phase/family/source_model_dir
- `phase`: training/evaluation lifecycle context.
- `family`: model grouping across ML/DL/Graph/ensemble lines.
- `source_model_dir`: ties metric rows back to generated artifacts.
- Together they prevent metric ambiguity across runs and disease cohorts.

## 8) Why Neo4j is built from PostgreSQL, not raw S3
- PostgreSQL is the normalized and validated evidence layer.
- KG should reflect governed entities and relationships, not raw artifact variability.
- This prevents loader duplication and contradictory entity resolution rules.

## 9) Expansion workflow
1. Create disease YAML configs.
2. Run s3fs profiler.
3. Review suggested YAML mappings.
4. Update YAML `input_files` manually.
5. Build generic PostgreSQL loader.
6. Pilot one disease (recommended: Colon or LUNG).
7. Validate PostgreSQL.
8. Load Neo4j KG.
9. Validate KG.
10. Repeat for remaining diseases.
11. Generalize FastAPI to `/api/{disease}/...`.

## 10) Warnings
- Do not manually drag/drop CSVs into PostgreSQL.
- Do not create disease-specific tables.
- Do not build KG directly from S3.
- Do not start Agentic AI before DB/KG/API are stable.
