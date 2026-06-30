import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogger } from "@/context/LoggerContext";

type Hit = {
  arxiv_id: string;
  title: string;
  chunk_idx: number;
  snippet: string;
  rank: number;
  engine?: string;
  distance?: number;
};

type RagStatus = {
  available: boolean;
  enabled?: boolean;
  indexed_chunks?: number;
  model?: string;
  install_hint?: string;
};

type SearchMode = "hybrid" | "semantic" | "fts";

export function DepotSemantic() {
  const { log } = useLogger();
  const [q, setQ] = useState("Copernican intelligence");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [hits, setHits] = useState<Hit[]>([]);
  const [engine, setEngine] = useState("");
  const [rag, setRag] = useState<RagStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiGet<RagStatus>("/api/depot/rag/status");
        setRag(data);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  async function search() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ q, limit: "25", mode });
      const data = await apiGet<{ hits: Hit[]; engine: string }>(
        `/api/depot/search?${params}`,
      );
      setHits(data.hits);
      setEngine(data.engine);
      log("info", `Depot ${data.engine}: ${data.hits.length} hits`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  async function reindex() {
    setReindexing(true);
    try {
      const data = await apiPost<Record<string, unknown>>(
        "/api/depot/rag/reindex",
        {},
      );
      log("info", `Reindexed vectors: ${JSON.stringify(data)}`);
      const status = await apiGet<RagStatus>("/api/depot/rag/status");
      setRag(status);
    } catch (e) {
      log("error", String(e));
    } finally {
      setReindexing(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Your library"
        title="Semantic search over your depot"
        lead="Hybrid mode merges BM25 keyword hits with LanceDB vector similarity (RRF). Install RAG deps with uv sync --extra rag, then ingest papers on Your library."
      />

      {rag && !rag.available && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm">
          Vector search unavailable. Run{" "}
          <span className="font-mono">uv sync --extra rag</span> in the
          arxiv-mcp repo, then reindex. FTS and hybrid (FTS-only fallback) still
          work.
        </div>
      )}

      <Card>
        <CardTitle>Search your library</CardTitle>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="flex-1"
            placeholder="Concept or phrase"
          />
          <select
            className="h-10 rounded-md border border-border bg-background px-3 text-sm"
            value={mode}
            onChange={(e) => setMode(e.target.value as SearchMode)}
          >
            <option value="hybrid">Hybrid (FTS + vectors)</option>
            <option value="semantic">Semantic only</option>
            <option value="fts">Keywords only (BM25)</option>
          </select>
          <Button onClick={search} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Button>
          <Button
            variant="outline"
            onClick={reindex}
            disabled={reindexing || !rag?.available}
          >
            {reindexing ? "Reindexing…" : "Reindex vectors"}
          </Button>
        </div>
        {rag?.available && (
          <p className="text-xs text-muted-foreground mt-2">
            LanceDB: {rag.indexed_chunks ?? 0} chunks · model {rag.model}
            {engine ? ` · last engine: ${engine}` : ""}
          </p>
        )}
        <ul className="mt-6 space-y-4">
          {hits.map((h) => (
            <li
              key={`${h.arxiv_id}-${h.chunk_idx}`}
              className="border-b border-border/30 pb-4 last:border-0"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <Link
                  to={`/depot?focus=${encodeURIComponent(h.arxiv_id)}`}
                  className="font-mono text-sm text-primary hover:underline"
                >
                  {h.arxiv_id}
                </Link>
                <span className="text-[10px] text-muted-foreground">
                  chunk {h.chunk_idx} · score {h.rank?.toFixed?.(3) ?? h.rank}
                  {h.engine ? ` · ${h.engine}` : ""}
                </span>
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
          <p className="text-sm text-muted-foreground mt-4">
            No matches yet. Ingest papers on Your library, reindex vectors if
            needed, then try again.
          </p>
        )}
      </Card>
    </div>
  );
}
