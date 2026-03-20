import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Row = { arxiv_id: string; title: string; ingested_at: number; source: string };
type Item = {
  arxiv_id: string;
  title: string;
  markdown: string;
  source: string;
  ingested_at: number;
};

export function Depot() {
  const { log } = useLogger();
  const [params] = useSearchParams();
  const focus = params.get("focus");

  const [rows, setRows] = useState<Row[]>([]);
  const [pid, setPid] = useState("2402.08954v1");
  const [ingesting, setIngesting] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Item | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await apiGet<{ ingested: Row[] }>("/api/corpus?limit=200");
      setRows(data.ingested);
    } catch (e) {
      log("error", String(e));
    }
  }, [log]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (focus) setSelected(focus);
  }, [focus]);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoadingDetail(true);
      try {
        const d = await apiGet<Item>(`/api/corpus/item?arxiv_id=${encodeURIComponent(selected)}`);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled) {
          setDetail(null);
          log("error", String(e));
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, log]);

  async function ingest() {
    setIngesting(true);
    try {
      const r = await apiPost<Record<string, unknown>>("/api/depot/ingest", { paper_id: pid });
      log("info", `Ingested ${JSON.stringify(r)}`);
      await refresh();
      if (r.arxiv_id) setSelected(String(r.arxiv_id));
    } catch (e) {
      log("error", String(e));
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Depot</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Ingest experimental HTML → Markdown, chunked into FTS5 for the semantic page.
        </p>
      </div>

      <Card>
        <CardTitle>Ingest paper</CardTitle>
        <div className="mt-4 flex flex-col sm:flex-row gap-2">
          <Input value={pid} onChange={(e) => setPid(e.target.value)} placeholder="arXiv id or URL" className="flex-1" />
          <Button onClick={ingest} disabled={ingesting}>
            {ingesting ? "Fetching…" : "Ingest HTML"}
          </Button>
          <Button variant="outline" type="button" onClick={refresh}>
            Refresh list
          </Button>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="min-h-[320px]">
          <CardTitle>Ingested</CardTitle>
          <ul className="mt-4 space-y-1 max-h-[480px] overflow-y-auto text-sm">
            {rows.map((r) => (
              <li key={r.arxiv_id}>
                <button
                  type="button"
                  className={`w-full text-left rounded-md px-2 py-1.5 hover:bg-muted/50 ${
                    selected === r.arxiv_id ? "bg-secondary" : ""
                  }`}
                  onClick={() => setSelected(r.arxiv_id)}
                >
                  <span className="font-mono text-xs text-primary">{r.arxiv_id}</span>
                  <div className="line-clamp-2">{r.title}</div>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="min-h-[320px]">
          <CardTitle>Reader</CardTitle>
          {loadingDetail && <p className="text-sm text-muted-foreground mt-4">Loading…</p>}
          {!loadingDetail && detail && (
            <div className="mt-4 space-y-2">
              <h2 className="font-semibold">{detail.title}</h2>
              <div className="text-xs text-muted-foreground font-mono">{detail.arxiv_id}</div>
              <div className="text-sm leading-relaxed max-w-none max-h-[520px] overflow-y-auto border border-border/40 rounded-lg p-3 bg-background/40 [&_a]:text-primary">
                <ReactMarkdown>{detail.markdown}</ReactMarkdown>
              </div>
            </div>
          )}
          {!loadingDetail && !detail && (
            <p className="text-sm text-muted-foreground mt-4">Select a paper or ingest one.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
