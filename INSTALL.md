# Installing arxiv-mcp

## Prerequisites

| Tool | Purpose | Install (Windows) |
|------|---------|-------------------|
| Git | Clone repo (Options C/D) | `winget install Git.Git` |
| uv | Python + deps | `winget install Astral.uv` |
| Node.js LTS | Web dashboard | `winget install OpenJS.NodeJS.LTS` |
| just | Fleet recipes (optional) | `winget install Casey.Just` |

> macOS: `brew install uv git node just` · Linux: [uv installer](https://docs.astral.sh/uv/)

RAG (LanceDB) is recommended: `uv sync --extra rag`. See [CONFIGURATION.md](docs/CONFIGURATION.md).

---

## Option A — MCPB drag and drop (recommended)

1. Go to [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest)
2. Download `arxiv-mcp.mcpb` (or build with `just mcpb-pack`)
3. Claude Desktop → Settings → MCP Servers → Install from file

No JSON editing required.

---

## Option B — Fastest from source (dashboard)

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
.\start.ps1
```

`start.ps1` runs `uv sync --extra dev --extra rag`, installs webapp deps if needed, starts backend **10770** + dashboard **10771**.

Or from `web_sota/`:

```powershell
cd web_sota
.\start.bat
```

---

## Option C — MCP stdio only

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
uv sync --extra rag
uv run python -m arxiv_mcp --stdio
```

Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\arxiv-mcp", "python", "-m", "arxiv_mcp", "--stdio"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```

Cursor and HTTP MCP: [docs/CURSOR-MCP.md](docs/CURSOR-MCP.md)

---

## Option D — Developer mode

```powershell
winget install Casey.Just
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
just install --extra dev
just dev
```

Common recipes: `just test`, `just lint-all`, `just serve`, `just mcpb-pack`. Full guide: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Verify installation

1. **Dashboard:** http://127.0.0.1:10771 — top bar shows backend health on **10770**.
2. **Health:** `GET http://127.0.0.1:10770/api/health` → OK.
3. **MCP host prompt:** *Search arXiv for recent papers about robotic manipulation in cs.RO.*

---

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

| Issue | Fix |
|-------|-----|
| `just` not found | `winget install Casey.Just` or use Option B/C |
| Port 10770/10771 in use | Change `ARXIV_MCP_PORT` in `.env`; update `web_sota/vite.config.ts` |
| Semantic search unavailable | `uv sync --extra rag` |
| arXiv rate limits | Increase `ARXIV_MCP_CLIENT_DELAY_SECONDS` |

---

*Feature overview: [README.md](README.md)*
