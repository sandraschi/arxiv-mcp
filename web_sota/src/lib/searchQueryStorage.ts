/** Browser-only persistence for arXiv keyword queries (search page). */

const KEY_HISTORY = "arxiv-mcp-search-query-history";
const KEY_FAVORITES = "arxiv-mcp-search-query-favorites";

export type HistoryEntry = { id: string; q: string; at: number };
export type FavoriteEntry = { id: string; q: string; label: string; topic: string; at: number };

/** Topic tag for saved favorites (user-facing categories). */
export const FAVORITE_TOPICS = [
  "General",
  "NLP",
  "Vision & graphics",
  "Machine learning",
  "Robotics",
  "Science & math",
  "Other",
] as const;

export type FavoriteTopic = (typeof FAVORITE_TOPICS)[number];

export type SuggestedQuery = { topic: string; label: string; q: string };

/** Curated starters (~12); `topic` groups the dropdown only. */
export const SUGGESTED_QUERIES: SuggestedQuery[] = [
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
