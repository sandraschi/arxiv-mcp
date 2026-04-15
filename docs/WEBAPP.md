# Webapp Dashboard

The **arxiv-mcp** dashboard is a high-performance, local-first web interface for researchers. It allows you to search papers, visualize research threads, and manage your local ingested corpus.

## Getting Started

The dashboard is built with **Vite** and **React**. To run it, you need to have the backend running first (see [INSTALL.md](INSTALL.md)).

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

### 2. The Depot (Local RAG)
- **Ingested Papers**: View all papers you've pulled the full text for.
- **FTS Search**: Search across the body text of all ingested papers using SQLite FTS5.
- **Recency Filtering**: Apply a "max age" filter (e.g., last 180 days) for fast-moving fields.

### 3. Favorites
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
