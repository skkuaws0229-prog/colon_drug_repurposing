# Reproducibility Protocol

This protocol is Windows PowerShell first and avoids DB writes, S3 writes, uploads, commits, and pushes.

## 1. Inspect Artifacts

```powershell
python .\scripts\reproducibility_audit.py
```

Outputs:

- `reports/repo_artifact_audit.csv`
- `reports/repo_artifact_audit.md`
- `manifests/artifact_manifest.csv`
- `manifests/checksums.sha256`
- `manifests/excluded_artifacts.csv`

## 2. Public Demo Dry Run

```powershell
.\bootstrap.ps1 -Profile public-demo -Verify -RunSmokeTest
```

By default this is a dry run. It does not download unless `-Download` is provided.

## 3. Full Reproduction Dry Run

```powershell
.\bootstrap.ps1 -Profile full-reproduction -Verify
```

Rows without verified S3 URI are reported as `UNRESOLVED`.

## 4. Optional Real Download

```powershell
.\bootstrap.ps1 -Profile full-reproduction -Disease BRCA -Verify -Download
```

This uses boto3 or AWS CLI default credential chain only. It does not accept access keys through command-line arguments.

## 5. Verify Existing Local Files

```powershell
python .\scripts\verify_artifacts.py --profile public-demo
python .\scripts\verify_artifacts.py --profile full-reproduction --disease BRCA
```

## Safety Rules

- Do not commit secrets.
- Do not invent S3 URIs.
- Do not run DB write or S3 write operations as part of public reproducibility.
- Treat `UNRESOLVED` artifacts as requiring human review.
