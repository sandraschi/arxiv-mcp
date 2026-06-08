# Installation (help topic)

> **Canonical guide:** [../INSTALL.md](../INSTALL.md)

## Quick verify

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
uv sync --extra rag
.\start.ps1
```

- Dashboard: http://127.0.0.1:10771  
- Backend: http://127.0.0.1:10770  
- Stdio MCP: `uv run python -m arxiv_mcp --stdio`

Full Options A–D, MCPB, and Claude Desktop JSON: **[../INSTALL.md](../INSTALL.md)**

Troubleshooting: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
