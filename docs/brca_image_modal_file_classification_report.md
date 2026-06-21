# BRCA Image Modal File Classification Report

## Summary
- canonical_project_root: `C:\work\drug-project`
- total_object_count: 25
- mode: DRY-RUN / CLASSIFICATION ONLY
- previous OneDrive outputs were not used

## Classification Rules
- classification_rules section is included in both JSON and Markdown.

[asset_type 분류 기준]
- .png, .jpg, .jpeg, .tif, .tiff, .webp, .bmp -> image
- .csv, .tsv, .xlsx, .xls -> table
- .json -> json
- .txt, .md -> text
- .pdf -> pdf
- .html, .htm -> html
- 기타 확장자 또는 확장자 없음 -> other

[warning_flags 기준]
- size_bytes == 0 -> ZERO_BYTE_OBJECT
- unknown extension 또는 extension 없음 -> UNKNOWN_EXTENSION

[load_recommendation 기준]
- image이고 ZERO_BYTE_OBJECT가 아니면 APPROVED_FOR_IMAGE_REGISTRY
- table/json/text/pdf/html이면 APPROVED_FOR_METADATA_REVIEW
- UNKNOWN_EXTENSION이면 NEEDS_REVIEW
- ZERO_BYTE_OBJECT이면 DO_NOT_LOAD

[proposed_postgres_target 기준]
- image + APPROVED_FOR_IMAGE_REGISTRY -> image_modal_asset
- table/json/text/pdf/html + APPROVED_FOR_METADATA_REVIEW -> image_modal_metadata_review
- UNKNOWN_EXTENSION -> manual_review_required
- ZERO_BYTE_OBJECT -> do_not_load

[proposed_neo4j_node 기준]
- image_modal_asset -> ImageModalAsset
- image_modal_metadata_review -> ImageModalMetadata
- manual_review_required -> REVIEW_REQUIRED
- do_not_load -> NONE

[proposed_next_action 기준]
- APPROVED_FOR_IMAGE_REGISTRY -> register_to_postgres_image_modal_asset
- APPROVED_FOR_METADATA_REVIEW -> inspect_metadata_content_later
- NEEDS_REVIEW -> manual_review_before_load
- DO_NOT_LOAD -> exclude_from_load

## Classification Results
- classification_results section is included in both JSON and Markdown.

| metric | counts |
|---|---|
| total_object_count | 25 |
| asset_type별 count | {"image": 3, "json": 4, "other": 5, "table": 11, "text": 2} |
| warning_flags별 count | {"UNKNOWN_EXTENSION": 5, "ZERO_BYTE_OBJECT": 1} |
| load_recommendation별 count | {"APPROVED_FOR_IMAGE_REGISTRY": 3, "APPROVED_FOR_METADATA_REVIEW": 17, "DO_NOT_LOAD": 1, "NEEDS_REVIEW": 4} |
| proposed_postgres_target별 count | {"do_not_load": 1, "image_modal_asset": 3, "image_modal_metadata_review": 17, "manual_review_required": 4} |
| proposed_neo4j_node별 count | {"ImageModalAsset": 3, "ImageModalMetadata": 17, "NONE": 1, "REVIEW_REQUIRED": 4} |
| proposed_next_action별 count | {"exclude_from_load": 1, "inspect_metadata_content_later": 17, "manual_review_before_load": 4, "register_to_postgres_image_modal_asset": 3} |

## Image files approved for registry
- cluster_kaplan_meier_os.png
- kaplan_meier_os.png
- pca_plot.png

## Metadata files requiring review
- brca_path_t_stage_test.json
- cluster_association_tests.csv
- cluster_clinical_mutation_merged.csv
- cluster_clinical_mutation_report.md
- cluster_mutation_frequency.csv
- cluster_stage_distribution.csv
- cluster_subtype_distribution.csv
- survival_logrank_pvalue.json
- cluster_assignments.csv
- cluster_metrics_k3_k4_k5.csv
- cluster_summary.csv
- silhouette_scores.json
- cluster_drug_pathway_hypothesis.csv
- all_slide_embeddings_shard00_merged_manifest.csv
- all_slide_embeddings_shard00_merged_summary.json
- brca_step4_step5_report.md
- step5_ablation_comparison.csv

## Needs review files
- all_slide_embeddings_shard00_merged.npy
- run_brca_cluster_clinical_mutation_analysis.py
- run_brca_image_clustering.py
- run_brca_step4_step5_local.py

## Do not load files
- (empty)

## Full file classification table
| index | disease_code | file_name | s3_uri | file_ext | inferred_asset_type | size_bytes | load_recommendation | warning_flags | proposed_postgres_target | proposed_neo4j_node | proposed_next_action | classification_reason |
|---:|---|---|---|---|---|---:|---|---|---|---|---|---|
| 1 | BRCA | (empty) | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/ | (none) | other | 0 | DO_NOT_LOAD | ZERO_BYTE_OBJECT,UNKNOWN_EXTENSION | do_not_load | NONE | exclude_from_load | Zero-byte object; excluded from load. |
| 2 | BRCA | brca_path_t_stage_test.json | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/brca_path_t_stage_test.json | .json | json | 920 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | JSON metadata file; requires metadata review before graph linkage. |
| 3 | BRCA | cluster_association_tests.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_association_tests.csv | .csv | table | 427 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 4 | BRCA | cluster_clinical_mutation_merged.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv | .csv | table | 132123 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 5 | BRCA | cluster_clinical_mutation_report.md | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_report.md | .md | text | 11982 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | Text metadata file; requires metadata review before any DB linkage. |
| 6 | BRCA | cluster_kaplan_meier_os.png | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_kaplan_meier_os.png | .png | image | 54079 | APPROVED_FOR_IMAGE_REGISTRY | - | image_modal_asset | ImageModalAsset | register_to_postgres_image_modal_asset | Image extension and non-zero size; eligible for registry metadata only. |
| 7 | BRCA | cluster_mutation_frequency.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_mutation_frequency.csv | .csv | table | 276 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 8 | BRCA | cluster_stage_distribution.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_stage_distribution.csv | .csv | table | 294 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 9 | BRCA | cluster_subtype_distribution.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_subtype_distribution.csv | .csv | table | 216 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 10 | BRCA | kaplan_meier_os.png | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/kaplan_meier_os.png | .png | image | 51025 | APPROVED_FOR_IMAGE_REGISTRY | - | image_modal_asset | ImageModalAsset | register_to_postgres_image_modal_asset | Image extension and non-zero size; eligible for registry metadata only. |
| 11 | BRCA | survival_logrank_pvalue.json | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/survival_logrank_pvalue.json | .json | json | 464 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | JSON metadata file; requires metadata review before graph linkage. |
| 12 | BRCA | cluster_assignments.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_assignments.csv | .csv | table | 87829 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 13 | BRCA | cluster_metrics_k3_k4_k5.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_metrics_k3_k4_k5.csv | .csv | table | 480 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 14 | BRCA | cluster_summary.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_summary.csv | .csv | table | 350 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 15 | BRCA | pca_plot.png | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/pca_plot.png | .png | image | 110110 | APPROVED_FOR_IMAGE_REGISTRY | - | image_modal_asset | ImageModalAsset | register_to_postgres_image_modal_asset | Image extension and non-zero size; eligible for registry metadata only. |
| 16 | BRCA | silhouette_scores.json | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/silhouette_scores.json | .json | json | 153 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | JSON metadata file; requires metadata review before graph linkage. |
| 17 | BRCA | cluster_drug_pathway_hypothesis.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/drug_interpretation/cluster_drug_pathway_hypothesis.csv | .csv | table | 4207 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 18 | BRCA | all_slide_embeddings_shard00_merged.npy | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged.npy | .npy | other | 1745024 | NEEDS_REVIEW | UNKNOWN_EXTENSION | manual_review_required | REVIEW_REQUIRED | manual_review_before_load | Unknown extension; manual review required. |
| 19 | BRCA | all_slide_embeddings_shard00_merged_manifest.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv | .csv | table | 54451 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |
| 20 | BRCA | all_slide_embeddings_shard00_merged_summary.json | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_summary.json | .json | json | 602 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | JSON metadata file; requires metadata review before graph linkage. |
| 21 | BRCA | run_brca_cluster_clinical_mutation_analysis.py | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_cluster_clinical_mutation_analysis.py | .py | other | 20426 | NEEDS_REVIEW | UNKNOWN_EXTENSION | manual_review_required | REVIEW_REQUIRED | manual_review_before_load | Unknown extension; manual review required. |
| 22 | BRCA | run_brca_image_clustering.py | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_image_clustering.py | .py | other | 12179 | NEEDS_REVIEW | UNKNOWN_EXTENSION | manual_review_required | REVIEW_REQUIRED | manual_review_before_load | Unknown extension; manual review required. |
| 23 | BRCA | run_brca_step4_step5_local.py | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_step4_step5_local.py | .py | other | 15388 | NEEDS_REVIEW | UNKNOWN_EXTENSION | manual_review_required | REVIEW_REQUIRED | manual_review_before_load | Unknown extension; manual review required. |
| 24 | BRCA | brca_step4_step5_report.md | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/brca_step4_step5_report.md | .md | text | 3303 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | Text metadata file; requires metadata review before any DB linkage. |
| 25 | BRCA | step5_ablation_comparison.csv | s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/step5_ablation_comparison.csv | .csv | table | 1879 | APPROVED_FOR_METADATA_REVIEW | - | image_modal_metadata_review | ImageModalMetadata | inspect_metadata_content_later | CSV table file; requires metadata review before any DB linkage. |

## Recommended PostgreSQL mapping
- do_not_load: 1
- image_modal_asset: 3
- image_modal_metadata_review: 17
- manual_review_required: 4

## Recommended Neo4j mapping
- ImageModalAsset: 3
- ImageModalMetadata: 17
- NONE: 1
- REVIEW_REQUIRED: 4

## Recommended next execution order
1. image 3개만 image_modal_asset registry 후보로 확정
2. ZERO_BYTE_OBJECT는 제외
3. UNKNOWN_EXTENSION은 수동 검토
4. table/json/text metadata 파일은 아직 DB 적재하지 않고 내용 검토 대기
5. image registry 적재 후 Neo4j HAS_IMAGE_MODAL 관계 생성
6. Agentic AI image interpretation은 이후 별도 단계로 분리

## Guardrail confirmation
- DB write was not performed.
- PostgreSQL load was not performed.
- Neo4j load was not performed.
- S3 object download was not performed.
- Only existing inventory JSON was read.
- Image content was not interpreted.
- Previous OneDrive path outputs were not used.
