# Fleet integration — aiwatcher, vla-mcp, supervisors

arxiv-mcp participates in the **open-weight / robotics research pipeline** alongside aiwatcher-mcp, vla-mcp, meta-mcp, and fleet-agent-mcp.

## Data flow

```
arxiv-mcp (code-hunt)  ──POST /api/fleet/ingest──►  aiwatcher-mcp
        │                                              │
        │  pipeline_liveness                           │  interests bundles
        ▼                                              ▼
meta-mcp / fleet-agent aggregate probes          Dashboard + distill + alerts

vla-mcp (pipeline complete) ──POST /api/fleet/ingest──►  aiwatcher-mcp

readly-mcp ◄── POST /api/content/match ──  arxiv-mcp (media traction)
     │                                              │
     └── aiwatcher READLY_ENABLED poll ────────────┘
```

## API keys (read this carefully)

### `AIWATCHER_API_KEY` — the only key that blocks fleet push

| Server | Variable | Required when |
|--------|----------|---------------|
| aiwatcher-mcp | `AIWATCHER_API_KEY` | You enable REST auth (optional) |
| arxiv-mcp | `ARXIV_MCP_AIWATCHER_API_KEY` | Same secret as above, for ingest + probes |
| vla-mcp | `VLA_AIWATCHER_API_KEY` | Same (falls back to `AIWATCHER_API_KEY`) |

**If `AIWATCHER_API_KEY` is empty** (default): no header needed; localhost ingest works.

**If you set `AIWATCHER_API_KEY`:** every producer must send:

```
X-AIWatcher-Key: <your-secret>
```

or `Authorization: Bearer <your-secret>`.

Exempt on aiwatcher (no key): `/health`, `/api/health`, `/metrics`, `/mcp`.

**Not** fleet-related:

- `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` — citation graph rate limits only
- `ARXIV_MCP_SAMPLING_API_KEY` — optional LLM sampling for epistemic tools

### Webapp gotcha

The aiwatcher **frontend** (10947) proxies to backend (10946). If auth is enabled, the Pipeline Health card may show 401 until the proxy forwards `X-AIWatcher-Key` or you access from loopback-only paths.

## Ports (fleet convention)

| Service | Backend | Webapp |
|---------|---------|--------|
| arxiv-mcp | 10770 | 10771 |
| aiwatcher-mcp | 10946 | 10947 |
| vla-mcp | 11024 | 11025 |
| robotics-mcp | 10706 | — |
| yahboom-mcp | 10892 | — |
| readly-mcp | 10863 | 10706 / 10846 |

**Wrong port alert:** `ARXIV_MCP_URL=http://localhost:10719` in aiwatcher is a known misconfig; use **10770**.

## Supervisor probes

These HTTP endpoints aggregate health:

- `GET http://127.0.0.1:10770/api/pipeline/liveness` — arxiv code-hunt
- `GET http://127.0.0.1:10946/api/pipeline/liveness` — aiwatcher feeds + upstream arxiv + vla
- `GET http://127.0.0.1:11024/api/pipeline/liveness` — vla robotics peers + pipeline age

**meta-mcp** `pipeline_liveness_check` and **fleet-agent** `pipeline_liveness_check` probe all three.

## aiwatcher interest bundles (relevant)

- **China Open Weights** — code-hunt drops, cs.SD/cs.RO, FunASR
- **VLA & Spatial AI** — vla-mcp pipeline events, Wall-OSS/X-VLA patterns
- **Robotics** — Fleet Events + embodied/VLA keywords

Fleet ingest items use `source: arxiv-codehunt` or `vla-mcp-pipeline` and match `Fleet Events` feed patterns.

## fleet-agent bridge

`vla` is registered in fleet-agent `FLEET_SERVERS` at `http://127.0.0.1:11024/mcp` alongside `arxiv` and `aiwatcher`.

## Quick diagnostic

1. `curl http://127.0.0.1:10946/api/health` — must be 200
2. `curl http://127.0.0.1:10770/api/pipeline/liveness` — check `aiwatcher_health`
3. If push fails with 401 — align `ARXIV_MCP_AIWATCHER_API_KEY` with `AIWATCHER_API_KEY`
4. `codehunt_stats_tool` — confirm `pushed_to_aiwatcher` increments after live drops
