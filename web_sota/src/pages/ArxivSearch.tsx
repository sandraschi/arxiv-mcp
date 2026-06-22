import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";
import { PaperHit, type Paper } from "@/components/PaperHit";

type CategoryRow = { code: string; name: string; group: string };

const selectClass = "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground outline-none focus:border-primary transition-colors";

export default function ArxivSearch() {
  const { log } = useLogger();
  const [catalog, setCatalog] = useState<CategoryRow[]>([]);
  const [q, setQ] = useState("");
  const [_filterCategory] = useState("");
  const [_sortBy] = useState("submitted");
  const [servers, setServers] = useState("arxiv,biorxiv,medrxiv,chemrxiv,researchsquare");
  const [loading, setLoading] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [perServer, setPerServer] = useState<Record<string, {label:string;count:number}>>({});
  const [recentCategory, setRecentCategory] = useState("cs.LG");
  const [recentHours, setRecentHours] = useState("72");
  const [latest, setLatest] = useState<Paper[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [singleId, setSingleId] = useState("");
  const [singleLoading, setSingleLoading] = useState(false);
  const [singlePaper, setSinglePaper] = useState<Paper | null>(null);
  const [singleError, setSingleError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<CategoryRow[]>("/api/categories")
      .then(setCatalog)
      .catch(() => log("error", "Failed to load category catalog"));
  }, [log]);

  const grouped = useMemo(() => {
    const m = new Map<string, CategoryRow[]>();
    for (const row of catalog) {
      const g = row.group || "Other";
      if (!m.has(g)) m.set(g, []);
      m.get(g)!.push(row);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [catalog]);

  const runSearch = useCallback(async () => {
    if (!q.trim()) return;
    setLoading(true);
    setSearchError(null);
    setSearched(true);
    try {
      const params = new URLSearchParams({ q, servers, limit: "15" });
      const data = await apiGet<{ merged: Paper[]; per_server: Record<string, {label:string;count:number;papers:Paper[]}> }>(`/api/preprints/search?${params}`);
      setPapers(data.merged ?? []);
      const counts: Record<string, {label:string;count:number}> = {};
      for (const [srv, info] of Object.entries(data.per_server)) {
        counts[srv] = { label: info.label, count: info.count };
      }
      setPerServer(counts);
      log("info", `Search returned ${data.merged?.length ?? 0} papers across ${Object.keys(data.per_server).length} servers`);
    } catch (e) {
      setSearchError(String(e));
      setPapers([]);
      setPerServer({});
    } finally {
      setLoading(false);
    }
  }, [q, servers, log]);

  const loadRecent = useCallback(async () => {
    try {
      const data = await apiGet<{ papers: Paper[] }>(`/api/category/latest?category=${recentCategory}&hours=${recentHours}`);
      setLatest(data.papers ?? []);
    } catch { /* ignore */ }
  }, [recentCategory, recentHours]);

  const lookupSingle = useCallback(async () => {
    const id = singleId.trim();
    if (!id) return;
    setSingleLoading(true);
    setSingleError(null);
    setSinglePaper(null);
    try {
      const data = await apiGet<Paper>(`/api/paper?paper_id=${encodeURIComponent(id)}`);
      setSinglePaper(data);
    } catch (e) {
      setSingleError(String(e));
    } finally {
      setSingleLoading(false);
    }
  }, [singleId]);

  const searchPresets = [
    { label: "Consciousness & AI", q: "consciousness AND (artificial intelligence OR large language model OR machine learning)" },
    { label: "Mechanistic interpretability", q: "mechanistic interpretability OR (sparse autoencoder AND language model)" },
    { label: "AI safety & alignment", q: "(AI safety OR alignment OR trustworthy)" },
    { label: "LLM evaluation & benchmarks", q: "(large language model AND (benchmark OR evaluation OR reasoning))" },
  ];

  return (
    <div className="space-y-8">
      <PageHero eyebrow="arXiv Search" title="Find papers" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          Search arXiv by keyword, browse a category, or look up a specific paper ID.
          Save papers to your library depot for offline reading and semantic search.
        </p>
      </PageHero>

      {/* Search form */}
      <Card>
        <CardTitle>Search arXiv</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Enter keywords for title/abstract search, an arXiv ID, or try a preset below.
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          {searchPresets.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => { setQ(p.q); }}
              className="px-2.5 py-1 rounded-full text-xs font-medium bg-primary/5 text-primary/80 border border-primary/10 hover:bg-primary/10 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-col gap-4">
          <div className="flex flex-col gap-3">
            <label className="text-xs font-medium text-foreground">Keywords</label>
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder='e.g. "consciousness AND transformer" or CRISPR'
              onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-foreground">Search servers</label>
            <div className="flex flex-wrap gap-3 mt-1">
              {[
                ["arxiv", "arXiv"],
                ["biorxiv", "bioRxiv"],
                ["medrxiv", "medRxiv"],
                ["chemrxiv", "ChemRxiv"],
                ["researchsquare", "Research Square"],
              ].map(([key, label]) => {
                const checked = servers.includes(key);
                return (
                  <label key={key} className="flex items-center gap-1.5 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {
                        const parts = servers.split(",").filter(Boolean);
                        setServers(checked ? parts.filter((s) => s !== key).join(",") : [...parts, key].join(","));
                      }}
                      className="rounded border-border"
                    />
                    {label}
                    {perServer[key] ? <span className="text-muted-foreground">({perServer[key].count})</span> : null}
                  </label>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button type="button" onClick={runSearch} disabled={loading}>
              {loading ? "Searching…" : "Search"}
            </Button>
            <Link to="/sweeps" className="text-xs text-primary hover:underline">Saved queries & sweeps →</Link>
          </div>
        </div>

        {searchError ? (
          <div className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Search failed: {searchError}
          </div>
        ) : null}

        {searched && !searchError && papers.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">No results. Try different keywords or remove category filter.</p>
        ) : null}
      </Card>

      {/* Search results */}
      {papers.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">{papers.length} result{papers.length !== 1 ? "s" : ""}</h2>
          {papers.map((p) => (
            <PaperHit key={p.paper_id} p={p} />
          ))}
        </div>
      ) : null}

      {/* Single paper lookup */}
      <Card>
        <CardTitle>Look up a specific paper</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">Enter an arXiv ID (e.g. 2401.00001) to fetch metadata and ingest it directly.</p>
        <div className="mt-3 flex gap-2">
          <Input
            value={singleId}
            onChange={(e) => setSingleId(e.target.value)}
            placeholder="arXiv ID"
            className="max-w-xs"
            onKeyDown={(e) => { if (e.key === "Enter") lookupSingle(); }}
          />
          <Button type="button" onClick={lookupSingle} disabled={singleLoading} variant="secondary">
            {singleLoading ? "Loading…" : "Look up"}
          </Button>
        </div>
        {singleError ? <p className="mt-2 text-xs text-destructive">{singleError}</p> : null}
        {singlePaper ? (
          <div className="mt-4">
            <PaperHit p={singlePaper} />
          </div>
        ) : null}
      </Card>

      {/* Recent submissions */}
      <Card>
        <CardTitle>New submissions</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">Recent papers in a subject area.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <select className={cn(selectClass, "max-w-48")} value={recentCategory} onChange={(e) => setRecentCategory(e.target.value)}>
            {grouped.map(([group, rows]) => (
              <optgroup key={group} label={group}>
                {rows.map((row) => (
                  <option key={row.code} value={row.code}>{row.code}</option>
                ))}
              </optgroup>
            ))}
          </select>
          <select className={cn(selectClass, "max-w-24")} value={recentHours} onChange={(e) => setRecentHours(e.target.value)}>
            <option value="24">24h</option>
            <option value="72">72h</option>
            <option value="168">7 days</option>
          </select>
          <Button type="button" onClick={loadRecent} variant="secondary" size="sm">Refresh</Button>
        </div>
        {latest.length > 0 ? (
          <div className="mt-4 space-y-3">
            {latest.map((p) => (
              <PaperHit key={p.paper_id} p={p} />
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">Click Refresh to load recent papers.</p>
        )}
      </Card>

      <p className="text-xs text-muted-foreground text-center pb-8">
        <Link to="/sweeps" className="text-primary hover:underline">Saved queries, sweep templates & history →</Link>
      </p>
    </div>
  );
}
