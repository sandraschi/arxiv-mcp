import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookMarked, Heart, Library, Search } from "lucide-react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

type Health = { status: string; service: string };
type Stats = { papers: number; favorites: number; chunks: number; data_dir: string };

export function Dashboard() {
  const { log } = useLogger();
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, s] = await Promise.all([
          apiGet<Health>("/api/health"),
          apiGet<Stats>("/api/stats"),
        ]);
        if (!cancelled) {
          setHealth(h);
          setStats(s);
          log("info", `Health ${h.status} · depot ${s.papers} papers / ${s.chunks} chunks`);
        }
      } catch (e) {
        const m = e instanceof Error ? e.message : String(e);
        if (!cancelled) {
          setErr(m);
          log("error", m);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [log]);

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
    <div className="space-y-8">
      <PageHero eyebrow="arxiv-mcp" title="Read and file arXiv papers without tab chaos" size="large">
        <p className="text-muted-foreground text-base md:text-lg leading-relaxed">
          Use this app in the browser or let a coding agent drive the same features over MCP.{" "}
          <strong className="text-foreground">Search arXiv</strong> is live on the internet. Your{" "}
          <strong className="text-foreground">depot</strong> is everything you keep on this machine: downloaded paper text,
          search index, and bookmarks—nothing is sent to a third-party “cloud” by this UI.
        </p>
        <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
          For SI work, arXiv matters because new capability and safety ideas appear there months before formal journal
          cycles. The goal of this app is simple: help you run a fast daily triage loop, keep the high-signal papers,
          and turn them into searchable notes you can reuse.
        </p>
        <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1.5">
          <li>
            <strong className="text-foreground">Search arXiv</strong> — find papers online by words, subjects, or “what
            just appeared.”
          </li>
          <li>
            <strong className="text-foreground">Your library (depot)</strong> — pull papers onto disk, then read or search
            them without juggling browser tabs.
          </li>
          <li>
            <strong className="text-foreground">MCP</strong> — Cursor, Claude, and other clients can run the same tools
            for you.
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
            Open <strong className="text-foreground">Search arXiv</strong> and choose an SI starter query.
          </li>
          <li>
            Run <strong className="text-foreground">New submissions in one subject</strong> for a 24h or 72h window.
          </li>
          <li>
            Pick 1-3 promising papers and ingest them into <strong className="text-foreground">Your library</strong>.
          </li>
          <li>
            Use <strong className="text-foreground">Search library</strong> to compare recurring claims and methods.
          </li>
          <li>Save recurring queries as favorites so tomorrow starts in one click.</li>
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
        <p className="text-muted-foreground text-sm mt-1">Backend connection and local library size.</p>
      </div>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on <code>10770</code>?
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">API</CardTitle>
          <p className="text-2xl font-semibold mt-1">{health?.status ?? "…"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Papers in your library</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.papers ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Indexed text chunks</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.chunks ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Favorites</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.favorites ?? "—"}</p>
        </Card>
      </div>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">Pages</h2>
        <p className="text-muted-foreground text-sm mt-1">Jump to a workflow.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to} className="block group">
            <Card className="h-full transition-transform group-hover:scale-[1.01]">
              <div className="flex gap-3">
                <t.icon className="h-8 w-8 text-primary shrink-0" />
                <div>
                  <CardTitle>{t.label}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1 leading-snug">{t.desc}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
