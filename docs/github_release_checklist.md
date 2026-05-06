# GitHub Release Checklist (BRCA Evidence Platform)

## 1) What is included in this repo
- PostgreSQL loader/validator
- Neo4j KG loader/validator
- FastAPI query layer
- team automation runner
- docs

## 2) What is not included
- raw S3 data
- generated outputs
- local database files
- real secrets
- Neo4j local data directory

## 3) Pre-push checklist
- [ ] `.env` not committed
- [ ] `outputs/` not committed
- [ ] no real Neo4j password in repo
- [ ] no AWS keys in repo
- [ ] `requirements.txt` present
- [ ] `README.md` has quickstart
- [ ] team automation doc present (`docs/team_automation_pipeline.md`)

## 4) Git commands
```bash
git status
git add .
git commit -m "Add BRCA evidence platform automation pipeline"
git remote add origin <repo-url>
git push -u origin main
```

## 5) If repo already exists
```bash
git remote -v
git push
```

