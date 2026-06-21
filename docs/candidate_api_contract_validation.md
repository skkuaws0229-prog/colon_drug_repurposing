# Candidate API Contract Validation

- Generated: 2026-05-20T17:03:29
- Project root: C:\\work\\drug-project
- API base tested: http://127.0.0.1:8000

| Disease | Endpoint | HTTP | Count | Items | Count=Items | Identity Key Rows | Model Leak Hits | Warnings |
|---|---|---:|---:|---:|---|---:|---:|---:|
| BRCA | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| BRCA | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| COAD | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| COAD | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| LUAD | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| LUAD | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| LIHC | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| LIHC | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| STAD | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| STAD | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| PAAD | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| PAAD | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| HNSC | candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |
| HNSC | final-candidates | 200 | 0 | 0 | True | 0 | 0 | 1 |

## Notes
- Endpoint response shape is now unified as `{ disease, count, items, warnings, diagnostics }`.
- `final-candidates` endpoint is added and uses final/admet source table priority in backend code.
- Model keyword guard is applied in normalization and drug_id-only rows are excluded.
- In this local runtime, PostgreSQL connectivity returned `OperationalError`, so counts are zero with warning.
- Validate again against EC2/live runtime where PostgreSQL is reachable.
