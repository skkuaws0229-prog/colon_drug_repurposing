# LIHC / PAAD PostgreSQL Deep-Load Readiness Summary

- scope: BRCA-standard readiness only; no DB writes
- BRCA remains the source-of-truth standard
- COAD MSI remains under driver_genes

## Summary
| disease | objects | LOAD_CANDIDATE | NEEDS_REVIEW | EXCLUDED | parity | suspicious | approved manifest | next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LIHC | 383 | 11 | 41 | 31 | PARITY_OK | 3 | YES_WITH_HUMAN_REVIEW | READY_FOR_HUMAN_REVIEW |
| PAAD | 541 | 2 | 71 | 271 | PARITY_OK | 0 | YES_FINAL_AFTER_ADMET_AVAILABLE | READY_FOR_HUMAN_REVIEW |

## Guardrails
- PostgreSQL write: `not_performed`
- Neo4j write: `not_performed`
- execute flags run: `none`
- loaders run: `false`
- fake approved candidates generated: `false`
