# BRCA Image Modal PostgreSQL Registry Plan (Dry-Run)

- project_root: `C:\work\drug-project`
- disease_code: BRCA
- source_classification_report: `C:\work\drug-project\outputs\config_validation\brca_image_modal_file_classification_report.json`
- candidate_count: 3
- execute_postgres: false
- target_table: `image_modal_asset`
- overall_status: PASS

## Approved Files
- cluster_kaplan_meier_os.png (s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_kaplan_meier_os.png)
- kaplan_meier_os.png (s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/kaplan_meier_os.png)
- pca_plot.png (s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/pca_plot.png)

## Excluded Counts By Reason
- metadata_review_excluded: 17
- needs_review_excluded: 4
- do_not_load_excluded: 1
- non_image_excluded: 22

## Guardrail Confirmation
- DB write was not performed.
- S3 object download was not performed.
- Image binary was not stored in PostgreSQL.
- Metadata review files were not loaded.
- Needs review files were not loaded.
- Zero-byte placeholder was not loaded.
- Neo4j load was not performed.
- Agentic AI image interpretation was not performed.

## Recommended Next Step
- If overall_status=PASS and explicit approval is given, run with --execute in a separate controlled step. For now keep dry-run only.
