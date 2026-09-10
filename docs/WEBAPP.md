# Webapp Dashboard

The **arxiv-mcp** dashboard is a high-performance, local-first web interface for researchers. It allows you to search papers, visualize research threads, and manage your local ingested corpus.

## Getting Started

The dashboard is built with **Vite** and **React**. To run it, start the backend first (see [../INSTALL.md](../INSTALL.md)).

### Development Mode (with HMR)
From the repo root:

```powershell
.\start.ps1
```

This starts the Vite dev server, typically at **http://localhost:10771**.

### Preview Mode (Production Build)
To test the production build:

```powershell
npm run build
npm run preview
```

## Main Features

### 1. Unified Search
- **Suggested Queries**: A rotating list of prompts to get you started.
- **Category Filters**: Easily toggle between AI, Robotics, Physics, etc.
- **Search History**: Automatically keeps track of your last 12 queries (browser-local).

### 2. The Depot (Hybrid RAG & Reader)
- **Ingested Papers**: View all papers you've pulled the full text for (prefers arXiv experimental HTML when available).
- **View Modes**: Toggle between **Card Grid** (multi-column) and **Compact List** (dense tabular rows) views; state is saved to `localStorage`.
- **Flexible Layouts**: Switch between **Stacked** (papers list on top, full-width Reader pane below) and **Split** (side-by-side) modes, or pop open a **Fullscreen** reading modal.
- **Sorting**: Sort papers by Newest Ingested, Oldest Ingested, Title (A-Z or Z-A), Most Claims, or arXiv ID.
- **Filtering & Reset**: Filter by search query, epistemic mode, and verification needs with an active-filter badge counter and a one-click **Reset filters** button.
- **1-Click Favoriting**: Star papers directly from the card, table row, inline reader header, or fullscreen viewer.
- **FTS Search**: Keyword/BM25 via SQLite FTS5.
- **Semantic Search**: LanceDB vector similarity (`uv sync --extra rag`).
- **Hybrid mode**: Reciprocal-rank fusion of FTS + vectors (default on `/api/depot/search?mode=hybrid`).
- **Recency Filtering**: Apply a "max age" filter (e.g., last 180 days) for fast-moving fields.

### 3. Calibre Integration
Each paper card in search results has two store buttons:
- **Depot**: Ingests HTML→Markdown into the local SQLite FTS corpus for RAG search.
- **Calibre**: Downloads the PDF, fetches metadata (title, authors, abstract, arXiv categories), auto-tags by category, sets the abstract as the book comment, optionally attaches the HTML→Markdown as a TXT format, and adds everything to **Calibre-Bibliothek IT**. The Calibre button is independent — you can use either or both.

### 4. Favorites
- **Pick from Depot**: Directly select any ingested paper from a dropdown for 1-click addition without typing IDs.
- **Manual Input**: Collapsible panel to manually bookmark external arXiv IDs with custom titles and notes.
- **Search**: Instant client-side search across saved favorites.
- **Direct Reader Navigation**: "Read in Depot" button to open any favorite straight into the Depot reader.
- Favorites and notes are persisted locally for privacy and speed.

### 4. Lab Blogs
- Dedicated tabs for **Anthropic**, **DeepMind**, **Google Research**, and **Google AI**.
- One-click "Known Posts" buttons for frequent research papers.

## Configuration & Ports

| Component | Default Port | Description |
| :--- | :--- | :--- |
| **Backend** | `10770` | FastAPI / MCP endpoint. |
| **Frontend**| `10771` | Vite dashboard interface. |

The frontend is pre-configured to proxy `/api` calls to port `10770`. If you change the backend port, you must also update `web_sota/vite.config.ts`.
