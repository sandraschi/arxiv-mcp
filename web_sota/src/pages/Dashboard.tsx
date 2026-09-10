import {
  Activity,
  ArrowRight,
  BookMarked,
  BrainCircuit,
  Clock,
  Database,
  ExternalLink,
  Flame,
  Globe,
  Heart,
  Layers,
  Library,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "@/api/client";
import { LlmOnboarding } from "@/components/LlmOnboarding";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";
import { useBackendStore } from "@/lib/store";

type Health = { status: string; service: string };
type Stats = {
  papers: number;
  favorites: number;
  chunks: number;
  data_dir: string;
};
type RagStatus = {
  available: boolean;
  enabled: boolean;
  backend?: string;
  model?: string;
  indexed_chunks?: number;
};
type Diagnostics = {
  tool_count: number;
  uptime_seconds: number;
  version: string;
};
type IngestedPaper = {
  arxiv_id: string;
  title: string;
  ingested_at: number;
  primary_mode?: string;
  claim_count?: number;
};
type FavoriteItem = {
  arxiv_id: string;
  title: string | null;
};
type PipelineStatus = {
  healthy: boolean;
  service: string;
};

const RETRY_DELAYS = [1, 2, 4, 8, 16];

function retryDelay(attempt: number): number {
  return attempt < RETRY_DELAYS.length ? RETRY_DELAYS[attempt] : 30;
}

function formatUptime(seconds: number): string {
  if (!seconds || seconds < 60) return `${seconds || 0}s`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return `${h}h ${remM}m`;
}

export function Dashboard() {
  const { log } = useLogger();
  const navigate = useNavigate();
  const setOnline = useBackendStore((s) => s.setOnline);

  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [rag, setRag] = useState<RagStatus | null>(null);
  const [diag, setDiag] = useState<Diagnostics | null>(null);
  const [recentPapers, setRecentPapers] = useState<IngestedPaper[]>([]);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  // Quick Action States
  const [quickQuery, setQuickQuery] = useState("");
  const [quickIngestId, setQuickIngestId] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<{
    text: string;
    err: boolean;
  } | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [h, s, r, d, c, f, p] = await Promise.all([
        apiGet<Health>("/api/health"),
        apiGet<Stats>("/api/stats"),
        apiGet<RagStatus>("/api/depot/rag/status").catch(() => null),
        apiGet<Diagnostics>("/api/v1/diagnostics").catch(() => null),
        apiGet<{ ingested: IngestedPaper[] }>("/api/corpus?limit=6").catch(
          () => ({ ingested: [] }),
        ),
        apiGet<{ favorites: FavoriteItem[] }>("/api/favorites?limit=6").catch(
          () => ({ favorites: [] }),
        ),
        apiGet<PipelineStatus>("/api/pipeline/liveness").catch(() => null),
      ]);

      setHealth(h);
      setStats(s);
      setRag(r);
      setDiag(d);
      setRecentPapers(c.ingested || []);
      setFavorites(f.favorites || []);
      setPipeline(p);

      setAttempt(0);
      setOnline(true);
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      setErr(m);
      setHealth(null);
      setStats(null);
      setOnline(false);
      log("error", m);
    }
  }, [log, setOnline]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!err) return;
    const timer = setTimeout(() => {
      setAttempt((a) => a + 1);
      void load();
    }, retryDelay(attempt) * 1000);
    return () => clearTimeout(timer);
  }, [err, attempt, load]);

  const handleQuickSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickQuery.trim()) return;
    navigate(`/search?q=${encodeURIComponent(quickQuery.trim())}`);
  };

  const handleQuickIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = quickIngestId.trim();
    if (!id) return;
    setIngesting(true);
    setIngestMsg(null);
    try {
      await apiPost("/api/depot/ingest", { paper_id: id });
      setIngestMsg({ text: `Successfully ingested ${id}!`, err: false });
      setQuickIngestId("");
      void load();
    } catch (error) {
      setIngestMsg({ text: `Failed: ${String(error)}`, err: true });
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="dashboard">
      {/* Compact Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-mono font-bold text-xs border border-primary/20">
            aX
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none flex items-center gap-2">
              arXiv Intelligence Depot
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border/50">
                {diag?.version ? `v${diag.version}` : "v0.7.0"}
              </span>
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              High-density arXiv pipeline · Port 10770 (REST/MCP) · Port 10771
              (Web)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/40 border border-border/40 font-mono">
            <span
              className={`h-2 w-2 rounded-full ${
                health ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span>{health ? "LIVE" : "OFFLINE"}</span>
          </div>

          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => void load()}
            title="Refresh KPIs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>

          <Button size="sm" variant="default" className="h-7 text-xs" asChild>
            <Link to="/search">
              <Search className="h-3 w-3 mr-1" /> Search arXiv
            </Link>
          </Button>
        </div>
      </div>

      {err && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300 flex items-center justify-between">
          <span>Backend offline or unreachable on port 10770: {err}</span>
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-[11px]"
            onClick={() => void load()}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Dense KPI Grid (6 Cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <Link to="/depot" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">Depot Papers</span>
              <Library className="h-3.5 w-3.5 text-primary" />
            </div>
            <p className="text-xl font-bold font-mono tracking-tight mt-1 text-foreground">
              {stats?.papers ?? "—"}
            </p>
            <span className="text-[10px] text-muted-foreground mt-0.5 block truncate">
              Stored in SQLite FTS
            </span>
          </Card>
        </Link>

        <Link to="/semantic" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">RAG Chunks</span>
              <Database className="h-3.5 w-3.5 text-indigo-400" />
            </div>
            <p className="text-xl font-bold font-mono tracking-tight mt-1 text-foreground">
              {stats?.chunks ?? "—"}
            </p>
            <span className="text-[10px] text-muted-foreground mt-0.5 block truncate">
              {rag?.indexed_chunks
                ? `${rag.indexed_chunks} LanceDB vectors`
                : "Vector index ready"}
            </span>
          </Card>
        </Link>

        <Link to="/favorites" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">Favorites</span>
              <Heart className="h-3.5 w-3.5 text-rose-400" />
            </div>
            <p className="text-xl font-bold font-mono tracking-tight mt-1 text-foreground">
              {stats?.favorites ?? "—"}
            </p>
            <span className="text-[10px] text-muted-foreground mt-0.5 block truncate">
              Starred preprints
            </span>
          </Card>
        </Link>

        <Link to="/tools" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">MCP Tools</span>
              <Terminal className="h-3.5 w-3.5 text-amber-400" />
            </div>
            <p className="text-xl font-bold font-mono tracking-tight mt-1 text-foreground">
              {diag?.tool_count ?? "49"}
            </p>
            <span className="text-[10px] text-muted-foreground mt-0.5 block truncate">
              FastMCP 3.2+ tools
            </span>
          </Card>
        </Link>

        <Link to="/semantic" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">RAG Status</span>
              <BrainCircuit className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <p className="text-sm font-bold font-mono tracking-tight mt-1.5 text-foreground flex items-center gap-1">
              <span
                className={`h-2 w-2 rounded-full ${
                  rag?.enabled ? "bg-emerald-400" : "bg-muted-foreground"
                }`}
              />
              {rag?.enabled ? "Hybrid Active" : "FTS Only"}
            </p>
            <span className="text-[10px] text-muted-foreground mt-1 block truncate">
              {rag?.backend || "fastembed"} ·{" "}
              {rag?.model?.split("/")[1] || "bge-small"}
            </span>
          </Card>
        </Link>

        <Link to="/logs" className="block group">
          <Card className="p-3 transition-colors hover:border-primary/40 bg-card/60">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium">Uptime / Health</span>
              <Activity className="h-3.5 w-3.5 text-cyan-400" />
            </div>
            <p className="text-xl font-bold font-mono tracking-tight mt-1 text-foreground">
              {diag?.uptime_seconds
                ? formatUptime(diag.uptime_seconds)
                : "100%"}
            </p>
            <span className="text-[10px] text-emerald-400 mt-0.5 block truncate font-medium">
              {pipeline?.healthy ? "✓ Pipeline Healthy" : "System Running"}
            </span>
          </Card>
        </Link>
      </div>

      {/* Quick Utility Strip (Search + Instant Ingest) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
        {/* Quick Search */}
        <form
          onSubmit={handleQuickSearch}
          className="md:col-span-7 flex items-center gap-2 p-2.5 rounded-xl border border-border/60 bg-muted/20"
        >
          <Search className="h-4 w-4 text-muted-foreground ml-1 shrink-0" />
          <Input
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            placeholder="Quick search arXiv (e.g. quantum circuits, LLM reasoning, robotics)..."
            className="h-8 text-xs bg-background/80 border-border/50 focus-visible:ring-1"
          />
          <Button type="submit" size="sm" className="h-8 px-3 text-xs shrink-0">
            Search
          </Button>
        </form>

        {/* Quick Ingest by arXiv ID */}
        <form
          onSubmit={handleQuickIngest}
          className="md:col-span-5 flex items-center gap-2 p-2.5 rounded-xl border border-border/60 bg-muted/20"
        >
          <Plus className="h-4 w-4 text-primary ml-1 shrink-0" />
          <Input
            value={quickIngestId}
            onChange={(e) => setQuickIngestId(e.target.value)}
            placeholder="Quick Ingest arXiv ID (e.g. 2503.05628)..."
            className="h-8 text-xs font-mono bg-background/80 border-border/50 focus-visible:ring-1"
          />
          <Button
            type="submit"
            size="sm"
            variant="secondary"
            disabled={ingesting || !quickIngestId.trim()}
            className="h-8 px-3 text-xs shrink-0"
          >
            {ingesting ? "Pulling..." : "Ingest"}
          </Button>
        </form>
      </div>

      {ingestMsg && (
        <div
          className={`text-xs px-3 py-1.5 rounded-md ${
            ingestMsg.err
              ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
              : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
          }`}
        >
          {ingestMsg.text}
        </div>
      )}

      {/* Main Dense Grid: Quick Tasks, Recent Papers, Quick Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left Column: Fast Task Launchers & Quick Links (7 Cols) */}
        <div className="lg:col-span-7 space-y-3">
          {/* Quick Task Hub */}
          <Card className="p-3.5 space-y-3 bg-card/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" /> Core Workflows
              </span>
              <span className="text-[11px] text-muted-foreground">
                One-click navigation
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <Link
                to="/search"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Search className="h-4 w-4 text-sky-400" />
                  <span className="text-xs font-medium">Discovery</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  Multi-server preprint search
                </span>
              </Link>

              <Link
                to="/depot"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Library className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-medium">Depot Reader</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  Stacked & full-text reader
                </span>
              </Link>

              <Link
                to="/semantic"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <BookMarked className="h-4 w-4 text-indigo-400" />
                  <span className="text-xs font-medium">Hybrid RAG</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  BM25 + LanceDB vectors
                </span>
              </Link>

              <Link
                to="/favorites"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Heart className="h-4 w-4 text-rose-400" />
                  <span className="text-xs font-medium">Favorites</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  Direct bookmarks & notes
                </span>
              </Link>

              <Link
                to="/sweeps"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Flame className="h-4 w-4 text-amber-400" />
                  <span className="text-xs font-medium">Sweeps</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  Batch topic monitoring
                </span>
              </Link>

              <Link
                to="/anthropic"
                className="flex flex-col p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/30 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Globe className="h-4 w-4 text-teal-400" />
                  <span className="text-xs font-medium">Lab Blogs</span>
                </div>
                <span className="text-[11px] text-muted-foreground line-clamp-1">
                  Anthropic & DeepMind feeds
                </span>
              </Link>
            </div>
          </Card>

          {/* Quick Subject Category Launchers */}
          <Card className="p-3.5 space-y-2.5 bg-card/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-primary" /> Fast Topic
                Queries
              </span>
              <Link
                to="/search"
                className="text-[11px] text-primary hover:underline"
              >
                All Categories →
              </Link>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {[
                { label: "AI & Machine Learning", q: "cs.AI,cs.LG" },
                { label: "Robotics", q: "cs.RO" },
                { label: "Computer Vision", q: "cs.CV" },
                { label: "NLP & LLMs", q: "cs.CL" },
                { label: "Quantum Physics", q: "quant-ph" },
                { label: "Cryptography", q: "cs.CR" },
                { label: "BioRxiv Genetics", q: "genetics" },
                { label: "Formal Logic", q: "cs.LO" },
              ].map((cat) => (
                <button
                  key={cat.label}
                  type="button"
                  onClick={() =>
                    navigate(`/search?q=${encodeURIComponent(cat.q)}`)
                  }
                  className="text-xs px-2.5 py-1 rounded-md bg-muted/40 hover:bg-primary/10 hover:text-primary hover:border-primary/30 border border-border/40 transition-colors text-left font-mono"
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </Card>

          <LlmOnboarding mode="banner" />
        </div>

        {/* Right Column: Recent Activity & Quick Ingested List (5 Cols) */}
        <div className="lg:col-span-5 space-y-3">
          {/* Ingested Depot Papers Feed */}
          <Card className="p-3.5 space-y-2.5 bg-card/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" /> Recent Ingested
                Papers
              </span>
              <Link
                to="/depot"
                className="text-[11px] text-primary hover:underline"
              >
                View all ({stats?.papers || 0}) →
              </Link>
            </div>

            {recentPapers.length === 0 ? (
              <p className="text-xs text-muted-foreground py-3 text-center">
                No papers ingested yet. Use Quick Ingest above or search arXiv.
              </p>
            ) : (
              <div className="space-y-1.5">
                {recentPapers.map((paper) => (
                  <div
                    key={paper.arxiv_id}
                    className="flex items-start justify-between gap-2 p-2 rounded-lg bg-background/50 border border-border/40 hover:border-primary/30 transition-colors group"
                  >
                    <div className="min-w-0 flex-1">
                      <Link
                        to={`/depot?focus=${encodeURIComponent(paper.arxiv_id)}`}
                        className="text-xs font-medium text-foreground hover:text-primary line-clamp-1 block"
                        title={paper.title}
                      >
                        {paper.title || paper.arxiv_id}
                      </Link>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono mt-0.5">
                        <span className="text-primary/90 font-medium">
                          {paper.arxiv_id}
                        </span>
                        {paper.primary_mode && (
                          <span className="px-1 rounded bg-muted/80">
                            {paper.primary_mode.replace(/_/g, " ")}
                          </span>
                        )}
                        {typeof paper.claim_count === "number" && (
                          <span>{paper.claim_count} claims</span>
                        )}
                      </div>
                    </div>
                    <Link
                      to={`/depot?focus=${encodeURIComponent(paper.arxiv_id)}`}
                      className="p-1 rounded text-muted-foreground hover:text-foreground shrink-0 mt-0.5"
                      title="Read in Depot"
                    >
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Quick Saved Favorites Preview */}
          <Card className="p-3.5 space-y-2 bg-card/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Heart className="h-3.5 w-3.5 text-rose-400" /> Starred
                Favorites
              </span>
              <Link
                to="/favorites"
                className="text-[11px] text-primary hover:underline"
              >
                All ({stats?.favorites || 0}) →
              </Link>
            </div>

            {favorites.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 text-center">
                No favorites saved yet.
              </p>
            ) : (
              <div className="space-y-1">
                {favorites.slice(0, 4).map((fav) => (
                  <div
                    key={fav.arxiv_id}
                    className="flex items-center justify-between gap-2 p-1.5 rounded-md hover:bg-muted/30 text-xs transition-colors"
                  >
                    <span className="font-mono text-[11px] text-primary shrink-0">
                      {fav.arxiv_id}
                    </span>
                    <span
                      className="text-[11px] text-muted-foreground truncate flex-1"
                      title={fav.title || ""}
                    >
                      {fav.title || "Untitled Paper"}
                    </span>
                    <Link
                      to={`/depot?focus=${encodeURIComponent(fav.arxiv_id)}`}
                      className="text-muted-foreground hover:text-foreground p-0.5"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
