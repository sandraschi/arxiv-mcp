# Installation Guide

This guide will help you get **arxiv-mcp** running on your local machine.

## Prerequisites

- **Python 3.11+**: The core server is written in Python.
- **uv**: We recommend [uv](https://docs.astral.sh/uv/) for incredibly fast dependency management.
- **Node.js (LTS)**: Required only if you want to run the web dashboard.
- **Git**: To clone the repository.

---

## Step-by-Step Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
```

### 2. Python Environment

Use `uv` to create a virtual environment and install dependencies:

```powershell
uv sync
```

This will install the core dependencies listed in `pyproject.toml`.

### 3. Optional Extras

If you want to use the **Rich Paper Cards** (via `prefab-ui`) in the dashboard or supported MCP clients, install the `apps` extra:

```powershell
uv sync --extra apps
```

For development (testing, linting), use:

```powershell
uv sync --extra dev
```

---

## Running Modes

### A. Stdio Mode (for MCP Clients)

Use this mode to integrate with Cursor, Claude Desktop, or other tools that communicate over standard input/output.

```powershell
uv run python -m arxiv_mcp --stdio
```

### B. Serve Mode (REST API + HTTP MCP)

Use this mode to start the FastAPI backend, which serves the REST API for the dashboard and allows MCP connections over HTTP.

```powershell
uv run python -m arxiv_mcp --serve
```

---

## Environment Variables

Copy `.env.example` to `.env` to customize your installation:

```powershell
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ARXIV_MCP_HOST` | `127.0.0.1` | The bind address for the server. |
| `ARXIV_MCP_PORT` | `10770` | The port for the backend. |
| `ARXIV_MCP_DATA_DIR` | `data/arxiv_mcp` | Path to store the SQLite database and ingested text. |
| `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` | *(None)* | Optional key for higher rate limits on citations. |
| `ARXIV_PREFAB_APPS` | `1` | Set to `0` to disable prefab tool registration. |

---

## Troubleshooting

- **Port Conflicts**: If port `10770` or `10771` is taken, update your `.env` and the Vite config in `web_sota/vite.config.ts`.
- **403 Forbidden**: If you get rate limited by arXiv, try increasing the `ARXIV_MCP_CLIENT_DELAY_SECONDS` in your environment.
- **SQLite Errors**: Ensure the `ARXIV_MCP_DATA_DIR` is writable by your user.

---

## Development

If you want to contribute to **arxiv-mcp**:

1.  **Install Dev Tools**:
    ```powershell
    uv sync --extra dev
    pre-commit install
    ```
2.  **Lint & Format**:
    ```powershell
    uv run ruff check src
    uv run ruff format src
    ```
3.  **Tests**:
    ```powershell
    uv run pytest
    ```
4.  **Type Checking**:
    ```powershell
    uv run ty check src
    ```
