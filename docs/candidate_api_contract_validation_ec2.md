# Candidate API Contract Validation (EC2)

- Generated: 2026-05-20T17:13:05+09:00
- Base URL: http://15.165.91.171
- HTTP 200 endpoints: 7/14
- Contract OK endpoints: 0/14
- final-candidates 404 count: 7

| Disease | candidates count | final-candidates count | final key match in candidates |
|---|---:|---:|---:|
| BRCA | 100 | 0 | 0/0 |
| COAD | 15 | 0 | 0/0 |
| LUAD | 100 | 0 | 0/0 |
| LIHC | 100 | 0 | 0/0 |
| STAD | 15 | 0 | 0/0 |
| PAAD | 35 | 0 | 0/0 |
| HNSC | 100 | 0 | 0/0 |

| Disease | Endpoint | HTTP | Contract OK | Count | Items | PG unavailable warnings | Identity OK | Model leaks | Shape |
|---|---|---:|---|---:|---:|---:|---|---:|---|
| BRCA | candidates | 200 | False | 100 | 100 | 0 | True | 0 | disease,source_table,candidates,warnings |
| BRCA | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| COAD | candidates | 200 | False | 15 | 15 | 0 | True | 0 | disease,source_table,candidates,warnings |
| COAD | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| LUAD | candidates | 200 | False | 100 | 100 | 0 | False | 0 | disease,source_table,candidates,warnings |
| LUAD | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| LIHC | candidates | 200 | False | 100 | 100 | 0 | True | 0 | disease,source_table,candidates,warnings |
| LIHC | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| STAD | candidates | 200 | False | 15 | 15 | 0 | True | 0 | disease,source_table,candidates,warnings |
| STAD | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| PAAD | candidates | 200 | False | 35 | 35 | 0 | True | 0 | disease,source_table,candidates,warnings |
| PAAD | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |
| HNSC | candidates | 200 | False | 100 | 100 | 0 | True | 0 | disease,source_table,candidates,warnings |
| HNSC | final-candidates | 404 | False | 0 | 0 | 0 | True | 0 | detail |

## Key Finding
- EC2 service is not yet running the new contract build for disease candidate APIs.
- `candidates` returns legacy shape (`source_table`, `candidates`) and `final-candidates` returns 404.
- This is a deployment/runtime-version mismatch, not a PostgreSQL-down symptom.

## Model Contamination Check
- Checked keywords: XGBoost, GAT, TabTransformer, LightGBM, RandomForest, GraphSAGE, CatBoost, ExtraTrees.
- Total hits across current EC2 responses: 0
