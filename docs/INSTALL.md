# Installation (help topic)

> **Canonical guide:** [../INSTALL.md](../INSTALL.md)

## Desktop app (recommended)

1. [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest) → **`arXiv MCP_*_x64-setup.exe`**
2. Double-click → install → launch **arXiv MCP**

No build step. Backend **10770** starts with the app.

## From source (developers)

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
.\start.ps1
```

- Dashboard: http://127.0.0.1:10771
- Backend: http://127.0.0.1:10770
- Stdio MCP: `uv run python -m arxiv_mcp --stdio`

Full Options A–E: **[../INSTALL.md](../INSTALL.md)**

Build installer (maintainers): [TAURI.md](./TAURI.md)

Troubleshooting: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
