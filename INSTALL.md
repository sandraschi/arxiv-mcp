# Installation — From Zero

This document covers a full cold-start on a machine that has nothing installed.

## Prerequisites (auto-installed if missing)

`start.bat` will install these automatically via **winget** if they are absent:

| Tool | What it does | Winget ID |
|---|---|---|
| **uv** | Python package manager, creates .venv, no global pip needed | `Astral.uv` |
| **Node.js LTS** | JavaScript runtime for the React frontend | `OpenJS.NodeJS.LTS` |

Everything else (vite, tailwind, react, etc.) is installed **locally** into
`.venv` and `web_sota/node_modules` — nothing goes into global Python or npm.

## Quick start

```bat
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp\web_sota
start.bat
```

`start.bat` will:
1. Check for `uv` and `node` — install via winget if missing
2. Run `uv sync --extra dev` — creates `.venv` and installs all Python deps
3. Run `npm install` — installs vite + all frontend deps locally
4. Confirm `vite` is present in `node_modules/.bin/`
5. Clear ports 10770 / 10771
6. Start the backend, wait for health, start frontend, open browser

## Manual step-by-step

```powershell
winget install --id Astral.uv --silent
winget install --id OpenJS.NodeJS.LTS --silent
# Reopen PowerShell

cd arxiv-mcp
uv sync --extra dev
uv run python -c "import arxiv_mcp; print('OK')"

cd web_sota
npm install
# Verify vite is local:
Test-Path node_modules\.bin\vite   # must return True

# Start backend (keep open)
cd ..
uv run python -m arxiv_mcp --serve

# Second window: frontend
cd web_sota
npm run dev
```

## What is NOT required globally

- Python, pip, vite, ruff, or any globally installed npm packages
- Node.js is only required for the web frontend; the MCP server works without it
