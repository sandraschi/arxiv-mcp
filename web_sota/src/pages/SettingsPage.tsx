import { Check, Save, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPatch, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";

type Stats = {
  papers: number;
  favorites: number;
  chunks: number;
  data_dir: string;
  rag?: Record<string, unknown>;
};

type LlmDiscover = {
  ollama_detected?: boolean;
  configured_sampling_url?: string | null;
  configured_model?: string;
  recommendation?: string | null;
  probes?: { kind: string; url: string; status?: number; error?: string }[];
};

type MediaSettings = {
  media_ignore_botblocks: boolean;
  media_use_brighthand?: boolean;
  brighthand_configured?: boolean;
  brighthand_zone?: string | null;
  source?: string;
  strategy_default?: string;
  strategy_when_enabled?: string;
};

type PublicationRow = {
  id: string;
  name: string;
  status: string;
  valid_till: string | null;
  has_cookie: boolean;
  configured: boolean;
  usable: boolean;
  expired: boolean;
  env_keys: {
    user: string;
    password: string;
    valid_till: string;
    cookie: string;
  };
};

type PublicationsResponse = {
  publications: PublicationRow[];
  alerts: { severity: string; code: string; message: string }[];
  healthy: boolean;
};

type LlmConfig = {
  provider: string;
  endpoint: string;
  model: string;
};

const LLM_PROVIDERS = [
  { key: "ollama", label: "Ollama", defaultEndpoint: "http://localhost:11434" },
  {
    key: "lmstudio",
    label: "LM Studio",
    defaultEndpoint: "http://localhost:1234",
  },
  { key: "openai", label: "OpenAI-compatible", defaultEndpoint: "" },
  {
    key: "deepseek",
    label: "DeepSeek",
    defaultEndpoint: "https://api.deepseek.com",
  },
];

const PROVIDER_PROBES = [
  {
    name: "ollama",
    label: "Ollama",
    port: 11434,
    url: "http://localhost:11434/api/tags",
  },
  {
    name: "lmstudio",
    label: "LM Studio",
    port: 1234,
    url: "http://localhost:1234/v1/models",
  },
  {
    name: "vllm",
    label: "vLLM",
    port: 8000,
    url: "http://localhost:8000/v1/models",
  },
] as const;

function fetchModelsForProvider(
  providerKey: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const probe = PROVIDER_PROBES.find((p) => p.name === providerKey);
  if (!probe) return Promise.resolve([]);
  return fetch(probe.url, { signal })
    .then((r) => (r.ok ? r.json() : Promise.reject()))
    .then((data) => {
      if (providerKey === "ollama")
        return (data.models ?? []).map((m: { name: string }) => m.name);
      return (data.data ?? []).map((m: { id: string }) => m.id);
    })
    .catch(() => []);
}

export function SettingsPage() {
  const { log } = useLogger();

  const [stats, setStats] = useState<Stats | null>(null);
  const [llm, setLlm] = useState<LlmDiscover | null>(null);
  const [llmConfig, setLlmConfig] = useState<LlmConfig>(() => ({
    provider: localStorage.getItem("llm_provider") || "ollama",
    endpoint: "http://localhost:11434",
    model: localStorage.getItem("llm_model") || "llama3.2",
  }));
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmSaved, setLlmSaved] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [media, setMedia] = useState<MediaSettings | null>(null);
  const [mediaSaving, setMediaSaving] = useState(false);
  const [publications, setPublications] = useState<PublicationsResponse | null>(
    null,
  );
  const [providerStatus, setProviderStatus] = useState<
    Record<string, "probing" | "detected" | "not_found">
  >({
    ollama: "probing",
    lmstudio: "probing",
    vllm: "probing",
  });
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [noProviderDetected, setNoProviderDetected] = useState(false);
  const [features, setFeatures] = useState<Record<string, unknown> | null>(
    null,
  );
  const probeAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setStats(await apiGet<Stats>("/api/stats"));
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        setLlm(await apiGet<LlmDiscover>("/api/llm/discover"));
      } catch (e) {
        log("error", `LLM discover failed: ${e}`);
      }
    })();
    (async () => {
      try {
        const cfg = await apiGet<LlmConfig>("/api/settings/llm");
        if (cfg?.provider) setLlmConfig(cfg);
      } catch (e) {
        log("error", `LLM config load failed: ${e}`);
      }
    })();
    (async () => {
      try {
        setMedia(await apiGet<MediaSettings>("/api/settings/media"));
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        setPublications(
          await apiGet<PublicationsResponse>("/api/settings/publications"),
        );
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        const d = await apiGet<{ features?: Record<string, unknown> }>(
          "/api/capabilities",
        );
        setFeatures(d.features ?? null);
      } catch {}
    })();

    // Probe local LLM providers
    const ac = new AbortController();
    probeAbortRef.current = ac;
    (async () => {
      const results: Record<string, "probing" | "detected" | "not_found"> = {
        ollama: "probing",
        lmstudio: "probing",
        vllm: "probing",
      };
      const detections = await Promise.allSettled(
        PROVIDER_PROBES.map(async (probe) => {
          const r = await fetch(probe.url, {
            signal: ac.signal,
            cache: "no-store",
          });
          if (!r.ok) throw new Error("not found");
          return probe.name;
        }),
      );
      if (ac.signal.aborted) return;
      let anyDetected = false;
      for (const result of detections) {
        if (result.status === "fulfilled") {
          results[result.value as keyof typeof results] = "detected";
          anyDetected = true;
        }
      }
      for (const key of Object.keys(results)) {
        if (results[key] === "probing") results[key] = "not_found";
      }
      setProviderStatus({ ...results });
      setNoProviderDetected(!anyDetected);
    })();

    return () => ac.abort();
  }, [log]);

  // Fetch models when provider changes
  useEffect(() => {
    const ac = new AbortController();
    const probe = PROVIDER_PROBES.find((p) => p.name === llmConfig.provider);
    if (!probe) {
      setAvailableModels([]);
      return;
    }
    setProviderStatus((prev) => ({ ...prev, [llmConfig.provider]: "probing" }));
    fetchModelsForProvider(llmConfig.provider, ac.signal).then((models) => {
      if (ac.signal.aborted) return;
      setAvailableModels(models);
      setProviderStatus((prev) => ({
        ...prev,
        [llmConfig.provider]: models.length > 0 ? "detected" : "not_found",
      }));
      if (models.length > 0) {
        const saved = localStorage.getItem("llm_model");
        if (saved && models.includes(saved)) {
          setLlmConfig((prev) => ({ ...prev, model: saved }));
        } else {
          const first = models[0];
          setLlmConfig((prev) => ({ ...prev, model: first }));
          localStorage.setItem("llm_model", first);
        }
      }
    });
    return () => ac.abort();
  }, [llmConfig.provider]);

  const toggleIgnoreBotblocks = useCallback(async () => {
    if (!media || mediaSaving) return;
    const next = !media.media_ignore_botblocks;
    setMediaSaving(true);
    try {
      const updated = await apiPatch<MediaSettings>("/api/settings/media", {
        media_ignore_botblocks: next,
      });
      setMedia(updated);
      log(
        "info",
        next
          ? "Ignore bot blocks enabled (Jina enrichment)"
          : "Ignore bot blocks disabled",
      );
    } catch (e) {
      log("error", String(e));
    }
    setMediaSaving(false);
  }, [media, mediaSaving, log]);

  const toggleBrighthand = useCallback(async () => {
    if (!media || mediaSaving || !media.media_ignore_botblocks) return;
    const next = !media.media_use_brighthand;
    setMediaSaving(true);
    try {
      const updated = await apiPatch<MediaSettings>("/api/settings/media", {
        media_use_brighthand: next,
      });
      setMedia(updated);
      log(
        "info",
        next
          ? "Bright Hand enabled (Bright Data unlocker)"
          : "Bright Hand disabled",
      );
    } catch (e) {
      log("error", String(e));
    }
    setMediaSaving(false);
  }, [media, mediaSaving, log]);

  const saveLlm = useCallback(async () => {
    setLlmSaving(true);
    setLlmSaved(false);
    setLlmError(null);
    try {
      await apiPost("/api/settings/llm", llmConfig);
      setLlmSaved(true);
      log(
        "info",
        `LLM config saved: ${llmConfig.provider} / ${llmConfig.model}`,
      );
      setTimeout(() => setLlmSaved(false), 3000);
    } catch (e) {
      setLlmError(String(e));
      log("error", String(e));
    }
    setLlmSaving(false);
  }, [llmConfig, log]);

  const handleProviderChange = useCallback((provider: string) => {
    const p = LLM_PROVIDERS.find((x) => x.key === provider);
    localStorage.setItem("llm_provider", provider);
    setLlmConfig((prev) => ({
      ...prev,
      provider,
      endpoint: p?.defaultEndpoint || prev.endpoint,
    }));
  }, []);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Configuration"
        title="Settings"
        lead="LLM provider, depot paths, media fetch policy, and API keys."
      />

      <Card>
        <CardTitle>LLM Provider</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Select a local or cloud LLM for epistemic analysis and chat.
        </p>

        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="llm-provider-select"
              className="text-xs font-medium text-foreground"
            >
              Provider
            </label>
            <select
              data-testid="llm-provider-select"
              value={llmConfig.provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground outline-none focus:border-primary transition-colors"
            >
              <option value="" disabled>
                Select provider…
              </option>
              {LLM_PROVIDERS.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="llm-endpoint"
              className="text-xs font-medium text-foreground"
            >
              Endpoint URL
            </label>
            <Input
              id="llm-endpoint"
              value={llmConfig.endpoint}
              onChange={(e) =>
                setLlmConfig((prev) => ({ ...prev, endpoint: e.target.value }))
              }
              placeholder={
                LLM_PROVIDERS.find((p) => p.key === llmConfig.provider)
                  ?.defaultEndpoint || "https://api.openai.com/v1"
              }
              className="font-mono text-xs"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="llm-model-select"
              className="text-xs font-medium text-foreground"
            >
              Model
            </label>
            <select
              data-testid="llm-model-select"
              value={llmConfig.model}
              onChange={(e) => {
                setLlmConfig((prev) => ({ ...prev, model: e.target.value }));
                localStorage.setItem("llm_model", e.target.value);
              }}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground outline-none focus:border-primary transition-colors"
            >
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))
              ) : (
                <option value="" disabled>
                  No models detected — enter manually below
                </option>
              )}
            </select>
            <Input
              value={llmConfig.model}
              onChange={(e) => {
                setLlmConfig((prev) => ({ ...prev, model: e.target.value }));
                localStorage.setItem("llm_model", e.target.value);
              }}
              placeholder="llama3.2, gpt-4o, deepseek-chat, etc."
              className="font-mono text-xs mt-2"
            />
          </div>

          <div className="flex items-center gap-3">
            <Button type="button" onClick={saveLlm} disabled={llmSaving}>
              <Save className="h-3.5 w-3.5 mr-1" />
              {llmSaving ? "Saving..." : "Save LLM config"}
            </Button>
            {llmSaved && (
              <span className="flex items-center gap-1 text-xs text-green-500">
                <Check className="h-3.5 w-3.5" /> Saved
              </span>
            )}
            {llmError && (
              <span className="flex items-center gap-1 text-xs text-destructive">
                <X className="h-3.5 w-3.5" /> {llmError}
              </span>
            )}
          </div>
        </div>

        <div className="mt-4 space-y-2 text-xs text-muted-foreground">
          {PROVIDER_PROBES.map((probe) => (
            <div key={probe.name} className="flex items-center gap-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  providerStatus[probe.name] === "detected"
                    ? "bg-green-500"
                    : providerStatus[probe.name] === "probing"
                      ? "bg-yellow-500 animate-pulse"
                      : "bg-zinc-600"
                }`}
              />
              <span>{probe.label}</span>
              <span className="text-muted-foreground/60">:{probe.port}</span>
              {providerStatus[probe.name] === "detected" && (
                <span className="text-green-400">Detected</span>
              )}
              {providerStatus[probe.name] === "not_found" && (
                <span className="text-zinc-500">Not found</span>
              )}
              {providerStatus[probe.name] === "probing" && (
                <span className="text-yellow-400">Probing...</span>
              )}
            </div>
          ))}
          {noProviderDetected && (
            <p className="text-amber-400 text-xs mt-2">
              Install Ollama or LM Studio to enable AI features.
            </p>
          )}
        </div>

        {llm && (
          <div className="mt-3 p-3 rounded-lg bg-card/50 border border-border/50 space-y-1 text-xs text-muted-foreground">
            <p>
              Current env:{" "}
              <code className="text-primary">
                {llm.configured_sampling_url || "not set"}
              </code>
              {" / "}
              <code className="text-primary">
                {llm.configured_model || "llama3.2"}
              </code>
            </p>
            {llm.recommendation && (
              <p className="text-primary">{llm.recommendation}</p>
            )}
          </div>
        )}
      </Card>

      <Card id="ignore-botblocks">
        <CardTitle>Ignore bot blocks</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Many sites ship anti-crawl guards from automatic scaffolding—the owner
          may not even know. Default media traction uses{" "}
          <strong className="text-foreground">RSS metadata only</strong> (no
          direct article HTML). Enable this to optionally enrich RSS hits via{" "}
          <strong className="text-foreground">Jina Reader</strong> when
          publishers block normal bots. For hard gates Jina cannot pass, enable{" "}
          <strong className="text-foreground">Bright Hand</strong> (Bright Data
          Web Unlocker) — billed, requires API token + zone.
        </p>

        <label className="mt-4 flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-border accent-primary"
            checked={media?.media_ignore_botblocks ?? false}
            disabled={media === null || mediaSaving}
            onChange={() => void toggleIgnoreBotblocks()}
          />
          <span className="text-sm">
            <span className="font-medium text-foreground">
              Ignore bot blocks
            </span>
            <span className="block text-muted-foreground text-xs mt-1">
              {media?.media_ignore_botblocks
                ? `Active — ${media.strategy_when_enabled ?? "Jina enrichment on RSS hits"}`
                : `Off — ${media?.strategy_default ?? "aggregators + RSS metadata only"}`}
              {media?.source === "runtime_override"
                ? " · saved in runtime_settings.json"
                : null}
            </span>
          </span>
        </label>

        <label className="mt-3 ml-6 flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            className="mt-1 h-4 w-4 rounded border-border accent-primary"
            checked={media?.media_use_brighthand ?? false}
            disabled={
              media === null || mediaSaving || !media?.media_ignore_botblocks
            }
            onChange={() => void toggleBrighthand()}
          />
          <span className="text-sm">
            <span className="font-medium text-foreground">Bright Hand</span>
            <span className="block text-muted-foreground text-xs mt-1">
              {media?.media_use_brighthand
                ? media.brighthand_configured
                  ? `Active — zone ${media.brighthand_zone ?? "configured"}`
                  : "Enabled but missing BRIGHTDATA_API_TOKEN or ARXIV_MCP_BRIGHTDATA_ZONE"
                : "Off — Jina only (no billed unlocker)"}
            </span>
          </span>
        </label>

        <p className="text-xs text-muted-foreground mt-4 leading-relaxed">
          <Link
            to="/help#ignore-botblocks"
            className="text-primary underline underline-offset-2"
          >
            Legal context &amp; the scaffolding antipattern
          </Link>{" "}
          — why Hollabrunn minigolf never gets mentioned, and when opt-in fetch
          is reasonable. API:{" "}
          <code className="text-xs bg-background/60 border border-border/40 rounded px-1">
            GET /api/help/botblocks
          </code>
        </p>
      </Card>

      <Card id="publication-subscriptions">
        <CardTitle>Publication subscriptions</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          Licensed outlets (NYT, WSJ, FT, New Scientist web): set{" "}
          <code className="text-xs">USER</code>,{" "}
          <code className="text-xs">PASSWORD</code>,{" "}
          <code className="text-xs">VALID_TILL</code>, and subscriber{" "}
          <code className="text-xs">COOKIE</code> in{" "}
          <code className="text-xs">.env</code>.{" "}
          <strong className="text-foreground">Readly</strong> (thousands of
          magazines incl. New Scientist issues):{" "}
          <code className="text-xs">ARXIV_MCP_READLY_ENABLED=1</code>,{" "}
          <code className="text-xs">ARXIV_MCP_READLY_MCP_URL</code>,{" "}
          <code className="text-xs">ARXIV_MCP_READLY_VALID_TILL</code> +{" "}
          <code className="text-xs">READLY_AUTH_TOKEN</code> on readly-mcp.
          Expired subs fail loudly.
        </p>
        {publications?.alerts?.length ? (
          <ul className="mt-3 space-y-2 text-xs">
            {publications.alerts.map((a) => (
              <li
                key={a.code}
                className={
                  a.severity === "critical"
                    ? "text-destructive"
                    : a.severity === "warning"
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-muted-foreground"
                }
              >
                {a.message}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="text-muted-foreground border-b border-border/60">
                <th className="py-2 pr-3 font-medium">Publication</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 pr-3 font-medium">Valid till</th>
                <th className="py-2 font-medium">Cookie</th>
              </tr>
            </thead>
            <tbody>
              {(publications?.publications ?? []).map((row) => (
                <tr key={row.id} className="border-b border-border/30">
                  <td className="py-2 pr-3 text-foreground">{row.name}</td>
                  <td className="py-2 pr-3 font-mono">{row.status}</td>
                  <td className="py-2 pr-3 font-mono">
                    {row.valid_till ?? "—"}
                  </td>
                  <td className="py-2">{row.has_cookie ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground mt-4">
          <Link
            to="/help#publication-subscriptions"
            className="text-primary underline underline-offset-2"
          >
            Publication auth guide
          </Link>
          {" · "}
          <code className="bg-background/60 border border-border/40 rounded px-1">
            GET /api/help/publication_auth
          </code>
        </p>
      </Card>

      <Card>
        <CardTitle>Data directory</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 break-all font-mono">
          {stats?.data_dir ?? "…"}
        </p>
        <p className="text-xs text-muted-foreground mt-3">
          Papers: {stats?.papers ?? 0} · FTS chunks: {stats?.chunks ?? 0} ·
          Vectors:{" "}
          {String(
            (stats?.rag as { indexed_chunks?: number })?.indexed_chunks ?? 0,
          )}
        </p>
      </Card>

      <Card>
        <CardTitle>Semantic Scholar</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Optional{" "}
          <code className="text-primary">
            ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY
          </code>{" "}
          for higher-rate <code>find_connected_papers</code> calls.
        </p>
      </Card>

      <Card>
        <CardTitle>RAG embedding</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Fleet default:{" "}
          <code className="text-primary">BAAI/bge-small-en-v1.5</code> via
          FastEmbed. After model changes, run <code>reindex_depot_vectors</code>
          .
        </p>
      </Card>

      {features && (
        <Card>
          <CardTitle>Feature flags</CardTitle>
          <p className="text-sm text-muted-foreground mt-2">
            Runtime capability status from the backend.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {Object.entries(features).map(([key, val]) => (
              <div
                key={key}
                className="flex items-center justify-between rounded-lg border border-border/40 bg-card/30 px-3 py-2"
              >
                <span className="text-sm font-medium capitalize text-foreground">
                  {key.replace(/_/g, " ")}
                </span>
                {typeof val === "boolean" ? (
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${val ? "bg-green-500/10 text-green-400 border border-green-500/30" : "bg-zinc-500/10 text-zinc-400 border border-zinc-500/30"}`}
                  >
                    {val ? "on" : "off"}
                  </span>
                ) : (
                  <span className="text-xs font-mono text-muted-foreground">
                    {String(val)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
