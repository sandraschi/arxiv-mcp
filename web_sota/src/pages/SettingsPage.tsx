import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

type Stats = { papers: number; favorites: number; chunks: number; data_dir: string };

export function SettingsPage() {
  const { log } = useLogger();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await apiGet<Stats>("/api/stats");
        setStats(s);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Configuration"
        title="Settings"
        lead="Where your depot stores files on disk and optional keys for tools. Changing the data directory moves your whole library—do that before you rely on paths."
      />
      <Card>
        <CardTitle>Data directory</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 break-all font-mono">{stats?.data_dir ?? "…"}</p>
        <p className="text-xs text-muted-foreground mt-3">
          Override with env <code className="text-primary">ARXIV_MCP_DATA_DIR</code>. Corpus + favorites live in SQLite next
          to markdown files.
        </p>
      </Card>
      <Card>
        <CardTitle>Semantic Scholar</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Optional <code className="text-primary">ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY</code> for higher-rate{" "}
          <code>find_connected_papers</code> calls (MCP tool).
        </p>
      </Card>
    </div>
  );
}
