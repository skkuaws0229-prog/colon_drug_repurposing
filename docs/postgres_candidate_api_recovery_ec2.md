# PostgreSQL Candidate API Recovery (EC2)

## Summary
- Goal: restore PostgreSQL connectivity for candidate APIs used by assistant top-candidates.
- Result: recovered.
  - `GET /api/diseases/BRCA/final-candidates` -> `count=55`
  - `GET /api/diseases/BRCA/candidates` -> `count=77`
  - `POST /api/assistant/BRAC/ask` -> `intent=top_candidates`, `evidence.returned_count=3`, `evidence.items` length `3`

## Root Cause
- Exact failure class: `OperationalError`
- Exact cause: PostgreSQL authentication failure for role `Drug`
  - message: `password authentication failed for user "Drug"`
- Service env itself was present (`backend/.env` loaded via systemd `EnvironmentFile`), but DB auth and configured password were mismatched.

## Systemd / Runtime Checks
- `WorkingDirectory=/home/ec2-user/drug-project` (OK)
- `ExecStart=/home/ec2-user/drug-project/backend/.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000` (OK)
- `EnvironmentFile=-/home/ec2-user/drug-project/backend/.env` configured (OK)

## Fix Applied
- No FastAPI source-code patch required for this incident.
- Applied authentication recovery on PostgreSQL role `Drug` to align runtime credentials.
- Restarted service:
  - `sudo systemctl restart drug-fastapi`
  - status: `active (running)`

## Validation
- Syntax checks (all pass):
  - `api/main.py`
  - `api/db/postgres.py`
  - `api/routers/diseases.py`
  - `api/routers/assistant.py`
- OpenAPI assistant route:
  - `/api/assistant/{disease}/ask` present

### Internal (127.0.0.1:8000)
- `GET /api/diseases/BRCA/final-candidates`
  - `count=55`
  - no `PostgreSQL unavailable` warning
  - items non-empty
- `GET /api/diseases/BRCA/candidates`
  - `count=77`
  - no `PostgreSQL unavailable` warning
  - items non-empty
- `POST /api/assistant/BRAC/ask` with `{"question":"BRAC 상위 3개 보여줘","context":{}}`
  - `disease=BRCA`
  - `intent=top_candidates`
  - `evidence.source_path=/api/diseases/BRCA/final-candidates`
  - `evidence.returned_count=3`
  - `evidence.items` length `3`
  - not routed to graph summary

### External (15.165.91.171)
- `GET /api/diseases/BRCA/final-candidates` -> `count=55`, items non-empty
- `GET /api/diseases/BRCA/candidates` -> `count=77`, items non-empty
- `POST /api/assistant/BRAC/ask` -> same top-candidates behavior (`returned_count=3`, items length `3`)

## Constraints / Safety
- No mock data inserted.
- No candidate/final-candidate table writes performed.
- No Neo4j modifications.
- No disease config changes.
- Note: incident recovery required PostgreSQL role authentication alignment; this is not candidate data mutation.
