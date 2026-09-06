# SPEC: Unified Local + Cloud LLM Providers (arxiv-mcp pilot)

Status: draft. Pilot repo: `arxiv-mcp`. Pattern target: fleet standard
(`WEBAPP_SOTA_STANDARDS.md` VI-extension + assfix rows) after pilot proves out.

Decisions locked with repo owner (2026-09-06):
1. Keys in `data/llm_keys.json` (0600, gitignored) + env override wins.
2. ALL traffic via backend proxy `POST /api/llm/chat` (local + cloud). No direct browser->provider.
3. All five cloud providers: OpenAI, Anthropic, DeepSeek, OpenRouter, Meta.
4. Curated model fallback lists; live fetch when key/configured.
5. Streaming required (SSE, OpenAI chunk passthrough).
6. Selection stays in localStorage (`llm_provider` / `llm_model`) for now; Zustand migration deferred to standard promotion.

## 1. Why per-repo proxy (not gateway-only)

`local-llm-mcp` (:10833) already IS the fleet cloud gateway (26 adapters, OpenAI-compat
`POST /v1/chat/completions`) despite its name. But `arxiv-mcp` must work standalone
(`start.bat` with no gateway running). So the pilot implements a self-contained proxy
in `arxiv-mcp`, with provider IDs + env names identical to the gateway's, so a later
"delegate to gateway when reachable, fallback to direct" step is a drop-in.
Same pass adds the missing Meta adapter to the gateway (2 files, separate commit).

## 2. Provider registry (canonical IDs)

| ID | Label | Kind | Chat base | Key env | Protocol |
|----|-------|------|-----------|---------|----------|
| `ollama` | Ollama | local | `http://localhost:11434` + native `/api/chat` | none | Native (NOT `/v1`: it ignores `options`, and 262k-ctx models offload to CPU — measured 3 vs 79 tok/s). `options.num_ctx` capped at 32768. lmstudio/vllm stay on `/v1` (proper OpenAI servers). |
| `lmstudio` | LM Studio | local | `http://localhost:1234/v1` | none | OpenAI-compat |
| `vllm` | vLLM | local | `http://localhost:8000/v1` | none | OpenAI-compat |
| `openai` | OpenAI | cloud | `https://api.openai.com/v1` | `OPENAI_API_KEY` | OpenAI native |
| `anthropic` | Anthropic | cloud | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | Messages API (`/messages`, `x-api-key` header, `anthropic-version: 2023-06-01`); proxy maps OpenAI messages <-> Messages (system extraction, `max_tokens` default 1024) |
| `deepseek` | DeepSeek | cloud | `https://api.deepseek.com` (chat path `/chat/completions`, NO `/v1` prefix — verified 2026-09-06) | `DEEPSEEK_API_KEY` | OpenAI-compat |
| `openrouter` | OpenRouter | cloud | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | OpenAI-compat + `HTTP-Referer`/`X-Title` headers |
| `meta` | Meta | cloud | `https://api.meta.ai/v1` | `MODEL_API_KEY` (official name per Meta docs; dashboard: dev.meta.ai) | OpenAI-compat (`POST /v1/chat/completions`, `GET /v1/models`, Bearer) |

Meta facts verified 2026-09-06 against `ai.developer.meta.com/docs`
(api-reference.md: base URL + auth; models.md: IDs).

Curated fallbacks (used when no key / live fetch fails):
- openai: `gpt-4o`, `gpt-4o-mini`
- anthropic: `claude-sonnet-4-20250514`, `claude-opus-4-20250514`
- deepseek: `deepseek-v4-pro`, `deepseek-v4-flash` (+ `deepseek-v4-flash-vision-exp` for image input; verified 2026-09-06 — old chat/reasoner IDs retired)
- openrouter: `openrouter/auto`, `anthropic/claude-sonnet-4`, `openai/gpt-4o`, `meta-llama/llama-4-maverick`
- meta: `muse-spark-1.3-contributor` (fleet default: $0.20/M out, training-on-prompts acceptable per owner 2026-09-06), `muse-spark-1.3`, `muse-spark-1.2-contributor`, `muse-spark-1.2`, `muse-spark-1.1` (Standard tier: prompts never train models)

## 3. Backend (`src/arxiv_mcp/`)

- `config.py`: `llm_provider: str = "ollama"`, `llm_model: str = "gemma4:12b"`
  (fleet default: strong 10–15B Q4; 3B-class models are out as defaults).
  Keys are NOT config fields (keystore + env only). Keep existing `sampling_*` untouched.
- New `llm_providers.py`: `PROVIDERS` registry (table above + curated lists),
  keystore load/save (`resolved_data_dir()/llm_keys.json`, 0600, `{provider: key}`),
  `get_key(provider)` (env first, then keystore), `configured(provider)` (bool only),
  local probe helper (httpx 3s, `/models`), cloud models helper
  (live `GET {base}/models` with key, fallback curated), chat forward helper
  (httpx, OpenAI body passthrough; anthropic mapping; openrouter extra headers).
- `app.py` (all new routes under `/llm`):
  - `GET /api/llm/providers` -> `[{id, label, kind, base_url, detected?, configured?, needs_key}]`. Never returns key material. Superset of `/llm/discover` (kept as compat shim).
  - `GET /api/llm/models?provider=` -> `{provider, models: [...], source: "live"|"curated"}`.
  - `POST /api/llm/chat` `{provider, model, messages}` -> `{content}` (non-stream).
  - `POST /api/llm/chat/stream` same body -> `text/event-stream` SSE, OpenAI `data:` chunk passthrough + `data: [DONE]`.
  - `POST /api/settings/llm` extended with write-only `api_key?: str`; saves selection to `llm_settings.json`, key to keystore. `GET /api/settings/llm` additionally returns `api_key_configured: bool`, never the key.
  - `DELETE /api/settings/llm/key?provider=` clears one key.
- Security: keys never in GET responses, logs, or exceptions. Key file 0600 + gitignored.
  No key in localStorage, bundle, or URL.

## 4. Frontend (`web_sota/src/`)

- `SettingsPage.tsx`: keep `llm-provider-select` / `llm-model-select` testids.
  Primary UI becomes one card per provider (8 cards, local section + cloud section):
  kind badge (Local/free vs Cloud/paid), status dot (Detected / Configured / Missing key),
  endpoint input (editable local + openai-compat custom, readonly pinned clouds),
  password key input (cloud only, show/hide, Save/Clear, placeholder `sk-... configured`
  vs empty), Test button (`llm-test-{id}` -> models fetch or minimal chat).
  New testids: `llm-provider-card-{id}`, `llm-key-{id}`, `llm-test-{id}`.
  Model dropdown populated from `GET /api/llm/models?provider=` (live or curated badge).
- `ChatPage.tsx`: delete hardcoded `OLLAMA` direct fetch. Send via
  `POST /api/llm/chat/stream` (SSE reader, progressive render) with selected
  provider/model; fallback non-stream on SSE failure. Controls bar shows
  `{provider} / {model}` + kind badge. Disabled only when no local detected AND
  no cloud configured. Keep `chat-*` testids + personalities + history + export.
- No new deps. No key in localStorage (selection only, per decision 6).

## 5. Verify

- `uv run ruff check src/`, `ruff format --check`, `pyright src/`, `uv run pytest tests/ -q`
  (add `tests/test_llm_providers.py`: keystore roundtrip 0600, GETs leak no key,
  providers list shape, anthropic mapping unit).
- Webapp `tsc --noEmit`, `biome check`, `npm run build` (no Browserslist warning).
- Manual: save Meta key -> card shows Configured -> models list shows curated ->
  Chat streams via `muse-spark-1.3`; reload -> selection persists, key field empty
  placeholder (never refilled); `GET /api/settings/llm` contains no key bytes.
- Batch discipline: max 5 files per op, `.bak` before 3+ file mutations, one commit.

## 6. LLM onboarding step (fresh install, fleet pattern)

Every webapp with chat (or floater) gets an LLM onboarding step on first run:
`GET /api/llm/onboarding` (shipped in this pilot) returns detected locals,
configured clouds, and a recommended starter path (local when detected, else
configured cloud, else Meta Contributor key as cheapest instant path with
Ollama install as the free alternative). The UI presents what exists, what can
be installed, and lets the user pick the optimum starter path; selection saves
via `POST /api/settings/llm`. Later changes (paste cloud key, install Ollama)
happen in the Settings provider cards — including a one-click Ollama-install
button on the Ollama card (`POST /api/llm/install`, allowlisted winget command,
polled status; manual commands as fallback).

## 7. Out of scope (follow-ups)

- Zustand `store/llm.ts` migration (deferred per decision 6).
- Gateway delegation (`local-llm-mcp` first, direct fallback).
- `docs/ONBOARDING.md` key-setup section + `CONFIGURATION.md` env table.
- Fleet standard text (VI-extension) + assfix checklist rows (separate proposal after pilot).
- local-llm-mcp Meta adapter: `gateway/adapters/meta.py` (subclass `OpenAIAdapter`,
  `base_url = "https://api.meta.ai/v1"`, `api_key_env = "MODEL_API_KEY"`) + import line.
  Separate repo, separate commit.
