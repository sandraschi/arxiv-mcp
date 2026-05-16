set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Display the SOTA Industrial Dashboard
default:
    @$lines = Get-Content '{{justfile()}}'; \
    Write-Host ' [SOTA] arxiv-mcp Operations Dashboard' -ForegroundColor White -BackgroundColor Cyan; \
    Write-Host '' ; \
    $currentCategory = ''; \
    foreach ($line in $lines) { \
        if ($line -match '^# ── ([^─]+) ─') { \
            $currentCategory = $matches[1].Trim(); \
            Write-Host "`n  $currentCategory" -ForegroundColor Cyan; \
            Write-Host ('  ' + ('─' * 45)) -ForegroundColor Gray; \
        } elseif ($line -match '^# ([^─].+)') { \
            $desc = $matches[1].Trim(); \
            $idx = [array]::IndexOf($lines, $line); \
            if ($idx -lt $lines.Count - 1) { \
                $nextLine = $lines[$idx + 1]; \
                if ($nextLine -match '^([a-z0-9-]+):') { \
                    $recipe = $matches[1]; \
                    $pad = ' ' * [math]::Max(2, (18 - $recipe.Length)); \
                    Write-Host "    $recipe" -ForegroundColor White -NoNewline; \
                    Write-Host "$pad$desc" -ForegroundColor Gray; \
                } \
            } \
        } \
    } \
    Write-Host "`n  [System State: PROD]" -ForegroundColor DarkGray; \
    Write-Host ''

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

# ── Utilities ──────────────────────────────────────────────────────────────────

# Repository statistics
stats:
    cd '{{justfile_directory()}}'
    uv run python tools/repo_stats.py

# Pre-commit run all files
precommit:
    cd '{{justfile_directory()}}'
    uv run pre-commit run --all-files

# Pack Claude Desktop bundle (creates dist/arxiv-mcp-v{version}.mcpb)
mcpb-pack:
    cd '{{justfile_directory()}}'
    $ver = (Get-Content pyproject.toml | Select-String '^version = "(.*)"' | ForEach-Object { $$_.Matches.Groups[1].Value }); \
    $null = New-Item -ItemType Directory -Path dist -Force; \
    Compress-Archive -Path manifest.json, assets, src, pyproject.toml -DestinationPath "dist/arxiv-mcp-v$ver.mcpb" -CompressionLevel Optimal -Force; \
    Write-Host "Created dist/arxiv-mcp-v$ver.mcpb" -ForegroundColor Green
