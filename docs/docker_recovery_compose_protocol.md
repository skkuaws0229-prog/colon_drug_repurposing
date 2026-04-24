# Docker Desktop Recovery + Superset Compose Protocol

This document captures a reproducible operational protocol for the Windows error:

`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`

## Problem Pattern
- `docker compose ... up` fails with pipe endpoint errors.
- `docker context ls` can show malformed `desktop-linux` endpoint (for example `npipe:////`).
- `com.docker.service` is `STOPPED` or fails to start from a non-admin shell.

## Reproducible Automation
- Script: `scripts/run_superset_with_docker_recovery.ps1`
- CMD wrapper: `scripts/run_superset_with_docker_recovery.cmd`

What the script does:
1. Clears `DOCKER_HOST` in the current shell.
2. Ensures `com.docker.service` startup type is `Automatic`.
3. Starts `com.docker.service`.
4. Launches Docker Desktop UI if not running.
5. Resets WSL backend (`wsl --shutdown`).
6. Waits until Docker Server is reachable.
7. Optionally repairs `desktop-linux` context (`-RepairContext`).
8. Runs `docker compose -f docker-compose-image-tag.yml up` in target project.

## Usage
PowerShell:

```powershell
.\scripts\run_superset_with_docker_recovery.ps1
```

Detached mode:

```powershell
.\scripts\run_superset_with_docker_recovery.ps1 -Detach
```

If context appears broken:

```powershell
.\scripts\run_superset_with_docker_recovery.ps1 -RepairContext
```

Dry run for recovery only (no compose):

```powershell
.\scripts\run_superset_with_docker_recovery.ps1 -SkipCompose
```

Custom target:

```powershell
.\scripts\run_superset_with_docker_recovery.ps1 `
  -ProjectDir "C:\Users\hjy10\superset" `
  -ComposeFile "docker-compose-image-tag.yml"
```

## Admin Requirement
Starting `com.docker.service` may require Administrator PowerShell.

If you get permission errors:
1. Close the current shell.
2. Re-open PowerShell as Administrator.
3. Re-run the script.

## Escalation Path (Manual)
If recovery still fails:
1. Docker Desktop -> `Settings` -> `Troubleshoot`.
2. Run `Reset to factory defaults`.
3. Re-run this protocol.

## Portfolio Note
This protocol demonstrates practical DevOps troubleshooting:
- daemon/service diagnosis
- Windows named pipe endpoint recovery
- WSL backend reset
- scripted, repeatable environment bring-up for local containers
