# arxiv-mcp

**Turn your AI assistant into a live arXiv lab** — search papers, pull clean text, follow citations, and stash what matters for later.

*Repo: [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)*

---

### Why bother?

Keeping up with arXiv is noisy. You bounce between tabs, PDFs that don’t copy well, and half-remembered paper IDs. **arxiv-mcp** gives an agent (or you, via a small dashboard) one consistent pipe: **find → read → connect → save**. When arXiv’s **experimental HTML** exists for a paper, you get **Markdown-friendly text** without fighting a PDF first.

**Good fit if you:** skim new cs.AI / cs.LG drops, deep-read a few papers a week, or want ingested text in a **local corpus** for RAG and notes.

---

### Get started (two minutes)

**Prerequisites:** [Python 3.11+](https://www.python.org/), [uv](https://docs.astral.sh/uv/), and for the dashboard [Node.js](https://nodejs.org/) (LTS is fine).

**A — Use it inside Cursor (or any MCP client over stdio)**

```powershell
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync
uv run python -m arxiv_mcp --stdio
```

Add a server command pointing at that line (repo root as cwd). You’re done.

**B — Browser dashboard + HTTP MCP**

```powershell
uv sync
uv run python -m arxiv_mcp --serve
```

In another terminal, from the same repo:

```powershell
.\start.ps1
```

Open the URL Vite prints (by default **http://127.0.0.1:10771**). The UI talks to the API on **10770**.

---

### What you can ask the agent to do

- *“What’s new in cs.RO in the last day?”*
- *“Pull the full text for this arXiv id as markdown if HTML exists.”*
- *“Who cites this paper / what does it cite?”*
- *“Save this paper into my local corpus for later search.”*

Exact tool names, ports, and stack live in **[docs/TECHNICAL.md](docs/TECHNICAL.md)**.

---

### Configuration

Copy `.env.example` to `.env` if you want custom host/port or a Semantic Scholar API key. Most people can skip this at first.

---

### License

MIT — see [LICENSE](LICENSE).
