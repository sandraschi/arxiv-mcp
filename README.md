# arxiv-mcp 

**The high-density arXiv research pipe for AI Agents and Humans.**

[![GitHub license](https://img.shields.io/github/license/sandraschi/arxiv-mcp)](https://github.com/sandraschi/arxiv-mcp/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/sandraschi/arxiv-mcp/pulls)

**arxiv-mcp** turns the world's primary research source into a clean, actionable data stream. It search papers, extracts clean Markdown from experimental HTML, maps citation lineages, and stashes everything in a searchable local depot.

---

## Why use arxiv-mcp?

1.  **Clean Text Extraction**: Stop fighting multi-column PDFs. We prefer arXiv's **experimental HTML** to give you (and your agents) clean, structured Markdown.
2.  **Local Depot (RAG-Ready)**: Any paper you ingest is indexed in a local **SQLite FTS5** database. Search thousands of papers by keyword in milliseconds.
3.  **Citation Graphs**: Follow the intellectual lineage of any paper using **Semantic Scholar** integration.
4.  **AI Lab Blog Support**: Beyond arXiv, we fetch from **Anthropic**, **DeepMind**, and **Google Research** blogs.
5.  **Agent Native**: Built on **FastMCP 3.1**, supporting sophisticated features like **sampling** (`ctx.sample`) and bundled **skills**.

---

## Documentation Index

| Guide | Content |
| :--- | :--- |
| 🚀 **[Installation](docs/INSTALL.md)** | Getting up and running step-by-step. |
| 🏗️ **[Architecture](docs/ARCHITECTURE.md)** | How the backend, frontend, and storage layers work. |
| 🔭 **[arXiv Context](docs/ARXIV.md)** | Philosophy on recency and why HTML > PDF. |
| 🛠️ **[MCP Server](docs/MCP_SERVER.md)** | Complete manifest of tools, prompts, and skills. |
| 📊 **[Web Dashboard](docs/WEBAPP.md)** | Features and usage patterns for the UI. |

---

## Quick Start (30 Seconds)

### 1. Backend & MCP
Requires [Python 3.11+](https://python.org) and [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync
uv run python -m arxiv_mcp --stdio
```

*Add the last line to your Cursor/Claude Desktop config to start research immediately.*

### 2. Dashboard
Requires [Node.js](https://nodejs.org).

While the backend is running (`uv run python -m arxiv_mcp --serve`), run:
```powershell
.\start.ps1
```
Open **http://127.0.0.1:10771** to start exploring.

---

## What can you do?

*   **Discovery**: *"What are the most cited papers in cs.RO from the last week?"*
*   **Deep Read**: *"Pull the full text of 2401.00001 and audit its methods for reproducibility."*
*   **Synthesis**: *"Compare the abstracts of these 5 papers for contradictions in their consciousness claims."*
*   **Expansion**: *"Save this whole thread of citations into my local corpus."*

---

## Changelog
See **[CHANGELOG.md](CHANGELOG.md)** for release notes.

## License
MIT — see [LICENSE](LICENSE).
