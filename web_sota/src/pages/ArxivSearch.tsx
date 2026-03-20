import { useState } from "react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Paper = {
  paper_id: string;
  title: string;
  summary: string;
  authors: string[];
  categories: string[];
  published: string | null;
  html_url: string | null;
  pdf_url: string | null;
};

export function ArxivSearch() {
  const { log } = useLogger();
  const [q, setQ] = useState("all:transformer");
  const [cats, setCats] = useState("cs.AI");
  const [sortBy, setSortBy] = useState("submitted");
  const [loading, setLoading] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [cat, setCat] = useState("cs.LG");
  const [latest, setLatest] = useState<Paper[]>([]);

  async function runSearch() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ q, limit: "15", sort_by: sortBy });
      if (cats.trim()) params.set("categories", cats);
      const data = await apiGet<{ papers: Paper[] }>(`/api/search?${params}`);
      setPapers(data.papers);
      log("info", `arXiv search: ${data.papers.length} results`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runLatest() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ category: cat, limit: "20", hours: "72" });
      const data = await apiGet<{ papers: Paper[] }>(`/api/category/latest?${params}`);
      setLatest(data.papers);
      log("info", `Category ${cat}: ${data.papers.length} recent`);
    } catch (e) {
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">arXiv search</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Live API search + category firehose (rolling window).
        </p>
      </div>

      <Card>
        <CardTitle>Query</CardTitle>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1">
            <label className="text-xs text-muted-foreground">search_query</label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. cat:cs.CL AND ti:attention" />
          </div>
          <div className="w-full sm:w-40 space-y-1">
            <label className="text-xs text-muted-foreground">categories</label>
            <Input value={cats} onChange={(e) => setCats(e.target.value)} placeholder="cs.AI,cs.LG" />
          </div>
          <div className="w-full sm:w-36 space-y-1">
            <label className="text-xs text-muted-foreground">sort</label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background/60 px-2 text-sm"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="submitted">submitted</option>
              <option value="relevance">relevance</option>
              <option value="updated">updated</option>
            </select>
          </div>
          <Button onClick={runSearch} disabled={loading}>
            Search
          </Button>
        </div>
        <ul className="mt-6 space-y-4">
          {papers.map((p) => (
            <li key={p.paper_id} className="border-b border-border/40 pb-4 last:border-0">
              <div className="font-medium">{p.title}</div>
              <div className="text-xs text-muted-foreground mt-1">{p.paper_id} · {p.categories?.join(", ")}</div>
              <p className="text-sm text-muted-foreground mt-2 line-clamp-3">{p.summary}</p>
              <div className="flex gap-3 mt-2 text-xs">
                {p.html_url && (
                  <a className="text-primary hover:underline" href={p.html_url} target="_blank" rel="noreferrer">
                    HTML
                  </a>
                )}
                {p.pdf_url && (
                  <a className="text-primary hover:underline" href={p.pdf_url} target="_blank" rel="noreferrer">
                    PDF
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardTitle>Category latest</CardTitle>
        <div className="mt-4 flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[120px] space-y-1">
            <label className="text-xs text-muted-foreground">category</label>
            <Input value={cat} onChange={(e) => setCat(e.target.value)} />
          </div>
          <Button variant="secondary" onClick={runLatest} disabled={loading}>
            Load ~72h
          </Button>
        </div>
        <ul className="mt-4 space-y-3">
          {latest.map((p) => (
            <li key={p.paper_id} className="text-sm">
              <span className="font-mono text-xs text-primary">{p.paper_id}</span> — {p.title}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
