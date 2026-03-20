import { useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Hit = {
  arxiv_id: string;
  title: string;
  chunk_idx: number;
  snippet: string;
  rank: number;
};

export function DepotSemantic() {
  const { log } = useLogger();
  const [q, setQ] = useState("method");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);

  async function search() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ q, limit: "25" });
      const data = await apiGet<{ hits: Hit[]; engine: string }>(`/api/depot/search?${params}`);
      setHits(data.hits);
      log("info", `Depot ${data.engine}: ${data.hits.length} hits`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Depot semantic / RAG</h1>
        <p className="text-sm text-muted-foreground mt-1">
          <strong className="text-foreground">SQLite FTS5</strong> over chunked Markdown from ingested papers (porter +
          unicode61). Snippets use BM25 ranking. For dense vectors, use your MCP host or extend the server with
          embeddings.
        </p>
      </div>

      <Card>
        <CardTitle>Search depot</CardTitle>
        <div className="mt-4 flex gap-2">
          <Input value={q} onChange={(e) => setQ(e.target.value)} className="flex-1" />
          <Button onClick={search} disabled={loading}>
            Search
          </Button>
        </div>
        <ul className="mt-6 space-y-4">
          {hits.map((h) => (
            <li key={`${h.arxiv_id}-${h.chunk_idx}`} className="border-b border-border/30 pb-4 last:border-0">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <Link
                  to={`/depot?focus=${encodeURIComponent(h.arxiv_id)}`}
                  className="font-mono text-sm text-primary hover:underline"
                >
                  {h.arxiv_id}
                </Link>
                <span className="text-[10px] text-muted-foreground">chunk {h.chunk_idx} · bm25 {h.rank?.toFixed?.(3) ?? h.rank}</span>
              </div>
              <div className="text-sm font-medium mt-1">{h.title}</div>
              <div
                className="text-sm text-muted-foreground mt-2 max-w-none [&_mark]:bg-primary/30 [&_mark]:text-foreground"
                dangerouslySetInnerHTML={{ __html: h.snippet }}
              />
            </li>
          ))}
        </ul>
        {hits.length === 0 && (
          <p className="text-sm text-muted-foreground mt-4">Ingest papers in Depot first; empty index returns no hits.</p>
        )}
      </Card>
    </div>
  );
}
