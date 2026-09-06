---
name: llm-guide
description: >
  User-facing guide to LLM choice in fleet webapps: local vs cloud tradeoffs,
  hardware requirements, Ollama/LM Studio setup, what fits a 24GB RTX 4090
  (including PRC open-weight models), cloud provider capabilities and pricing,
  and how fleet apps wire providers (Settings cards, backend proxy, keystore).
  Load when the user asks which model/provider to use, why chat is disabled,
  how to install a local LLM, or what anything costs.
tags: [llm, providers, ollama, lm-studio, gpu, cloud, pricing, models, open-weights]
---

# LLM Guide (fleet webapps)

Prices below: Meta = official docs 2026-09-06; everything else = OpenRouter
catalog snapshot 2026-09-06 (`GET https://openrouter.ai/api/v1/models`, USD per
1M tokens in/out). Prices move monthly — re-check live before budgeting:
[Meta pricing](https://ai.developer.meta.com/docs/pricing-rate-limits),
[OpenRouter models](https://openrouter.ai/models),
[DeepSeek](https://api-docs.deepseek.com/quick_start/pricing).

## 1. Local vs cloud in one table

| | Local (Ollama / LM Studio / vLLM) | Cloud (OpenAI, Anthropic, DeepSeek, OpenRouter, Meta) |
|---|---|---|
| Cost | Free after hardware | Per-token (see §6) |
| Privacy | Prompts never leave the machine | Prompts go to vendor (Meta Contributor tier explicitly trains on them — cheap for a reason) |
| Needs | NVIDIA GPU, 16GB VRAM min (§2), model downloaded | API key in Settings card, internet |
| Speed | 20–60 tok/s on RTX 4090 for 30B-class | Datacenter GPUs; fastest wall-clock for big models |
| Best for | Private docs, offline work, zero marginal cost | Frontier capability, huge context, no hardware |

Fleet rule: the app never talks to providers from the browser. Everything goes
through the backend proxy (`POST /api/llm/chat`, streaming SSE), keys stay in
the server keystore. If Chat is disabled, no local engine is detected AND no
cloud key is configured — fix it in Settings, not in chat.

## 2. Local requirements

- **GPU:** NVIDIA, **16GB VRAM minimum**. 16GB runs up to ~24B params in Q4;
  a 24GB RTX 4090 comfortably runs 32B dense or 30B MoE in Q4 (§4).
- **RAM/disk:** 32GB system RAM recommended; models are 10–20GB downloads each.
- **OS:** Windows 11. `start.ps1` expects providers on localhost ports below.

## 3. Ollama setup (how-to)

```powershell
winget install -e --id Ollama.Ollama   # install
ollama pull qwen3:32b                  # download a model (~20GB)
ollama serve                           # daemon; serves http://localhost:11434
```

- Verify: `http://localhost:11434/api/tags` lists installed models.
- Fleet apps probe this URL plus `/api/ps` (currently loaded — the app prefers
  the already-loaded model instead of evicting it).
- Models live in `%USERPROFILE%\.ollama`. `ollama run <model>` chats in terminal.
- LAN access: set `OLLAMA_HOST=0.0.0.0` before `ollama serve` (then Models are
  reachable to peers; keep the firewall in mind).

## 4. LM Studio setup (how-to)

1. Download from `lmstudio.ai`, install, open it.
2. Search tab → download a model (e.g. `qwen3-30b-a3b`, GGUF Q4_K_M).
3. Developer tab → toggle Server ON (port `1234`), load the model.
4. Verify: `http://localhost:1234/v1/models` returns the loaded model.
5. Fleet apps read `/v1/models` — OpenAI-compatible, same as Ollama's `/v1`.

vLLM note: production-grade server (Docker), same OpenAI-compatible shape on
port `8000`. Only worth it when serving one model to many clients; Ollama or
LM Studio is the right default on a desktop.

## 5. What fits a 24GB RTX 4090 (Q4 rule of thumb: ~0.6GB per billion params)

| Model | Params | Q4 size | Fits? | Note |
|---|---|---|---|---|
| Qwen3-8B / 14B | 8B / 14B | ~5 / ~9GB | yes, easy | Daily driver on small VRAM |
| Qwen3-32B | 32B dense | ~20GB | yes | Best open 32B-class: multilingual, coding |
| Qwen3-30B-A3B (+ coder) | 30B MoE, 3B active | ~18GB | yes | Fast (only 3B active per token) |
| DeepSeek-R1-Distill-Qwen-32B | 32B | ~20GB | yes | Reasoning distillate |
| gpt-oss-20b | ~20B | ~13GB | yes | OpenAI open-weight |
| Ministral-8B | 8B | ~5GB | yes | Mistral open-weight |
| Muse Glimmer 30B (GGUF) | 27.9B + opts | 16–18GB | yes | Fleet resident model (`local-llm-mcp`). Four local tags share ONE 27.9B Q4_K_M weight blob — they differ only in Modelfile pins, which is the confusing part (§5b) |
| DeepSeek-R1 / V3 full | ~671B | ~400GB | no | API only |
| Kimi K2 | ~1T (32B active) | ~500GB+ | no | API only (Moonshot platform) |
| Llama-4-Maverick / Scout | 400B / 109B | 60GB+ | no | API only |
| GLM-4.5 full | ~355B | ~200GB | no | API only; small GLM-4-9B fits |

PRC open-weight labs to watch: **DeepSeek** (V-series, R-distillates),
**Alibaba Qwen** (Qwen3 dense + MoE + Coder — the safest local bet),
**Zhipu GLM** (strong bilingual CN/EN), **Moonshot Kimi** (long-context agents,
cloud-only at K2 scale), **MiniMax** (M-series). Verify param counts on
Hugging Face, multiply by 0.6GB/B for Q4 — that decides fit, not the brand.

## 5b. Muse Glimmer tags demystified (verified 2026-09-06 via `ollama show`)

One 27.9B Q4_K_M weight blob, four tags — the tag only pins Modelfile options:

| Tag | Size | num_ctx pin | Vision (1.9B projector) | Thinking | Notes |
|---|---|---|---|---|---|
| `muse-glimmer:latest` | 18GB | none (model max 131072) | yes | yes | Full fat; needs ctx cap or KV offloads to CPU |
| `muse-glimmer-65k` | 18GB | 65536 | yes | yes | Same weights, saner KV |
| `muse-glimmer-131k` | 18GB | 131072 | yes | yes | Max context; slowest, hungriest |
| `muse-glimmer-kquant` | 16GB | 32768 | no | yes | Practical pick: no projector weight, preset SYSTEM prompt, `num_predict` 4096 cap |

Quirks that bite: custom `RENDERER glimmer`/`PARSER glimmer` + `TEMPLATE {{ .Prompt }}`
(plain chat UIs may render oddly — the fleet proxy passes text through, unaffected);
default `temperature 1.0 / top_k 64 / top_p 0.95` is Meta's spec, don't "fix" it
down blindly; `thinking` emits long reasoning traces (the kquant `num_predict`
cap trims them); first load from spinning disk takes minutes (28B ≈ 16–18GB),
subsequent calls are fast; long-ctx pins + 4090 = same KV-offload trap as
Gemma4 — the fleet proxy caps Ollama at 32768 for exactly this reason.
If even trivial prompts hang with nothing loaded, check VRAM headroom FIRST
(`nvidia-smi`, or fleet `just gpu-status` — InvokeAI/games routinely sit on
20GB and starve Ollama into load-looping, which looks exactly like a broken
model but isn't).

## 6. Cloud providers (the five + gateway)

| Provider | Base URL | Key env | Dashboard |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` | platform.openai.com |
| Anthropic | `https://api.anthropic.com/v1` (Messages API) | `ANTHROPIC_API_KEY` | console.anthropic.com |
| DeepSeek | `https://api.deepseek.com` (`/chat/completions`, no `/v1`) | `DEEPSEEK_API_KEY` | platform.deepseek.com |
| OpenRouter | `https://openrouter.ai/api/v1` (200+ models, one key) | `OPENROUTER_API_KEY` | openrouter.ai/keys |
| Meta | `https://api.meta.ai/v1` | `MODEL_API_KEY` (official name) | dev.meta.ai |

Keys go in the provider's Settings card (password field) → server keystore
(`data/llm_keys.json`, 0600) or env var (env wins). Cards show Configured /
Missing key, never the key itself.

## 7. Pricing (USD per 1M tokens in/out; verify live)

Meta official: Standard `1.25 / 4.25` (cached input 0.15, data never trains);
**Contributor `0.10 / 0.20`** (cached 0.002 — trains on your prompts, 20x cheaper
than Standard, 250x cheaper than a $50/M flagship). Contributor limits:
100 RPM / 3M TPM per team vs Standard 3000 RPM / 4M TPM.

OpenRouter snapshot 2026-09-06 (1M in / out):
cheap bulk — `deepseek-v4-flash` 0.08/0.16, `qwen3-32b` 0.08/0.28,
`gpt-4o-mini` 0.15/0.60, `llama-4-maverick` 0.20/0.70, `glm-4.5-air` 0.13/0.85;
mid — `gpt-4o` 2.50/10.00, `sonnet-4` 3.00/15.00, `glm-4.5` 0.60/2.20,
`deepseek-v4-flash` 0.08/0.16; flagship — `fable-5.1` 10.00/50.00 (days old,
successor of deprecated `fable-5`, 1M ctx), `opus-4` 15.00/75.00,
`gpt-5-pro` 15.00/120.00, `gpt-6-astra-pro` 10.00/50.00.

Reading rule: output tokens cost 2–8x input. Long agentic loops are won or lost
on output price — that is the whole Contributor arbitrage.

## 8. Capability notes (stable roles, not benchmarks)

- `muse-spark-1.3[-contributor]`: agentic/coding loops, 1M context, tool calling.
- GPT-4o / 5.x: general flagship; mini/nano for cheap bulk.
- Claude Sonnet: coding-agent sweet spot; Opus: max capability, flagship price; Fable 5.1: newest Anthropic flagship line (replaces deprecated Fable 5), 1M context.
- DeepSeek V4 flash: the DeepSeek pick (newest and stronger than pro despite the name — pro skipped); flash is also the cheapest usable bulk at 0.08/0.16.
- Qwen3 / Coder: best local-or-cheap-API coding + multilingual.
- Kimi K2, GLM-4.5, Grok, Gemini flash/pro: horses for courses via OpenRouter
  with one key — compare live per task, prices above are the starting grid.

## 9. Fleet wiring (for agents, not end users)

Provider registry + proxy + keystore: `arxiv-mcp/docs/SPEC-llm-providers.md`.
Gateway reference: `local-llm-mcp` (`POST :10833/v1/chat/completions`,
`x-lightport-provider` header). When adding a provider: registry row, curated
fallback list, Settings card, Test button path, never return key bytes from GET.
