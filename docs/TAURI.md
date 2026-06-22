# Tauri 2.0 Native Desktop App

> **End users:** download `arXiv MCP_*_x64-setup.exe` from [Releases](https://github.com/sandraschi/arxiv-mcp/releases/latest) and double-click. This page is for **maintainers** building the installer.

arXiv MCP ships with a Tauri 2.0 native wrapper — **one** Windows installer and **one** desktop shortcut. The Python backend is embedded inside the operator bundle (extracted to `%LOCALAPPDATA%` cache on launch, not a sibling `.exe` in the install folder).

## Build (maintainers)

```powershell
just build-native
```

Installer output:

```text
native/target/release/bundle/nsis/arXiv MCP_0.7.0_x64-setup.exe
```

Sidecar only:

```powershell
just build-sidecar
```

## Architecture

| Layer | Port | Notes |
|-------|------|-------|
| Tauri operator | — | Single install shortcut; WebView2 + UI |
| Embedded Python backend | **10770** | Bundled resource → app cache → child process |

In production the UI calls `http://127.0.0.1:10770` directly (no dev proxy).

## Dev mode

```powershell
cd native
npm install
npx @tauri-apps/cli dev
```

Frontend dev server: `http://localhost:10771` (see `native/tauri.conf.json`).

## Prerequisites

- Rust + Cargo (`rustup`)
- Node.js 20+
- `uv` + project deps (`uv sync --extra rag`)
- WebView2 (bootstrapped by NSIS if missing)
