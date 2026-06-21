# Candidate API Contract Validation (EC2 Redeploy)

- Generated: 2026-05-21T09:43:00.559744+00:00
- Service: drug-fastapi (api.main:app)

## Overall
- internal: candidate HTTP 200 = 14/14, contract match = 14/14, pg_warning_any = False, model_hits_total = 0
- nginx: candidate HTTP 200 = 14/14, contract match = 14/14, pg_warning_any = False, model_hits_total = 0
- external: candidate HTTP 200 = 14/14, contract match = 14/14, pg_warning_any = False, model_hits_total = 0

## Disease Counts
| Channel | Disease | candidates_http | final_http | candidates_count | final_count | contract_ok | pg_warning | model_hits | matching |
|---|---|---:|---:|---:|---:|---|---|---:|---:|
| internal | BRCA | 200 | 200 | 77 | 55 | True | False | 0 | 55/55 |
| internal | COAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| internal | LUAD | 200 | 200 | 30 | 13 | True | False | 0 | 13/13 |
| internal | LIHC | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| internal | STAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| internal | PAAD | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| internal | HNSC | 200 | 200 | 35 | 9 | True | False | 0 | 9/9 |
| nginx | BRCA | 200 | 200 | 77 | 55 | True | False | 0 | 55/55 |
| nginx | COAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| nginx | LUAD | 200 | 200 | 30 | 13 | True | False | 0 | 13/13 |
| nginx | LIHC | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| nginx | STAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| nginx | PAAD | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| nginx | HNSC | 200 | 200 | 35 | 9 | True | False | 0 | 9/9 |
| external | BRCA | 200 | 200 | 77 | 55 | True | False | 0 | 55/55 |
| external | COAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| external | LUAD | 200 | 200 | 30 | 13 | True | False | 0 | 13/13 |
| external | LIHC | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| external | STAD | 200 | 200 | 15 | 15 | True | False | 0 | 15/15 |
| external | PAAD | 200 | 200 | 15 | 0 | True | False | 0 | 0/0 |
| external | HNSC | 200 | 200 | 35 | 9 | True | False | 0 | 9/9 |

## Docking Endpoints
- internal:
  - 200 http://127.0.0.1:8000/api/docking/BRCA/gene-pdb
  - 200 http://127.0.0.1:8000/api/docking/BRCA/gene-pdb/TP53
- nginx:
  - 200 http://127.0.0.1/api/docking/BRCA/gene-pdb
  - 200 http://127.0.0.1/api/docking/BRCA/gene-pdb/TP53
- external:
  - 200 http://15.165.91.171/api/docking/BRCA/gene-pdb
  - 200 http://15.165.91.171/api/docking/BRCA/gene-pdb/TP53