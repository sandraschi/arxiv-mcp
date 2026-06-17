set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

REPO := justfile_directory()

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Quality ───────────────────────────────────────────────────────────────────

# Ruff lint Python source
lint:
    cd '{{justfile_directory()}}'
    uv run ruff check src/ tests/

# Ruff auto-fix Python source
fix:
    cd '{{justfile_directory()}}'
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Biome lint frontend
lint-web:
    cd '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome lint src/

# Biome auto-fix frontend
fix-web:
    cd '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write src/

# TypeScript type check
tsc:
    cd '{{justfile_directory()}}\web_sota'
    npx tsc --noEmit

# Full lint (Python + frontend)
lint-all: lint lint-web tsc

# Full fix (Python + frontend)
fix-all: fix fix-web

# ── Testing ───────────────────────────────────────────────────────────────────

# Run Python tests
test:
    cd '{{justfile_directory()}}'
    uv run pytest

# Run tests verbosely
test-v:
    cd '{{justfile_directory()}}'
    uv run pytest -v

# ── Serving ───────────────────────────────────────────────────────────────────

# Start backend only (HTTP mode)
serve:
    cd '{{justfile_directory()}}'
    uv run python -m arxiv_mcp --serve

# Start backend only (stdio mode)
stdio:
    cd '{{justfile_directory()}}'
    uv run python -m arxiv_mcp --stdio

# Start full stack (via web_sota/start.ps1)
dev:
    cd '{{justfile_directory()}}\web_sota'
    .\start.ps1

# ── Python ────────────────────────────────────────────────────────────────────

# Install all deps (Python + frontend). Run after git clone.
install sync="--extra dev":
    cd '{{justfile_directory()}}'
    uv sync {{sync}}
    if (Test-Path '{{justfile_directory()}}\web_sota') { Push-Location '{{justfile_directory()}}\web_sota'; npm install; Pop-Location }
    Write-Host "Install complete. Run: just install-mcp claude" -ForegroundColor Green

# Sync Python deps with dev extras
sync:
    cd '{{justfile_directory()}}'
    uv sync --extra dev

# Install frontend deps
sync-web:
    cd '{{justfile_directory()}}\web_sota'
    npm install

# Full sync (Python + frontend deps)
sync-all: sync sync-web

# ── Federation ─────────────────────────────────────────────────────────────────

# Start the federation hub bridge (requires Admin for NSSM, direct otherwise)
hub:
    cd '{{justfile_directory()}}'
    & "C:\Users\sandr\AppData\Local\Microsoft\WinGet\Links\nssm.exe" status mcp-federation-hub 2>$null; \
    if ($LASTEXITCODE -eq 0) { \
        Write-Host "Federation hub NSSM service found." -ForegroundColor Cyan; \
        $svc = Get-Service -Name mcp-federation-hub; \
        if ($svc.Status -eq 'Stopped') { \
            Write-Host "Service is stopped. Starting with Admin privileges..." -ForegroundColor Yellow; \
            Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile','-Command', \
                "C:\Users\sandr\AppData\Local\Microsoft\WinGet\Links\nssm.exe start mcp-federation-hub" \
                -WindowStyle Hidden; \
            Write-Host "Admin prompt may appear. Check status with: just hub-status" -ForegroundColor Gray; \
        } else { Write-Host "Service is running." -ForegroundColor Green } \
    } else { \
        Write-Host "No NSSM service — starting directly..." -ForegroundColor Cyan; \
        $null = Start-Process -WindowStyle Hidden -FilePath "uv" -ArgumentList "run","python","-m","uvicorn","app.main:app","--host","127.0.0.1","--port","10857" \
            -WorkingDirectory "D:\Dev\repos\mcp-federation-hub\bridge"; \
        Write-Host "Federation hub bridge started on :10857" -ForegroundColor Green; \
        Write-Host "Fleet Supervisor will start polling servers in ~30s." -ForegroundColor Gray; \
    }

# Check federation hub status
hub-status:
    cd '{{justfile_directory()}}'; \
    try { \
        $r = curl.exe -s http://127.0.0.1:10857/health; \
        $d = $r | ConvertFrom-Json; \
        Write-Host "Hub: $($d.status) ($($d.federation.servers) servers, $($d.federation.categories) categories)" -ForegroundColor Green; \
    } catch { \
        Write-Host "Hub not reachable on :10857" -ForegroundColor Red; \
        Get-Service -Name mcp-federation-hub -ErrorAction SilentlyContinue | \
            ForEach-Object { Write-Host "NSSM service: $($_.Status)" }; \
    }

# ── arXiv ─────────────────────────────────────────────────────────────────

# Search arXiv papers
search query="attention":
    uv run python -c "import asyncio; from arxiv_mcp.services.papers import search_papers; import sys; r=asyncio.run(search_papers('{{query}}',limit=int(sys.argv[1]) if len(sys.argv)>1 else 5)); [print(f'{p.paper_id}: {p.title[:80]}') for p in r]"

# Get paper details by arXiv ID
paper id="2401.00001":
    uv run python -c "import asyncio; from arxiv_mcp.services.papers import get_paper_details; r=asyncio.run(get_paper_details('{{id}}')); print(f'{r.paper_id}\n{r.title}\n{r.summary[:200]}...')"

# Resolve a DOI
resolve-doi doi="10.1016/j.cell.2018.06.048":
    uv run python -c "import asyncio; from arxiv_mcp.doi_resolver import DOIResolver; r=asyncio.run(DOIResolver().resolve('{{doi}}')); print(f'{r.doi}: {r.is_oa} oa={r.oa_status} url={r.pdf_url}')" if resolver else print(f'DOI not found')

# Fetch full text of a paper
full-text id="2401.00001":
    uv run python -c "import asyncio; from arxiv_mcp.html_extract import fetch_html_markdown; ok,md,st,ct=asyncio.run(fetch_html_markdown('{{id}}')); print(md[:1000] if ok else md)"

# ── Utilities ──────────────────────────────────────────────────────────────────

# Repository statistics
stats:
    cd '{{justfile_directory()}}'
    uv run python tools/repo_stats.py

# Pre-commit run all files
precommit:
    cd '{{justfile_directory()}}'
    uv run pre-commit run --all-files

# ── RAG (LanceDB vector index) ─────────────────────────────────────────────────

rag-gpu:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/just/rag-gpu.ps1

rag-gpu-install:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/just/rag-gpu-install.ps1

rag-cpu-install:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/just/rag-cpu-install.ps1

# ── MCP Client Install ─────────────────────────────────────────────────────────

# Install into an MCP client config: claude|cursor|windsurf|zed|antigravity|lmstudio|code|print
# Delegates to install-mcp.ps1 which reads manifest.json for server identity.
install-mcp client="print":
    .\install-mcp.ps1 '{{client}}'

# ── Native (Tauri) ─────────────────────────────────────────────────────────────

# Build embedded Python backend → native/resources/
build-sidecar:
    pwsh -NoProfile -ExecutionPolicy Bypass -File '{{justfile_directory()}}\native\build-sidecar.ps1'

# Primary end-user deliverable: Vite + embedded backend + NSIS installer
build-native:
    pwsh -NoProfile -File "{{justfile_directory()}}/native/build.ps1"

# Debug Tauri shell (dev server + sidecar)
build-native-debug:
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build --debug
    C:\Windows\py.exe scripts/cua-smoke.py
