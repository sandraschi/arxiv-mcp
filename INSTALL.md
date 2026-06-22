# Installing arxiv-mcp

## Option A — Desktop app (recommended)

**Download, double-click, done.** No Git, no Python, no `just`, no build step.

1. Go to [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest)
2. Download **`arXiv MCP_*_x64-setup.exe`**
3. Double-click the installer → finish the wizard
4. Launch **arXiv MCP** from the Start menu

That's it. The app includes the UI and Python backend (backend starts automatically on **10770**).

**Requirements:** Windows 10/11. [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) if the installer prompts for it (usually already on the system).

---

## Other install paths

Need MCP-only (no desktop UI), source dev, or Claude Desktop JSON? Use the options below.

### Prerequisites (Options B–E only)

| Tool | Purpose |
|------|---------|
| Git | Clone repo |
| uv | Python + deps |
| Node.js LTS | Web dashboard dev |
| just | Optional dev shortcuts |

> macOS/Linux: use Options B–E from source (no Windows desktop installer yet).

RAG (LanceDB): `uv sync --extra rag`. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

---

## Option B — MCPB drag and drop

1. Go to [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest)
2. Download `arxiv-mcp*.mcpb` (or build with `just mcpb-pack`)
3. Claude Desktop → Settings → MCP Servers → Install from file

No JSON editing required. Does not include the desktop UI — MCP tools only.

---

## Option C — Fastest from source (dashboard)

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

## Option D — MCP stdio only

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

## Option E — Developer mode

```powershell
winget install Casey.Just
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
just install --extra dev
just dev
```

Common recipes: `just test`, `just lint-all`, `just serve`, `just mcpb-pack`.

**Build the Windows installer** (maintainers only): `just build-native` → see [docs/TAURI.md](docs/TAURI.md).

Full guide: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Verify installation

1. **Desktop app or dashboard:** health indicator shows backend on **10770**
2. **Health:** `GET http://127.0.0.1:10770/api/health` → OK
3. **MCP host prompt:** *Search arXiv for recent papers about robotic manipulation in cs.RO.*

---

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

| Issue | Fix |
|-------|-----|
| Desktop app won't start | Install [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/); check `%LOCALAPPDATA%` isn't blocking backend extract |
| `just` not found | `winget install Casey.Just` or use Options B–D without just |
| Port 10770/10771 in use | Change `ARXIV_MCP_PORT` in `.env`; update `web_sota/vite.config.ts` |
| Semantic search unavailable | `uv sync --extra rag` |
| arXiv rate limits | Increase `ARXIV_MCP_CLIENT_DELAY_SECONDS` |

---

*Feature overview: [README.md](README.md)*
