import { Check, Save, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPatch, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

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

export function SettingsPage() {
  const { log } = useLogger();

  const [stats, setStats] = useState<Stats | null>(null);
  const [llm, setLlm] = useState<LlmDiscover | null>(null);
  const [llmConfig, setLlmConfig] = useState<LlmConfig>({
    provider: "ollama",
    endpoint: "http://localhost:11434",
    model: "llama3.2",
  });
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmSaved, setLlmSaved] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [media, setMedia] = useState<MediaSettings | null>(null);
  const [mediaSaving, setMediaSaving] = useState(false);
  const [publications, setPublications] = useState<PublicationsResponse | null>(
    null,
  );

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
      } catch {
        /* ignore */
      }
    })();
    (async () => {
      try {
        const cfg = await apiGet<LlmConfig>("/api/settings/llm");
        if (cfg && cfg.provider) setLlmConfig(cfg);
      } catch {
        /* ignore */
      }
    })();
    (async () => {
      try {
        setMedia(await apiGet<MediaSettings>("/api/settings/media"));
      } catch {
        /* ignore */
      }
    })();
    (async () => {
      try {
        setPublications(
          await apiGet<PublicationsResponse>("/api/settings/publications"),
        );
      } catch {
        /* ignore */
      }
    })();
  }, [log]);

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
          Select the local or cloud LLM to use for epistemic analysis, semantic
          enrichment, and chat. The provider and model are passed to the server
          via <code className="text-xs">ARXIV_MCP_SAMPLING_BASE_URL</code> and{" "}
          <code className="text-xs">ARXIV_MCP_SAMPLING_MODEL</code>.
        </p>

        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            {LLM_PROVIDERS.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => handleProviderChange(p.key)}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm font-medium border transition-colors",
                  llmConfig.provider === p.key
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:border-primary/50",
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-foreground">
              Endpoint URL
            </label>
            <Input
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
            <label className="text-xs font-medium text-foreground">Model</label>
            <Input
              value={llmConfig.model}
              onChange={(e) =>
                setLlmConfig((prev) => ({ ...prev, model: e.target.value }))
              }
              placeholder="llama3.2, gpt-4o, deepseek-chat, etc."
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

        {llm && (
          <div className="mt-4 p-3 rounded-lg bg-card/50 border border-border/50 space-y-1 text-xs text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">Auto-detect: </span>
              {llm.ollama_detected
                ? "Ollama reachable on :11434"
                : "Ollama not detected"}
              {llm.probes
                ?.filter((p) => p.status && p.status < 500)
                .map((p) => (
                  <span key={p.kind}> · {p.kind} up</span>
                ))}
            </p>
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
    </div>
  );
}
