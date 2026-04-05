/** Browser-only persistence for arXiv keyword queries (search page). */

const KEY_HISTORY = "arxiv-mcp-search-query-history";
const KEY_FAVORITES = "arxiv-mcp-search-query-favorites";
const KEY_SWEEP_TEMPLATES = "arxiv-mcp-search-sweep-templates";
const KEY_DEFAULT_SWEEP_TEMPLATE_ID = "arxiv-mcp-search-default-sweep-template-id";

export type HistoryEntry = { id: string; q: string; at: number };
export type FavoriteEntry = { id: string; q: string; label: string; topic: string; at: number };

/** Topic tag for saved favorites (user-facing categories). */
export const FAVORITE_TOPICS = [
  "General",
  "AI safety / SI",
  "NLP",
  "Vision & graphics",
  "Machine learning",
  "Robotics",
  "Science & math",
  "Other",
] as const;

export type FavoriteTopic = (typeof FAVORITE_TOPICS)[number];

export type SuggestedQuery = { topic: string; label: string; q: string };
export type SweepTemplate = {
  id: string;
  label: string;
  query: string;
  primaryCategory: string;
  extraCategories: string;
  recentCategory: string;
  recentHours: string;
  sortBy: "submitted" | "relevance" | "updated";
  createdAt: number;
};

/** Curated starters (~12); `topic` groups the dropdown only. */
export const SUGGESTED_QUERIES: SuggestedQuery[] = [
  { topic: "AI safety / SI", label: "AI control and oversight", q: "AI control oversight monitoring" },
  { topic: "AI safety / SI", label: "Scalable oversight and evals", q: "scalable oversight evaluation llm" },
  { topic: "AI safety / SI", label: "Interpretability and mechanistic", q: "mechanistic interpretability transformer" },
  { topic: "AI safety / SI", label: "Alignment and objective robustness", q: "alignment objective robustness reward hacking" },
  { topic: "AI safety / SI", label: "Agent safety and tool use", q: "agent safety tool use evaluation" },
  { topic: "AI safety / SI", label: "Governance and forecasting", q: "AI governance forecasting compute trends" },
  { topic: "Machine learning", label: "Diffusion & generative models", q: "diffusion generative model" },
  { topic: "Machine learning", label: "Transformers & attention", q: "all:transformer attention" },
  { topic: "Machine learning", label: "Graph neural networks", q: "graph neural network" },
  { topic: "NLP", label: "Large language models", q: "large language model" },
  { topic: "NLP", label: "Instruction tuning & alignment", q: "instruction tuning alignment" },
  { topic: "Vision & graphics", label: "3D vision & NeRF", q: "NeRF 3D reconstruction" },
  { topic: "Vision & graphics", label: "Vision–language models", q: "vision language model CLIP" },
  { topic: "Robotics", label: "Manipulation & control", q: "robot manipulation reinforcement" },
  { topic: "Science & math", label: "Molecular & protein ML", q: "protein structure prediction deep learning" },
  { topic: "General", label: "Broad CS.AI sweep", q: "cat:cs.AI" },
  { topic: "General", label: "Title search example", q: "ti:quantum error correction" },
  { topic: "General", label: "Everything recent-ish (broad)", q: "all" },
];

function isHistoryEntry(x: unknown): x is HistoryEntry {
  if (typeof x !== "object" || x === null) return false;
  const o = x as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.q === "string" && typeof o.at === "number";
}

function isFavoriteEntry(x: unknown): x is FavoriteEntry {
  if (typeof x !== "object" || x === null) return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.q === "string" &&
    typeof o.label === "string" &&
    typeof o.topic === "string" &&
    typeof o.at === "number"
  );
}

function isSweepTemplate(x: unknown): x is SweepTemplate {
  if (typeof x !== "object" || x === null) return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.label === "string" &&
    typeof o.query === "string" &&
    typeof o.primaryCategory === "string" &&
    typeof o.extraCategories === "string" &&
    typeof o.recentCategory === "string" &&
    typeof o.recentHours === "string" &&
    typeof o.sortBy === "string" &&
    typeof o.createdAt === "number"
  );
}

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY_HISTORY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isHistoryEntry).slice(0, 60);
  } catch {
    return [];
  }
}

export function saveHistory(entries: HistoryEntry[]): void {
  localStorage.setItem(KEY_HISTORY, JSON.stringify(entries.slice(0, 60)));
}

/** Prepend; dedupe same query (case-insensitive); cap length. */
export function addHistoryEntry(q: string): HistoryEntry[] {
  const trimmed = q.trim();
  if (trimmed.length < 2) return loadHistory();
  const prev = loadHistory().filter((e) => e.q.toLowerCase() !== trimmed.toLowerCase());
  const next: HistoryEntry = {
    id: `h-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    q: trimmed,
    at: Date.now(),
  };
  const merged = [next, ...prev].slice(0, 40);
  saveHistory(merged);
  return merged;
}

export function removeHistoryEntry(id: string): HistoryEntry[] {
  const next = loadHistory().filter((e) => e.id !== id);
  saveHistory(next);
  return next;
}

export function clearHistory(): void {
  localStorage.removeItem(KEY_HISTORY);
}

export function loadFavorites(): FavoriteEntry[] {
  try {
    const raw = localStorage.getItem(KEY_FAVORITES);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isFavoriteEntry);
  } catch {
    return [];
  }
}

export function saveFavorites(entries: FavoriteEntry[]): void {
  localStorage.setItem(KEY_FAVORITES, JSON.stringify(entries));
}

export function addFavorite(q: string, topic: string, label: string): FavoriteEntry[] {
  const trimmed = q.trim();
  if (trimmed.length < 2) return loadFavorites();
  const prev = loadFavorites();
  if (prev.some((f) => f.q.toLowerCase() === trimmed.toLowerCase())) return prev;
  const safeTopic = FAVORITE_TOPICS.includes(topic as FavoriteTopic) ? topic : "Other";
  const next: FavoriteEntry = {
    id: `f-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    q: trimmed,
    label: label.trim() || trimmed.slice(0, 48) + (trimmed.length > 48 ? "…" : ""),
    topic: safeTopic,
    at: Date.now(),
  };
  const merged = [next, ...prev];
  saveFavorites(merged);
  return merged;
}

export function removeFavorite(id: string): FavoriteEntry[] {
  const next = loadFavorites().filter((f) => f.id !== id);
  saveFavorites(next);
  return next;
}

export function updateFavoriteTopic(id: string, topic: string): FavoriteEntry[] {
  const safeTopic = FAVORITE_TOPICS.includes(topic as FavoriteTopic) ? topic : "Other";
  const next = loadFavorites().map((f) => (f.id === id ? { ...f, topic: safeTopic } : f));
  saveFavorites(next);
  return next;
}

export function loadSweepTemplates(): SweepTemplate[] {
  try {
    const raw = localStorage.getItem(KEY_SWEEP_TEMPLATES);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSweepTemplate);
  } catch {
    return [];
  }
}

export function saveSweepTemplates(entries: SweepTemplate[]): void {
  localStorage.setItem(KEY_SWEEP_TEMPLATES, JSON.stringify(entries));
}

export function addSweepTemplate(input: Omit<SweepTemplate, "id" | "createdAt">): SweepTemplate[] {
  const label = input.label.trim();
  const query = input.query.trim();
  if (!label || !query) return loadSweepTemplates();
  const next: SweepTemplate = {
    ...input,
    label,
    query,
    id: `sw-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt: Date.now(),
  };
  const merged = [next, ...loadSweepTemplates()];
  saveSweepTemplates(merged);
  return merged;
}

export function removeSweepTemplate(id: string): SweepTemplate[] {
  const next = loadSweepTemplates().filter((s) => s.id !== id);
  saveSweepTemplates(next);
  if (loadDefaultSweepTemplateId() === id) {
    clearDefaultSweepTemplateId();
  }
  return next;
}

export function loadDefaultSweepTemplateId(): string | null {
  try {
    return localStorage.getItem(KEY_DEFAULT_SWEEP_TEMPLATE_ID);
  } catch {
    return null;
  }
}

export function setDefaultSweepTemplateId(id: string): void {
  localStorage.setItem(KEY_DEFAULT_SWEEP_TEMPLATE_ID, id);
}

export function clearDefaultSweepTemplateId(): void {
  localStorage.removeItem(KEY_DEFAULT_SWEEP_TEMPLATE_ID);
}
