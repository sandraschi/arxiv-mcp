# Cursor & Claude Desktop MCP Setup

## Cursor

Settings → Features → MCP Servers → Add:

| Field | Value |
|-------|-------|
| Name | `arxiv-mcp` |
| Type | command |
| Command | `uv run --directory C:\path\to\arxiv-mcp python -m arxiv_mcp --stdio` |

Or use workspace `.cursor/mcp.json` when arxiv-mcp is the project root.

## Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\arxiv-mcp", "python", "-m", "arxiv_mcp", "--stdio"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "ARXIV_MCP_UNPAYWALL_EMAIL": "you@example.com"
      }
    }
  }
}
```

Restart Claude Desktop after edits.

## MCPB (drag and drop)

```powershell
just mcpb-pack
```

Creates `dist/arxiv-mcp.mcpb` — install via Claude Desktop Settings → MCP Servers → Install from file.

Pre-built bundles: [Releases](https://github.com/sandraschi/arxiv-mcp/releases).

## HTTP / MCP Inspector

```powershell
uv run python -m arxiv_mcp --serve
```

- **MCP:** http://127.0.0.1:10770/mcp
- **REST / OpenAPI:** http://127.0.0.1:10770/docs
- **Health:** http://127.0.0.1:10770/api/health

## Verify

> Search arXiv for papers about diffusion models published in the last 7 days.

Expected: structured results with titles, IDs, and abstracts.

Configuration: [CONFIGURATION.md](./CONFIGURATION.md)
