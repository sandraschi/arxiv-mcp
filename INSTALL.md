# Installation — From Zero

This document covers a full cold-start on a machine that has nothing installed.

## Prerequisites (auto-installed if missing)

`start.bat` will install these automatically via **winget** if they are absent:

| Tool | What it does | Winget ID |
|---|---|---|
| **uv** | Python package manager — also downloads Python 3.11 automatically | `Astral.uv` |
| **Node.js LTS** | JavaScript runtime for the React frontend | `OpenJS.NodeJS.LTS` |
| **just** | Command runner — enables `just <recipe>` after install | `Casey.Just` |

Everything else is installed locally by those tools:
- Python 3.11+ — fetched by uv on first `uv sync --extra dev`
- All Python deps — installed into `.venv/` by uv
- vite, tailwind, react, biome — installed into `web_sota/node_modules/` by npm

**Nothing goes into global Python or npm.**

## Quick start

```bat
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp\web_sota
start.bat
```

`start.bat` (in `web_sota/`) does everything:
1. Installs uv, Node.js LTS via winget if missing
2. Runs `uv sync --extra dev` — downloads Python if needed, installs all Python deps
3. Runs `npm install` if `node_modules` absent — installs Vite and all frontend deps locally
4. Verifies `node_modules/.bin/vite` exists (explicit guard)
5. Clears ports 10770 / 10771
6. Starts the backend (`--serve` mode), waits for health, starts Vite, opens browser

## Manual step-by-step (if start.bat fails)

```powershell
# 1. Install prereqs (if missing)
winget install --id Astral.uv --silent
winget install --id OpenJS.NodeJS.LTS --silent
winget install --id Casey.Just --silent

# 2. Close and reopen PowerShell to pick up new PATH

# 3. Python deps (uv downloads Python 3.11 automatically on first run)
cd D:\path\to\arxiv-mcp
uv sync --extra dev

# 4. Smoke-test
uv run python -c "import arxiv_mcp; print('OK')"

# 5. Frontend deps
cd web_sota
npm install
cd ..

# 6. Start backend (keep this window open)
uv run python -m arxiv_mcp --serve

# 7. Second window: start frontend
cd web_sota
npm run dev

# 8. Open http://localhost:10771
```

## After install — using just

Once `start.bat` has run once, `just` is available everywhere:

```powershell
just --list        # show all recipes
just serve         # start backend only
just lint          # ruff + biome
just test          # pytest
just mcpb-pack     # build Claude Desktop bundle
```

## Minimum system requirements

- Windows 10 version 1809+ or Windows 11 (winget requires this)
- 4 GB RAM, 2 GB free disk
- Internet connection for first-time dep install

## What is NOT required globally

- Python (uv downloads it automatically)
- pip, vite, biome, ruff (all installed locally)
- just (installed by start.bat via winget)
- Any globally installed npm packages
