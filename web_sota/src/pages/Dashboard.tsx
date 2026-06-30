import {
  Activity,
  ArrowRight,
  BookMarked,
  Heart,
  Library,
  RefreshCw,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "@/api/client";
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

  // Exponential backoff on error
  useEffect(() => {
    if (!err) return;
    const timer = setTimeout(() => {
      setAttempt((a) => a + 1);
      void load();
    }, retryDelay(attempt) * 1000);
    return () => clearTimeout(timer);
  }, [err, attempt, load]);

  // Tauri backend-status event listener
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
        /* not inside Tauri — HTTP polling handles it */
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, [load, setOnline]);

  const tiles = [
    {
      to: "/search",
      label: "Search arXiv",
      desc: "Find papers by keywords, filter by subject, or browse new submissions in a category.",
      icon: Search,
    },
    {
      to: "/semantic",
      label: "Search library",
      desc: "Keyword search across text you already saved in your depot on this computer.",
      icon: BookMarked,
    },
    {
      to: "/depot",
      label: "Your library",
      desc: "Download papers from arXiv into your depot: stored files plus search index.",
      icon: Library,
    },
    {
      to: "/favorites",
      label: "Favorites",
      desc: "Bookmarked arXiv IDs and short notes.",
      icon: Heart,
    },
  ];

  return (
    <div className="space-y-8" data-testid="dashboard">
      <PageHero
        eyebrow="arxiv-mcp"
        title="Read and file arXiv papers without tab chaos"
        size="large"
      >
        <p className="text-muted-foreground text-base md:text-lg leading-relaxed">
          Use this app in the browser or let a coding agent drive the same
          features over MCP.{" "}
          <strong className="text-foreground">Search arXiv</strong> is live on
          the internet. Your <strong className="text-foreground">depot</strong>{" "}
          is everything you keep on this machine: downloaded paper text, search
          index, and bookmarks—nothing is sent to a third-party "cloud" by this
          UI.
        </p>
        <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
          For SI work, arXiv matters because new capability and safety ideas
          appear there months before formal journal cycles. The goal of this app
          is simple: help you run a fast daily triage loop, keep the high-signal
          papers, and turn them into searchable notes you can reuse.
        </p>
        <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1.5">
          <li>
            <strong className="text-foreground">Search arXiv</strong> — find
            papers online by words, subjects, or "what just appeared."
          </li>
          <li>
            <strong className="text-foreground">Your library (depot)</strong> —
            pull papers onto disk, then read or search them without juggling
            browser tabs.
          </li>
          <li>
            <strong className="text-foreground">MCP</strong> — Cursor, Claude,
            and other clients can run the same tools for you.
          </li>
        </ul>
        <div className="flex flex-wrap gap-3 pt-2">
          <Button asChild>
            <Link to="/search">
              Search arXiv
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/depot">Open your library</Link>
          </Button>
        </div>
      </PageHero>

      <Card>
        <CardTitle>Start here: 5-minute daily SI sweep</CardTitle>
        <ol className="mt-3 list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground">
          <li>
            Open <strong className="text-foreground">Search arXiv</strong> and
            choose an SI starter query.
          </li>
          <li>
            Run{" "}
            <strong className="text-foreground">
              New submissions in one subject
            </strong>{" "}
            for a 24h or 72h window.
          </li>
          <li>
            Pick 1-3 promising papers and ingest them into{" "}
            <strong className="text-foreground">Your library</strong>.
          </li>
          <li>
            Use <strong className="text-foreground">Search library</strong> to
            compare recurring claims and methods.
          </li>
          <li>
            Save recurring queries as favorites so tomorrow starts in one click.
          </li>
        </ol>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" asChild>
            <Link to="/search">Start sweep</Link>
          </Button>
          <Button size="sm" variant="secondary" asChild>
            <Link to="/help">Read SI guide</Link>
          </Button>
          <Button size="sm" variant="outline" asChild>
            <Link to="/help">Agentic workflow examples</Link>
          </Button>
        </div>
      </Card>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">Status</h2>
        <p className="text-muted-foreground text-sm mt-1">
          Backend connection and local library size.
        </p>
      </div>

      {/* Backend status indicator */}
      <div className="flex items-center gap-3">
        <div
          data-testid="backend-dot"
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
            err
              ? "bg-red-500/10 text-red-400"
              : health
                ? "bg-green-500/10 text-green-400"
                : "bg-yellow-500/10 text-yellow-400"
          }`}
        >
          <span
            className={`relative flex h-2.5 w-2.5 ${err ? "bg-red-500" : health ? "bg-emerald-500" : "bg-gray-500"} rounded-full`}
          >
            {!err && health && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
          </span>
          {err ? "Offline" : health ? "Connected" : "Connecting..."}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void load()}
          className="border-border text-muted-foreground"
        >
          <RefreshCw className="mr-1 h-3 w-3" />
          Refresh
        </Button>
        {err && (
          <span className="text-xs text-muted-foreground">
            Backend not reachable on 127.0.0.1:10770
          </span>
        )}
      </div>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on <code>10770</code>?
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card data-testid="kpi-server">
          <CardTitle className="text-sm text-muted-foreground font-normal flex items-center gap-1">
            <Activity className="h-3 w-3" /> Server
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">
            {health?.service ?? "…"}
          </p>
        </Card>
        <Card data-testid="kpi-papers">
          <CardTitle className="text-sm text-muted-foreground font-normal">
            Papers in your library
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.papers ?? "—"}</p>
        </Card>
        <Card data-testid="kpi-chunks">
          <CardTitle className="text-sm text-muted-foreground font-normal">
            Indexed text chunks
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.chunks ?? "—"}</p>
        </Card>
        <Card data-testid="kpi-favorites">
          <CardTitle className="text-sm text-muted-foreground font-normal">
            Favorites
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">
            {stats?.favorites ?? "—"}
          </p>
        </Card>
      </div>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">Pages</h2>
        <p className="text-muted-foreground text-sm mt-1">
          Jump to a workflow.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to} className="block group">
            <Card className="h-full transition-transform group-hover:scale-[1.01]">
              <div className="flex gap-3">
                <t.icon className="h-8 w-8 text-primary shrink-0" />
                <div>
                  <CardTitle>{t.label}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1 leading-snug">
                    {t.desc}
                  </p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
