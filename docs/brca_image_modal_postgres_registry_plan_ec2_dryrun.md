# BRCA Image Modal PostgreSQL Registry Report

- runtime_project_root: `C:\work\drug-project`
- project_root: `C:\work\drug-project`
- disease_code: BRCA
- source_classification_report: `C:\work\drug-project\outputs\config_validation\brca_image_modal_file_classification_report.json`
- execute_postgres: false
- target_table: image_modal_asset
- inserted_or_upserted_count: 0
- candidate_count: 3
- overall_status: PASS

## Approved Files
- cluster_kaplan_meier_os.png
- kaplan_meier_os.png
- pca_plot.png

## Excluded Counts By Reason
- metadata_review_excluded: 17
- needs_review_excluded: 4
- do_not_load_excluded: 1
- non_image_excluded: 22

## Guardrail Confirmation
- S3 object download was not performed.
- Image binary was not stored in PostgreSQL.
- Metadata review files were not loaded.
- Needs review files were not loaded.
- Zero-byte placeholder was not loaded.
- Neo4j load was not performed.
- Agentic AI image interpretation was not performed.
