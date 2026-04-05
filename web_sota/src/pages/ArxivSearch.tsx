import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Star, Trash2 } from "lucide-react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";
import {
  SUGGESTED_QUERIES,
  FAVORITE_TOPICS,
  addFavorite,
  addHistoryEntry,
  addSweepTemplate,
  clearDefaultSweepTemplateId,
  clearHistory,
  loadDefaultSweepTemplateId,
  loadFavorites,
  loadHistory,
  loadSweepTemplates,
  removeFavorite,
  removeHistoryEntry,
  removeSweepTemplate,
  saveSweepTemplates,
  setDefaultSweepTemplateId,
  updateFavoriteTopic,
  type FavoriteEntry,
  type HistoryEntry,
  type SweepTemplate,
} from "@/lib/searchQueryStorage";

type Paper = {
  paper_id: string;
  title: string;
  summary: string;
  authors: string[];
  categories: string[];
  published: string | null;
  html_url: string | null;
  pdf_url: string | null;
};

type CategoryRow = { code: string; name: string; group: string };

function PaperHit({ p }: { p: Paper }) {
  return (
    <li className="border-b border-border/40 pb-4 last:border-0">
      <div className="font-medium">{p.title}</div>
      <div className="text-xs text-muted-foreground mt-1">
        {p.paper_id} · {p.categories?.join(", ")}
      </div>
      <p className="text-sm text-muted-foreground mt-2 line-clamp-3">{p.summary}</p>
      <div className="flex gap-3 mt-2 text-xs">
        {p.html_url && (
          <a className="text-primary hover:underline" href={p.html_url} target="_blank" rel="noreferrer">
            HTML
          </a>
        )}
        {p.pdf_url && (
          <a className="text-primary hover:underline" href={p.pdf_url} target="_blank" rel="noreferrer">
            PDF
          </a>
        )}
      </div>
    </li>
  );
}

const selectClass =
  "flex h-10 w-full rounded-md border border-input bg-background/60 px-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

const HOURS_OPTIONS: { value: string; label: string }[] = [
  { value: "24", label: "Last 24 hours" },
  { value: "48", label: "Last 48 hours" },
  { value: "72", label: "Last 3 days (72 h)" },
  { value: "168", label: "Last week (168 h)" },
];
const SI_DAILY_SWEEP_QUERY = "alignment objective robustness reward hacking";
const SI_DAILY_SWEEP_CATEGORY = "cs.AI";
const SI_DAILY_SWEEP_HOURS = "24";

function groupSuggestedByTopic() {
  const m = new Map<string, typeof SUGGESTED_QUERIES>();
  for (const s of SUGGESTED_QUERIES) {
    if (!m.has(s.topic)) m.set(s.topic, []);
    m.get(s.topic)!.push(s);
  }
  return [...m.entries()];
}

function groupFavoritesByTopic(favs: FavoriteEntry[]) {
  const m = new Map<string, FavoriteEntry[]>();
  for (const f of favs) {
    const t = f.topic || "Other";
    if (!m.has(t)) m.set(t, []);
    m.get(t)!.push(f);
  }
  return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

export function ArxivSearch() {
  const { log } = useLogger();
  const [catalog, setCatalog] = useState<CategoryRow[]>([]);
  const [q, setQ] = useState("all");
  const [filterCategory, setFilterCategory] = useState("");
  const [extraCategories, setExtraCategories] = useState("");
  const [sortBy, setSortBy] = useState("submitted");
  const [loading, setLoading] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [recentCategory, setRecentCategory] = useState("cs.LG");
  const [recentHours, setRecentHours] = useState("72");
  const [latest, setLatest] = useState<Paper[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchedKeyword, setSearchedKeyword] = useState(false);

  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory());
  const [favorites, setFavorites] = useState<FavoriteEntry[]>(() => loadFavorites());
  const [pickerKey, setPickerKey] = useState(0);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveLabel, setSaveLabel] = useState("");
  const [saveTopic, setSaveTopic] = useState<string>(FAVORITE_TOPICS[0]);
  const [sweeps, setSweeps] = useState<SweepTemplate[]>(() => loadSweepTemplates());
  const [defaultSweepId, setDefaultSweepId] = useState<string | null>(() => loadDefaultSweepTemplateId());
  const [newSweepLabel, setNewSweepLabel] = useState("");
  const [editingSweepId, setEditingSweepId] = useState<string | null>(null);
  const [editingSweepLabel, setEditingSweepLabel] = useState("");
  const importRef = useRef<HTMLInputElement | null>(null);

  const suggestedGroups = useMemo(() => groupSuggestedByTopic(), []);
  const favoriteGroups = useMemo(() => groupFavoritesByTopic(favorites), [favorites]);

  const refreshStorage = useCallback(() => {
    setHistory(loadHistory());
    setFavorites(loadFavorites());
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiGet<{ categories: CategoryRow[] }>("/api/categories");
        if (!cancelled) setCatalog(data.categories);
      } catch (e) {
        log("error", String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [log]);

  const grouped = useMemo(() => {
    const m = new Map<string, CategoryRow[]>();
    for (const c of catalog) {
      const g = c.group;
      if (!m.has(g)) m.set(g, []);
      m.get(g)!.push(c);
    }
    return [...m.entries()];
  }, [catalog]);

  function categoriesParam(): string | undefined {
    const parts: string[] = [];
    if (filterCategory.trim()) parts.push(filterCategory.trim());
    for (const x of extraCategories.split(",")) {
      const t = x.trim();
      if (t) parts.push(t);
    }
    const uniq = [...new Set(parts)];
    if (!uniq.length) return undefined;
    return uniq.join(",");
  }

  function applyPickerValue(raw: string) {
    if (!raw) return;
    if (raw.startsWith("s:")) {
      const i = Number.parseInt(raw.slice(2), 10);
      if (Number.isFinite(i) && SUGGESTED_QUERIES[i]) setQ(SUGGESTED_QUERIES[i].q);
      return;
    }
    if (raw.startsWith("f:")) {
      const id = raw.slice(2);
      const f = favorites.find((x) => x.id === id);
      if (f) setQ(f.q);
      return;
    }
    if (raw.startsWith("h:")) {
      const id = raw.slice(2);
      const h = history.find((x) => x.id === id);
      if (h) setQ(h.q);
    }
  }

  async function runSearch() {
    setSearchError(null);
    setLoading(true);
    try {
      const params = new URLSearchParams({ q, limit: "15", sort_by: sortBy });
      const cats = categoriesParam();
      if (cats) params.set("categories", cats);
      const data = await apiGet<{ papers?: Paper[] }>(`/api/search?${params}`);
      const list = Array.isArray(data.papers) ? data.papers : [];
      setPapers(list);
      setSearchedKeyword(true);
      log("info", `arXiv search: ${list.length} results`);
      try {
        setHistory(addHistoryEntry(q));
      } catch (he) {
        log("error", `History not saved: ${String(he)}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setSearchError(msg);
      setPapers([]);
      setSearchedKeyword(true);
      log("error", msg);
    } finally {
      setLoading(false);
    }
  }

  function handleToggleFavorite() {
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    const existing = favorites.find((x) => x.q.toLowerCase() === trimmed.toLowerCase());
    if (existing) {
      setFavorites(removeFavorite(existing.id));
      log("info", "Removed saved query");
      setSaveOpen(false);
      return;
    }
    setSaveOpen(true);
    setSaveLabel("");
    setSaveTopic(FAVORITE_TOPICS[0]);
  }

  function confirmSaveFavorite() {
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    setFavorites(addFavorite(trimmed, saveTopic, saveLabel));
    setSaveOpen(false);
    log("info", "Saved query to favorites");
  }

  async function runLatest() {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        category: recentCategory,
        limit: "20",
        hours: recentHours,
      });
      const data = await apiGet<{ papers: Paper[] }>(`/api/category/latest?${params}`);
      setLatest(data.papers);
      log("info", `Recent in ${recentCategory} (${recentHours}h): ${data.papers.length} papers`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runDailySISweep() {
    const byId = defaultSweepId ? sweeps.find((s) => s.id === defaultSweepId) : null;
    if (byId) {
      await runSweepTemplate(byId);
      return;
    }
    await runSweepTemplate({
      id: "builtin-si",
      label: "SI daily sweep",
      query: SI_DAILY_SWEEP_QUERY,
      primaryCategory: SI_DAILY_SWEEP_CATEGORY,
      extraCategories: "cs.LG",
      recentCategory: SI_DAILY_SWEEP_CATEGORY,
      recentHours: SI_DAILY_SWEEP_HOURS,
      sortBy: "submitted",
      createdAt: Date.now(),
    });
  }

  const favorited = favorites.some((f) => f.q.toLowerCase() === q.trim().toLowerCase() && q.trim().length >= 2);
  const activeSweepId =
    sweeps.find(
      (s) =>
        s.query === q &&
        s.primaryCategory === filterCategory &&
        s.extraCategories === extraCategories &&
        s.recentCategory === recentCategory &&
        s.recentHours === recentHours &&
        s.sortBy === sortBy,
    )?.id ?? null;

  async function runSweepTemplate(sweep: SweepTemplate) {
    setSearchError(null);
    setLoading(true);
    setQ(sweep.query);
    setFilterCategory(sweep.primaryCategory);
    setExtraCategories(sweep.extraCategories);
    setSortBy(sweep.sortBy);
    setRecentCategory(sweep.recentCategory);
    setRecentHours(sweep.recentHours);
    try {
      const keywordParams = new URLSearchParams({
        q: sweep.query,
        limit: "15",
        sort_by: sweep.sortBy,
      });
      const categories = [sweep.primaryCategory.trim(), ...sweep.extraCategories.split(",").map((x) => x.trim())]
        .filter(Boolean)
        .join(",");
      if (categories) keywordParams.set("categories", categories);
      const latestParams = new URLSearchParams({
        category: sweep.recentCategory,
        limit: "20",
        hours: sweep.recentHours,
      });
      const [searchData, latestData] = await Promise.all([
        apiGet<{ papers?: Paper[] }>(`/api/search?${keywordParams}`),
        apiGet<{ papers: Paper[] }>(`/api/category/latest?${latestParams}`),
      ]);
      const list = Array.isArray(searchData.papers) ? searchData.papers : [];
      setPapers(list);
      setLatest(latestData.papers);
      setSearchedKeyword(true);
      setHistory(addHistoryEntry(sweep.query));
      log("info", `Sweep "${sweep.label}" loaded: ${list.length} keyword hits + ${latestData.papers.length} recent`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setSearchError(msg);
      log("error", msg);
    } finally {
      setLoading(false);
    }
  }

  function saveCurrentAsSweep() {
    const label = newSweepLabel.trim();
    if (!label) return;
    const next = addSweepTemplate({
      label,
      query: q,
      primaryCategory: filterCategory,
      extraCategories,
      recentCategory,
      recentHours,
      sortBy: sortBy as "submitted" | "relevance" | "updated",
    });
    setSweeps(next);
    setNewSweepLabel("");
    log("info", `Saved sweep template: ${label}`);
  }

  function startEditSweepLabel(sweep: SweepTemplate) {
    setEditingSweepId(sweep.id);
    setEditingSweepLabel(sweep.label);
  }

  function saveEditedSweepLabel() {
    const id = editingSweepId;
    const label = editingSweepLabel.trim();
    if (!id || !label) return;
    const next = sweeps.map((s) => (s.id === id ? { ...s, label } : s));
    setSweeps(next);
    saveSweepTemplates(next);
    setEditingSweepId(null);
    setEditingSweepLabel("");
    log("info", "Template renamed");
  }

  function exportSweepTemplates() {
    const payload = {
      version: 1,
      exported_at: new Date().toISOString(),
      default_template_id: defaultSweepId,
      templates: sweeps,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "arxiv-mcp-sweep-templates.json";
    a.click();
    URL.revokeObjectURL(url);
    log("info", `Exported ${sweeps.length} templates`);
  }

  async function importSweepTemplates(file: File) {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as {
        templates?: unknown[];
        default_template_id?: string | null;
      };
      if (!Array.isArray(parsed.templates)) {
        throw new Error("Invalid JSON: templates array missing");
      }
      const imported = parsed.templates
        .map((t) => t as Partial<SweepTemplate>)
        .filter((t) => typeof t.label === "string" && typeof t.query === "string")
        .map((t, idx) => ({
          id: `sw-${Date.now()}-${idx}-${Math.random().toString(36).slice(2, 9)}`,
          label: (t.label || "").trim(),
          query: (t.query || "").trim(),
          primaryCategory: (t.primaryCategory || "").trim(),
          extraCategories: (t.extraCategories || "").trim(),
          recentCategory: (t.recentCategory || "").trim() || "cs.AI",
          recentHours: (t.recentHours || "").trim() || "24",
          sortBy: t.sortBy === "relevance" || t.sortBy === "updated" ? t.sortBy : "submitted",
          createdAt: Date.now(),
        }))
        .filter((t) => t.label && t.query);
      if (!imported.length) {
        throw new Error("No valid templates found");
      }
      setSweeps(imported);
      saveSweepTemplates(imported);
      if (parsed.default_template_id) {
        const fallback = imported[0]?.id ?? null;
        if (fallback) {
          setDefaultSweepTemplateId(fallback);
          setDefaultSweepId(fallback);
        }
      } else {
        clearDefaultSweepTemplateId();
        setDefaultSweepId(null);
      }
      log("info", `Imported ${imported.length} templates`);
    } catch (e) {
      log("error", `Import failed: ${String(e)}`);
    }
  }

  return (
    <div className="space-y-8">
      <PageHero eyebrow="Live on arXiv" title="Search the public arXiv website">
        <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
          This page talks to arXiv over the internet. It does not search papers you have saved on your computer—that is
          your{" "}
          <Link to="/depot" className="text-primary font-medium underline underline-offset-2 hover:no-underline">
            library (depot)
          </Link>
          . Use the forms below for keyword search, or for a simple list of new papers in one subject.
        </p>
        <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
          Start with the SI starter queries in <strong className="text-foreground">Load a query</strong>, then save the
          ones you actually use. Treat this page as your incoming paper feed; move the important ones to your library.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" onClick={runDailySISweep} disabled={loading}>
            {loading ? "Running sweep…" : defaultSweepId ? "Run default sweep" : "Run SI daily sweep"}
          </Button>
          <Button type="button" size="sm" variant="secondary" asChild>
            <Link to="/help">Workflow examples</Link>
          </Button>
        </div>
      </PageHero>

      <Card>
        <CardTitle>Custom sweep templates</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Save your own one-click workflows (query + categories + time window). Set one as default so the hero button
          runs it directly.
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Input
            value={newSweepLabel}
            onChange={(e) => setNewSweepLabel(e.target.value)}
            placeholder="Template name (e.g. weekly eval+alignment sweep)"
            className="flex-1"
          />
          <Button type="button" onClick={saveCurrentAsSweep} disabled={!newSweepLabel.trim()}>
            Save current settings
          </Button>
          <Button type="button" variant="outline" onClick={exportSweepTemplates} disabled={sweeps.length === 0}>
            Export JSON
          </Button>
          <Button type="button" variant="outline" onClick={() => importRef.current?.click()}>
            Import JSON
          </Button>
          <input
            ref={importRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                void importSweepTemplates(file);
              }
              e.currentTarget.value = "";
            }}
          />
        </div>
        <ul className="mt-4 space-y-2">
          {sweeps.map((s) => (
            <li
              key={s.id}
              className={cn(
                "rounded-lg border border-border/40 px-3 py-2 text-sm",
                activeSweepId === s.id && "border-primary/50 bg-primary/5",
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  {editingSweepId === s.id ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={editingSweepLabel}
                        onChange={(e) => setEditingSweepLabel(e.target.value)}
                        className="h-8"
                      />
                      <Button type="button" size="sm" onClick={saveEditedSweepLabel} disabled={!editingSweepLabel.trim()}>
                        Save
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingSweepId(null);
                          setEditingSweepLabel("");
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <div className="font-medium truncate">
                      {s.label}
                      {defaultSweepId === s.id ? " (default)" : ""}
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground font-mono truncate">
                    q={s.query} · cat={s.primaryCategory || "any"} · extra={s.extraCategories || "-"} · latest=
                    {s.recentCategory}/{s.recentHours}h
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="secondary" onClick={() => runSweepTemplate(s)}>
                    Run
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => startEditSweepLabel(s)}>
                    Rename
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={defaultSweepId === s.id ? "default" : "outline"}
                    onClick={() => {
                      if (defaultSweepId === s.id) {
                        clearDefaultSweepTemplateId();
                        setDefaultSweepId(null);
                        log("info", "Cleared default sweep");
                      } else {
                        setDefaultSweepTemplateId(s.id);
                        setDefaultSweepId(s.id);
                        log("info", `Default sweep set: ${s.label}`);
                      }
                    }}
                  >
                    {defaultSweepId === s.id ? "Default" : "Set default"}
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => {
                      const next = removeSweepTemplate(s.id);
                      setSweeps(next);
                      if (defaultSweepId === s.id) {
                        setDefaultSweepId(null);
                      }
                    }}
                    title="Delete template"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </li>
          ))}
          {sweeps.length === 0 ? (
            <li className="text-sm text-muted-foreground">
              No saved templates yet. Configure the search controls and save your first template.
            </li>
          ) : null}
        </ul>
      </Card>

      <Card>
        <CardTitle>Keyword search</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Enter words to find in title or abstract, or an advanced query (e.g.{" "}
          <span className="font-mono text-xs">ti:attention AND cat:cs.CL</span>). Pick a starter from the menu, or reuse
          queries you ran before on this browser.
        </p>
        <div className="mt-4 flex flex-col gap-4">
          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Load a query</label>
            <select
              key={pickerKey}
              className={cn(selectClass)}
              defaultValue=""
              onChange={(e) => {
                const v = e.target.value;
                applyPickerValue(v);
                setPickerKey((k) => k + 1);
              }}
            >
              <option value="">Suggestions, saved queries, or recent…</option>
              {suggestedGroups.map(([topic, items]) => (
                <optgroup key={`s-${topic}`} label={`Suggested — ${topic}`}>
                  {items.map((item, idx) => {
                    const globalIdx = SUGGESTED_QUERIES.indexOf(item);
                    return (
                      <option key={item.label + item.q} value={`s:${globalIdx}`}>
                        {item.label}
                      </option>
                    );
                  })}
                </optgroup>
              ))}
              {favoriteGroups.length > 0 ? (
                <optgroup label="Saved (by topic)">
                  {favoriteGroups.flatMap(([topic, items]) =>
                    items.map((f) => (
                      <option key={f.id} value={`f:${f.id}`}>
                        [{topic}] {f.label}
                      </option>
                    )),
                  )}
                </optgroup>
              ) : null}
              {history.length > 0 ? (
                <optgroup label="Recent on this browser">
                  {history.slice(0, 25).map((h) => (
                    <option key={h.id} value={`h:${h.id}`}>
                      {h.q.length > 70 ? `${h.q.slice(0, 70)}…` : h.q}
                    </option>
                  ))}
                </optgroup>
              ) : null}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Keywords or query</label>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder='e.g. "diffusion" or all:transformer'
                className="flex-1"
              />
              <div className="flex gap-2 shrink-0">
                <Button
                  type="button"
                  variant={favorited ? "secondary" : "outline"}
                  className="gap-1.5"
                  onClick={handleToggleFavorite}
                  title={favorited ? "Remove from saved queries" : "Save this query"}
                >
                  <Star className={cn("h-4 w-4", favorited && "fill-primary text-primary")} />
                  {favorited ? "Saved" : "Save"}
                </Button>
              </div>
            </div>
          </div>

          {saveOpen ? (
            <div className="rounded-lg border border-border/60 bg-muted/20 p-4 space-y-3">
              <p className="text-sm font-medium text-foreground">Save this query</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Category</label>
                  <select
                    className={cn(selectClass)}
                    value={saveTopic}
                    onChange={(e) => setSaveTopic(e.target.value)}
                  >
                    {FAVORITE_TOPICS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Short label (optional)</label>
                  <Input
                    value={saveLabel}
                    onChange={(e) => setSaveLabel(e.target.value)}
                    placeholder="e.g. Weekly LLM sweep"
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" size="sm" onClick={confirmSaveFavorite}>
                  Add to saved
                </Button>
                <Button type="button" size="sm" variant="ghost" onClick={() => setSaveOpen(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Primary subject (optional)</label>
              <select
                className={cn(selectClass)}
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="">Any subject — no category filter</option>
                {grouped.map(([group, rows]) => (
                  <optgroup key={group} label={group}>
                    {rows.map((row) => (
                      <option key={row.code} value={row.code}>
                        {row.code} — {row.name}
                      </option>
                    ))}
                  </optgroup>
                  ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Sort results by</label>
              <select className={cn(selectClass)} value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="submitted">Newest submission date</option>
                <option value="relevance">Relevance to query</option>
                <option value="updated">Last updated on arXiv</option>
              </select>
            </div>
            <div className="space-y-1 sm:col-span-2 lg:col-span-1">
              <label className="text-xs font-medium text-foreground">Extra subject tags (optional)</label>
              <Input
                value={extraCategories}
                onChange={(e) => setExtraCategories(e.target.value)}
                placeholder="e.g. cs.CV, cs.RO"
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                Comma-separated. Combined with the primary subject so hits match your query and any of these tags.
              </p>
            </div>
          </div>
          <Button type="button" className="w-fit" onClick={runSearch} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Button>
        </div>

        {searchError ? (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Search failed: {searchError}. Is the backend running on port 10770 (see top bar)?
          </div>
        ) : null}

        {searchedKeyword && !searchError && papers.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No papers matched this query. Try different keywords or relax category filters.
          </p>
        ) : null}

        {(favorites.length > 0 || history.length > 0) && (
          <div className="mt-8 pt-6 border-t border-border/40 space-y-6">
            {favorites.length > 0 ? (
              <div>
                <h3 className="text-sm font-semibold text-foreground">Saved queries</h3>
                <p className="text-xs text-muted-foreground mt-1 mb-3">
                  Organize by topic; change category anytime. Stored only in this browser.
                </p>
                <ul className="space-y-2">
                  {favoriteGroups.flatMap(([, items]) =>
                    items.map((f) => (
                      <li
                        key={f.id}
                        className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between rounded-lg border border-border/40 px-3 py-2 text-sm"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate">{f.label}</div>
                          <div className="text-xs text-muted-foreground font-mono truncate mt-0.5">{f.q}</div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                          <select
                            className={cn(selectClass, "h-9 min-w-[10rem]")}
                            value={f.topic}
                            onChange={(e) => {
                              setFavorites(updateFavoriteTopic(f.id, e.target.value));
                            }}
                          >
                            {FAVORITE_TOPICS.map((t) => (
                              <option key={t} value={t}>
                                {t}
                              </option>
                            ))}
                          </select>
                          <Button type="button" size="sm" variant="secondary" onClick={() => setQ(f.q)}>
                            Use
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="h-9 w-9 text-muted-foreground hover:text-destructive"
                            title="Remove"
                            onClick={() => setFavorites(removeFavorite(f.id))}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </li>
                    )),
                  )}
                </ul>
              </div>
            ) : null}

            {history.length > 0 ? (
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Recent queries</h3>
                    <p className="text-xs text-muted-foreground mt-1">Auto-saved after each successful search.</p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      clearHistory();
                      refreshStorage();
                      log("info", "Cleared query history");
                    }}
                  >
                    Clear recent
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {history.map((h) => (
                    <div
                      key={h.id}
                      className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-background/80 pl-3 pr-1 py-1 text-xs max-w-full"
                    >
                      <button
                        type="button"
                        className="truncate text-left hover:text-primary max-w-[min(100%,14rem)] sm:max-w-[18rem]"
                        onClick={() => setQ(h.q)}
                        title={h.q}
                      >
                        {h.q.length > 42 ? `${h.q.slice(0, 42)}…` : h.q}
                      </button>
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 shrink-0 rounded-full"
                        title="Remove from history"
                        onClick={() => setHistory(removeHistoryEntry(h.id))}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}

        <ul className="mt-6 space-y-4">
          {papers.map((p) => (
            <PaperHit key={p.paper_id} p={p} />
          ))}
        </ul>
      </Card>

      <Card>
        <CardTitle>New submissions in one subject</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 max-w-3xl">
          This is <strong>not</strong> a keyword search. It lists papers whose <em>primary subject</em> includes the
          category you pick, and whose submission time falls within the window (arXiv’s “recent” listing, exposed as a
          rolling hour count). Use it to skim what appeared in e.g. machine learning this week without deciding on
          search terms first.
        </p>
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="space-y-1 min-w-[220px] flex-1">
            <label className="text-xs font-medium text-foreground">Subject category</label>
            <select
              className={cn(selectClass)}
              value={recentCategory}
              onChange={(e) => setRecentCategory(e.target.value)}
            >
              {grouped.map(([group, rows]) => (
                <optgroup key={group} label={group}>
                  {rows.map((row) => (
                    <option key={row.code} value={row.code}>
                      {row.code} — {row.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="space-y-1 min-w-[200px]">
            <label className="text-xs font-medium text-foreground">Time window</label>
            <select className={cn(selectClass)} value={recentHours} onChange={(e) => setRecentHours(e.target.value)}>
              {HOURS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <Button variant="secondary" className="w-fit" onClick={runLatest} disabled={loading}>
            Load recent papers
          </Button>
        </div>
        <ul className="mt-6 space-y-4">
          {latest.map((p) => (
            <PaperHit key={p.paper_id} p={p} />
          ))}
        </ul>
      </Card>
    </div>
  );
}
