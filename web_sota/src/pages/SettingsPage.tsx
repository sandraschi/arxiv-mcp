import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { LlmOnboarding } from "@/components/LlmOnboarding";
import { LlmProviderCards } from "@/components/LlmProviderCards";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  fetchModels,
  fetchProviders,
  loadSelection,
  type ProviderInfo,
  saveLlmSettings,
  saveSelection,
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
      await saveLlmSettings({
        provider: selected,
        endpoint: endpoints[selected],
        model,
      });
      saveSelection(selected, model);
      await refreshProviders();
      await reloadModels(selected);
      setSaveMsg("Saved.");
    } catch (e) {
      setSaveMsg(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleCardsChanged(id: string) {
    await refreshProviders();
    await reloadModels(id);
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

      <LlmProviderCards
        providers={providers}
        probing={probing}
        selected={selected}
        onChanged={(id) => handleCardsChanged(id)}
      />

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
