# BUILD_LOG.md — arxiv-mcp NSIS Build Records

## Build 2026-06-25 (v0.7.0)

**Status:** In progress

### Changes
- Fixed `tauri.conf.json` resources: `.env` → `.env.example` (never bundle dev secrets)
- `build.ps1` step 0: API_BASE port verification against backend port 10770
- `build.ps1` step 2: PyInstaller now uses venv-local `pyinstaller.exe`, pre-cleans stale exe, adds >= 5MB size gate, adds frozen binary smoke test (Start-Process + 5s + HasExited check)
- `build.ps1` step 3: bundles `.env.example` instead of `.env`
- New `GET /api/v1/diagnostics` endpoint for CUA-NSIS compliance
- Dashboard: exponential backoff health poll [1,2,4,8,16]s + Zustand store for backend online/offline state
- Dashboard: `data-testid="backend-dot"` element replacing generic backend-status

### Cert Pipeline Status
| Gate | Status |
|------|--------|
| TypeScript lint | PENDING |
| Frontend build | PENDING |
| PyInstaller backend | PENDING |
| Frozen binary smoke test | PENDING |
| Size gate (>= 5 MB) | PENDING |
| NSIS build | PENDING |
| CUA-NSIS smoke test | PENDING |
