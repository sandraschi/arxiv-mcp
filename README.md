# arxiv-mcp

**arXiv MCP server**  search papers, pull clean text when experimental HTML exists, follow citations, and stash ingested text in a **local corpus** (SQLite FTS5).

*Repo: [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)*

---

### Why bother?

Keeping up with arXiv is noisy. You bounce between tabs, PDFs that dont copy well, and half-remembered paper IDs. **arxiv-mcp** gives an agent (or you, via a small dashboard) one consistent pipe: **find  read  connect  save**. When arXivs **experimental HTML** exists for a paper, you get **Markdown-friendly text** without fighting a PDF first.

**Good fit if you:** skim new cs.AI / cs.LG drops, deep-read a few papers a week, or want ingested text in a **local corpus** for RAG and notes.

---

### Get started (two minutes)

**Prerequisites:** [Python 3.11+](https://www.python.org/), [uv](https://docs.astral.sh/uv/), and for the dashboard [Node.js](https://nodejs.org/) (LTS is fine).

**A  Use it inside Cursor (or any MCP client over stdio)**

```powershell
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync
uv run python -m arxiv_mcp --stdio
```

Add a server command pointing at that line (repo root as cwd). Youre done.

**Dual transport (FastMCP 3.1):** the same tool surface is available over **stdio** (above) and, after **`--serve`**, over **streamable HTTP** at `http://127.0.0.1:10770/mcp`. Machine-readable discovery: `GET http://127.0.0.1:10770/.well-known/mcp/manifest.json`.

**B  Browser dashboard + HTTP MCP**

From the **same repo root** as in **A** (after `git clone` and `uv sync` there):

```powershell
uv sync
uv run python -m arxiv_mcp --serve
```

In another terminal, from the same repo:

```powershell
.\start.ps1
```

Open the URL Vite prints (by default **http://127.0.0.1:10771**). The UI talks to the API on **10770** (Vite proxies `/api` in dev and in `npm run preview`).

The **Search** page loads suggested queries, keeps **recent searches** and optional **saved favorites** (stored in the browser only), and shows clear errors if the backend is unreachable.

---

### What you can ask the agent to do

- *Whats new in cs.RO in the last day?*
- *Pull the full text for this arXiv id as markdown if HTML exists.*
- *Who cites this paper / what does it cite?*
- *Save this paper into my local corpus for later search.*

Exact tool names, ports, and stack live in **[docs/TECHNICAL.md](docs/TECHNICAL.md)**.

---

### Configuration

Copy `.env.example` to `.env` if you want custom host/port or a Semantic Scholar API key. Most people can skip this at first.

---

### Changelog

Release notes and migration hints: **[CHANGELOG.md](CHANGELOG.md)**.

### License

MIT  see [LICENSE](LICENSE).
