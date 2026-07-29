import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { type Paper, PaperCard } from "@/components/PaperCard";
import { PaperDetailModal } from "@/components/PaperDetailModal";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type CategoryRow = { code: string; name: string; group: string };

const selectClass =
  "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground outline-none focus:border-primary transition-colors";

export default function ArxivSearch() {
  const { log } = useLogger();
  const [searchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<CategoryRow[]>([]);
  const [q, setQ] = useState(() => searchParams.get("q") || "");
  const [servers, setServers] = useState(
    "arxiv,biorxiv,medrxiv,chemrxiv,researchsquare",
  );
  const [loading, setLoading] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [perServer, setPerServer] = useState<
    Record<string, { label: string; count: number }>
  >({});
  const [recentCategory, setRecentCategory] = useState("cs.LG");
  const [recentHours, setRecentHours] = useState("72");
  const [latest, setLatest] = useState<Paper[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [singleId, setSingleId] = useState("");
  const [singleLoading, setSingleLoading] = useState(false);
  const [singlePaper, setSinglePaper] = useState<Paper | null>(null);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [detailPaper, setDetailPaper] = useState<Paper | null>(null);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    apiGet<{ categories: CategoryRow[] }>("/api/categories")
      .then((d) => setCatalog(d.categories ?? []))
      .catch(() => log("error", "Failed to load category catalog"));
  }, [log]);

  // Auto-search when navigated with ?q= from SweepsPage / favorites / history
  useEffect(() => {
    const urlQuery = searchParams.get("q");
    if (urlQuery) {
      setQ(urlQuery);
      // Defer the fetch so state settles
      const timer = setTimeout(() => {
        const params = new URLSearchParams({
          q: urlQuery,
          servers,
          limit: "15",
        });
        apiGet<{
          merged: Paper[];
          per_server: Record<
            string,
            { label: string; count: number; papers: Paper[] }
          >;
        }>(`/api/preprints/search?${params}`)
          .then((data) => {
            setPapers(data.merged ?? []);
            setSearched(true);
            const counts: Record<string, { label: string; count: number }> = {};
            for (const [srv, info] of Object.entries(data.per_server))
              counts[srv] = { label: info.label, count: info.count };
            setPerServer(counts);
          })
          .catch((e) => setSearchError(String(e)));
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [searchParams.get, servers]); // run once on mount

  const grouped = useMemo(() => {
    const m = new Map<string, CategoryRow[]>();
    for (const row of catalog) {
      const g = row.group || "Other";
      if (!m.has(g)) m.set(g, []);
      m.get(g)?.push(row);
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
      const data = await apiGet<{
        merged: Paper[];
        per_server: Record<
          string,
          { label: string; count: number; papers: Paper[] }
        >;
      }>(`/api/preprints/search?${params}`);
      setPapers(data.merged ?? []);
      const counts: Record<string, { label: string; count: number }> = {};
      for (const [srv, info] of Object.entries(data.per_server))
        counts[srv] = { label: info.label, count: info.count };
      setPerServer(counts);
      log(
        "info",
        `Search returned ${data.merged?.length ?? 0} papers across ${Object.keys(data.per_server).length} servers`,
      );
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
      const data = await apiGet<{ papers: Paper[] }>(
        `/api/category/latest?category=${recentCategory}&hours=${recentHours}`,
      );
      setLatest(data.papers ?? []);
    } catch (e) {
      log("error", `Failed to load recent: ${e}`);
    }
  }, [recentCategory, recentHours, log]);

  const lookupSingle = useCallback(async () => {
    const id = singleId.trim();
    if (!id) return;
    setSingleLoading(true);
    setSingleError(null);
    setSinglePaper(null);
    try {
      const data = await apiGet<{ paper: Paper }>(
        `/api/paper?paper_id=${encodeURIComponent(id)}`,
      );
      setSinglePaper(data.paper);
    } catch (e) {
      setSingleError(String(e));
    } finally {
      setSingleLoading(false);
    }
  }, [singleId]);

  const searchPresets = [
    {
      label: "Consciousness & AI",
      q: "consciousness AND (artificial intelligence OR large language model OR machine learning)",
    },
    {
      label: "Mechanistic interpretability",
      q: "mechanistic interpretability OR (sparse autoencoder AND language model)",
    },
    {
      label: "AI safety & alignment",
      q: "(AI safety OR alignment OR trustworthy)",
    },
    {
      label: "LLM evaluation",
      q: "(large language model AND (benchmark OR evaluation OR reasoning))",
    },
  ];

  return (
    <div className="space-y-6" data-testid="search-page">
      <PageHero eyebrow="arXiv Search" title="Find papers" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          Search arXiv by keyword, browse a category, or look up a specific
          paper ID.
        </p>
      </PageHero>

      <Card data-testid="search-card">
        <div className="flex items-center justify-between">
          <CardTitle>Search</CardTitle>
          <button
            type="button"
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Options{" "}
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                showConfig && "rotate-180",
              )}
            />
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mt-3">
          {searchPresets.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => setQ(p.q)}
              className="px-2.5 py-1 rounded-full text-xs font-medium bg-primary/5 text-primary/80 border border-primary/10 hover:bg-primary/10 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="mt-3 flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder='e.g. "consciousness AND transformer"'
              className="pl-9"
              onKeyDown={(e) => {
                if (e.key === "Enter") runSearch();
              }}
            />
          </div>
          <Button
            onClick={runSearch}
            disabled={loading}
            data-testid="search-button"
          >
            {loading ? "Searching..." : "Search"}
          </Button>
        </div>

        <AnimatePresence>
          {showConfig && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="pt-3 space-y-3 border-t border-border/40 mt-3">
                <div>
                  <span className="text-xs font-medium text-foreground block">
                    Search servers
                  </span>
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
                        <label
                          key={key}
                          className="flex items-center gap-1.5 text-xs cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              const parts = servers.split(",").filter(Boolean);
                              setServers(
                                checked
                                  ? parts.filter((s) => s !== key).join(",")
                                  : [...parts, key].join(","),
                              );
                            }}
                            className="rounded border-border"
                          />
                          {label}
                          {perServer[key] ? (
                            <span className="text-muted-foreground">
                              ({perServer[key].count})
                            </span>
                          ) : null}
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {searchError && (
          <div
            className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            data-testid="search-error"
          >
            Search failed: {searchError}
          </div>
        )}
        {searched && !searchError && papers.length === 0 && (
          <p className="mt-4 text-sm text-muted-foreground">
            No results. Try different keywords.
          </p>
        )}
      </Card>

      <AnimatePresence>
        {papers.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
            data-testid="search-results"
          >
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {papers.length} result{papers.length !== 1 ? "s" : ""}
              <Link
                to="/sweeps"
                className="ml-3 font-normal normal-case text-primary hover:underline"
              >
                Saved queries & sweeps &rarr;
              </Link>
            </h2>
            {papers.map((p) => (
              <PaperCard key={p.paper_id} p={p} onQuickView={setDetailPaper} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardTitle>Look up a paper</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Single arXiv ID lookup.
          </p>
          <div className="mt-3 flex gap-2">
            <Input
              value={singleId}
              onChange={(e) => setSingleId(e.target.value)}
              placeholder="arXiv ID (e.g. 2401.00001)"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === "Enter") lookupSingle();
              }}
            />
            <Button
              onClick={lookupSingle}
              disabled={singleLoading}
              variant="secondary"
              size="sm"
            >
              {singleLoading ? "Loading..." : "Look up"}
            </Button>
          </div>
          {singleError && (
            <p className="mt-2 text-xs text-destructive">{singleError}</p>
          )}
          {singlePaper && (
            <div className="mt-3">
              <PaperCard p={singlePaper} onQuickView={setDetailPaper} />
            </div>
          )}
        </Card>

        <Card>
          <CardTitle>New submissions</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Recent papers in a subject area.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <select
              className={cn(selectClass, "max-w-40")}
              value={recentCategory}
              onChange={(e) => setRecentCategory(e.target.value)}
            >
              {grouped.map(([group, rows]) => (
                <optgroup key={group} label={group}>
                  {rows.map((row) => (
                    <option key={row.code} value={row.code}>
                      {row.code}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <select
              className={cn(selectClass, "max-w-20")}
              value={recentHours}
              onChange={(e) => setRecentHours(e.target.value)}
            >
              <option value="24">24h</option>
              <option value="72">72h</option>
              <option value="168">7d</option>
            </select>
            <Button onClick={loadRecent} variant="secondary" size="sm">
              Refresh
            </Button>
          </div>
          {latest.length > 0 && (
            <div className="mt-3 space-y-2">
              {latest.map((p) => (
                <PaperCard
                  key={p.paper_id}
                  p={p}
                  onQuickView={setDetailPaper}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      <AnimatePresence>
        {detailPaper && (
          <PaperDetailModal
            paper={detailPaper}
            onClose={() => setDetailPaper(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
