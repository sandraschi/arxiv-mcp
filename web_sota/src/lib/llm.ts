import { API_BASE, apiGet, apiPost } from "@/api/client";

export type ProviderKind = "local" | "cloud";
export type ModelSource = "live" | "curated" | "none";

export interface ProviderInfo {
  id: string;
  label: string;
  kind: ProviderKind;
  base_url: string;
  needs_key: boolean;
  key_env: string | null;
  configured: boolean;
  detected?: boolean;
  models?: string[];
}

export interface ModelsResponse {
  provider: string;
  models: string[];
  source: ModelSource;
}

export interface OnboardingState {
  locals: Array<{ id: string; label: string; port: number | null }>;
  clouds_configured: string[];
  recommendation: { path: string; reason: string };
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

const PROVIDER_KEY = "llm_provider";
const MODEL_KEY = "llm_model";
const ONBOARDED_KEY = "llm_onboarded";

function storageGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* quota */
  }
}

export function loadSelection(): { provider: string; model: string } {
  return {
    provider: storageGet(PROVIDER_KEY) || "ollama",
    model: storageGet(MODEL_KEY) || "",
  };
}

export function saveSelection(provider: string, model: string) {
  storageSet(PROVIDER_KEY, provider);
  storageSet(MODEL_KEY, model);
}

export function isOnboarded(): boolean {
  return storageGet(ONBOARDED_KEY) === "1";
}

export function markOnboarded() {
  storageSet(ONBOARDED_KEY, "1");
}

export function fetchProviders(): Promise<{ providers: ProviderInfo[] }> {
  return apiGet<{ providers: ProviderInfo[] }>("/api/llm/providers");
}

export function fetchModels(provider: string): Promise<ModelsResponse> {
  return apiGet<ModelsResponse>(
    `/api/llm/models?provider=${encodeURIComponent(provider)}`,
  );
}

export function fetchOnboarding(): Promise<OnboardingState> {
  return apiGet<OnboardingState>("/api/llm/onboarding");
}

export function saveLlmSettings(body: {
  provider: string;
  endpoint?: string;
  model: string;
  api_key?: string;
}): Promise<{ success: boolean; key_saved?: boolean }> {
  return apiPost("/api/settings/llm", body);
}

export function startInstall(
  engine: string,
): Promise<{ engine: string; started: boolean; reason?: string }> {
  return apiPost("/api/llm/install", { engine });
}

export function installStatus(
  engine: string,
): Promise<{ engine: string; state: string; output?: string }> {
  return apiGet(`/api/llm/install/status?engine=${encodeURIComponent(engine)}`);
}

export async function chatComplete(
  provider: string,
  model: string,
  messages: ChatMessage[],
): Promise<string> {
  const d = await apiPost<{ content: string }>("/api/llm/chat", {
    provider,
    model,
    messages,
  });
  return d.content;
}

/** Stream assistant tokens via SSE; calls onToken per delta. Falls back to non-stream. */
export async function streamChat(
  provider: string,
  model: string,
  messages: ChatMessage[],
  onToken: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  let r: Response;
  try {
    r = await fetch(`${API_BASE}/api/llm/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, model, messages }),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return;
    throw e;
  }
  if (!r.ok || !r.body) {
    const text = await chatComplete(provider, model, messages);
    onToken(text);
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]" || payload === "") continue;
      try {
        const chunk = JSON.parse(payload) as {
          choices?: Array<{ delta?: { content?: string } }>;
        };
        const text = chunk.choices?.[0]?.delta?.content ?? "";
        if (text) onToken(text);
      } catch {
        /* keep-alive or partial frame */
      }
    }
  }
}
