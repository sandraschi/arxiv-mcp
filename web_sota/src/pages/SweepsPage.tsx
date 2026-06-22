import { useMemo, useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";
import {
  SUGGESTED_QUERIES,
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
  type FavoriteEntry,
  type HistoryEntry,
  type SweepTemplate,
} from "@/lib/searchQueryStorage";

export default function SweepsPage() {
  const { log } = useLogger();
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory());
  const [favorites, setFavorites] = useState<FavoriteEntry[]>(() => loadFavorites());
  const [sweeps, setSweeps] = useState<SweepTemplate[]>(() => loadSweepTemplates());
  const [defaultSweepId, setDefaultSweepId] = useState<string | null>(() => loadDefaultSweepTemplateId());
  const [newSweepLabel, setNewSweepLabel] = useState("");
  const [editingSweepId, setEditingSweepId] = useState<string | null>(null);
  const [editingSweepLabel, setEditingSweepLabel] = useState("");


  const suggestedGroups = useMemo(() => {
    const m = new Map<string, typeof SUGGESTED_QUERIES>();
    for (const sq of SUGGESTED_QUERIES) {
      const g = sq.topic || "General";
      if (!m.has(g)) m.set(g, []);
      m.get(g)!.push(sq);
    }
    return [...m.entries()];
  }, []);

  const favoriteGroups = useMemo(() => {
    const m = new Map<string, FavoriteEntry[]>();
    for (const f of favorites) {
      const t = f.topic || "General";
      if (!m.has(t)) m.set(t, []);
      m.get(t)!.push(f);
    }
    return [...m.entries()];
  }, [favorites]);

  return (
    <div className="space-y-8">
      <PageHero eyebrow="Saved queries & sweeps" title="Research sweeps" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          Save search queries as templates to run daily or weekly sweeps. Your favorites and history are stored in this browser.
        </p>
      </PageHero>

      {/* Suggested queries */}
      <Card>
        <CardTitle>Suggested starter queries</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">Click any to copy it into the search page.</p>
        <div className="mt-4 space-y-4">
          {suggestedGroups.map(([topic, items]) => (
            <div key={topic}>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">{topic}</h4>
              <div className="flex flex-wrap gap-2">
                {items.map((item, i) => (
                  <a
                    key={i}
                    href={`/search?q=${encodeURIComponent(item.q)}`}
                    className="px-3 py-1.5 rounded-full text-xs font-medium bg-primary/5 text-primary/80 border border-primary/10 hover:bg-primary/10 transition-colors"
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Sweep templates */}
      <Card>
        <CardTitle>Sweep templates</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">Saved query configurations you can run on the search page. Set one as default for a one-click daily sweep.</p>

        <div className="mt-4 flex gap-2">
          <input
            value={newSweepLabel}
            onChange={(e) => setNewSweepLabel(e.target.value)}
            placeholder="New template name…"
            className="flex-1 max-w-xs bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary"
          />
          <Button
            type="button"
            size="sm"
            disabled={!newSweepLabel.trim()}
            onClick={() => {
              const next = addSweepTemplate({ label: newSweepLabel.trim(), query: "", primaryCategory: "", extraCategories: "", recentCategory: "cs.LG", recentHours: "72", sortBy: "submitted" });
              setSweeps(next);
              setNewSweepLabel("");
              log("info", `Sweep template created: ${newSweepLabel.trim()}`);
            }}
          >
            Create
          </Button>
        </div>

        {sweeps.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {sweeps.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border/40 bg-card/30">
                <div className="min-w-0 flex-1">
                  {editingSweepId === s.id ? (
                    <input
                      value={editingSweepLabel}
                      onChange={(e) => setEditingSweepLabel(e.target.value)}
                      onBlur={() => { setEditingSweepId(null); }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && editingSweepLabel.trim()) {
                          const next = sweeps.map((sw) => sw.id === s.id ? { ...sw, label: editingSweepLabel.trim() } : sw);
                          saveSweepTemplates(next);
                          setSweeps(next);
                          setEditingSweepId(null);
                        }
                      }}
                      className="bg-background border border-border rounded px-2 py-1 text-sm w-full max-w-xs outline-none"
                      autoFocus
                    />
                  ) : (
                    <span
                      className="text-sm font-medium cursor-pointer hover:text-primary"
                      onClick={() => { setEditingSweepId(s.id); setEditingSweepLabel(s.label); }}
                      title="Click to rename"
                    >
                      {s.label}
                    </span>
                  )}
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {s.query || "(no query)"} · {s.primaryCategory || "all"} · {s.recentHours}h
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      if (defaultSweepId === s.id) {
                        clearDefaultSweepTemplateId();
                        setDefaultSweepId(null);
                      } else {
                        setDefaultSweepTemplateId(s.id);
                        setDefaultSweepId(s.id);
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
                      if (defaultSweepId === s.id) setDefaultSweepId(null);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">No templates yet. Create one above.</p>
        )}
      </Card>

      {/* Favorites */}
      <Card>
        <CardTitle>Saved queries</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">Organized by topic. Click a saved query to run it on the search page.</p>
        {favoriteGroups.length > 0 ? (
          <div className="mt-4 space-y-4">
            {favoriteGroups.map(([topic, items]) => (
              <div key={topic}>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">{topic}</h4>
                <div className="flex flex-wrap gap-2">
                  {items.map((f) => (
                    <div key={f.id} className="group flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium bg-primary/5 text-primary/80 border border-primary/10">
                      <a href={`/search?q=${encodeURIComponent(f.q)}`} className="hover:underline">{f.label}</a>
                      <button
                        type="button"
                        onClick={() => {
                          const next = removeFavorite(f.id);
                          setFavorites(next);
                        }}
                        className="ml-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">No saved queries. Save one from the search page.</p>
        )}
      </Card>

      {/* History */}
      <Card>
        <CardTitle>Recent searches</CardTitle>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">Stored in this browser only.</p>
          {history.length > 0 ? (
            <Button type="button" size="sm" variant="ghost" onClick={() => { clearHistory(); setHistory([]); }}>
              Clear history
            </Button>
          ) : null}
        </div>
        {history.length > 0 ? (
          <ul className="mt-3 space-y-1">
            {history.slice(0, 50).map((h) => (
              <li key={h.id} className="flex items-center justify-between gap-2 py-1.5 border-b border-border/20 last:border-0">
                <a
                  href={`/search?q=${encodeURIComponent(h.q)}`}
                  className="text-sm text-muted-foreground hover:text-foreground truncate flex-1"
                  title={h.q}
                >
                  {h.q.length > 90 ? `${h.q.slice(0, 90)}…` : h.q}
                </a>
                <button
                  type="button"
                  onClick={() => { const next = removeHistoryEntry(h.id); setHistory(next); }}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">No search history yet.</p>
        )}
      </Card>
    </div>
  );
}
