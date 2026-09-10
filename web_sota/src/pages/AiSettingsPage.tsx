import { useCallback, useEffect, useState } from "react";
import { ActiveLlmCard } from "@/components/ActiveLlmCard";
import { LlmOnboarding } from "@/components/LlmOnboarding";
import { LlmProviderCards } from "@/components/LlmProviderCards";
import {
  fetchLlmSettings,
  fetchProviders,
  loadSelection,
  type ProviderInfo,
} from "@/lib/llm";

export function AiSettingsPage() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [probing, setProbing] = useState(true);
  const [selected, setSelected] = useState("ollama");

  const refreshProviders = useCallback(async () => {
    try {
      const pv = await fetchProviders();
      setProviders(pv.providers);
    } catch {
      /* keep previous list */
    }
  }, []);

  useEffect(() => {
    (async () => {
      await refreshProviders();
      const prev = loadSelection();
      if (prev.provider) setSelected(prev.provider);
      try {
        const s = await fetchLlmSettings();
        if (s.provider) setSelected(s.provider);
      } catch {
        /* backend truth unavailable: local mirror stands */
      }
      setProbing(false);
    })();
  }, [refreshProviders]);

  async function handleCardsChanged() {
    await refreshProviders();
  }

  return (
    <div className="space-y-4" data-testid="ai-settings-page">
      <LlmOnboarding mode="full" />
      <ActiveLlmCard />
      <LlmProviderCards
        providers={providers}
        probing={probing}
        selected={selected}
        onChanged={handleCardsChanged}
      />
    </div>
  );
}
