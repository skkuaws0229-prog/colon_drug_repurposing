# LIHC PostgreSQL Deep-Load Validation Checklist (No-Write)

- approved_candidates_row_count: `8`
- ready_for_execute_approval: `false`
- execute_flags_run: `false`
- db_writes_occurred: `false`

| step | required | status |
|---|---|---|
| EC2 file transfer completed | True | PENDING |
| EC2 python and .venv verified | True | PENDING |
| Patched loader syntax check passed on EC2 | True | PENDING |
| PostgreSQL env variables loaded (masked verification) | True | PENDING |
| LIHC baseline read-only counts captured | True | PENDING |
| LIHC idempotency-check-only report generated | True | PENDING |
| LIHC 1-row rollback test report generated | True | PENDING |
| LIHC full 8-row rollback test report generated | True | PENDING |
| db_persisted=false confirmed in rollback reports | True | PENDING |
| Post-rollback baseline counts unchanged | True | PENDING |
| Manual human review sign-off before any future execute | True | PENDING |

## Prohibited

- --execute-postgres
- --execute-neo4j
- --execute-all
- PAAD execute rerun
