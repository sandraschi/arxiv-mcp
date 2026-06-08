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

### 2. The Depot (Hybrid RAG)
- **Ingested Papers**: View all papers you've pulled the full text for (prefers arXiv experimental HTML when available).
- **FTS Search**: Keyword/BM25 via SQLite FTS5.
- **Semantic Search**: LanceDB vector similarity (`uv sync --extra rag`).
- **Hybrid mode**: Reciprocal-rank fusion of FTS + vectors (default on `/api/depot/search?mode=hybrid`).
- **Recency Filtering**: Apply a "max age" filter (e.g., last 180 days) for fast-moving fields.

### 3. Calibre Integration
Each paper card in search results has two store buttons:
- **Depot**: Ingests HTML→Markdown into the local SQLite FTS corpus for RAG search.
- **Calibre**: Downloads the PDF, fetches metadata (title, authors, abstract, arXiv categories), auto-tags by category, sets the abstract as the book comment, optionally attaches the HTML→Markdown as a TXT format, and adds everything to **Calibre-Bibliothek IT**. The Calibre button is independent — you can use either or both.

### 4. Favorites
- Save papers for later with **tags** and **notes**.
- Favorites are stored in your browser's `localStorage` for privacy and speed.

### 4. Lab Blogs
- Dedicated tabs for **Anthropic**, **DeepMind**, **Google Research**, and **Google AI**.
- One-click "Known Posts" buttons for frequent research papers.

## Configuration & Ports

| Component | Default Port | Description |
| :--- | :--- | :--- |
| **Backend** | `10770` | FastAPI / MCP endpoint. |
| **Frontend**| `10771` | Vite dashboard interface. |

The frontend is pre-configured to proxy `/api` calls to port `10770`. If you change the backend port, you must also update `web_sota/vite.config.ts`.
