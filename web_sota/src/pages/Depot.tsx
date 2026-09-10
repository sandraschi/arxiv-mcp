import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowUpDown,
  BookOpen,
  ChevronDown,
  Columns2,
  ExternalLink,
  Filter,
  LayoutGrid,
  List,
  Maximize2,
  Minimize2,
  RefreshCw,
  RotateCcw,
  Rows2,
  Search,
  Star,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSearchParams } from "react-router-dom";
import { apiDelete, apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { cn } from "@/lib/utils";

type EpistemicItem = { kind: string; label: string; detail: string };
type ClaimRow = {
  claim: string;
  evidence_mode: string;
  confidence: string;
  needs_human_judgment: boolean;
  needs_bench: boolean;
  needs_telescope_or_instrument: boolean;
  needs_formal_verification: boolean;
  needs_simulation_compute: boolean;
  falsifier: string | null;
  section_hint: string | null;
};
type AggregateNeeds = {
  needs_human_judgment?: boolean;
  needs_bench?: boolean;
  needs_telescope_or_instrument?: boolean;
  needs_formal_verification?: boolean;
  needs_simulation_compute?: boolean;
};
type EpistemicProfile = {
  primary_mode: string;
  knowing_requires: string[];
  still_needs_human_or_physical: EpistemicItem[];
  automation_readiness: string;
  summary: string;
  deep_summary?: string;
  analyzer?: string;
  evidence_signals?: Record<string, number>;
  claims?: ClaimRow[];
  aggregate_needs?: AggregateNeeds;
};
type Row = {
  arxiv_id: string;
  title: string;
  ingested_at: number;
  source: string;
  primary_mode?: string | null;
  claim_count?: number;
  aggregate_needs?: AggregateNeeds | null;
};
type Item = {
  arxiv_id: string;
  title: string;
  markdown: string;
  source: string;
  ingested_at: number;
  meta?: { epistemic_profile?: EpistemicProfile };
};

const MODES = [
  "",
  "formal_proof",
  "simulation",
  "computational",
  "observational_instrumental",
  "interventional_experiment",
  "mixed",
] as const;

type SortOption =
  | "ingested_desc"
  | "ingested_asc"
  | "title_asc"
  | "title_desc"
  | "claims_desc"
  | "arxiv_id_asc";

function flagBadges(c: ClaimRow) {
  const f: string[] = [];
  if (c.needs_bench) f.push("bench");
  if (c.needs_telescope_or_instrument) f.push("telescope");
  if (c.needs_formal_verification) f.push("formal");
  if (c.needs_simulation_compute) f.push("compute");
  if (c.needs_human_judgment) f.push("human");
  return f;
}

function EpistemicCard({ profile }: { profile: EpistemicProfile }) {
  const [showClaims, setShowClaims] = useState(false);
  const summary = profile.deep_summary || profile.summary;
  const hasClaims = (profile.claims?.length ?? 0) > 0;

  return (
    <div
      className="rounded-lg border border-border/50 bg-muted/20 p-4 text-sm space-y-3"
      data-testid="epistemic-card"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium capitalize px-2 py-0.5 rounded bg-primary/10 text-primary text-xs">
          {profile.primary_mode.replace(/_/g, " ")}
        </span>
        {profile.analyzer && (
          <span className="text-xs font-mono text-muted-foreground">
            {profile.analyzer}
          </span>
        )}
        {hasClaims && (
          <span className="text-[11px] rounded bg-secondary px-1.5 py-0.5 font-medium text-muted-foreground">
            {profile.claims?.length} claims
          </span>
        )}
      </div>

      <p className="text-sm text-muted-foreground/90 leading-relaxed">
        {summary}
      </p>

      {hasClaims && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowClaims(!showClaims)}
            className="flex items-center gap-1 text-sm text-primary hover:underline"
          >
            {showClaims ? "Hide" : "View"} claim table{" "}
            <ChevronDown
              className={cn(
                "h-3 w-3 transition-transform",
                showClaims && "rotate-180",
              )}
            />
          </button>
        </div>
      )}

      <AnimatePresence>
        {hasClaims && showClaims && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="overflow-x-auto border border-border/30 rounded-lg">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border/40 bg-muted/30">
                    <th className="py-1.5 px-2 font-medium">Claim</th>
                    <th className="py-1.5 px-2 font-medium">Mode</th>
                    <th className="py-1.5 px-2 font-medium">Needs</th>
                    <th className="py-1.5 px-2 font-medium">Falsifier</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.claims
                    ?.slice(0, showClaims ? undefined : 3)
                    .map((c) => (
                      <tr
                        key={`${c.claim}-${c.evidence_mode}`}
                        className="border-b border-border/20 align-top"
                      >
                        <td className="py-2 px-3 max-w-[200px] text-sm">
                          {c.claim}
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap capitalize text-sm">
                          {c.evidence_mode.replace(/_/g, " ")}
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex flex-wrap gap-1">
                            {flagBadges(c).map((f) => (
                              <span
                                key={f}
                                className="rounded bg-secondary px-1.5 text-xs"
                              >
                                {f}
                              </span>
                            ))}
                            {!flagBadges(c).length ? (
                              <span className="text-muted-foreground">
                                &mdash;
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td className="py-2 px-3 text-muted-foreground max-w-[160px] text-sm">
                          {c.falsifier || "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              {(profile.claims?.length ?? 0) > 3 && !showClaims && (
                <p className="text-xs text-muted-foreground text-center py-1.5">
                  +{(profile.claims?.length ?? 0) - 3} more claims
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-2 text-xs">
        <div>
          <span className="font-semibold text-muted-foreground">
            Knowing requires:{" "}
          </span>
          <span className="text-muted-foreground">
            {profile.knowing_requires.join("; ")}
          </span>
        </div>
        {profile.still_needs_human_or_physical.length > 0 && (
          <div>
            <span className="font-semibold text-muted-foreground">
              Still needs:{" "}
            </span>
            <span className="text-muted-foreground">
              {profile.still_needs_human_or_physical
                .map((i) => i.label)
                .join(", ")}
            </span>
          </div>
        )}
        <div className="text-muted-foreground">
          AI fit: {profile.automation_readiness.replace(/_/g, " ")}
        </div>
      </div>
    </div>
  );
}

function buildCorpusQuery(filters: {
  primary_mode: string;
  needs_bench: boolean | null;
  needs_telescope: boolean | null;
  needs_formal: boolean | null;
  has_deep_claims: boolean | null;
}) {
  const p = new URLSearchParams({ limit: "500" });
  if (filters.primary_mode) p.set("primary_mode", filters.primary_mode);
  if (filters.needs_bench !== null)
    p.set("needs_bench", String(filters.needs_bench));
  if (filters.needs_telescope !== null)
    p.set("needs_telescope_or_instrument", String(filters.needs_telescope));
  if (filters.needs_formal !== null)
    p.set("needs_formal_verification", String(filters.needs_formal));
  if (filters.has_deep_claims !== null)
    p.set("has_deep_claims", String(filters.has_deep_claims));
  return `/api/corpus?${p.toString()}`;
}

export function Depot() {
  const { log } = useLogger();
  const [params] = useSearchParams();
  const focus = params.get("focus");

  const [rows, setRows] = useState<Row[]>([]);
  const [filtered, setFiltered] = useState(false);
  const [pid, setPid] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [deepAnalyzing, setDeepAnalyzing] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Item | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [primaryMode, setPrimaryMode] = useState("");
  const [needsBench, setNeedsBench] = useState<boolean | null>(null);
  const [needsTelescope, setNeedsTelescope] = useState<boolean | null>(null);
  const [needsFormal, setNeedsFormal] = useState<boolean | null>(null);
  const [hasDeepClaims, setHasDeepClaims] = useState<boolean | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Sorting state
  const [sortBy, setSortBy] = useState<SortOption>("ingested_desc");

  // View & Layout mode (persisted to localStorage)
  const [viewMode, setViewMode] = useState<"list" | "card">(() => {
    return (
      (localStorage.getItem("depot_view_mode") as "list" | "card") || "card"
    );
  });
  const [layoutMode, setLayoutMode] = useState<"split" | "stacked">(() => {
    return (
      (localStorage.getItem("depot_layout_mode") as "split" | "stacked") ||
      "stacked"
    );
  });

  // Favorites state
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());

  const [readerTab, setReaderTab] = useState<"profile" | "text">("profile");
  const [fullscreen, setFullscreen] = useState(false);

  const loadFavorites = useCallback(async () => {
    try {
      const data = await apiGet<{ favorites: { arxiv_id: string }[] }>(
        "/api/favorites",
      );
      setFavoriteIds(new Set((data.favorites || []).map((f) => f.arxiv_id)));
    } catch {
      // Non-fatal
    }
  }, []);

  const toggleFavorite = async (
    arxivId: string,
    title?: string,
    e?: React.MouseEvent,
  ) => {
    if (e) e.stopPropagation();
    const isFav = favoriteIds.has(arxivId);
    setFavoriteIds((prev) => {
      const next = new Set(prev);
      if (isFav) next.delete(arxivId);
      else next.add(arxivId);
      return next;
    });
    try {
      if (isFav) {
        await apiDelete(`/api/favorites/${encodeURIComponent(arxivId)}`);
        log("info", `Removed ${arxivId} from favorites`);
      } else {
        await apiPost("/api/favorites", {
          arxiv_id: arxivId,
          title: title || null,
          note: null,
        });
        log("info", `Added ${arxivId} to favorites`);
      }
    } catch (err) {
      setFavoriteIds((prev) => {
        const next = new Set(prev);
        if (isFav) next.add(arxivId);
        else next.delete(arxivId);
        return next;
      });
      log("error", `Favorite failed: ${err}`);
    }
  };

  const refresh = useCallback(async () => {
    try {
      const path = buildCorpusQuery({
        primary_mode: primaryMode,
        needs_bench: needsBench,
        needs_telescope: needsTelescope,
        needs_formal: needsFormal,
        has_deep_claims: hasDeepClaims,
      });
      const data = await apiGet<{ ingested: Row[]; filtered?: boolean }>(path);
      setRows(data.ingested || []);
      setFiltered(Boolean(data.filtered));
    } catch (e) {
      log("error", String(e));
    }
  }, [
    log,
    primaryMode,
    needsBench,
    needsTelescope,
    needsFormal,
    hasDeepClaims,
  ]);

  const resetFilters = () => {
    setPrimaryMode("");
    setNeedsBench(null);
    setNeedsTelescope(null);
    setNeedsFormal(null);
    setHasDeepClaims(null);
    setSearchQuery("");
  };

  const activeFilterCount = [
    primaryMode !== "",
    needsBench !== null,
    needsTelescope !== null,
    needsFormal !== null,
    hasDeepClaims !== null,
    searchQuery.trim() !== "",
  ].filter(Boolean).length;

  const loadDetail = useCallback(
    async (arxivId: string) => {
      setLoadingDetail(true);
      try {
        const d = await apiGet<Item>(
          `/api/corpus/item?arxiv_id=${encodeURIComponent(arxivId)}`,
        );
        setDetail(d);
      } catch (e) {
        setDetail(null);
        log("error", String(e));
      } finally {
        setLoadingDetail(false);
      }
    },
    [log],
  );

  useEffect(() => {
    refresh();
    loadFavorites();
  }, [refresh, loadFavorites]);

  useEffect(() => {
    if (focus) {
      setSelected(focus);
      loadDetail(focus);
    }
  }, [focus, loadDetail]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    loadDetail(selected);
  }, [selected, loadDetail]);

  const handleViewModeChange = (mode: "list" | "card") => {
    setViewMode(mode);
    localStorage.setItem("depot_view_mode", mode);
  };

  const handleLayoutModeChange = (mode: "split" | "stacked") => {
    setLayoutMode(mode);
    localStorage.setItem("depot_layout_mode", mode);
  };

  async function ingest(deep = false) {
    if (deep) setAnalyzing(true);
    else setIngesting(true);
    try {
      const path = deep
        ? "/api/depot/ingest-analyze?deep=true"
        : "/api/depot/ingest";
      const r = await apiPost<Record<string, unknown>>(path, { paper_id: pid });
      log(
        "info",
        deep
          ? `Ingest+analyze ${JSON.stringify(r.epistemic_profile)}`
          : `Ingested ${JSON.stringify(r)}`,
      );
      setPid("");
      await refresh();
      if (r.arxiv_id) {
        setSelected(String(r.arxiv_id));
        await loadDetail(String(r.arxiv_id));
      }
    } catch (e) {
      log("error", String(e));
    } finally {
      setIngesting(false);
      setAnalyzing(false);
    }
  }

  async function deepAnalyze(forceRefresh = false) {
    const target = selected || pid;
    if (!target.trim()) return;
    setDeepAnalyzing(true);
    try {
      const q = forceRefresh ? "?force_refresh=true" : "";
      const r = await apiPost<{
        arxiv_id?: string;
        epistemic_profile?: EpistemicProfile;
        cached?: boolean;
      }>(`/api/depot/deep-analyze${q}`, { paper_id: target });
      log("info", r.cached ? "Deep profile (cached)" : "Deep profile saved");
      await refresh();
      if (r.arxiv_id) {
        setSelected(r.arxiv_id);
        await loadDetail(r.arxiv_id);
      }
    } catch (e) {
      log("error", String(e));
    } finally {
      setDeepAnalyzing(false);
    }
  }

  function cycleTriState(
    value: boolean | null,
    setter: (v: boolean | null) => void,
  ) {
    if (value === null) setter(true);
    else if (value === true) setter(false);
    else setter(null);
  }

  // Filter & Sort rows in memory
  const processedRows = useMemo(() => {
    let list = rows;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.arxiv_id.toLowerCase().includes(q) ||
          r.primary_mode?.toLowerCase().includes(q),
      );
    }
    return [...list].sort((a, b) => {
      switch (sortBy) {
        case "ingested_asc":
          return (a.ingested_at ?? 0) - (b.ingested_at ?? 0);
        case "ingested_desc":
          return (b.ingested_at ?? 0) - (a.ingested_at ?? 0);
        case "title_asc":
          return a.title.localeCompare(b.title);
        case "title_desc":
          return b.title.localeCompare(a.title);
        case "claims_desc":
          return (b.claim_count ?? 0) - (a.claim_count ?? 0);
        case "arxiv_id_asc":
          return a.arxiv_id.localeCompare(b.arxiv_id);
        default:
          return (b.ingested_at ?? 0) - (a.ingested_at ?? 0);
      }
    });
  }, [rows, searchQuery, sortBy]);

  const profile = detail?.meta?.epistemic_profile;

  // Render Reader view (reusable between inline and stacked)
  const renderReaderContent = (isInline = true) => {
    if (!selected) {
      return (
        <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
          <BookOpen className="h-10 w-10 stroke-1 text-muted-foreground/50 mb-3" />
          <p className="text-sm font-medium">No paper selected</p>
          <p className="text-xs text-muted-foreground/70 mt-1 max-w-xs">
            Select a paper from the list or card grid to view its epistemic
            profile and full text.
          </p>
        </div>
      );
    }

    if (loadingDetail) {
      return (
        <div className="py-16 text-center text-sm text-muted-foreground animate-pulse">
          Loading paper details...
        </div>
      );
    }

    if (!detail) {
      return (
        <div className="py-12 text-center text-sm text-muted-foreground">
          Could not load details for {selected}.
        </div>
      );
    }

    const isFav = favoriteIds.has(detail.arxiv_id);

    return (
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-border/40 pb-4">
          <div className="space-y-1 min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-primary font-semibold">
                {detail.arxiv_id}
              </span>
              <span className="text-xs text-muted-foreground">
                source: {detail.source}
              </span>
            </div>
            <h2 className="text-base font-semibold leading-snug">
              {detail.title}
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button
              variant={isFav ? "default" : "outline"}
              size="sm"
              onClick={(e) => toggleFavorite(detail.arxiv_id, detail.title, e)}
              className={cn(
                "gap-1.5 text-xs transition-colors",
                isFav
                  ? "bg-amber-500 hover:bg-amber-600 text-white border-transparent"
                  : "hover:text-amber-500",
              )}
            >
              <Star className={cn("h-3.5 w-3.5", isFav && "fill-current")} />
              {isFav ? "Favorited" : "Favorite"}
            </Button>

            <a
              href={`https://arxiv.org/abs/${detail.arxiv_id}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs border border-border/60 hover:bg-muted/50 rounded-md px-2.5 py-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              arXiv <ExternalLink className="h-3 w-3" />
            </a>

            <div className="flex rounded-lg border border-border/40 overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => setReaderTab("profile")}
                className={cn(
                  "px-3 py-1.5 transition-colors font-medium",
                  readerTab === "profile"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground bg-muted/20",
                )}
              >
                Profile
              </button>
              <button
                type="button"
                onClick={() => setReaderTab("text")}
                className={cn(
                  "px-3 py-1.5 transition-colors font-medium",
                  readerTab === "text"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground bg-muted/20",
                )}
              >
                Full text
              </button>
            </div>

            <Button
              size="sm"
              variant="secondary"
              disabled={deepAnalyzing}
              onClick={() => deepAnalyze(false)}
            >
              {deepAnalyzing ? "Deep..." : "Deep analyze"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={deepAnalyzing}
              onClick={() => deepAnalyze(true)}
            >
              Re-run
            </Button>
            <button
              type="button"
              onClick={() => setFullscreen(!fullscreen)}
              className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground border border-border/40"
              title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </button>
            {layoutMode === "stacked" && (
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground border border-border/40"
                title="Close reader"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {readerTab === "profile" &&
          (profile ? (
            <EpistemicCard profile={profile} />
          ) : (
            <div className="rounded-lg border border-dashed border-border/60 p-8 text-center space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                No epistemic profile computed yet.
              </p>
              <p className="text-xs text-muted-foreground/70">
                Click &quot;Deep analyze&quot; above to run claims extraction
                and epistemic profiling via Ollama/MCP.
              </p>
            </div>
          ))}

        {readerTab === "text" && (
          <div
            className={cn(
              "text-sm leading-relaxed max-w-none overflow-y-auto border border-border/40 rounded-lg p-5 bg-background/50 [&_a]:text-primary [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm [&_h1]:font-bold [&_h2]:font-semibold [&_h3]:font-semibold [&_pre]:bg-muted/50 [&_pre]:p-3 [&_pre]:rounded-md [&_code]:text-xs",
              isInline ? "max-h-[600px]" : "max-h-[800px]",
            )}
          >
            <ReactMarkdown>{detail.markdown}</ReactMarkdown>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="depot-page">
      <PageHero
        eyebrow="Your library"
        title="Depot"
        lead="Ingested papers, epistemic profiles, and full text with flexible layout."
        size="default"
      />

      {/* Ingest Card */}
      <Card data-testid="depot-ingest">
        <div className="flex items-center justify-between">
          <CardTitle>Ingest paper</CardTitle>
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
          </Button>
        </div>
        <div className="mt-3 flex flex-col sm:flex-row gap-2">
          <Input
            value={pid}
            onChange={(e) => setPid(e.target.value)}
            placeholder="arXiv id or URL (e.g. 2401.00001)"
            className="flex-1"
          />
          <div className="flex gap-2">
            <Button
              onClick={() => ingest(false)}
              disabled={ingesting || analyzing || deepAnalyzing}
            >
              {ingesting ? "Fetching..." : "Ingest"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => ingest(true)}
              disabled={ingesting || analyzing || deepAnalyzing}
            >
              {analyzing ? "Analyzing..." : "Ingest + analyze"}
            </Button>
          </div>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Deep analyze needs Ollama or MCP sampling. Ingest extracts full text
          and creates FTS/vector chunks.
        </p>
      </Card>

      {/* Control Bar: Search, Filters, Sorting, View & Layout toggles */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-muted/20 p-3 rounded-lg border border-border/40">
        {/* Left: Search input */}
        <div className="flex items-center gap-2 flex-1 max-w-md relative">
          <Search className="h-4 w-4 text-muted-foreground absolute left-3 pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search papers by title, ID, or mode..."
            className="pl-9 pr-8 text-xs h-9 bg-background"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Right: Controls cluster */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Filters Toggle Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            data-testid="depot-filters-toggle"
            className={cn(
              "h-9 gap-1.5 text-xs",
              (filtered || activeFilterCount > 0) &&
                "border-primary text-primary",
            )}
          >
            <Filter className="h-3.5 w-3.5" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
                {activeFilterCount}
              </span>
            )}
            <ChevronDown
              className={cn(
                "h-3 w-3 transition-transform ml-0.5",
                showFilters && "rotate-180",
              )}
            />
          </Button>

          {/* Reset Filters Button */}
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground gap-1"
              title="Reset all filters and search"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </Button>
          )}

          {/* Sort Selector */}
          <div className="flex items-center gap-1 border border-border/60 rounded-md bg-background px-2 h-9 text-xs">
            <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="bg-transparent border-none text-xs focus:outline-none cursor-pointer pr-1"
            >
              <option value="ingested_desc">Newest First</option>
              <option value="ingested_asc">Oldest First</option>
              <option value="title_asc">Title (A → Z)</option>
              <option value="title_desc">Title (Z → A)</option>
              <option value="claims_desc">Most Claims</option>
              <option value="arxiv_id_asc">arXiv ID</option>
            </select>
          </div>

          {/* View Mode Switch (List vs Card) */}
          <div className="flex rounded-md border border-border/60 bg-background overflow-hidden h-9">
            <button
              type="button"
              onClick={() => handleViewModeChange("card")}
              className={cn(
                "px-2.5 flex items-center gap-1 text-xs transition-colors",
                viewMode === "card"
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
              title="Card Grid View"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Cards</span>
            </button>
            <button
              type="button"
              onClick={() => handleViewModeChange("list")}
              className={cn(
                "px-2.5 flex items-center gap-1 text-xs transition-colors border-l border-border/40",
                viewMode === "list"
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
              title="Compact List View"
            >
              <List className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">List</span>
            </button>
          </div>

          {/* Layout Mode Switch (Split vs Stacked) */}
          <div className="flex rounded-md border border-border/60 bg-background overflow-hidden h-9">
            <button
              type="button"
              onClick={() => handleLayoutModeChange("stacked")}
              className={cn(
                "px-2.5 flex items-center gap-1 text-xs transition-colors",
                layoutMode === "stacked"
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
              title="Stacked layout: Full width list on top, Reader below"
            >
              <Rows2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Stacked</span>
            </button>
            <button
              type="button"
              onClick={() => handleLayoutModeChange("split")}
              className={cn(
                "px-2.5 flex items-center gap-1 text-xs transition-colors border-l border-border/40",
                layoutMode === "split"
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
              title="Split layout: Side-by-side panels"
            >
              <Columns2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Split</span>
            </button>
          </div>

          <p className="text-xs text-muted-foreground ml-1">
            {processedRows.length} of {rows.length} paper
            {rows.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Collapsible Filter Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <Card className="bg-muted/10 border-border/50">
              <div className="flex flex-wrap gap-3 items-center text-xs">
                <label className="flex items-center gap-1.5 font-medium">
                  Epistemic Mode:
                  <select
                    className="rounded border border-border bg-background px-2.5 py-1 text-xs font-normal"
                    value={primaryMode}
                    onChange={(e) => setPrimaryMode(e.target.value)}
                  >
                    {MODES.map((m) => (
                      <option key={m || "all"} value={m}>
                        {m ? m.replace(/_/g, " ") : "All modes"}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="flex items-center gap-1 text-muted-foreground">
                  <span>Requirements:</span>
                  {(["bench", "telescope", "formal", "claims"] as const).map(
                    (label) => {
                      const val =
                        label === "bench"
                          ? needsBench
                          : label === "telescope"
                            ? needsTelescope
                            : label === "formal"
                              ? needsFormal
                              : hasDeepClaims;
                      const setter =
                        label === "bench"
                          ? setNeedsBench
                          : label === "telescope"
                            ? setNeedsTelescope
                            : label === "formal"
                              ? setNeedsFormal
                              : setHasDeepClaims;
                      return (
                        <Button
                          variant={val !== null ? "default" : "outline"}
                          size="sm"
                          type="button"
                          onClick={() => cycleTriState(val, setter)}
                          key={label}
                          className={cn(
                            "h-7 text-xs px-2",
                            val === true &&
                              "bg-primary text-primary-foreground",
                            val === false && "bg-muted text-muted-foreground",
                          )}
                        >
                          {label}: {val === null ? "any" : val ? "yes" : "no"}
                        </Button>
                      );
                    },
                  )}
                </div>

                {activeFilterCount > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={resetFilters}
                    className="h-7 text-xs ml-auto text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="h-3 w-3 mr-1" /> Reset all
                  </Button>
                )}
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area based on Layout Mode */}
      {layoutMode === "split" ? (
        /* Split Layout (Side-by-Side) */
        <div className="grid gap-6 lg:grid-cols-12" data-testid="depot-panels">
          <Card className="lg:col-span-5 min-h-[400px] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-border/40">
              <CardTitle>Papers</CardTitle>
              <span className="text-xs text-muted-foreground">
                {processedRows.length} items
              </span>
            </div>

            <div className="mt-3 flex-1 max-h-[640px] overflow-y-auto space-y-1.5 pr-1">
              {processedRows.length === 0 && (
                <div className="py-12 text-center text-xs text-muted-foreground">
                  {rows.length === 0
                    ? "No papers ingested yet. Ingest an arXiv ID above."
                    : "No papers match the current filters or search query."}
                </div>
              )}

              {viewMode === "card"
                ? processedRows.map((r) => {
                    const isFav = favoriteIds.has(r.arxiv_id);
                    const isSelected = selected === r.arxiv_id;
                    return (
                      <div
                        key={r.arxiv_id}
                        className={cn(
                          "rounded-lg border p-3 transition-all text-left",
                          isSelected
                            ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary/30"
                            : "border-border/60 hover:border-border hover:bg-muted/30",
                        )}
                      >
                        <div className="flex items-center justify-between gap-1.5">
                          <button
                            type="button"
                            onClick={() => setSelected(r.arxiv_id)}
                            className="font-mono text-xs font-semibold text-primary hover:underline text-left"
                          >
                            {r.arxiv_id}
                          </button>
                          <button
                            type="button"
                            onClick={(e) =>
                              toggleFavorite(r.arxiv_id, r.title, e)
                            }
                            className="p-1 text-muted-foreground hover:text-amber-500 transition-colors"
                            title={
                              isFav ? "Remove favorite" : "Add to favorites"
                            }
                          >
                            <Star
                              className={cn(
                                "h-4 w-4",
                                isFav && "fill-amber-500 text-amber-500",
                              )}
                            />
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelected(r.arxiv_id)}
                          className="text-xs font-medium line-clamp-2 mt-1 text-left w-full hover:text-primary transition-colors"
                        >
                          {r.title}
                        </button>
                        <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[11px]">
                          {r.primary_mode && (
                            <span className="capitalize text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded font-medium">
                              {r.primary_mode.replace(/_/g, " ")}
                            </span>
                          )}
                          {(r.claim_count ?? 0) > 0 && (
                            <span className="text-primary font-medium bg-primary/10 px-1.5 py-0.5 rounded">
                              {r.claim_count} claims
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                : processedRows.map((r) => {
                    const isFav = favoriteIds.has(r.arxiv_id);
                    const isSelected = selected === r.arxiv_id;
                    return (
                      <div
                        key={r.arxiv_id}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-2.5 py-2 transition-colors text-xs border border-transparent",
                          isSelected
                            ? "bg-primary/10 border-primary/30"
                            : "hover:bg-muted/40",
                        )}
                      >
                        <button
                          type="button"
                          onClick={(e) =>
                            toggleFavorite(r.arxiv_id, r.title, e)
                          }
                          className="shrink-0 text-muted-foreground hover:text-amber-500"
                          title={isFav ? "Remove favorite" : "Add to favorites"}
                        >
                          <Star
                            className={cn(
                              "h-3.5 w-3.5",
                              isFav && "fill-amber-500 text-amber-500",
                            )}
                          />
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelected(r.arxiv_id)}
                          className="flex items-center gap-2 min-w-0 flex-1 text-left hover:text-primary transition-colors"
                        >
                          <span className="font-mono text-[11px] text-primary shrink-0 font-semibold">
                            {r.arxiv_id}
                          </span>
                          <span className="truncate flex-1 font-medium">
                            {r.title}
                          </span>
                        </button>
                        {r.primary_mode && (
                          <span className="hidden sm:inline text-[10px] capitalize text-muted-foreground bg-muted/50 px-1 py-0.5 rounded shrink-0">
                            {r.primary_mode.replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                    );
                  })}
            </div>
          </Card>

          {/* Reader Panel */}
          <Card
            className="lg:col-span-7 min-h-[400px]"
            data-testid="depot-reader"
          >
            {renderReaderContent(true)}
          </Card>
        </div>
      ) : (
        /* Stacked Layout: Papers Top (Full width Cards/List), Reader Below */
        <div className="space-y-6">
          {/* Papers Container */}
          <Card>
            <div className="flex items-center justify-between pb-3 border-b border-border/40">
              <CardTitle>Papers in Depot</CardTitle>
              <span className="text-xs text-muted-foreground">
                Showing {processedRows.length} of {rows.length} papers
              </span>
            </div>

            {processedRows.length === 0 && (
              <div className="py-16 text-center text-sm text-muted-foreground">
                {rows.length === 0
                  ? "No papers ingested yet. Use the Ingest form above to import arXiv papers."
                  : "No papers match the current filters or search query."}
              </div>
            )}

            {viewMode === "card" ? (
              /* Card Grid View */
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {processedRows.map((r) => {
                  const isFav = favoriteIds.has(r.arxiv_id);
                  const isSelected = selected === r.arxiv_id;
                  return (
                    <div
                      key={r.arxiv_id}
                      className={cn(
                        "rounded-lg border p-4 flex flex-col justify-between transition-all hover:shadow-sm",
                        isSelected
                          ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/40"
                          : "border-border/60 hover:border-border hover:bg-muted/20",
                      )}
                    >
                      <div className="space-y-2">
                        <div className="flex items-start justify-between gap-1">
                          <button
                            type="button"
                            onClick={() => setSelected(r.arxiv_id)}
                            className="font-mono text-xs font-bold text-primary hover:underline text-left"
                          >
                            {r.arxiv_id}
                          </button>
                          <button
                            type="button"
                            onClick={(e) =>
                              toggleFavorite(r.arxiv_id, r.title, e)
                            }
                            className="p-1 -mr-1 -mt-1 text-muted-foreground hover:text-amber-500 transition-colors"
                            title={
                              isFav ? "Remove favorite" : "Add to favorites"
                            }
                          >
                            <Star
                              className={cn(
                                "h-4 w-4",
                                isFav && "fill-amber-500 text-amber-500",
                              )}
                            />
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelected(r.arxiv_id)}
                          className="text-sm font-semibold line-clamp-3 leading-snug text-left w-full hover:text-primary transition-colors"
                        >
                          {r.title}
                        </button>
                      </div>

                      <div className="mt-4 pt-3 border-t border-border/30 space-y-2">
                        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                          {r.primary_mode ? (
                            <span className="capitalize text-muted-foreground bg-muted/80 px-1.5 py-0.5 rounded font-medium">
                              {r.primary_mode.replace(/_/g, " ")}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/60 text-[10px]">
                              unprofiled
                            </span>
                          )}
                          {(r.claim_count ?? 0) > 0 && (
                            <span className="text-primary font-medium bg-primary/10 px-1.5 py-0.5 rounded">
                              {r.claim_count} claims
                            </span>
                          )}
                          <span className="text-muted-foreground/60 ml-auto text-[10px]">
                            {r.source}
                          </span>
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <Button
                            size="sm"
                            variant={isSelected ? "default" : "outline"}
                            className="h-7 text-xs px-3"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(r.arxiv_id);
                            }}
                          >
                            <BookOpen className="h-3 w-3 mr-1" />
                            {isSelected ? "Reading" : "Read"}
                          </Button>
                          <a
                            href={`https://arxiv.org/abs/${r.arxiv_id}`}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 hover:underline"
                          >
                            arXiv <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* List View */
              <div className="mt-4 divide-y divide-border/30 border border-border/40 rounded-lg overflow-hidden">
                {processedRows.map((r) => {
                  const isFav = favoriteIds.has(r.arxiv_id);
                  const isSelected = selected === r.arxiv_id;
                  return (
                    <div
                      key={r.arxiv_id}
                      className={cn(
                        "flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 transition-colors text-xs",
                        isSelected
                          ? "bg-primary/10 font-medium"
                          : "hover:bg-muted/30",
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <button
                          type="button"
                          onClick={(e) =>
                            toggleFavorite(r.arxiv_id, r.title, e)
                          }
                          className="shrink-0 text-muted-foreground hover:text-amber-500"
                          title={isFav ? "Remove favorite" : "Add to favorites"}
                        >
                          <Star
                            className={cn(
                              "h-4 w-4",
                              isFav && "fill-amber-500 text-amber-500",
                            )}
                          />
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelected(r.arxiv_id)}
                          className="flex items-center gap-2 min-w-0 flex-1 text-left hover:text-primary transition-colors"
                        >
                          <span className="font-mono text-xs text-primary font-bold shrink-0">
                            {r.arxiv_id}
                          </span>
                          <span className="truncate text-sm font-medium">
                            {r.title}
                          </span>
                        </button>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 pl-6 sm:pl-0">
                        {r.primary_mode && (
                          <span className="text-[11px] capitalize text-muted-foreground bg-muted/60 px-2 py-0.5 rounded">
                            {r.primary_mode.replace(/_/g, " ")}
                          </span>
                        )}
                        {(r.claim_count ?? 0) > 0 && (
                          <span className="text-[11px] text-primary bg-primary/10 px-1.5 py-0.5 rounded font-medium">
                            {r.claim_count} claims
                          </span>
                        )}
                        <Button
                          size="sm"
                          variant={isSelected ? "default" : "outline"}
                          className="h-7 text-xs px-2.5"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelected(r.arxiv_id);
                          }}
                        >
                          {isSelected ? "Reading" : "Read"}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Reader Below (Full width) */}
          {selected && (
            <Card
              data-testid="depot-reader-stacked"
              className="border-primary/50 shadow-md"
            >
              {renderReaderContent(false)}
            </Card>
          )}
        </div>
      )}

      {/* Fullscreen Reader Modal */}
      {fullscreen && detail && (
        <div
          className="fixed inset-0 z-50 bg-background flex flex-col"
          data-testid="depot-fullscreen"
        >
          <div className="flex items-center justify-between border-b border-border/40 px-6 py-3 bg-muted/20">
            <div className="min-w-0 flex-1 mr-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-primary font-bold">
                  {detail.arxiv_id}
                </span>
                <button
                  type="button"
                  onClick={(e) =>
                    toggleFavorite(detail.arxiv_id, detail.title, e)
                  }
                  className="p-1 text-muted-foreground hover:text-amber-500 transition-colors"
                >
                  <Star
                    className={cn(
                      "h-4 w-4",
                      favoriteIds.has(detail.arxiv_id) &&
                        "fill-amber-500 text-amber-500",
                    )}
                  />
                </button>
              </div>
              <h2 className="text-base font-semibold truncate mt-0.5">
                {detail.title}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg border border-border/40 overflow-hidden text-xs">
                <button
                  type="button"
                  onClick={() => setReaderTab("profile")}
                  className={cn(
                    "px-3 py-1.5 transition-colors font-medium",
                    readerTab === "profile"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground bg-muted/30",
                  )}
                >
                  Profile
                </button>
                <button
                  type="button"
                  onClick={() => setReaderTab("text")}
                  className={cn(
                    "px-3 py-1.5 transition-colors font-medium",
                    readerTab === "text"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground bg-muted/30",
                  )}
                >
                  Full text
                </button>
              </div>
              <button
                type="button"
                onClick={() => setFullscreen(false)}
                className="p-2 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground border border-border/40"
                title="Exit fullscreen"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-5xl mx-auto w-full">
            {readerTab === "profile" &&
              (profile ? (
                <EpistemicCard profile={profile} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No epistemic profile.
                </p>
              ))}
            {readerTab === "text" && (
              <div className="text-sm leading-relaxed max-w-none [&_a]:text-primary [&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base [&_h1]:font-bold [&_h2]:font-semibold [&_pre]:bg-muted/50 [&_pre]:p-4 [&_pre]:rounded-lg">
                <ReactMarkdown>{detail.markdown}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
