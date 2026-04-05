set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Display the SOTA Industrial Dashboard
default:
    @powershell -NoLogo -Command " \
        $lines = Get-Content '{{justfile()}}'; \
        Write-Host ' [SOTA] Industrial Operations Dashboard v1.3.1' -ForegroundColor White -BackgroundColor Cyan; \
        Write-Host '' ; \
        $currentCategory = ''; \
        foreach ($line in $lines) { \
            if ($line -match '^# ── ([^─]+) ─') { \
                $currentCategory = $matches[1].Trim(); \
                Write-Host \"`n  $currentCategory\" -ForegroundColor Cyan; \
                Write-Host '  ' + ('─' * 45) -ForegroundColor Gray; \
            } elseif ($line -match '^# ([^─].+)') { \
                $desc = $matches[1].Trim(); \
                $idx = [array]::IndexOf($lines, $line); \
                if ($idx -lt $lines.Count - 1) { \
                    $nextLine = $lines[$idx + 1]; \
                    if ($nextLine -match '^([a-z0-9-]+):') { \
                        $recipe = $matches[1]; \
                        $pad = ' ' * [math]::Max(2, (18 - $recipe.Length)); \
                        Write-Host \"    $recipe\" -ForegroundColor White -NoNewline; \
                        Write-Host \"$pad$desc\" -ForegroundColor Gray; \
                    } \
                } \
            } \
        } \
        Write-Host \"`n  [System State: PROD/HARDENED]\" -ForegroundColor DarkGray; \
        Write-Host ''"

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff SOTA v13.1 linting
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .

# Execute Ruff SOTA v13.1 fix and formatting
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check

# arxiv-mcp — fleet recipes (uv). Run: just --list

stats:
    uv run python tools/repo_stats.py

sync:
    uv sync --extra dev

lint:
    uv run ruff check src tests

fmt:
    uv run ruff format src tests

test:
    uv run pytest

ty:
    uv run ty check src

precommit:
    uv run pre-commit run --all-files

serve:
    uv run python -m arxiv_mcp --serve

stdio:
    uv run python -m arxiv_mcp --stdio

# Pack Claude Desktop bundle (requires `mcpb` CLI on PATH; see assets/prompts + manifest.json)
mcpb-pack:
    mcpb pack . dist/arxiv-mcp.mcpb
