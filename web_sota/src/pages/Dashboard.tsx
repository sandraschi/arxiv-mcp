import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookMarked, Heart, Library, Search } from "lucide-react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
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
    { to: "/search", label: "Search arXiv", desc: "Query + categories", icon: Search },
    { to: "/semantic", label: "Depot FTS", desc: "BM25 over ingested chunks", icon: BookMarked },
    { to: "/depot", label: "Depot", desc: "Ingest HTML → Markdown", icon: Library },
    { to: "/favorites", label: "Favorites", desc: "Saved paper IDs", icon: Heart },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Fleet-standard shell: discovery, depot RAG (FTS5), and MCP tools.
        </p>
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
          <CardTitle className="text-sm text-muted-foreground font-normal">Depot papers</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.papers ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">FTS chunks</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.chunks ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Favorites</CardTitle>
          <p className="text-2xl font-semibold mt-1">{stats?.favorites ?? "—"}</p>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to} className="block group">
            <Card className="h-full transition-transform group-hover:scale-[1.01]">
              <div className="flex gap-3">
                <t.icon className="h-8 w-8 text-primary shrink-0" />
                <div>
                  <CardTitle>{t.label}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">{t.desc}</p>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
