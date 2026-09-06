# Development Setup

## Tools required

```powershell
winget install Astral.uv
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Casey.Just
```

Verify: `uv --version`, `node --version`, `just --version`

## Bootstrap

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
just install --extra dev
```

Installs Python deps (`uv sync --extra dev`) and `web_sota` npm packages.

For RAG tests and semantic search:

```powershell
uv sync --extra dev --extra rag
```

For prefab paper cards:

```powershell
uv sync --extra dev --extra rag --extra apps
```

## Common tasks

| Command | Purpose |
|---------|---------|
| `just dev` | Full stack via `web_sota/start.ps1` |
| `just serve` | Backend HTTP only (`--serve`) |
| `just stdio` | Stdio MCP only |
| `just test` | pytest |
| `just lint` | Ruff on `src/` + `tests/` |
| `just lint-web` | Biome on frontend |
| `just lint-all` | Python + Biome + `tsc` |
| `just ci` | Local CI mirror (ruff, format check, pytest, `tsc`, Biome) — green before push |
| `just fix` / `just fix-all` | Auto-fix lint |
| `just mcpb-pack` | Build Claude Desktop `.mcpb` |
| `just --list` | All recipes |

## Pre-commit (optional)

```powershell
uv sync --extra dev
pre-commit install
```

## Project layout

```
src/arxiv_mcp/       Python MCP server + FastAPI
web_sota/            React + Vite dashboard (10771)
tests/               pytest (97+ tests)
config/              code-hunt watch lists, feeds
docs/                Detailed guides
```

## Code standards

- **Python:** Ruff lint + format; no `print` in core handlers (`T201`)
- **Webapp:** Biome; strict `noConsoleLog`
- **Protocol:** stdout/stderr isolation for crash-resistant JSON-RPC
- **Security:** `bandit` / `safety` via just recipes where configured
- **Fleet standards:** [mcp-central-docs/standards](https://github.com/sandraschi/mcp-central-docs/tree/master/standards)

Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md) · FastMCP details: [FASTMCP_FEATURES.md](./FASTMCP_FEATURES.md)

## CI

CI runs the fleet reusable workflow (`sandraschi/fleet-ci` hybrid: ruff,
pytest, `tsc`, Biome on Windows). Local gate before push:

```powershell
just ci
```
