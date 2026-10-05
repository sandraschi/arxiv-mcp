# BUILD_LOG.md — arxiv-mcp NSIS Build Records

## Build 2026-10-05 (v0.7.1)

**Status:** PASS (installer produced, sidecar smoke green)

### Audit fixes applied first (TAURI_PRODUCTION_PITFALLS Phase 1 A-J)
- Operator backend moved to dedicated fleet port **11236** (`arxiv-mcp-native` row claimed via `claim_ports.py`): `backend.rs` BACKEND_PORT, frontend prod `API_BASE`, `build.ps1` Step 0 gate, `cua-nsis-config.json`. Dev stack stays on 10770/10771 (side-by-side).
- `backend.rs`: runtime `ARXIV_MCP_DATA_DIR` now points at `%LOCALAPPDATA%\ai.fleet.arxiv-mcp` so upgrades never wipe the depot.
- `tauri.conf.json`: explicit CSP (`connect-src` 11236) replacing `csp: null`; NSIS `installerHooks` wired to `windows/hooks.nsh` + `installMode: currentUser`; version 0.7.1.
- `build.ps1` smoke: uses `ARXIV_MCP_PORT/HOST` (frozen exe ignores `MCP_PORT`) + polls `/api/health` up to 120s (155MB onefile cold start needs ~60s; single-shot false-failed).
- `build-sidecar.ps1`: venv-local `pyinstaller.exe` (was banned `uv run pyinstaller`).
- Spec: `joserfc` trio + `cachetools` hiddenimports (fastmcp 3.4.4); `run_server.py` eager `_datetime`.
- `.gitignore`: `native/resources|binaries/*.exe`, `cua-reports/`. CUA deps added (`pywinauto pillow pytesseract`); `just cua-nsis-test` recipe added.

### Artifacts
- `dist/arxiv-mcp-backend.exe` 155-163MB, `native/resources/` embedded + `.env.example`.
- `dist/arXiv MCP_0.7.1_x64-setup.exe` 164.9MB (staged from `native/target/release/bundle/nsis/`).
- Frozen sidecar answers `/api/health` 200 on any `ARXIV_MCP_PORT` (verified :11999).

### Cert Pipeline Status
| Gate | Status |
|------|--------|
| TypeScript lint | PASS |
| Frontend build | PASS (2205 modules, 7.3s) |
| PyInstaller backend | PASS (155MB, venv-local 6.22.2) |
| Frozen binary smoke test | PASS (`/api/health` 200) |
| Size gate (>= 5 MB) | PASS |
| NSIS build | PASS |
| CUA-NSIS smoke test | PENDING (next) |

### Residual (non-blocking, follow-up)
- `backend-status` Tauri event bridge not yet in frontend (HTTP poll only); dashboard uses `backend-status-dot` testid, standard wants `backend-dot`.
- One pre-existing `unused_mut` warning in `backend.rs` (`let mut child`).
- `mcpb/pack.ps1` Step 10 launch check fails when dev backend holds 10770 (environmental; manual unpack+launch on free port passes, incl. `/api/shutdown` orderly exit).

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
