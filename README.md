# arxiv-mcp

## Preview

<video src="https://github.com/sandraschi/arxiv-mcp/raw/main/docs/screenshots/final.mp4" controls="controls" muted="muted" preload="metadata" width="720"></video>

*Search, deep-read, and corpus RAG — from chat, in seconds.*

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-97%20passing-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

Research assistant for scientific papers: search arXiv, read full text, track citations and code drops, remember everything in a local library.

The high-density arXiv research pipe for AI agents and humans — search papers, extract clean Markdown from experimental HTML, map citation lineages, and search a local hybrid RAG depot.

**v0.7.1** · Intel lane · FastMCP 3.2 · [Releases](https://github.com/sandraschi/arxiv-mcp/releases)

**Why this instead of arxiv.org?** arXiv search finds titles. This *reads* the papers (clean full-text Markdown, no PDF-column soup), *remembers* what you read (local hybrid RAG depot you can query forever), shows *who cites whom* (citation graphs), and *watches for code drops* (open-weight repo tracking) — all from chat, all agent-callable, all free and local-first.

---

## Contents

- [Features](#features)
- [What you can do](#what-you-can-do)
- [Quick start](#quick-start)
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

## What you can do

No API keys, no cloud, no subscription. Pick a row, paste the prompt into chat, get the result.

| I want to... | Paste this into chat | What you get |
|---|---|---|
| Find papers about chatbots | Find recent papers about LLM chatbots and conversational agents, newest first | Ranked list with abstracts, links, and citation counts |
| Never miss a paper again | Scan cs.AI and cs.LG from the last 72 hours, flag mechanistic interpretability | Triaged digest of what's new and what matters |
| See who built on a paper | Map the citation graph around 2401.00001 | Who cited it, who refuted it, where the idea went |
| Actually read a paper | Pull full text for 2401.00001 and summarize the methods section | Clean Markdown full text (no PDF-column soup) + summary |
| Get past a paywall | Get the open-access full text behind this DOI: 10.1016/j.cell.2018.06.048 | Best OA PDF from 50,000+ publishers via Unpaywall/Crossref |
| Build my own library | Ingest these five consciousness papers, then hybrid-search "global workspace vs IIT" | A permanent local corpus (keyword + semantic search) |
| Find the code, not just the paper | Code-hunt scan on cs.AI — show papers with live GitHub repos | Papers with working, still-alive repos attached |
| Get pinged on new weights | Watch these authors via aiwatcher and alert me on open-weight drops | Push alerts the week a model goes public |
| Compare rival claims | Cross-check these three papers: convergence, contradictions, replication risks | Structured verdict instead of three separate summaries |
| Read the labs, not just arXiv | What did Anthropic and DeepMind publish this month, related to my depot? | Blog posts distilled and linked to your corpus |

---

## Quick start

Download **`arXiv MCP_*_x64-setup.exe`** from [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest) → double-click → launch **arXiv MCP**.

Claude Desktop bundle (one-liner):
```powershell
powershell -c "irm https://github.com/sandraschi/arxiv-mcp/releases/latest/download/install.ps1 | iex"
```

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

Every line below is a real prompt you can paste into chat once the server is connected. No API keys, no cloud, no subscription.

**Discover — never miss a paper again**

> What are the most cited cs.RO papers from the last week?

> Scan cs.AI + cs.LG from the last 72 hours and flag anything on mechanistic interpretability.

> Map the citation graph around 2401.00001 — who built on it, who refuted it?

**Deep-read — full text, not abstracts**

> Pull full text for 2401.00001 and summarize the methods section.

> Get me the actual paper behind DOI 10.1016/j.cell.2018.06.048 — open-access full text, not the paywall.

> Cross-check these three papers: where do they converge, where do they contradict, and which claims would a replication audit flag?

**Remember — your own research corpus**

> Ingest these five consciousness papers into my depot and run a hybrid search for "global workspace vs IIT."

> I read 40 papers on diffusion last month. Which ones actually released code, and are the repos still alive?

**Watch — the code-hunt pipeline**

> Run a code-hunt scan on cs.AI and show papers with live GitHub repos from watch-list authors.

> Alert me (via aiwatcher) the next time a paper from these authors drops open weights.

**Learn — beyond arXiv**

> What did Anthropic and DeepMind publish on the blogs this month, and how does it relate to my depot?

> Give me the adversarial deep-read of this paper: steelman it, then try to break it.

---

## Fleet Crossconnects (Companions)

`arxiv-mcp` works completely standalone. You can optionally connect it with companion servers in the `sandraschi` fleet to unlock extended features:

| Companion Server | Feature Unlocked | Status | Setup |
|---|---|---|---|
| [`calibre-mcp`](https://github.com/sandraschi/calibre-mcp) | store_paper_to_calibre, pdf-ebook-catalog | Optional | [Install Guide](https://github.com/sandraschi/calibre-mcp#quick-install) |

> **Self-Contained Companions**: Fleet companions operate independently. Installing companions does not trigger transitive dependency chains.

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
