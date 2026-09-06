import {
  Activity,
  ArrowRight,
  BookMarked,
  Heart,
  Library,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "@/api/client";
import { LlmOnboarding } from "@/components/LlmOnboarding";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";
import { useBackendStore } from "@/lib/store";

type Health = { status: string; service: string };
type Stats = {
  papers: number;
  favorites: number;
  chunks: number;
  data_dir: string;
};

const RETRY_DELAYS = [1, 2, 4, 8, 16];

function retryDelay(attempt: number): number {
  return attempt < RETRY_DELAYS.length ? RETRY_DELAYS[attempt] : 30;
}

export function Dashboard() {
  const { log } = useLogger();
  const setOnline = useBackendStore((s) => s.setOnline);
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [h, s] = await Promise.all([
        apiGet<Health>("/api/health"),
        apiGet<Stats>("/api/stats"),
      ]);
      setHealth(h);
      setStats(s);
      setAttempt(0);
      setOnline(true);
      log(
        "info",
        `Health ${h.status} · depot ${s.papers} papers / ${s.chunks} chunks`,
      );
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

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") {
            setAttempt(0);
            void load();
          } else if (
            typeof event.payload === "string" &&
            event.payload.startsWith("error:")
          ) {
            setOnline(false);
          }
        });
      } catch {
        /* not in Tauri */
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, [load, setOnline]);

  return (
    <div className="space-y-6" data-testid="dashboard">
      <PageHero
        eyebrow="arxiv-mcp"
        title="Search, ingest, and analyse arXiv papers"
        size="default"
      >
        <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
          Search arXiv by keyword or category, ingest papers into a local depot,
          and run epistemic analysis. Backend on :10770 · Vite on :10771 · MCP
          at <code className="text-xs">/mcp</code>
          {health && (
            <span>
              {" "}
              · <span className="text-green-400">Connected</span>
            </span>
          )}
          {err && (
            <span>
              {" "}
              · <span className="text-red-400">Offline</span>
            </span>
          )}
        </p>
        <div className="flex gap-2 pt-1">
          <Button size="sm" asChild>
            <Link to="/search">
              Search arXiv <ArrowRight className="ml-1 h-3 w-3" />
            </Link>
          </Button>
          <Button size="sm" variant="secondary" asChild>
            <Link to="/depot">Your library</Link>
          </Button>
          <Button size="sm" variant="ghost" asChild>
            <Link to="/help">How arXiv works</Link>
          </Button>
        </div>
      </PageHero>

      <LlmOnboarding mode="banner" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link to="/depot" className="block group">
          <Card
            data-testid="kpi-papers"
            className="transition-transform group-hover:scale-[1.02]"
          >
            <CardTitle className="text-sm text-muted-foreground font-normal">
              Papers in library
            </CardTitle>
            <p className="text-2xl font-semibold mt-1">
              {stats?.papers ?? "—"}
            </p>
          </Card>
        </Link>
        <Link to="/semantic" className="block group">
          <Card
            data-testid="kpi-chunks"
            className="transition-transform group-hover:scale-[1.02]"
          >
            <CardTitle className="text-sm text-muted-foreground font-normal">
              Indexed chunks
            </CardTitle>
            <p className="text-2xl font-semibold mt-1">
              {stats?.chunks ?? "—"}
            </p>
          </Card>
        </Link>
        <Link to="/favorites" className="block group">
          <Card
            data-testid="kpi-favorites"
            className="transition-transform group-hover:scale-[1.02]"
          >
            <CardTitle className="text-sm text-muted-foreground font-normal">
              Favorites
            </CardTitle>
            <p className="text-2xl font-semibold mt-1">
              {stats?.favorites ?? "—"}
            </p>
          </Card>
        </Link>
        <Card data-testid="kpi-server">
          <CardTitle className="text-sm text-muted-foreground font-normal flex items-center gap-1">
            <Activity className="h-3 w-3" /> Server
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">
            {health?.service ?? "…"}
          </p>
        </Card>
      </div>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on <code>10770</code>?
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <Link to="/search" className="block group">
          <Card className="transition-transform group-hover:scale-[1.02]">
            <div className="flex items-center gap-3">
              <Search className="h-6 w-6 text-primary shrink-0" />
              <div>
                <CardTitle>Search arXiv</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Keywords, categories, new submissions.
                </p>
              </div>
            </div>
          </Card>
        </Link>
        <Link to="/depot" className="block group">
          <Card className="transition-transform group-hover:scale-[1.02]">
            <div className="flex items-center gap-3">
              <Library className="h-6 w-6 text-primary shrink-0" />
              <div>
                <CardTitle>Your library</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Ingested papers, full text, epistemic profiles.
                </p>
              </div>
            </div>
          </Card>
        </Link>
        <Link to="/semantic" className="block group">
          <Card className="transition-transform group-hover:scale-[1.02]">
            <div className="flex items-center gap-3">
              <BookMarked className="h-6 w-6 text-primary shrink-0" />
              <div>
                <CardTitle>Search library</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  FTS, semantic, or hybrid search over your depot.
                </p>
              </div>
            </div>
          </Card>
        </Link>
        <Link to="/favorites" className="block group">
          <Card className="transition-transform group-hover:scale-[1.02]">
            <div className="flex items-center gap-3">
              <Heart className="h-6 w-6 text-primary shrink-0" />
              <div>
                <CardTitle>Favorites</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Bookmarked arXiv IDs and saved searches.
                </p>
              </div>
            </div>
          </Card>
        </Link>
      </div>
    </div>
  );
}
