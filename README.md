# arxiv-mcp

<div align="center">

**The high-density arXiv research pipe for AI Agents and Humans.**

[![GitHub release](https://img.shields.io/github/v/release/sandraschi/arxiv-mcp?style=flat-square&logo=semver&logoColor=white&color=blue)](https://github.com/sandraschi/arxiv-mcp/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2.0-blue?style=flat-square&logo=python&logoColor=white)](https://github.com/jlowin/fastmcp)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square)](https://github.com/astral-sh/ruff)
[![Biome](https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white)](https://biomejs.dev/)
[![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vite.dev)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![uv](https://img.shields.io/badge/uv-000000?style=flat-square&logo=astral&logoColor=white)](https://docs.astral.sh/uv)
[![Just](https://img.shields.io/badge/Just-000000?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/casey/just)
[![License](https://img.shields.io/github/license/sandraschi/arxiv-mcp?style=flat-square&color=blue)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/sandraschi/arxiv-mcp?style=flat-square&label=updated)](https://github.com/sandraschi/arxiv-mcp/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/sandraschi/arxiv-mcp/pulls)

</div>

**arxiv-mcp** turns the world's primary research source into a clean, actionable data stream. It search papers, extracts clean Markdown from experimental HTML, maps citation lineages, and stashes everything in a searchable local depot.

---

## Why use arxiv-mcp?

1.  **Clean Text Extraction**: Stop fighting multi-column PDFs. We prefer arXiv's **experimental HTML** to give you (and your agents) clean, structured Markdown.
2.  **Local Depot (RAG-Ready)**: Any paper you ingest is indexed in a local **SQLite FTS5** database. Search thousands of papers by keyword in milliseconds.
3.  **Citation Graphs**: Follow the intellectual lineage of any paper using **Semantic Scholar** integration.
4.  **DOI Resolution**: Resolve any DOI to metadata and OA PDF via **Unpaywall + Crossref**. Fetches open-access full text from 50,000+ publishers — no API keys required.
5.  **AI Lab Blog Support**: Beyond arXiv, we fetch from **Anthropic**, **DeepMind**, and **Google Research** blogs.
6.  **Agent Native**: Built on **FastMCP 3.2.0**, supporting sophisticated features like **sampling** (`ctx.sample`) and bundled **skills**.

---

## Documentation Index

| Guide | Content |
| :--- | :--- |
| 🚀 **[Installation](docs/INSTALL.md)** | Getting up and running step-by-step. |
| 🏗️ **[Architecture](docs/ARCHITECTURE.md)** | How the backend, frontend, and storage layers work. |
| 🔭 **[arXiv Context](docs/ARXIV.md)** | Philosophy on recency and why HTML > PDF. |
| 🛠️ **[MCP Server](docs/MCP_SERVER.md)** | Complete manifest of tools, prompts, and skills. |
| 📊 **[Web Dashboard](docs/WEBAPP.md)** | Features and usage patterns for the UI. |
| 🔗 **[DOI Resolution](docs/DOI_RESOLUTION.md)** | How Unpaywall + Crossref work, OA statuses explained, publishing ecosystem. |

---

## Quick Start (30 Seconds)

```powershell
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync
```

That's it. Now configure your MCP client (see below).

---

### Configuring MCP Clients

#### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\arxiv-mcp", "python", "-m", "arxiv_mcp", "--stdio"]
    }
  }
}
```

Replace `C:\\path\\to\\arxiv-mcp` with the actual path to your clone.

#### Cursor

In Cursor settings → Features → MCP Servers → Add new MCP server:

```
Name: arxiv-mcp
Type: command
Command: uv run --directory C:\path\to\arxiv-mcp python -m arxiv_mcp --stdio
```

#### MCPB Package (Claude Desktop drag-and-drop)

If you have the [MCPB CLI](https://github.com/sandraschi/fastmcp) installed:

```powershell
just mcpb-pack
```

This creates `dist/arxiv-mcp.mcpb` — drag this file into Claude Desktop to install.

Alternatively, download the pre-built `.mcpb` from the [Releases page](https://github.com/sandraschi/arxiv-mcp/releases).

---

### Full Stack (Backend + Web Dashboard)

Requires [Node.js](https://nodejs.org) in addition to Python/uv.

```powershell
cd arxiv-mcp\web_sota
.\start.bat
```

This starts both the backend and Vite dashboard, then opens **http://127.0.0.1:10771** in your browser.

---

### Using just

After setup, [just](https://github.com/casey/just) is available for common tasks:

```powershell
just lint         # Ruff lint Python
just lint-web     # Biome lint frontend
just fix          # Ruff auto-fix Python
just test         # Run Python tests
just serve        # Start backend only (HTTP)
just stdio        # Start backend only (stdio)
just dev          # Full stack (backend + Vite)
just sync         # uv sync with dev extras
```

Run `just --list` to see all recipes.

---

## What can you do?

*   **Discovery**: *"What are the most cited papers in cs.RO from the last week?"*
*   **Deep Read**: *"Pull the full text of 2401.00001 and audit its methods for reproducibility."*
*   **Synthesis**: *"Compare the abstracts of these 5 papers for contradictions in their consciousness claims."*
*   **Expansion**: *"Save this whole thread of citations into my local corpus."*

---

## Changelog
See **[CHANGELOG.md](CHANGELOG.md)** for release notes.


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.

## License
MIT — see [LICENSE](LICENSE).
