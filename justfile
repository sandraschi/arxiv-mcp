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

# ── MCP Client Install ─────────────────────────────────────────────────────────

# Install into an MCP client config: claude | cursor | windsurf | zed | antigravity | code (VS Code) | print
# Reads manifest.json for server name, command, and args.
# For claude: writes to %APPDATA%\Claude\claude_desktop_config.json
# For cursor: %APPDATA%\Cursor\User\globalStorage\cursor-storage\mcp_config.json
# For windsurf: %USERPROFILE%\.codeium\windsurf\mcp_config.json
# For zed: %APPDATA%\Zed\settings.json
# For antigravity: %USERPROFILE%\.gemini\antigravity\mcp_config.json
# For code: project .vscode\settings.json
# For print: outputs the JSON block to the console.
install-mcp client="print":
    cd '{{justfile_directory()}}'; \
    $mf = Get-Content manifest.json -Raw | ConvertFrom-Json; \
    $name = $mf.name; \
    $cmd = $mf.server.mcp_config.command; \
    $args = $mf.server.mcp_config.args -join ' '; \
    $dir = '{{justfile_directory()}}'; \
    $$entry = @{ \
        command = $cmd; \
        args = @("run", "--directory", $dir) + $mf.server.mcp_config.args; \
    }; \
    if ($mf.server.mcp_config.env.PSObject.Properties.Name -and @($mf.server.mcp_config.env.PSObject.Properties).Count -gt 0) { \
        $$env = @{}; $mf.server.mcp_config.env.PSObject.Properties | ForEach-Object { $$env[$$_.Name] = $$_.Value }; \
        $$entry['env'] = $$env; \
    }; \
    $$block = @{ mcpServers = @{ $name = $$entry } }; \
    $$json = $$block | ConvertTo-Json -Depth 4; \
    switch -Wildcard ('{{client}}') { \
        'print' { Write-Host "$$json" -ForegroundColor Cyan; \
                  Write-Host "`nCopy this into your MCP client config." -ForegroundColor Gray }; \
        'claude' { \
            $$cfgDir = "$$env:APPDATA\Claude"; \
            $$cfgPath = "$$cfgDir\claude_desktop_config.json"; \
            if (-not (Test-Path $$cfgDir)) { New-Item -ItemType Directory -Path $$cfgDir -Force > $$null }; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'cursor' { \
            $$cfgPath = "$$env:APPDATA\Cursor\User\globalStorage\cursor-storage\mcp_config.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'windsurf' { \
            $$cfgPath = "$$env:USERPROFILE\.codeium\windsurf\mcp_config.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'antigravity' { \
            $$cfgPath = "$$env:USERPROFILE\.gemini\antigravity\mcp_config.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'zed' { \
            $$cfgPath = "$$env:APPDATA\Zed\settings.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'code' { \
            $$cfgPath = "$dir\.vscode\settings.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcp')) { $$existing['mcp'] = @{} }; \
            if (-not $$existing['mcp'].ContainsKey('servers')) { $$existing['mcp']['servers'] = @{} }; \
            $$existing['mcp']['servers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        'lmstudio' { \
            $$cfgPath = "$$env:USERPROFILE\.lmstudio\mcp.json"; \
            $$existing = @{}; \
            if (Test-Path $$cfgPath) { $$existing = Get-Content $$cfgPath -Raw | ConvertFrom-Json -AsHashtable }; \
            if (-not $$existing.ContainsKey('mcpServers')) { $$existing['mcpServers'] = @{} }; \
            $$existing['mcpServers'][$$name] = $$entry; \
            $$existing | ConvertTo-Json -Depth 10 | Set-Content $$cfgPath; \
            Write-Host "Installed into $$cfgPath" -ForegroundColor Green }; \
        default { Write-Host "Unknown client '{{client}}'. Use: claude, cursor, windsurf, zed, antigravity, lmstudio, code, print" -ForegroundColor Red }; \
    }
