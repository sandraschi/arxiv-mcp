import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiDelete, apiGet } from "@/api/client";
import { LlmOnboarding } from "@/components/LlmOnboarding";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  fetchModels,
  fetchProviders,
  installStatus,
  loadSelection,
  type ProviderInfo,
  saveLlmSettings,
  saveSelection,
  startInstall,
} from "@/lib/llm";
import { cn } from "@/lib/utils";

type Health = { status: string; service: string };

type GpuInfo = {
  index: number;
  name: string;
  vramMb: number;
};

async function fetchGpus(): Promise<GpuInfo[]> {
  try {
    const d = await apiGet<{ gpus?: GpuInfo[] }>("/api/llm/gpus");
    return d.gpus ?? [];
  } catch {
    return [];
  }
}

function currentTheme(): string {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("light")
    ? "light"
    : "dark";
}

export function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [probing, setProbing] = useState(true);
  const [selected, setSelected] = useState("ollama");
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [modelsSource, setModelsSource] = useState<string>("");
  const [endpoints, setEndpoints] = useState<Record<string, string>>({});
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [cardMsg, setCardMsg] = useState<Record<string, string>>({});
  const [installing, setInstalling] = useState(false);
  const [installMsg, setInstallMsg] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [gpus, setGpus] = useState<GpuInfo[]>([]);
  const [targetGpu, setTargetGpu] = useState("0");
  const [theme, setTheme] = useState(currentTheme);

  useEffect(() => {
    (async () => {
      try {
        const h = await apiGet<Health>("/api/health");
        setHealth(h);
      } catch {
        setHealth(null);
      }
      try {
        const pv = await fetchProviders();
        setProviders(pv.providers);
        const eps: Record<string, string> = {};
        for (const p of pv.providers) eps[p.id] = p.base_url;
        try {
          const s = await apiGet<{
            provider?: string;
            endpoint?: string;
            model?: string;
          }>("/api/settings/llm");
          if (s.provider) setSelected(s.provider);
          else {
            const prev = loadSelection();
            if (prev.provider) setSelected(prev.provider);
          }
          if (s.endpoint && s.provider) eps[s.provider] = s.endpoint;
          if (s.model) setModel(s.model);
        } catch {
          const prev = loadSelection();
          if (prev.provider) setSelected(prev.provider);
          if (prev.model) setModel(prev.model);
        }
        setEndpoints(eps);
      } catch {
        /* providers unavailable */
      } finally {
        setProbing(false);
      }
      const cards = await fetchGpus();
      setGpus(cards);
      if (cards.length > 1) {
        const saved =
          typeof localStorage !== "undefined"
            ? localStorage.getItem("llm_gpu")
            : null;
        const secondary = cards.find((g) => g.index > 0);
        setTargetGpu(saved ?? String(secondary?.index ?? cards[0].index));
      }
    })();
  }, []);

  const reloadModels = useCallback(async (id: string) => {
    try {
      const m = await fetchModels(id);
      setModels(m.models);
      setModelsSource(m.source);
      setModel((cur) =>
        cur && m.models.includes(cur) ? cur : (m.models[0] ?? ""),
      );
    } catch {
      setModels([]);
      setModelsSource("none");
    }
  }, []);

  useEffect(() => {
    if (!selected) return;
    void reloadModels(selected);
  }, [selected, reloadModels]);

  async function refreshProviders() {
    try {
      const pv = await fetchProviders();
      setProviders(pv.providers);
    } catch {
      /* ignore */
    }
  }

  async function chooseProvider(id: string) {
    setSelected(id);
    setSaveMsg(null);
  }

  async function save() {
    setSaveMsg(null);
    try {
      const key = keyInputs[selected]?.trim() || undefined;
      await saveLlmSettings({
        provider: selected,
        endpoint: endpoints[selected],
        model,
        api_key: key,
      });
      saveSelection(selected, model);
      setKeyInputs((k) => ({ ...k, [selected]: "" }));
      await refreshProviders();
      await reloadModels(selected);
      setSaveMsg("Saved.");
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : String(e));
    }
  }

  async function saveKey(id: string) {
    const key = keyInputs[id]?.trim();
    if (!key) return;
    setCardMsg((m) => ({ ...m, [id]: "Saving…" }));
    try {
      await saveLlmSettings({
        provider: id,
        model: models[0] ?? "",
        api_key: key,
      });
      setKeyInputs((k) => ({ ...k, [id]: "" }));
      await refreshProviders();
      if (id === selected) await reloadModels(id);
      setCardMsg((m) => ({ ...m, [id]: "Key saved." }));
    } catch (e) {
      setCardMsg((m) => ({
        ...m,
        [id]: e instanceof Error ? e.message : String(e),
      }));
    }
  }

  async function clearKey(id: string) {
    setCardMsg((m) => ({ ...m, [id]: "Clearing…" }));
    try {
      await apiDelete(
        `/api/settings/llm/key?provider=${encodeURIComponent(id)}`,
      );
      await refreshProviders();
      setCardMsg((m) => ({ ...m, [id]: "Key cleared." }));
    } catch (e) {
      setCardMsg((m) => ({
        ...m,
        [id]: e instanceof Error ? e.message : String(e),
      }));
    }
  }

  async function installOllama() {
    setInstalling(true);
    setInstallMsg("Starting winget install…");
    try {
      await startInstall("ollama");
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 5000));
        const st = await installStatus("ollama");
        if (st.state === "done") {
          setInstallMsg("Installed. Re-probing…");
          await refreshProviders();
          await reloadModels("ollama");
          setInstallMsg(
            "Ollama installed and detected. Pull a model: ollama pull qwen3:32b",
          );
          break;
        }
        if (st.state === "error") {
          setInstallMsg(
            `Install failed: ${(st.output ?? "").slice(-300) || "see backend logs"}`,
          );
          break;
        }
        setInstallMsg(`Installing… (${i * 5 + 5}s)`);
      }
    } catch (e) {
      setInstallMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setInstalling(false);
    }
  }

  async function testProvider(id: string) {
    setCardMsg((m) => ({ ...m, [id]: "Testing…" }));
    try {
      const m = await fetchModels(id);
      setCardMsg((m2) => ({
        ...m2,
        [id]: m.models.length
          ? `${m.models.length} models (${m.source})`
          : `No models (${m.source})`,
      }));
    } catch (e) {
      setCardMsg((m) => ({
        ...m,
        [id]: e instanceof Error ? e.message : String(e),
      }));
    }
  }

  const localProviders = providers.filter((p) => p.kind === "local");
  const cloudProviders = providers.filter((p) => p.kind === "cloud");

  function statusDot(p: ProviderInfo) {
    if (p.kind === "local") {
      if (probing)
        return (
          <span className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse" />
        );
      return p.detected ? (
        <span className="h-2 w-2 rounded-full bg-green-500" />
      ) : (
        <span className="h-2 w-2 rounded-full bg-muted-foreground" />
      );
    }
    return p.configured ? (
      <span className="h-2 w-2 rounded-full bg-green-500" />
    ) : (
      <span className="h-2 w-2 rounded-full bg-amber-500" />
    );
  }

  function statusText(p: ProviderInfo): string {
    if (p.kind === "local") {
      if (probing) return "Probing…";
      return p.detected
        ? `Detected · ${p.models?.length ?? 0} models`
        : "Not found";
    }
    return p.configured ? "Key configured" : "Missing key";
  }

  return (
    <div className="space-y-4" data-testid="settings-page">
      <LlmOnboarding mode="full" />

      <Card className="p-4">
        <p className="text-xs text-muted-foreground">Backend</p>
        <p className="text-sm mt-1 flex items-center gap-2">
          <span
            data-testid="backend-status-dot"
            className={cn(
              "h-2 w-2 rounded-full",
              health ? "bg-green-500" : "bg-red-500",
            )}
          />
          <span data-testid="backend-status-text">
            {health ? `${health.service} · ${health.status}` : "Offline"}
          </span>
        </p>
      </Card>

      <Card className="p-4">
        <p className="text-xs text-muted-foreground">Theme</p>
        <div className="mt-2">
          <Button
            size="sm"
            variant="secondary"
            data-testid="theme-toggle"
            onClick={() => {
              const next = theme === "dark" ? "light" : "dark";
              document.documentElement.classList.toggle(
                "light",
                next === "light",
              );
              setTheme(next);
            }}
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
        </div>
      </Card>

      <Card className="p-4 space-y-3">
        <p className="text-xs text-muted-foreground">
          Active LLM (used by Chat)
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <label
            className="text-xs text-muted-foreground"
            htmlFor="llm-provider"
          >
            Provider
          </label>
          <select
            id="llm-provider"
            data-testid="llm-provider-select"
            value={selected}
            onChange={(e) => void chooseProvider(e.target.value)}
            className="rounded border border-border bg-background px-2 py-1 text-sm"
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label} ({p.kind})
              </option>
            ))}
          </select>
          <label className="text-xs text-muted-foreground" htmlFor="llm-model">
            Model
          </label>
          {models.length > 0 ? (
            <select
              id="llm-model"
              data-testid="llm-model-select"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="rounded border border-border bg-background px-2 py-1 text-sm font-mono"
            >
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="llm-model"
              data-testid="llm-model-select"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="model id"
              aria-label="Model name"
              className="rounded border border-border bg-background px-2 py-1 text-sm font-mono w-40"
            />
          )}
          {modelsSource && (
            <span className="text-[10px] text-muted-foreground">
              source: {modelsSource}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label
            className="text-xs text-muted-foreground"
            htmlFor="llm-endpoint"
          >
            Endpoint
          </label>
          <input
            id="llm-endpoint"
            data-testid="llm-endpoint"
            value={endpoints[selected] ?? ""}
            onChange={(e) =>
              setEndpoints((eps) => ({ ...eps, [selected]: e.target.value }))
            }
            className="rounded border border-border bg-background px-2 py-1 text-sm font-mono w-64"
          />
          <Button size="sm" data-testid="settings-llm-save" onClick={save}>
            Save
          </Button>
          {saveMsg && (
            <span className="text-xs text-muted-foreground">{saveMsg}</span>
          )}
        </div>
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        {localProviders.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground font-medium">
              Local engines (free)
            </p>
            {localProviders.map((p) => (
              <Card
                key={p.id}
                data-testid={`llm-provider-card-${p.id}`}
                className="p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  {statusDot(p)}
                  <span className="text-sm font-semibold">{p.label}</span>
                  <span className="text-[10px] rounded bg-muted/50 px-1.5 py-0.5 text-muted-foreground">
                    local · free
                  </span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {statusText(p)}
                  </span>
                </div>
                {p.id === "ollama" && !p.detected && !probing && (
                  <div className="text-xs text-muted-foreground rounded border border-border/40 px-2 py-1.5 space-y-2">
                    <p>
                      Not running. Manual:{" "}
                      <code className="font-mono">
                        winget install -e --id Ollama.Ollama
                      </code>{" "}
                      then{" "}
                      <code className="font-mono">ollama pull qwen3:32b</code> —
                      or see the{" "}
                      <Link to="/skills" className="underline">
                        llm-guide skill
                      </Link>
                      .
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        data-testid="llm-install-ollama"
                        disabled={installing}
                        onClick={() => void installOllama()}
                      >
                        {installing ? "Installing…" : "Install Ollama now"}
                      </Button>
                      {installMsg && <span>{installMsg}</span>}
                    </div>
                  </div>
                )}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    data-testid={`llm-test-${p.id}`}
                    onClick={() => void testProvider(p.id)}
                  >
                    Test
                  </Button>
                  {cardMsg[p.id] && (
                    <span className="text-xs text-muted-foreground self-center">
                      {cardMsg[p.id]}
                    </span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        {cloudProviders.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground font-medium">
              Cloud (API key)
            </p>
            {cloudProviders.map((p) => (
              <Card
                key={p.id}
                data-testid={`llm-provider-card-${p.id}`}
                className="p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  {statusDot(p)}
                  <span className="text-sm font-semibold">{p.label}</span>
                  <span className="text-[10px] rounded bg-muted/50 px-1.5 py-0.5 text-muted-foreground">
                    cloud · paid
                  </span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {statusText(p)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type={showKeys[p.id] ? "text" : "password"}
                    value={keyInputs[p.id] ?? ""}
                    onChange={(e) =>
                      setKeyInputs((k) => ({ ...k, [p.id]: e.target.value }))
                    }
                    placeholder={
                      p.configured
                        ? "•••••••• configured"
                        : `Paste ${p.key_env}`
                    }
                    aria-label={`${p.label} API key`}
                    data-testid={`llm-key-${p.id}`}
                    className="flex-1 min-w-40 rounded border border-border bg-background px-2 py-1 text-xs font-mono"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setShowKeys((s) => ({ ...s, [p.id]: !s[p.id] }))
                    }
                  >
                    {showKeys[p.id] ? "Hide" : "Show"}
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!keyInputs[p.id]?.trim()}
                    onClick={() => void saveKey(p.id)}
                  >
                    Save key
                  </Button>
                  {p.configured && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void clearKey(p.id)}
                    >
                      Clear
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    data-testid={`llm-test-${p.id}`}
                    onClick={() => void testProvider(p.id)}
                  >
                    Test
                  </Button>
                  {cardMsg[p.id] && (
                    <span className="text-xs text-muted-foreground self-center">
                      {cardMsg[p.id]}
                    </span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {gpus.length > 1 && (
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">
            Target GPU (local models avoid GPU 0)
          </p>
          <select
            data-testid="llm-gpu-select"
            value={targetGpu}
            onChange={(e) => {
              setTargetGpu(e.target.value);
              try {
                localStorage.setItem("llm_gpu", e.target.value);
              } catch {
                /* ignore */
              }
            }}
            className="mt-2 rounded border border-border bg-background px-2 py-1 text-sm"
          >
            {gpus.map((g) => (
              <option key={g.index} value={String(g.index)}>
                GPU {g.index} - {g.name} ({Math.round(g.vramMb / 1024)} GB)
              </option>
            ))}
          </select>
        </Card>
      )}
    </div>
  );
}
