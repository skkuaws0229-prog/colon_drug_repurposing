# Artifact Policy

This repository is prepared for public reproducibility without committing private credentials or large binary artifacts.

## GitHub Include

Include source code, PowerShell scripts, SQL, YAML/TOML/config examples, documentation, tests, manifests, audit reports, and small public final CSV/JSON/LOG/NPY artifacts under 20 MiB when no secret is detected.

## Externalize to S3 or Release

Keep large or binary artifacts outside Git:

- model weights: `.pt`, `.pth`, `.ckpt`
- serialized models: `.pkl`, `.joblib`
- large feature/data files: `.parquet`, large `.csv`, raw data
- archives and dumps: `.zip`, `.tar`, `.gz`, `.dump`
- cache and training telemetry

Only real S3 URIs discovered in existing files are recorded. Missing locations remain `UNRESOLVED`.

## Exclude From Git

Never commit:

- `.env`, credentials, access keys, secret keys, tokens
- `.pem`, `.key`, private key blocks
- DB URLs with credentials
- local caches, virtual environments, `node_modules`
- temporary outputs and local service state

## Review Required

Files marked `review` in `reports/repo_artifact_audit.csv` need a human decision before public release.
