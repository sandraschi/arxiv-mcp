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
