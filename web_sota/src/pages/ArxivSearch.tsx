import { AnimatePresence, motion } from "framer-motion";
import { Search } from "lucide-react";
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
    "arxiv,biorxiv,medrxiv,chemrxiv,researchsquare,socarxiv,psyarxiv",
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
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [searched, setSearched] = useState(false);
  const [singleId, setSingleId] = useState("");
  const [singleLoading, setSingleLoading] = useState(false);
  const [singlePaper, setSinglePaper] = useState<Paper | null>(null);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [titleQ, setTitleQ] = useState("");
  const [titleLoading, setTitleLoading] = useState(false);
  const [titleResults, setTitleResults] = useState<Paper[]>([]);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [titleSort, setTitleSort] = useState("relevance");
  const [sort, setSort] = useState<"relevance" | "newest" | "oldest">(
    "relevance",
  );

  // Exact title matches first: arXiv ranks by relevance, so the seminal
  // paper can sit pages down. Normalized compare, then prefix, then rest.
  const boostExact = useCallback((items: Paper[], query: string) => {
    const norm = (s: string) =>
      s
        .toLowerCase()
        .replace(/[^a-z0-9 ]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    const nq = norm(query);
    if (!nq) return items;
    const exact = items.filter((p) => norm(p.title) === nq);
    const starts = items.filter(
      (p) => norm(p.title) !== nq && norm(p.title).startsWith(nq),
    );
    const rest = items.filter(
      (p) => norm(p.title) !== nq && !norm(p.title).startsWith(nq),
    );
    return [...exact, ...starts, ...rest];
  }, []);
  const [detailPaper, setDetailPaper] = useState<Paper | null>(null);
  const [categoryScope, setCategoryScope] = useState("");

  // Server personas: a medically oriented user and a CS user should not
  // have to uncheck boxes every time — one click sets the relevant servers.
  const serverPersonas: Array<{ label: string; servers: string }> = [
    {
      label: "All servers",
      servers:
        "arxiv,biorxiv,medrxiv,chemrxiv,researchsquare,socarxiv,psyarxiv",
    },
    { label: "Computer science", servers: "arxiv,researchsquare" },
    { label: "Life sciences", servers: "arxiv,biorxiv,medrxiv" },
    { label: "Chemistry", servers: "arxiv,chemrxiv" },
    { label: "Social sciences", servers: "socarxiv,psyarxiv" },
  ];

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
          errors?: Record<string, string>;
        }>(`/api/preprints/search?${params}`)
          .then((data) => {
            setPapers(data.merged ?? []);
            setSearched(true);
            setServerErrors(data.errors ?? {});
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

  // Keyword results arrive interleaved from 5 servers with no date order.
  // Client-side sort: relevance keeps server order, newest/oldest parse
  // the published stamp (unparseable dates sink to the bottom).
  // The category scope filters merged results to that arXiv category.
  const sortedPapers = useMemo(() => {
    let list = papers;
    if (categoryScope) {
      list = list.filter((p) => p.categories?.includes(categoryScope));
    }
    if (sort === "relevance") return list;
    const stamp = (p: Paper) => {
      const t = p.published ? Date.parse(p.published) : NaN;
      return Number.isNaN(t) ? null : t;
    };
    return [...list].sort((a, b) => {
      const ta = stamp(a);
      const tb = stamp(b);
      if (ta === null && tb === null) return 0;
      if (ta === null) return 1;
      if (tb === null) return -1;
      return sort === "newest" ? tb - ta : ta - tb;
    });
  }, [papers, sort, categoryScope]);

  const runSearch = useCallback(async () => {
    if (!q.trim()) return;
    setLoading(true);
    setSearchError(null);
    setServerErrors({});
    setSearched(true);
    try {
      const params = new URLSearchParams({ q, servers, limit: "15" });
      const data = await apiGet<{
        merged: Paper[];
        per_server: Record<
          string,
          { label: string; count: number; papers: Paper[] }
        >;
        errors?: Record<string, string>;
      }>(`/api/preprints/search?${params}`);
      setPapers(data.merged ?? []);
      setServerErrors(data.errors ?? {});
      const counts: Record<string, { label: string; count: number }> = {};
      for (const [srv, info] of Object.entries(data.per_server))
        counts[srv] = { label: info.label, count: info.count };
      setPerServer(counts);
      if (data.errors && Object.keys(data.errors).length > 0) {
        log(
          "warn",
          `Some servers reported errors: ${Object.entries(data.errors)
            .map(([k, v]) => `${k}: ${v}`)
            .join("; ")}`,
        );
      }
      log(
        "info",
        `Search returned ${data.merged?.length ?? 0} papers across ${Object.keys(data.per_server).length} servers`,
      );
    } catch (e) {
      setSearchError(String(e));
      setPapers([]);
      setPerServer({});
      setServerErrors({});
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

  const lookupTitle = useCallback(async () => {
    const t = titleQ.trim();
    if (!t) return;
    setTitleLoading(true);
    setTitleError(null);
    setTitleResults([]);
    try {
      // Verbatim title search (ti:) — exact phrases in quotes work too,
      // e.g. "Attention is all you need".
      const catParam = categoryScope
        ? `&category=${encodeURIComponent(categoryScope)}`
        : "";
      const data = await apiGet<{ papers: Paper[] }>(
        `/api/searchAdvanced?title=${encodeURIComponent(t)}&page_size=50&sort_by=${titleSort}${catParam}`,
      );
      // Backend returns the full arXiv result page: boost exact matches
      // first, then show the top 10.
      setTitleResults(boostExact(data.papers ?? [], t).slice(0, 10));
    } catch (e) {
      setTitleError(String(e));
    } finally {
      setTitleLoading(false);
    }
  }, [titleQ, titleSort, boostExact, categoryScope]);

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

  const titlePresets = [
    "Attention Is All You Need",
    "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    "Language Models are Few-Shot Learners",
    "ImageNet Classification with Deep Convolutional Neural Networks",
    "Deep Residual Learning for Image Recognition",
    "Generative Adversarial Nets",
    "Auto-Encoding Variational Bayes",
    "Long Short-Term Memory",
    "Dropout: A Simple Way to Prevent Neural Networks from Overfitting",
    "Adam: A Method for Stochastic Optimization",
    "Mastering the Game of Go with Deep Neural Networks and Tree Search",
    "Playing Atari with Deep Reinforcement Learning",
  ];

  return (
    <div className="space-y-6" data-testid="search-page">
      <PageHero eyebrow="arXiv Search" title="Find papers" size="large">
        <p className="text-muted-foreground text-sm md:text-base">
          Search arXiv by keyword, exact title, browse a category, or look up a
          specific paper ID.
        </p>
      </PageHero>

      <Card data-testid="search-card">
        <CardTitle>Search</CardTitle>

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

        {searchError && (
          <div
            className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            data-testid="search-error"
          >
            Search failed: {searchError}
          </div>
        )}

        <div className="pt-3 space-y-3 border-t border-border/40 mt-4">
          <div>
            <span className="text-xs font-medium text-foreground block">
              Who are you? (server preset)
            </span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {serverPersonas.map((persona) => (
                <button
                  key={persona.label}
                  type="button"
                  onClick={() => setServers(persona.servers)}
                  className={cn(
                    "px-2.5 py-1 rounded-full text-xs font-medium border transition-colors",
                    servers === persona.servers
                      ? "bg-primary/15 text-primary border-primary/30"
                      : "bg-primary/5 text-primary/80 border-primary/10 hover:bg-primary/10",
                  )}
                >
                  {persona.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <span className="text-xs font-medium text-foreground block">
              Servers
            </span>
            <div className="flex flex-wrap gap-3 mt-1">
              {[
                ["arxiv", "arXiv"],
                ["biorxiv", "bioRxiv"],
                ["medrxiv", "medRxiv"],
                ["chemrxiv", "ChemRxiv"],
                ["researchsquare", "Research Square"],
                ["socarxiv", "SocArXiv"],
                ["psyarxiv", "PsyArXiv"],
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
          <div>
            <span className="text-xs font-medium text-foreground block">
              arXiv category scope
            </span>
            <select
              className={cn(selectClass, "max-w-64 mt-1")}
              value={categoryScope}
              onChange={(e) => setCategoryScope(e.target.value)}
              data-testid="category-scope"
              aria-label="arXiv category scope"
            >
              <option value="">All categories</option>
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
            <p className="text-[11px] text-muted-foreground mt-1">
              Filters keyword results to this category; narrows title search
              too. Non-arXiv servers have no arXiv categories, so they drop out
              while a scope is set.{" "}
              <Link to="/categories" className="text-primary hover:underline">
                What do the codes mean?
              </Link>
            </p>
          </div>
        </div>

        {searchError && (
          <div
            className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            data-testid="search-error"
          >
            Search failed: {searchError}
          </div>
        )}
        {Object.keys(serverErrors).length > 0 && (
          <div
            className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-600 dark:text-amber-400 space-y-1"
            data-testid="server-errors"
          >
            <div className="font-semibold flex items-center gap-1.5">
              <span>⚠️ Some preprint servers encountered errors:</span>
            </div>
            <ul className="list-disc pl-5 text-xs space-y-0.5">
              {Object.entries(serverErrors).map(([srv, err]) => (
                <li key={srv}>
                  <strong className="uppercase">{srv}</strong>: {err}
                </li>
              ))}
            </ul>
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
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center">
              <span>
                {papers.length} result{papers.length !== 1 ? "s" : ""}
              </span>
              <select
                className={cn(selectClass, "max-w-36 ml-3")}
                value={sort}
                onChange={(e) =>
                  setSort(e.target.value as "relevance" | "newest" | "oldest")
                }
                data-testid="results-sort"
                aria-label="Sort results"
              >
                <option value="relevance">Relevance</option>
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
              </select>
              <Link
                to="/sweeps"
                className="ml-3 font-normal normal-case text-primary hover:underline"
              >
                Saved queries & sweeps &rarr;
              </Link>
            </h2>
            {sortedPapers.map((p) => (
              <PaperCard key={p.paper_id} p={p} onQuickView={setDetailPaper} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-4 grid-cols-1">
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
          <div className="mt-4 border-t border-border/40 pt-3">
            <p className="text-xs font-medium text-foreground">
              Or find by exact title
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verbatim title search (ti:) — e.g. Attention is all you need.
            </p>
            <div className="mt-2">
              <select
                className={cn(selectClass, "w-full")}
                value=""
                onChange={(e) => {
                  if (!e.target.value) return;
                  setTitleQ(e.target.value);
                  setTitleResults([]);
                  setTitleError(null);
                }}
                data-testid="title-preset-select"
              >
                <option value="">Seminal papers — pick one…</option>
                {titlePresets.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="mt-2 flex gap-2">
              <Input
                value={titleQ}
                onChange={(e) => setTitleQ(e.target.value)}
                placeholder="Paper title (e.g. Attention is all you need)"
                className="flex-1"
                data-testid="title-search-input"
                onKeyDown={(e) => {
                  if (e.key === "Enter") lookupTitle();
                }}
              />
              <Button
                onClick={lookupTitle}
                disabled={titleLoading}
                variant="secondary"
                size="sm"
                data-testid="title-search-button"
              >
                {titleLoading ? "Searching..." : "Find title"}
              </Button>
              <select
                className={cn(selectClass, "max-w-36")}
                value={titleSort}
                onChange={(e) => setTitleSort(e.target.value)}
                data-testid="title-sort"
                aria-label="Title sort order"
              >
                <option value="relevance">Relevance</option>
                <option value="date_desc">Newest first</option>
                <option value="date_asc">Oldest first</option>
              </select>
            </div>
            {titleError && (
              <p className="mt-2 text-xs text-destructive">{titleError}</p>
            )}
            {titleResults.length > 0 && (
              <div className="mt-3 space-y-2" data-testid="title-results">
                {titleResults.map((p) => (
                  <PaperCard
                    key={p.paper_id}
                    p={p}
                    onQuickView={setDetailPaper}
                  />
                ))}
              </div>
            )}
          </div>
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
