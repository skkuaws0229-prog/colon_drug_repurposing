# BRCA Image Modal Inventory Report (Dry-Run)

- generated_at: 2026-05-13T08:54:41.163254+00:00
- inventory_version: v1.0.0
- mode: DRY_RUN_INVENTORY_ONLY
- disease_code: BRCA
- disease_aliases: BRAC
- source_s3_prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/`
- total_object_count: 25
- total_size_bytes: 2308187

## Recommendation Scope
- All `load_recommendation` values are registry-candidate triage only.
- This report does not perform PostgreSQL/Neo4j loading.
- This report does not download image binaries.
- This report does not load raw/curated/glue/reference datasets.

## Asset Type Counts
- image: 3
- json: 4
- other: 5
- table: 11
- text: 2

## Extension Counts
- (none): 1
- .csv: 11
- .json: 4
- .md: 2
- .npy: 1
- .png: 3
- .py: 3

## Warning Summary
- zero byte count: 1
- unknown extension count: 5
- warning::UNKNOWN_EXTENSION: 5
- warning::ZERO_BYTE_OBJECT: 1

## Recommendation Summary
- approved_for_image_registry count: 3
- needs_review count: 4
- recommendation::APPROVED_FOR_IMAGE_REGISTRY: 3
- recommendation::APPROVED_FOR_METADATA_REVIEW: 17
- recommendation::DO_NOT_LOAD: 1
- recommendation::NEEDS_REVIEW: 4

## Top 30 File Preview
| # | key | file_name | ext | asset_type | size_bytes | recommendation | warning_flags |
|---:|---|---|---|---|---:|---|---|
| 1 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/` |  | (none) | other | 0 | DO_NOT_LOAD | ZERO_BYTE_OBJECT,UNKNOWN_EXTENSION |
| 2 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/brca_path_t_stage_test.json` | brca_path_t_stage_test.json | .json | json | 920 | APPROVED_FOR_METADATA_REVIEW | - |
| 3 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_association_tests.csv` | cluster_association_tests.csv | .csv | table | 427 | APPROVED_FOR_METADATA_REVIEW | - |
| 4 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_merged.csv` | cluster_clinical_mutation_merged.csv | .csv | table | 132123 | APPROVED_FOR_METADATA_REVIEW | - |
| 5 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_clinical_mutation_report.md` | cluster_clinical_mutation_report.md | .md | text | 11982 | APPROVED_FOR_METADATA_REVIEW | - |
| 6 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_kaplan_meier_os.png` | cluster_kaplan_meier_os.png | .png | image | 54079 | APPROVED_FOR_IMAGE_REGISTRY | - |
| 7 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_mutation_frequency.csv` | cluster_mutation_frequency.csv | .csv | table | 276 | APPROVED_FOR_METADATA_REVIEW | - |
| 8 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_stage_distribution.csv` | cluster_stage_distribution.csv | .csv | table | 294 | APPROVED_FOR_METADATA_REVIEW | - |
| 9 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/cluster_subtype_distribution.csv` | cluster_subtype_distribution.csv | .csv | table | 216 | APPROVED_FOR_METADATA_REVIEW | - |
| 10 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/kaplan_meier_os.png` | kaplan_meier_os.png | .png | image | 51025 | APPROVED_FOR_IMAGE_REGISTRY | - |
| 11 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clinical_analysis/survival_logrank_pvalue.json` | survival_logrank_pvalue.json | .json | json | 464 | APPROVED_FOR_METADATA_REVIEW | - |
| 12 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_assignments.csv` | cluster_assignments.csv | .csv | table | 87829 | APPROVED_FOR_METADATA_REVIEW | - |
| 13 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_metrics_k3_k4_k5.csv` | cluster_metrics_k3_k4_k5.csv | .csv | table | 480 | APPROVED_FOR_METADATA_REVIEW | - |
| 14 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/cluster_summary.csv` | cluster_summary.csv | .csv | table | 350 | APPROVED_FOR_METADATA_REVIEW | - |
| 15 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/pca_plot.png` | pca_plot.png | .png | image | 110110 | APPROVED_FOR_IMAGE_REGISTRY | - |
| 16 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/clustering/silhouette_scores.json` | silhouette_scores.json | .json | json | 153 | APPROVED_FOR_METADATA_REVIEW | - |
| 17 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/drug_interpretation/cluster_drug_pathway_hypothesis.csv` | cluster_drug_pathway_hypothesis.csv | .csv | table | 4207 | APPROVED_FOR_METADATA_REVIEW | - |
| 18 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged.npy` | all_slide_embeddings_shard00_merged.npy | .npy | other | 1745024 | NEEDS_REVIEW | UNKNOWN_EXTENSION |
| 19 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv` | all_slide_embeddings_shard00_merged_manifest.csv | .csv | table | 54451 | APPROVED_FOR_METADATA_REVIEW | - |
| 20 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/embeddings/shard00_merged/all_slide_embeddings_shard00_merged_summary.json` | all_slide_embeddings_shard00_merged_summary.json | .json | json | 602 | APPROVED_FOR_METADATA_REVIEW | - |
| 21 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_cluster_clinical_mutation_analysis.py` | run_brca_cluster_clinical_mutation_analysis.py | .py | other | 20426 | NEEDS_REVIEW | UNKNOWN_EXTENSION |
| 22 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_image_clustering.py` | run_brca_image_clustering.py | .py | other | 12179 | NEEDS_REVIEW | UNKNOWN_EXTENSION |
| 23 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/scripts/run_brca_step4_step5_local.py` | run_brca_step4_step5_local.py | .py | other | 15388 | NEEDS_REVIEW | UNKNOWN_EXTENSION |
| 24 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/brca_step4_step5_report.md` | brca_step4_step5_report.md | .md | text | 3303 | APPROVED_FOR_METADATA_REVIEW | - |
| 25 | `20260408_new_pre_project_biso/202604_Final_data/BRCA/0.Image_modal_BRCA/step4_step5_ablation/step5_ablation_comparison.csv` | step5_ablation_comparison.csv | .csv | table | 1879 | APPROVED_FOR_METADATA_REVIEW | - |

## Next Steps (Proposed)
1. image_modal_asset PostgreSQL registry table 생성
2. registry upsert loader 작성
3. Neo4j ImageModalAsset node + HAS_IMAGE_MODAL 관계 생성
4. FastAPI /api/images/{disease} endpoint 추가
5. Agentic AI image interpretation은 별도 단계로 분리
