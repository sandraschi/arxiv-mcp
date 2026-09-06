#

## Preview
![Demo video](docs/screenshots/final.mp4)

arxiv-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-97%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

The high-density arXiv research pipe for AI agents and humans — search papers, extract clean Markdown from experimental HTML, map citation lineages, and search a local hybrid RAG depot.

**v0.7.0** · Intel lane · FastMCP 3.2 · [Releases](https://github.com/sandraschi/arxiv-mcp/releases)

---

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [What you can do](#what-you-can-do)
- [Ports](#ports)
- [Documentation](#documentation)
- [Requirements](#requirements)
- [License](#license)

---

## Features

- **Clean text extraction** — prefers arXiv experimental HTML → Markdown over fighting PDF columns
- **Hybrid local depot** — SQLite FTS5 (BM25) + LanceDB vectors; keyword, semantic, or hybrid RRF search
- **Citation graphs** — Semantic Scholar lineage for any paper
- **DOI resolution** — Unpaywall + Crossref for OA full text from 50,000+ publishers
- **Lab blogs** — Anthropic, DeepMind, Google Research feeds alongside arXiv
- **Code-hunt pipeline** — track open-weight repo drops; optional push to aiwatcher-mcp
- **Agent-native** — sampling, bundled skills, prompts, prefab paper cards

---

## Quick start

Download **`arXiv MCP_*_x64-setup.exe`** from [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest) → double-click → launch **arXiv MCP**.

Developers from source:

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
uv sync --extra rag
.\start.ps1
```

Dashboard **http://127.0.0.1:10771** · backend **http://127.0.0.1:10770** · MCP HTTP **/mcp**

All install paths: **[INSTALL.md](INSTALL.md)**

---

## What you can do

**Discovery**

> What are the most cited cs.RO papers from the last week?

**Deep read**

> Pull full text for 2401.00001 and summarize the methods section.

**Corpus**

> Ingest these five consciousness papers into my depot and run a hybrid search for "global workspace vs IIT."

**Fleet code-hunt**

> Run a code-hunt scan on cs.AI and show papers with live GitHub repos from watch-list authors.

---

## Ports

| Service | Port | URL |
|---------|------|-----|
| Backend (REST + MCP `/mcp`) | 10770 | http://127.0.0.1:10770 |
| Web dashboard | 10771 | http://127.0.0.1:10771 |

---

## Documentation

| Doc | Contents |
|-----|----------|
| [INSTALL.md](INSTALL.md) | Options A–E (Tauri desktop primary), verify, MCPB |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Env vars, RAG, sampling, code-hunt, integrations |
| [docs/TOOLS.md](docs/TOOLS.md) | MCP tools, prompts, skills |
| [docs/WEBAPP.md](docs/WEBAPP.md) | Dashboard features and routes |
| [docs/CURSOR-MCP.md](docs/CURSOR-MCP.md) | Cursor, Claude Desktop, HTTP MCP |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Backend, storage, transport layers |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | just, lint, test, contributing |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors and fixes |
| [docs/ARXIV.md](docs/ARXIV.md) | Recency philosophy, HTML vs PDF |
| [docs/DOI_RESOLUTION.md](docs/DOI_RESOLUTION.md) | Unpaywall, Crossref, OA statuses |
| [docs/FASTMCP_FEATURES.md](docs/FASTMCP_FEATURES.md) | Dual transport, sampling, safety wrapping |
| [docs/CODEHUNT.md](docs/CODEHUNT.md) | Open-weight repo tracking pipeline |
| [docs/FLEET_INTEGRATION.md](docs/FLEET_INTEGRATION.md) | aiwatcher, readly, Intel lane hooks |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

Fleet central mirror: [mcp-central-docs/projects/arxiv-mcp](https://github.com/sandraschi/mcp-central-docs/tree/master/projects/arxiv-mcp)

---

## Requirements

- **Python 3.11+** via [uv](https://docs.astral.sh/uv/)
- **Node.js LTS** for the web dashboard (`web_sota/`)
- Optional: [Ollama](https://ollama.com) for local epistemic deep analysis / sampling
- Optional: `uv sync --extra rag` for LanceDB semantic search (recommended)
- Optional: `uv sync --extra apps` for prefab paper cards

---

## License

MIT — see [LICENSE](LICENSE).
