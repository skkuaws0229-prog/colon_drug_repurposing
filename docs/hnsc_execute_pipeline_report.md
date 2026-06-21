# HNSC Execute Pipeline Report

- generated_at: `2026-05-10T20:11:57.396773+00:00`
- dry_run: `false`
- execute_postgres_requested: `true`
- execute_neo4j_requested: `false`
- validate_neo4j_requested: `false`
- postgres_execute_status: `POSTGRES_LOADED`
- postgres_validation_status: `PASS`
- neo4j_execute_performed: `false`
- overall_status: `PASS`
- stop_phase: ``
- stop_reason: ``

## Gate Status
- Gate A (YAML validation): `PASS`
- Gate B (S3 inventory / dry-run reconciliation): `PASS_WITH_WARNINGS`
- Gate C (safe write-plan): `PASS`
- Gate D (real-file inspection): `PASS`
- Gate E (PostgreSQL load plan from real inspection): `PASS`
- Gate F (PostgreSQL execute): `PASS`
- Gate G (PostgreSQL validation): `PASS`
- Gate H (Neo4j write-plan): `PASS_WITH_WARNINGS`
- Gate I (Neo4j execute): `NOT_RUN`
- Gate J (Neo4j validation): `NOT_RUN`
