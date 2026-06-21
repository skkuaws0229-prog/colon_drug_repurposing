# Multi-Cancer Restart Inventory Report

- generated_at: `2026-05-10T18:54:52.035572+00:00`
- project_root: `C:\work\drug-project`
- brca_alias_normalization_status: `PASS`

## Canonical Reference
- loader_orchestrator: `C:\work\drug-project\scripts\load\run_disease_execute_pipeline.py`
- postgres_plan_builder: `C:\work\drug-project\scripts\load\build_disease_postgres_load_plan_from_real_inspection.py`
- postgres_executor: `C:\work\drug-project\scripts\load\execute_disease_postgres_from_real_inspection_plan.py`
- postgres_validator: `C:\work\drug-project\scripts\load\validate_disease_postgres_load_result.py`
- neo4j_plan_builder: `C:\work\drug-project\scripts\load\build_disease_neo4j_write_plan.py`
- neo4j_executor: `C:\work\drug-project\scripts\load\execute_disease_neo4j_from_write_plan.py`
- neo4j_validator: `C:\work\drug-project\scripts\load\validate_disease_neo4j_load_result.py`
- api_alias_file: `C:\work\drug-project\api\services\disease_aliases.py`

## Disease Prefixes
- BRCA: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`
- COAD: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`
- LUAD: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- LIHC: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- STAD: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/`
- PAAD: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/`
- HNSC: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/`
